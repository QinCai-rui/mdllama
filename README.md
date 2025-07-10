# mdllama

[![Build and Publish mdllama DEB and RPM](https://github.com/QinCai-rui/packages/actions/workflows/build-and-publish-ppa.yml/badge.svg)](https://github.com/QinCai-rui/packages/actions/workflows/build-and-publish-ppa.yml)

[![Publish to PyPI on mdllama.py Update](https://github.com/QinCai-rui/mdllama/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/QinCai-rui/mdllama/actions/workflows/publish-to-pypi.yml)

[![PPA development (GH Pages)](https://github.com/QinCai-rui/packages/actions/workflows/pages/pages-build-deployment/badge.svg?branch=gh-pages)](https://github.com/QinCai-rui/packages/actions/workflows/pages/pages-build-deployment)

A CLI tool that lets you chat with Ollama models right from your terminal, with built-in Markdown rendering.

mdllama makes it easy to interact with Ollama's AI models directly from your command line, meanwhile providing you with real-time Markdown rendering

## Features

- Chat with Ollama models from the terminal
- Built-in Markdown rendering
- Simple installation and removal (see below)

## Screenshots

### Chat Interface
![Chat](https://raw.githubusercontent.com/QinCai-rui/mdllama/refs/heads/main/assets/chat.png)

### Help
![Help](https://raw.githubusercontent.com/QinCai-rui/mdllama/refs/heads/main/assets/help.png)

## Demo

<video controls src="https://raw.githubusercontent.com/QinCai-rui/mdllama/refs/heads/main/assets/demo.webm" title="Demo"></video>
Note: If the video does not play, you can download it [here](https://raw.githubusercontent.com/QinCai-rui/mdllama/refs/heads/main/assets/demo.webm).


## Installation

### Install using package manager (recommended)

#### Debian/Ubuntu Installation

1. Add the PPA to your sources list:

   ```bash
   echo 'deb [trusted=yes] https://packages.qincai.xyz/debian stable main' | sudo tee /etc/apt/sources.list.d/qincai-mdllama.list
   sudo apt update
   ```

2. Install mdllama:

   ```bash
   sudo apt install python3-mdllama
   ```

#### Fedora Installation

1. Download the latest RPM from:
   [https://packages.qincai.xyz/fedora/](https://packages.qincai.xyz/fedora/)

   Or, to install directly:

   ```bash
   sudo dnf install https://packages.qincai.xyz/fedora/mdllama-<version>.noarch.rpm
   ```

   Replace `<version>` with the latest version number.

2. (Optional, highly recommended) To enable as a repository for updates, create `/etc/yum.repos.d/qincai-mdllama.repo`:

   ```ini
   [qincai-mdllama]
   name=Raymont's Personal RPMs
   baseurl=https://packages.qincai.xyz/fedora/
   enabled=1
   metadata_expire=0
   gpgcheck=0
   ```

   Then install with:

   ```bash
   sudo dnf install mdllama
   ```

3, Install the `ollama` library from pip:

   ```bash
   pip install ollama
   ```

   You can also install it globally with:

   ```bash
   sudo pip install ollama
   ```

   > [!NOTE]
   > The `ollama` library is not installed by default in the RPM package since there is no system `ollama` package avaliable (`python3-ollama`). You need to install it manually using pip in order to use `mdllama` with Ollama models.

---

### Traditional Bash Script Installation (Linux)

To install **mdllama** using the traditional bash script, run:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/QinCai-rui/mdllama/refs/heads/main/install.sh)
```

To uninstall **mdllama**, run:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/QinCai-rui/mdllama/refs/heads/main/uninstall.sh)
```

---

### Windows & macOS Installation

Install via pip (recommended for Windows/macOS):

```bash
pip install mdllama
```

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

---
