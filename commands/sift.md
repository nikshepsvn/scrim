---
description: Show what Sift thinned and the API-equivalent token mix
---

# /sift

Run the local CLI. Do not invent numbers. Prefer `$CLAUDE_PLUGIN_ROOT`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sift.py" --today
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sift.py"
```

If they ask about lifetime API-equivalent cost from Claude Code transcripts:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sift.py" --backfill
```

Max/Ultra is a subscription. Backfill dollars are list-price shadow cost, not Stripe. Hook metrics only exist after this plugin is installed.
