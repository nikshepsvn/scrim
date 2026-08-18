#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# pin the timezone so local-day assertions are deterministic
os.environ["TZ"] = "America/Los_Angeles"
time.tzset()

from scrim.observe import parse_transcript
from scrim.prices import price_for
from scrim.timeutil import local_day


def _row(ts: str, model: str = "claude-opus-5", mid: str | None = None, rid: str | None = None) -> dict:
    rec = {
        "type": "assistant",
        "timestamp": ts,
        "sessionId": "s1",
        "cwd": "/tmp",
        "message": {
            "model": model,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "cache_read_input_tokens": 1000,
                "cache_creation_input_tokens": 50,
            },
        },
    }
    if mid:
        rec["message"]["id"] = mid
    if rid:
        rec["requestId"] = rid
    return rec


def _write(rows: list[dict]) -> Path:
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
        return Path(f.name)


def test_parse_usage():
    path = _write([_row("2026-08-18T00:00:00Z")])
    u = parse_transcript(path)
    path.unlink()
    assert u["total"]["turns"] == 1
    assert u["total"]["cr"] == 1000
    assert u["total"]["cost"] > 0
    assert u["session_id"] == "s1"


def test_day_filter_is_local():
    # 02:00 UTC on Aug 19 is still Aug 18 evening in Los Angeles
    assert local_day("2026-08-19T02:00:00Z") == "2026-08-18"
    path = _write([
        _row("2026-08-19T02:00:00Z"),   # local Aug 18
        _row("2026-08-19T20:00:00Z"),   # local Aug 19
    ])
    u = parse_transcript(path, day="2026-08-18")
    path.unlink()
    assert u["total"]["turns"] == 1


def test_retry_rows_deduped():
    rows = [
        _row("2026-08-18T00:00:00Z", mid="msg_1", rid="req_1"),
        _row("2026-08-18T00:00:01Z", mid="msg_1", rid="req_1"),  # API retry
        _row("2026-08-18T00:00:02Z", mid="msg_2", rid="req_2"),
    ]
    path = _write(rows)
    u = parse_transcript(path)
    path.unlink()
    assert u["total"]["turns"] == 2


def test_synthetic_skipped():
    path = _write([_row("2026-08-18T00:00:00Z", model="<synthetic>")])
    u = parse_transcript(path)
    path.unlink()
    assert u["total"]["turns"] == 0


def test_list_prices():
    assert price_for("claude-opus-5") == (5.0, 25.0)
    assert price_for("claude-sonnet-5") == (3.0, 15.0)
    assert price_for("claude-haiku-4-5-20251001") == (1.0, 5.0)
    # Fable is priced above Opus tier — undercounting it hides real burn
    assert price_for("claude-fable-5") == (10.0, 50.0)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("all ok")
