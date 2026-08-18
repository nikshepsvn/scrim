#!/usr/bin/env python3
"""Stop: write last report; warn if the session was huge."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from scrim.config import data_dir, load_config
from scrim.metrics import summarize
from scrim.observe import parse_transcript
from scrim.report import render


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print("{}")
        return 0
    try:
        cfg = load_config()
        today = datetime.now(timezone.utc).date().isoformat()
        usage = {}
        tpath = data.get("transcript_path")
        if tpath:
            usage = parse_transcript(Path(tpath))
        tools = summarize(today)
        text = render(usage, tools)
        last = data_dir() / "last.txt"
        last.write_text(text, encoding="utf-8")
        (data_dir() / "last.json").write_text(
            json.dumps({"usage": usage, "tools": tools}, default=str, indent=2),
            encoding="utf-8",
        )
        tot_in = tools.get("bytes_in") or 0
        warn_mb = float(cfg.get("session_tool_mb_warn") or 2)
        hook = {"hookEventName": "Stop"}
        if tot_in >= warn_mb * 1_000_000:
            hook["additionalContext"] = (
                f"[scrim] this session: {tot_in/1e6:.1f} MB of tool results. Run /scrim."
            )
        print(json.dumps({"hookSpecificOutput": hook} if len(hook) > 1 else {}))
    except Exception:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
