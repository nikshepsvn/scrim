---
name: sift
description: Report what Sift thinned from tool output and API-equivalent token mix. Use when the user runs /sift, or asks about quota, context burn, or tool-output size.
---

# Sift

Run the CLI. Do not invent numbers.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sift.py" --today
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sift.py"
```

Lifetime shadow $ from transcripts:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sift.py" --backfill
```

Remind them Max/Ultra is a subscription. Backfill dollars are list-price, not Stripe.
