"""Optional cheap-model reducer. Off by default. Fail-open. Needs ANTHROPIC_API_KEY."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .config import data_dir

PROMPT = """Extract evidence from this coding-agent tool output.
Keep: failures, errors, stack traces, file:line hits, unique log templates with counts, exit codes.
Drop: passing tests, repeated info lines, HTML chrome, duplicate rows.
Preserve exact error strings, paths, and numbers. No prose, no markdown fences.
If nothing important, return the first 25 and last 15 lines labeled as such.
"""


def cache_path(digest: str) -> Path:
    d = data_dir() / "reducer-cache"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{digest}.txt"


def reduce_with_haiku(text: str, cfg: dict) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("SPEND_REDUCER_KEY")
    if not key:
        return None
    lo = int(cfg.get("reducer_min_bytes") or 8000)
    hi = int(cfg.get("reducer_max_bytes") or 120000)
    if len(text) < lo:
        return None
    snippet = text[:hi]
    digest = hashlib.sha256(snippet.encode("utf-8", "replace")).hexdigest()[:24]
    cached = cache_path(digest)
    if cached.exists():
        out = cached.read_text(encoding="utf-8", errors="replace")
        return out or None

    body = {
        "model": cfg.get("reducer_model") or "claude-haiku-4-5-20251001",
        "max_tokens": 2048,
        "messages": [
            {
                "role": "user",
                "content": PROMPT + "\n\n---\n" + snippet,
            }
        ],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=float(cfg.get("reducer_timeout_sec") or 4)) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    parts = []
    for block in payload.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    out = "\n".join(parts).strip()
    if not out or len(out) >= len(text) * 0.95:
        return None
    out = "[spend:haiku]\n" + out
    try:
        cached.write_text(out, encoding="utf-8")
    except OSError:
        pass
    return out
