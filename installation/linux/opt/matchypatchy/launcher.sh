#!/usr/bin/env bash
# Launch MatchyPatchy from its bundled Python environment.
# Works from /opt/matchypatchy (.deb) and ~/.MatchyPatchy (per-user install).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/python_env/bin/python"

# The app writes matchypatchy.log into its working directory, and /opt is
# read-only for normal users, so run from a per-user state directory.
STATE_DIR="${MATCHYPATCHY_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/matchypatchy}"
mkdir -p "$STATE_DIR"
cd "$STATE_DIR" || exit 1

LOG_FILE="$STATE_DIR/launcher.log"
if [ -f "$LOG_FILE" ] && [ "$(stat -c %s "$LOG_FILE" 2>/dev/null || echo 0)" -gt 5242880 ]; then
    mv -f "$LOG_FILE" "$LOG_FILE.1"
fi
exec > >(tee -a "$LOG_FILE") 2>&1

export PYTHONNOUSERSITE=1   # ignore ~/.local packages that could shadow the bundle

echo "=================================================="
echo "MatchyPatchy launcher started: $(date)"
echo "Install directory: $SCRIPT_DIR"

RC=0
if [ ! -x "$PYTHON_BIN" ]; then
    echo "Error: bundled Python not found: $PYTHON_BIN"
    RC=1
else
    "$PYTHON_BIN" -m matchypatchy "$@" || RC=$?
fi

echo "MatchyPatchy exited with code: $RC"

# Only pause when started from a terminal, so menu launches don't hang.
if [ "$RC" -ne 0 ] && [ -t 0 ]; then
    read -r -p "Press Enter to close this window..."
fi
exit "$RC"
