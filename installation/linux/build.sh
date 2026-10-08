#!/usr/bin/env bash
# Build the MatchyPatchy Linux packages: a .deb (installs to /opt) and a
# tarball (per-user install via install.sh).
#
# Both contain a ready-made Python environment, built here from
# requirements-<variant>.txt, so installing needs no internet and no system Python.
#
# Usage (from anywhere):  bash installation/linux/build.sh [cpu|gpu]
# Requires: uv (pip install uv), dpkg-deb, internet access (build time only).
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
die() { echo -e "${RED}Error: $*${NC}" >&2; exit 1; }

VARIANT="${1:-cpu}"
case "$VARIANT" in cpu|gpu) ;; *) die "usage: $0 [cpu|gpu]" ;; esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

command -v uv >/dev/null 2>&1 || die "uv not found (pip install uv)"
command -v dpkg-deb >/dev/null 2>&1 || die "dpkg-deb not found (sudo apt install dpkg-dev)"

VERSION="$(sed -n 's/^__version__ *= *"\(.*\)".*/\1/p' src/matchypatchy/__init__.py)"
[ -n "$VERSION" ] || die "could not read __version__ from src/matchypatchy/__init__.py"

REQ="$ROOT/requirements-$VARIANT.txt"
[ -f "$REQ" ] || die "missing $REQ"

if [ "$VARIANT" = "gpu" ]; then
    PKG="matchypatchy-gpu"; CONFLICTS="matchypatchy"
else
    PKG="matchypatchy";     CONFLICTS="matchypatchy-gpu"
fi

WORK="$ROOT/build/linux-$VARIANT"
OUT="$ROOT/dist"
TAR_NAME="matchypatchy-${VERSION}-linux-${VARIANT}-x86_64"
STAGE_TAR="$WORK/$TAR_NAME"
STAGE_DEB="$WORK/deb"

echo -e "${GREEN}Building MatchyPatchy $VERSION ($VARIANT)...${NC}"
rm -rf "$WORK"
mkdir -p "$WORK" "$OUT" "$STAGE_TAR"

# ---------------------------------------------------------------
# 1. Python environment.
#    A normal venv is NOT portable (it symlinks to the build machine's
#    interpreter), so start from a standalone, relocatable Python
#    (python-build-standalone, fetched by uv).
# ---------------------------------------------------------------
echo -e "${YELLOW}Fetching standalone Python 3.12...${NC}"
uv python install 3.12 --install-dir "$WORK/pbs"
PBS_PY="$(find "$WORK/pbs" -maxdepth 1 -type d -name 'cpython-3.12.*' | sort | tail -1)"
[ -n "$PBS_PY" ] || die "standalone Python not found in $WORK/pbs"

cp -a "$PBS_PY" "$STAGE_TAR/python_env"
rm -f "$STAGE_TAR"/python_env/lib/python3.12/EXTERNALLY-MANAGED   # allow pip
PY="$STAGE_TAR/python_env/bin/python"

# ---------------------------------------------------------------
# 2. Install requirements-<variant>.txt exactly as written
#    (includes the released matchypatchy from PyPI)
# ---------------------------------------------------------------
echo -e "${YELLOW}Installing packages from requirements-$VARIANT.txt...${NC}"
"$PY" -m pip install --no-cache-dir --no-deps -r "$REQ"

INSTALLED="$("$PY" -c 'import importlib.metadata as m; print(m.version("matchypatchy"))')"
[ "$INSTALLED" = "$VERSION" ] || die "installed matchypatchy $INSTALLED != __version__ $VERSION (update the pin in $REQ)"

# Verify the packaged subpackages made it into the wheel
SITE="$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
for SUB in database gui threads; do
    [ -f "$SITE/matchypatchy/$SUB/__init__.py" ] || die "installed matchypatchy is missing the '$SUB' subpackage (check pyproject packaging)"
done

echo -e "${GREEN}✓ Python environment ready (matchypatchy $INSTALLED)${NC}"

