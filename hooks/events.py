#!/usr/bin/env python3
"""Session events: subagent swarms and compactions. Cannot block either —
this hook counts and hints. Fail-open."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# env when launched via run.sh; __file__ when invoked directly (e.g. Codex)
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or str(Path(__file__).resolve().parents[1])
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)


def _open_count(iter_metrics, session_id: str) -> int:
    n = 0
    for row in iter_metrics() or []:
        if row.get("session_id") != session_id:
            continue
        k = row.get("kind")
        if k == "subagent_start":
            n += 1
        elif k == "subagent_stop":
            n = max(0, n - 1)
    return n


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print("{}")
        return 0
    try:
        # imports inside the guard: a broken install must not exit non-zero
        from scrim.config import load_config
        from scrim.metrics import append_metric, iter_metrics

        cfg = load_config()
        event = data.get("hook_event_name") or ""
        sid = data.get("session_id")
        hook = {"hookEventName": event or "SubagentStart"}

        if event == "PreCompact":
            # each compaction means the window overflowed — the exact thing
            # thinning exists to delay. Count it; /scrim surfaces the total.
            # Claude Code names the field compaction_reason; Codex names it trigger.
            append_metric(
                {
                    "session_id": sid,
                    "kind": "compact",
                    "tool_name": data.get("compaction_reason") or data.get("trigger") or "auto",
                    "bytes_in": 0,
                    "bytes_out": 0,
                    "shrunk": False,
                }
            )
        else:
            agent_type = data.get("agent_type") or data.get("agent_id") or ""
            kind = "subagent_start" if event == "SubagentStart" else "subagent_stop"
            append_metric(
                {
                    "session_id": sid,
                    "kind": kind,
                    "tool_name": agent_type,
                    "bytes_in": 0,
                    "bytes_out": 0,
                    "shrunk": False,
                }
            )
            if kind == "subagent_start" and sid:
                cap = int(cfg.get("max_open_subagents") or 8)
                open_n = _open_count(iter_metrics, sid)
                if open_n >= cap:
                    hook["additionalContext"] = (
                        f"[scrim] {open_n} subagents already open in this session "
                        f"(cap {cap}). Finish work yourself instead of spawning more."
                    )
        print(json.dumps({"hookSpecificOutput": hook} if len(hook) > 1 else {}))
    except Exception:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
