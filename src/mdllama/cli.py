"""Main CLI class for mdllama"""

import os
import datetime
import re
from typing import List, Dict, Optional, Any
from pathlib import Path

from .config import load_config, save_config, OLLAMA_DEFAULT_HOST
from .colors import Colors
from .output import OutputFormatter
from .history import HistoryManager
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient
from .input_utils import input_with_history, read_multiline_input

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

class LLM_CLI:
    """Main CLI class for mdllama."""
    
    def __init__(self, use_colors: bool = True, render_markdown: bool = True):
        self.config = load_config()
        self.use_colors = use_colors
        self.render_markdown = render_markdown
        self.current_context: List[Dict[str, Any]] = []
        self.output = OutputFormatter(use_colors, render_markdown)
        self.history = HistoryManager()
        self.console = Console() if RICH_AVAILABLE else None
        
        # Initialize clients
        self.ollama_client = None
        self.openai_client = None
        
    def setup(self, ollama_host: Optional[str] = None, openai_api_base: Optional[str] = None, provider: str = "ollama"):
        """Set up the CLI with Ollama or OpenAI-compatible configuration."""
        self.output.print_info("Setting up mdllama...")
        provider = provider.lower()
        
        if provider == "ollama":
            self._setup_ollama(ollama_host)
        elif provider == "openai":
            self._setup_openai(openai_api_base)
        else:
            self.output.print_error(f"Unknown provider: {provider}. Use 'ollama' or 'openai'.")
            
    def _setup_ollama(self, ollama_host: Optional[str] = None):
        """Setup Ollama configuration."""
        if ollama_host:
            self.config['ollama_host'] = ollama_host
        else:
            ollama_host = input(f"Enter your Ollama host URL (leave empty for default: {OLLAMA_DEFAULT_HOST}): ").strip()
            if ollama_host:
                self.config['ollama_host'] = ollama_host
                
        save_config(self.config)
        
        # Test connection
        ollama_client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
        if ollama_client.is_available():
            self.output.print_success("Ollama connected successfully!")
            self.output.print_success("Setup complete!")
        else:
            self.output.print_error("Ollama not configured or connection failed. Please check your settings.")
            
    def _setup_openai(self, openai_api_base: Optional[str] = None):
        """Setup OpenAI-compatible configuration."""
        if openai_api_base:
            self.config['openai_api_base'] = openai_api_base
        else:
            openai_api_base = input("Enter your OpenAI-compatible API base URL (e.g. https://ai.hackclub.com): ").strip()
            if openai_api_base:
                self.config['openai_api_base'] = openai_api_base
                
        # Ask for API key
        api_key = input("Enter your API key (leave blank if no API key required): ").strip()
        if api_key:
            self.config['openai_api_key'] = api_key
        else:
            self.config['openai_api_key'] = None
            
        save_config(self.config)
        
        # Test connection
        openai_client = OpenAIClient(self.config.get('openai_api_base', openai_api_base), self.config)
        if openai_client.test_connection():
            self.output.print_success("OpenAI-compatible endpoint connected successfully!")
            self.output.print_success("Setup complete!")
        else:
            self.output.print_error("Could not connect to OpenAI-compatible endpoint. Please check your settings.")
            
    def list_models(self, provider: Optional[str] = None, openai_api_base: Optional[str] = None):
        """List available models."""
        
        # If provider is explicitly specified, use only that provider
        if provider == "openai":
            # Use OpenAI only
            api_base = openai_api_base or self.config.get('openai_api_base')
            if not api_base:
                self.output.print_error("OpenAI API base URL not configured. Use 'mdllama setup -p openai' to configure.")
                return
                
            openai_client = OpenAIClient(api_base, self.config)
            try:
                models, error = openai_client.get_models()
                if error:
                    self.output.print_error(f"Error listing OpenAI models: {error}")
                else:
                    self.output.print_info("Available OpenAI-compatible models:")
                    for model in models:
                        if self.use_colors:
                            print(f"- {Colors.BRIGHT_YELLOW}{model}{Colors.RESET}")
                        else:
                            print(f"- {model}")
                return
            except Exception as e:
                self.output.print_error(f"Error listing OpenAI models: {e}")
                return
                
        elif provider == "ollama":
            # Use Ollama only
            ollama_client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
            if not ollama_client.is_available():
                self.output.print_error("Ollama is not available. Please make sure Ollama is running.")
                return
                
            try:
                models = ollama_client.list_models()
                self.output.print_info("Available Ollama models:")
                for model in models:
                    model_name = model.get('name', 'Unknown')
                    if self.use_colors:
                        print(f"- {Colors.BRIGHT_YELLOW}{model_name}{Colors.RESET}")
                    else:
                        print(f"- {model_name}")
                return
            except Exception as e:
                self.output.print_error(f"Error listing Ollama models: {e}")
                return
        
        # Default behavior - try both providers
        # Try Ollama first
        ollama_client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
        if ollama_client.is_available():
            try:
                models = ollama_client.list_models()
                self.output.print_info("Available Ollama models:")
                for model in models:
                    model_name = model.get('name', 'Unknown')
                    if self.use_colors:
                        print(f"- {Colors.BRIGHT_YELLOW}{model_name}{Colors.RESET}")
                    else:
                        print(f"- {model_name}")
                return
            except Exception as e:
                self.output.print_error(f"Error listing Ollama models: {e}")
                
        # Try OpenAI if configured
        if self.config.get('openai_api_base'):
            openai_client = OpenAIClient(self.config['openai_api_base'], self.config)
            try:
                models, error = openai_client.get_models()
                if error:
                    self.output.print_error(f"Error listing OpenAI models: {error}")
                else:
                    self.output.print_info("Available OpenAI-compatible models:")
                    for model in models:
                        if self.use_colors:
                            print(f"- {Colors.BRIGHT_YELLOW}{model}{Colors.RESET}")
                        else:
                            print(f"- {model}")
                return
            except Exception as e:
                self.output.print_error(f"Error listing OpenAI models: {e}")
                
        self.output.print_error("No configured providers available.")
        
    def clear_context(self):
        """Clear the current conversation context."""
        self.current_context = []
        self.output.print_success("Context cleared.")
        
    def list_sessions(self):
        """List all saved conversation sessions."""
        sessions = self.history.list_sessions()
        
        if not sessions:
            self.output.print_info("No session history found.")
            return
            
        self.output.print_info("Available sessions:")
        for session in sessions:
            session_id = session['id']
            if session['corrupted']:
                if self.use_colors:
                    print(f"- {Colors.YELLOW}{session_id}{Colors.RESET} {Colors.RED}(corrupted){Colors.RESET}")
                else:
                    print(f"- {session_id} (corrupted)")
            else:
                date = session['date']
                message_count = session['message_count']
                if self.use_colors:
                    print(f"- {Colors.YELLOW}{session_id}{Colors.RESET}: {Colors.WHITE}{date.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET} ({message_count} messages)")
                else:
                    print(f"- {session_id}: {date.strftime('%Y-%m-%d %H:%M:%S')} ({message_count} messages)")
                    
    def load_session(self, session_id: str) -> bool:
        """Load a conversation session."""
        try:
            self.current_context = self.history.load_history(session_id)
            self.history.current_session_id = session_id
            self.output.print_success(f"Loaded history from session {session_id}")
            return True
        except (FileNotFoundError, ValueError) as e:
            self.output.print_error(f"Error loading history: {e}")
            return False
            
    def _prepare_messages(self, prompt: str, system_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Prepare messages for completion, including context."""
        messages = self.current_context.copy()

        # Add system prompt if provided and not already present
        if system_prompt and not any(m.get("role") == "system" for m in messages):
            messages.append({"role": "system", "content": system_prompt})
            
        # Add the text prompt
        messages.append({"role": "user", "content": prompt})
            
        return messages
        
    def _process_file_attachments(self, prompt: str, file_paths: Optional[List[str]]) -> str:
        """Process file attachments and add to prompt."""
        if not file_paths:
            return prompt
            
        for file_path in file_paths:
            try:
                # Validate file path for security
                resolved_path = Path(file_path).resolve()
                if str(resolved_path).startswith('/dev/'):
                    self.output.print_error(f"Access to system device files is not allowed: {file_path}")
                    continue
                
                # Check file size (2MB limit)
                file_size = os.path.getsize(file_path)
                max_size = 2 * 1024 * 1024  # 2MB in bytes
                if file_size > max_size:
                    self.output.print_error(f"File '{Path(file_path).name}' is too large ({file_size:,} bytes). Maximum allowed size is 2MB ({max_size:,} bytes).")
                    continue
                
                with open(file_path, 'r') as f:
                    content = f.read()
                    file_name = Path(file_path).name
                    prompt += f"\n\nContents of {file_name}:\n```\n{content}\n```"
            except Exception as e:
                self.output.print_error(f"Error reading file {file_path}: {e}")
                
        return prompt
        
    def complete(self,
                 prompt: str,
                 model: str = "gemma3:1b",
                 stream: bool = False,
                 system_prompt: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 file_paths: Optional[List[str]] = None,
                 keep_context: bool = True,
                 save_history: bool = False,
                 provider: Optional[str] = None,
                 openai_api_base: Optional[str] = None) -> Optional[str]:
        """Generate a completion using the configured provider."""
        
        # Process file attachments
        prompt = self._process_file_attachments(prompt, file_paths)
        
        # Prepare messages
        messages = self._prepare_messages(prompt, system_prompt)
        
        # If provider is explicitly specified, use only that provider
        if provider == "openai":
            # Use OpenAI only
            api_base = openai_api_base or self.config.get('openai_api_base')
            if not api_base:
                self.output.print_error("OpenAI API base URL not configured. Use 'mdllama setup -p openai' to configure.")
                return None
                
            openai_client = OpenAIClient(api_base, self.config)
            return self._complete_with_openai(
                openai_client, messages, model, stream, temperature, max_tokens, keep_context, save_history
            )
            
        elif provider == "ollama":
            # Use Ollama only
            ollama_client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
            if not ollama_client.is_available():
                self.output.print_error("Ollama is not available. Please make sure Ollama is running.")
                return None
                
            return self._complete_with_ollama(
                ollama_client, messages, model, stream, temperature, max_tokens, keep_context, save_history
            )
        
        # Default behavior - try both providers
        # Try Ollama first
        ollama_client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
        if ollama_client.is_available():
            return self._complete_with_ollama(
                ollama_client, messages, model, stream, temperature, max_tokens, keep_context, save_history
            )
            
        # Try OpenAI if configured
        if self.config.get('openai_api_base'):
            openai_client = OpenAIClient(self.config['openai_api_base'], self.config)
            return self._complete_with_openai(
                openai_client, messages, model, stream, temperature, max_tokens, keep_context, save_history
            )
            
        self.output.print_error("No configured providers available.")
        return None
        
    def _complete_with_ollama(self,
                              client: OllamaClient,
                              messages: List[Dict[str, Any]],
                              model: str,
                              stream: bool,
                              temperature: float,
                              max_tokens: Optional[int],
                              keep_context: bool,
                              save_history: bool) -> Optional[str]:
        """Complete using Ollama."""
        try:
            if stream:
                full_response = ""
                buffer = ""
                
                for chunk in client.chat(messages, model, stream, temperature, max_tokens):
                    if 'message' in chunk and 'content' in chunk['message']:
                        content = chunk['message']['content']
                        if content:
                            buffer += content
                            full_response += content
                            
                            # Process buffer for link formatting
                            if len(buffer) > 100 or any(c in buffer for c in [' ', '\n', '.', ',', ')']):
                                self.output.stream_response(buffer, Colors.GREEN)
                                buffer = ""
                                
                # Process remaining buffer
                if buffer:
                    self.output.stream_response(buffer, Colors.GREEN)
                    
                print()  # Add final newline
            else:
                response = client.chat(messages, model, stream, temperature, max_tokens)
                if 'message' in response and 'content' in response['message']:
                    full_response = response['message']['content']
                    
                    # Render markdown if enabled
                    if self.render_markdown and RICH_AVAILABLE and self.console:
                        self.console.print(Markdown(full_response))
                    else:
                        processed_response = self.output.process_links_in_markdown(full_response)
                        if self.use_colors:
                            print(f"{Colors.GREEN}{processed_response}{Colors.RESET}")
                        else:
                            print(full_response)
                        
                        # Render markdown after response if enabled but not rendered
                        if self.render_markdown and not (RICH_AVAILABLE and self.console):
                            self.output.render_markdown(full_response)
                else:
                    self.output.print_error("Invalid response format from Ollama.")
                    return None
                    
            # Update context
            if keep_context:
                user_message = messages[-1]
                self.current_context.append(user_message)
                self.current_context.append({"role": "assistant", "content": full_response})
                
            # Save history if requested
            if save_history:
                self.history.save_history(self.current_context)
                
            return full_response
            
        except Exception as e:
            self.output.print_error(f"Error during Ollama completion: {e}")
            return None
            
    def _complete_with_openai(self,
                              client: OpenAIClient,
                              messages: List[Dict[str, Any]],
                              model: str,
                              stream: bool,
                              temperature: float,
                              max_tokens: Optional[int],
                              keep_context: bool,
                              save_history: bool) -> Optional[str]:
        """Complete using OpenAI-compatible API."""
        try:
            if stream:
                full_response = ""
                
                # For OpenAI, always fall back to non-streaming due to API compatibility issues
                if True:  # Disable streaming for now
                    response = client.chat(messages, model, False, temperature, max_tokens)
                    if 'choices' in response and len(response['choices']) > 0:
                        full_response = response['choices'][0]['message']['content']
                        
                        # Render markdown if enabled
                        if self.render_markdown and RICH_AVAILABLE and self.console:
                            self.console.print(Markdown(full_response))
                        else:
                            processed_response = self.output.process_links_in_markdown(full_response)
                            if self.use_colors:
                                print(f"{Colors.GREEN}{processed_response}{Colors.RESET}")
                            else:
                                print(full_response)
                    else:
                        self.output.print_error("Invalid response format from OpenAI API.")
                        return None
            else:
                response = client.chat(messages, model, stream, temperature, max_tokens)
                if 'choices' in response and len(response['choices']) > 0:
                    full_response = response['choices'][0]['message']['content']
                    
                    # Render markdown if enabled
                    if self.render_markdown and RICH_AVAILABLE and self.console:
                        self.console.print(Markdown(full_response))
                    else:
                        processed_response = self.output.process_links_in_markdown(full_response)
                        if self.use_colors:
                            print(f"{Colors.GREEN}{processed_response}{Colors.RESET}")
                        else:
                            print(full_response)
                        
                        # Render markdown after response if enabled but not rendered
                        if self.render_markdown and not (RICH_AVAILABLE and self.console):
                            self.output.render_markdown(full_response)
                else:
                    self.output.print_error("Invalid response format from OpenAI API.")
                    return None
                    
            # Update context
            if keep_context:
                user_message = messages[-1]
                self.current_context.append(user_message)
                self.current_context.append({"role": "assistant", "content": full_response})
                
            # Save history if requested
            if save_history:
                self.history.save_history(self.current_context)
                
            return full_response
            
        except Exception as e:
            self.output.print_error(f"Error during OpenAI completion: {e}")
            return None
            
    def interactive_chat(self,
                         model: str = "gemma3:1b",
                         system_prompt: Optional[str] = None,
                         temperature: float = 0.7,
                         max_tokens: Optional[int] = None,
                         save_history: bool = False,
                         provider: str = "ollama"):
        """Start an interactive chat session."""
        provider = provider.lower()
        
        # Print header
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.use_colors:
            print(f"{Colors.BG_BLUE}{Colors.WHITE} mdllama {Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}Model:{Colors.RESET} {Colors.BRIGHT_YELLOW}{model}{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}Time: {Colors.RESET}{Colors.WHITE}{current_time}{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}User: {Colors.RESET}{Colors.WHITE}{os.environ.get('USER', 'unknown')}{Colors.RESET}")
            print()
        else:
            print("mdllama")
            print(f"Model: {model}")
            print(f"Time: {current_time}")
            print(f"User: {os.environ.get('USER', 'unknown')}")
            print()
            
        # Print help
        self.output.print_info("Interactive chat commands:")
        self.output.print_command("exit/quit      - End the conversation")
        self.output.print_command("clear          - Clear the conversation context")
        self.output.print_command("file:<path>    - Include a file in your next message (max 2MB)")
        self.output.print_command("system:<prompt>- Set or change the system prompt")
        self.output.print_command("temp:<value>   - Change the temperature setting")
        self.output.print_command("model:<name>   - Switch to a different model")
        self.output.print_command('"""           - Start/end a multiline message')
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
                try:
                    if self.use_colors:
                        user_input = input_with_history(f"{Colors.BOLD}{Colors.BLUE}You:{Colors.RESET} ")
                    else:
                        user_input = input_with_history("You: ")
                except EOFError:
                    print("\nExiting interactive chat...")
                    break
                    
                # Handle special commands
                if user_input.lower() in ['exit', 'quit']:
                    print("Exiting interactive chat...")
                    break
                elif user_input.lower() == 'clear':
                    self.clear_context()
                    if system_prompt:
                        self.current_context.append({"role": "system", "content": system_prompt})
                    continue
                elif user_input.startswith('file:'):
                    file_path = user_input[5:].strip()
                    try:
                        # Validate and read file
                        resolved_path = Path(file_path).resolve()
                        if str(resolved_path).startswith('/dev/'):
                            self.output.print_error(f"Access to system device files is not allowed: {file_path}")
                            continue
                        
                        file_size = os.path.getsize(file_path)
                        max_size = 2 * 1024 * 1024  # 2MB
                        if file_size > max_size:
                            self.output.print_error(f"File '{Path(file_path).name}' is too large ({file_size:,} bytes). Maximum allowed size is 2MB ({max_size:,} bytes).")
                            continue
                        
                        with open(file_path, 'r') as f:
                            file_content = f.read()
                            file_name = Path(file_path).name
                            self.output.print_success(f"File '{file_name}' loaded. Include it in your next message.")
                            if self.use_colors:
                                print(f"{Colors.BRIGHT_BLACK}Preview: {file_content[:200]}{'...' if len(file_content) > 200 else ''}{Colors.RESET}")
                            else:
                                print(f"Preview: {file_content[:200]}{'...' if len(file_content) > 200 else ''}")
                    except Exception as e:
                        self.output.print_error(f"Error reading file: {e}")
                        continue
                elif user_input.startswith('system:'):
                    new_system_prompt = user_input[7:].strip()
                    self.current_context = [msg for msg in self.current_context if msg.get("role") != "system"]
                    if new_system_prompt:
                        self.current_context.insert(0, {"role": "system", "content": new_system_prompt})
                        self.output.print_success(f"System prompt set to: {new_system_prompt}")
                    else:
                        self.output.print_success("System prompt cleared")
                    continue
                elif user_input.startswith('temp:'):
                    try:
                        temperature = float(user_input[5:].strip())
                        self.output.print_success(f"Temperature set to {temperature}")
                    except ValueError:
                        self.output.print_error("Invalid temperature value. Please use a number between 0 and 1.")
                    continue
                elif user_input.startswith('model:'):
                    new_model = user_input[6:].strip()
                    if new_model:
                        model = new_model
                        self.output.print_success(f"Switched to model: {model}")
                    else:
                        self.output.print_error("Please specify a model name.")
                    continue
                elif user_input.strip() == '"""':
                    user_input = read_multiline_input()
                    self.output.print_success("Multiline input received")
                    
                if not user_input.strip():
                    continue
                    
                if self.use_colors:
                    print(f"\n{Colors.BOLD}{Colors.GREEN}Assistant:{Colors.RESET}")
                else:
                    print("\nAssistant:")
                    
                # Generate response
                # Disable streaming for OpenAI provider as it may have compatibility issues
                use_streaming = True if provider != "openai" else False
                self.complete(
                    prompt=user_input,
                    model=model,
                    stream=use_streaming,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    keep_context=True,
                    save_history=False,
                    provider=provider
                )
                
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting interactive chat...")
            
        if save_history and self.current_context:
            self.history.save_history(self.current_context)
            self.output.print_success(f"Conversation saved to session {self.history.current_session_id}")
