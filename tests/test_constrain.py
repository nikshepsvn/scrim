#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scrim.constrain import constrain

CFG = {"pretool": True, "ls_max_lines": 50, "grep_max_count": 20}


def test_ls_piped():
    r = constrain("Bash", {"command": "ls -R src"}, CFG)
    assert "updated_input" in r
    assert "| head -n 50" in r["updated_input"]["command"]


def test_ls_already_piped():
    r = constrain("Bash", {"command": "ls -R src | wc -l"}, CFG)
    assert r == {}


def test_grep_head_limit():
    r = constrain("Grep", {"pattern": "TODO", "path": "src"}, CFG)
    assert r["updated_input"]["head_limit"] == 20


def test_rg_max_count():
    r = constrain("Bash", {"command": "rg TODO src"}, CFG)
    assert "--max-count 20" in r["updated_input"]["command"]


def test_off():
    assert constrain("Bash", {"command": "ls -R"}, {**CFG, "pretool": False}) == {}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("all ok")
