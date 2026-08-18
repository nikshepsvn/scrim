#!/usr/bin/env python3
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["TZ"] = "America/Los_Angeles"
time.tzset()

_TMP = tempfile.TemporaryDirectory(prefix="scrim-test-")
os.environ["SCRIM_DATA_DIR"] = _TMP.name

from scrim.metrics import append_metric, prune_metrics, summarize


def _seed():
    append_metric({
        "session_id": "sA", "tool_name": "Bash", "kind": "test_build_lint",
        "bytes_in": 1000, "bytes_out": 100, "shrunk": True,
        "stash_id": "abc", "ts": "2026-08-18T20:00:00+00:00",
    })
    append_metric({
        "session_id": "sB", "tool_name": "Grep", "kind": "search",
        "bytes_in": 500, "bytes_out": 500, "shrunk": False,
        "ts": "2026-08-19T02:00:00+00:00",  # still Aug 18 in LA
    })
    append_metric({
        "session_id": "sA", "kind": "subagent_start", "tool_name": "explore",
        "bytes_in": 0, "bytes_out": 0, "shrunk": False,
        "ts": "2026-08-18T20:00:01+00:00",
    })
    append_metric({
        "session_id": "sA", "tool_name": "Bash", "kind": "bash",
        "bytes_in": 300, "bytes_out": 300, "shrunk": False,
        "ts": "2026-08-19T20:00:00+00:00",  # Aug 19 in LA
    })


def test_summarize_all():
    _seed()
    s = summarize()
    assert s["n"] == 3
    assert s["swarms"] == 1
    assert s["stashes"] == 1
    assert s["bytes_in"] == 1800
    assert s["saved"] == 900


def test_day_filter_local():
    s = summarize(day="2026-08-18")
    assert s["n"] == 2  # the 02:00Z row counts as local Aug 18
    s19 = summarize(day="2026-08-19")
    assert s19["n"] == 1


def test_session_filter():
    s = summarize(session_id="sA")
    assert s["n"] == 2
    assert s["bytes_in"] == 1300


def test_by_kind():
    s = summarize()
    assert s["by_kind"]["test_build_lint"]["in"] == 1000
    assert s["by_kind"]["search"]["n"] == 1
    assert "subagent_start" not in s["by_kind"]


def test_prune():
    append_metric({
        "session_id": "old", "tool_name": "Bash", "kind": "bash",
        "bytes_in": 1, "bytes_out": 1, "shrunk": False,
        "ts": "2020-01-01T00:00:00+00:00",
    })
    before = summarize()["n"]
    dropped = prune_metrics(keep_days=30)
    assert dropped == 1
    assert summarize()["n"] == before - 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("all ok")