# ---------------------------------------------------------------
# 3. Tarball (per-user install: run install.sh)
# ---------------------------------------------------------------
echo -e "${YELLOW}Assembling tarball...${NC}"
for F in install.sh launcher.sh uninstall.sh; do
    install -m 0755 "$SCRIPT_DIR/opt/matchypatchy/$F" "$STAGE_TAR/$F"
done
cp -r "$SCRIPT_DIR/icons" "$STAGE_TAR/icons"
echo "$VERSION" > "$STAGE_TAR/VERSION"
chmod -R a+rX,go-w "$STAGE_TAR"

tar -C "$WORK" -czf "$OUT/$TAR_NAME.tar.gz" "$TAR_NAME"
echo -e "${GREEN}✓ $OUT/$TAR_NAME.tar.gz${NC}"

# ---------------------------------------------------------------
# 4. .deb (system-wide, runs straight from /opt/matchypatchy)
# ---------------------------------------------------------------
echo -e "${YELLOW}Assembling .deb...${NC}"
mkdir -p "$STAGE_DEB/DEBIAN" "$STAGE_DEB/opt/matchypatchy" \
         "$STAGE_DEB/usr/bin" "$STAGE_DEB/usr/share/applications"

cp -al "$STAGE_TAR/python_env" "$STAGE_DEB/opt/matchypatchy/python_env"   # hardlinks: no second copy
install -m 0755 "$SCRIPT_DIR/opt/matchypatchy/launcher.sh" "$STAGE_DEB/opt/matchypatchy/launcher.sh"
echo "$VERSION" > "$STAGE_DEB/opt/matchypatchy/VERSION"
install -m 0755 "$SCRIPT_DIR/usr/bin/matchypatchy" "$STAGE_DEB/usr/bin/matchypatchy"
install -m 0644 "$SCRIPT_DIR/usr/share/applications/matchypatchy.desktop" \
                "$STAGE_DEB/usr/share/applications/matchypatchy.desktop"

ICON_COUNT=0
for ICON in "$SCRIPT_DIR"/icons/hicolor/*/apps/matchypatchy.png; do
    [ -f "$ICON" ] || continue
    REL="${ICON#"$SCRIPT_DIR"/icons/}"
    install -D -m 0644 "$ICON" "$STAGE_DEB/usr/share/icons/$REL"
    ICON_COUNT=$((ICON_COUNT + 1))
done
[ "$ICON_COUNT" -gt 0 ] || die "no icons found in $SCRIPT_DIR/icons/hicolor"

install -m 0755 "$SCRIPT_DIR/DEBIAN/postinst" "$STAGE_DEB/DEBIAN/postinst"
install -m 0755 "$SCRIPT_DIR/DEBIAN/postrm"   "$STAGE_DEB/DEBIAN/postrm"

INSTALLED_SIZE="$(du -sk "$STAGE_DEB" | cut -f1)"
cat > "$STAGE_DEB/DEBIAN/control" <<EOF_CONTROL
Package: $PKG
Version: $VERSION
Section: science
Priority: optional
Architecture: amd64
Installed-Size: $INSTALLED_SIZE
Maintainer: Kyra Swanson <tswanson@sdzwa.org>
Depends: libc6 (>= 2.28), libgl1, libegl1, libfontconfig1, libdbus-1-3, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xinerama0, libxcb-xkb1
Conflicts: $CONFLICTS
Homepage: https://github.com/conservationtechlab/matchypatchy
Description: GUI tool for human validation of AI-powered animal re-identification
 MatchyPatchy ($VARIANT build) with a bundled Python runtime, installed in
 /opt/matchypatchy. Start it from the application menu or with "matchypatchy".
EOF_CONTROL

dpkg-deb --root-owner-group -Zxz --build "$STAGE_DEB" "$OUT/${PKG}_${VERSION}_${VARIANT}_amd64.deb"
echo -e "${GREEN}✓ $OUT/${PKG}_${VERSION}_${VARIANT}_amd64.deb${NC}"

echo -e "${GREEN}All builds complete in $OUT/${NC}"
