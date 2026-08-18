"""PreToolUse: stop fat dumps before they exist. Fail-open.

Rewrites must never change what a command *does* — only how much it prints.
Anything piped, redirected, or mutating is left alone.
"""

from __future__ import annotations

import re
from typing import Any

from .classify import segments

# recursive ls (flags in any order), find, tree — at command position only,
# so `grep find src` or a "find me" string argument is not touched
LIST_HEAD_RE = re.compile(r"^(ls\s+(?:-\S+\s+)*-\w*R|find(?:\s|$)|tree(?:\s|$))", re.I)
# find actions that mutate or have side effects: capping output via head can
# SIGPIPE-kill the command mid-run
FIND_MUTATING_RE = re.compile(r"\s-(exec|execdir|ok|okdir|delete|fprint\w*|fls)\b")
RG_HEAD_RE = re.compile(r"^rg\s")
RG_BOUNDED_RE = re.compile(
    r"(--max-count|\s-m\s|--count\b|\s-c\b|--files-with-matches\b|\s-l\b|--files\b|--json\b|--stats\b)"
)


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
        if not isinstance(cmd, str) or "|" in cmd or ">" in cmd:
            return {}
        segs = segments(cmd)
        if any(LIST_HEAD_RE.match(s) for s in segs):
            if FIND_MUTATING_RE.search(cmd):
                return {}
            n = int(cfg.get("ls_max_lines") or 200)
            updated = dict(tool_input)
            updated["command"] = f"({cmd}) | head -n {n}"
            return {"updated_input": updated, "note": f"piped head -n {n}"}
        if segs and RG_HEAD_RE.match(segs[-1]) and not RG_BOUNDED_RE.search(cmd):
            n = int(cfg.get("grep_max_count") or 80)
            updated = dict(tool_input)
            updated["command"] = f"{cmd} --max-count {n}"
            return {"updated_input": updated, "note": f"rg --max-count {n}"}

    lname = name.lower()
    if "chrome" in lname or "playwright" in lname:
        if "screenshot" in lname or "computer" in lname or "browser_batch" in lname:
            return {
                "additionalContext": "[scrim] Prefer accessibility/text over another screenshot unless pixels are required."
            }
    return {}
