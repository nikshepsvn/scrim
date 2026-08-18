from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import data_dir
from .timeutil import local_day


# session events, not tool calls — excluded from byte rollups
EVENT_KINDS = {"subagent_start", "subagent_stop", "compact", "mb_warned", "retrieve"}


def metrics_path() -> Path:
    return data_dir() / "metrics.jsonl"


def append_metric(row: dict) -> None:
    row = dict(row)
    row.setdefault("ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    # never persist payloads
    for k in ("tool_response", "content", "stdout", "output", "input"):
        row.pop(k, None)
    path = metrics_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def iter_metrics():
    path = metrics_path()
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def prune_metrics(keep_days: int = 90) -> int:
    """Drop rows older than keep_days (local time). Returns rows removed."""
    path = metrics_path()
    if not path.exists():
        return 0
    kept: list[str] = []
    dropped = 0
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).astimezone().date().isoformat()
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                day = local_day(json.loads(line).get("ts"))
            except json.JSONDecodeError:
                dropped += 1
                continue
            if day and day < cutoff:
                dropped += 1
                continue
            kept.append(line)
        if dropped:
            path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    except OSError:
        return 0
    return dropped


def daily_tools(start_day: str) -> dict[str, dict]:
    """Tool bytes in/out bucketed by local day, from start_day onward."""
    acc: dict[str, dict] = defaultdict(lambda: {"in": 0, "out": 0, "n": 0})
    for row in iter_metrics() or []:
        if (row.get("kind") or "") in EVENT_KINDS:
            continue
        day = local_day(row.get("ts"))
        if not day or day < start_day:
            continue
        bi = int(row.get("bytes_in") or 0)
        d = acc[day]
        d["n"] += 1
        d["in"] += bi
        d["out"] += int(row.get("bytes_out") or bi)
    return dict(acc)


def summarize(day: str | None = None, session_id: str | None = None) -> dict:
    """Roll up hook metrics. day is a local YYYY-MM-DD; timestamps are UTC."""
    n = 0
    bytes_in = 0
    bytes_out = 0
    shrunk = 0
    stashes = 0
    swarms = 0
    compactions = 0
    retrievals = 0
    by_tool = defaultdict(lambda: {"n": 0, "in": 0, "out": 0})
    by_kind = defaultdict(lambda: {"n": 0, "in": 0, "out": 0})
    for row in iter_metrics() or []:
        if day and local_day(row.get("ts")) != day:
            continue
        if session_id and row.get("session_id") != session_id:
            continue
        k = row.get("kind") or ""
        if k in EVENT_KINDS:
            if k == "subagent_start":
                swarms += 1
            elif k == "compact":
                compactions += 1
            elif k == "retrieve":
                retrievals += 1
            continue
        n += 1
        bi = int(row.get("bytes_in") or 0)
        bo = int(row.get("bytes_out") or bi)
        bytes_in += bi
        bytes_out += bo
        if row.get("shrunk"):
            shrunk += 1
        if row.get("stash_id"):
            stashes += 1
        t = row.get("tool_name") or "unknown"
        by_tool[t]["n"] += 1
        by_tool[t]["in"] += bi
        by_tool[t]["out"] += bo
        kk = k or "other"
        by_kind[kk]["n"] += 1
        by_kind[kk]["in"] += bi
        by_kind[kk]["out"] += bo
    return {
        "n": n,
        "bytes_in": bytes_in,
        "bytes_out": bytes_out,
        "saved": max(0, bytes_in - bytes_out),
        "shrunk": shrunk,
        "stashes": stashes,
        "swarms": swarms,
        "compactions": compactions,
        "retrievals": retrievals,
        "by_tool": dict(
            sorted(by_tool.items(), key=lambda kv: -kv[1]["in"])[:12]
        ),
        "by_kind": dict(
            sorted(by_kind.items(), key=lambda kv: -kv[1]["in"])[:12]
        ),
    }
