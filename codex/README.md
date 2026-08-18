# Codex

If your Codex build has hooks enabled, point PostToolUse at the same script:

```json
{
  "PostToolUse": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "python3 /ABS/PATH/TO/scrim/hooks/posttooluse.py",
          "timeout": 8
        }
      ]
    }
  ]
}
```

Stdin shape is close enough (tool_name, tool_input, tool_response, session_id). Tracking will work — the hook finds the `scrim` package from its own path, so no `CLAUDE_PLUGIN_ROOT` or `PYTHONPATH` is needed. Do not assume `updatedToolOutput` is honored until you test it.
