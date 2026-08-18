# How it works

```
PreToolUse
    cap ls -R / find / tree / rg before they run
    never touch pipes, redirects, or mutating find
    hint: skip another Chrome screenshot
         │
         ▼
    tool runs
         │
         ▼
PostToolUse  (fail-open)
    classify → thin → stash original → metrics
         │
         ▼
Stop
    write ~/.scrim/last.txt  (usage + tools)
    warn if THIS session dumped ≥2 MB of tool results
    warn if session shadow cost passed warn_session_usd
```

`/scrim` should spawn **scrim-analyst** (Haiku). Stash pulls go through **scrim-retrieve** so the parent never loads the blob.

`SubagentStart` / `SubagentStop` count swarms and inject a hint past `max_open_subagents`. Claude Code does not let a hook cancel a spawn. `PreCompact` is logged too — each compaction is a window that overflowed, and `/scrim` reports the count.

The hook cannot change the session model. Routing Opus → Haiku is a different process.

## Fail-open

Any parse error, timeout, reducer miss, or even a broken install (missing interpreter, missing hook file, import error) prints `{}` and exits 0. Claude sees the original tool result. `scrim.py doctor` checks the whole chain.

Harness stubs (`<persisted-output>`) are left alone. If a rewrite would not actually be smaller than the original, Scrim leaves the original alone too.

## Observability

Usage comes from `~/.claude/projects` transcripts: per-model tokens, cache-read share, and list-price shadow dollars (Max/Ultra is a subscription; this is quota shape, not a card charge). Retried API requests (same message id + request id) are counted once. "Today" is the local calendar day, not UTC.

Tool metrics come from the hooks themselves: bytes in/out per tool and per kind, thinned counts, stash ids. `metrics.jsonl` stores counts and names, never payloads.

## Why not gzip

Tokenizers count text. A compressed blob is unreadable and still billed if you send it. Scrim emits a **shorter string the model can use**.
