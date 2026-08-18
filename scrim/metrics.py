from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .config import data_dir


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


def summarize(since_prefix: str | None = None) -> dict:
    n = 0
    bytes_in = 0
    bytes_out = 0
    shrunk = 0
    swarms = 0
    by_tool = defaultdict(lambda: {"n": 0, "in": 0, "out": 0})
    for row in iter_metrics() or []:
        ts = row.get("ts") or ""
        if since_prefix and not ts.startswith(since_prefix):
            continue
        k = row.get("kind") or ""
        if k in {"subagent_start", "subagent_stop"}:
            if k == "subagent_start":
                swarms += 1
            continue
        n += 1
        bi = int(row.get("bytes_in") or 0)
        bo = int(row.get("bytes_out") or bi)
        bytes_in += bi
        bytes_out += bo
        if row.get("shrunk"):
            shrunk += 1
        t = row.get("tool_name") or "unknown"
        by_tool[t]["n"] += 1
        by_tool[t]["in"] += bi
        by_tool[t]["out"] += bo
    return {
        "n": n,
        "bytes_in": bytes_in,
        "bytes_out": bytes_out,
        "saved": max(0, bytes_in - bytes_out),
        "shrunk": shrunk,
        "swarms": swarms,
        "by_tool": dict(
            sorted(by_tool.items(), key=lambda kv: -kv[1]["in"])[:12]
        ),
    }
