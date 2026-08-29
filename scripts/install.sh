#!/usr/bin/env bash
set -e

# MiniGit Standalone Client Installer for Linux and macOS
# Usage: curl -fsSL https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/install.sh | bash

REPO="Anirban-dev/Git"
INSTALL_DIR="$HOME/.minigit/bin"
EXECUTABLE_NAME="minigit"

# Color formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==>${NC} Installing ${GREEN}MiniGit CLI${NC}..."

# 1. Detect OS and Architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

BINARY_NAME=""

case "$OS" in
    Linux)
        if [ "$ARCH" = "x86_64" ]; then
            BINARY_NAME="minigit-linux-x86_64"
        elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
            BINARY_NAME="minigit-linux-arm64"
        else
            echo -e "${RED}Error:${NC} Unsupported Linux architecture: $ARCH"
            exit 1
        fi
        ;;
    Darwin)
        if [ "$ARCH" = "arm64" ]; then
            BINARY_NAME="minigit-macos-arm64"
        else
            BINARY_NAME="minigit-macos-x86_64"
        fi
        ;;
    *)
        echo -e "${RED}Error:${NC} Unsupported Operating System: $OS"
        echo "For Windows, please use: irm https://raw.githubusercontent.com/$REPO/main/scripts/install.ps1 | iex"
        exit 1
        ;;
esac

# 2. Get latest release download URL
DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${BINARY_NAME}"

echo -e "${BLUE}==>${NC} Downloading binary from: ${DOWNLOAD_URL}"

# Create destination directory
mkdir -p "$INSTALL_DIR"

# Download binary
if command -v curl >/dev/null 2>&1; then
    curl -fL "$DOWNLOAD_URL" -o "$INSTALL_DIR/$EXECUTABLE_NAME" || {
        echo -e "${YELLOW}Warning: Direct asset not found, checking release JSON...${NC}"
        LATEST_URL=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest" | grep "browser_download_url.*${BINARY_NAME}" | cut -d : -f 2,3 | tr -d '\" ')
        if [ -n "$LATEST_URL" ]; then
            curl -fL "$LATEST_URL" -o "$INSTALL_DIR/$EXECUTABLE_NAME"
        else
            echo -e "${RED}Failed to download ${BINARY_NAME}. Please verify that a release exists at https://github.com/${REPO}/releases${NC}"
            exit 1
        fi
    }
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$INSTALL_DIR/$EXECUTABLE_NAME" "$DOWNLOAD_URL"
else
    echo -e "${RED}Error:${NC} curl or wget is required to download MiniGit."
    exit 1
fi

chmod +x "$INSTALL_DIR/$EXECUTABLE_NAME"

# 3. Add to PATH in Shell config files
PATH_LINE="export PATH=\"\$HOME/.minigit/bin:\$PATH\""
UPDATED_SHELL=false

for PROFILE in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" "$HOME/.bash_profile"; do
    if [ -f "$PROFILE" ]; then
        if ! grep -q ".minigit/bin" "$PROFILE"; then
            echo "" >> "$PROFILE"
            echo "# MiniGit CLI" >> "$PROFILE"
            echo "$PATH_LINE" >> "$PROFILE"
            UPDATED_SHELL=true
        fi
    fi
done

echo ""
echo -e "${GREEN}✔ MiniGit installed successfully to: ${INSTALL_DIR}/${EXECUTABLE_NAME}${NC}"
echo ""

if [ "$UPDATED_SHELL" = true ]; then
    echo -e "${YELLOW}To start using minigit immediately in this terminal, run:${NC}"
    echo -e "  ${BLUE}export PATH=\"\$HOME/.minigit/bin:\$PATH\"${NC}"
    echo -e "or restart your terminal."
else
    echo -e "Make sure ${BLUE}\$HOME/.minigit/bin${NC} is in your ${BLUE}PATH${NC}."
fi

echo ""
echo "Try running:"
echo "  minigit help"
echo "  minigit auth register --server https://<your-dokploy-server-url>"
