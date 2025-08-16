# mdllama

[![Build and Publish mdllama DEB and RPM](https://github.com/QinCai-rui/packages/actions/workflows/build-and-publish-ppa.yml/badge.svg)](https://github.com/QinCai-rui/packages/actions/workflows/build-and-publish-ppa.yml)

[![Build and Publish mdllama DEB and RPM (testing branch)](https://github.com/QinCai-rui/packages/actions/workflows/build-and-publish-ppa-testing.yml/badge.svg)](https://github.com/QinCai-rui/packages/actions/workflows/build-and-publish-ppa-testing.yml)

[![Publish to PyPI on mdllama.py Update](https://github.com/QinCai-rui/mdllama/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/QinCai-rui/mdllama/actions/workflows/publish-to-pypi.yml)

[![PPA development (GH Pages)](https://github.com/QinCai-rui/packages/actions/workflows/pages/pages-build-deployment/badge.svg?branch=gh-pages)](https://github.com/QinCai-rui/packages/actions/workflows/pages/pages-build-deployment)

A CLI tool that lets you chat with Ollama and OpenAI models right from your terminal, with built-in Markdown rendering.

`mdllama` makes it easy to interact with AI models directly from your command line, meanwhile providing you with real-time Markdown rendering.

## Features

### Core Functionality

- **Multi-provider support**: Chat with both Ollama and OpenAI-compatible models from the terminal
- **Built-in Markdown rendering**: Rich text display with proper formatting
- **Interactive chat sessions**: Full conversation management with context
- **Streaming responses**: Real-time response generation

### Web Integration/access

- **Web search**: Search the web using DuckDuckGo directly from chat
- **Smart search queries**: AI-powered search query optimization with spelling correction
- **Website content fetching**: Extract and include content from any website in your conversations
- **Multiple search modes**:
  - `search:query` - Basic web search with results added to context
  - `searchask:query|question` - Search and ask a specific question about results
  - `websearch:question` - AI-generated search with automatic query optimization
  - `site:url` - Fetch content from a specific website

### Session Management

- **Conversation history**: Save and restore chat sessions with timestamps
- **Sessions**: Continue conversations across sessions
- **Context**: Clear context, load previous sessions, and manage conversation flow
- **Multiple session support**: Switch between different conversations

### File Integration

- **Local file support**: Include files from your filesystem in conversations (up to 2MB per file)
- **Multiple file formats**: Support for text files, code, documentation, and more
- **Context-aware processing**: Files are integrated into conversation contexxt

TODO--------------------------------------------------------------|

## Screenshots

### Chat Interface

![Chat](https://raw.githubusercontent.com/QinCai-rui/mdllama/refs/heads/main/assets/chat.png)

### Help

![Help](https://github.com/user-attachments/assets/bb080fe0-9e7b-4ba0-b9c8-f4fe1415082f)

## Interactive Commands

When using `mdllama run` for interactive chat, you have access to special commands:

### Basic Commands

- `exit` or `quit` - End the interactive session
- `clear` - Clear the current conversation context
- `models` - Show numbered list of available models for selection
- `"""` - Start/end multiline input mode for longer messages

### File and Content Integration

- `file:path/to/file` - Include local file content in your next message
- `site:url` - Fetch and include website content in conversation context
- `system:prompt` - Set or change the system prompt (use without prompt to clear)

### Web Search Commands

- `search:query` - Search the web and add results to conversation context
- `searchask:query|question` - Search for specific query and ask a question about results
- `websearch:question` - Let AI generate optimized search query and get results

### Runtime Controls

- `temp:value` - Change temperature setting (0.0 to 1.0)
- `model:name` - Switch to different model (or show list if name omitted)

### Command Line Options

- `mdllama search "query"` - Standalone web search command
- `mdllama sessions` - List all saved conversation sessions
- `mdllama load-session session_id` - Load a previous conversation
- `mdllama clear-context` - Clear current conversation context
- `mdllama models` - List available models
- `mdllama pull model_name` - Download a model from Ollama registry

## OpenAI and Provider Support

### Supported Providers

- **Ollama**: Local models running on your machine
- **OpenAI**: Official OpenAI API (GPT-3.5, GPT-4, etc.)
- **OpenAI-compatible**: Any API that follows OpenAI's format (Hackclub AI, LocalAI, etc.)

### Setup Instructions

#### For Ollama (Default)
```bash
mdllama setup
# Or specify explicitly
mdllama setup --provider ollama
```

#### For OpenAI
```bash
mdllama setup --provider openai
# Will prompt for your OpenAI API key
```

#### For OpenAI-Compatible APIs
```bash
mdllama setup --provider openai --openai-api-base https://ai.hackclub.com
# Then provide your API key when prompted
```

### Usage Examples

```bash
# Use with OpenAI
mdllama chat --provider openai "Explain quantum computing"

# Use with specific model and provider
mdllama run --provider openai --model gpt-4

# Interactive session with streaming
mdllama run --provider openai --stream --render-markdown
```

## Live Demo

Go to this [mdllama demo](https://mdllama-demo.qincai.xyz) to try it out live in your browser. The API key is `9c334d5a0863984b641b1375a850fb5d`

> [!NOTE]
> Try asking the model to give you some markdown-formatted text, or test the web search features:
>
> - `Give me a markdown-formatted text about the history of AI.`
> - `search:Python 3.13` (web search)
> - `site:python.org` (fetch website content)
> - `websearch:What are the latest Python features?` (AI-powered search)

So try it out and see how it works!

## Installation

### Install using package manager (recommended)

#### Debian/Ubuntu Installation

1. Add the PPA to your sources list:

   ```bash
   echo 'deb [trusted=yes] https://packages.qincai.xyz/debian stable main' | sudo tee /etc/apt/sources.list.d/qincai-ppa.list
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

2. (Optional, highly recommended) To enable as a repository for updates, create `/etc/yum.repos.d/qincai-ppa.repo`:

   ```ini
   [qincai-ppa]
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
   > ~~The `ollama` library is not installed by default in the RPM package since there is no system `ollama` package avaliable (`python3-ollama`). You need to install it manually using pip in order to use `mdllama` with Ollama models.~~ This issue has been resolved by including a post-installation script for RPM packages that automatically installs the `ollama` library using pip.

---

### PyPI Installation (Cross-Platform)

Install via pip (recommended for Windows/macOS and Python virtual environments):

```bash
pip install mdllama
```

### Traditional Bash Script Installation (Linux)

> [!WARNING]
> This method of un-/installation is deprecated and shall be avoided
> Please use the `pip` method, or use DEB/RPM packages instead

To install **mdllama** using the traditional bash script, run:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/QinCai-rui/mdllama/refs/heads/main/install.sh)
```

To uninstall **mdllama**, run:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/QinCai-rui/mdllama/refs/heads/main/uninstall.sh)
```

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

---
