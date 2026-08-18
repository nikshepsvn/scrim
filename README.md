# spend

Local **spend tracking** and **tool-output thinning** for [Claude Code](https://code.claude.com). Optional Codex hooks.

No cloud. No API keys. Tool payloads never leave the machine. Hooks **fail open**.

This is not Codag. It does not change your model. On Claude Max it will not lower Stripe — it lowers **quota burn** and shows where the session went.

## What it does

| | |
|---|---|
| **Track** | Every tool call: name, bytes in/out, whether it was thinned. `~/.spend/metrics.jsonl` |
| **Optimize output** | By kind, before the model reads it. Fail-open. Source `Read`s are never touched. |

### What gets thinned

| Kind | How |
|---|---|
| `test_build_lint` | Keep FAIL / Error / traceback + tail |
| `log` | Template-group repetitive lines (Drain-lite) |
| `search` (Grep / `rg`) | First N hits + tail + omitted count |
| `file_list` (`ls`, Glob) | First N paths + omitted count |
| `mcp` (Chrome / Playwright) | Drop **images**, then cap leftover text |
| `web` | Cap at 16 KB |
| `bash` (other fat) | Signal lines, else head+tail |
| `read` / `edit` | **Passthrough** |
| **Report** | `/spend` or `python3 scripts/spend.py` |
| **Backfill** | `python3 scripts/spend.py --backfill` reads `~/.claude/projects` usage fields (API-equivalent $) |

It will **not** switch Opus → Haiku. Hooks cannot do that.

## Install (Claude Code)

```bash
git clone https://github.com/YOU/spend.git
claude --plugin-dir /path/to/spend
```

Or add the folder as a local plugin marketplace and enable `spend`. Restart Claude Code, then run a tool and `/spend`.

## CLI

```bash
python3 scripts/spend.py          # all hook metrics
python3 scripts/spend.py --today
python3 scripts/spend.py --backfill   # historical transcript $
python3 scripts/spend.py --config
```

## Config

`~/.spend/config.json` (created with defaults on first hook):

```json
{
  "shrink": true,
  "strip_images": true,
  "thin_tests": true,
  "thin_reads": false,
  "bash_cap_bytes": 48000,
  "search_keep_lines": 40,
  "list_keep_lines": 80,
  "web_cap_bytes": 16000,
  "mcp_text_cap_bytes": 12000
}
```

Set `"shrink": false` to log only.

### Compressor (optional)

`gzip` / `zstd` do **not** help. The model has to read text, not bytes.

There are two real compressors, both agent-readable:

1. **Structural** (on by default) — large JSON/NDJSON becomes `{_n, head, tail}`; HTML becomes stripped text.
2. **Model reducer** (off) — extractive pass on fat logs/bash/MCP. Fail-open, cached.

**OpenRouter** (any model):

```bash
export OPENROUTER_API_KEY=sk-or-...
```

```json
{
  "structural": true,
  "reducer": "openrouter",
  "reducer_model": "google/gemini-2.5-flash",
  "reducer_timeout_sec": 8
}
```

Stronger (and slower/pricier) examples:

```json
"reducer_model": "anthropic/claude-sonnet-4.5"
"reducer_model": "google/gemini-2.5-pro"
"reducer_model": "qwen/qwen3-32b"
```

**Anthropic direct** still works: `"reducer": "haiku"` + `ANTHROPIC_API_KEY`.

Leave `reducer` at `"off"` unless you want to pay per fat dump. Structural + image-drop is free. Don't point this at Opus — you will spend more reducing than you save.

## Codex

Codex hooks can call the same `hooks/posttooluse.py` if you map PostToolUse in `~/.codex/hooks.json`. Replacement of tool output is first-class on Claude Code (`updatedToolOutput` / `updatedMCPToolOutput`); on Codex treat this as **tracking** unless you confirm output replacement in your CLI version.

## Privacy

Metrics rows are counts and tool names. No prompts, paths of file bodies, or stdout. Originals stay in Claude’s own transcripts.

## License

MIT
