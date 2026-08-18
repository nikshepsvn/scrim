---
description: Show local tool-output thinning and API-equivalent spend
---

# /spend

Run the local spend CLI. Do not invent numbers. Prefer `$CLAUDE_PLUGIN_ROOT` if set; otherwise find `scripts/spend.py` in the installed spend plugin.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/spend.py" --today
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/spend.py"
```

If the user asks about lifetime API-equivalent cost from Claude Code transcripts:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/spend.py" --backfill
```

Present the output as-is. Remind them Max/Ultra is a subscription — backfill dollars are list-price shadow cost, not Stripe.

If hook metrics are empty, say the plugin just started logging from this install forward, and offer `--backfill` for historical usage.
