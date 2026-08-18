"""Local omitted-output store. Fail-open. Never uploaded."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import data_dir, load_config


def blobs_dir() -> Path:
    p = data_dir() / "blobs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def index_path() -> Path:
    return data_dir() / "stashes.jsonl"


def _new_id(tool_use_id: str | None, text: str) -> str:
    base = "".join(c for c in (tool_use_id or "")[-12:] if c.isalnum())[:16]
    if base:
        return base
    # no tool_use_id: time alone collides within a second, so mix in content
    h = hashlib.sha1(text[:4096].encode("utf-8", "replace")).hexdigest()[:6]
    return f"{int(time.time()):x}{h}"


def put(text: str, *, tool_use_id: str | None = None, kind: str = "", tool_name: str = "") -> str | None:
    if not text or len(text) < 400:
        return None
    try:
        bdir = blobs_dir()
    except OSError:
        return None
    bid = _new_id(tool_use_id, text)
    path = bdir / f"{bid}.txt"
    for n in range(2, 8):
        try:
            if not path.exists() or path.stat().st_size == len(text):
                break
        except OSError:
            break
        bid = f"{_new_id(tool_use_id, text)}{n}"
        path = bdir / f"{bid}.txt"
    try:
        path.write_text(text, encoding="utf-8")
        meta = {
            "id": bid,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bytes": len(text),
            "kind": kind,
            "tool_name": tool_name,
        }
        with index_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(meta) + "\n")
    except OSError:
        return None
    gc()
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


def entries(limit: int = 20) -> list[dict]:
    """Most-recent-first index rows, flagged live/expired."""
    idx = index_path()
    if not idx.exists():
        return []
    rows: list[dict] = []
    try:
        for line in idx.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("id"):
                rows.append(row)
    except OSError:
        return []
    by_id: dict[str, dict] = {}
    for row in rows:
        by_id[row["id"]] = row  # re-puts of one id: newest meta wins
    try:
        live = {p.stem for p in blobs_dir().glob("*.txt")}
    except OSError:
        live = set()
    out = sorted(by_id.values(), key=lambda r: str(r.get("ts") or ""), reverse=True)[:limit]
    for row in out:
        row["live"] = row["id"] in live
    return out


def gc() -> None:
    ttl_days = 7
    cap_bytes = 512 * 1024 * 1024
    try:
        cfg = load_config()
        ttl_days = int(cfg.get("stash_ttl_days") or 7)
        cap_bytes = int(cfg.get("stash_max_mb") or 512) * 1024 * 1024
    except Exception:
        pass
    try:
        bdir = blobs_dir()
    except OSError:
        return
    cutoff = time.time() - ttl_days * 86400
    files = []
    for p in bdir.glob("*.txt"):
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
    while total > cap_bytes and files:
        _, sz, p = files.pop(0)
        try:
            p.unlink()
            total -= sz
        except OSError:
            break
    _compact_index()


def _compact_index() -> None:
    """The index only grows; rewrite it to live blobs once it gets fat."""
    idx = index_path()
    try:
        if not idx.exists() or idx.stat().st_size < 512 * 1024:
            return
        live = {p.stem for p in blobs_dir().glob("*.txt")}
        kept = []
        for line in idx.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                if json.loads(line).get("id") in live:
                    kept.append(line)
            except json.JSONDecodeError:
                continue
        idx.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    except OSError:
        pass
