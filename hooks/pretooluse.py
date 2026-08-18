#!/usr/bin/env python3
"""PreToolUse: cap unbounded list/grep before they run. Fail-open."""

from __future__ import annotations

import json
import os
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from scrim.config import load_config
from scrim.constrain import constrain


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print("{}")
        return 0
    try:
        cfg = load_config()
        decision = constrain(data.get("tool_name") or "", data.get("tool_input"), cfg)
        hook = {"hookEventName": "PreToolUse"}
        if decision.get("updated_input") is not None:
            hook["updatedInput"] = decision["updated_input"]
        if decision.get("note"):
            hook["additionalContext"] = f"[scrim] {decision['note']}"
        if decision.get("additionalContext"):
            hook["additionalContext"] = decision["additionalContext"]
        out = {"hookSpecificOutput": hook} if len(hook) > 1 else {}
        print(json.dumps(out))
    except Exception:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
