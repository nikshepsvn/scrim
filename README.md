# Sift

**Sift tool output before the model reads it.**

Coding agents drown in passing tests, `ls -R`, log spam, and Chrome screenshots. Sift is a Claude Code plugin that classifies each tool result and keeps the evidence. What it drops stays off the next request. Hooks fail open. Source `Read`s and `Edit`s are never rewritten.

It does not change your model. On Claude Max it does not lower Stripe. It keeps the window from filling with chaff, and it shows you what filled it.

## Install

Private repo.

```bash
git clone git@github.com:nikshepsvn/sift.git
claude --plugin-dir /absolute/path/to/sift
```

Or, with GitHub auth:

```text
/plugin marketplace add nikshepsvn/sift
/plugin install sift@sift
```

Restart Claude Code. Use a tool. Then `/sift`.

```bash
make test
```

## What it does

| Layer | Default | Role |
|---|---|---|
| Track | on | Tool name, kind, bytes in/out → `~/.sift/metrics.jsonl` |
| Filter | on | Deterministic, kind-aware thinning |
| Structural | on | Fat JSON → `{_n, head, tail}`; HTML → text |
| Reducer | **off** | Optional OpenRouter extract (`inception/mercury-2`) |

| Kind | Policy |
|---|---|
| Tests / lint | FAIL, Error, traceback, tail |
| Logs | Drain-lite templates + counts |
| Grep / `rg` | Head + tail; never drop FAIL/Error hits |
| `ls` / Glob | Head + omitted count |
| Chrome / Playwright | Drop images, cap leftover text |
| Web | 16 KB cap |
| Other fat bash | Signal lines, else head+tail |
| `Read` / `Edit` | Untouched |

gzip does not help. The model has to read text.

## Config

Copy [`config.example.json`](config.example.json) to `~/.sift/config.json`.  
If you still have `~/.spend` from the old name, Sift renames it on first run.

`"shrink": false` logs only.

### Optional reducer

After a live bake-off, **`inception/mercury-2`** is the one that extracts. Use at least 4096 completion tokens. Fail-open if OpenRouter is slow.

```bash
export OPENROUTER_API_KEY=sk-or-...
```

If Claude is launched from the macOS app, it may not see that env var. You can set `reducer_api_key` in `~/.sift/config.json` instead. Do not commit that file.

```json
{
  "reducer": "openrouter",
  "reducer_model": "inception/mercury-2",
  "reducer_max_tokens": 4096,
  "reducer_timeout_sec": 20
}
```

Do not use Morph apply models or Inkling. Morph reprints the dump. Inkling spends the budget on hidden reasoning and often returns empty `content`. Notes: [docs/eval.md](docs/eval.md). Backup: `google/gemini-2.5-flash`.

## CLI

```bash
python3 scripts/sift.py
python3 scripts/sift.py --today
python3 scripts/sift.py --backfill
python3 scripts/sift.py --config
```

## Codex

[codex/README.md](codex/README.md). Tracking works. Output replacement is first-class on Claude Code; treat Codex as tracking-first until you verify it on your CLI.

## Privacy

Default path: nothing extra leaves the machine. Metrics are counts and tool names.  
Opt-in reducer: truncated tool output goes to OpenRouter (or Anthropic). Cache: `~/.sift/reducer-cache/`.

## Why “Sift”

Not “spend.” This is not a billing product. Sift is the verb: keep the grain, drop the rest.

## Docs

- [docs/how-it-works.md](docs/how-it-works.md)
- [docs/config.md](docs/config.md)
- [docs/eval.md](docs/eval.md)
- [SECURITY.md](SECURITY.md)

## License

MIT
