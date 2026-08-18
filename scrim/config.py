from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "shrink": True,
    "strip_images": True,
    "thin_tests": True,
    "thin_reads": False,
    "bash_cap_bytes": 48000,
    "search_keep_lines": 40,
    "list_keep_lines": 80,
    "web_cap_bytes": 16000,
    "mcp_text_cap_bytes": 12000,
    "warn_session_usd": 40.0,
    "structural": True,
    "reducer": "off",
    "reducer_model": "inception/mercury-2",
    "reducer_min_bytes": 8000,
    "reducer_max_bytes": 120000,
    "reducer_timeout_sec": 20,
    "reducer_max_tokens": 4096,
    "reducer_api_key": "",
    "pretool": True,
    "ls_max_lines": 200,
    "grep_max_count": 80,
    "rg_max_columns": 300,
    "codex_block_thin": False,
    "stash": True,
    "stash_ttl_days": 7,
    "stash_max_mb": 512,
    "session_tool_mb_warn": 2,
    "max_open_subagents": 8,
}

_MISSING = object()


def data_dir() -> Path:
    override = os.environ.get("SCRIM_DATA_DIR")
    if override:
        dest = Path(override).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        return dest
    dest = Path.home() / ".scrim"
    if dest.exists():
        return dest
    for old in (Path.home() / ".sift", Path.home() / ".spend"):
        if old.exists():
            try:
                old.rename(dest)
                return dest
            except OSError:
                return old
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def config_path() -> Path:
    return data_dir() / "config.json"


def load_config() -> dict:
    return load_config_report()[0]


def load_config_report() -> tuple[dict, list[str]]:
    """Effective config plus human-readable warnings. Never raises —
    an unreadable disk still gets defaults so thinning can proceed."""
    cfg = dict(DEFAULTS)
    warnings: list[str] = []
    try:
        path = config_path()
        if not path.exists():
            return cfg, warnings
        user = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        warnings.append(f"config unreadable ({type(e).__name__}); using defaults")
        return cfg, warnings
    if not isinstance(user, dict):
        warnings.append("config.json is not a JSON object; using defaults")
        return cfg, warnings
    for key, value in user.items():
        if key not in DEFAULTS:
            warnings.append(f"unknown key {key!r} ignored")
            continue
        coerced = _coerce(value, DEFAULTS[key])
        if coerced is _MISSING:
            warnings.append(
                f"{key!r}: expected {type(DEFAULTS[key]).__name__}, "
                f"got {type(value).__name__}; using default"
            )
            continue
        cfg[key] = coerced
    return cfg, warnings


def _coerce(value, default):
    # bool must come first: isinstance(True, int) is True
    if isinstance(default, bool):
        return value if isinstance(value, bool) else _MISSING
    if isinstance(default, float):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return _MISSING
    if isinstance(default, int):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return int(value)
        return _MISSING
    if isinstance(default, str):
        return value if isinstance(value, str) else _MISSING
    return value
