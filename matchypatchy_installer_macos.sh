#!/usr/bin/env bash
# install_macos.sh
# Per-user macOS installer for a Python app that uses a virtualenv.
#
# Usage:
#   ./install_macos.sh -n MyApp -m mypackage.module:main -r requirements.txt [-p /path/to/wheel_or_src] [-f]
#
# -n NAME        Application name (used for paths and .app)
# -m MODULE      Module to run inside venv, format "package.module:callable" or just "package.module"
# -r REQFILE     requirements.txt path (optional)
# -p PACKAGE     local wheel or path to install into venv (optional)
# -f             force overwrite existing install
#
set -euo pipefail

APP_NAME="MatchyPatchy"
MODULE=""
REQFILE=""
PACKAGE=""
FORCE=0

usage() {
  cat <<EOF
Usage: $0 -n APP_NAME -m MODULE [-r requirements.txt] [-p package_to_install] [-f]
Example:
  $0 -n matchypatchy -m matchypatchy.gui:main -r requirements.txt
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n) APP_NAME="$2"; shift 2;;
    -m) MODULE="$2"; shift 2;;
    -r) REQFILE="$2"; shift 2;;
    -p) PACKAGE="$2"; shift 2;;
    -f) FORCE=1; shift;;
    -h) usage;;
    *) echo "Unknown arg: $1"; usage;;
  esac
done

if [[ -z "$MODULE" ]]; then
  echo "Error: module (-m) required"
  usage
fi

# Locations (macOS-friendly)
APP_SUPPORT="${HOME}/Library/Application Support/${APP_NAME}"
VENV_DIR="${APP_SUPPORT}/venv"
APP_BUNDLE_DIR="${HOME}/Applications/${APP_NAME}.app"
LAUNCHER_SCRIPT="${APP_BUNDLE_DIR}/Contents/MacOS/${APP_NAME}"

# Choose Python interpreter
PYTHON_BIN=$(command -v python3 || true)
if [[ -z "$PYTHON_BIN" ]]; then
  echo "python3 not found in PATH. Please install Python 3.9+ (Homebrew, system, or pyenv)."
  exit 2
fi

echo "Using Python: $PYTHON_BIN"
echo "Installing to: $APP_SUPPORT"
echo "App bundle: $APP_BUNDLE_DIR"

if [[ -d "$APP_SUPPORT" && $FORCE -ne 1 ]]; then
  echo "App support dir exists. Use -f to overwrite or remove ${APP_SUPPORT}"
fi

# Create dirs
mkdir -p "$APP_SUPPORT"
mkdir -p "$(dirname "$LAUNCHER_SCRIPT")"

# Create venv if missing
if [[ ! -d "$VENV_DIR" || $FORCE -eq 1 ]]; then
  rm -rf "$VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR" --upgrade-deps
fi

# Ensure pip up-to-date
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

# Install requirements if provided
if [[ -n "$REQFILE" ]]; then
  if [[ ! -f "$REQFILE" ]]; then
    echo "Requirements file not found: $REQFILE"
    exit 3
  fi
  echo "Installing requirements from $REQFILE..."
  "$VENV_DIR/bin/python" -m pip install -r "$REQFILE"
fi

# Install optional package (local wheel or package path)
if [[ -n "$PACKAGE" ]]; then
  echo "Installing package: $PACKAGE"
  "$VENV_DIR/bin/python" -m pip install "$PACKAGE"
fi

# Install the application package (assume source tree is parent of installer)
# You may prefer to pip install a wheel from dist/ instead.
if [[ -f "setup.py" || -f "pyproject.toml" ]]; then
  echo "Installing local package into venv..."
  "$VENV_DIR/bin/python" -m pip install -e .
fi

# Create app bundle (small launcher script) by calling helper script in project
# If helper exists, use it; otherwise write a minimal launcher here.
if [[ -x "./make_app_bundle.sh" ]]; then
  ./make_app_bundle.sh "$APP_NAME" "$MODULE" "$VENV_DIR" "$APP_BUNDLE_DIR"
else
  echo "Creating minimal .app bundle at $APP_BUNDLE_DIR"
  mkdir -p "${APP_BUNDLE_DIR}/Contents/MacOS"
  mkdir -p "${APP_BUNDLE_DIR}/Contents/Resources"
  # Basic Info.plist
  cat > "${APP_BUNDLE_DIR}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>${APP_NAME}</string>
  <key>CFBundleDisplayName</key><string>${APP_NAME}</string>
  <key>CFBundleIdentifier</key><string>org.example.${APP_NAME}</string>
  <key>CFBundleExecutable</key><string>${APP_NAME}</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>10.14</string>
</dict>
</plist>
PLIST

  # Launcher exec that runs the module inside the venv
  cat > "${LAUNCHER_SCRIPT}" <<'SH'
#!/usr/bin/env bash
# Minimal launcher to exec the app inside its venv
VENV_DIR="$1"; shift
MODULE="$1"; shift
exec "$VENV_DIR/bin/python" -m "$MODULE" "$@"
SH
  # Make launcher immutable: pass venv and module as executable args via wrapper
  # But we need a static file; we'll create a small shim that hardcodes paths below.
  # Replace the temporary placeholder with actual values:
  sed -i '' "s|VENV_DIR=\"\$1\"; shift|VENV_DIR=\"${VENV_DIR}\"; shift|g" "${LAUNCHER_SCRIPT}"
  sed -i '' "s|MODULE=\"\$1\"; shift|MODULE=\"${MODULE}\"; shift|g" "${LAUNCHER_SCRIPT}"
  chmod +x "${LAUNCHER_SCRIPT}"
fi

echo "Installation complete."
echo "You can open the app from Finder (~/Applications/${APP_NAME}.app) or run:"
echo "  open -a \"${APP_NAME}\""