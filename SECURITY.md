# Security

- Hooks always exit 0. A bug must not block the agent or swallow a tool result.
- Default path sends **no** tool output to a third party. Only Claude’s normal provider call happens.
- `~/.sift/metrics.jsonl` stores counts and tool names. No stdout, no file bodies.
- `reducer_api_key` and `.env` must never be committed. The repo gitignores `.env*`.
- Opt-in reducer sends truncated tool output (up to `reducer_max_bytes`) to OpenRouter or Anthropic. Treat that like any other LLM API: no secrets in dumps you would not paste into a chat.
- Do not enable `thin_reads` unless you accept the model seeing a truncated source file.
