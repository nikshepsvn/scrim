from __future__ import annotations

import re
from typing import Any

TEST_RE = re.compile(
    r"(npm test|pnpm test|yarn test|pytest|vitest|jest|cargo test|go test|npx tsc|eslint|\blint\b|playwright test)",
    re.I,
)
LOG_RE = re.compile(
    r"(kubectl logs|docker logs|journalctl|\btail\b|.*\.log\b)",
    re.I,
)
SEARCH_RE = re.compile(r"\b(rg|grep|git grep|ag|ack)\b", re.I)
LIST_RE = re.compile(r"\b(ls|find|tree|fd|glob)\b", re.I)


def command_of(tool_input: Any) -> str:
    if isinstance(tool_input, dict):
        for k in ("command", "cmd", "pattern", "query"):
            v = tool_input.get(k)
            if isinstance(v, str) and v:
                return v
    if isinstance(tool_input, str):
        return tool_input
    return ""


def classify(tool_name: str, tool_input: Any) -> str:
    n = (tool_name or "").lower()
    cmd = command_of(tool_input)

    if n in {"read", "readfile", "notebookread"}:
        return "read"
    if n in {"edit", "write", "multiedit", "notebookedit"}:
        return "edit"
    if n in {"grep", "rg"} or (n in {"bash", "shell", "zsh"} and SEARCH_RE.search(cmd)):
        return "search"
    if n in {"glob", "ls"} or (n in {"bash", "shell", "zsh"} and LIST_RE.search(cmd) and not SEARCH_RE.search(cmd)):
        return "file_list"
    if n in {"websearch", "webfetch", "web_search", "web_fetch"}:
        return "web"
    if n.startswith("mcp__") or "mcp" in n:
        return "mcp"
    if n in {"bash", "shell", "zsh"}:
        if TEST_RE.search(cmd):
            return "test_build_lint"
        if LOG_RE.search(cmd):
            return "log"
        return "bash"
    return "other"
