---
name: spend
description: Report local Claude Code tool-output thinning and API-equivalent spend. Use when the user asks /spend, about quota, token burn, or what was thinned.
---

# spend

Run the CLI. Do not invent numbers.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/spend.py" --today
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/spend.py"
```

Lifetime shadow $ from transcripts:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/spend.py" --backfill
```

Remind them Max/Ultra is a subscription. Backfill dollars are list-price, not Stripe. Hook metrics only exist after this plugin is installed.
