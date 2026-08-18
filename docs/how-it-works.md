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
    write ~/.sift/last.txt  (usage + tools)
    warn if this session dumped ≥2 MB
```

`/sift` should spawn **sift-analyst** (Haiku). Stash pulls go through **sift-retrieve** so the parent never loads the blob.

`SubagentStart` / `SubagentStop` count swarms and inject a hint past `max_open_subagents`. Claude Code does not let a hook cancel a spawn.

The hook cannot change the session model. Routing Opus → Haiku is a different process.

## Fail-open

Any parse error, timeout, or reducer miss prints `{}` and exits 0. Claude sees the original tool result.

Harness stubs (`<persisted-output>`) are left alone.

## Why not gzip

Tokenizers count text. A compressed blob is unreadable and still billed if you send it. Sift emits a **shorter string the model can use**.
