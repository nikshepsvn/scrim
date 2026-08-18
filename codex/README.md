# Codex

Codex CLI (0.146+) ships **stable lifecycle hooks** in Claude Code's exact
`hooks.json` format — same events, same stdin JSON (`tool_name`, `tool_input`,
`tool_response`, `tool_use_id`, `session_id`, plus a Codex-only `turn_id`).
Verified against codex-cli 0.146.1.

## Install

```bash
make codex-hooks     # writes ~/.codex/hooks.json pointed at this checkout
```

If `~/.codex/hooks.json` already exists, merge [`hooks.json`](hooks.json) into
it by hand (replace `SCRIM_ROOT` with this repo's absolute path). Per-repo
instead: put the same content in `<repo>/.codex/hooks.json`, or use
`[[hooks.PreToolUse]]` tables in `config.toml`.

**Trust:** Codex refuses to run an unreviewed hook. Run `/hooks` inside the
TUI once to trust the five Scrim entries (trust is recorded against the hook's
hash, so editing a hook re-prompts). For non-interactive runs there is
`codex exec --dangerously-bypass-hook-trust`.

The `hooks` feature flag is on by default on 0.146+ (`codex features list` to
check); older builds need `[features]` `hooks = true` in `config.toml`. Hooks
are reported unavailable on Windows. Managed enterprise configs can suppress
user hooks entirely (`allow_managed_hooks_only`).

## What works on Codex

| Job | Status |
|---|---|
| **See** — bytes per tool/kind, stash, `/scrim` report | ✅ works (verified live) |
| **Usage $** — `scrim.py --today` reads `~/.codex/sessions` rollouts | ✅ works, shows a `Codex` block |
| **Prevent** — PreToolUse `updatedInput` caps `ls -R` / `find` / `rg` | ⚠️ fires for direct `shell`/`exec_command` dispatches, but Code Mode `exec` (the default JS surface) never emits PreToolUse — known bug, [#23411](https://github.com/openai/codex/issues/23411)/[#20204](https://github.com/openai/codex/issues/20204) |
| **Thin** — neutral PostToolUse rewrite of builtin output | ❌ not shipped: `updatedToolOutput` PR [#20703](https://github.com/openai/codex/pull/20703) closed stale; tracked in [#34895](https://github.com/openai/codex/issues/34895) |
| **Thin via block** — opt-in `codex_block_thin` | ✅ verified live: a 5,092-byte listing reached model context as 762 bytes, stash pointer included, and the model still answered correctly from the omitted-count marker |
| **Thin MCP** — `updatedMCPToolOutput` | ⏳ "parsed but not supported yet" (0.146); Scrim already emits it, so it lights up when Codex ships it. MCP hooks themselves fire (`mcp__server__tool` names — Scrim's classifier already matches) |

Scrim detects Codex by the `turn_id` field and goes observe-only where a
rewrite cannot reach the model — it never reports bytes as thinned that Codex
didn't actually drop (`kinds` and `metrics.jsonl` show what really happened).

Two native mitigations while rewrite is missing: `tool_output_token_limit` in
`config.toml` caps what any tool output costs in history, and code-mode `exec`
caps its own output (`max_output_tokens`, spill-to-store). Scrim's remaining
edge on Codex is *selective* trimming — knowing a FAIL line from a PASS line —
which a flat token cap cannot do.

One shipped replacement path exists: PostToolUse `decision: "block"` + `reason`
replaces the tool result the model sees with your feedback text (merged PR
[#18888](https://github.com/openai/codex/pull/18888) added regression coverage
for exactly this). The replacement is framed as feedback rather than a neutral
rewrite, so it is **opt-in**: set `"codex_block_thin": true` in
`~/.scrim/config.json` and Scrim will thin builtin output on Codex through the
block lever. Codex's code-mode wrapper labels the replacement "Script error:",
so Scrim prefixes the view with "the tool ran successfully" — in live testing
the model neither retried nor mistook the command for a failure. The full
original is stashed as usual.

## Notes

- Codex normalizes hook input toward Claude shapes (code-mode `exec_command`
  arrives as `tool_name: "Bash"` with a string `command`), and Scrim also
  handles the raw `shell` argv form `["bash", "-lc", "…"]`.
- Plugin-bundled hooks get `CLAUDE_PLUGIN_ROOT` as a compatibility alias, so
  `hooks/run.sh` works unchanged if Scrim is ever packaged as a Codex plugin
  (`plugin.json` → `"hooks": "./hooks.json"`).
- Hook `additionalContext` over ~2,500 tokens is spilled to disk by Codex;
  Scrim's notes are ≤500 bytes.
