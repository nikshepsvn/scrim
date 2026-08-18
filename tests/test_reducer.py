#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sift.reducer import reduce_text


def test_off():
    assert reduce_text("x" * 20000, {"reducer": "off"}) is None


def test_openrouter_no_key(monkeypatch=None):
    import os

    os.environ.pop("OPENROUTER_API_KEY", None)
    os.environ.pop("SIFT_REDUCER_KEY", None)
    os.environ.pop("SPEND_REDUCER_KEY", None)
    assert (
        reduce_text(
            "x" * 20000,
            {"reducer": "openrouter", "reducer_min_bytes": 8},
        )
        is None
    )


if __name__ == "__main__":
    test_off()
    test_openrouter_no_key()
    print("ok")
