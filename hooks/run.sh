#!/bin/sh
# Fail-open launcher: a missing interpreter, argument, or hook file must
# print {} and exit 0 — a non-zero exit could block the tool call.
ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [ -z "$ROOT" ]; then
  ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
fi
export CLAUDE_PLUGIN_ROOT="$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

HOOK="$ROOT/hooks/$1"
if [ -z "$1" ] || [ ! -f "$HOOK" ]; then
  echo '{}'
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
  # bare `python` can still be 2.x on old systems
  if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    echo '{}'
    exit 0
  fi
else
  echo '{}'
  exit 0
fi

exec "$PY" "$HOOK"
