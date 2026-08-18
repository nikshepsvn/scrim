"""Optional model reducer. Off by default. Fail-open.

Backends:
  haiku       Anthropic Messages API (ANTHROPIC_API_KEY)
  openrouter  OpenRouter chat completions (OPENROUTER_API_KEY)
"""

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

DEFAULT_OPENROUTER_MODEL = "inception/mercury-2"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


def _message_text(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict) and isinstance(b.get("text"), str):
                parts.append(b["text"])
        out = "\n".join(parts).strip()
        if out:
            return out
    return ""


def cache_path(digest: str) -> Path:
    d = data_dir() / "reducer-cache"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{digest}.txt"


def reduce_text(text: str, cfg: dict) -> str | None:
    backend = (cfg.get("reducer") or "off").lower()
    if backend in {"off", "false", "0", ""}:
        return None
    lo = int(cfg.get("reducer_min_bytes") or 8000)
    hi = int(cfg.get("reducer_max_bytes") or 120000)
    if len(text) < lo:
        return None
    snippet = text[:hi]

    if backend in {"openrouter", "or"}:
        model = cfg.get("reducer_model") or DEFAULT_OPENROUTER_MODEL
        # ignore leftover Anthropic default if they flipped backend only
        if not str(model).count("/"):
            model = DEFAULT_OPENROUTER_MODEL
        raw = _openrouter(snippet, model, cfg)
        tag = "openrouter"
    elif backend in {"haiku", "anthropic"}:
        model = cfg.get("reducer_model") or DEFAULT_ANTHROPIC_MODEL
        raw = _anthropic(snippet, model, cfg)
        tag = "haiku"
    else:
        return None

    if not raw or len(raw) >= len(text) * 0.95:
        return None
    return f"[sift:{tag}:{model}]\n" + raw


def _cached(snippet: str, backend: str, model: str) -> tuple[str, Path]:
    digest = hashlib.sha256(f"{backend}\n{model}\n{snippet}".encode("utf-8", "replace")).hexdigest()[:24]
    return digest, cache_path(digest)


def _read_cache(path: Path) -> str | None:
    if path.exists():
        out = path.read_text(encoding="utf-8", errors="replace").strip()
        return out or None
    return None


def _write_cache(path: Path, text: str) -> None:
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        pass


def _openrouter(snippet: str, model: str, cfg: dict) -> str | None:
    key = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("SIFT_REDUCER_KEY")
        or os.environ.get("SPEND_REDUCER_KEY")
        or (cfg.get("reducer_api_key") or "")
    )
    if not key:
        return None
    _, cached = _cached(snippet, "openrouter", model)
    hit = _read_cache(cached)
    if hit:
        return hit
    body = {
        "model": model,
        "max_tokens": int(cfg.get("reducer_max_tokens") or 4096),
        "temperature": 0,
        "messages": [{"role": "user", "content": PROMPT + "\n\n---\n" + snippet}],
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {key}",
            "http-referer": "https://github.com/nikshepsvn/sift",
            "x-title": "sift",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=float(cfg.get("reducer_timeout_sec") or 20)) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    choices = payload.get("choices") or []
    if not choices:
        return None
    msg = (choices[0] or {}).get("message") or {}
    out = _message_text(msg)
    if not out:
        return None
    _write_cache(cached, out)
    return out


def _anthropic(snippet: str, model: str, cfg: dict) -> str | None:
    key = (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("SIFT_REDUCER_KEY")
        or os.environ.get("SPEND_REDUCER_KEY")
        or (cfg.get("reducer_api_key") or "")
    )
    if not key:
        return None
    _, cached = _cached(snippet, "anthropic", model)
    hit = _read_cache(cached)
    if hit:
        return hit
    body = {
        "model": model,
        "max_tokens": int(cfg.get("reducer_max_tokens") or 4096),
        "messages": [{"role": "user", "content": PROMPT + "\n\n---\n" + snippet}],
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
        with urllib.request.urlopen(req, timeout=float(cfg.get("reducer_timeout_sec") or 20)) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    parts = []
    for block in payload.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    out = "\n".join(parts).strip()
    if not out:
        return None
    _write_cache(cached, out)
    return out


# back-compat name used in earlier hook wiring
def reduce_with_haiku(text: str, cfg: dict) -> str | None:
    return reduce_text(text, cfg)
