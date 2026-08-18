"""Fail-open thinning. Returns (new_response_or_None, bytes_in, bytes_out, note)."""

from __future__ import annotations

import json
import re
from typing import Any

TEST_RE = re.compile(
    r"(npm test|pnpm test|yarn test|pytest|vitest|jest|cargo test|go test|npx tsc|eslint|\blint\b)",
    re.I,
)
FAIL_RE = re.compile(
    r"(FAIL|Error|AssertionError|FAILED|error TS|✖|×|not ok |panic:)",
    re.I,
)


def _nbytes(obj: Any) -> int:
    if obj is None:
        return 0
    if isinstance(obj, str):
        return len(obj)
    if isinstance(obj, (bytes, bytearray)):
        return len(obj)
    try:
        return len(json.dumps(obj, default=str))
    except TypeError:
        return len(str(obj))


def _stdout_of(resp: Any) -> str | None:
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        for k in ("stdout", "output", "content"):
            v = resp.get(k)
            if isinstance(v, str):
                return v
    return None


def _strip_images(resp: Any) -> tuple[Any, int]:
    """Drop image blocks from a content list. Returns (new, n_dropped)."""
    if isinstance(resp, list):
        kept = []
        dropped = 0
        for b in resp:
            if isinstance(b, dict) and (
                b.get("type") == "image" or "source" in b and b.get("type") != "text"
            ):
                dropped += 1
                continue
            kept.append(b)
        return kept, dropped
    if isinstance(resp, dict) and isinstance(resp.get("content"), list):
        content, dropped = _strip_images(resp["content"])
        if dropped:
            out = dict(resp)
            out["content"] = content
            return out, dropped
    return resp, 0


def _thin_test_stdout(text: str, cap: int) -> str | None:
    if len(text) < 2000:
        return None
    lines = text.splitlines()
    keep = [ln for ln in lines if FAIL_RE.search(ln)]
    # always keep last 15 lines (summary / exit)
    tail = lines[-15:]
    seen = set()
    out_lines = []
    for ln in keep + tail:
        if ln in seen:
            continue
        seen.add(ln)
        out_lines.append(ln)
    thinned = "\n".join(out_lines)
    note = f"\n\n[spend] kept {len(out_lines)} of {len(lines)} lines ({len(text)}→{len(thinned)} bytes)"
    body = thinned + note
    if cap and len(body) > cap:
        body = body[:cap] + "\n[spend] capped"
    if len(body) >= len(text):
        return None
    return body


def shrink_tool(tool_name: str, tool_input: Any, tool_response: Any, cfg: dict) -> dict:
    """Decide whether to replace the tool result.

    Returns {
      bytes_in, bytes_out, shrunk: bool, note: str,
      updated_tool_output?: dict,  # Bash-shaped
      updated_mcp_output?: Any,
    }
    """
    bytes_in = _nbytes(tool_response)
    result = {
        "bytes_in": bytes_in,
        "bytes_out": bytes_in,
        "shrunk": False,
        "note": "",
    }
    if not cfg.get("shrink"):
        return result

    name = tool_name or ""
    cmd = ""
    if isinstance(tool_input, dict):
        cmd = str(tool_input.get("command") or tool_input.get("cmd") or "")
    elif isinstance(tool_input, str):
        cmd = tool_input

    # MCP / chrome / playwright: drop images
    is_mcp = name.startswith("mcp__") or "chrome" in name.lower() or "playwright" in name.lower()
    if cfg.get("strip_images") and is_mcp:
        new_resp, dropped = _strip_images(tool_response)
        if dropped:
            note = f"[spend] dropped {dropped} image block(s)"
            if isinstance(new_resp, list):
                new_resp = list(new_resp) + [{"type": "text", "text": note}]
            result["updated_mcp_output"] = new_resp
            result["bytes_out"] = _nbytes(new_resp)
            result["shrunk"] = True
            result["note"] = note
            return result

    # Bash / test output
    if name in {"Bash", "bash", "Shell", "Zsh"} and cfg.get("thin_tests"):
        stdout = _stdout_of(tool_response)
        if stdout and TEST_RE.search(cmd or stdout[:2000]):
            thinned = _thin_test_stdout(stdout, int(cfg.get("bash_cap_bytes") or 0))
            if thinned:
                if isinstance(tool_response, dict):
                    updated = dict(tool_response)
                    if "stdout" in updated:
                        updated["stdout"] = thinned
                    else:
                        updated["stdout"] = thinned
                    result["updated_tool_output"] = updated
                else:
                    result["updated_tool_output"] = {
                        "stdout": thinned,
                        "stderr": "",
                        "interrupted": False,
                        "isImage": False,
                    }
                result["bytes_out"] = len(thinned)
                result["shrunk"] = True
                result["note"] = "thinned test output"
                return result

        cap = int(cfg.get("bash_cap_bytes") or 0)
        stdout = _stdout_of(tool_response)
        if stdout and cap and len(stdout) > cap:
            cut = stdout[:cap] + f"\n[spend] capped at {cap} bytes (was {len(stdout)})"
            if isinstance(tool_response, dict) and "stdout" in tool_response:
                updated = dict(tool_response)
                updated["stdout"] = cut
                result["updated_tool_output"] = updated
            else:
                result["updated_tool_output"] = {
                    "stdout": cut,
                    "stderr": "",
                    "interrupted": False,
                    "isImage": False,
                }
            result["bytes_out"] = len(cut)
            result["shrunk"] = True
            result["note"] = "capped bash"
    return result
