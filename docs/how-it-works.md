# How it works

```
tool runs
    │
    ▼
PostToolUse hook  (≤25s, always exit 0)
    │
    ├─ classify(name, command)
    ├─ drop MCP images
    ├─ kind filter (tests / logs / grep / ls / bash / web)
    ├─ structural JSON/HTML rewrite
    ├─ optional OpenRouter reducer (if still fat)
    ├─ append ~/.spend/metrics.jsonl
    └─ return updatedToolOutput / updatedMCPToolOutput
           or {} on any error  →  original bytes
```

The hook cannot change the session model. Routing Opus → Haiku is a different process (`claude-code-router`).

`Stop` only adds a one-line warning if this session’s tool results exceeded 2 MB.

## Fail-open

Any parse error, timeout, or reducer miss prints `{}` and exits 0. Claude sees the original tool result.

Already-spilled harness stubs (`<persisted-output>`) are left alone.

## Why not gzip

Tokenizers count text. A zstd blob is unreadable and still billed if you send it. Compression here means a **shorter string the model can use**.
