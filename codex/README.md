# Codex

If your Codex build has hooks enabled, point PostToolUse at the same script:

```json
{
  "PostToolUse": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "python3 /ABS/PATH/TO/sift/hooks/posttooluse.py",
          "timeout": 8
        }
      ]
    }
  ]
}
```

Stdin shape is close enough (tool_name, tool_input, tool_response, session_id). Tracking will work. Do not assume `updatedToolOutput` is honored until you test it.
