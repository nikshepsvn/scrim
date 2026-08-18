#!/usr/bin/env python3
"""scrim — report, backfill, retrieve omitted tool output, check health."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scrim as scrim_pkg
from scrim.config import config_path, data_dir, load_config, load_config_report
from scrim.metrics import daily_tools, metrics_path, prune_metrics, summarize
from scrim.observe import (
    daily_codex,
    daily_usage,
    parse_codex_sessions,
    parse_projects,
    parse_transcript,
    window_start,
)
from scrim.report import render
from scrim.stash import blobs_dir, entries as stash_entries, gc as stash_gc, get as stash_get
from scrim.timeutil import today_local


def cmd_report(today: bool, session_path: str | None, as_json: bool) -> int:
    day = today_local() if today else None
    if session_path:
        usage = parse_transcript(Path(session_path))
    else:
        usage = parse_projects(day)
    codex = None if session_path else parse_codex_sessions(day)
    tools = summarize(day)
    if as_json:
        print(json.dumps(
            {"day": day, "usage": usage, "codex": codex, "tools": tools},
            default=str, indent=2,
        ))
        return 0
    text = render(usage, tools, codex)
    print(text, end="")
    print(f"data: {data_dir()}")
    try:
        (data_dir() / "last.txt").write_text(text, encoding="utf-8")
    except OSError:
        pass
    return 0


def cmd_get(bid: str, lines: str | None) -> int:
    start = end = None
    if lines:
        if "-" in lines:
            a, b = lines.split("-", 1)
            start, end = int(a), int(b)
        else:
            start = end = int(lines)
    text = stash_get(bid, start, end)
    if text is None:
        print(f"scrim: no stash {bid!r}", file=sys.stderr)
        return 1
    print(text)
    return 0


def cmd_stashes() -> int:
    rows = stash_entries(20)
    if not rows:
        print("no stashes")
        return 0
    now = time.time()
    print(f"{'id':<18} {'age':>6} {'size':>8}  {'kind':<16} tool")
    for row in rows:
        age = "?"
        try:
            ts = datetime.fromisoformat(str(row.get("ts")).replace("Z", "+00:00"))
            hours = max(0.0, (now - ts.timestamp()) / 3600)
            age = f"{hours:.0f}h" if hours < 48 else f"{hours/24:.0f}d"
        except (ValueError, TypeError):
            pass
        size = f"{(row.get('bytes') or 0)/1000:.0f} KB"
        live = "" if row.get("live") else "  (expired)"
        print(
            f"{row['id']:<18} {age:>6} {size:>8}  {(row.get('kind') or '-'):<16} "
            f"{row.get('tool_name') or '-'}{live}"
        )
    print("\nscrim get <id> [start-end]")
    return 0


def cmd_kinds(today: bool) -> int:
    day = today_local() if today else None
    tools = summarize(day)
    kinds = tools.get("by_kind") or {}
    if not kinds:
        print("no hook metrics yet")
        return 0
    scope = f"today ({day})" if day else "all time"
    print(f"kind breakdown — {scope}")
    print(f"{'kind':<16} {'n':>6} {'in MB':>8} {'out MB':>8} {'saved MB':>9}")
    for kind, v in kinds.items():
        saved = max(0, v["in"] - v["out"])
        print(f"{kind:<16} {v['n']:>6} {v['in']/1e6:>8.2f} {v['out']/1e6:>8.2f} {saved/1e6:>9.2f}")
    return 0


def cmd_days(days_arg: str | None) -> int:
    days = 7
    if days_arg:
        try:
            days = max(1, min(90, int(days_arg)))
        except ValueError:
            print(f"scrim: days wants a day count, got {days_arg!r}", file=sys.stderr)
            return 2
    claude = daily_usage(days)
    codex = daily_codex(days)
    tools = daily_tools(window_start(days))
    all_days = sorted(set(claude) | set(codex) | set(tools), reverse=True)
    if not all_days:
        print("no usage in range")
        return 0
    print(f"last {days} days  (list prices, not Stripe)")
    print(f"{'day':<12} {'claude $':>9} {'codex $':>8} {'turns':>7} {'tool MB in→out':>18}")
    for day in all_days:
        c = claude.get(day) or {}
        x = codex.get(day) or {}
        t = tools.get(day) or {}
        turns = (c.get("turns") or 0) + (x.get("turns") or 0)
        mb = f"{(t.get('in') or 0)/1e6:.2f} → {(t.get('out') or 0)/1e6:.2f}" if t else "-"
        print(
            f"{day:<12} {c.get('cost') or 0:>9,.0f} {x.get('cost') or 0:>8,.0f} "
            f"{turns:>7,} {mb:>18}"
        )
    total_c = sum(v["cost"] for v in claude.values())
    total_x = sum(v["cost"] for v in codex.values())
    print(f"{'total':<12} {total_c:>9,.0f} {total_x:>8,.0f}")
    return 0


def cmd_prune(days_arg: str | None) -> int:
    days = 90
    if days_arg:
        try:
            days = max(1, int(days_arg))
        except ValueError:
            print(f"scrim: prune wants a day count, got {days_arg!r}", file=sys.stderr)
            return 2
    stash_gc()
    dropped = prune_metrics(keep_days=days)
    print(f"stash gc done; dropped {dropped} metric rows older than {days} days")
    return 0


def _doctor_line(ok: bool, label: str, detail: str = "") -> None:
    mark = "ok " if ok else "!! "
    print(f"  {mark} {label}" + (f" — {detail}" if detail else ""))


def cmd_doctor() -> int:
    print(f"scrim {scrim_pkg.__version__}")
    hard_fail = False

    v = sys.version_info
    _doctor_line(v >= (3, 9), f"python {v.major}.{v.minor}.{v.micro}", sys.executable)

    d = data_dir()
    writable = os.access(d, os.W_OK)
    hard_fail |= not writable
    _doctor_line(writable, f"data dir {d}", "" if writable else "not writable")

    cpath = config_path()
    if cpath.exists():
        _, warnings = load_config_report()
        _doctor_line(not warnings, f"config {cpath}", "; ".join(warnings) if warnings else "valid")
    else:
        _doctor_line(True, "config", f"defaults (no {cpath})")

    mpath = metrics_path()
    if mpath.exists():
        rows_today = summarize(today_local()).get("n") or 0
        size_mb = mpath.stat().st_size / 1e6
        detail = f"{rows_today} tool calls today, {size_mb:.1f} MB"
        if size_mb > 20:
            detail += " — consider `scrim prune`"
        _doctor_line(size_mb <= 20, "metrics", detail)
    else:
        _doctor_line(False, "metrics", "no metrics.jsonl yet — hooks not installed, or no tool has run")

    blobs = list(blobs_dir().glob("*.txt"))
    blob_mb = sum(p.stat().st_size for p in blobs) / 1e6 if blobs else 0.0
    _doctor_line(True, "stash", f"{len(blobs)} blobs, {blob_mb:.1f} MB")

    cfg = load_config()
    backend = (cfg.get("reducer") or "off").lower()
    if backend in {"off", "false", "0", ""}:
        _doctor_line(True, "reducer", "off (deterministic filters only)")
    else:
        env_names = ["OPENROUTER_API_KEY", "SCRIM_REDUCER_KEY", "SPEND_REDUCER_KEY"]
        if backend in {"haiku", "anthropic"}:
            env_names.insert(0, "ANTHROPIC_API_KEY")
        source = next((n for n in env_names if os.environ.get(n)), None)
        if not source and cfg.get("reducer_api_key"):
            source = "config reducer_api_key"
        _doctor_line(
            bool(source),
            f"reducer {backend} ({cfg.get('reducer_model')})",
            f"key via {source}" if source else "no API key found — reducer will silently skip",
        )

    proj = Path.home() / ".claude" / "projects"
    if proj.exists():
        count = sum(1 for _ in proj.rglob("*.jsonl"))
        _doctor_line(count > 0, "transcripts", f"{count} jsonl files under {proj}")
    else:
        _doctor_line(False, "transcripts", f"{proj} missing — usage report will be empty")

    codex = Path.home() / ".codex" / "sessions"
    if codex.exists():
        count = sum(1 for _ in codex.rglob("*.jsonl"))
        _doctor_line(True, "codex", f"{count} rollout files under {codex}")
    else:
        _doctor_line(True, "codex", "not installed (no ~/.codex/sessions)")

    return 1 if hard_fail else 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="scrim",
        description="Scrim: cost observability and tool-output thinning",
    )
    p.add_argument("--today", action="store_true", help="limit to the local calendar day")
    p.add_argument("--backfill", action="store_true", help="lifetime transcript usage (alias for the default report)")
    p.add_argument("--session", metavar="JSONL", help="one Claude Code transcript")
    p.add_argument("--config", action="store_true", help="print effective config and any warnings")
    p.add_argument("--json", action="store_true", help="machine-readable report")
    p.add_argument("--version", action="store_true", help="print version")
    p.add_argument(
        "cmd",
        nargs="?",
        choices=["get", "stashes", "kinds", "days", "doctor", "prune"],
        help="get <id> [range] | stashes | kinds | days [n] | doctor | prune [days]",
    )
    p.add_argument("target", nargs="?", help="stash id (get) or day count (days/prune)")
    p.add_argument("lines", nargs="?", help="start-end line range (get)")
    args = p.parse_args()

    if args.version:
        print(f"scrim {scrim_pkg.__version__}")
        return 0
    if args.config:
        cfg, warnings = load_config_report()
        print(json.dumps(cfg, indent=2))
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        print(f"edit {config_path()}")
        return 0
    if args.cmd == "get":
        if not args.target:
            print("usage: scrim get <id> [start-end]", file=sys.stderr)
            return 2
        return cmd_get(args.target, args.lines)
    if args.cmd == "stashes":
        return cmd_stashes()
    if args.cmd == "kinds":
        return cmd_kinds(args.today)
    if args.cmd == "days":
        return cmd_days(args.target)
    if args.cmd == "doctor":
        return cmd_doctor()
    if args.cmd == "prune":
        return cmd_prune(args.target)
    if args.backfill:
        return cmd_report(today=False, session_path=None, as_json=args.json)
    return cmd_report(today=args.today, session_path=args.session, as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
