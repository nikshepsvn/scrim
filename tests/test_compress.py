#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spendlib.compress import compress_text
from spendlib.shrink import shrink_tool


def test_json_array():
    obj = {"orders": [{"id": i, "ok": True} for i in range(200)]}
    raw = json.dumps(obj)
    out = compress_text(raw)
    assert out is not None
    assert len(out) < len(raw) / 5
    assert '"_n": 200' in out or '"_n":200' in out


def test_html():
    html = "<html><head><style>x{c:1}</style></head><body>" + ("<p>hello</p>" * 80) + "</body></html>"
    out = compress_text(html)
    assert out is not None
    assert "<style" not in out
    assert "hello" in out


def test_small_skipped():
    assert compress_text('{"a":1}') is None


def test_wired_into_bash_json():
    payload = json.dumps({"rows": [{"x": i} for i in range(100)]})
    cfg = {
        "shrink": True,
        "strip_images": True,
        "thin_tests": True,
        "thin_reads": False,
        "structural": True,
        "reducer": "off",
        "bash_cap_bytes": 48000,
        "search_keep_lines": 40,
        "list_keep_lines": 80,
        "web_cap_bytes": 16000,
        "mcp_text_cap_bytes": 12000,
    }
    r = shrink_tool("Bash", {"command": "curl api/orders"}, {"stdout": payload}, cfg)
    assert r["shrunk"] is True
    assert "structural" in r["note"] or "_n" in r["updated_tool_output"]["stdout"]


if __name__ == "__main__":
    test_json_array()
    test_html()
    test_small_skipped()
    test_wired_into_bash_json()
    print("ok")
