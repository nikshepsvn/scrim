# How it works

```
PreToolUse
    cap ls -R / find / rg before they run
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
    warn if this session dumped ≥2 MB
```

`/scrim` should spawn **scrim-analyst** (Haiku). Stash pulls go through **scrim-retrieve** so the parent never loads the blob.

`SubagentStart` / `SubagentStop` count swarms and inject a hint past `max_open_subagents`. Claude Code does not let a hook cancel a spawn.

The hook cannot change the session model. Routing Opus → Haiku is a different process.

## Fail-open

Any parse error, timeout, or reducer miss prints `{}` and exits 0. Claude sees the original tool result.

Harness stubs (`<persisted-output>`) are left alone.

## Why not gzip

Tokenizers count text. A compressed blob is unreadable and still billed if you send it. Scrim emits a **shorter string the model can use**.
