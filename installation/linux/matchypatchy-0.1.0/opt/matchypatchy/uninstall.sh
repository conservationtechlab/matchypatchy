#!/usr/bin/env bash
set -euo pipefail

APP_NAME="MatchyPatchy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MENU_SHORTCUT="$HOME/.local/share/applications/MatchyPatchy.desktop"
DESKTOP_SHORTCUT="$HOME/Desktop/MatchyPatchy.desktop"

printf '%s' "Remove $APP_NAME from $SCRIPT_DIR? [y/N]: "
read -r REPLY
case "$REPLY" in
  y|Y|yes|YES) ;;
  *)
    echo "Uninstall cancelled."
    exit 0
    ;;
esac

rm -f "$MENU_SHORTCUT"
rm -f "$DESKTOP_SHORTCUT"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

cd "$HOME"
rm -rf "$SCRIPT_DIR"

echo "$APP_NAME was removed."
