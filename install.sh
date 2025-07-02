#!/usr/bin/env bash

# mdllama installation script
# Very basic. only tested on Debian 13/trixie 

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "Installing dependencies using pip and venv..."


echo "Cloning latest mdllama from GitHub..."
TMP_CLONE_DIR="/tmp/mdllama-install-$$"
git clone --depth=1 https://github.com/qincai-rui/mdllama "$TMP_CLONE_DIR"

echo
read -p "Can I use sudo for a system-wide install? [y/N]: " USE_SUDO
USE_SUDO=$(echo "$USE_SUDO" | tr '[:upper:]' '[:lower:]')

echo "Installing dependencies using pip and venv..."
if [ "$USE_SUDO" = "y" ] || [ "$USE_SUDO" = "yes" ]; then
    MDLLAMA_DIR="/usr/share/_mdllama"
    VENV_DIR="$MDLLAMA_DIR/venv"
    echo "Using system install (sudo)."
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
    echo "mdllama command installed to /usr/bin/mdllama"
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
        echo "$HOME/.local/bin added to PATH. Please restart your terminal or run: source ~/.bashrc"
    fi
    echo "mdllama command installed to $HELPER_PATH"
fi

echo
echo "Installation complete! You can now run: mdllama --help"
