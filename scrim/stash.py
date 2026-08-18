"""Local omitted-output store. Fail-open. Never uploaded."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import data_dir


def blobs_dir() -> Path:
    p = data_dir() / "blobs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def put(text: str, *, tool_use_id: str | None = None, kind: str = "", tool_name: str = "") -> str | None:
    if not text or len(text) < 400:
        return None
    bid = (tool_use_id or "")[-12:] or f"{int(time.time()):x}"
    bid = "".join(c for c in bid if c.isalnum())[:16] or f"{int(time.time()):x}"
    path = blobs_dir() / f"{bid}.txt"
    try:
        path.write_text(text, encoding="utf-8")
        meta = {
            "id": bid,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bytes": len(text),
            "kind": kind,
            "tool_name": tool_name,
        }
        with (data_dir() / "stashes.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(meta) + "\n")
    except OSError:
        return None
    _gc()
    return bid


def get(bid: str, start: int | None = None, end: int | None = None) -> str | None:
    path = blobs_dir() / f"{bid}.txt"
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if start is None and end is None:
        return text
    lines = text.splitlines()
    lo = max(1, start or 1)
    hi = min(len(lines), end or len(lines))
    body = "\n".join(lines[lo - 1 : hi])
    return f"[scrim] {bid} lines {lo}-{hi} of {len(lines)}\n{body}"


def _gc() -> None:
    cfg_ttl = 7
    cfg_cap = 512 * 1024 * 1024
    try:
        from .config import load_config

        cfg = load_config()
        cfg_ttl = int(cfg.get("stash_ttl_days") or 7)
        cfg_cap = int(cfg.get("stash_max_mb") or 512) * 1024 * 1024
    except Exception:
        pass
    cutoff = time.time() - cfg_ttl * 86400
    files = []
    for p in blobs_dir().glob("*.txt"):
        try:
            st = p.stat()
        except OSError:
            continue
        if st.st_mtime < cutoff:
            try:
                p.unlink()
            except OSError:
                pass
            continue
        files.append((st.st_mtime, st.st_size, p))
    files.sort()  # oldest first
    total = sum(sz for _, sz, _ in files)
    while total > cfg_cap and files:
        _, sz, p = files.pop(0)
        try:
            p.unlink()
            total -= sz
        except OSError:
            break
