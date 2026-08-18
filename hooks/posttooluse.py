#!/usr/bin/env python3
"""PostToolUse: thin, stash original, log. Always fail-open."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# env when launched via run.sh; __file__ when invoked directly (e.g. Codex)
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or str(Path(__file__).resolve().parents[1])
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)


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
        # imports inside the guard: a broken install must not exit non-zero
        from scrim.config import load_config
        from scrim.metrics import append_metric
        from scrim.shrink import response_text, shrink_tool
        from scrim.stash import put as stash_put

        cfg = load_config()
        tool_name = data.get("tool_name") or ""
        tool_input = data.get("tool_input")
        tool_response = data.get("tool_response")
        decision = shrink_tool(tool_name, tool_input, tool_response, cfg)
        # Codex stamps turn_id on hook input; its PostToolUse output schema
        # (additionalProperties: false) accepts updatedMCPToolOutput but not
        # updatedToolOutput, so a builtin-tool rewrite would be rejected
        # whole. Codex's only shipped replacement lever is decision:"block",
        # whose reason text replaces the tool result — opt in via
        # codex_block_thin. Otherwise track those calls instead of claiming
        # a thin that never reached the model.
        codex = "turn_id" in data
        if codex and decision.get("updated_mcp_output") is None:
            if decision.get("updated_tool_output") is not None:
                if cfg.get("codex_block_thin"):
                    decision["codex_block"] = True
                    decision["note"] = (decision.get("note") or "") + "; codex-block"
                else:
                    decision.pop("updated_tool_output")
                    decision["bytes_out"] = decision["bytes_in"]
                    decision["shrunk"] = False
                    # metrics-only: additionalContext would spam the model
                    decision["log_note"] = "codex: builtin output not rewritable"
                    decision["note"] = ""
        stash_id = None
        if decision.get("shrunk") and cfg.get("stash", True):
            try:
                original = response_text(tool_response)
                if original:
                    stash_id = stash_put(
                        original,
                        tool_use_id=data.get("tool_use_id"),
                        kind=decision.get("kind") or "",
                        tool_name=tool_name,
                    )
                if stash_id:
                    extra = f"\n[scrim] full output: scrim get {stash_id}"
                    _append_note(decision, extra)
                    decision["note"] = (decision.get("note") or "") + extra
            except Exception:
                stash_id = None  # stash trouble must not cost us the thinning
        try:
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
                    "note": (decision.get("note") or decision.get("log_note") or "")[:200],
                    "stash_id": stash_id,
                }
            )
        except Exception:
            pass  # a full disk must not cost us the thinned output
        if decision.get("codex_block"):
            # block's reason replaces the tool result on Codex; say the tool
            # succeeded so the model doesn't retry a command that worked
            body = response_text(decision.get("updated_tool_output")) or ""
            reason = (
                "[scrim] The tool ran successfully. Its full output was "
                "replaced with this signal-only view:\n" + body
            )
            print(json.dumps({"decision": "block", "reason": reason}), file=sys.stdout)
            return 0
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
