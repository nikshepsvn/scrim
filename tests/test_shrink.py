#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scrim.classify import classify
from scrim.shrink import shrink_tool

CFG = {
    "shrink": True,
    "strip_images": True,
    "thin_tests": True,
    "thin_reads": False,
    "bash_cap_bytes": 8000,
    "search_keep_lines": 5,
    "list_keep_lines": 5,
    "web_cap_bytes": 100,
    "mcp_text_cap_bytes": 80,
}


def test_passthrough_small_bash():
    r = shrink_tool("Bash", {"command": "echo hi"}, {"stdout": "hi\n", "stderr": ""}, CFG)
    assert r["shrunk"] is False
    assert r["kind"] == "bash"


def test_thin_pytest():
    lines = ["PASS test_a"] * 200 + ["FAIL test_b", "AssertionError: boom"]
    stdout = "\n".join(lines)
    r = shrink_tool("Bash", {"command": "pytest -q"}, {"stdout": stdout, "stderr": ""}, CFG)
    assert r["kind"] == "test_build_lint"
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
    assert r["kind"] == "mcp"
    assert r["shrunk"] is True
    out = r["updated_mcp_output"]
    kinds = [b.get("type") for b in out if isinstance(b, dict)]
    assert "image" not in kinds
    assert r["bytes_out"] < r["bytes_in"]


def test_grep_head():
    text = "\n".join(f"src/a.ts:{i}: hit" for i in range(80))
    r = shrink_tool("Grep", {"pattern": "hit"}, text, CFG)
    assert r["kind"] == "search"
    assert r["shrunk"] is True
    assert "omitted" in r["updated_tool_output"]["stdout"]
    assert "src/a.ts:0: hit" in r["updated_tool_output"]["stdout"]


def test_ls_file_list():
    text = "\n".join(f"file_{i}.ts" for i in range(200))
    r = shrink_tool("Bash", {"command": "ls -R src"}, {"stdout": text}, CFG)
    assert r["kind"] == "file_list"
    assert r["shrunk"] is True


def test_logs_drain():
    lines = [f"INFO request id={i} path=/v1/orders 200" for i in range(300)]
    lines += ["ERROR psycopg2.OperationalError: connection"]
    text = "\n".join(lines)
    r = shrink_tool("Bash", {"command": "kubectl logs deploy/api --tail=500"}, {"stdout": text}, CFG)
    assert r["kind"] == "log"
    assert r["shrunk"] is True
    assert r["bytes_out"] < r["bytes_in"]
    assert "templates" in r["updated_tool_output"]["stdout"] or "ERROR" in r["updated_tool_output"]["stdout"]


def test_read_passthrough():
    big = "def foo():\n    pass\n" * 500
    r = shrink_tool("Read", {"file_path": "a.py"}, big, CFG)
    assert r["kind"] == "read"
    assert r["shrunk"] is False


def test_persisted_passthrough():
    r = shrink_tool("Bash", {"command": "pytest"}, "<persisted-output>\nOutput too large", CFG)
    assert r["shrunk"] is False


def test_fail_open_disabled():
    r = shrink_tool("Bash", {"command": "pytest"}, {"stdout": "FAIL\n" * 5000}, {**CFG, "shrink": False})
    assert r["shrunk"] is False


def test_classify_bash_rg():
    assert classify("Bash", {"command": "rg -n TODO src"}) == "search"


def test_classify_command_position():
    # "find"/"ls" inside string args or pipelines must not misclassify
    assert classify("Bash", {"command": "python3 -c \"print('find me')\""}) == "bash"
    assert classify("Bash", {"command": "cat data.txt | grep ERROR"}) == "search"
    assert classify("Bash", {"command": "pytest -q && ls"}) == "test_build_lint"
    assert classify("Bash", {"command": "ruff check ."}) == "test_build_lint"


def test_search_keeps_fail_in_omitted_middle():
    lines = [f"src/mod_{i}.py:{i}: match line here" for i in range(200)]
    lines[100] = "src/checkout.py:118: FAIL expected 500 == 502"
    r = shrink_tool("Grep", {"pattern": "checkout"}, "\n".join(lines), CFG)
    assert r["shrunk"] is True
    out = r["updated_tool_output"]["stdout"]
    assert "FAIL expected 500 == 502" in out
    assert "omitted" in out


def test_thin_tests_off_passthrough():
    stdout = "\n".join(["PASS test_a"] * 300 + ["FAIL test_b"])
    r = shrink_tool("Bash", {"command": "pytest -q"}, {"stdout": stdout}, {**CFG, "thin_tests": False})
    assert r["shrunk"] is False


def test_web_capped():
    text = "word " * 400  # 2000 chars, cap is 100
    r = shrink_tool("WebFetch", {"url": "https://example.com"}, text, CFG)
    assert r["kind"] == "web"
    assert r["shrunk"] is True
    assert "capped" in r["updated_tool_output"]["stdout"]
    assert r["bytes_out"] < r["bytes_in"]


def test_never_larger_than_input():
    # a marginal head/tail cut plus annotations would exceed the original
    text = "\n".join(f"line number {i:04d} padding" for i in range(16))
    r = shrink_tool("Grep", {"pattern": "line"}, text, CFG)
    assert r["shrunk"] is False
    assert r["bytes_out"] == r["bytes_in"]


if __name__ == "__main__":
    for fn, val in list(globals().items()):
        if fn.startswith("test_") and callable(val):
            val()
            print("ok", fn)
    print("all ok")
