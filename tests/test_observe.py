#!/usr/bin/env python3
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scrim.observe import parse_transcript


def test_parse_usage():
    rec = {
        "type": "assistant",
        "timestamp": "2026-08-18T00:00:00Z",
        "sessionId": "s1",
        "cwd": "/tmp",
        "message": {
            "model": "claude-opus-5",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "cache_read_input_tokens": 1000,
                "cache_creation_input_tokens": 50,
            },
        },
    }
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps(rec) + "\n")
        path = Path(f.name)
    u = parse_transcript(path)
    path.unlink()
    assert u["total"]["turns"] == 1
    assert u["total"]["cr"] == 1000
    assert u["total"]["cost"] > 0
    assert u["session_id"] == "s1"


if __name__ == "__main__":
    test_parse_usage()
    print("ok")
