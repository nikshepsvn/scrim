from __future__ import annotations

import re
from collections import OrderedDict

FAIL_RE = re.compile(
    r"(FAIL|Error|AssertionError|FAILED|error TS|✖|×|not ok |panic:|Traceback|EXCEPTION)",
    re.I,
)
LEVEL_RE = re.compile(r"\b(ERROR|WARN|WARNING|FATAL|CRITICAL)\b")
SLOT_RE = re.compile(
    r"\b\d+\b|[0-9a-f]{8}-[0-9a-f-]{4,}|0x[0-9a-f]+|\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
    re.I,
)
# stack frames under a signal line: Python "  File ...", JS "    at ...",
# and generically indented assertion/code context — without these a
# Traceback keeps only its header and exception line
CONT_RE = re.compile(r"^\s+at |^\s+File \"|^\s{2,}\S")


def keep_signal_lines(
    text: str, extra_keep: int = 15, max_signal: int = 400, frames_after: int = 25
) -> str | None:
    if len(text) < 2000:
        return None
    lines = text.splitlines()
    kept_idx: set[int] = set()
    keep: list[str] = []
    for i, ln in enumerate(lines):
        if not (FAIL_RE.search(ln) or LEVEL_RE.search(ln)):
            continue
        if i not in kept_idx:
            kept_idx.add(i)
            keep.append(ln)
        j = i + 1
        while j < len(lines) and j - i <= frames_after and CONT_RE.match(lines[j]):
            if j not in kept_idx:
                kept_idx.add(j)
                keep.append(lines[j])
            j += 1
    if len(keep) > max_signal:
        omitted = len(keep) - max_signal
        keep = keep[: max_signal // 2] + [
            f"[scrim] … {omitted} more signal lines omitted …"
        ] + keep[-max_signal // 2:]
    # lines[-0:] would be the whole list, silently returning the full text
    tail = lines[-extra_keep:] if extra_keep > 0 else []
    seen: set[str] = set()
    out: list[str] = []
    for ln in keep + tail:
        if ln in seen:
            continue
        seen.add(ln)
        out.append(ln)
    body = "\n".join(out)
    if len(body) >= len(text):
        return None
    return body


def head_tail(text: str, head: int, tail: int, label: str) -> str | None:
    lines = text.splitlines()
    if len(lines) <= head + tail + 2:
        return None
    omitted = len(lines) - head - tail
    parts = lines[:head]
    parts.append(f"[scrim] … {omitted} {label} omitted …")
    parts.extend(lines[-tail:])
    return "\n".join(parts)


def drain(text: str, max_groups: int = 40, samples: int = 1) -> str | None:
    """Cheap log templating: slot numbers/ids, keep counts + one sample."""
    if len(text) < 4000:
        return None
    groups: OrderedDict[str, list[str]] = OrderedDict()
    for ln in text.splitlines():
        key = SLOT_RE.sub("<*>", ln)
        groups.setdefault(key, []).append(ln)
    if len(groups) >= len(text.splitlines()) * 0.8:
        return None  # not repetitive
    rows = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    out = [f"[scrim] {len(text.splitlines())} lines → {len(groups)} templates"]
    for i, (tmpl, members) in enumerate(rows):
        if i >= max_groups:
            out.append(f"[scrim] +{len(rows) - max_groups} more templates")
            break
        out.append(f"[{len(members):6}] {tmpl[:240]}")
        for s in members[:samples]:
            if s != tmpl:
                out.append(f"         e.g. {s[:200]}")
    # templates are sorted by count, which loses time order — keep the raw
    # tail, where a crash usually is
    tail = [ln for ln in text.splitlines()[-5:] if ln.strip()]
    if tail:
        out.append("[scrim] last lines:")
        out.extend(ln[:240] for ln in tail)
    body = "\n".join(out)
    if len(body) >= len(text) * 0.9:
        return None
    return body
