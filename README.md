# Sift

**Sift tool output before the model reads it.**

Claude Code will feed the model 4,000 lines of passing tests and a folder of screenshots. Sift sits on `PostToolUse`, classifies the result, and hands the model the evidence. Hooks fail open. `Read` and `Edit` are never rewritten.

It does not switch models and it does not change your Anthropic bill. It keeps chaff out of the window.

## Before / after

`pytest -q` — 402 lines, one failure:

```
PASS test_a
PASS test_a
… 398 more …
FAIL test_b
AssertionError: boom
```

What the model gets:

```
FAIL test_b
AssertionError: boom

[sift] test_build_lint: 2827 → 34 bytes.
```

Chrome `browser_batch` with six screenshots: images dropped, text kept. On this machine that was 104 MB → 3 MB of MCP payload.

## Install

```bash
git clone git@github.com:nikshepsvn/sift.git
claude --plugin-dir "$(pwd)/sift"
```

Needs GitHub auth (private repo):

```text
/plugin marketplace add nikshepsvn/sift
/plugin install sift@sift
```

Restart Claude Code. Run any tool. Then `/sift`.

```bash
make test
```

## `/sift`

```
today 2026-08-18
  tool calls     12
  bytes in       4.20 MB
  bytes out      0.31 MB
  thinned        3 calls, 3.89 MB dropped
  top tools
    mcp__claude-in-chrome__browser_batch   n=2     3.80 MB
    Bash                                   n=8     0.28 MB
data: ~/.sift
```

CLI is the same thing:

```bash
python3 scripts/sift.py --today
python3 scripts/sift.py --backfill   # list-price $ from ~/.claude/projects
```

`--backfill` is shadow cost (Opus/Sonnet list prices). Max/Ultra subscribers do not pay that cash.

## What gets thinned

| Kind | Policy |
|---|---|
| Tests / lint | FAIL, Error, traceback + tail |
| Logs | Drain-lite templates + counts |
| Grep / `rg` | Head + tail; FAIL/Error hits always kept |
| `ls` / Glob | Head + omitted count |
| Chrome / Playwright | Drop images, cap leftover text |
| Web | 16 KB cap |
| Other fat bash | Signal lines, else head+tail |
| `Read` / `Edit` | Untouched |

gzip does not reduce tokens. The model has to read text.

Copy [`config.example.json`](config.example.json) to `~/.sift/config.json`. `"shrink": false` logs only. Full key list: [docs/config.md](docs/config.md).

If `~/.spend` still exists from the old name, the first run renames it.

## Optional: OpenRouter extract

Deterministic filters are the default and enough for screenshots and fat bash. For logs that need a real extract, turn on a reducer. **`inception/mercury-2`** is the one that worked in our bake-off (keep ≥4096 completion tokens).

```bash
export OPENROUTER_API_KEY=sk-or-...
```

```json
{
  "reducer": "openrouter",
  "reducer_model": "inception/mercury-2",
  "reducer_max_tokens": 4096,
  "reducer_timeout_sec": 20
}
```

The macOS Claude app often does not inherit shell env. You can set `reducer_api_key` in `~/.sift/config.json` instead. Do not commit that file.

Skip Morph (`morph/morph-v3-*`) and Inkling. Morph reprints the dump. Inkling burns the budget on hidden reasoning. Notes: [docs/eval.md](docs/eval.md). Backup: `google/gemini-2.5-flash`.

## Privacy

Default: nothing extra leaves the machine. Metrics are counts and tool names.

Reducer on: truncated tool output goes to OpenRouter (or Anthropic). Cache: `~/.sift/reducer-cache/`.

## Codex

Tracking works if you point Codex `PostToolUse` at `hooks/posttooluse.py`. Replacing output is first-class in Claude Code; confirm it on your Codex build before relying on it. [codex/README.md](codex/README.md).

## Docs

- [docs/how-it-works.md](docs/how-it-works.md) — hook pipeline
- [docs/config.md](docs/config.md) — every key
- [docs/eval.md](docs/eval.md) — measured save rates and model bake-off
- [SECURITY.md](SECURITY.md)

## License

MIT
