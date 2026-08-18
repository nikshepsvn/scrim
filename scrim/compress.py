"""Agent-readable compressors. gzip/zstd do not reduce tokens — the model
must see text — so these rewrite structure, they do not pack bytes."""

from __future__ import annotations

import json
import re
from typing import Any

HTML_RE = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>|<[^>]+>")
WS_RE = re.compile(r"[ \t]+\n")


def compress_text(text: str) -> str | None:
    """Best structural rewrite, or None if it doesn't help."""
    s = text.strip()
    if len(s) < 800:
        return None
    if s[:1] in "{[":
        out = _compress_json(s)
        if out and len(out) < len(text) * 0.85:
            return out
    if "<html" in s[:2000].lower() or s[:200].lstrip().lower().startswith("<!"):
        out = _compress_html(s)
        if out and len(out) < len(text) * 0.7:
            return out
    return None


def _compress_json(text: str) -> str | None:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return _compress_ndjson(text)
    slim = _summarize(obj, 0)
    return "[scrim:json]\n" + json.dumps(slim, indent=2, default=str)


def _compress_ndjson(text: str) -> str | None:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            return None
    if len(rows) < 8:
        return None
    slim = _summarize(rows, 0)
    return "[scrim:ndjson]\n" + json.dumps(slim, indent=2, default=str)


def _summarize(obj: Any, depth: int) -> Any:
    if isinstance(obj, list):
        if len(obj) <= 3 or depth > 4:
            return [_summarize(x, depth + 1) for x in obj[:3]]
        return {
            "_n": len(obj),
            "head": [_summarize(x, depth + 1) for x in obj[:2]],
            "tail": [_summarize(obj[-1], depth + 1)],
        }
    if isinstance(obj, dict):
        if depth > 5:
            return {"_keys": list(obj)[:24], "_n": len(obj)}
        items = list(obj.items())
        if len(items) > 40:
            head = {k: _summarize(v, depth + 1) for k, v in items[:20]}
            head["_omitted_keys"] = len(items) - 20
            return head
        return {k: _summarize(v, depth + 1) for k, v in items}
    if isinstance(obj, str) and len(obj) > 400:
        return obj[:240] + f"…({len(obj)}c)"
    return obj


def _compress_html(text: str) -> str:
    no = HTML_RE.sub(" ", text)
    no = WS_RE.sub("\n", no)
    no = re.sub(r"\n{3,}", "\n\n", no)
    no = re.sub(r"[ \t]{2,}", " ", no).strip()
    if len(no) > 12000:
        no = no[:12000] + "\n[scrim:html] truncated"
    return "[scrim:html]\n" + no
