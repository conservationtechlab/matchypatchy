#!/usr/bin/env bash
# Build the MatchyPatchy macOS package: a MatchyPatchy.app bundle (with a
# ready-made, relocatable Python environment inside) wrapped in a .dmg.
#
# Usage (from anywhere):  bash installation/macos/build.sh
# Build on the architecture you are targeting (arm64 runner -> Apple Silicon
# build, Intel runner -> x86_64 build); the standalone Python is arch-specific.
#
# Requires: uv (pip install uv), hdiutil, sips, iconutil (all built into macOS).
#
# Optional environment variables:
#   MAC_SIGN_IDENTITY   "Developer ID Application: Name (TEAMID)"; if unset the
#                       app is ad-hoc signed (users must right-click > Open once)
#   NOTARY_PROFILE      notarytool keychain profile; if set (and signing with a
#                       real identity) the dmg is notarized and stapled
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
die() { echo -e "${RED}Error: $*${NC}" >&2; exit 1; }

[ "$(uname -s)" = "Darwin" ] || die "this script must run on macOS"

ARCH="$(uname -m)"                      # arm64 or x86_64
case "$ARCH" in arm64|x86_64) ;; *) die "unsupported architecture: $ARCH" ;; esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

command -v uv >/dev/null 2>&1 || die "uv not found (pip install uv)"
command -v hdiutil >/dev/null 2>&1 || die "hdiutil not found"

VERSION="$(sed -n 's/^__version__ *= *"\(.*\)".*/\1/p' src/matchypatchy/__init__.py)"
[ -n "$VERSION" ] || die "could not read __version__ from src/matchypatchy/__init__.py"

REQ="$ROOT/requirements-cpu.txt"
[ -f "$REQ" ] || die "missing $REQ"

APP_NAME="MatchyPatchy"
BUNDLE_ID="org.conservationtechlab.matchypatchy"
WORK="$ROOT/build/macos-$ARCH"
OUT="$ROOT/dist"
APP="$WORK/$APP_NAME.app"
DMG_NAME="matchypatchy-${VERSION}-macos-${ARCH}"
ICON_SRC_DIR="$ROOT/installation/linux/icons/hicolor"   # reuse the Linux PNGs

echo -e "${GREEN}Building MatchyPatchy $VERSION (macOS $ARCH)...${NC}"
rm -rf "$WORK"
mkdir -p "$WORK" "$OUT" \
         "$APP/Contents/MacOS" "$APP/Contents/Resources"

# ---------------------------------------------------------------
# 1. Python environment (standalone, relocatable, fetched by uv)
# ---------------------------------------------------------------
echo -e "${YELLOW}Fetching standalone Python 3.12...${NC}"
uv python install 3.12 --install-dir "$WORK/pbs"
PBS_PY="$(find "$WORK/pbs" -maxdepth 1 -type d -name 'cpython-3.12.*' | sort | tail -1)"
[ -n "$PBS_PY" ] || die "standalone Python not found in $WORK/pbs"

cp -a "$PBS_PY" "$APP/Contents/Resources/python_env"
rm -f "$APP"/Contents/Resources/python_env/lib/python3.12/EXTERNALLY-MANAGED   # allow pip
PY="$APP/Contents/Resources/python_env/bin/python3"
[ -x "$PY" ] || die "python not found at $PY"

# ---------------------------------------------------------------
# 2. Install requirements-mac.txt exactly as written
#    (includes the released matchypatchy from PyPI)
# ---------------------------------------------------------------
echo -e "${YELLOW}Installing packages from requirements-cpu.txt...${NC}"
"$PY" -m pip install --no-cache-dir --no-deps -r "$REQ"

INSTALLED="$("$PY" -c 'import importlib.metadata as m; print(m.version("matchypatchy"))')"
[ "$INSTALLED" = "$VERSION" ] || die "installed matchypatchy $INSTALLED != __version__ $VERSION (update the pin in $REQ)"

SITE="$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
for SUB in database gui threads; do
    [ -f "$SITE/matchypatchy/$SUB/__init__.py" ] || die "installed matchypatchy is missing the '$SUB' subpackage (check pyproject packaging)"
done
echo -e "${GREEN}✓ Python environment ready (matchypatchy $INSTALLED)${NC}"

# Drop bytecode caches so the bundle is smaller and signing is stable
find "$APP" -name '__pycache__' -type d -prune -exec rm -rf {} +

# ---------------------------------------------------------------
# 3. App bundle: launcher, Info.plist, icon
# ---------------------------------------------------------------
echo -e "${YELLOW}Assembling $APP_NAME.app...${NC}"

