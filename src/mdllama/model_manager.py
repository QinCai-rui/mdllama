"""Model management utilities for mdllama"""

from .ollama_client import OllamaClient
from .openai_client import OpenAIClient
from .output import OutputFormatter
from .config import OLLAMA_DEFAULT_HOST
from .colors import Colors
from typing import Optional, Dict, Any

class ModelManager:
    def __init__(self, output: OutputFormatter, config: Dict[str, Any]):
        self.output = output
        self.config = config

    def show_model_chooser(self, provider: str = "ollama", openai_api_base: Optional[str] = None) -> Optional[str]:
        """Show a numbered list of available models and allow user to choose."""
        models = []
        
        if provider == "openai":
            # Get OpenAI models
            api_base = openai_api_base or self.config.get('openai_api_base')
            if not api_base:
                self.output.print_error("OpenAI API base URL not configured.")
                return None
                
            openai_client = OpenAIClient(api_base, self.config)
            try:
                model_list, error = openai_client.get_models()
                if error:
                    self.output.print_error(f"Error listing OpenAI models: {error}")
                    return None
                models = model_list
            except Exception as e:
                self.output.print_error(f"Error listing OpenAI models: {e}")
                return None
                
        elif provider == "ollama":
            # Get Ollama models
            ollama_client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
            if not ollama_client.is_available():
                self.output.print_error("Ollama is not available. Please make sure Ollama is running.")
                return None
                
            try:
                model_data = ollama_client.list_models()
                models = [model.get('name', 'Unknown') for model in model_data]
            except Exception as e:
                self.output.print_error(f"Error listing Ollama models: {e}")
                return None
        else:
            # Try both providers
            # Try Ollama first
            ollama_client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
            if ollama_client.is_available():
                try:
                    model_data = ollama_client.list_models()
                    models = [model.get('name', 'Unknown') for model in model_data]
                except Exception as e:
                    pass
                    
            # Try OpenAI if no Ollama models found
            if not models and self.config.get('openai_api_base'):
                openai_client = OpenAIClient(self.config['openai_api_base'], self.config)
                try:
                    model_list, error = openai_client.get_models()
                    if not error:
                        models = model_list
                except Exception as e:
                    pass
        
        if not models:
            self.output.print_error("No models available.")
            return None
            
        # Display numbered list
        self.output.print_info("Available models:")
        for i, model in enumerate(models, 1):
            print(f"({i}) {Colors.BRIGHT_YELLOW}{model}{Colors.RESET}")
        
        print(f"\n{Colors.BRIGHT_BLACK}Tip: Enter 'q', 'quit', 'exit', or 'cancel' to abort model selection{Colors.RESET}")
                
        # Get user choice with retry logic
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                choice = input(f"\n{Colors.BRIGHT_CYAN}Enter model number (1-{len(models)}): {Colors.RESET}")
                    
                # Allow user to cancel
                if choice.lower() in ['q', 'quit', 'exit', 'cancel']:
                    self.output.print_info("Model selection cancelled.")
                    return None
                    
                choice_num = int(choice.strip())
                if 1 <= choice_num <= len(models):
                    selected_model = models[choice_num - 1]
                    self.output.print_success(f"Selected model: {selected_model}")
                    return selected_model
                else:
                    remaining_attempts = max_attempts - attempt - 1
                    if remaining_attempts > 0:
                        self.output.print_error(f"Invalid choice. Please enter a number between 1 and {len(models)}. {remaining_attempts} attempts remaining.")
                    else:
                        self.output.print_error("Invalid choice. Maximum attempts reached.")
                        return None
            except (ValueError, EOFError, KeyboardInterrupt):
                remaining_attempts = max_attempts - attempt - 1
                if remaining_attempts > 0:
                    self.output.print_error(f"Invalid input. Please enter a valid number. {remaining_attempts} attempts remaining.")
                else:
                    self.output.print_error("Invalid input. Maximum attempts reached.")
                    return None
        
        return None

    def list_models(self, provider: str = "ollama", openai_api_base: Optional[str] = None):
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
                        print(f"- {Colors.BRIGHT_YELLOW}{model}{Colors.RESET}")
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
                    print(f"- {Colors.BRIGHT_YELLOW}{model_name}{Colors.RESET}")
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
                    print(f"- {Colors.BRIGHT_YELLOW}{model_name}{Colors.RESET}")
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
                        print(f"- {Colors.BRIGHT_YELLOW}{model}{Colors.RESET}")
                return
            except Exception as e:
                self.output.print_error(f"Error listing OpenAI models: {e}")
                
        self.output.print_error("No configured providers available.")
