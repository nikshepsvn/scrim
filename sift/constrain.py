"""PreToolUse: stop fat dumps before they exist. Fail-open."""

from __future__ import annotations

import re
from typing import Any

LIST_CMD = re.compile(r"\b(ls\s+-\w*R|find\s|tree\b)", re.I)
RG_CMD = re.compile(r"\b(rg|grep|git\s+grep)\b", re.I)


def constrain(tool_name: str, tool_input: Any, cfg: dict) -> dict:
    if not cfg.get("pretool", True):
        return {}
    name = tool_name or ""
    if name in {"Grep", "grep"} and isinstance(tool_input, dict):
        cap = int(cfg.get("grep_max_count") or 80)
        if tool_input.get("head_limit") is None and tool_input.get("headLimit") is None:
            updated = dict(tool_input)
            updated["head_limit"] = cap
            return {"updated_input": updated, "note": f"grep head_limit={cap}"}

    if name in {"Bash", "bash", "Shell"} and isinstance(tool_input, dict):
        cmd = tool_input.get("command") or ""
        if not isinstance(cmd, str) or "|" in cmd:
            return {}
        if LIST_CMD.search(cmd):
            n = int(cfg.get("ls_max_lines") or 200)
            updated = dict(tool_input)
            updated["command"] = f"({cmd}) | head -n {n}"
            return {"updated_input": updated, "note": f"piped head -n {n}"}
        if RG_CMD.search(cmd) and "--max-count" not in cmd and "-m " not in cmd:
            n = int(cfg.get("grep_max_count") or 80)
            updated = dict(tool_input)
            updated["command"] = f"{cmd} --max-count {n}" if cmd.startswith("rg") or " rg " in f" {cmd}" else cmd
            if updated["command"] != cmd:
                return {"updated_input": updated, "note": f"rg --max-count {n}"}

    lname = name.lower()
    if "chrome" in lname or "playwright" in lname:
        if "screenshot" in lname or "computer" in lname or "browser_batch" in lname:
            return {
                "additionalContext": "[sift] Prefer accessibility/text over another screenshot unless pixels are required."
            }
    return {}
