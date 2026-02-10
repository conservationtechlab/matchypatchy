#!/usr/bin/env bash
set -euo pipefail

# Installer for MatchyPatchy (merged, XDG-aware)
# - Moves packaged assets into XDG data dir (~/.local/share by default)
# - Creates a venv at XDG_DATA_HOME/matchypatchy/envs/mp-lite and installs the package there
# - Installs a launcher script and .desktop entry, copies icon into hicolor icon theme,
#   and creates a symlink in ~/.local/bin for easy CLI invocation.
#
# Usage: ./install.command
# If you run this script from a packaged directory, include the `assets/` folder next to it.
#
# Author/maintainer: adapted for user request

APP_NAME="matchypatchy"

# Respect XDG Base Directory spec with sensible fallbacks
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
LOCAL_BIN="${LOCAL_BIN:-$HOME/.local/bin}"
DESKTOP_DIR="${DESKTOP_DIR:-$HOME/Desktop}"

DATA_DIR="$XDG_DATA_HOME/$APP_NAME"
CONFIG_DIR="$XDG_CONFIG_HOME/$APP_NAME"
APPLICATIONS_DIR="$XDG_DATA_HOME/applications"
VENVS_DIR="$DATA_DIR/envs"
VENV_NAME="mp-lite"
VENV_DIR="$VENVS_DIR/$VENV_NAME"
LAUNCHER_SCRIPT="$DATA_DIR/matchypatchy.sh"
DESKTOP_FILE="$APPLICATIONS_DIR/$APP_NAME.desktop"
LOCAL_SYMLINK="$LOCAL_BIN/$APP_NAME"


# Determine script location (so we can find bundled assets next to the installer)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installer started at: $(date)"
echo "Script directory: $SCRIPT_DIR"
echo "Using XDG data dir: $XDG_DATA_HOME"
echo "Target application data dir: $DATA_DIR"
echo ""

# Create required directories
mkdir -p "$DATA_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$APPLICATIONS_DIR"
mkdir -p "$LOCAL_BIN"
mkdir -p "$VENVS_DIR"


# Create Python virtual environment and install package into it if python3 present
if command -v python3 >/dev/null 2>&1; then
  if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  else
    echo "Virtual environment already exists at $VENV_DIR"
  fi

  echo "Upgrading pip in venv..."
  "$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel || true

  # TODO install onnxruntime-gpu

  # Install the package into the venv. If you have a local wheel or source tree included, adapt this line.
  echo "Installing $APP_NAME into virtualenv..."
  # Prefer installing from local path if the packaged installer includes the project dir next to script
  if [ -d "$SCRIPT_DIR/$APP_NAME" ]; then
    echo "Found local project directory, installing from local source..."
    "$VENV_DIR/bin/python" -m pip install --upgrade "$SCRIPT_DIR/$APP_NAME"
  else
    "$VENV_DIR/bin/python" -m pip install --upgrade "$APP_NAME" || {
      echo "pip install failed for package '$APP_NAME'. You may need to install it manually in the venv."
    }
  fi
else
  echo "python3 not found on PATH. Please install Python 3 and then run:"
  echo "  python3 -m venv \"$VENV_DIR\""
  echo "  \"$VENV_DIR/bin/python\" -m pip install --upgrade pip setuptools wheel"
  echo "  \"$VENV_DIR/bin/python\" -m pip install $APP_NAME"
fi


# If packaged assets exist next to installer script, move them into DATA_DIR/MatchyPatchy/assets
PACKAGED_ASSETS_DIR="$SCRIPT_DIR/assets"
DEST_ASSETS_DIR="$DATA_DIR/assets"
if [ -d "$PACKAGED_ASSETS_DIR" ]; then
  echo "Found packaged assets at $PACKAGED_ASSETS_DIR"
  mkdir -p "$(dirname "$DEST_ASSETS_DIR")"
  # Remove existing dest assets to ensure a clean move
  if [ -d "$DEST_ASSETS_DIR" ]; then
    echo "Removing existing assets at $DEST_ASSETS_DIR"
    rm -rf "$DEST_ASSETS_DIR"
  fi
  echo "Moving assets -> $DEST_ASSETS_DIR"
  cp -r "$PACKAGED_ASSETS_DIR" "$DEST_ASSETS_DIR"
