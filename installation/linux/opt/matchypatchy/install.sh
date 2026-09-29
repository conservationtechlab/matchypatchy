#!/usr/bin/env bash
# Per-user install of MatchyPatchy (tarball users). The .deb does not use this.
# Usage: ./install.sh [-y|--yes]
set -euo pipefail

APP_NAME="MatchyPatchy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_VERSION="$(cat "$SCRIPT_DIR/VERSION" 2>/dev/null || echo unknown)"

INSTALL_DIR="${INSTALL_DIR:-$HOME/.MatchyPatchy}"
VERSION_FILE="$INSTALL_DIR/version.txt"
LAUNCHER_PATH="$INSTALL_DIR/launcher.sh"
UNINSTALLER_PATH="$INSTALL_DIR/uninstall.sh"
MENU_SHORTCUT_DIR="$HOME/.local/share/applications"
MENU_SHORTCUT="$MENU_SHORTCUT_DIR/matchypatchy.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
[ -n "$DESKTOP_DIR" ] || DESKTOP_DIR="$HOME/Desktop"
DESKTOP_SHORTCUT="$DESKTOP_DIR/matchypatchy.desktop"

ASSUME_YES=0
case "${1:-}" in -y|--yes) ASSUME_YES=1 ;; esac

for NEEDED in python_env launcher.sh uninstall.sh; do
    if [ ! -e "$SCRIPT_DIR/$NEEDED" ]; then
        echo "Error: $NEEDED not found in $SCRIPT_DIR"
        exit 1
    fi
done

if [ -d "$INSTALL_DIR" ] && [ "$ASSUME_YES" -eq 0 ]; then
    EXISTING_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || true)"
    if [ -n "$EXISTING_VERSION" ]; then
        echo "$APP_NAME version $EXISTING_VERSION is already installed at $INSTALL_DIR"
        printf '%s' "Update/reinstall to version $APP_VERSION? [y/N]: "
    else
        echo "$APP_NAME appears to already be installed at $INSTALL_DIR"
        printf '%s' "Reinstall version $APP_VERSION? [y/N]: "
    fi
    read -r REPLY || REPLY=""
    case "$REPLY" in
        y|Y|yes|YES) ;;
        *) echo "Installation cancelled."; exit 0 ;;
    esac
fi

mkdir -p "$INSTALL_DIR"
rm -rf "$INSTALL_DIR/python_env"
cp -R "$SCRIPT_DIR/python_env" "$INSTALL_DIR/python_env"
install -m 0755 "$SCRIPT_DIR/launcher.sh" "$LAUNCHER_PATH"
install -m 0755 "$SCRIPT_DIR/uninstall.sh" "$UNINSTALLER_PATH"
printf '%s\n' "$APP_VERSION" > "$VERSION_FILE"

# Icons into the user's icon theme, so the .desktop file can say Icon=matchypatchy
ICON_LINE="Icon=utilities-terminal"
if [ -d "$SCRIPT_DIR/icons/hicolor" ]; then
    for SIZE in 16 24 32 48 64 128 256 512; do
        SRC="$SCRIPT_DIR/icons/hicolor/${SIZE}x${SIZE}/apps/matchypatchy.png"
        [ -f "$SRC" ] || continue
        mkdir -p "$ICON_DIR/${SIZE}x${SIZE}/apps"
        cp "$SRC" "$ICON_DIR/${SIZE}x${SIZE}/apps/matchypatchy.png"
    done
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -f -t "$ICON_DIR" >/dev/null 2>&1 || true
    fi
    ICON_LINE="Icon=matchypatchy"
else
    echo "Warning: icons not found, using a generic icon."
fi

# Clean up shortcuts from older installer versions (capitalised filename)
rm -f "$MENU_SHORTCUT_DIR/MatchyPatchy.desktop" "$DESKTOP_DIR/MatchyPatchy.desktop"

mkdir -p "$MENU_SHORTCUT_DIR"
cat > "$MENU_SHORTCUT" <<DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=MatchyPatchy
Comment=Individual re-identification matching tool
Exec="$LAUNCHER_PATH"
$ICON_LINE
Terminal=false
Categories=Science;Utility;
StartupNotify=true
DESKTOP_EOF
chmod 755 "$MENU_SHORTCUT"

if [ -d "$DESKTOP_DIR" ]; then
    cp "$MENU_SHORTCUT" "$DESKTOP_SHORTCUT"
    chmod 755 "$DESKTOP_SHORTCUT"
    if command -v gio >/dev/null 2>&1; then
        gio set "$DESKTOP_SHORTCUT" metadata::trusted true 2>/dev/null || true
    fi
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$MENU_SHORTCUT_DIR" >/dev/null 2>&1 || true
fi

echo "$APP_NAME $APP_VERSION installed to: $INSTALL_DIR"
echo "Menu shortcut: $MENU_SHORTCUT"
[ -f "$DESKTOP_SHORTCUT" ] && echo "Desktop shortcut: $DESKTOP_SHORTCUT"
echo "To uninstall, run: $UNINSTALLER_PATH"
