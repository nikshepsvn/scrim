from __future__ import annotations

import re
from typing import Any

TEST_RE = re.compile(
    r"(npm test|pnpm test|yarn test|bun test|deno test|make test|pytest|tox\b|vitest|jest"
    r"|cargo test|cargo clippy|go test|go vet|npx tsc|\btsc\b|eslint|\blint\b|ruff\b"
    r"|mypy\b|pyright\b|playwright test|rspec\b|phpunit\b|mvn test|gradle\w* test)",
    re.I,
)
LOG_RE = re.compile(
    r"(kubectl logs|docker logs|compose logs|journalctl|\btail\b|\.log\b)",
    re.I,
)
# match at command position (segment start), not anywhere in a string argument
SEGMENT_RE = re.compile(r"\|\||&&|[|;&]")
SEARCH_HEAD_RE = re.compile(r"^(rg|grep|egrep|fgrep|ag|ack)\b|^git\s+grep\b", re.I)
LIST_HEAD_RE = re.compile(r"^(ls|find|tree|fd|eza|exa)\b|^git\s+ls-files\b", re.I)
# our own retrieval: thinning `scrim get` would re-shrink the blob the
# agent explicitly asked to recover, and re-stash it under a new id
SCRIM_GET_RE = re.compile(r"\bscrim(\.py)?\s+get\b")


def segments(cmd: str) -> list[str]:
    return [s.strip() for s in SEGMENT_RE.split(cmd) if s.strip()]


def argv_to_command(argv: list) -> str:
    """Codex sends shell commands as argv, e.g. ["bash", "-lc", "pytest -q"].
    The element after -c/-lc is the actual script; else join what's stringy."""
    parts = [a for a in argv if isinstance(a, str)]
    for i, a in enumerate(parts[:-1]):
        if a in {"-c", "-lc", "-cl"} or (a.startswith("-") and a.endswith("c") and len(a) <= 4):
            return parts[i + 1]
    return " ".join(parts)


def command_of(tool_input: Any) -> str:
    if isinstance(tool_input, dict):
        for k in ("command", "cmd", "pattern", "query", "input"):
            v = tool_input.get(k)
            if isinstance(v, str) and v:
                return v
            if isinstance(v, list) and v:
                return argv_to_command(v)
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
    if n in {"grep", "rg"}:
        return "search"
    if n in {"glob", "ls"}:
        return "file_list"
    if n in {"websearch", "webfetch", "web_search", "web_fetch"}:
        return "web"
    if n.startswith("mcp__") or "mcp" in n:
        return "mcp"
    # "exec" is Codex code-mode: JS in tool_input["input"] whose embedded
    # commands still name the runner, so the same command regexes apply
    if n in {"bash", "shell", "zsh", "exec"}:
        if SCRIM_GET_RE.search(cmd):
            return "other"
        # test runners first: `pytest && ls` should get FAIL-line thinning,
        # not head/tail that can drop the failure
        if TEST_RE.search(cmd):
            return "test_build_lint"
        segs = segments(cmd)
        if any(SEARCH_HEAD_RE.match(s) for s in segs):
            return "search"
        if any(LIST_HEAD_RE.match(s) for s in segs):
            return "file_list"
        if LOG_RE.search(cmd):
            return "log"
        return "bash"
    return "other"
