#!/usr/bin/env bash
# mdllama uninstallation script

# Removes system or user install of mdllama and its venv

set -e

echo "mdllama uninstaller"


# Try to remove system-wide install if present
if [ -d /usr/share/_mdllama ] || [ -f /usr/bin/mdllama ]; then
    echo "System-wide mdllama install detected."
    read -p "Use sudo to remove system-wide install? [y/N]: " USE_SUDO
    USE_SUDO=$(echo "$USE_SUDO" | tr '[:upper:]' '[:lower:]')
    if [ "$USE_SUDO" = "y" ] || [ "$USE_SUDO" = "yes" ]; then
        echo "Removing system-wide install..."
        sudo rm -rf /usr/share/_mdllama
        if [ -f /usr/bin/mdllama ]; then
            sudo rm /usr/bin/mdllama
            echo "Removed /usr/bin/mdllama"
        fi
        echo "System-wide mdllama removed."
    else
        echo "Skipped removing system-wide install."
    fi
fi

# Try to remove user install if present
if [ -d "$HOME/.local/share/_mdllama" ] || [ -f "$HOME/.local/bin/mdllama" ]; then
    echo "Removing user install..."
    rm -rf "$HOME/.local/share/_mdllama"
    if [ -f "$HOME/.local/bin/mdllama" ]; then
        rm "$HOME/.local/bin/mdllama"
        echo "Removed $HOME/.local/bin/mdllama"
    fi
    echo "User mdllama removed. If you wish, remove the PATH line from your ~/.bashrc manually."
fi

echo "Uninstallation complete."
