#!/usr/bin/env python3
"""UserPromptSubmit: warn once per session when tool output piles up.

The Stop-hook warning arrives after the turn; this one lands where it can
still change what happens. Fail-open."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# env when launched via run.sh; __file__ when invoked directly (e.g. Codex)
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or str(Path(__file__).resolve().parents[1])
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print("{}")
        return 0
    try:
        # imports inside the guard: a broken install must not exit non-zero
        from scrim.config import load_config
        from scrim.metrics import append_metric, iter_metrics, summarize

        cfg = load_config()
        sid = data.get("session_id")
        warn_mb = float(cfg.get("session_tool_mb_warn") or 0)
        if not sid or warn_mb <= 0:
            print("{}")
            return 0
        already = any(
            row.get("kind") == "mb_warned" and row.get("session_id") == sid
            for row in iter_metrics() or []
        )
        if already:
            print("{}")
            return 0
        mb = (summarize(session_id=sid).get("bytes_in") or 0) / 1e6
        if mb < warn_mb:
            print("{}")
            return 0
        append_metric(
            {"session_id": sid, "kind": "mb_warned", "bytes_in": 0, "bytes_out": 0, "shrunk": False}
        )
        hook = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"[scrim] {mb:.1f} MB of tool output already ran through this "
                "session. Prefer subagents for further fat reads; /scrim shows "
                "the breakdown. (One-time note.)"
            ),
        }
        print(json.dumps({"hookSpecificOutput": hook}))
    except Exception:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