else
  echo "No packaged assets found at $PACKAGED_ASSETS_DIR (expected if installer distributed without assets)."
  mkdir -p "$DEST_ASSETS_DIR"
fi

# ---- Create inner script (written by installer) ----
# The inner script runs the Python app using the venv python, tees output to a logfile,
# prints exit code and waits for the user to press Enter so terminals stay open.
INNER_SCRIPT="$DATA_DIR/launch_inner.sh"
LOGFILE="$DATA_DIR/launcher.log"

cat > "$INNER_SCRIPT" <<INNER_EOF
#!/usr/bin/env bash
set -euo pipefail
# inner launcher script (created by installer)
LOGFILE="$LOGFILE"
# Ensure LOGFILE directory exists
mkdir -p "\$(dirname "\$LOGFILE")"
# Redirect all output to both the terminal and the logfile (append)
exec > >(tee -a "\$LOGFILE") 2>&1

# Run the python app using the venv python
"$VENV_DIR/bin/python" "$DATA_DIR/src/matchypatchy/main.py"
rc=\$?
echo
echo "Process exited with code \$rc"
echo
read -p 'Press Enter to close this window...' -r
exit \$rc
INNER_EOF

chmod +x "$INNER_SCRIPT"
echo "Created inner launch script at: $INNER_SCRIPT"
echo "Logfile will be: $LOGFILE"

# ---- Create launcher script that opens a terminal and runs the inner script ----
mkdir -p "$(dirname "$LAUNCHER_SCRIPT")"
cat > "$LAUNCHER_SCRIPT" <<'LAUNCHER_EOF'
#!/usr/bin/env bash
set -euo pipefail

# This launcher attempts to open a visible terminal emulator to run the inner script
# (inner script handles tee'ing output to the logfile and waiting for Enter).
INNER_SCRIPT_PATH="__INNER_SCRIPT_PLACEHOLDER__"
LOGFILE_PATH="__LOGFILE_PLACEHOLDER__"

# Write a short debug header to the logfile
{
  echo "==== MatchyPatchy launcher debug (launcher) ===="
  echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "Launcher executed: $(realpath "$0" 2>/dev/null || echo "$0")"
  echo "Inner script: ${INNER_SCRIPT_PATH}"
  echo "Logfile: ${LOGFILE_PATH}"
  echo "Effective PATH: $PATH"
  echo "----"
} >> "${LOGFILE_PATH}"

TERMINALS=(
  "/usr/bin/gnome-terminal"
  "/usr/bin/konsole"
  "/usr/bin/xfce4-terminal"
  "/usr/bin/mate-terminal"
  "/usr/bin/terminator"
  "/usr/bin/alacritty"
  "/usr/bin/kitty"
  "/usr/bin/xterm"
  "/usr/bin/lxterminal"
  "gnome-terminal"
  "konsole"
  "xfce4-terminal"
  "mate-terminal"
  "terminator"
  "alacritty"
  "kitty"
  "xterm"
  "lxterminal"
)

run_inner_in_terminal() {
  local term="$1"
  case "$(basename "$term")" in
    gnome-terminal)
      "$term" -- bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0 ;;
    konsole)
      if "$term" --help 2>&1 | grep -q -- '--noclose'; then
        "$term" --noclose -e bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0
      else
        "$term" -e bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0
      fi ;;
    xfce4-terminal)
      "$term" --hold --command="bash -lc \"'${INNER_SCRIPT_PATH}'\"" &>> "${LOGFILE_PATH}" & return 0 ;;
    mate-terminal)
      "$term" -- bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0 ;;
    terminator)
      "$term" -x bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0 ;;
    alacritty)
      "$term" -e bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0 ;;
    kitty)
      "$term" --hold bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0 ;;
    xterm)
      "$term" -hold -e bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0 ;;
    lxterminal)
      "$term" -e bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0 ;;
    *)
      if command -v "$term" >/dev/null 2>&1; then
        "$term" -e bash -lc "\"${INNER_SCRIPT_PATH}\"" &>> "${LOGFILE_PATH}" & return 0
      fi
      return 1 ;;
  esac
}

