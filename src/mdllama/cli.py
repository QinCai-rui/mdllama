"""Main CLI class for mdllama"""

import os
import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

from .config import load_config, save_config, OLLAMA_DEFAULT_HOST
from .colors import Colors
from .output import OutputFormatter
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient
from .input_utils import input_with_history, read_multiline_input
from .session import SessionManager
from .model_manager import ModelManager
from .web_search import DuckDuckGoSearch, create_search_prompt_enhancement, WebsiteContentFetcher, create_website_prompt_enhancement

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
        self.output = OutputFormatter(use_colors, render_markdown)
        self.session_manager = SessionManager(self.output, use_colors)
        self.model_manager = ModelManager(self.output, self.config)
        self.console = Console() if RICH_AVAILABLE else None
        
        # Initialize clients
        self.ollama_client = None
        self.openai_client = None
        
        # Initialise web search
        self.search_client = DuckDuckGoSearch(self.output)
        self.website_fetcher = WebsiteContentFetcher(self.output)
        self._pending_search_query = None  # For interactive chat web search enhancement
        
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
        self.model_manager.list_models(provider or "ollama", openai_api_base)
        
    def clear_context(self):
        """Clear the current conversation context."""
        self.session_manager.clear_context()
        
    def list_sessions(self):
        """List all saved conversation sessions."""
        self.session_manager.list_sessions()
                    
    def load_session(self, session_id: str) -> bool:
        """Load a conversation session."""
        return self.session_manager.load_session(session_id)
            
    def show_model_chooser(self, provider: str = "ollama") -> Optional[str]:
        """Show a numbered list of available models and allow user to choose."""
        return self.model_manager.show_model_chooser(provider)
    
    def web_search(self, query: str, max_results: int = 5) -> str:
        """
        Perform a web search using DuckDuckGo and return formatted results.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return (default: 5)
        
        Returns:
            Formatted search results
        """
        self.output.print_info(f"Searching the web for: {query}")
        return self.search_client.search_and_format(query, max_results)
    
    def fetch_website_content(self, url: str, max_length: int = 8000) -> Optional[str]:
        """
        Fetch content from a website and return as text.
        
        Args:
            url: The website URL to fetch
            max_length: Maximum length of content to return (default: 8000)
        
        Returns:
            Website content as text or None if failed
        """
        return self.website_fetcher.fetch_website_content(url, max_length)
    
    def _generate_search_query(self, question: str, provider: str = "openai", model: Optional[str] = None) -> str:
        """
        Generate an effective search query based on a user's question using AI.
        
        Args:
            question: The user's question
            provider: Which AI provider to use for generating the search query
            model: The specific model to use for generation (uses current model if provided)
            
        Returns:
            AI-generated optimized search query
        """
        # Get recent conversation context for better search query generation
        context_messages = []
        if hasattr(self.session_manager, 'current_context') and self.session_manager.current_context:
            # Get the last few messages for context (skip system messages)
            recent_messages = [msg for msg in self.session_manager.current_context[-6:] 
                             if msg.get('role') in ['user', 'assistant']]
            if recent_messages:
                context_text = "\n".join([f"{msg['role'].title()}: {msg['content']}" 
                                        for msg in recent_messages[-4:]])  # Last 4 messages
                context_messages.append(f"\nRecent conversation context:\n{context_text}")
        
        context_str = "".join(context_messages) if context_messages else ""
        
        search_prompt = f"""You are a search query optimizer. Convert this user input into an effective web search query.

Input: "{question}"{context_str}

Instructions:
1. Consider the conversation context when generating the search query
2. Fix any spelling errors (e.g., "limux" → "linux", "artihicial" → "artificial")
3. Remove question words (what, how, why, etc.) but preserve important context
4. Extract key terms that would appear in search results
5. Make it concise but specific (3-8 words)
6. Use proper spelling and common terminology
7. If the question refers to something mentioned earlier in context, include relevant details

Examples:
Input: "what is the latest limux kernal version?"
Output: linux kernel latest version

Input: "how do i install python on ubuntu?"
Output: install python ubuntu

Input: "wat is artihicial intelledasdgince"
Output: artificial intelligence

Now convert: "{question}"

Respond with ONLY the optimized search query, nothing else (not even <think>):"""

        # Normalize provider name to lowercase
        provider = provider.lower()
        
        try:
            # Create a simple message for the AI
            messages = [{"role": "user", "content": search_prompt}]
            
            # Try to use the configured provider to generate the search query
            if provider == "openai":
                api_base = self.config.get('openai_api_base')
                
                if api_base:
                    try:
                        openai_client = OpenAIClient(api_base, self.config)
                        
                        # Use provided model or try different models in order of preference
                        if model:
                            models_to_try = [model, "llama3-8b-8192", "mixtral-8x7b-32768", "gpt-4o-mini", "gpt-3.5-turbo"]
                        else:
                            models_to_try = ["llama3-8b-8192", "mixtral-8x7b-32768", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4", "gpt-4o"]
                        
                        for model_name in models_to_try:
                            try:
                                response = openai_client.chat(messages, model_name, False, 0.3, 30)
                                
                                if 'choices' in response and len(response['choices']) > 0:
                                    choice = response['choices'][0]
                                    search_query = choice['message']['content'].strip()
                                    
                                    # Check if response is empty
                                    if not search_query or search_query == '':
                                        continue
                                    
                                    # Clean up the response - remove quotes and extra text
                                    import re
                                    search_query = re.sub(r'^["\']|["\']$', '', search_query)
                                    search_query = re.sub(r'(Search query:|Output:)\s*', '', search_query, flags=re.IGNORECASE)
                                    
                                    # Handle "thinking" model responses - extract actual query from <think> blocks
                                    if '<think>' in search_query or '<thinking>' in search_query:
                                        # Try to extract content after thinking blocks
                                        think_patterns = [
                                            r'</think>\s*(.+?)(?:\n|$)',
                                            r'</thinking>\s*(.+?)(?:\n|$)',
                                            r'<think>.*?</think>\s*(.+?)(?:\n|$)',
                                            r'<thinking>.*?</thinking>\s*(.+?)(?:\n|$)'
                                        ]
                                        
                                        for pattern in think_patterns:
                                            match = re.search(pattern, search_query, re.DOTALL | re.IGNORECASE)
                                            if match:
                                                extracted = match.group(1).strip()
                                                if extracted and len(extracted) > 2:
                                                    search_query = extracted
                                                    break
                                        else:
                                            # If no extraction worked, fall back to simple keyword extraction
                                            words = re.findall(r'\b\w+\b', question.lower())
                                            filtered_words = [word for word in words if word not in ['what', 'is', 'the', 'how', 'do', 'does'] and len(word) > 2]
                                            search_query = ' '.join(filtered_words[:5]) or question.strip()
                                    
                                    search_query = search_query.strip()
                                    if search_query and len(search_query) > 2:
                                        return search_query[:100]  # Limit length
                                    else:
                                        continue
                                break
                            except Exception:
                                continue  # Try next model
                    except Exception:
                        pass  # Fall through to Ollama
            
            # Try Ollama as fallback or primary choice
            try:
                ollama_client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
                is_available = ollama_client.is_available()
                
                if is_available:
                    # Use provided model or try multiple models in order of preference
                    if model:
                        models_to_try = [model, "llama3.2:1b", "llama3:8b", "llama2", "gemma2:2b", "qwen2:1.5b"]
                    else:
                        models_to_try = ["llama3.2:1b", "llama3:8b", "llama2", "gemma2:2b", "qwen2:1.5b"]
                    
                    for model_name in models_to_try:
                        try:
                            response = ollama_client.chat(messages, model_name, False, 0.3, 30)
                            
                            if 'message' in response and 'content' in response['message']:
                                search_query = response['message']['content'].strip()
                                
                                # Check if response is empty
                                if not search_query or search_query == '':
                                    continue
                                
                                # Clean up the response
                                import re
                                search_query = re.sub(r'^["\']|["\']$', '', search_query)
                                search_query = re.sub(r'(Search query:|Output:)\s*', '', search_query, flags=re.IGNORECASE)
                                
                                # Handle "thinking" model responses
                                if '<think>' in search_query or '<thinking>' in search_query:
                                    think_patterns = [
                                        r'</think>\s*(.+?)(?:\n|$)',
                                        r'</thinking>\s*(.+?)(?:\n|$)',
                                        r'<think>.*?</think>\s*(.+?)(?:\n|$)',
                                        r'<thinking>.*?</thinking>\s*(.+?)(?:\n|$)'
                                    ]
                                    
                                    for pattern in think_patterns:
                                        match = re.search(pattern, search_query, re.DOTALL | re.IGNORECASE)
                                        if match:
                                            extracted = match.group(1).strip()
                                            if extracted and len(extracted) > 2:
                                                search_query = extracted
                                                break
                                    else:
                                        # If no extraction worked, fall back to simple keyword extraction
                                        words = re.findall(r'\b\w+\b', question.lower())
                                        filtered_words = [word for word in words if word not in ['what', 'is', 'the', 'how', 'do', 'does'] and len(word) > 2]
                                        search_query = ' '.join(filtered_words[:5]) or question.strip()
                                
                                search_query = search_query.strip()
                                if search_query and len(search_query) > 2:
                                    return search_query[:100]  # Limit length
                                else:
                                    continue
                            break
                        except Exception:
                            continue  # Try next model
                            
            except Exception:
                pass  # Continue to fallback
                        
        except Exception:
            pass  # Continue to fallback
            
        # Enhanced fallback: Smart keyword extraction with spelling fixes
        import re
        
        # Common spelling fixes. removed now since it is now useless
        spelling_fixes = {
            
        }
        
        # Apply spelling fixes
        question_fixed = question.lower()
        for wrong, correct in spelling_fixes.items():
            question_fixed = re.sub(r'\b' + wrong + r'\b', correct, question_fixed)
        
        # Remove question words but keep important terms
        question_words = [
            'what', 'is', 'the', 'how', 'do', 'does', 'can', 'could', 'would', 'should',
            'why', 'when', 'where', 'who', 'which', 'a', 'an', 'are', 'was', 'were',
            'will', 'have', 'has', 'had', 'be', 'been', 'being', 'there', 'no'
        ]
        
        words = re.findall(r'\b\w+\b', question_fixed)
        filtered_words = [word for word in words if word not in question_words and len(word) > 2]
        
        # Take the most important words
        search_query = ' '.join(filtered_words[:5])
        
        # If still too short, try a different approach
        if len(search_query.split()) < 2:
            # Remove common question patterns but keep the core content
            cleaned = re.sub(r'^(what|how|why|when|where|who|which)\s+(is|are|do|does|can|could|would|should)\s*', '', question_fixed.strip())
            cleaned = re.sub(r'\?+$', '', cleaned).strip()
            if cleaned and len(cleaned) > 3:
                search_query = cleaned
        
        # Final cleanup
        search_query = re.sub(r'\?+$', '', search_query).strip()
        
        return search_query or question_fixed.strip()
            
    def _prepare_messages(self, prompt: str, system_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Prepare messages for completion, including context."""
        return self.session_manager.prepare_messages(prompt, system_prompt)
        
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
                
                with open(file_path, 'r', encoding='utf-8') as f:
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
                 openai_api_base: Optional[str] = None,
                 web_search_query: Optional[str] = None,
                 max_search_results: int = 3,
                 website_url: Optional[str] = None) -> Optional[str]:
        """Generate a completion using the configured provider."""
        
        # Process file attachments
        prompt = self._process_file_attachments(prompt, file_paths)
        
        # Enhance prompt with web search results if requested
        if web_search_query:
            self.output.print_info(f"Searching the web for: {web_search_query}")
            search_results = self.search_client.search(web_search_query, max_search_results)
            if search_results:
                prompt = create_search_prompt_enhancement(prompt, search_results)
                self.output.print_success(f"Enhanced prompt with {len(search_results)} web search results")
            else:
                self.output.print_info("No web search results found")
        
        # Enhance prompt with website content if requested
        if website_url:
            website_content = self.fetch_website_content(website_url)
            if website_content:
                prompt = create_website_prompt_enhancement(prompt, website_content, website_url)
                self.output.print_success(f"Enhanced prompt with website content from {website_url}")
            else:
                self.output.print_info(f"Failed to fetch content from {website_url}")
        
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
                
                if self.render_markdown and RICH_AVAILABLE and self.console:
                    # Use Rich Live for real-time markdown rendering with vertical overflow visible
                    with Live(Markdown(""), console=self.console, refresh_per_second=10, vertical_overflow="visible") as live_display:
                        for chunk in client.chat(messages, model, stream, temperature, max_tokens):
                            if 'message' in chunk and 'content' in chunk['message']:
                                content = chunk['message']['content']
                                if content:
                                    full_response += content
                                    try:
                                        live_display.update(Markdown(full_response))
                                    except Exception:
                                        # Fallback to plain text if markdown parsing fails
                                        live_display.update(full_response)
                else:
                    # Fallback to traditional streaming
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
                self.session_manager.update_context(user_message, full_response)
                
            # Save history if requested
            self.session_manager.save_history_if_requested(save_history)
                
            return full_response
            
        except KeyboardInterrupt:
            # Re-raise KeyboardInterrupt to be caught by interactive_chat
            raise
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
            full_response = ""
            
            if stream:
                # Try streaming first, fallback to non-streaming if it fails
                try:
                    full_response = ""
                    
                    if self.render_markdown and RICH_AVAILABLE and self.console:
                        # Use Rich Live for real-time markdown rendering with vertical overflow visible
                        with Live(Markdown(""), console=self.console, refresh_per_second=10, vertical_overflow="visible") as live_display:
                            for chunk in client.chat(messages, model, True, temperature, max_tokens):
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    if 'content' in delta and delta['content']:
                                        content = delta['content']
                                        full_response += content
                                        try:
                                            live_display.update(Markdown(full_response))
                                        except Exception:
                                            # Fallback to plain text if markdown parsing fails
                                            live_display.update(full_response)
                    else:
                        # Fallback to traditional streaming
                        buffer = ""
                        for chunk in client.chat(messages, model, True, temperature, max_tokens):
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta and delta['content']:
                                    content = delta['content']
                                    buffer += content
                                    full_response += content
                                    
                                    # Process buffer for smoother streaming output
                                    if len(buffer) > 50 or any(c in buffer for c in [' ', '\n', '.', ',', ')']):
                                        self.output.stream_response(buffer, Colors.GREEN)
                                        buffer = ""
                        
                        # Process remaining buffer
                        if buffer:
                            self.output.stream_response(buffer, Colors.GREEN)
                        
                        print()  # Add final newline
                    
                except Exception as streaming_error:
                    # Fallback to non-streaming if streaming fails
                    self.output.print_error(f"Streaming failed, falling back to non-streaming: {streaming_error}")
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
                # Non-streaming response
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
                        
                        # Render markdown after response if enabled but not rendered
                        if self.render_markdown and not (RICH_AVAILABLE and self.console):
                            self.output.render_markdown(full_response)
                else:
                    self.output.print_error("Invalid response format from OpenAI API.")
                    return None
                    
            # Update context
            if keep_context:
                user_message = messages[-1]
                self.session_manager.update_context(user_message, full_response)
                
            # Save history if requested
            self.session_manager.save_history_if_requested(save_history)
                
            return full_response
            
        except KeyboardInterrupt:
            # Re-raise KeyboardInterrupt to be caught by interactive_chat
            raise
        except Exception as e:
            self.output.print_error(f"Error during OpenAI completion: {e}")
            return None
            
    def interactive_chat(self,
                         model: str = "gemma3:1b",
                         system_prompt: Optional[str] = None,
                         temperature: float = 0.7,
                         max_tokens: Optional[int] = None,
                         save_history: bool = False,
                         stream: bool = False,
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
        self.output.print_command("exit/quit        - Exit the chat session")
        self.output.print_command("clear            - Clear the conversation context")
        self.output.print_command("file:<path>      - Include a file in your next message (max 2MB)")
        self.output.print_command("system:<prompt>  - Set or change the system prompt")
        self.output.print_command("temp:<value>     - Change the temperature setting")
        self.output.print_command("model:<name>     - Switch to a different model")
        self.output.print_command("search:<query>   - Search the web and add results to context")
        self.output.print_command("searchask:<query>|<question> - Search and immediately ask about results")
        self.output.print_command("searchask:<query> - Search and ask for summary")
        self.output.print_command("websearch:<question> - AI-powered search: auto-generate query and answer")
        self.output.print_command("site:<url>       - Fetch website content and add to context")
        self.output.print_command("models           - Show available models with numbers")
        self.output.print_command('"""              - Start/end a multiline message')
        self.output.print_info("Keyboard shortcuts:")
        self.output.print_command("Ctrl+C           - Interrupt model response (not for exiting)")
        self.output.print_command("Ctrl+D           - Exit the chat session")
        print()
        
        # Add system prompt if provided
        if system_prompt:
            self.session_manager.current_context.append({"role": "system", "content": system_prompt})
            if self.use_colors:
                print(f"{Colors.MAGENTA}System:{Colors.RESET} {system_prompt}")
            else:
                print(f"System: {system_prompt}")
            print()
            
        while True:
            try:
                # Show current model in prompt
                prompt_text = f"You ({model}): " if not self.use_colors else f"{Colors.BOLD}{Colors.BLUE}You ({Colors.BRIGHT_YELLOW}{model}{Colors.BLUE}):{Colors.RESET} "
                user_input = input_with_history(prompt_text)
            except EOFError:
                print("\nExiting interactive chat...")
                break
            except KeyboardInterrupt:
                # CTRL-C during input - don't exit, just show a message
                print("\nUse 'exit', 'quit', or Ctrl+D to exit the chat.")
                continue
                
            # Handle special commands
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting interactive chat...")
                break
            elif user_input.lower() == 'clear':
                self.clear_context()
                if system_prompt:
                    self.session_manager.current_context.append({"role": "system", "content": system_prompt})
                continue
            elif user_input.lower() == 'models':
                selected_model = self.show_model_chooser(provider)
                if selected_model:
                    model = selected_model
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
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
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
                self.session_manager.current_context = [msg for msg in self.session_manager.current_context if msg.get("role") != "system"]
                if new_system_prompt:
                    self.session_manager.current_context.insert(0, {"role": "system", "content": new_system_prompt})
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
            elif user_input.startswith('search:'):
                search_query = user_input[7:].strip()
                if search_query:
                    search_results_text = self.web_search(search_query)
                    print(search_results_text)
                    print()
                    
                    # Add search results to conversation context as a system message
                    search_context = f"""IMPORTANT: Use the following current web search results to answer the user's question. This is real-time information from the internet:

Web search results for '{search_query}':
{search_results_text}

You MUST base your response on the above search results. Do not say you don't have access to real-time information - you do, it's provided above."""
                    self.session_manager.current_context.append({
                        "role": "system", 
                        "content": search_context
                    })
                    self.output.print_success(f"Search results added to conversation context. You can now ask questions about the search results.")
                else:
                    self.output.print_error("Please specify a search query.")
                continue
            elif user_input.startswith('searchask:'):
                # Format: searchask:query|question
                # e.g., "searchask:Python 3.13|What are the new features?"
                parts = user_input[10:].strip().split('|', 1)
                if len(parts) == 2:
                    search_query, question = parts[0].strip(), parts[1].strip()
                    
                    # Perform search and add to context
                    search_results_text = self.web_search(search_query)
                    search_context = f"""IMPORTANT: Use the following current web search results to answer the user's question. This is real-time information from the internet:

Web search results for '{search_query}':
{search_results_text}

You MUST base your response on the above search results. Do not say you don't have access to real-time information - you do, it's provided above."""
                    self.session_manager.current_context.append({
                        "role": "system", 
                        "content": search_context
                    })
                    
                    # Now ask the question - this will be processed as a regular prompt
                    user_input = question
                    self.output.print_success(f"Search completed for '{search_query}'. Now asking: {question}")
                    print()
                    # Don't continue here - let it fall through to process the question
                elif len(parts) == 1 and parts[0]:
                    # Just search query, ask a default question
                    search_query = parts[0].strip()
                    search_results_text = self.web_search(search_query)
                    search_context = f"""IMPORTANT: Use the following current web search results to answer the user's question. This is real-time information from the internet:

Web search results for '{search_query}':
{search_results_text}

You MUST base your response on the above search results. Do not say you don't have access to real-time information - you do, it's provided above."""
                    self.session_manager.current_context.append({
                        "role": "system", 
                        "content": search_context
                    })
                    
                    user_input = f"Based on the search results above, please summarize the key information about {search_query}."
                    self.output.print_success(f"Search completed for '{search_query}'. Asking for summary.")
                    print()
                    # Don't continue here - let it fall through to process the question
                else:
                    self.output.print_error("Please specify a search query. Format: searchask:query|question or searchask:query")
                    continue
            elif user_input.startswith('websearch:'):
                question = user_input[10:].strip()
                if question:
                    # Generate search query from the question using AI
                    try:
                        search_query = self._generate_search_query(question, provider, model)
                        self.output.print_success(f"AI generated query: {search_query}")
                        
                        # Perform search and add to context
                        search_results_text = self.web_search(search_query, max_results=3)
                        
                        # Get the search results to show URLs accessed
                        search_results = self.search_client.search(search_query, max_results=3)
                        if search_results:
                            urls = [result.url for result in search_results[:3] if result.url]
                            if urls:
                                for url in urls:
                                    self.output.print_info(f"Accessing: {url}")
                        
                        search_context = f"""IMPORTANT: Use the following current web search results to answer the user's question. This is real-time information from the internet:

Web search results for '{search_query}':
{search_results_text}

You MUST base your response on the above search results. Do not say you don't have access to real-time information - you do, it's provided above."""
                        self.session_manager.current_context.append({
                            "role": "system", 
                            "content": search_context
                        })
                        
                        # Now ask the question - this will be processed as a regular prompt
                        user_input = question
                        self.output.print_success(f"Now answering: {question}")
                        print()
                        # Don't continue here - let it fall through to process the question
                    except Exception as e:
                        self.output.print_error(f"Search failed: {e}")
                        continue
                else:
                    self.output.print_error("Please specify a question after websearch:")
                    continue
            elif user_input.startswith('site:'):
                url = user_input[5:].strip()
                if url:
                    # Fetch website content
                    website_content = self.fetch_website_content(url)
                    if website_content:
                        # Add website content to conversation context as a system message
                        site_context = f"Website content from '{url}':\n\n{website_content}"
                        self.session_manager.current_context.append({
                            "role": "system", 
                            "content": site_context
                        })
                        self.output.print_success(f"Website content from '{url}' added to conversation context.")
                        
                        # Show a preview
                        preview_length = 200
                        preview = website_content[:preview_length]
                        if len(website_content) > preview_length:
                            preview += "..."
                        
                        if self.use_colors:
                            print(f"{Colors.BRIGHT_BLACK}Preview: {preview}{Colors.RESET}")
                        else:
                            print(f"Preview: {preview}")
                        print()
                        
                        self.output.print_success("You can now ask questions about the website content.")
                    else:
                        self.output.print_error("Failed to fetch website content.")
                else:
                    self.output.print_error("Please specify a website URL after site:")
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
            # Use streaming if requested, with fallback for OpenAI compatibility issues
            use_streaming = stream
            try:
                # Check if we have a pending web search query
                search_query = self._pending_search_query
                self._pending_search_query = None  # Clear after use
                
                self.complete(
                    prompt=user_input,
                    model=model,
                    stream=use_streaming,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    keep_context=True,
                    save_history=False,
                    provider=provider,
                    web_search_query=search_query,
                    max_search_results=3
                )
            except KeyboardInterrupt:
                # CTRL-C interrupts the current response but continues the chat
                print("\n\nResponse interrupted. Continuing chat...")
                print()
                
        if save_history and self.session_manager.current_context:
            session_id = self.session_manager.save_history_if_requested(True)
            if session_id:
                self.output.print_success(f"Conversation saved to session {session_id}")
