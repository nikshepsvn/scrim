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


def test_ls_long_flags():
    r = constrain("Bash", {"command": "ls -la -R src"}, CFG)
    assert "| head -n 50" in r["updated_input"]["command"]


def test_ls_already_piped():
    r = constrain("Bash", {"command": "ls -R src | wc -l"}, CFG)
    assert r == {}


def test_redirect_untouched():
    r = constrain("Bash", {"command": "find . -name '*.py' > /tmp/out.txt"}, CFG)
    assert r == {}


def test_find_capped():
    r = constrain("Bash", {"command": "find . -name '*.ts'"}, CFG)
    assert "| head -n 50" in r["updated_input"]["command"]


def test_find_delete_untouched():
    # head can SIGPIPE-kill a mutating find mid-run
    assert constrain("Bash", {"command": "find . -name '*.pyc' -delete"}, CFG) == {}


def test_find_exec_untouched():
    assert constrain("Bash", {"command": "find . -name '*.tmp' -exec rm {} \\;"}, CFG) == {}


def test_find_in_string_arg_untouched():
    # "find" not at command position must not be rewritten
    assert constrain("Bash", {"command": "python3 -c \"print('find me')\""}, CFG) == {}
    assert constrain("Bash", {"command": "grep -r 'find src' lib"}, CFG) == {}


def test_grep_head_limit():
    r = constrain("Grep", {"pattern": "TODO", "path": "src"}, CFG)
    assert r["updated_input"]["head_limit"] == 20


def test_rg_max_count():
    r = constrain("Bash", {"command": "rg TODO src"}, CFG)
    assert "--max-count 20" in r["updated_input"]["command"]


def test_rg_already_bounded():
    assert constrain("Bash", {"command": "rg -l TODO src"}, CFG) == {}
    assert constrain("Bash", {"command": "rg --files-with-matches TODO"}, CFG) == {}
    assert constrain("Bash", {"command": "rg --max-count 5 TODO src"}, CFG) == {}
    assert constrain("Bash", {"command": "rg -c TODO src"}, CFG) == {}


def test_rg_after_cd():
    r = constrain("Bash", {"command": "cd src && rg TODO"}, CFG)
    assert r["updated_input"]["command"].endswith("--max-count 20")


def test_off():
    assert constrain("Bash", {"command": "ls -R"}, {**CFG, "pretool": False}) == {}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("all ok")
