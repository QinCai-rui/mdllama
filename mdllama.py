#!/usr/bin/env python3
"""
Ollama & Groq CLI - A command-line interface for both Ollama and Groq APIs
Features:
- Support for both Ollama (local) and Groq (cloud) APIs
- Interactive chat mode with multiline support
- Terminal formatting and colors
- Context management for conversations
- File upload support
- Response streaming
- Multiple model selection
- History saving and loading
- Real-time markdown rendering
- Clickable links in terminal
"""

import argparse
import json
import os
import sys
import readline  # For better input handling (command history)
from typing import List, Dict, Optional, Union, Any, Literal
from pathlib import Path
import datetime
import re  # For URL detection
import requests  # For direct API calls to Ollama if needed

try:
    # Try to import the Ollama Python client
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.live import Live
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

CONFIG_DIR = Path.home() / ".llm-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_DIR = CONFIG_DIR / "history"
OLLAMA_DEFAULT_HOST = "http://localhost:11434"

# ANSI color codes for terminal formatting
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Special formats for links
    LINK = "\033]8;;"  # OSC 8 hyperlink start
    LINK_END = "\033]8;;\033\\"  # OSC 8 hyperlink end


class LLM_CLI:
    def __init__(self, 
                 use_colors=True, 
                 render_markdown=True, 
                 provider: Literal["groq", "ollama", "auto"] = "auto"):
        self.groq_client = None
        self.ollama_client = None
        self.api_key = None
        self.config = self._load_config()
        self.use_colors = use_colors
        self.render_markdown = render_markdown
        self.current_context: List[Dict[str, Any]] = []
        self.current_session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.provider = provider
        self.current_provider = None  # Will be set during client setup
        
        # Initialize rich console if available
        self.console = Console() if RICH_AVAILABLE else None
        
        # URL detection regex
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!$&\'()*+,;=:@/~]+)*(?:\?[-\w%!$&\'()*+,;=:@/~]*)?(?:#[-\w%!$&\'()*+,;=:@/~]*)?'
        )

    def _setup_groq_client(self):
        """Initialize the Groq client with API key from config or environment."""
        if not GROQ_AVAILABLE:
            self._print_error("Groq Python package not installed. Install with: pip install groq")
            return False
            
        self.api_key = self.config.get('groq_api_key') or os.environ.get("GROQ_API_KEY")
        
        if not self.api_key:
            return False
        
        try:
            self.groq_client = Groq(api_key=self.api_key)
            return True
        except Exception as e:
            self._print_error(f"Error initializing Groq client: {e}")
            return False
            
    def _setup_ollama_client(self):
        """Initialize the Ollama client."""
        if not OLLAMA_AVAILABLE:
            self._print_error("Ollama Python package not installed. Install with: pip install ollama")
            return False
            
        self.ollama_host = self.config.get('ollama_host') or os.environ.get("OLLAMA_HOST") or OLLAMA_DEFAULT_HOST
        
        try:
            # Check if Ollama is running by making a simple request
            try:
                test_response = requests.get(f"{self.ollama_host}/api/tags")
                if test_response.status_code != 200:
                    self._print_error(f"Ollama server not responding at {self.ollama_host}")
                    return False
            except requests.exceptions.ConnectionError:
                self._print_error(f"Could not connect to Ollama at {self.ollama_host}")
                return False
                
            # Initialize Ollama client with the host
            self.ollama_client = ollama.Client(host=self.ollama_host)
            return True
        except Exception as e:
            self._print_error(f"Error initializing Ollama client: {e}")
            return False

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True)
            HISTORY_DIR.mkdir(exist_ok=True)
            
        if not CONFIG_FILE.exists():
            return {}
            
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_config(self):
        """Save current configuration to file."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _print_error(self, message):
        """Print an error message with color if enabled."""
        if self.use_colors:
            print(f"{Colors.RED}{message}{Colors.RESET}")
        else:
            print(f"Error: {message}")
            
    def _print_success(self, message):
        """Print a success message with color if enabled."""
        if self.use_colors:
            print(f"{Colors.GREEN}{message}{Colors.RESET}")
        else:
            print(message)
            
    def _print_info(self, message):
        """Print an info message with color if enabled."""
        if self.use_colors:
            print(f"{Colors.CYAN}{message}{Colors.RESET}")
        else:
            print(message)
            
    def _print_command(self, message):
        """Print a command reference with color if enabled."""
        if self.use_colors:
            print(f"{Colors.YELLOW}{message}{Colors.RESET}")
        else:
            print(message)
            
    def _format_links(self, text):
        """Format links in text to be clickable in the terminal."""
        if not self.use_colors:
            return text
            
        # Find all URLs in the text
        position = 0
        formatted_text = ""
        
        for match in self.url_pattern.finditer(text):
            start, end = match.span()
            url = text[start:end]
            
            # Add text before the URL
            formatted_text += text[position:start]
            
            # Add the formatted URL
            formatted_text += f"{Colors.LINK}{url}{Colors.LINK_END}{Colors.BLUE}{Colors.UNDERLINE}{url}{Colors.RESET}"
            
            position = end
            
        # Add remaining text after the last URL
        formatted_text += text[position:]
        
        return formatted_text
    
    def _print_with_links(self, text, color=None):
        """Print text with formatted, clickable links."""
        if RICH_AVAILABLE and self.console:
            # Use Rich to format text with clickable links
            rich_text = Text.from_markup(text)
            
            # Style links in the text
            for match in self.url_pattern.finditer(text):
                url = match.group(0)
                start, end = match.span()
                rich_text.stylize(f"link {url}", start, end)
                rich_text.stylize("bold blue underline", start, end)
                
            self.console.print(rich_text)
        else:
            # Fall back to ANSI escape sequences
            formatted_text = self._format_links(text)
            if color and self.use_colors:
                print(f"{color}{formatted_text}{Colors.RESET}")
            else:
                print(formatted_text)

    def setup(self, groq_api_key: Optional[str] = None, ollama_host: Optional[str] = None):
        """Set up the CLI with API keys and other configurations."""
        self._print_info("Setting up LLM CLI...")
        
        # Groq setup
        if groq_api_key:
            self.config['groq_api_key'] = groq_api_key
        else:
            groq_api_key = input("Enter your Groq API key (leave empty to use environment variable or skip): ").strip()
            if groq_api_key:
                self.config['groq_api_key'] = groq_api_key
                
        # Ollama setup
        if ollama_host:
            self.config['ollama_host'] = ollama_host
        else:
            ollama_host = input(f"Enter your Ollama host URL (leave empty for default: {OLLAMA_DEFAULT_HOST}): ").strip()
            if ollama_host:
                self.config['ollama_host'] = ollama_host
                
        self._save_config()
        
        # Test connections
        groq_success = self._setup_groq_client()
        ollama_success = self._setup_ollama_client()
        
        if groq_success:
            self._print_success("Groq API connected successfully!")
        else:
            self._print_info("Groq API not configured or connection failed.")
            
        if ollama_success:
            self._print_success("Ollama connected successfully!")
        else:
            self._print_info("Ollama not configured or connection failed.")
            
        if not groq_success and not ollama_success:
            self._print_error("No LLM providers configured successfully. Please check your settings.")
        else:
            self._print_success("Setup complete!")

    def _determine_provider(self, model_name: str):
        """Determine which provider to use based on model name and availability."""
        if self.provider != "auto":
            return self.provider
            
        # Common Groq model prefixes
        groq_prefixes = ["meta-llama", "llama-", "gemma-", "mixtral-"]
        
        # Check if model name matches Groq model patterns
        is_likely_groq = any(model_name.startswith(prefix) for prefix in groq_prefixes) or "-" in model_name
        
        # If model looks like a Groq model and Groq is available, use Groq
        if is_likely_groq and self.groq_client is not None:
            return "groq"
        # Otherwise if Ollama is available, use Ollama
        elif self.ollama_client is not None:
            return "ollama"
        # Fall back to Groq if it's available
        elif self.groq_client is not None:
            return "groq"
        # No providers available
        else:
            return None

    def list_models(self):
        """List available models from both Groq and Ollama."""
        # List Groq models if available
        if self.groq_client or self._setup_groq_client():
            try:
                models = self.groq_client.models.list()
                self._print_info("Available Groq models:")
                for model in models.data:
                    if self.use_colors:
                        print(f"- {Colors.BRIGHT_GREEN}{model.id}{Colors.RESET}")
                    else:
                        print(f"- {model.id}")
            except Exception as e:
                self._print_error(f"Error listing Groq models: {e}")
                
        # List Ollama models if available
        if self.ollama_client or self._setup_ollama_client():
            try:
                # Direct REST API call to get models
                response = requests.get(f"{self.ollama_host}/api/tags")
                if response.status_code == 200:
                    models_data = response.json()
                    self._print_info("Available Ollama models:")
                    for model in models_data.get('models', []):
                        model_name = model.get('name', 'Unknown')
                        if self.use_colors:
                            print(f"- {Colors.BRIGHT_YELLOW}{model_name}{Colors.RESET}")
                        else:
                            print(f"- {model_name}")
                else:
                    self._print_error(f"Error listing Ollama models: HTTP {response.status_code}")
            except Exception as e:
                self._print_error(f"Error listing Ollama models: {e}")

    def _ensure_client(self, provider=None):
        """Ensure the appropriate client is initialized before making API calls."""
        if provider == "groq" or (provider is None and self.provider == "groq"):
            if self.groq_client is None:
                if not self._setup_groq_client():
                    self._print_error("No Groq API key configured. Please run 'setup' command first.")
                    return False
            return True
            
        if provider == "ollama" or (provider is None and self.provider == "ollama"):
            if self.ollama_client is None:
                if not self._setup_ollama_client():
                    self._print_error("Ollama not configured or not running. Please check Ollama installation.")
                    return False
            return True
            
        # If auto or not specified, try to ensure at least one client is available
        if self.groq_client is None and self.ollama_client is None:
            groq_ok = self._setup_groq_client()
            ollama_ok = self._setup_ollama_client()
            if not groq_ok and not ollama_ok:
                self._print_error("No LLM providers configured. Please run 'setup' command first.")
                return False
        return True

    def _prepare_messages(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        image_paths: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Prepare messages for completion, including context and images."""
        messages = self.current_context.copy()

        # Add system prompt if provided and not already present
        if system_prompt and not any(m.get("role") == "system" for m in messages):
            messages.append({"role": "system", "content": system_prompt})
            
        # Handle image uploads if provided
        if image_paths:
            # Only Groq supports images currently
            if self.current_provider == "groq":
                content_parts = []
                
                # Add each image as a content part
                for img_path in image_paths:
                    try:
                        with open(img_path, "rb") as img_file:
                            # For simplicity, we'll use base64 encoding
                            import base64
                            image_data = base64.b64encode(img_file.read()).decode("utf-8")
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            })
                    except Exception as e:
                        self._print_error(f"Error processing image {img_path}: {e}")
                
                # Add the text prompt
                content_parts.append({"type": "text", "text": prompt})
                
                # Add the multimodal message
                messages.append({"role": "user", "content": content_parts})
            else:
                self._print_error("Image support is only available with Groq API.")
                # Add text-only message
                messages.append({"role": "user", "content": prompt})
        else:
            # Simple text-only message
            messages.append({"role": "user", "content": prompt})
            
        return messages

    def _save_history(self, messages: List[Dict[str, Any]]):
        """Save conversation history to file."""
        history_file = HISTORY_DIR / f"session_{self.current_session_id}.json"
        
        with open(history_file, 'w') as f:
            json.dump(messages, f, indent=2)
            
        self._print_success(f"History saved to {history_file}")

    def _load_history(self, session_id: str):
        """Load conversation history from file."""
        try:
            history_file = HISTORY_DIR / f"session_{session_id}.json"
            with open(history_file, 'r') as f:
                self.current_context = json.load(f)
            
            self.current_session_id = session_id
            self._print_success(f"Loaded history from session {session_id}")
            return True
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._print_error(f"Error loading history: {e}")
            return False

    def list_sessions(self):
        """List all saved conversation sessions."""
        if not HISTORY_DIR.exists():
            self._print_info("No session history found.")
            return
            
        sessions = list(HISTORY_DIR.glob("session_*.json"))
        
        if not sessions:
            self._print_info("No session history found.")
            return
            
        self._print_info("Available sessions:")
        for session_file in sessions:
            session_id = session_file.stem.replace("session_", "")
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    message_count = len(data)
                    date = datetime.datetime.strptime(session_id, "%Y%m%d_%H%M%S")
                    if self.use_colors:
                        print(f"- {Colors.YELLOW}{session_id}{Colors.RESET}: {Colors.WHITE}{date.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET} ({message_count} messages)")
                    else:
                        print(f"- {session_id}: {date.strftime('%Y-%m-%d %H:%M:%S')} ({message_count} messages)")
            except:
                if self.use_colors:
                    print(f"- {Colors.YELLOW}{session_id}{Colors.RESET} {Colors.RED}(corrupted){Colors.RESET}")
                else:
                    print(f"- {session_id} (corrupted)")

    def _render_markdown(self, text):
        """Render markdown text if rich is available, otherwise just print it."""
        if not self.render_markdown:
            return
            
        if RICH_AVAILABLE and self.console:
            print("\n--- Rendered Markdown ---")
            # Use Rich's Markdown renderer which automatically formats links
            self.console.print(Markdown(text))
            print("-------------------------")
        else:
            # If rich is not available, we can still try a simple markdown rendering
            # using ANSI escape codes, but for now we'll just skip rendering
            if self.render_markdown:
                self._print_info("Rich library not available. Install it with: pip install rich")

    def _stream_with_live_markdown(self, completion_generator):
        """Stream response with live markdown rendering."""
        full_response = ""
        
        # Open a live display for updating markdown in real time
        with Live(Markdown(""), console=self.console, refresh_per_second=10) as live_display:
            for chunk in completion_generator:
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
                        
                        # Update the markdown display with the full response so far
                        try:
                            live_display.update(Markdown(full_response))
                        except Exception:
                            # If rendering fails, just show the text
                            live_display.update(full_response)
        
        return full_response

    def _process_links_in_markdown(self, text):
        """Process markdown links to make them clickable in terminal."""
        # Process [text](url) style markdown links
        md_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        def replace_with_clickable(match):
            text, url = match.groups()
            if self.use_colors:
                return f"{Colors.LINK}{url}{Colors.LINK_END}{Colors.BLUE}{Colors.UNDERLINE}{text}{Colors.RESET}"
            else:
                return f"{text} ({url})"
                
        processed_text = md_link_pattern.sub(replace_with_clickable, text)
        
        # Also process plain URLs that aren't part of markdown links
        return self._format_links(processed_text)
        
    def _stream_ollama_response(self, generator):
        """Stream response from Ollama."""
        full_response = ""
        buffer = ""  # Buffer to accumulate text for link processing
        
        for chunk in generator:
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                if content:
                    buffer += content
                    full_response += content
                    
                    # Process buffer when we have enough context to identify links
                    # or when we encounter specific characters that might delimit links
                    if len(buffer) > 100 or any(c in buffer for c in [' ', '\n', '.', ',', ')']):
                        if self.use_colors:
                            processed_buffer = self._process_links_in_markdown(buffer)
                            print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
                        else:
                            print(buffer, end="", flush=True)
                        buffer = ""  # Clear the buffer after processing
        
        # Process any remaining text in the buffer
        if buffer:
            if self.use_colors:
                processed_buffer = self._process_links_in_markdown(buffer)
                print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
            else:
                print(buffer, end="", flush=True)
                
        print()  # Add final newline
        
        return full_response

    def complete(
        self,
        prompt: str,
        model: str = "meta-llama/llama-4-scout-17b-16e-instruct",
        stream: bool = False,
        system_prompt: Optional[str] = None,
        image_paths: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        file_paths: Optional[List[str]] = None,
        keep_context: bool = True,
        save_history: bool = False
    ) -> Optional[str]:
        """Generate a completion from Groq or Ollama API."""
        # Determine which provider to use for this model
        self.current_provider = self._determine_provider(model)
        
        if not self.current_provider:
            self._print_error("No available provider for this model.")
            return None
            
        if not self._ensure_client(self.current_provider):
            return None

        # Prepare any file attachments
        if file_paths:
            for file_path in file_paths:
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        file_name = Path(file_path).name
                        prompt += f"\n\nContents of {file_name}:\n```\n{content}\n```"
                except Exception as e:
                    self._print_error(f"Error reading file {file_path}: {e}")

        # Prepare messages including context
        messages = self._prepare_messages(prompt, system_prompt, image_paths)

        try:
            if self.current_provider == "groq":
                return self._complete_with_groq(
                    messages, model, stream, temperature, max_tokens, keep_context, save_history
                )
            else:  # ollama
                return self._complete_with_ollama(
                    messages, model, stream, temperature, max_tokens, keep_context, save_history
                )
                
        except Exception as e:
            self._print_error(f"Error during completion: {e}")
            return None

    def _complete_with_groq(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
        keep_context: bool,
        save_history: bool
    ) -> Optional[str]:
        """Complete using Groq API."""
        # Set up completion parameters
        completion_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        
        if max_tokens:
            completion_params["max_tokens"] = max_tokens
            
        if stream:
            # Check if we should use live markdown rendering
            if self.render_markdown and RICH_AVAILABLE and self.console:
                # Use live display for streaming markdown
                full_response = self._stream_with_live_markdown(
                    self.groq_client.chat.completions.create(**completion_params)
                )
            else:
                # Standard streaming without markdown rendering
                full_response = ""
                buffer = ""  # Buffer to accumulate text for link processing
                
                for chunk in self.groq_client.chat.completions.create(**completion_params):
                    if chunk.choices:
                        content = chunk.choices[0].delta.content
                        if content:
                            buffer += content
                            full_response += content
                            
                            # Process buffer when we have enough context to identify links
                            if len(buffer) > 100 or any(c in buffer for c in [' ', '\n', '.', ',', ')']):
                                if self.use_colors:
                                    processed_buffer = self._process_links_in_markdown(buffer)
                                    print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
                                else:
                                    print(buffer, end="", flush=True)
                                buffer = ""  # Clear the buffer after processing
                
                # Process any remaining text in the buffer
                if buffer:
                    if self.use_colors:
                        processed_buffer = self._process_links_in_markdown(buffer)
                        print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
                    else:
                        print(buffer, end="", flush=True)
                        
                print()  # Add final newline
                
                # Render markdown after streaming if enabled but not streamed
                if self.render_markdown and not (RICH_AVAILABLE and self.console):
                    self._render_markdown(full_response)
            
            # Add the assistant's response to the context if keeping context
            if keep_context:
                user_message = messages[-1]  # Get the last user message
                self.current_context.append(user_message)
                self.current_context.append({"role": "assistant", "content": full_response})
            
            return full_response
        else:
            # Get the full response at once
            response = self.groq_client.chat.completions.create(**completion_params)
            if response.choices:
                full_response = response.choices[0].message.content
                
                # For non-streaming responses with markdown
                if self.render_markdown and RICH_AVAILABLE and self.console:
                    self.console.print(Markdown(full_response))
                else:
                    # Process links in the full response
                    processed_response = self._process_links_in_markdown(full_response)
                    if self.use_colors:
                        print(f"{Colors.GREEN}{processed_response}{Colors.RESET}")
                    else:
                        print(full_response)
                    
                    # Render markdown after response if enabled but not rendered
                    if self.render_markdown and not (RICH_AVAILABLE and self.console):
                        self._render_markdown(full_response)
                
                # Add to context if keeping context
                if keep_context:
                    user_message = messages[-1]  # Get the last user message
                    self.current_context.append(user_message)
                    self.current_context.append({"role": "assistant", "content": full_response})
                
                return full_response
        
        # Save history if requested
        if save_history:
            self._save_history(self.current_context)
    
    def _complete_with_ollama(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
        keep_context: bool,
        save_history: bool
    ) -> Optional[str]:
        """Complete using Ollama API."""
        # Set up completion parameters
        # Note: The Ollama API might have different parameter names compared to the OpenAI/Groq API
        completion_params = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        
        # Add temperature only if it's specified (Ollama might use different defaults)
        if temperature != 0.7:  # Only if not default
            # Different versions of Ollama Python client have different parameter names
            try:
                # Use direct API endpoint to avoid compatibility issues
                base_url = self.ollama_host.rstrip('/')
                api_endpoint = f"{base_url}/api/chat"
                
                # Format messages for direct API call
                payload = {
                    "model": model,
                    "messages": messages,
                    "stream": stream,
                    "options": {
                        "temperature": temperature
                    }
                }
                
                if max_tokens:
                    payload["options"]["num_predict"] = max_tokens
                
                if stream:
                    # Handle streaming response
                    full_response = ""
                    response = requests.post(api_endpoint, json=payload, stream=True)
                    
                    if response.status_code == 200:
                        buffer = ""
                        content = ""
                        
                        for line in response.iter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    if 'message' in chunk and 'content' in chunk['message']:
                                        chunk_content = chunk['message']['content']
                                        if chunk_content:
                                            buffer += chunk_content
                                            full_response += chunk_content
                                            content += chunk_content
                                            
                                            # Process buffer when appropriate
                                            if len(buffer) > 100 or any(c in buffer for c in [' ', '\n', '.', ',', ')']):
                                                if self.use_colors:
                                                    processed_buffer = self._process_links_in_markdown(buffer)
                                                    print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
                                                else:
                                                    print(buffer, end="", flush=True)
                                                buffer = ""
                                except json.JSONDecodeError:
                                    continue
                        
                        # Process any remaining text in the buffer
                        if buffer:
                            if self.use_colors:
                                processed_buffer = self._process_links_in_markdown(buffer)
                                print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
                            else:
                                print(buffer, end="", flush=True)
                                
                        print()  # Add final newline
                    else:
                        self._print_error(f"Ollama API error: {response.status_code} - {response.text}")
                        return None
                else:
                    # Non-streaming response
                    response = requests.post(api_endpoint, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        if 'message' in data and 'content' in data['message']:
                            full_response = data['message']['content']
                            
                            # For non-streaming responses with markdown
                            if self.render_markdown and RICH_AVAILABLE and self.console:
                                self.console.print(Markdown(full_response))
                            else:
                                # Process links in the full response
                                processed_response = self._process_links_in_markdown(full_response)
                                if self.use_colors:
                                    print(f"{Colors.GREEN}{processed_response}{Colors.RESET}")
                                else:
                                    print(full_response)
                                
                                # Render markdown after response if enabled but not rendered
                                if self.render_markdown and not (RICH_AVAILABLE and self.console):
                                    self._render_markdown(full_response)
                        else:
                            self._print_error("Invalid response format from Ollama API.")
                            return None
                    else:
                        self._print_error(f"Ollama API error: {response.status_code} - {response.text}")
                        return None
                
                # Add to context if keeping context
                if keep_context:
                    user_message = messages[-1]  # Get the last user message
                    self.current_context.append(user_message)
                    self.current_context.append({"role": "assistant", "content": full_response})
                
                # Save history if requested
                if save_history:
                    self._save_history(self.current_context)
                    
                return full_response
                
            except Exception as e:
                self._print_error(f"Error with direct Ollama API call: {e}")
                return None
                
        else:
            # Use the Python client for default parameters
            try:
                if stream:
                    # Stream the response using Ollama
                    full_response = ""
                    generator = self.ollama_client.chat(**completion_params)
                    
                    if self.render_markdown and RICH_AVAILABLE and self.console:
                        # Use Rich for rendering
                        accumulated_text = ""
                        with Live(Markdown(""), console=self.console, refresh_per_second=10) as live_display:
                            for chunk in generator:
                                if 'message' in chunk and 'content' in chunk['message']:
                                    content = chunk['message']['content']
                                    if content:
                                        full_response += content
                                        accumulated_text += content
                                        try:
                                            live_display.update(Markdown(accumulated_text))
                                        except Exception:
                                            live_display.update(accumulated_text)
                    else:
                        # Standard streaming
                        full_response = self._stream_ollama_response(generator)
                        
                        # Render markdown after streaming if enabled
                        if self.render_markdown and not (RICH_AVAILABLE and self.console):
                            self._render_markdown(full_response)
                    
                    # Add to context if keeping context
                    if keep_context:
                        user_message = messages[-1]  # Get the last user message
                        self.current_context.append(user_message)
                        self.current_context.append({"role": "assistant", "content": full_response})
                    
                else:
                    # Get the full response at once
                    response = self.ollama_client.chat(**completion_params)
                    if 'message' in response and 'content' in response['message']:
                        full_response = response['message']['content']
                        
                        # For non-streaming responses with markdown
                        if self.render_markdown and RICH_AVAILABLE and self.console:
                            self.console.print(Markdown(full_response))
                        else:
                            # Process links in the full response
                            processed_response = self._process_links_in_markdown(full_response)
                            if self.use_colors:
                                print(f"{Colors.GREEN}{processed_response}{Colors.RESET}")
                            else:
                                print(full_response)
                            
                            # Render markdown after response if enabled but not rendered
                            if self.render_markdown and not (RICH_AVAILABLE and self.console):
                                self._render_markdown(full_response)
                        
                        # Add to context if keeping context
                        if keep_context:
                            user_message = messages[-1]  # Get the last user message
                            self.current_context.append(user_message)
                            self.current_context.append({"role": "assistant", "content": full_response})
                    else:
                        self._print_error("Invalid response format from Ollama.")
                        return None
                
                # Save history if requested
                if save_history:
                    self._save_history(self.current_context)
                    
                return full_response
                    
            except Exception as e:
                self._print_error(f"Error with Ollama Python client: {e}")
                # Try direct API call as fallback
                return self._complete_with_ollama_direct_api(
                    messages, model, stream, temperature, max_tokens, keep_context, save_history
                )

    def _complete_with_ollama_direct_api(
        self,
        messages,
        model,
        stream,
        temperature,
        max_tokens,
        keep_context,
        save_history
    ):
        """Fallback method to use direct API calls to Ollama."""
        try:
            base_url = self.ollama_host.rstrip('/')
            api_endpoint = f"{base_url}/api/chat"
            
            # Format messages for direct API call
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {}
            }
            
            if temperature != 0.7:
                payload["options"]["temperature"] = temperature
                
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
            
            if stream:
                # Handle streaming response
                full_response = ""
                response = requests.post(api_endpoint, json=payload, stream=True)
                
                if response.status_code == 200:
                    buffer = ""
                    
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                if 'message' in chunk and 'content' in chunk['message']:
                                    content = chunk['message']['content']
                                    if content:
                                        buffer += content
                                        full_response += content
                                        
                                        # Process buffer when appropriate
                                        if len(buffer) > 100 or any(c in buffer for c in [' ', '\n', '.', ',', ')']):
                                            if self.use_colors:
                                                processed_buffer = self._process_links_in_markdown(buffer)
                                                print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
                                            else:
                                                print(buffer, end="", flush=True)
                                            buffer = ""
                            except json.JSONDecodeError:
                                continue
                    
                    # Process any remaining text in the buffer
                    if buffer:
                        if self.use_colors:
                            processed_buffer = self._process_links_in_markdown(buffer)
                            print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
                        else:
                            print(buffer, end="", flush=True)
                            
                    print()  # Add final newline
                else:
                    self._print_error(f"Ollama API error: {response.status_code} - {response.text}")
                    return None
            else:
                # Non-streaming response
                response = requests.post(api_endpoint, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if 'message' in data and 'content' in data['message']:
                        full_response = data['message']['content']
                        
                        # For non-streaming responses with markdown
                        if self.render_markdown and RICH_AVAILABLE and self.console:
                            self.console.print(Markdown(full_response))
                        else:
                            # Process links in the full response
                            processed_response = self._process_links_in_markdown(full_response)
                            if self.use_colors:
                                print(f"{Colors.GREEN}{processed_response}{Colors.RESET}")
                            else:
                                print(full_response)
                            
                            # Render markdown after response if enabled but not rendered
                            if self.render_markdown and not (RICH_AVAILABLE and self.console):
                                self._render_markdown(full_response)
                    else:
                        self._print_error("Invalid response format from Ollama API.")
                        return None
                else:
                    self._print_error(f"Ollama API error: {response.status_code} - {response.text}")
                    return None
            
            # Add to context if keeping context
            if keep_context:
                user_message = messages[-1]  # Get the last user message
                self.current_context.append(user_message)
                self.current_context.append({"role": "assistant", "content": full_response})
            
            # Save history if requested
            if save_history:
                self._save_history(self.current_context)
                
            return full_response
                
        except Exception as e:
            self._print_error(f"Error with direct Ollama API call: {e}")
            return None

    def clear_context(self):
        """Clear the current conversation context."""
        self.current_context = []
        self._print_success("Context cleared.")
        
    def read_multiline_input(self) -> str:
        """Read multiline input from the user, starting with triple quotes and ending with triple quotes."""
        lines = []
        if self.use_colors:
            print(f"{Colors.YELLOW}Enter your multiline input (end with \"\"\" on a new line):{Colors.RESET}")
        else:
            print("Enter your multiline input (end with \"\"\" on a new line):")
        
        while True:
            try:
                line = input()
                if line.strip() == '"""':
                    break
                lines.append(line)
            except EOFError:
                break
                
        return "\n".join(lines)
        
    def interactive_chat(
        self,
        model: str = "meta-llama/llama-4-scout-17b-16e-instruct",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        save_history: bool = False
    ):
        """Start an interactive chat session."""
        # Determine which provider to use for this model
        self.current_provider = self._determine_provider(model)
        
        if not self.current_provider:
            self._print_error("No available provider for this model.")
            return
            
        if not self._ensure_client(self.current_provider):
            return
            
        # Print header with model info and date/time
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        provider_display = self.current_provider.upper()
        
        if self.use_colors:
            provider_color = Colors.BRIGHT_CYAN if self.current_provider == "groq" else Colors.BRIGHT_YELLOW
            print(f"{Colors.BG_BLUE}{Colors.WHITE} {provider_display} CLI {Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}Model:{Colors.RESET} {provider_color}{model}{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}Time: {Colors.RESET}{Colors.WHITE}{current_time}{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}User: {Colors.RESET}{Colors.WHITE}{os.environ.get('USER', 'unknown')}{Colors.RESET}")
            print()
        else:
            print(f"{provider_display} CLI")
            print(f"Model: {model}")
            print(f"Time: {current_time}")
            print(f"User: {os.environ.get('USER', 'unknown')}")
            print()
        
        # Print help information
        self._print_info("Interactive chat commands:")
        self._print_command("exit/quit      - End the conversation")
        self._print_command("clear          - Clear the conversation context")
        self._print_command("file:<path>    - Include a file in your next message")
        self._print_command("system:<prompt>- Set or change the system prompt")
        self._print_command("temp:<value>   - Change the temperature setting")
        self._print_command("model:<name>   - Switch to a different model")
        self._print_command("\"\"\"           - Start/end a multiline message")
        print()
        
        # Add system prompt if provided
        if system_prompt:
            self.current_context.append({"role": "system", "content": system_prompt})
            if self.use_colors:
                print(f"{Colors.MAGENTA}System:{Colors.RESET} {system_prompt}")
            else:
                print(f"System: {system_prompt}")
            print()
            
        try:
            while True:
                # Get user input
                try:
                    if self.use_colors:
                        user_input = input(f"{Colors.BOLD}{Colors.BLUE}You:{Colors.RESET} ")
                    else:
                        user_input = input("You: ")
                except EOFError:  # Handle Ctrl+D
                    print("\nExiting interactive chat...")
                    break
                
                # Check for special commands
                if user_input.lower() in ['exit', 'quit']:
                    print("Exiting interactive chat...")
                    break
                    
                elif user_input.lower() == 'clear':
                    self.clear_context()
                    # Re-add system prompt if it was set
                    if system_prompt:
                        self.current_context.append({"role": "system", "content": system_prompt})
                    continue
                    
                elif user_input.startswith('file:'):
                    file_path = user_input[5:].strip()
                    try:
                        with open(file_path, 'r') as f:
                            file_content = f.read()
                            file_name = Path(file_path).name
                            self._print_success(f"File '{file_name}' loaded. Include it in your next message.")
                            if self.use_colors:
                                user_input = input(f"{Colors.BOLD}{Colors.BLUE}You:{Colors.RESET} ")
                            else:
                                user_input = input("You: ")
                            # Append file content to the user input
                            user_input += f"\n\nContents of {file_name}:\n```\n{file_content}\n```"
                    except Exception as e:
                        self._print_error(f"Error reading file: {e}")
                        continue
                
                elif user_input.startswith('system:'):
                    new_system_prompt = user_input[7:].strip()
                    # Remove any existing system prompts
                    self.current_context = [msg for msg in self.current_context if msg.get("role") != "system"]
                    # Add the new system prompt
                    if new_system_prompt:
                        self.current_context.append({"role": "system", "content": new_system_prompt})
                        system_prompt = new_system_prompt
                        self._print_success("System prompt updated.")
                    else:
                        self._print_info("System prompt cleared.")
                    continue
                    
                elif user_input.startswith('temp:'):
                    try:
                        temperature = float(user_input[5:].strip())
                        self._print_success(f"Temperature set to {temperature}")
                    except ValueError:
                        self._print_error("Invalid temperature value. Please use a number between 0 and 1.")
                    continue
                    
                elif user_input.startswith('model:'):
                    new_model = user_input[6:].strip()
                    if new_model:
                        # Check if we need to switch providers
                        new_provider = self._determine_provider(new_model)
                        if new_provider and self._ensure_client(new_provider):
                            model = new_model
                            self.current_provider = new_provider
                            self._print_success(f"Switched to model: {model} (Provider: {self.current_provider})")
                        else:
                            self._print_error(f"Could not switch to model: {new_model}")
                    else:
                        self._print_error("Please specify a model name.")
                    continue
                
                # Handle multiline input
                elif user_input.strip() == '"""':
                    user_input = self.read_multiline_input()
                    self._print_success("Multiline input received")
                    
                # Skip empty inputs
                if not user_input.strip():
                    continue
                
                # Process regular user input
                if self.use_colors:
                    print(f"\n{Colors.BOLD}{Colors.GREEN}Assistant:{Colors.RESET}")
                else:
                    print("\nAssistant:")
                    
                self.complete(
                    prompt=user_input,
                    model=model,
                    stream=True,  # Always stream in interactive mode
                    temperature=temperature,
                    max_tokens=max_tokens,
                    keep_context=True,
                    save_history=False  # Don't save after each message
                )
                
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting interactive chat...")
        
        # Save the final conversation if requested
        if save_history and self.current_context:
            self._save_history(self.current_context)
            self._print_success(f"Conversation saved to session {self.current_session_id}")


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(description="LLM CLI - A command-line interface for Groq and Ollama APIs")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up the CLI with API keys")
    setup_parser.add_argument("--groq-api-key", help="Groq API key")
    setup_parser.add_argument("--ollama-host", help="Ollama host URL")
    
    # List models command
    subparsers.add_parser("models", help="List available models")
    
    # Chat completion command
    chat_parser = subparsers.add_parser("chat", help="Generate a chat completion")
    chat_parser.add_argument("prompt", help="The prompt to send to the API", nargs="?")
    chat_parser.add_argument("--model", "-m", default="meta-llama/llama-4-scout-17b-16e-instruct", 
                            help="Model to use for completion")
    chat_parser.add_argument("--provider", "-p", choices=["groq", "ollama", "auto"], default="auto",
                            help="Provider to use (groq, ollama, or auto-detect)")
    chat_parser.add_argument("--stream", "-s", action="store_true", help="Stream the response")
    chat_parser.add_argument("--system", help="System prompt to use")
    chat_parser.add_argument("--image", "-i", action="append", help="Path to image file(s) to include (Groq only)")
    chat_parser.add_argument("--temperature", "-t", type=float, default=0.7, help="Temperature for sampling")
    chat_parser.add_argument("--max-tokens", type=int, help="Maximum number of tokens to generate")
    chat_parser.add_argument("--file", "-f", action="append", help="Path to file(s) to include as context")
    chat_parser.add_argument("--context", "-c", action="store_true", help="Keep conversation context")
    chat_parser.add_argument("--save", action="store_true", help="Save conversation history")
    chat_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    chat_parser.add_argument("--render-markdown", "-r", action="store_true", help="Render markdown in the response")
    
    # File with prompt content
    chat_parser.add_argument("--prompt-file", help="Path to file containing the prompt")
    
    # Interactive chat command
    interactive_parser = subparsers.add_parser("run", help="Start an interactive chat session")
    interactive_parser.add_argument("--model", "-m", default="meta-llama/llama-4-scout-17b-16e-instruct", 
                                  help="Model to use for completion")
    interactive_parser.add_argument("--provider", "-p", choices=["groq", "ollama", "auto"], default="auto",
                                  help="Provider to use (groq, ollama, or auto-detect)")
    interactive_parser.add_argument("--system", "-s", help="System prompt to use")
    interactive_parser.add_argument("--temperature", "-t", type=float, default=0.7, help="Temperature for sampling")
    interactive_parser.add_argument("--max-tokens", type=int, help="Maximum number of tokens to generate")
    interactive_parser.add_argument("--save", action="store_true", help="Save conversation history")
    interactive_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    interactive_parser.add_argument("--render-markdown", "-r", action="store_true", help="Render markdown in the response")
    
    # Context and history management
    subparsers.add_parser("clear-context", help="Clear the current conversation context")
    
    # Session management
    subparsers.add_parser("sessions", help="List available conversation sessions")
    load_parser = subparsers.add_parser("load-session", help="Load a conversation session")
    load_parser.add_argument("session_id", help="Session ID to load")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Determine if colors should be used
    use_colors = True
    if hasattr(args, 'no_color') and args.no_color:
        use_colors = False
    # Also check if NO_COLOR environment variable is set (common standard)
    if os.environ.get('NO_COLOR') is not None:
        use_colors = False
        
    # Initialize CLI
    render_markdown = False
    if hasattr(args, 'render_markdown') and args.render_markdown:
        render_markdown = True
        
    # Check if Rich is available when markdown rendering is requested
    if render_markdown and not RICH_AVAILABLE:
        print("Warning: Rich library not available. Install it with: pip install rich")
        print("Markdown rendering will be disabled.")
        render_markdown = False
    
    # Set provider preference if specified
    provider = "auto"
    if hasattr(args, 'provider'):
        provider = args.provider
    
    cli = LLM_CLI(use_colors=use_colors, render_markdown=render_markdown, provider=provider)
    
    # Handle commands
    if args.command == "setup":
        cli.setup(args.groq_api_key, args.ollama_host)
    elif args.command == "models":
        cli.list_models()
    elif args.command == "chat":
        # Handle prompt from file if specified
        prompt = args.prompt
        if args.prompt_file:
            try:
                with open(args.prompt_file, 'r') as f:
                    prompt = f.read()
            except Exception as e:
                cli._print_error(f"Error reading prompt file: {e}")
                return
        
        # If no prompt is provided, read from stdin
        if not prompt:
            if not sys.stdin.isatty():
                prompt = sys.stdin.read()
            else:
                cli._print_error("No prompt provided. Use --prompt-file or pipe content.")
                return
        
        cli.complete(
            prompt=prompt,
            model=args.model,
            stream=args.stream,
            system_prompt=args.system,
            image_paths=args.image,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            file_paths=args.file,
            keep_context=args.context,
            save_history=args.save
        )
    elif args.command == "run":
        # Interactive chat mode
        cli.interactive_chat(
            model=args.model,
            system_prompt=args.system,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            save_history=args.save
        )
    elif args.command == "clear-context":
        cli.clear_context()
    elif args.command == "sessions":
        cli.list_sessions()
    elif args.command == "load-session":
        cli.load_history(args.session_id)
    else:
        # If no command is provided, print help
        parser.print_help()


if __name__ == "__main__":
    main()
