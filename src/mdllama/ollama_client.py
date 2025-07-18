"""Ollama API client for mdllama"""

import json
import requests
import sys
import datetime
from typing import List, Dict, Any, Optional, Generator
from .config import OLLAMA_DEFAULT_HOST

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, host: str = OLLAMA_DEFAULT_HOST, use_colors: bool = True, render_markdown: bool = False):
        self.host = host
        self.client = None
        self.use_colors = use_colors
        self.render_markdown = render_markdown
        self.console = Console() if RICH_AVAILABLE else None
        
    def setup_client(self) -> bool:
        """Initialize the Ollama client."""
        if not OLLAMA_AVAILABLE:
            return False
            
        try:
            # Check if Ollama is running by making a simple request
            test_response = requests.get(f"{self.host}/api/tags")
            if test_response.status_code != 200:
                return False
                
            # Initialize Ollama client with the host
            self.client = ollama.Client(host=self.host)
            return True
        except (requests.exceptions.ConnectionError, Exception):
            return False
            
    def is_available(self) -> bool:
        """Check if Ollama is available and running."""
        return OLLAMA_AVAILABLE and self.setup_client()
        
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models from Ollama."""
        try:
            response = requests.get(f"{self.host}/api/tags")
            if response.status_code == 200:
                models_data = response.json()
                return models_data.get('models', [])
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"Error listing models: {e}")
            
    def pull_model(self, model_name: str, show_progress: bool = True) -> bool:
        """Pull a model from Ollama registry with progress display. Handles Ctrl+C gracefully."""
        try:
            url = f"{self.host}/api/pull"
            resp = requests.post(url, json={"name": model_name}, stream=True)
            if resp.status_code != 200:
                print(f"Error: {resp.status_code} {resp.text}")
                return False
            try:
                if show_progress and RICH_AVAILABLE:
                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        DownloadColumn(),
                        TransferSpeedColumn(),
                        TimeRemainingColumn(),
                    ) as progress:
                        task = progress.add_task(f"Pulling {model_name}", total=None)
                        total = None
                        completed = 0
                        for line in resp.iter_lines():
                            if line:
                                data = json.loads(line)
                                if 'status' in data and data['status'] == 'success':
                                    progress.update(task, completed=total or completed)
                                    break
                                if 'total' in data:
                                    total = data['total']
                                    progress.update(task, total=total)
                                if 'completed' in data:
                                    completed = data['completed']
                                    progress.update(task, completed=completed)
                                if 'digest' in data:
                                    progress.update(task, description=f"Pulling {model_name} [{data['digest'][:12]}]")
                else:
                    # Simple fallback progress
                    total = None
                    completed = 0
                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            if 'status' in data and data['status'] == 'success':
                                print(f"\nPull complete: {model_name}")
                                break
                            if 'total' in data:
                                total = data['total']
                            if 'completed' in data:
                                completed = data['completed']
                            if total:
                                percent = (completed / total) * 100 if total else 0
                                sys.stdout.write(f"\rPulling {model_name}: {percent:.1f}% ({completed}/{total})")
                                sys.stdout.flush()
                    print()
            except KeyboardInterrupt:
                print(f"\nPull cancelled by user (Ctrl+C)")
                return False
            return True
        except Exception:
            return False
            
    def delete_model(self, model_name: str) -> bool:
        """Delete a model from Ollama."""
        try:
            url = f"{self.host}/api/delete"
            resp = requests.delete(url, json={"name": model_name})
            if resp.status_code == 200:
                print(f"Model '{model_name}' removed successfully.")
                return True
            else:
                print(f"Error: {resp.status_code} {resp.text}")
                return False
        except Exception:
            return False
            
    def list_running_models(self) -> List[Dict[str, Any]]:
        """List running model processes with detailed formatting."""
        try:
            url = f"{self.host}/api/ps"
            resp = requests.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get('models', [])
                if not models:
                    print("No models are currently running.")
                    return []
                
                # Import Colors here to avoid circular imports
                from .colors import Colors
                
                # Print header
                if self.use_colors:
                    print(f"{Colors.BOLD}NAME{Colors.RESET:<12} {Colors.BOLD}ID{Colors.RESET:<18} {Colors.BOLD}SIZE{Colors.RESET:<9} {Colors.BOLD}PROCESSOR{Colors.RESET:<7} {Colors.BOLD}UNTIL{Colors.RESET}")
                else:
                    print("NAME         ID              SIZE      PROCESSOR    UNTIL")
                
                # Print each running model
                for model in models:
                    name = model.get('name', 'Unknown')
                    model_id = model.get('digest', '')[:12] if model.get('digest') else 'Unknown'
                    size = model.get('size', 0)
                    size_str = f"{size // (1024*1024)} MB" if size > 0 else "Unknown"
                    
                    # Format processor info based on size_vram and other details
                    size_vram = model.get('size_vram', 0)
                    details = model.get('details', {})
                    
                    if size_vram > 0:
                        # Model is using GPU memory
                        vram_mb = size_vram // (1024 * 1024)
                        if vram_mb < 1024:
                            processor = f"GPU ({vram_mb}MB)"
                        else:
                            vram_gb = vram_mb / 1024
                            processor = f"GPU ({vram_gb:.1f}GB)"
                    else:
                        # Model is using CPU - check if we have quantization info
                        quant_level = details.get('quantization_level', '')
                        if quant_level:
                            processor = f"CPU ({quant_level})"
                        else:
                            processor = "100% CPU"
                    
                    # Format expiry time
                    expires_at = model.get('expires_at', '')
                    until = "Unknown"
                    if expires_at:
                        try:
                            # Parse the expiry time and calculate relative time
                            # Try to parse ISO format timestamp
                            if expires_at.endswith('Z'):
                                # Remove Z and treat as UTC
                                expires_at = expires_at[:-1] + '+00:00'
                            
                            # Parse the timestamp
                            if '+' in expires_at or expires_at.endswith('Z'):
                                # Has timezone info
                                expire_time = datetime.datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                                now = datetime.datetime.now(datetime.timezone.utc)
                            else:
                                # No timezone info, assume local time
                                expire_time = datetime.datetime.fromisoformat(expires_at)
                                now = datetime.datetime.now()
                            
                            diff = expire_time - now
                            if diff.total_seconds() > 0:
                                minutes = int(diff.total_seconds() / 60)
                                if minutes < 60:
                                    until = f"{minutes} minutes from now"
                                else:
                                    hours = minutes // 60
                                    remaining_minutes = minutes % 60
                                    if remaining_minutes > 0:
                                        until = f"{hours}h {remaining_minutes}m from now"
                                    else:
                                        until = f"{hours} hours from now"
                            else:
                                until = "Expired"
                        except Exception as e:
                            # Fallback if parsing fails
                            until = "Unknown"
                    
                    if self.use_colors:
                        print(f"{Colors.BRIGHT_YELLOW}{name:<12}{Colors.RESET} {model_id:<16} {size_str:<9} {processor:<12} {until}")
                    else:
                        print(f"{name:<12} {model_id:<16} {size_str:<9} {processor:<12} {until}")
                        
                return models
            else:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            raise Exception(f"Error listing running models: {e}")
            
    def list_models_formatted(self) -> None:
        """List available models with formatted output."""
        try:
            url = f"{self.host}/api/tags"
            resp = requests.get(url)
            if resp.status_code == 200:
                data = resp.json()
                print("Available models:")
                
                # Import Colors here to avoid circular imports
                from .colors import Colors
                
                for model in data.get('models', []):
                    name = model.get('name', 'Unknown')
                    size = model.get('size', 0)
                    if self.use_colors:
                        print(f"- {Colors.BRIGHT_YELLOW}{name}{Colors.RESET} ({size} bytes)")
                    else:
                        print(f"- {name} ({size} bytes)")
            else:
                print(f"Error: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"Error listing models: {e}")
            
    def chat(self, 
             messages: List[Dict[str, Any]], 
             model: str,
             stream: bool = False,
             temperature: float = 0.7,
             max_tokens: Optional[int] = None,
             keep_context: bool = False,
             current_context: Optional[List[Dict[str, Any]]] = None,
             process_links_callback: Optional[callable] = None) -> Optional[str]:
        """Generate a chat completion using Ollama with full functionality from original."""
        
        # Use direct API endpoint for better control
        api_endpoint = f"{self.host.rstrip('/')}/api/chat"
        
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
            return self._stream_response_with_formatting(api_endpoint, payload, messages, keep_context, current_context, process_links_callback)
        else:
            return self._non_stream_response_with_formatting(api_endpoint, payload, messages, keep_context, current_context, process_links_callback)
            
    def _stream_response_with_formatting(self, api_endpoint: str, payload: Dict[str, Any], 
                                       messages: List[Dict[str, Any]], keep_context: bool,
                                       current_context: Optional[List[Dict[str, Any]]],
                                       process_links_callback: Optional[callable]) -> Optional[str]:
        """Handle streaming response with formatting from original implementation."""
        full_response = ""
        response = requests.post(api_endpoint, json=payload, stream=True)
        
        if response.status_code == 200:
            buffer = ""
            
            # Import Colors here to avoid circular imports
            from .colors import Colors
            
            if self.render_markdown and RICH_AVAILABLE and self.console:
                # Use Rich for live markdown rendering
                accumulated_text = ""
                with Live(Markdown(""), console=self.console, refresh_per_second=10) as live_display:
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                if 'message' in chunk and 'content' in chunk['message']:
                                    chunk_content = chunk['message']['content']
                                    if chunk_content:
                                        full_response += chunk_content
                                        accumulated_text += chunk_content
                                        try:
                                            live_display.update(Markdown(accumulated_text))
                                        except Exception:
                                            live_display.update(accumulated_text)
                            except json.JSONDecodeError:
                                continue
            else:
                # Standard streaming with link processing
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if 'message' in chunk and 'content' in chunk['message']:
                                chunk_content = chunk['message']['content']
                                if chunk_content:
                                    buffer += chunk_content
                                    full_response += chunk_content
                                    
                                    # Process buffer when appropriate
                                    if len(buffer) > 100 or any(c in buffer for c in [' ', '\n', '.', ',', ')']):
                                        if self.use_colors:
                                            if process_links_callback:
                                                processed_buffer = process_links_callback(buffer)
                                            else:
                                                processed_buffer = buffer
                                            print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
                                        else:
                                            print(buffer, end="", flush=True)
                                        buffer = ""
                        except json.JSONDecodeError:
                            continue
                
                # Process any remaining text in the buffer
                if buffer:
                    if self.use_colors:
                        if process_links_callback:
                            processed_buffer = process_links_callback(buffer)
                        else:
                            processed_buffer = buffer
                        print(f"{Colors.GREEN}{processed_buffer}{Colors.RESET}", end="", flush=True)
                    else:
                        print(buffer, end="", flush=True)
                        
            print()  # Add final newline
            
            # Add to context if keeping context
            if keep_context and current_context is not None:
                user_message = messages[-1]  # Get the last user message
                current_context.append(user_message)
                current_context.append({"role": "assistant", "content": full_response})
                
            return full_response
        else:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
    def _non_stream_response_with_formatting(self, api_endpoint: str, payload: Dict[str, Any],
                                           messages: List[Dict[str, Any]], keep_context: bool,
                                           current_context: Optional[List[Dict[str, Any]]],
                                           process_links_callback: Optional[callable]) -> Optional[str]:
        """Handle non-streaming response with formatting from original implementation."""
        response = requests.post(api_endpoint, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if 'message' in data and 'content' in data['message']:
                full_response = data['message']['content']
                
                # Import Colors here to avoid circular imports
                from .colors import Colors
                
                # For non-streaming responses with markdown
                if self.render_markdown and RICH_AVAILABLE and self.console:
                    self.console.print(Markdown(full_response))
                else:
                    # Process links in the full response
                    if process_links_callback:
                        processed_response = process_links_callback(full_response)
                    else:
                        processed_response = full_response
                        
                    if self.use_colors:
                        print(f"{Colors.GREEN}{processed_response}{Colors.RESET}")
                    else:
                        print(full_response)
                
                # Add to context if keeping context
                if keep_context and current_context is not None:
                    user_message = messages[-1]  # Get the last user message
                    current_context.append(user_message)
                    current_context.append({"role": "assistant", "content": full_response})
                    
                return full_response
            else:
                raise Exception("Invalid response format from Ollama API.")
        else:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
    def _stream_response(self, api_endpoint: str, payload: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """Handle streaming response from Ollama (basic version for compatibility)."""
        response = requests.post(api_endpoint, json=payload, stream=True)
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        yield chunk
                    except json.JSONDecodeError:
                        continue
        else:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
    def _non_stream_response(self, api_endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle non-streaming response from Ollama (basic version for compatibility)."""
        response = requests.post(api_endpoint, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
