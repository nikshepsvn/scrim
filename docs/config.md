# Config reference

File: `~/.scrim/config.json`  
Template: [`config.example.json`](../config.example.json)

On first run, `~/.sift` or `~/.spend` is renamed to `~/.scrim` if the new path does not exist. Set `SCRIM_DATA_DIR` to move the data dir somewhere else entirely (tests use this).

Unknown keys are ignored. Missing keys use defaults. A value of the wrong type falls back to the default. `scrim.py --config` prints the effective config and warns about anything it ignored; `scrim.py doctor` includes the same check.

| Key | Default | Meaning |
|---|---|---|
| `shrink` | `true` | Master switch for rewriting output |
| `strip_images` | `true` | Drop MCP `type=image` blocks |
| `thin_tests` | `true` | Keep FAIL/Error lines from test/lint dumps. `false` passes test output through untouched |
| `thin_reads` | `false` | Never touch `Read` / `Edit` unless true |
| `structural` | `true` | JSON/NDJSON/HTML rewrite |
| `bash_cap_bytes` | `48000` | Head+tail fallback for fat bash |
| `search_keep_lines` | `40` | Grep head. FAIL/Error hits in the omitted middle are appended anyway |
| `list_keep_lines` | `80` | `ls` / Glob head |
| `web_cap_bytes` | `16000` | WebFetch/Search cap |
| `mcp_text_cap_bytes` | `12000` | MCP leftover text after images |
| `warn_session_usd` | `40` | Stop-hook warning when the session's list-price shadow cost passes this. `0` disables |
| `reducer` | `"off"` | `"off"` \| `"openrouter"` \| `"haiku"` |
| `reducer_model` | `inception/mercury-2` | OpenRouter slug, or Anthropic model id |
| `reducer_min_bytes` | `8000` | Skip reducer below this |
| `reducer_max_bytes` | `120000` | Truncate reducer input |
| `reducer_max_tokens` | `4096` | Completion budget (Mercury needs this on fat dumps) |
| `reducer_timeout_sec` | `20` | HTTP timeout |
| `reducer_api_key` | `""` | Optional if env is unset. Do not commit. |
| `pretool` | `true` | Cap unbounded `ls`/`rg`/`Grep` before they run |
| `ls_max_lines` | `200` | `head -n` for recursive `ls` / `find` / `tree`. Pipes, redirects, and mutating `find` (`-exec`/`-delete`/…) are never rewritten |
| `grep_max_count` | `80` | `Grep.head_limit` and `rg --max-count` |
| `rg_max_columns` | `300` | `rg --max-columns` — one minified-JS hit can be a 200 KB line. `0` disables |
| `codex_block_thin` | `false` | On Codex, thin builtin output via `decision:"block"` (its only shipped replacement lever). The replacement is framed as feedback, so this is opt-in |
| `stash` | `true` | Keep omitted originals in `~/.scrim/blobs/` |
| `stash_ttl_days` | `7` | Delete older blobs |
| `stash_max_mb` | `512` | Cap stash dir |
| `session_tool_mb_warn` | `2` | Stop-hook warning once *this session's* tool results pass this many MB |
| `max_open_subagents` | `8` | Warn (do not block) when this many are already open |

"Today" everywhere means the machine's **local calendar day** — timestamps on disk are UTC and get converted before comparing.

Env, in order: `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY`, then `SCRIM_REDUCER_KEY` / `SPEND_REDUCER_KEY`, then `reducer_api_key`.

Reducer cache (`~/.scrim/reducer-cache/`) self-prunes after 30 days. `metrics.jsonl` grows until you run `scrim.py prune [days]` (default keeps 90 days); `doctor` warns past 20 MB.
