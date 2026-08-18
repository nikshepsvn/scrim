---
name: scrim
description: Report what Scrim thinned from tool output and API-equivalent token mix. Use when the user runs /scrim, or asks about quota, context burn, or tool-output size.
---

# Scrim

Run the CLI. Do not invent numbers.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrim.py" --today
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrim.py"
```

Omitted original:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrim.py" get <id> [start-end]
```

Lifetime shadow $ from transcripts:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrim.py" --backfill
```

Health check / per-kind breakdown / stash listing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrim.py" doctor
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrim.py" kinds --today
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrim.py" stashes
```

Remind them Max/Ultra is a subscription. Backfill dollars are list-price, not Stripe. "Today" is their local calendar day.
