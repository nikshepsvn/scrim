"""Read Claude Code transcripts for usage / shadow cost. No payloads stored."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .prices import cost_usd


def parse_transcript(path: Path, since_prefix: str | None = None) -> dict:
    models: dict[str, dict] = defaultdict(lambda: {
        "turns": 0, "inp": 0, "out": 0, "cr": 0, "cw": 0, "cw1h": 0, "cost": 0.0
    })
    first_ts = last_ts = None
    session_id = cwd = None
    if not path.exists():
        return _empty()
    try:
        fh = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return _empty()
    with fh:
        for line in fh:
            if not line.startswith("{"):
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = o.get("sessionId") or o.get("session_id")
            if sid:
                session_id = sid
            if o.get("cwd"):
                cwd = o["cwd"]
            ts = o.get("timestamp")
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            if since_prefix and ts and not str(ts).startswith(since_prefix):
                continue
            if o.get("type") != "assistant":
                continue
            msg = o.get("message") or {}
            if not isinstance(msg, dict):
                continue
            model = msg.get("model") or "unknown"
            if model == "<synthetic>":
                continue
            u = msg.get("usage") or {}
            if not u:
                continue
            cc = u.get("cache_creation") or {}
            cw1h = cc.get("ephemeral_1h_input_tokens") if isinstance(cc, dict) else 0
            inp = u.get("input_tokens") or 0
            out = u.get("output_tokens") or 0
            cr = u.get("cache_read_input_tokens") or 0
            cw = u.get("cache_creation_input_tokens") or 0
            c = cost_usd(model, inp, out, cr, cw, cw1h or 0)
            m = models[model]
            m["turns"] += 1
            m["inp"] += inp
            m["out"] += out
            m["cr"] += cr
            m["cw"] += cw
            m["cw1h"] += cw1h or 0
            m["cost"] += c
    return _rollup(models, session_id, cwd, first_ts, last_ts)


def parse_projects(since_prefix: str | None = None) -> dict:
    root = Path.home() / ".claude" / "projects"
    models: dict[str, dict] = defaultdict(lambda: {
        "turns": 0, "inp": 0, "out": 0, "cr": 0, "cw": 0, "cw1h": 0, "cost": 0.0
    })
    if not root.exists():
        return _empty()
    for path in root.rglob("*.jsonl"):
        part = parse_transcript(path, since_prefix=since_prefix)
        if not (part.get("total") or {}).get("turns"):
            continue
        for model, m in (part.get("models") or {}).items():
            acc = models[model]
            for k in ("turns", "inp", "out", "cr", "cw", "cw1h", "cost"):
                acc[k] += m[k]
    return _rollup(models, None, None, None, None)


def _empty() -> dict:
    return _rollup({}, None, None, None, None)


def _rollup(models, session_id, cwd, first_ts, last_ts) -> dict:
    tot = {"turns": 0, "inp": 0, "out": 0, "cr": 0, "cw": 0, "cw1h": 0, "cost": 0.0}
    clean = {}
    for model, m in models.items():
        clean[model] = dict(m)
        for k in tot:
            tot[k] += m[k]
    tokens = tot["inp"] + tot["out"] + tot["cr"] + tot["cw"]
    return {
        "session_id": session_id,
        "cwd": cwd,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "models": clean,
        "total": tot,
        "tokens": tokens,
        "cache_read_share": (tot["cr"] / tokens) if tokens else 0.0,
    }
