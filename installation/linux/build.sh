#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

VERSION="0.2.0"
BUILD_DIR="./build"
OUTPUT_DIR="./dist"
PACKAGE_NAME="matchypatchy-${VERSION}-linux"

echo -e "${GREEN}Building MatchyPatchy ${VERSION} Linux installer...${NC}"

# Clean up previous builds
rm -rf "$BUILD_DIR" "$OUTPUT_DIR"
mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

# Create directory structure
mkdir -p "$BUILD_DIR/opt/matchypatchy"
mkdir -p "$BUILD_DIR/usr/local/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"

# ============================================
# BUILD BUNDLED PYTHON
# ============================================
echo -e "${YELLOW}Building bundled Python environment...${NC}"
if [ ! -d "python_env" ]; then
    python3 -m venv python_env
fi

source python_env/bin/activate

# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Install requirements as-is, WITHOUT dependency resolution
echo -e "${YELLOW}Installing packages from requirements.txt (--no-deps)...${NC}"
pip install --no-deps -r requirements.txt

# Verify installation
echo -e "${YELLOW}Verifying installation...${NC}"
pip list

deactivate

echo -e "${GREEN}✓ Python environment ready${NC}"

# ============================================
# Copy bundled Python
# ============================================
echo -e "${YELLOW}Copying Python runtime...${NC}"
cp -r python_env "$BUILD_DIR/opt/matchypatchy/"

echo -e "${YELLOW}Copying application...${NC}"
cp -r src/matchypatchy "$BUILD_DIR/opt/matchypatchy/"

echo -e "${YELLOW}Copying scripts...${NC}"
cp installation/linux/opt/matchypatchy/install.sh "$BUILD_DIR/opt/matchypatchy/"
cp installation/linux/opt/matchypatchy/launcher.sh "$BUILD_DIR/opt/matchypatchy/"
cp installation/linux/opt/matchypatchy/uninstall.sh "$BUILD_DIR/opt/matchypatchy/"
chmod +x "$BUILD_DIR/opt/matchypatchy"/*.sh

echo -e "${YELLOW}Copying wrapper and desktop entry...${NC}"
cp installation/linux/usr/local/bin/matchypatchy "$BUILD_DIR/usr/local/bin/"
chmod +x "$BUILD_DIR/usr/local/bin/matchypatchy"
cp installation/linux/usr/share/applications/matchypatchy.desktop "$BUILD_DIR/usr/share/applications/"

# ============================================
# CREATE TARBALL
# ============================================
echo -e "${YELLOW}Creating tarball...${NC}"
cd "$BUILD_DIR"
tar -czf "../$OUTPUT_DIR/${PACKAGE_NAME}-x86_64.tar.gz" .
cd ..

TARBALL_SIZE=$(du -h "$OUTPUT_DIR/${PACKAGE_NAME}-x86_64.tar.gz" | cut -f1)
echo -e "${GREEN}✓ Tarball created: $OUTPUT_DIR/${PACKAGE_NAME}-x86_64.tar.gz ($TARBALL_SIZE)${NC}"

# ============================================
# CREATE .DEB PACKAGE
# ============================================
echo -e "${YELLOW}Creating .deb package...${NC}"
mkdir -p "$BUILD_DIR/DEBIAN"
cat > "$BUILD_DIR/DEBIAN/control" <<EOF
Package: matchypatchy
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Conservation Technology Lab <info@example.com>
Depends: bash
Description: MatchyPatchy - Image matching application
 MatchyPatchy with bundled Python runtime.
EOF

cat > "$BUILD_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
chmod +x /opt/matchypatchy/install.sh
chmod +x /opt/matchypatchy/launcher.sh
chmod +x /opt/matchypatchy/uninstall.sh
chmod +x /usr/local/bin/matchypatchy
/opt/matchypatchy/install.sh
EOF
chmod +x "$BUILD_DIR/DEBIAN/postinst"

dpkg-deb --build "$BUILD_DIR" "$OUTPUT_DIR/${PACKAGE_NAME}_amd64.deb" 2>/dev/null && \
    echo -e "${GREEN}✓ .deb package created${NC}" || \
    echo -e "${YELLOW}Note: dpkg not available, skipping .deb creation${NC}"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ All builds complete in $OUTPUT_DIR/${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"