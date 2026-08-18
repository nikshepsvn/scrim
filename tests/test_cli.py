#!/usr/bin/env python3
"""CLI + hook subprocess smoke tests. Hooks must exit 0 and print valid
JSON (or nothing) no matter what they are fed."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_TMP = tempfile.TemporaryDirectory(prefix="scrim-test-")
ENV = {
    **os.environ,
    "SCRIM_DATA_DIR": _TMP.name,
    "CLAUDE_PLUGIN_ROOT": str(ROOT),
}
CLI = [sys.executable, str(ROOT / "scripts" / "scrim.py")]


def _run(args, stdin: str | None = None, cmd=None):
    return subprocess.run(
        cmd or (CLI + args),
        input=stdin,
        capture_output=True,
        text=True,
        env=ENV,
        timeout=30,
    )


def _hook(name: str, stdin: str):
    return _run([], stdin=stdin, cmd=["sh", str(ROOT / "hooks" / "run.sh"), name])


def test_version_matches_plugin_json():
    import scrim

    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["version"] == scrim.__version__
    r = _run(["--version"])
    assert r.returncode == 0
    assert scrim.__version__ in r.stdout


def test_config_prints_json():
    r = _run(["--config"])
    assert r.returncode == 0
    body = r.stdout.rsplit("edit", 1)[0]
    assert isinstance(json.loads(body), dict)


def test_report_runs():
    r = _run(["--today"])
    assert r.returncode == 0
    assert "Scrim" in r.stdout


def test_report_json():
    r = _run(["--today", "--json"])
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert "usage" in out and "tools" in out


def test_get_missing():
    r = _run(["get", "nope"])
    assert r.returncode == 1


def test_doctor_runs():
    r = _run(["doctor"])
    assert r.returncode == 0
    assert "python" in r.stdout


def test_kinds_and_stashes_run():
    for cmd in (["kinds"], ["stashes"]):
        r = _run(cmd)
        assert r.returncode == 0, r.stderr


def test_posttooluse_thins_and_exits_zero():
    payload = json.dumps({
        "session_id": "cli-test",
        "tool_name": "Bash",
        "tool_input": {"command": "pytest -q"},
        "tool_response": {"stdout": "\n".join(["PASS a"] * 400 + ["FAIL b", "AssertionError: boom"])},
        "tool_use_id": "toolu_clitest001",
    })
    r = _hook("posttooluse.py", payload)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    hook = out["hookSpecificOutput"]
    assert "FAIL b" in hook["updatedToolOutput"]["stdout"]
    assert "scrim get" in hook["additionalContext"]


def test_posttooluse_codex_never_emits_updated_tool_output():
    # Codex's PostToolUse output schema (additionalProperties: false) rejects
    # updatedToolOutput; the hook must go observe-only for builtin tools there
    payload = json.dumps({
        "session_id": "codex-test",
        "turn_id": "t-1",
        "tool_name": "shell",
        "tool_input": {"command": ["bash", "-lc", "pytest -q"], "workdir": "/tmp"},
        "tool_response": {"output": "\n".join(["PASS a"] * 400 + ["FAIL b", "AssertionError: boom"])},
        "tool_use_id": "call_codextest1",
    })
    r = _hook("posttooluse.py", payload)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    hook = out.get("hookSpecificOutput") or {}
    assert "updatedToolOutput" not in hook
    assert "updatedMCPToolOutput" not in hook


def test_pretooluse_codex_argv_updated_input():
    payload = json.dumps({
        "turn_id": "t-1",
        "tool_name": "shell",
        "tool_input": {"command": ["bash", "-lc", "ls -R /"], "workdir": "/tmp"},
    })
    r = _hook("pretooluse.py", payload)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    argv = out["hookSpecificOutput"]["updatedInput"]["command"]
    assert argv[0] == "bash" and "head -n" in argv[2]


def test_posttooluse_codex_block_thin_opt_in():
    # with codex_block_thin on, the hook uses Codex's decision:"block" lever —
    # the reason text replaces the tool result the model sees
    with tempfile.TemporaryDirectory(prefix="scrim-blockthin-") as td:
        (Path(td) / "config.json").write_text(json.dumps({"codex_block_thin": True}))
        payload = json.dumps({
            "session_id": "codex-test",
            "turn_id": "t-1",
            "tool_name": "shell",
            "tool_input": {"command": ["bash", "-lc", "pytest -q"]},
            "tool_response": {"output": "\n".join(["PASS a"] * 400 + ["FAIL b", "AssertionError: boom"])},
            "tool_use_id": "call_codexblock1",
        })
        r = subprocess.run(
            ["sh", str(ROOT / "hooks" / "run.sh"), "posttooluse.py"],
            input=payload, capture_output=True, text=True,
            env={**ENV, "SCRIM_DATA_DIR": td}, timeout=30,
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["decision"] == "block"
        assert "FAIL b" in out["reason"]
        assert "ran successfully" in out["reason"]
        assert "hookSpecificOutput" not in out


def test_events_logs_compaction():
    with tempfile.TemporaryDirectory(prefix="scrim-compact-") as td:
        payload = json.dumps({
            "hook_event_name": "PreCompact",
            "session_id": "s-compact",
            "trigger": "auto",
        })
        r = subprocess.run(
            ["sh", str(ROOT / "hooks" / "run.sh"), "events.py"],
            input=payload, capture_output=True, text=True,
            env={**ENV, "SCRIM_DATA_DIR": td}, timeout=30,
        )
        assert r.returncode == 0, r.stderr
        row = json.loads((Path(td) / "metrics.jsonl").read_text().splitlines()[-1])
        assert row["kind"] == "compact"
        assert row["tool_name"] == "auto"


def test_days_runs():
    r = _run(["days", "3"])
    assert r.returncode == 0, r.stderr


def test_pretooluse_caps_ls():
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -R /"}})
    r = _hook("pretooluse.py", payload)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "head -n" in out["hookSpecificOutput"]["updatedInput"]["command"]


def test_posttooluse_thins_even_with_dead_data_dir():
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "pytest -q"},
        "tool_response": {"stdout": "\n".join(["PASS a"] * 400 + ["FAIL b"])},
    })
    env = {**ENV, "SCRIM_DATA_DIR": "/dev/null/nope"}
    r = subprocess.run(
        ["sh", str(ROOT / "hooks" / "run.sh"), "posttooluse.py"],
        input=payload, capture_output=True, text=True, env=env, timeout=30,
    )
    assert r.returncode == 0, r.stderr
    hook = json.loads(r.stdout)["hookSpecificOutput"]
    assert "FAIL b" in hook["updatedToolOutput"]["stdout"]  # thinning survived
    assert "scrim get" not in hook.get("additionalContext", "")  # stash skipped


def test_hooks_fail_open_on_garbage():
    for name in ("pretooluse.py", "posttooluse.py", "stop.py", "events.py"):
        r = _hook(name, "this is not json{{{")
        assert r.returncode == 0, f"{name}: rc={r.returncode} {r.stderr}"
        if r.stdout.strip():
            json.loads(r.stdout)


def test_hook_direct_invocation_no_env():
    # Codex points straight at the .py file with no CLAUDE_PLUGIN_ROOT
    env = {k: v for k, v in ENV.items() if k not in {"CLAUDE_PLUGIN_ROOT", "PYTHONPATH"}}
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "pytest -q"},
        "tool_response": {"stdout": "\n".join(["PASS a"] * 400 + ["FAIL b"])},
    })
    r = subprocess.run(
        [sys.executable, str(ROOT / "hooks" / "posttooluse.py")],
        input=payload, capture_output=True, text=True, env=env, timeout=30,
    )
    assert r.returncode == 0, r.stderr
    hook = json.loads(r.stdout)["hookSpecificOutput"]
    assert "FAIL b" in hook["updatedToolOutput"]["stdout"]


def test_run_sh_missing_hook_fails_open():
    r = _run([], stdin="{}", cmd=["sh", str(ROOT / "hooks" / "run.sh"), "no-such-hook.py"])
    assert r.returncode == 0
    assert r.stdout.strip() == "{}"
    r = _run([], stdin="{}", cmd=["sh", str(ROOT / "hooks" / "run.sh")])
    assert r.returncode == 0
    assert r.stdout.strip() == "{}"


def test_stop_writes_last_report():
    payload = json.dumps({"session_id": "cli-test", "transcript_path": "/nonexistent.jsonl"})
    r = _hook("stop.py", payload)
    assert r.returncode == 0, r.stderr
    assert (Path(_TMP.name) / "last.txt").exists()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("all ok")
