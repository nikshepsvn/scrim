# spend

Local **tool-output thinning** and **quota tracking** for [Claude Code](https://code.claude.com). Optional Codex hooks.

Hooks **fail open**. Source `Read`s and `Edit`s are never rewritten. Metrics never include prompts or stdout.

This is not a billing product. On Claude Max it does not lower Stripe. It keeps chaff out of the context window and shows where the session went.

## Install

Private repo. Clone, then either:

```bash
git clone git@github.com:nikshepsvn/spend.git
claude --plugin-dir /path/to/spend
```

or, from Claude Code (needs GitHub auth for a private marketplace):

```text
/plugin marketplace add nikshepsvn/spend
/plugin install spend@spend
```

Restart Claude Code. Run a tool, then `/spend`.

```bash
python3 tests/test_shrink.py
python3 tests/test_compress.py
python3 tests/test_reducer.py
```

## What it does

| Layer | Default | What |
|---|---|---|
| Track | on | Every tool: name, kind, bytes in/out. `~/.spend/metrics.jsonl` |
| Filter | on | Kind-aware deterministic thinning (below) |
| Structural | on | Fat JSON → `{_n, head, tail}`; HTML → text |
| Model reducer | **off** | Optional OpenRouter extract (Mercury-2 recommended) |

### Kind policies

| Kind | How |
|---|---|
| `test_build_lint` | Keep FAIL / Error / traceback + tail |
| `log` | Drain-lite templates + counts |
| `search` (Grep / `rg`) | First N + tail; never drop FAIL/Error hits |
| `file_list` (`ls`, Glob) | First N paths + omitted count |
| `mcp` (Chrome / Playwright) | Drop **images**, then cap leftover text |
| `web` | Cap at 16 KB |
| `bash` (other fat) | Signal lines, else head+tail |
| `read` / `edit` | **Passthrough** |

gzip/zstd do not help. The model has to read text.

## Config

Copy [config.example.json](config.example.json) to `~/.spend/config.json`.

Set `"shrink": false` to log only.

### OpenRouter reducer (optional)

Recommended model after a live bake-off: **`inception/mercury-2`**. Cheap, ~3s, keeps failures, templates repeated INFO. Needs ≥4096 completion tokens on fat dumps. Fail-open if OpenRouter is slow.

```bash
export OPENROUTER_API_KEY=sk-or-...
```

If Claude is launched from the app and does not inherit your shell env, put the key in `~/.spend/config.json` as `reducer_api_key` (that file stays on this machine; do not commit it).

```json
{
  "reducer": "openrouter",
  "reducer_model": "inception/mercury-2",
  "reducer_max_tokens": 4096,
  "reducer_timeout_sec": 20
}
```

Do not use Morph apply models (`morph/morph-v3-*`) or Inkling as the reducer. Morph reprints the dump. Inkling spends the token budget on hidden reasoning and often returns empty `content`. See [docs/eval.md](docs/eval.md).

Flash (`google/gemini-2.5-flash`) is the boring backup.

## CLI

```bash
python3 scripts/spend.py           # all hook metrics
python3 scripts/spend.py --today
python3 scripts/spend.py --backfill   # API-eq $ from ~/.claude/projects
python3 scripts/spend.py --config
```

`/spend` in Claude Code runs the same CLI.

## Codex

See [codex/README.md](codex/README.md). Tracking works. Output replacement is first-class on Claude Code; treat Codex as tracking-first unless you verify `updatedToolOutput` on your CLI version.

## Privacy

- Default path: nothing leaves the machine except Claude’s normal provider call.
- Metrics: counts and tool names only.
- Reducer path: opted-in tool output is sent to OpenRouter (or Anthropic) to produce a shorter extract. Cached under `~/.spend/reducer-cache/`.

## Docs

- [docs/how-it-works.md](docs/how-it-works.md)
- [docs/config.md](docs/config.md)
- [docs/eval.md](docs/eval.md)
- [SECURITY.md](SECURITY.md)

## License

MIT
