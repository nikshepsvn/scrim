---
description: Cost and tool-output report. Retrieve a stashed original with sift get.
---

# /sift

Do not invent numbers.

1. Run the CLI (plugin root is `$CLAUDE_PLUGIN_ROOT` when set):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sift.py" --today
```

2. If that fails, Read `~/.sift/last.txt`.

3. If the user asks for an omitted original: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sift.py" get <id> [start-end]`

4. Lifetime transcript usage: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sift.py" --backfill`

Max/Ultra is a subscription. Dollar figures are list-price shadow cost.
