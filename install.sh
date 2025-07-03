#!/usr/bin/env bash

# mdllama installation script
# Very basic. only tested on Debian 13/trixie 

set -e

# Colour def
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${CYAN}Installing dependencies using pip and venv...${NC}"

echo -e "${YELLOW}Cloning latest mdllama from GitHub...${NC}"
TMP_CLONE_DIR="/tmp/mdllama-install-$$"
git clone --depth=1 https://github.com/qincai-rui/mdllama "$TMP_CLONE_DIR"

echo
echo -en "${YELLOW}Can I use sudo for a system-wide install? [y/N]: ${NC}"
read USE_SUDO
USE_SUDO=$(echo "$USE_SUDO" | tr '[:upper:]' '[:lower:]')

echo -e "${CYAN}Installing dependencies using pip and venv...${NC}"
if [ "$USE_SUDO" = "y" ] || [ "$USE_SUDO" = "yes" ]; then
    MDLLAMA_DIR="/usr/share/_mdllama"
    VENV_DIR="$MDLLAMA_DIR/venv"
    echo -e "${YELLOW}Using system install (sudo).${NC}"
    sudo mkdir -p "$MDLLAMA_DIR"
    sudo python3 -m venv "$VENV_DIR"
    sudo cp "$TMP_CLONE_DIR/mdllama.py" "$MDLLAMA_DIR/mdllama.py"
    sudo chmod 755 "$MDLLAMA_DIR/mdllama.py"
    sudo "$VENV_DIR/bin/pip" install --upgrade pip
    sudo "$VENV_DIR/bin/pip" install requests ollama rich
else
    MDLLAMA_DIR="$HOME/.local/share/_mdllama"
    VENV_DIR="$MDLLAMA_DIR/venv"
    mkdir -p "$MDLLAMA_DIR"
    python3 -m venv "$VENV_DIR"
    cp "$TMP_CLONE_DIR/mdllama.py" "$MDLLAMA_DIR/mdllama.py"
    chmod 755 "$MDLLAMA_DIR/mdllama.py"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install requests ollama rich
fi

rm -rf "$TMP_CLONE_DIR"

# create a bash helper script in /usr/bin or ~/.local/bin
if [ "$MDLLAMA_DIR" = "/usr/share/_mdllama" ]; then
    HELPER_PATH="/usr/bin/mdllama"
    sudo tee "$HELPER_PATH" > /dev/null <<EOF
#!/usr/bin/env bash
source /usr/share/_mdllama/venv/bin/activate
exec python /usr/share/_mdllama/mdllama.py "\$@"
EOF
    sudo chmod +x "$HELPER_PATH"
    echo -e "${GREEN}mdllama command installed to /usr/bin/mdllama${NC}"
else
    HELPER_PATH="$HOME/.local/bin/mdllama"
    mkdir -p "$HOME/.local/bin"
    tee "$HELPER_PATH" > /dev/null <<EOF
#!/usr/bin/env bash
source "$MDLLAMA_DIR/venv/bin/activate"
exec python "$MDLLAMA_DIR/mdllama.py" "\$@"
EOF
    chmod +x "$HELPER_PATH"
    # Add ~/.local/bin to $PATH if not present
    if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${YELLOW}$HOME/.local/bin added to PATH. Please restart your terminal or run: source ~/.bashrc${NC}"
    fi
    echo -e "${GREEN}mdllama command installed to $HELPER_PATH${NC}"
fi

echo
echo -e "${GREEN}Installation complete! You can now run: mdllama --help${NC}"