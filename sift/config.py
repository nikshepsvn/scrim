from __future__ import annotations

import json
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
    "stash": True,
    "stash_ttl_days": 7,
    "stash_max_mb": 512,
    "session_tool_mb_warn": 2,
}


def data_dir() -> Path:
    new = Path.home() / ".sift"
    old = Path.home() / ".spend"
    if new.exists():
        return new
    if old.exists():
        try:
            old.rename(new)
            return new
        except OSError:
            return old
    new.mkdir(parents=True, exist_ok=True)
    return new


def load_config() -> dict:
    path = data_dir() / "config.json"
    cfg = dict(DEFAULTS)
    if path.exists():
        try:
            user = json.loads(path.read_text())
            if isinstance(user, dict):
                cfg.update({k: user[k] for k in DEFAULTS if k in user})
        except (OSError, json.JSONDecodeError):
            pass
    return cfg
