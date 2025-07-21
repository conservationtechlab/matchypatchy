#!/bin/bash

# === Configuration ===
APP_NAME="MatchyPatchy"
APP_FOLDER_NAME="MatchyPatchy"  # Folder where the built PyInstaller output lives
INSTALL_DIR="/opt/$APP_NAME"
ENTRYPOINT="MatchyPatchy"  # name of the main executable
SYMLINK="/usr/local/bin/$ENTRYPOINT"

# === Print heading ===
echo "Installing $APP_NAME..."
echo "Source directory: $(pwd)/$APP_FOLDER_NAME"
echo "Target install directory: $INSTALL_DIR"

# === Check for root ===
if [[ $EUID -ne 0 ]]; then
   echo "This installer must be run as root (use sudo)." 
   exit 1
fi

# === Create target directory ===
mkdir -p "$INSTALL_DIR"
if [ $? -ne 0 ]; then
  echo "Error: Could not create install directory."
  exit 2
fi

# === Copy files ===
echo "Copying files to $INSTALL_DIR..."
cp -r "./$APP_FOLDER_NAME/"* "$INSTALL_DIR/"
if [ $? -ne 0 ]; then
  echo "Error: File copy failed."
  exit 3
fi

# === Create symlink for command line launch ===
if [ -f "$INSTALL_DIR/$ENTRYPOINT" ]; then
  echo "Creating symlink: $SYMLINK -> $INSTALL_DIR/$ENTRYPOINT"
  ln -sf "$INSTALL_DIR/$ENTRYPOINT" "$SYMLINK"
else
  echo "Warning: Main executable '$ENTRYPOINT' not found. Skipping symlink."
fi

echo "$APP_NAME installed successfully."
