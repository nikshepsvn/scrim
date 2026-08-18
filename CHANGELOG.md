# Changelog

## Unreleased

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
