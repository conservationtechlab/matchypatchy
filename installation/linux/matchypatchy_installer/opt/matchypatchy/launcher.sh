#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/matchypatchy.log"
PYTHON_BIN="$SCRIPT_DIR/python_env/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$SCRIPT_DIR/python_env/python"
fi

mkdir -p "$SCRIPT_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

cd "$SCRIPT_DIR"

echo "=================================================="
echo "MatchyPatchy launcher started: $(date)"
echo "Install directory: $SCRIPT_DIR"

RC=0
if [ ! -x "$PYTHON_BIN" ]; then
  echo "Error: Python executable not found in bundled environment."
  echo "Expected: $SCRIPT_DIR/python_env/bin/python"
  RC=1
else
  "$PYTHON_BIN" -m matchypatchy || RC=$?
fi

echo
echo "MatchyPatchy exited with code: $RC"
read -r -p "Press Enter to close this window..."
exit "$RC"
