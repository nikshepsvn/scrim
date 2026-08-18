"""Fail-open tool-output optimization. Never throw; caller fail-opens."""

from __future__ import annotations

import json
from typing import Any

from .classify import classify
from .compress import compress_text
from .reducer import reduce_text
from .textops import drain, head_tail, keep_signal_lines

# kinds we refuse to rewrite (source / diffs / small structured)
PASSTHROUGH = {"read", "edit", "other"}


def _nbytes(obj: Any) -> int:
    if obj is None:
        return 0
    if isinstance(obj, (str, bytes, bytearray)):
        return len(obj)
    try:
        return len(json.dumps(obj, default=str))
    except TypeError:
        return len(str(obj))


def _as_text(resp: Any) -> str | None:
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        for k in ("stdout", "output"):
            if isinstance(resp.get(k), str):
                return resp[k]
        c = resp.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return _as_text(c)
    if isinstance(resp, list):
        parts = []
        for b in resp:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict) and isinstance(b.get("text"), str):
                parts.append(b["text"])
        if parts:
            return "\n".join(parts)
    return None


def _strip_images(resp: Any) -> tuple[Any, int]:
    if isinstance(resp, list):
        kept, dropped = [], 0
        for b in resp:
            if isinstance(b, dict) and (
                b.get("type") == "image"
                or ("source" in b and b.get("type") != "text")
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


def _wrap_text(resp: Any, text: str, *, mcp: bool) -> dict:
    """Put thinned text back in the original shape."""
    if mcp:
        if isinstance(resp, list):
            return {"updated_mcp_output": [{"type": "text", "text": text}]}
        if isinstance(resp, dict):
            out = dict(resp)
            if isinstance(out.get("content"), list):
                out["content"] = [{"type": "text", "text": text}]
            elif "content" in out:
                out["content"] = text
            else:
                out["content"] = text
            return {"updated_mcp_output": out}
        return {"updated_mcp_output": [{"type": "text", "text": text}]}

    if isinstance(resp, dict) and "stdout" in resp:
        updated = dict(resp)
        updated["stdout"] = text
        return {"updated_tool_output": updated}
    if isinstance(resp, dict) and isinstance(resp.get("content"), str):
        updated = dict(resp)
        updated["content"] = text
        return {"updated_tool_output": updated}
    # Claude often delivers Bash/Grep as a raw string
    return {
        "updated_tool_output": {
            "stdout": text,
            "stderr": "",
            "interrupted": False,
            "isImage": False,
        }
    }


def _annotate(body: str, n_orig: int, kind: str) -> str:
    return body + f"\n\n[spend] {kind}: {n_orig} → {len(body)} bytes. Re-run with a tighter query if you need the rest."


def _optimize_text(kind: str, text: str, cfg: dict) -> str | None:
    search_n = int(cfg.get("search_keep_lines") or 40)
    list_n = int(cfg.get("list_keep_lines") or 80)
    web_cap = int(cfg.get("web_cap_bytes") or 16000)
    mcp_cap = int(cfg.get("mcp_text_cap_bytes") or 12000)
    bash_cap = int(cfg.get("bash_cap_bytes") or 48000)

    if kind == "test_build_lint":
        return keep_signal_lines(text)
    if kind == "log":
        return drain(text) or keep_signal_lines(text, extra_keep=30)
    if kind == "search":
        # never drop FAIL/Error hits (measured miss on Codex/SWE-smith)
        sig = keep_signal_lines(text, extra_keep=0)
        ht = head_tail(text, search_n, 8, "matches")
        if sig and ht and "FAIL" in text:
            return sig + "\n" + ht
        return ht
    if kind == "file_list":
        return head_tail(text, list_n, 10, "paths")
    if kind == "web":
        if len(text) > web_cap:
            return text[:web_cap] + f"\n[spend] web capped at {web_cap} bytes"
        return None
    if kind == "mcp":
        if len(text) > mcp_cap:
            return text[:mcp_cap] + f"\n[spend] mcp text capped at {mcp_cap} bytes"
        return None
    if kind == "bash":
        sig = keep_signal_lines(text)
        if sig:
            return sig
        if bash_cap and len(text) > bash_cap:
            return head_tail(text, 80, 40, "lines") or text[:bash_cap]
        return None
    return None


def shrink_tool(tool_name: str, tool_input: Any, tool_response: Any, cfg: dict) -> dict:
    bytes_in = _nbytes(tool_response)
    kind = classify(tool_name, tool_input)
    result = {
        "bytes_in": bytes_in,
        "bytes_out": bytes_in,
        "shrunk": False,
        "note": "",
        "kind": kind,
    }
    if not cfg.get("shrink"):
        return result
    if kind in PASSTHROUGH and not cfg.get("thin_reads"):
        return result
    # already spilled by the harness
    if isinstance(tool_response, str) and tool_response.startswith("<persisted-output>"):
        return result

    working = tool_response
    notes: list[str] = []

    if kind == "mcp" and cfg.get("strip_images"):
        working, dropped = _strip_images(working)
        if dropped:
            notes.append(f"dropped {dropped} image(s)")

    text = _as_text(working)
    if text is None:
        if notes and working is not tool_response:
            result.update(_wrap_from_resp(kind, working))
            result["bytes_out"] = _nbytes(working)
            result["shrunk"] = True
            result["note"] = "; ".join(notes)
        return result

    thinned = None
    if kind == "test_build_lint" and not cfg.get("thin_tests", True):
        thinned = None
    else:
        thinned = _optimize_text(kind, text, cfg)

    if cfg.get("structural", True) and (thinned is None or len(thinned) > 4000):
        src = thinned or text
        packed = compress_text(src)
        if packed and (thinned is None or len(packed) < len(thinned)):
            thinned = packed
            notes.append("structural")

    if (cfg.get("reducer") or "off") not in {"off", "false", "0", ""} and kind not in PASSTHROUGH:
        src = thinned or text
        reduced = reduce_text(src, cfg)
        if reduced and len(reduced) < len(src):
            thinned = reduced
            notes.append("reducer")

    if thinned:
        thinned = _annotate(thinned, len(text), kind)
        notes.append(kind)
        wrapped = _wrap_text(tool_response, thinned, mcp=(kind == "mcp"))
        result.update(wrapped)
        result["bytes_out"] = len(thinned)
        result["shrunk"] = True
        result["note"] = "; ".join(notes)
        return result

    if notes and working is not tool_response:
        # images stripped but no further text cut
        result["updated_mcp_output"] = working if kind == "mcp" else None
        if kind == "mcp":
            if isinstance(working, list):
                working = list(working) + [{"type": "text", "text": "[spend] " + notes[0]}]
                result["updated_mcp_output"] = working
        result["bytes_out"] = _nbytes(working)
        result["shrunk"] = True
        result["note"] = "; ".join(notes)
    return result


def _wrap_from_resp(kind: str, working: Any) -> dict:
    if kind == "mcp":
        return {"updated_mcp_output": working}
    return {}
