#!/usr/bin/env bash
set -e

# MiniGit Standalone Client Uninstaller for Linux and macOS
# Usage: curl -fsSL https://raw.githubusercontent.com/Anirban-dev/Git/main/scripts/uninstall.sh | bash

INSTALL_DIR="$HOME/.minigit"
EXECUTABLE="$INSTALL_DIR/bin/minigit"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==>${NC} Uninstalling ${RED}MiniGit CLI${NC}..."

# 1. Remove binary and minigit directory
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✔ Removed directory: ${INSTALL_DIR}${NC}"
else
    echo -e "${YELLOW}MiniGit directory not found at ${INSTALL_DIR}.${NC}"
fi

# 2. Clean up PATH lines from shell configs
for PROFILE in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" "$HOME/.bash_profile"; do
    if [ -f "$PROFILE" ]; then
        if grep -q ".minigit/bin" "$PROFILE"; then
            # Remove MiniGit lines from profile
            grep -v ".minigit/bin" "$PROFILE" | grep -v "# MiniGit CLI" > "${PROFILE}.tmp" && mv "${PROFILE}.tmp" "$PROFILE"
            echo -e "${GREEN}✔ Cleaned PATH from: ${PROFILE}${NC}"
        fi
    fi
done

echo ""
echo -e "${GREEN}✔ MiniGit CLI has been completely uninstalled.${NC}"
echo -e "Please restart your terminal or open a new tab."
