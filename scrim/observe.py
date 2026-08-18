"""Read Claude Code transcripts for usage / shadow cost. No payloads stored."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from .prices import cost_usd
from .timeutil import local_day


def parse_transcript(path: Path, day: str | None = None, seen: set | None = None) -> dict:
    """Sum usage rows. day is a local YYYY-MM-DD filter; seen dedups
    API retries (same message id + requestId) across files."""
    models: dict[str, dict] = defaultdict(lambda: {
        "turns": 0, "inp": 0, "out": 0, "cr": 0, "cw": 0, "cw1h": 0, "cost": 0.0
    })
    first_ts = last_ts = None
    session_id = cwd = None
    if seen is None:
        seen = set()
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
            if day and ts and local_day(ts) != day:
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
            mid = msg.get("id")
            rid = o.get("requestId") or o.get("request_id")
            if mid and rid:
                if (mid, rid) in seen:
                    continue
                seen.add((mid, rid))
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


def _day_start_epoch(day: str) -> float | None:
    """Epoch of local midnight for a YYYY-MM-DD, minus an hour of slack."""
    try:
        start = datetime.fromisoformat(day)
    except ValueError:
        return None
    return time.mktime(start.timetuple()) - 3600


def parse_projects(day: str | None = None) -> dict:
    root = Path.home() / ".claude" / "projects"
    models: dict[str, dict] = defaultdict(lambda: {
        "turns": 0, "inp": 0, "out": 0, "cr": 0, "cw": 0, "cw1h": 0, "cost": 0.0
    })
    if not root.exists():
        return _empty()
    # a transcript not touched since before the day cannot contain its rows;
    # skipping by mtime turns a ~2000-file scan into a handful
    min_mtime = _day_start_epoch(day) if day else None
    seen: set = set()
    for path in root.rglob("*.jsonl"):
        if min_mtime is not None:
            try:
                if path.stat().st_mtime < min_mtime:
                    continue
            except OSError:
                continue
        part = parse_transcript(path, day=day, seen=seen)
        if not (part.get("total") or {}).get("turns"):
            continue
        for model, m in (part.get("models") or {}).items():
            acc = models[model]
            for k in ("turns", "inp", "out", "cr", "cw", "cw1h", "cost"):
                acc[k] += m[k]
    return _rollup(models, None, None, None, None)


def parse_codex_sessions(day: str | None = None, root: Path | None = None) -> dict:
    """Usage from Codex CLI rollout files (~/.codex/sessions/YYYY/MM/DD).

    The model rides on turn_context; each token_count event with an `info`
    block is one API request whose last_token_usage is that request's bill.
    cached_input_tokens is a subset of input_tokens, so it maps to cache-read
    and the remainder to fresh input. Codex has no cache-write premium."""
    root = root or Path.home() / ".codex" / "sessions"
    models: dict[str, dict] = defaultdict(lambda: {
        "turns": 0, "inp": 0, "out": 0, "cr": 0, "cw": 0, "cw1h": 0, "cost": 0.0
    })
    if not root.exists():
        return _empty()
    min_mtime = _day_start_epoch(day) if day else None
    for path in root.rglob("*.jsonl"):
        if min_mtime is not None:
            try:
                if path.stat().st_mtime < min_mtime:
                    continue
            except OSError:
                continue
        try:
            fh = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        model = "unknown"
        with fh:
            for line in fh:
                if not line.startswith("{"):
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                p = o.get("payload") or {}
                if o.get("type") == "turn_context" and p.get("model"):
                    model = p["model"]
                    continue
                if p.get("type") != "token_count":
                    continue
                info = p.get("info") or {}
                last = info.get("last_token_usage") or {}
                if not last:
                    continue
                if day and local_day(o.get("timestamp")) != day:
                    continue
                inp_total = last.get("input_tokens") or 0
                cr = last.get("cached_input_tokens") or 0
                inp = max(0, inp_total - cr)
                out = last.get("output_tokens") or 0
                m = models[model]
                m["turns"] += 1
                m["inp"] += inp
                m["out"] += out
                m["cr"] += cr
                m["cost"] += cost_usd(model, inp, out, cr, 0, 0)
    return _rollup(models, None, None, None, None)


def window_start(days: int) -> str:
    """First local day of a trailing window that ends today."""
    return (date.today() - timedelta(days=max(1, days) - 1)).isoformat()


def daily_usage(days: int = 7, root: Path | None = None) -> dict[str, dict]:
    """Claude transcript cost/turns bucketed by local day, one pass."""
    start = window_start(days)
    root = root or Path.home() / ".claude" / "projects"
    acc: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "turns": 0})
    if not root.exists():
        return {}
    min_mtime = _day_start_epoch(start)
    seen: set = set()
    for path in root.rglob("*.jsonl"):
        try:
            if min_mtime is not None and path.stat().st_mtime < min_mtime:
                continue
            fh = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if not line.startswith("{"):
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if o.get("type") != "assistant":
                    continue
                day = local_day(o.get("timestamp"))
                if not day or day < start:
                    continue
                msg = o.get("message") or {}
                if not isinstance(msg, dict) or msg.get("model") == "<synthetic>":
                    continue
                u = msg.get("usage") or {}
                if not u:
                    continue
                mid, rid = msg.get("id"), o.get("requestId") or o.get("request_id")
                if mid and rid:
                    if (mid, rid) in seen:
                        continue
                    seen.add((mid, rid))
                cc = u.get("cache_creation") or {}
                cw1h = cc.get("ephemeral_1h_input_tokens") if isinstance(cc, dict) else 0
                d = acc[day]
                d["turns"] += 1
                d["cost"] += cost_usd(
                    msg.get("model") or "unknown",
                    u.get("input_tokens") or 0,
                    u.get("output_tokens") or 0,
                    u.get("cache_read_input_tokens") or 0,
                    u.get("cache_creation_input_tokens") or 0,
                    cw1h or 0,
                )
    return dict(acc)


def daily_codex(days: int = 7, root: Path | None = None) -> dict[str, dict]:
    """Codex rollout cost/requests bucketed by local day."""
    start = window_start(days)
    root = root or Path.home() / ".codex" / "sessions"
    acc: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "turns": 0})
    if not root.exists():
        return {}
    min_mtime = _day_start_epoch(start)
    for path in root.rglob("*.jsonl"):
        try:
            if min_mtime is not None and path.stat().st_mtime < min_mtime:
                continue
            fh = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        model = "unknown"
        with fh:
            for line in fh:
                if not line.startswith("{"):
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                p = o.get("payload") or {}
                if o.get("type") == "turn_context" and p.get("model"):
                    model = p["model"]
                    continue
                if p.get("type") != "token_count":
                    continue
                last = (p.get("info") or {}).get("last_token_usage") or {}
                if not last:
                    continue
                day = local_day(o.get("timestamp"))
                if not day or day < start:
                    continue
                cr = last.get("cached_input_tokens") or 0
                inp = max(0, (last.get("input_tokens") or 0) - cr)
                d = acc[day]
                d["turns"] += 1
                d["cost"] += cost_usd(model, inp, last.get("output_tokens") or 0, cr, 0, 0)
    return dict(acc)


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
