#!/usr/bin/env bash
set -euo pipefail

APP_NAME="MatchyPatchy"
APP_VERSION="0.1.4"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.MatchyPatchy}"
VERSION_FILE="$INSTALL_DIR/version.txt"
LAUNCHER_PATH="$INSTALL_DIR/launcher.sh"
UNINSTALLER_PATH="$INSTALL_DIR/uninstall.sh"
MENU_SHORTCUT_DIR="$HOME/.local/share/applications"
MENU_SHORTCUT="$MENU_SHORTCUT_DIR/MatchyPatchy.desktop"
DESKTOP_SHORTCUT="$HOME/Desktop/MatchyPatchy.desktop"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_PYTHON_ENV="$SCRIPT_DIR/python_env"
SOURCE_LAUNCHER="$SCRIPT_DIR/launcher.sh"
SOURCE_UNINSTALLER="$SCRIPT_DIR/uninstall.sh"

if [ -d "$INSTALL_DIR" ]; then
  EXISTING_VERSION=""
  if [ -f "$VERSION_FILE" ]; then
    EXISTING_VERSION="$(cat "$VERSION_FILE")"
  fi

  if [ -n "$EXISTING_VERSION" ]; then
    printf '%s\n' "$APP_NAME version $EXISTING_VERSION is already installed at $INSTALL_DIR"
    printf '%s' "Update/reinstall to version $APP_VERSION? [y/N]: "
  else
    printf '%s\n' "$APP_NAME appears to already be installed at $INSTALL_DIR"
    printf '%s' "Reinstall version $APP_VERSION? [y/N]: "
  fi

  read -r REPLY
  case "$REPLY" in
    y|Y|yes|YES) ;;
    *)
      echo "Installation cancelled."
      exit 0
      ;;
  esac
fi

if [ ! -d "$SOURCE_PYTHON_ENV" ]; then
  echo "Error: bundled python_env not found at: $SOURCE_PYTHON_ENV"
  exit 1
fi

if [ ! -f "$SOURCE_LAUNCHER" ]; then
  echo "Error: launcher.sh not found at: $SOURCE_LAUNCHER"
  exit 1
fi

if [ ! -f "$SOURCE_UNINSTALLER" ]; then
  echo "Error: uninstall.sh not found at: $SOURCE_UNINSTALLER"
  exit 1
fi

mkdir -p "$INSTALL_DIR"
rm -rf "$INSTALL_DIR/python_env"
cp -R "$SOURCE_PYTHON_ENV" "$INSTALL_DIR/python_env"
cp "$SOURCE_LAUNCHER" "$LAUNCHER_PATH"
cp "$SOURCE_UNINSTALLER" "$UNINSTALLER_PATH"
chmod +x "$LAUNCHER_PATH" "$UNINSTALLER_PATH"

printf '%s\n' "$APP_VERSION" > "$VERSION_FILE"

mkdir -p "$MENU_SHORTCUT_DIR"

ICON_PATH=""
for CANDIDATE in \
  "$INSTALL_DIR/python_env/lib/site-packages/matchypatchy/assets/graphics/desktop_icon.png" \
  "$INSTALL_DIR/python_env/Lib/site_packages/matchypatchy/assets/graphics/desktop_icon.ico" \
  "$INSTALL_DIR/python_env/Lib/site-packages/matchypatchy/assets/graphics/desktop_icon.ico"
do
  if [ -f "$CANDIDATE" ]; then
    ICON_PATH="$CANDIDATE"
    break
  fi
done

if [ -n "$ICON_PATH" ]; then
  ICON_LINE="Icon=$ICON_PATH"
else
  ICON_LINE="Icon=utilities-terminal"
fi

cat > "$MENU_SHORTCUT" <<DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=MatchyPatchy
Exec=$LAUNCHER_PATH
$ICON_LINE
Terminal=true
Categories=Utility;
DESKTOP_EOF
chmod 755 "$MENU_SHORTCUT"

if [ -d "$HOME/Desktop" ]; then
  cp "$MENU_SHORTCUT" "$DESKTOP_SHORTCUT"
  chmod 755 "$DESKTOP_SHORTCUT"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$MENU_SHORTCUT_DIR" >/dev/null 2>&1 || true
fi

echo "$APP_NAME $APP_VERSION installed to: $INSTALL_DIR"
echo "Menu shortcut: $MENU_SHORTCUT"
if [ -f "$DESKTOP_SHORTCUT" ]; then
  echo "Desktop shortcut: $DESKTOP_SHORTCUT"
fi
echo "To uninstall, run: $UNINSTALLER_PATH"
