#!/bin/sh
# Resolve python and plugin root. Always fail-open if the interpreter is missing.
ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [ -z "$ROOT" ]; then
  ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
fi
export CLAUDE_PLUGIN_ROOT="$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo '{}'
  exit 0
fi

exec "$PY" "$ROOT/hooks/$1"
