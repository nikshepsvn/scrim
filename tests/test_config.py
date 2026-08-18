#!/usr/bin/env python3
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_TMP = tempfile.TemporaryDirectory(prefix="scrim-test-")
os.environ["SCRIM_DATA_DIR"] = _TMP.name

from scrim.config import DEFAULTS, config_path, data_dir, load_config, load_config_report


def _write_cfg(obj) -> None:
    config_path().write_text(json.dumps(obj) if not isinstance(obj, str) else obj)


def test_env_override():
    assert data_dir() == Path(_TMP.name)


def test_defaults_when_missing():
    if config_path().exists():
        config_path().unlink()
    cfg, warnings = load_config_report()
    assert cfg == DEFAULTS
    assert warnings == []


def test_valid_overrides():
    _write_cfg({"shrink": False, "grep_max_count": 33, "warn_session_usd": 5})
    cfg = load_config()
    assert cfg["shrink"] is False
    assert cfg["grep_max_count"] == 33
    assert cfg["warn_session_usd"] == 5.0  # int accepted for float keys


def test_wrong_types_fall_back():
    _write_cfg({"shrink": "yes", "grep_max_count": "80", "reducer": 3})
    cfg, warnings = load_config_report()
    assert cfg["shrink"] is DEFAULTS["shrink"]
    assert cfg["grep_max_count"] == DEFAULTS["grep_max_count"]
    assert cfg["reducer"] == DEFAULTS["reducer"]
    assert len(warnings) == 3


def test_unknown_key_warns_but_loads():
    _write_cfg({"grep_max_count": 12, "no_such_key": 1})
    cfg, warnings = load_config_report()
    assert cfg["grep_max_count"] == 12
    assert any("no_such_key" in w for w in warnings)


def test_garbage_file_fails_open():
    _write_cfg("{not json")
    cfg, warnings = load_config_report()
    assert cfg == DEFAULTS
    assert warnings
    _write_cfg([1, 2, 3])
    cfg, warnings = load_config_report()
    assert cfg == DEFAULTS
    assert warnings
    config_path().unlink()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("all ok")
