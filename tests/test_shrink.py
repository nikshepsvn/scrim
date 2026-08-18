#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spendlib.shrink import shrink_tool

CFG = {
    "shrink": True,
    "strip_images": True,
    "thin_tests": True,
    "bash_cap_bytes": 8000,
}


def test_passthrough_small_bash():
    r = shrink_tool("Bash", {"command": "echo hi"}, {"stdout": "hi\n", "stderr": ""}, CFG)
    assert r["shrunk"] is False


def test_thin_pytest():
    lines = ["PASS test_a"] * 200 + ["FAIL test_b", "AssertionError: boom"]
    stdout = "\n".join(lines)
    r = shrink_tool("Bash", {"command": "pytest -q"}, {"stdout": stdout, "stderr": ""}, CFG)
    assert r["shrunk"] is True
    assert r["bytes_out"] < r["bytes_in"]
    assert "FAIL test_b" in r["updated_tool_output"]["stdout"]
    assert "AssertionError" in r["updated_tool_output"]["stdout"]


def test_strip_images():
    resp = [
        {"type": "text", "text": "navigated"},
        {"type": "image", "source": {"type": "base64", "data": "x" * 5000}},
        {"type": "text", "text": "ok"},
    ]
    r = shrink_tool("mcp__claude-in-chrome__browser_batch", {}, resp, CFG)
    assert r["shrunk"] is True
    kinds = [b.get("type") for b in r["updated_mcp_output"] if isinstance(b, dict)]
    assert "image" not in kinds
    assert r["bytes_out"] < r["bytes_in"]


def test_fail_open_disabled():
    r = shrink_tool("Bash", {"command": "pytest"}, {"stdout": "FAIL\n" * 5000}, {**CFG, "shrink": False})
    assert r["shrunk"] is False


if __name__ == "__main__":
    test_passthrough_small_bash()
    test_thin_pytest()
    test_strip_images()
    test_fail_open_disabled()
    print("ok")
