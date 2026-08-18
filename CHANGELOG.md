# Changelog

## 0.8.0

The public release.

- `scrim statusline` — a line for Claude Code's `statusLine` slot: model, context %, real cost from the harness, plus this session's tool MB, thinned MB, and compaction count from Scrim's own metrics.
- The session-MB warning now also fires **before** a turn (`UserPromptSubmit`, once per session), not only at Stop where it arrives too late to change anything.
- `scrim get` logs retrievals (`kind: retrieve`); the report shows pull counts — if stashes are never pulled, the thinning provably loses nothing anyone wanted.
- Compaction trigger recorded correctly on Claude Code (`compaction_reason`; Codex sends `trigger`).

New:

- `scrim days [n]` — daily trend table: Claude $, Codex $, turns, tool MB in→out per local day (default 7).
- Compaction tracking: `PreCompact` is logged (`kind: compact`), and `/scrim` reports the count — each compaction is a window that overflowed.
- `codex_block_thin` (opt-in): on Codex, thin builtin output through the shipped `decision:"block"` replacement lever, with a "tool ran successfully" preface and the usual stash.
- `rg_max_columns` (default 300): unbounded `rg` also gets `--max-columns` — one minified-JS hit can be a 200 KB line that `--max-count` can't touch.
- `hooks/subagent.py` → `hooks/events.py` (now logs swarms *and* compactions).

Codex, first-class (verified live against codex-cli 0.146.1, which ships stable Claude-format hooks):

- `make codex-hooks` installs `codex/hooks.json` (PreToolUse, PostToolUse, Subagent, Stop) into `~/.codex/hooks.json`; `codex/README.md` documents the trust step and exactly what works.
- Argv commands (`["bash", "-lc", "pytest -q"]`) classify and constrain like their string forms; Codex's code-mode `exec` tool classifies by its embedded command; `{"output": …}` responses keep their shape on rewrite.
- Codex's PostToolUse schema rejects `updatedToolOutput` (`additionalProperties: false`), so on Codex (detected via `turn_id`) the hook goes observe-only for builtin tools instead of logging thins that never reached the model. MCP rewrites still emit `updatedMCPToolOutput` for when Codex starts applying it.
- `/scrim` and `--backfill` grow a **Codex** usage block parsed from `~/.codex/sessions` rollouts (per-model, cached-input share, GPT list prices); `doctor` reports the rollout count.

Filter quality:

- Retrieving a stash (`scrim get`) is exempt from thinning — it used to re-shrink and re-stash the very blob the agent asked to recover.
- Signal-line thinning keeps stack-trace frames (Python `File "…"`, JS `at …`, indented context) under each FAIL/Error line, not just the header and exception.
- Log templating (`drain`) appends the raw last lines — the crash is usually at the end, and count-sorted templates lost time order.

Identity redesign: lamp-through-cloth mark, single banner lockup, and a before/after diagram (`assets/diagram.svg`) replacing the ASCII box. README restructured — what / why / install first, reducer and Codex parked below.

## 0.7.0

CLI grows up: `doctor`, `kinds`, `stashes`, `prune`, `--json`, `--version`.

Correctness:

- Fable 5 list price fixed ($10/$50 — was counted at Sonnet rates, hiding ~3× of its shadow cost).
- "Today" is now the local calendar day, not UTC, for both transcripts and hook metrics.
- Transcript parsing dedups API retries (same message id + request id).
- Search thinning no longer loses FAIL/Error hits to the omitted middle, and a slice bug that could make search output *larger* than the input is fixed. Rewrites that would not shrink the result are dropped entirely.
- The Stop-hook MB warning now measures *this session*, not every session today. `warn_session_usd` is implemented (session shadow-cost warning).
- `PreToolUse` never rewrites mutating `find` (`-exec`/`-delete`/…), redirects, or `find`/`ls` appearing inside string arguments; `rg` already bounded by `-l`/`-c`/`--max-count` is left alone.
- Stash ids no longer collide for same-second puts; the stash index compacts itself.

Robustness: hooks fail open even on import errors, a missing hook file, or a Python 2 `python`; an unwritable data dir skips stash/metrics but still delivers the thinned output; reducer catches all transport errors and prunes its cache after 30 days. Config values are type-checked (bad values fall back to defaults, `--config`/`doctor` show warnings). `SCRIM_DATA_DIR` overrides the data dir; tests are hermetic. Hooks resolve the plugin root from their own path, so Codex-style direct invocation works without env vars. `--today` skips transcripts untouched since before the day (17s → <1s).

## 0.6.0

Rebrand to **Scrim**. Mark, banner, and product README.

## 0.5.0

Haiku subagents: `scrim-analyst`, `scrim-retrieve`. Swarm count on `SubagentStart`.

## 0.4.0

Transcript observability, `PreToolUse` caps, stash / `scrim get`.

## 0.3.0

Kind-aware thinning, structural JSON/HTML, optional OpenRouter reducer.

## 0.1.0

First hook: track + thin tests and screenshots.
