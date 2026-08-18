#!/usr/bin/env python3
"""Stop: optional one-line warning if this session's hook metrics are huge."""

from __future__ import annotations

import json
import os
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from sift.config import load_config
from sift.metrics import iter_metrics


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    try:
        cfg = load_config()
        sid = data.get("session_id")
        if not sid:
            return 0
        total_in = 0
        n = 0
        for row in iter_metrics() or []:
            if row.get("session_id") == sid:
                n += 1
                total_in += int(row.get("bytes_in") or 0)
        # ~4 chars/token; warn on very fat sessions only
        if n and total_in >= 2_000_000:
            mb = total_in / 1e6
            msg = f"[sift] this session's tool results were {mb:.1f} MB across {n} calls. Run /sift."
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "Stop",
                            "additionalContext": msg,
                        }
                    }
                )
            )
        else:
            print("{}")
    except Exception:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
