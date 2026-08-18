#!/usr/bin/env python3
"""PostToolUse: log sizes, optionally replace fat/image output. Always fail-open."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from spendlib.config import load_config
from spendlib.metrics import append_metric
from spendlib.shrink import shrink_tool


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        data = json.loads(raw)
    except Exception:
        return 0

    try:
        cfg = load_config()
        tool_name = data.get("tool_name") or ""
        tool_input = data.get("tool_input")
        tool_response = data.get("tool_response")
        decision = shrink_tool(tool_name, tool_input, tool_response, cfg)
        append_metric(
            {
                "session_id": data.get("session_id"),
                "cwd": data.get("cwd"),
                "tool_name": tool_name,
                "tool_use_id": data.get("tool_use_id"),
                "bytes_in": decision["bytes_in"],
                "bytes_out": decision["bytes_out"],
                "shrunk": decision["shrunk"],
                "note": decision.get("note") or "",
            }
        )
        out: dict = {}
        hook: dict = {"hookEventName": "PostToolUse"}
        if decision.get("updated_tool_output") is not None:
            hook["updatedToolOutput"] = decision["updated_tool_output"]
        if decision.get("updated_mcp_output") is not None:
            hook["updatedMCPToolOutput"] = decision["updated_mcp_output"]
        if decision.get("note"):
            hook["additionalContext"] = decision["note"]
        if len(hook) > 1:
            out["hookSpecificOutput"] = hook
        print(json.dumps(out), file=sys.stdout)
    except Exception:
        # fail open — never break the session
        print("{}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
