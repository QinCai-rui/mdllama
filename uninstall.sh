#!/usr/bin/env bash
# mdllama uninstallation script

# Removes system or user install of mdllama and its venv

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}mdllama uninstaller${NC}"

# Try to remove system-wide install if present
if [ -d /usr/share/_mdllama ] || [ -f /usr/bin/mdllama ]; then
    echo -e "${YELLOW}System-wide mdllama install detected.${NC}"
    echo -en "${YELLOW}Use sudo to remove system-wide install? [y/N]: ${NC}"
    read USE_SUDO
    USE_SUDO=$(echo "$USE_SUDO" | tr '[:upper:]' '[:lower:]')
    if [ "$USE_SUDO" = "y" ] || [ "$USE_SUDO" = "yes" ]; then
        echo -e "${YELLOW}Removing system-wide install...${NC}"
        sudo rm -rf /usr/share/_mdllama
        if [ -f /usr/bin/mdllama ]; then
            sudo rm /usr/bin/mdllama
            echo -e "${GREEN}Removed /usr/bin/mdllama${NC}"
        fi
        echo -e "${GREEN}System-wide mdllama removed.${NC}"
    else
        echo -e "${RED}Skipped removing system-wide install.${NC}"
    fi
fi

# Try to remove user install if present
if [ -d "$HOME/.local/share/_mdllama" ] || [ -f "$HOME/.local/bin/mdllama" ]; then
    echo -e "${YELLOW}Removing user install...${NC}"
    rm -rf "$HOME/.local/share/_mdllama"
    if [ -f "$HOME/.local/bin/mdllama" ]; then
        rm "$HOME/.local/bin/mdllama"
        echo -e "${GREEN}Removed $HOME/.local/bin/mdllama${NC}"
    fi
    echo -e "${GREEN}User mdllama removed. If you wish, remove the PATH line from your ~/.bashrc manually.${NC}"
fi

echo -e "${GREEN}Uninstallation complete.${NC}"