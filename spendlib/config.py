from __future__ import annotations

import json
from pathlib import Path

DEFAULTS = {
    "shrink": True,
    "strip_images": True,
    "thin_tests": True,
    "bash_cap_bytes": 48000,
    "warn_session_usd": 40.0,
}


def data_dir() -> Path:
    p = Path.home() / ".spend"
    p.mkdir(parents=True, exist_ok=True)
    return p


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
