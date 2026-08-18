#!/usr/bin/env python3
"""Stop: write last report; warn if this session was heavy."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# env when launched via run.sh; __file__ when invoked directly (e.g. Codex)
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or str(Path(__file__).resolve().parents[1])
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

# parsing a transcript this big can blow the hook timeout; skip usage, keep tools
MAX_TRANSCRIPT_BYTES = 50 * 1024 * 1024


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print("{}")
        return 0
    try:
        # imports inside the guard: a broken install must not exit non-zero
        from scrim.config import data_dir, load_config
        from scrim.metrics import summarize
        from scrim.observe import parse_transcript
        from scrim.report import render
        from scrim.timeutil import today_local

        cfg = load_config()
        usage = {}
        tpath = data.get("transcript_path")
        if tpath:
            p = Path(tpath)
            try:
                too_big = p.stat().st_size > MAX_TRANSCRIPT_BYTES
            except OSError:
                too_big = False
            if not too_big:
                usage = parse_transcript(p)
        tools = summarize(day=today_local())
        text = render(usage, tools)
        last = data_dir() / "last.txt"
        last.write_text(text, encoding="utf-8")
        (data_dir() / "last.json").write_text(
            json.dumps({"usage": usage, "tools": tools}, default=str, indent=2),
            encoding="utf-8",
        )
        msgs = []
        sid = data.get("session_id")
        session_tools = summarize(session_id=sid) if sid else {}
        sess_in = session_tools.get("bytes_in") or 0
        warn_mb = float(cfg.get("session_tool_mb_warn") or 2)
        if sess_in >= warn_mb * 1_000_000:
            msgs.append(f"this session: {sess_in/1e6:.1f} MB of tool results. Run /scrim.")
        cost = float((usage.get("total") or {}).get("cost") or 0)
        warn_usd = float(cfg.get("warn_session_usd") or 0)
        if warn_usd and cost >= warn_usd:
            msgs.append(f"session shadow cost ${cost:,.0f} (list price, not Stripe).")
        hook = {"hookEventName": "Stop"}
        if msgs:
            hook["additionalContext"] = "[scrim] " + " ".join(msgs)
        print(json.dumps({"hookSpecificOutput": hook} if len(hook) > 1 else {}))
    except Exception:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
