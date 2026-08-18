---
description: Cost and tool-output report. Retrieve a stashed original with scrim get.
---

# /scrim

Do not invent numbers. **Delegate to the `scrim-analyst` subagent** (Haiku) instead of analyzing transcripts yourself.

1. Spawn `scrim-analyst`, or run the CLI (plugin root is `$CLAUDE_PLUGIN_ROOT` when set):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrim.py" --today
```

2. If that fails, Read `~/.scrim/last.txt`.

3. If they need an omitted original, spawn `scrim-retrieve` with the stash id. Do not Read the blob in the parent session.

4. Lifetime transcript usage: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrim.py" --backfill`

Max/Ultra is a subscription. Dollar figures are list-price shadow cost.
