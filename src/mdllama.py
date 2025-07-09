__version__ = "1.2.5"
#!/usr/bin/env python3
"""
mdllama - A command-line interface for Ollama API
Features:
- Support for Ollama (local) API
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
#import readline  # For better input handling (command history)
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
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.live import Live
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

CONFIG_DIR = Path.home() / ".mdllama"
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
                 render_markdown=True):
        self.ollama_client = None
        self.config = self._load_config()
        self.use_colors = use_colors
        self.render_markdown = render_markdown
        self.current_context: List[Dict[str, Any]] = []
        self.current_session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize rich console if available
        self.console = Console() if RICH_AVAILABLE else None
        
        # URL detection regex
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!$&\'()*+,;=:@/~]+)*(?:\?[-\w%!$&\'()*+,;=:@/~]*)?(?:#[-\w%!$&\'()*+,;=:@/~]*)?'
        )

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

    def setup(self, ollama_host: Optional[str] = None, openai_api_base: Optional[str] = None, provider: str = "ollama"):
        """Set up the CLI with Ollama or OpenAI-compatible configuration."""
        self._print_info("Setting up mdllama...")
        provider = provider.lower()
        if provider == "ollama":
            # Ollama setup
            if ollama_host:
                self.config['ollama_host'] = ollama_host
            else:
                ollama_host = input(f"Enter your Ollama host URL (leave empty for default: {OLLAMA_DEFAULT_HOST}): ").strip()
                if ollama_host:
                    self.config['ollama_host'] = ollama_host
            self._save_config()
            # Test connection
            ollama_success = self._setup_ollama_client()
            if ollama_success:
                self._print_success("Ollama connected successfully!")
                self._print_success("Setup complete!")
            else:
                self._print_error("Ollama not configured or connection failed. Please check your settings.")
        elif provider == "openai":
            # OpenAI-compatible setup
            if openai_api_base:
                self.config['openai_api_base'] = openai_api_base
            else:
                openai_api_base = input("Enter your OpenAI-compatible API base URL (e.g. https://ai.hackclub.com): ").strip()
                if openai_api_base:
                    self.config['openai_api_base'] = openai_api_base
            self._save_config()
            # Test connection: try /v1/models, then /models, then /model (for hackclub/ai)
            test_url = self.config.get('openai_api_base', openai_api_base)
            if test_url:
                endpoints_to_try = ["/v1/models", "/models", "/model"]
                for endpoint in endpoints_to_try:
                    try:
                        resp = requests.get(test_url.rstrip('/') + endpoint)
                        if resp.status_code == 200:
                            self._print_success(f"OpenAI-compatible endpoint connected successfully using '{endpoint}'!")
                            self.config['openai_model_list_endpoint'] = endpoint
                            self._save_config()
                            self._print_success("Setup complete!")
                            break
                        elif resp.status_code == 404:
                            continue
                        else:
                            self._print_error(f"OpenAI-compatible endpoint error at {endpoint}: HTTP {resp.status_code}")
                            break
                    except Exception as e:
                        self._print_error(f"Error connecting to OpenAI-compatible endpoint at {endpoint}: {e}")
                        break
                else:
                    self._print_error("Could not connect to any known model listing endpoint (/v1/models, /models, /model). Please check your API base URL.")
            else:
                self._print_error("No OpenAI-compatible API base URL provided.")
        else:
            self._print_error(f"Unknown provider: {provider}. Use 'ollama' or 'openai'.")

    def list_models(self):
        """List available models from Ollama."""
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
        else:
            self._print_error("Ollama not configured or not running. Please check Ollama installation.")

    def _ensure_client(self):
        """Ensure the Ollama client is initialized before making API calls."""
        if self.ollama_client is None:
            if not self._setup_ollama_client():
                self._print_error("Ollama not configured or not running. Please run 'setup' command first.")
                return False
        return True

    def _prepare_messages(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Prepare messages for completion, including context."""
        messages = self.current_context.copy()

        # Add system prompt if provided and not already present
        if system_prompt and not any(m.get("role") == "system" for m in messages):
            messages.append({"role": "system", "content": system_prompt})
            
        # Add the text prompt
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
        model: str = "gemma3:1b",
        stream: bool = False,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        file_paths: Optional[List[str]] = None,
        keep_context: bool = True,
        save_history: bool = False
    ) -> Optional[str]:
        """Generate a completion from Ollama API."""
        
        if not self._ensure_client():
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
        messages = self._prepare_messages(prompt, system_prompt)

        try:
            return self._complete_with_ollama(
                messages, model, stream, temperature, max_tokens, keep_context, save_history
            )
                
        except Exception as e:
            self._print_error(f"Error during completion: {e}")
            return None

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
        # Set up completion parameters for Ollama API
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
        model: str = "gemma3:1b",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        save_history: bool = False,
        provider: str = "ollama",
        openai_api_base: Optional[str] = None
    ):
        """Start an interactive chat session for the selected provider, with unified UI."""
        provider = provider.lower() if provider else "ollama"
        # Print header with model info and date/time
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display_model = model
        # For openai, always display the selected model (from -m or prompt)
        # This ensures the UI header matches the user's selection
        if self.use_colors:
            print(f"{Colors.BG_BLUE}{Colors.WHITE} mdllama {Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}Model:{Colors.RESET} {Colors.BRIGHT_YELLOW}{display_model}{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}Time: {Colors.RESET}{Colors.WHITE}{current_time}{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}User: {Colors.RESET}{Colors.WHITE}{os.environ.get('USER', 'unknown')}{Colors.RESET}")
            print()
        else:
            print("mdllama")
            print(f"Model: {display_model}")
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
        context = []
        if system_prompt:
            context.append({"role": "system", "content": system_prompt})
            if self.use_colors:
                print(f"{Colors.MAGENTA}System:{Colors.RESET} {system_prompt}")
            else:
                print(f"System: {system_prompt}")
            print()
        # For Ollama, use self.current_context; for OpenAI, use local context
        if provider == "ollama":
            self.current_context = context.copy()
        else:
            # For OpenAI, context is local to this function
            pass
        try:
            while True:
                try:
                    if self.use_colors:
                        user_input = input(f"{Colors.BOLD}{Colors.BLUE}You:{Colors.RESET} ")
                    else:
                        user_input = input("You: ")
                except EOFError:
                    print("\nExiting interactive chat...")
                    break
                # Check for special commands
                if user_input.lower() in ['exit', 'quit']:
                    print("Exiting interactive chat...")
                    break
                elif user_input.lower() == 'clear':
                    if provider == "ollama":
                        self.clear_context()
                        if system_prompt:
                            self.current_context.append({"role": "system", "content": system_prompt})
                    else:
                        context = []
                        if system_prompt:
                            context.append({"role": "system", "content": system_prompt})
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
                            user_input += f"\n\nContents of {file_name}:\n```\n{file_content}\n```"
                    except Exception as e:
                        self._print_error(f"Error reading file: {e}")
                        continue
                elif user_input.startswith('system:'):
                    new_system_prompt = user_input[7:].strip()
                    if provider == "ollama":
                        self.current_context = [msg for msg in self.current_context if msg.get("role") != "system"]
                        if new_system_prompt:
                            self.current_context.append({"role": "system", "content": new_system_prompt})
                            system_prompt = new_system_prompt
                            self._print_success("System prompt updated.")
                        else:
                            system_prompt = None
                            self._print_info("System prompt cleared.")
                    else:
                        context = [msg for msg in context if msg.get("role") != "system"]
                        if new_system_prompt:
                            context.append({"role": "system", "content": new_system_prompt})
                            system_prompt = new_system_prompt
                            self._print_success("System prompt updated.")
                        else:
                            system_prompt = None
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
                        model = new_model
                        self._print_success(f"Switched to model: {model}")
                    else:
                        self._print_error("Please specify a model name.")
                    continue
                elif user_input.strip() == '"""':
                    user_input = self.read_multiline_input()
                    self._print_success("Multiline input received")
                if not user_input.strip():
                    continue
                if self.use_colors:
                    print(f"\n{Colors.BOLD}{Colors.GREEN}Assistant:{Colors.RESET}")
                else:
                    print("\nAssistant:")
                if provider == "ollama":
                    self.complete(
                        prompt=user_input,
                        model=model,
                        stream=True,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        keep_context=True,
                        save_history=False
                    )
                else:
                    context.append({"role": "user", "content": user_input})
                    url = (openai_api_base or self.config.get('openai_api_base', '')).rstrip('/') + "/chat/completions"
                    payload = {
                        "model": model,
                        "messages": context,
                        "stream": True,
                        "temperature": temperature
                    }
                    if max_tokens:
                        payload["max_tokens"] = max_tokens
                    headers = {"Content-Type": "application/json"}
                    try:
                        resp = requests.post(url, json=payload, headers=headers, stream=True)
                        full_response = ""
                        for line in resp.iter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line.decode())
                                    if 'choices' in chunk and chunk['choices']:
                                        delta = chunk['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            full_response += content
                                except Exception:
                                    continue
                        if self.render_markdown and RICH_AVAILABLE and self.console:
                            print()  # Ensure markdown starts on a new line
                            self.console.print(Markdown(full_response))
                        else:
                            print(full_response)
                    except Exception as e:
                        print(f"[OpenAI-compatible error: {e}]")
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting interactive chat...")
        if save_history and provider == "ollama" and self.current_context:
            self._save_history(self.current_context)
            self._print_success(f"Conversation saved to session {self.current_session_id}")




def get_version():
    return __version__


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(description="mdllama - A command-line interface for Ollama API and OpenAI-compatible endpoints")
    parser.add_argument('--version', action='version', version=f'%(prog)s {get_version()}')

    # Add provider and OpenAI-compatible endpoint option
    parser.add_argument('-p', '--provider', choices=['ollama', 'openai'], default=None, help='Provider to use: ollama or openai (default: ollama)')
    parser.add_argument('--openai-api-base', help='OpenAI-compatible API base URL (e.g. https://ai.hackclub.com)', default=None)

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up the CLI with Ollama or OpenAI-compatible configuration")
    setup_parser.add_argument("-p", "--provider", choices=["ollama", "openai"], default=None, help="Provider to set up: ollama or openai (default: ollama)")
    setup_parser.add_argument("--ollama-host", help="Ollama host URL")
    setup_parser.add_argument("--openai-api-base", help="OpenAI-compatible API base URL (e.g. https://ai.hackclub.com)")

    # List models command
    models_parser = subparsers.add_parser("models", help="List available models")
    models_parser.add_argument("-p", "--provider", choices=["ollama", "openai"], default=None, help="Provider to use: ollama or openai (default: ollama)")
    models_parser.add_argument("--openai-api-base", help=argparse.SUPPRESS)

    # Chat completion command
    chat_parser = subparsers.add_parser("chat", help="Generate a chat completion")
    chat_parser.add_argument("prompt", help="The prompt to send to the API", nargs="?")
    chat_parser.add_argument("--model", "-m", default="gemma3:1b", help="Model to use for completion")
    chat_parser.add_argument("--stream", "-s", action="store_true", help="Stream the response")
    chat_parser.add_argument("--system", help="System prompt to use")
    chat_parser.add_argument("--temperature", "-t", type=float, default=0.7, help="Temperature for sampling")
    chat_parser.add_argument("--max-tokens", type=int, help="Maximum number of tokens to generate")
    chat_parser.add_argument("--file", "-f", action="append", help="Path to file(s) to include as context")
    chat_parser.add_argument("--context", "-c", action="store_true", help="Keep conversation context")
    chat_parser.add_argument("--save", action="store_true", help="Save conversation history")
    chat_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    chat_parser.add_argument("--render-markdown", "-r", action="store_true", help="Render markdown in the response")
    chat_parser.add_argument("-p", "--provider", choices=["ollama", "openai"], default=None, help="Provider to use: ollama or openai (default: ollama)")
    chat_parser.add_argument("--openai-api-base", help=argparse.SUPPRESS)  # allow override per-command
    # File with prompt content
    chat_parser.add_argument("--prompt-file", help="Path to file containing the prompt")

    # Interactive chat command
    interactive_parser = subparsers.add_parser("run", help="Start an interactive chat session")
    interactive_parser.add_argument("--model", "-m", default=None, help="Model to use for completion (if not specified, will prompt to select)")
    interactive_parser.add_argument("--system", "-s", help="System prompt to use")
    interactive_parser.add_argument("--temperature", "-t", type=float, default=0.7, help="Temperature for sampling")
    interactive_parser.add_argument("--max-tokens", type=int, help="Maximum number of tokens to generate")
    interactive_parser.add_argument("--save", action="store_true", help="Save conversation history")
    interactive_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    interactive_parser.add_argument("--render-markdown", "-r", action="store_true", help="Render markdown in the response")
    interactive_parser.add_argument("-p", "--provider", choices=["ollama", "openai"], default=None, help="Provider to use: ollama or openai (default: ollama)")
    interactive_parser.add_argument("--openai-api-base", help=argparse.SUPPRESS)

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

    # Determine OpenAI-compatible API base
    openai_api_base = getattr(args, 'openai_api_base', None)
    if not openai_api_base:
        openai_api_base = os.environ.get('OPENAI_API_BASE')

    cli = LLM_CLI(use_colors=use_colors, render_markdown=render_markdown)

    def get_provider(args, cli):
        # Prefer explicit argument, then config, then default to 'ollama'
        provider = getattr(args, 'provider', None)
        if provider:
            return provider
        if hasattr(cli, 'config') and 'provider' in cli.config:
            return cli.config['provider']
        return 'ollama'

    def call_openai_chat(messages, model="meta-llama/llama-4-maverick-17b-128e-instruct", stream=False, temperature=0.7, max_tokens=None):
        url = (openai_api_base or os.environ.get('OPENAI_API_BASE', '')).rstrip('/') + "/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        headers = {"Content-Type": "application/json"}
        if stream:
            resp = requests.post(url, json=payload, headers=headers, stream=True)
        else:
            resp = requests.post(url, json=payload, headers=headers, stream=False)
        if not stream:
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                print(content)
                return content
            else:
                print(f"Error: {resp.status_code} {resp.text}")
                return None
        else:
            # Streamed response: application/x-ndjson, each line is a JSON object
            try:
                for line in resp.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode())
                            if 'choices' in chunk and chunk['choices']:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    print(delta['content'], end='', flush=True)
                        except Exception:
                            continue
                print()
            except Exception as e:
                print(f"Streaming error: {e}")
            return None

    # Handle commands
    if args.command == "setup":
        provider = get_provider(args, cli)
        cli.setup(
            ollama_host=getattr(args, 'ollama_host', None),
            openai_api_base=getattr(args, 'openai_api_base', None),
            provider=provider
        )
    elif args.command == "models":
        provider = get_provider(args, cli)
        if provider == 'openai':
            # List models from OpenAI-compatible endpoint
            openai_api_base = getattr(args, 'openai_api_base', None) or os.environ.get('OPENAI_API_BASE') or cli.config.get('openai_api_base')
            if not openai_api_base:
                cli._print_error("No OpenAI-compatible API base URL provided. Use --openai-api-base or set in config.")
                return
            try:
                resp = requests.get(openai_api_base.rstrip('/') + "/models")
                if resp.status_code == 200:
                    data = resp.json()
                    cli._print_info("Available OpenAI-compatible models:")
                    for model in data.get('data', []):
                        model_id = model.get('id', 'Unknown')
                        print(f"- {model_id}")
                else:
                    cli._print_error(f"Error listing models: HTTP {resp.status_code} {resp.text}")
            except Exception as e:
                cli._print_error(f"Error listing models: {e}")
        else:
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

        # Provider selection
        provider = get_provider(args, cli)
        if provider == 'openai':
            openai_api_base = getattr(args, 'openai_api_base', None) or os.environ.get('OPENAI_API_BASE') or cli.config.get('openai_api_base')
            if not openai_api_base:
                cli._print_error("No OpenAI-compatible API base URL provided. Use --openai-api-base or set in config.")
                return
            messages = cli._prepare_messages(prompt, args.system)
            call_openai_chat(messages, model=args.model, stream=args.stream, temperature=args.temperature, max_tokens=args.max_tokens)
        else:
            cli.complete(
                prompt=prompt,
                model=args.model,
                stream=args.stream,
                system_prompt=args.system,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                file_paths=args.file,
                keep_context=args.context,
                save_history=args.save
            )
    elif args.command == "run":
        provider = get_provider(args, cli)
        openai_api_base = getattr(args, 'openai_api_base', None) or os.environ.get('OPENAI_API_BASE') or cli.config.get('openai_api_base')
        # --- Model selection logic for -m flag ---
        model = args.model
        available_models = []
        if not model:
            # If not specified, fetch models and prompt user to select
            if provider == 'ollama':
                ollama_host = cli.config.get('ollama_host') or os.environ.get("OLLAMA_HOST") or OLLAMA_DEFAULT_HOST
                try:
                    resp = requests.get(f"{ollama_host}/api/tags")
                    if resp.status_code == 200:
                        models_data = resp.json()
                        available_models = [m.get('name', '') for m in models_data.get('models', [])]
                except Exception:
                    pass
            elif provider == 'openai':
                api_base = openai_api_base
                endpoints_to_try = [cli.config.get('openai_model_list_endpoint', None), '/v1/models', '/models', '/model']
                endpoints_to_try = [e for e in endpoints_to_try if e]
                if not api_base:
                    print("Error: No OpenAI API base URL set. Please run 'mdllama setup -p openai' or set the OPENAI_API_BASE environment variable.")
                    return
                for endpoint in endpoints_to_try:
                    try:
                        url = api_base.rstrip('/') + endpoint
                        resp = requests.get(url)
                        if resp.status_code == 200:
                            content_type = resp.headers.get('Content-Type', '')
                            # Try JSON first
                            try:
                                data = resp.json()
                                # OpenAI format
                                if 'data' in data and isinstance(data['data'], list) and data['data']:
                                    available_models = [m.get('id', '') for m in data.get('data', []) if m.get('id')]
                                # hackclub/ai format: {"models": ["model1", ...]}
                                elif 'models' in data and isinstance(data['models'], list) and data['models']:
                                    available_models = [m for m in data['models'] if m]
                                # hackclub/ai format: {"model": "modelname"}
                                elif 'model' in data and isinstance(data['model'], str) and data['model']:
                                    available_models = [data['model']]
                            except Exception:
                                # If not JSON, try plain text (e.g. hackclub/ai /model returns just the model name)
                                try:
                                    text = resp.text.strip()
                                    if text and '\n' not in text and len(text) < 128:
                                        available_models = [text]
                                except Exception:
                                    pass
                            if available_models:
                                break
                    except Exception:
                        pass
            if available_models:
                print("Available models:")
                for idx, m in enumerate(available_models):
                    print(f"  [{idx+1}] {m}")
                while True:
                    try:
                        sel = input("Select a model by number: ").strip()
                        if sel.isdigit() and 1 <= int(sel) <= len(available_models):
                            model = available_models[int(sel)-1]
                            break
                        else:
                            print("Invalid selection. Please enter a valid number.")
                    except (KeyboardInterrupt, EOFError):
                        print("\nAborted.")
                        return
            else:
                print("No models found for the selected provider. Please check your configuration.")
                return
        cli.interactive_chat(
            model=model or "gemma3:1b",
            system_prompt=args.system,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            save_history=args.save,
            provider=provider,
            openai_api_base=openai_api_base
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
