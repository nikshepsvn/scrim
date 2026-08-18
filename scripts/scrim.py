#!/usr/bin/env python3
"""scrim — report, backfill, retrieve omitted tool output."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrim.config import data_dir, load_config
from scrim.metrics import summarize
from scrim.observe import parse_projects, parse_transcript
from scrim.report import render
from scrim.stash import get as stash_get


def cmd_report(today: bool, session_path: str | None) -> int:
    prefix = datetime.now(timezone.utc).date().isoformat() if today else None
    if session_path:
        usage = parse_transcript(Path(session_path))
    elif today:
        usage = parse_projects(prefix)
    else:
        usage = parse_projects(None)
    tools = summarize(prefix)
    text = render(usage, tools)
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


def main() -> int:
    p = argparse.ArgumentParser(description="Scrim: cost observability and tool-output thinning")
    p.add_argument("--today", action="store_true")
    p.add_argument("--backfill", action="store_true", help="alias for full transcript usage")
    p.add_argument("--session", metavar="JSONL", help="one Claude Code transcript")
    p.add_argument("--config", action="store_true")
    p.add_argument("cmd", nargs="?", help="get")
    p.add_argument("target", nargs="?", help="stash id")
    p.add_argument("lines", nargs="?", help="start-end line range")
    args = p.parse_args()

    if args.config:
        print(json.dumps(load_config(), indent=2))
        print("edit", data_dir() / "config.json")
        return 0
    if args.cmd == "get":
        if not args.target:
            print("usage: scrim get <id> [start-end]", file=sys.stderr)
            return 2
        return cmd_get(args.target, args.lines)
    if args.backfill:
        return cmd_report(today=False, session_path=None)
    return cmd_report(today=args.today, session_path=args.session)


if __name__ == "__main__":
    raise SystemExit(main())
