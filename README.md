# spend

Local **spend tracking** and **tool-output thinning** for [Claude Code](https://code.claude.com). Optional Codex hooks.

No cloud. No API keys. Tool payloads never leave the machine. Hooks **fail open**.

This is not Codag. It does not change your model. On Claude Max it will not lower Stripe — it lowers **quota burn** and shows where the session went.

## What it does

| | |
|---|---|
| **Track** | Every tool call: name, bytes in/out, whether it was thinned. `~/.spend/metrics.jsonl` |
| **Thin** | Drop Chrome/Playwright **image** blocks. Keep FAIL lines from fat pytest/jest. Cap huge bash. |
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
  "bash_cap_bytes": 48000,
  "warn_session_usd": 40
}
```

Set `"shrink": false` to log only.

## Codex

Codex hooks can call the same `hooks/posttooluse.py` if you map PostToolUse in `~/.codex/hooks.json`. Replacement of tool output is first-class on Claude Code (`updatedToolOutput` / `updatedMCPToolOutput`); on Codex treat this as **tracking** unless you confirm output replacement in your CLI version.

## Privacy

Metrics rows are counts and tool names. No prompts, paths of file bodies, or stdout. Originals stay in Claude’s own transcripts.

## License

MIT
