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


def _script_of(raw: Any) -> tuple[str | None, int | None]:
    """The rewritable shell script inside `command`, plus its argv index.

    Codex sends argv like ["bash", "-lc", "<script>"]; only that script slot
    is safe to rewrite — bare argv with no shell must be left alone."""
    if isinstance(raw, str):
        return (raw, None) if raw else (None, None)
    if isinstance(raw, list):
        for i, a in enumerate(raw[:-1]):
            if a in {"-c", "-lc", "-cl"} and isinstance(raw[i + 1], str):
                return raw[i + 1], i + 1
    return None, None


def _rebuild(tool_input: dict, raw: Any, script_idx: int | None, new_cmd: str) -> dict:
    updated = dict(tool_input)
    if script_idx is None:
        updated["command"] = new_cmd
    else:
        argv = list(raw)
        argv[script_idx] = new_cmd
        updated["command"] = argv
    return updated


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

    if name in {"Bash", "bash", "Shell", "shell"} and isinstance(tool_input, dict):
        raw = tool_input.get("command")
        cmd, script_idx = _script_of(raw)
        if cmd is None or "|" in cmd or ">" in cmd:
            return {}
        segs = segments(cmd)
        if any(LIST_HEAD_RE.match(s) for s in segs):
            if FIND_MUTATING_RE.search(cmd):
                return {}
            n = int(cfg.get("ls_max_lines") or 200)
            updated = _rebuild(tool_input, raw, script_idx, f"({cmd}) | head -n {n}")
            return {"updated_input": updated, "note": f"piped head -n {n}"}
        if segs and RG_HEAD_RE.match(segs[-1]) and not RG_BOUNDED_RE.search(cmd):
            n = int(cfg.get("grep_max_count") or 80)
            caps = f"--max-count {n}"
            # one hit in minified JS can be a 200 KB line; --max-count can't help
            cols = int(cfg.get("rg_max_columns") or 0)
            if cols and "--max-columns" not in cmd:
                caps += f" --max-columns {cols}"
            updated = _rebuild(tool_input, raw, script_idx, f"{cmd} {caps}")
            return {"updated_input": updated, "note": f"rg {caps}"}

    lname = name.lower()
    if "chrome" in lname or "playwright" in lname:
        if "screenshot" in lname or "computer" in lname or "browser_batch" in lname:
            return {
                "additionalContext": "[scrim] Prefer accessibility/text over another screenshot unless pixels are required."
            }
    return {}
