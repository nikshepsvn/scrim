#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_TMP = tempfile.TemporaryDirectory(prefix="scrim-test-")
os.environ["SCRIM_DATA_DIR"] = _TMP.name

from scrim.stash import entries, gc, get, put


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


def test_same_second_no_collision():
    a = put("A" * 500, kind="bash", tool_name="Bash")
    b = put("B" * 600, kind="bash", tool_name="Bash")
    assert a and b and a != b
    assert get(a) == "A" * 500
    assert get(b) == "B" * 600


def test_same_tool_use_id_different_content():
    a = put("A" * 500, tool_use_id="toolu_dupetest99", kind="bash")
    b = put("B" * 600, tool_use_id="toolu_dupetest99", kind="bash")
    assert a and b and a != b
    assert get(a) == "A" * 500
    assert get(b) == "B" * 600


def test_entries_listing():
    bid = put("C" * 700, tool_use_id="toolu_entrytest1", kind="search", tool_name="Grep")
    rows = entries(50)
    mine = [r for r in rows if r["id"] == bid]
    assert mine and mine[0]["live"] is True
    assert mine[0]["kind"] == "search"


def test_gc_respects_ttl():
    bid = put("D" * 800, tool_use_id="toolu_gctest0001", kind="bash")
    blob = Path(_TMP.name) / "blobs" / f"{bid}.txt"
    assert blob.exists()
    # age the blob past any ttl and confirm gc removes it
    old = 60 * 60 * 24 * 400
    stat = blob.stat()
    os.utime(blob, (stat.st_atime - old, stat.st_mtime - old))
    gc()
    assert not blob.exists()


def test_short_text_not_stashed():
    assert put("tiny") is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("all ok")
