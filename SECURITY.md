# Security

- Hooks always exit 0. A bug must not block the agent or swallow a tool result.
- Default path sends **no** tool output to a third party. Only Claude’s normal provider call happens.
- `~/.scrim/metrics.jsonl` stores counts and tool names. No stdout, no file bodies.
- `~/.scrim/blobs/` **does** store the full text of thinned tool output (that is the point of `scrim get`), locally, for `stash_ttl_days` (default 7). If your tool output can contain secrets, set `"stash": false` or shorten the TTL. Blobs never leave the machine.
- `reducer_api_key` and `.env` must never be committed. The repo gitignores `.env*`.
- Opt-in reducer sends truncated tool output (up to `reducer_max_bytes`) to OpenRouter or Anthropic. Treat that like any other LLM API: no secrets in dumps you would not paste into a chat.
- Do not enable `thin_reads` unless you accept the model seeing a truncated source file.
