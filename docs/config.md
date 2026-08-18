# Config reference

File: `~/.scrim/config.json`  
Template: [`config.example.json`](../config.example.json)

On first run, `~/.sift` or `~/.spend` is renamed to `~/.scrim` if the new path does not exist.

Unknown keys are ignored. Missing keys use defaults.

| Key | Default | Meaning |
|---|---|---|
| `shrink` | `true` | Master switch for rewriting output |
| `strip_images` | `true` | Drop MCP `type=image` blocks |
| `thin_tests` | `true` | Keep FAIL/Error lines from test/lint dumps |
| `thin_reads` | `false` | Never touch `Read` / `Edit` unless true |
| `structural` | `true` | JSON/NDJSON/HTML rewrite |
| `bash_cap_bytes` | `48000` | Head+tail fallback for fat bash |
| `search_keep_lines` | `40` | Grep head |
| `list_keep_lines` | `80` | `ls` / Glob head |
| `web_cap_bytes` | `16000` | WebFetch/Search cap |
| `mcp_text_cap_bytes` | `12000` | MCP leftover text after images |
| `warn_session_usd` | `40` | Reserved |
| `reducer` | `"off"` | `"off"` \| `"openrouter"` \| `"haiku"` |
| `reducer_model` | `inception/mercury-2` | OpenRouter slug, or Anthropic model id |
| `reducer_min_bytes` | `8000` | Skip reducer below this |
| `reducer_max_bytes` | `120000` | Truncate reducer input |
| `reducer_max_tokens` | `4096` | Completion budget (Mercury needs this on fat dumps) |
| `reducer_timeout_sec` | `20` | HTTP timeout |
| `reducer_api_key` | `""` | Optional if env is unset. Do not commit. |
| `pretool` | `true` | Cap unbounded `ls`/`rg`/`Grep` before they run |
| `ls_max_lines` | `200` | `head -n` for `ls -R` / `find` / `tree` |
| `grep_max_count` | `80` | `Grep.head_limit` and `rg --max-count` |
| `stash` | `true` | Keep omitted originals in `~/.scrim/blobs/` |
| `stash_ttl_days` | `7` | Delete older blobs |
| `stash_max_mb` | `512` | Cap stash dir |
| `session_tool_mb_warn` | `2` | Stop-hook warning threshold |
| `max_open_subagents` | `8` | Warn (do not block) when this many are already open |

Env, in order: `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY`, then `SPEND_REDUCER_KEY` / `SCRIM_REDUCER_KEY`, then `reducer_api_key`.
