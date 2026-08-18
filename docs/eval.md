# Eval notes

Replay of the deterministic filter on local + public traces, and live OpenRouter calls for the optional reducer. Not a published benchmark.

## Deterministic filter (no model)

| Dataset | Calls | Byte save | Notes |
|---|---:|---:|---|
| This machine’s Claude Code | 28,994 | 47% | Almost all Chrome images (104→3 MB). Tests 0.2 MB. |
| This machine’s Codex | 5,159 | 14% | Fat bash, few tests. |
| OpenHands SFT | 8,299 | 68% | SWE-bench-style `execute_bash`. |
| SWE-smith shard | 34,804 | 17% | Mostly file *views* we refuse to touch. |

Zero dropped `FAIL`/`AssertionError` on Claude Code tests. Grep head/tail can hide a `FAIL` hit in the omitted middle; the filter now also keeps signal lines on search.

Shadow $ of those bytes is small versus Opus cache-reread of the prefix. The filter is for **window hygiene**, not a 75% bill cut.

## OpenRouter reducers (same extract prompt)

| Model | Synth extract | 40 KB `ls` | Use? |
|---|---|---|---|
| `inception/mercury-2` @ 4096 tok | Perfect + INFO count | First/last 25, ~3s | **Yes, opt-in** |
| Mercury @ 1024 tok | Perfect | Empty / `length` | No |
| `thinkingmachines/inkling` @ 4096 | Perfect (after 1.6k reasoning) | Empty — 4k reasoning, no `content` | No |
| `morph/morph-v3-fast` | Reprints the dump | Reprints | No |
| `morph/morph-v3-large` | Drops PASS, keeps INFO spam | Photocopy, 16s | No |
| `google/gemini-2.5-flash` | (not re-run here; chat model, safe backup) | | Backup |

Prompt variants did not change Morph’s output. Inkling can consume an arbitrary reasoning budget. Mercury-2 is the only one of this set that behaves like a reducer at hook latency and price.
