#!/usr/bin/env bash
# make_app_bundle.sh
# Create a proper .app bundle structure with Info.plist and a launcher executable.
# Usage: ./make_app_bundle.sh APP_NAME MODULE VENV_DIR DEST_APP_BUNDLE
#
set -euo pipefail
if [[ $# -ne 4 ]]; then
  echo "Usage: $0 APP_NAME MODULE VENV_DIR DEST_APP_BUNDLE"
  exit 1
fi

APP_NAME="$1"
MODULE="$2"
VENV_DIR="$3"
APP_BUNDLE_DIR="$4"

echo "Building app bundle: $APP_BUNDLE_DIR"
rm -rf "$APP_BUNDLE_DIR"
mkdir -p "${APP_BUNDLE_DIR}/Contents/MacOS"
mkdir -p "${APP_BUNDLE_DIR}/Contents/Resources"

# Info.plist - customize identifier and version as needed
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

# Launcher executable: a small shell wrapper that execs into the venv
LAUNCHER="${APP_BUNDLE_DIR}/Contents/MacOS/${APP_NAME}"
cat > "$LAUNCHER" <<SH
#!/usr/bin/env bash
# Launcher for ${APP_NAME}
VENV_DIR="${VENV_DIR}"
MODULE="${MODULE}"
exec "\${VENV_DIR}/bin/python" -m "\${MODULE}" "\$@"
SH
chmod +x "$LAUNCHER"

echo "App bundle created: $APP_BUNDLE_DIR"
echo "You can open it with: open -a \"${APP_BUNDLE_DIR}\""