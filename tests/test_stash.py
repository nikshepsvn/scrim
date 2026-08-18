#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sift.stash import get, put


def test_roundtrip():
    text = "line1\nline2\nline3\n" + ("x" * 500)
    bid = put(text, tool_use_id="abc123tooluse", kind="bash", tool_name="Bash")
    assert bid
    got = get(bid)
    assert got == text
    sl = get(bid, 1, 2)
    assert "line1" in sl and "line2" in sl
    assert "xxx" not in sl


def test_missing():
    assert get("no-such-id") is None


if __name__ == "__main__":
    test_roundtrip()
    test_missing()
    print("ok")
