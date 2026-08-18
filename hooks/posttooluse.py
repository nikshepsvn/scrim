#!/usr/bin/env python3
"""PostToolUse: thin, stash original, log. Always fail-open."""

from __future__ import annotations

import json
import os
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from sift.config import load_config
from sift.metrics import append_metric
from sift.shrink import response_text, shrink_tool
from sift.stash import put as stash_put


def _append_note(decision: dict, extra: str) -> None:
    for key in ("updated_tool_output", "updated_mcp_output"):
        blob = decision.get(key)
        if isinstance(blob, dict) and isinstance(blob.get("stdout"), str):
            blob["stdout"] = blob["stdout"] + extra
        elif isinstance(blob, dict) and isinstance(blob.get("content"), str):
            blob["content"] = blob["content"] + extra
        elif isinstance(blob, list):
            blob.append({"type": "text", "text": extra.strip()})


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
        stash_id = None
        if decision.get("shrunk") and cfg.get("stash", True):
            original = response_text(tool_response)
            if original:
                stash_id = stash_put(
                    original,
                    tool_use_id=data.get("tool_use_id"),
                    kind=decision.get("kind") or "",
                    tool_name=tool_name,
                )
                if stash_id:
                    extra = f"\n[sift] full output: sift get {stash_id}"
                    _append_note(decision, extra)
                    decision["note"] = (decision.get("note") or "") + extra
        append_metric(
            {
                "session_id": data.get("session_id"),
                "cwd": data.get("cwd"),
                "tool_name": tool_name,
                "tool_use_id": data.get("tool_use_id"),
                "bytes_in": decision["bytes_in"],
                "bytes_out": decision["bytes_out"],
                "shrunk": decision["shrunk"],
                "kind": decision.get("kind") or "",
                "note": (decision.get("note") or "")[:200],
                "stash_id": stash_id,
            }
        )
        hook: dict = {"hookEventName": "PostToolUse"}
        if decision.get("updated_tool_output") is not None:
            hook["updatedToolOutput"] = decision["updated_tool_output"]
        if decision.get("updated_mcp_output") is not None:
            hook["updatedMCPToolOutput"] = decision["updated_mcp_output"]
        if decision.get("note"):
            hook["additionalContext"] = decision["note"][:500]
        out = {"hookSpecificOutput": hook} if len(hook) > 1 else {}
        print(json.dumps(out), file=sys.stdout)
    except Exception:
        print("{}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
