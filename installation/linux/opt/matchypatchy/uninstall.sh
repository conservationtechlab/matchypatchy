#!/usr/bin/env bash
# Remove a per-user MatchyPatchy install (the folder this script lives in).
set -euo pipefail

APP_NAME="MatchyPatchy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MENU_SHORTCUT_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
[ -n "$DESKTOP_DIR" ] || DESKTOP_DIR="$HOME/Desktop"

# Safety: only proceed if this looks like an installed copy, not the unpacked package
if [ ! -f "$SCRIPT_DIR/version.txt" ] || [ ! -d "$SCRIPT_DIR/python_env" ]; then
    echo "Error: $SCRIPT_DIR does not look like an installed $APP_NAME directory."
    echo "Run the uninstaller from the install location (default: ~/.MatchyPatchy)."
    exit 1
fi

printf '%s' "Remove $APP_NAME from $SCRIPT_DIR? [y/N]: "
read -r REPLY || REPLY=""
case "$REPLY" in
    y|Y|yes|YES) ;;
    *) echo "Uninstall cancelled."; exit 0 ;;
esac

# Shortcuts (current and legacy filenames)
rm -f "$MENU_SHORTCUT_DIR/matchypatchy.desktop" "$MENU_SHORTCUT_DIR/MatchyPatchy.desktop"
rm -f "$DESKTOP_DIR/matchypatchy.desktop" "$DESKTOP_DIR/MatchyPatchy.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$MENU_SHORTCUT_DIR" >/dev/null 2>&1 || true
fi

# Icons
rm -f "$ICON_DIR"/*/apps/matchypatchy.png
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -f -t "$ICON_DIR" >/dev/null 2>&1 || true
fi

# App files last
cd "$HOME"
rm -rf "$SCRIPT_DIR"

echo "$APP_NAME was removed."
echo "Logs and settings in ~/.local/state/matchypatchy were left in place."