# Try each terminal
for t in "${TERMINALS[@]}"; do
  if run_inner_in_terminal "$t"; then
    echo "Launched using terminal: $t" >> "${LOGFILE_PATH}"
    exit 0
  fi
done

# Fallback: append output of running the inner script to the logfile
{
  echo "No supported terminal emulator found or all launches failed. Running inner script and appending output to log."
  echo "---- OUTPUT START ----"
  "${INNER_SCRIPT_PATH}"
  rc=$?
  echo "---- OUTPUT END ----"
  echo "Process exited with code $rc"
} >> "${LOGFILE_PATH}" 2>&1 || {
  echo "Failed to execute inner script; check the launcher and venv. See ${LOGFILE_PATH} for details."
  exit 1
}

# Try to open the logfile for the user
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "${LOGFILE_PATH}" >/dev/null 2>&1 || true
elif command -v gio >/dev/null 2>&1; then
  gio open "${LOGFILE_PATH}" >/dev/null 2>&1 || true
fi

exit 0
LAUNCHER_EOF

# Substitute placeholders in the launcher file with actual paths
sed -i "s|__INNER_SCRIPT_PLACEHOLDER__|$INNER_SCRIPT|g" "$LAUNCHER_SCRIPT"
sed -i "s|__LOGFILE_PLACEHOLDER__|$LOGFILE|g" "$LAUNCHER_SCRIPT"

chmod +x "$LAUNCHER_SCRIPT"
echo "Created launcher at: $LAUNCHER_SCRIPT"

# assume DEST_ASSETS_DIR already set
ICON_DST="$DEST_ASSETS_DIR/graphics/desktop_icon.png"   # place icon inside app data tree

# Write .desktop using absolute icon path (if available)
if [ -f "$ICON_DST" ]; then
  ICON_FIELD="$ICON_DST"
else
  ICON_FIELD="$APP_NAME"   # fallback to theme lookup
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Terminal=false
Name=MatchyPatchy
Icon=${ICON_FIELD}
Exec=${LAUNCHER_SCRIPT}
Categories=Utility;
EOF

chmod 644 "$DESKTOP_FILE"
echo "Installed desktop file at: $DESKTOP_FILE"

# Also place a copy on the user's Desktop so an icon appears there
DESKTOP_SHORTCUT="$DESKTOP_DIR/$APP_NAME.desktop"
cp -f "$DESKTOP_FILE" "$DESKTOP_SHORTCUT" || {
  echo "Warning: could not copy desktop file to $DESKTOP_SHORTCUT"
}
# Many file managers require the .desktop file to be executable to allow "trusted launcher" behavior;
# mark it executable so the user can double-click it.
chmod +x "$DESKTOP_SHORTCUT" || true
echo "Installed desktop shortcut to: $DESKTOP_SHORTCUT (marked executable)"

# Create symlink into ~/.local/bin for easy CLI invocation
ln -sf "$LAUNCHER_SCRIPT" "$LOCAL_SYMLINK"
chmod +x "$LOCAL_SYMLINK"
echo "Created symlink: $LOCAL_SYMLINK -> $LAUNCHER_SCRIPT"


echo ""
echo "Installation finished at: $(date)"
echo ""
echo "What was installed:"
echo "  - Application data: $DATA_DIR"
echo "  - Virtualenv:       $VENV_DIR"
echo "  - Launcher:         $LAUNCHER_SCRIPT"
echo "  - Desktop file:     $DESKTOP_FILE"
echo "  - CLI symlink:      $LOCAL_SYMLINK"

echo ""
echo "To run the app from a terminal, you can use:"
echo "  $LOCAL_SYMLINK"
echo ""
echo "Or launch it from your desktop environment menu (you may need to log out/in for menus to refresh)."
echo ""
