#!/usr/bin/env python3
"""CLI: spend  |  spend --today  |  spend --backfill"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spendlib.config import data_dir, load_config
from spendlib.metrics import summarize
from spendlib.prices import cost_usd


def print_summary(s: dict, title: str) -> None:
    saved = s["saved"]
    print(title)
    print(f"  tool calls     {s['n']:,}")
    print(f"  bytes in       {s['bytes_in']/1e6:.2f} MB")
    print(f"  bytes out      {s['bytes_out']/1e6:.2f} MB")
    print(f"  thinned        {s['shrunk']:,} calls, {saved/1e6:.2f} MB dropped")
    if s["by_tool"]:
        print("  top tools")
        for name, v in list(s["by_tool"].items())[:8]:
            print(f"    {name:<40} n={v['n']:<5} {v['in']/1e6:6.2f} MB")


def backfill_transcripts() -> None:
    """One-shot: estimate API-eq $ from ~/.claude/projects (usage fields only)."""
    root = Path.home() / ".claude" / "projects"
    if not root.exists():
        print("no ~/.claude/projects", file=sys.stderr)
        return
    by_model = {}
    n = 0
    total = 0.0
    for path in root.rglob("*.jsonl"):
        try:
            fh = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if not line.startswith("{"):
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if o.get("type") != "assistant":
                    continue
                msg = o.get("message") or {}
                if not isinstance(msg, dict):
                    continue
                model = msg.get("model") or "unknown"
                if model == "<synthetic>":
                    continue
                u = msg.get("usage") or {}
                if not u:
                    continue
                cc = u.get("cache_creation") or {}
                cw1h = cc.get("ephemeral_1h_input_tokens") if isinstance(cc, dict) else 0
                c = cost_usd(
                    model,
                    u.get("input_tokens") or 0,
                    u.get("output_tokens") or 0,
                    u.get("cache_read_input_tokens") or 0,
                    u.get("cache_creation_input_tokens") or 0,
                    cw1h or 0,
                )
                by_model[model] = by_model.get(model, 0.0) + c
                total += c
                n += 1
    print(f"transcripts: {n:,} assistant turns, ${total:,.0f} API-equivalent (not cash)")
    for m, v in sorted(by_model.items(), key=lambda kv: -kv[1]):
        print(f"  {m:<32} ${v:,.0f}")
    print("Max/Ultra subscribers do not pay this. It is list-price shadow cost.")


def main() -> int:
    p = argparse.ArgumentParser(description="Local Claude Code spend tracker")
    p.add_argument("--today", action="store_true")
    p.add_argument("--backfill", action="store_true", help="sum API-eq $ from ~/.claude/projects")
    p.add_argument("--config", action="store_true")
    args = p.parse_args()

    if args.config:
        print(json.dumps(load_config(), indent=2))
        print("edit", data_dir() / "config.json")
        return 0
    if args.backfill:
        backfill_transcripts()
        return 0

    prefix = None
    title = "all hook metrics"
    if args.today:
        prefix = datetime.now(timezone.utc).date().isoformat()
        title = f"today {prefix}"
    print_summary(summarize(prefix), title)
    print(f"data: {data_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