# NOTE: assumes the package is runnable with `python -m matchypatchy`.
# If the Linux launcher.sh uses a different entry point, change it here.
cat > "$APP/Contents/MacOS/$APP_NAME" <<'EOF_LAUNCHER'
#!/bin/bash
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PYENV="$HERE/Resources/python_env"

# Finder starts apps in "/", which is read-only. MatchyPatchy writes
# matchypatchy.log (and possibly other files) relative to the working directory.
DATA="$HOME/Library/Application Support/MatchyPatchy"
mkdir -p "$DATA"
cd "$DATA"

export PATH="$HERE/Resources/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONFAULTHANDLER=1
exec "$PYENV/bin/python3" -m matchypatchy "$@"
EOF_LAUNCHER
chmod 0755 "$APP/Contents/MacOS/$APP_NAME"

cat > "$APP/Contents/Info.plist" <<EOF_PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>               <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>        <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>         <string>$BUNDLE_ID</string>
    <key>CFBundleVersion</key>            <string>$VERSION</string>
    <key>CFBundleShortVersionString</key> <string>$VERSION</string>
    <key>CFBundleExecutable</key>         <string>$APP_NAME</string>
    <key>CFBundleIconFile</key>           <string>matchypatchy</string>
    <key>CFBundlePackageType</key>        <string>APPL</string>
    <key>LSMinimumSystemVersion</key>     <string>11.0</string>
    <key>NSHighResolutionCapable</key>    <true/>
    <key>LSApplicationCategoryType</key>  <string>public.app-category.education</string>
</dict>
</plist>
EOF_PLIST

# Icon: build an .icns from the largest Linux PNG (resized with sips)
BIGGEST="$(find "$ICON_SRC_DIR" -name matchypatchy.png -path '*apps*' 2>/dev/null \
           | sed -E 's#.*/([0-9]+)x[0-9]+/apps/.*#\1 &#' | sort -n | tail -1 | cut -d' ' -f2-)"
[ -n "$BIGGEST" ] || die "no icons found in $ICON_SRC_DIR"
ICONSET="$WORK/matchypatchy.iconset"
mkdir -p "$ICONSET"
for SZ in 16 32 128 256 512; do
    sips -z "$SZ" "$SZ" "$BIGGEST" --out "$ICONSET/icon_${SZ}x${SZ}.png" >/dev/null
    sips -z $((SZ * 2)) $((SZ * 2)) "$BIGGEST" --out "$ICONSET/icon_${SZ}x${SZ}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/matchypatchy.icns"

# ---------------------------------------------------------------
# 4. Code signing (ad-hoc unless MAC_SIGN_IDENTITY is set)
# ---------------------------------------------------------------
IDENTITY="${MAC_SIGN_IDENTITY:--}"
echo -e "${YELLOW}Signing app (identity: ${MAC_SIGN_IDENTITY:-ad-hoc})...${NC}"
if [ "$IDENTITY" = "-" ]; then
    codesign --force --deep --sign - "$APP"
else
    # Sign nested binaries first, then the bundle, with hardened runtime
    find "$APP" -type f \( -name '*.so' -o -name '*.dylib' -o -perm -111 \) -print0 \
        | xargs -0 -n 20 codesign --force --options runtime --timestamp --sign "$IDENTITY" 2>/dev/null || true
    codesign --force --options runtime --timestamp --sign "$IDENTITY" "$APP"
fi
codesign --verify --verbose=1 "$APP" || die "code signature verification failed"

# ---------------------------------------------------------------
# 5. DMG (drag-to-Applications)
# ---------------------------------------------------------------
echo -e "${YELLOW}Assembling .dmg...${NC}"
STAGE_DMG="$WORK/dmg"
mkdir -p "$STAGE_DMG"
cp -a "$APP" "$STAGE_DMG/"
ln -s /Applications "$STAGE_DMG/Applications"
echo "$VERSION" > "$STAGE_DMG/VERSION.txt"

rm -f "$OUT/$DMG_NAME.dmg"
hdiutil create -volname "$APP_NAME $VERSION" -srcfolder "$STAGE_DMG" \
    -ov -format UDZO "$OUT/$DMG_NAME.dmg" >/dev/null

if [ "$IDENTITY" != "-" ]; then
    codesign --force --sign "$IDENTITY" --timestamp "$OUT/$DMG_NAME.dmg"
    if [ -n "${NOTARY_PROFILE:-}" ]; then
        echo -e "${YELLOW}Notarizing (this can take a few minutes)...${NC}"
        xcrun notarytool submit "$OUT/$DMG_NAME.dmg" --keychain-profile "$NOTARY_PROFILE" --wait
        xcrun stapler staple "$OUT/$DMG_NAME.dmg"
    fi
fi

echo -e "${GREEN}✓ $OUT/$DMG_NAME.dmg${NC}"
echo -e "${GREEN}All builds complete in $OUT/${NC}"