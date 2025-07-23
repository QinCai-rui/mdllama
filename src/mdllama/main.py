import sys
import json
"""Main entry point for mdllama CLI"""

import argparse
import os
import requests
from .version import __version__
from .release import check_github_release
from .cli import LLM_CLI

def get_version():
    """Get the version of mdllama."""
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

    # Check release command (moved here)
    subparsers.add_parser("check-release", help="Check for new stable and pre-releases of mdllama")

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
    chat_parser.add_argument("--file", "-f", action="append", help="Path to file(s) to include as context (max 2MB per file)")
    chat_parser.add_argument("--context", "-c", action="store_true", help="Keep conversation context")
    chat_parser.add_argument("--save", action="store_true", help="Save conversation history")
    chat_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    chat_parser.add_argument("--render-markdown", "-r", action="store_true", help="Render markdown in the response")
    chat_parser.add_argument("-p", "--provider", choices=["ollama", "openai"], default=None, help="Provider to use: ollama or openai (default: ollama)")
    chat_parser.add_argument("--openai-api-base", help=argparse.SUPPRESS)
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

    # Ollama commands
    pull_parser = subparsers.add_parser("pull", help="Pull a model from Ollama registry")
    pull_parser.add_argument("model", help="Model name to pull")

    list_parser = subparsers.add_parser("list", help="List all models in Ollama")
    ps_parser = subparsers.add_parser("ps", help="Show running model processes in Ollama")
    rm_parser = subparsers.add_parser("rm", help="Remove a model from Ollama")
    rm_parser.add_argument("model", help="Model name to remove")

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

    cli = LLM_CLI(use_colors=use_colors, render_markdown=render_markdown)

    # Handle commands
    if args.command == "check-release":
        check_github_release()
        return
    if args.command == "setup":
        provider = getattr(args, 'provider', None) or 'ollama'
        cli.setup(
            ollama_host=getattr(args, 'ollama_host', None),
            openai_api_base=getattr(args, 'openai_api_base', None),
            provider=provider
        )
    elif args.command == "models":
        provider = getattr(args, 'provider', None)
        openai_api_base = getattr(args, 'openai_api_base', None)
        cli.list_models(provider=provider, openai_api_base=openai_api_base)
    elif args.command == "chat":
        # Handle prompt from file or argument
        prompt = args.prompt
        if args.prompt_file:
            try:
                with open(args.prompt_file, 'r') as f:
                    prompt = f.read().strip()
            except Exception as e:
                cli.output.print_error(f"Error reading prompt file: {e}")
                return
        
        if not prompt:
            cli.output.print_error("No prompt provided. Use --prompt-file or provide a prompt argument.")
            return
            
        provider = getattr(args, 'provider', None)
        openai_api_base = getattr(args, 'openai_api_base', None)
            
        cli.complete(
            prompt=prompt,
            model=args.model,
            stream=args.stream,
            system_prompt=args.system,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            file_paths=args.file,
            keep_context=args.context,
            save_history=args.save,
            provider=provider,
            openai_api_base=openai_api_base
        )
    elif args.command == "run":
        provider = getattr(args, 'provider', None) or 'ollama'
        
        # If no model specified, let user choose from available models
        model = args.model
        if not model:
            # Show model chooser at startup
            selected_model = cli._show_model_chooser(provider)
            if selected_model:
                model = selected_model
            else:
                # Fall back to defaults if selection fails
                if provider == "openai":
                    # Get the first available OpenAI model
                    from .openai_client import OpenAIClient
                    openai_api_base = getattr(args, 'openai_api_base', None) or cli.config.get('openai_api_base')
                    if openai_api_base:
                        openai_client = OpenAIClient(openai_api_base, cli.config)
                        models, error = openai_client.get_models()
                        if models and not error:
                            model = models[0]
                        else:
                            cli.output.print_error(f"Could not get OpenAI models: {error}")
                            return
                    else:
                        cli.output.print_error("OpenAI API base URL not configured. Use 'mdllama setup -p openai' to configure.")
                        return
                else:
                    model = "gemma3:1b"  # Default Ollama model
        
        cli.interactive_chat(
            model=model,
            system_prompt=args.system,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            save_history=args.save,
            provider=provider
        )
    elif args.command == "clear-context":
        cli.clear_context()
    elif args.command == "sessions":
        cli.list_sessions()
    elif args.command == "load-session":
        cli.load_session(args.session_id)
    elif args.command == "pull":
        from .ollama_client import OllamaClient
        from .config import OLLAMA_DEFAULT_HOST
        
        ollama_client = OllamaClient(cli.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
        if ollama_client.pull_model(args.model):
            cli.output.print_success(f"Model '{args.model}' pulled successfully.")
        else:
            cli.output.print_error(f"Failed to pull model '{args.model}'.")
    elif args.command == "list":
        cli.list_models()
    elif args.command == "ps":
        from .ollama_client import OllamaClient
        from .config import OLLAMA_DEFAULT_HOST
        
        ollama_client = OllamaClient(cli.config.get('ollama_host', OLLAMA_DEFAULT_HOST), use_colors=use_colors)
        try:
            models = ollama_client.list_running_models()
            ollama_client.format_running_models(models)
        except Exception as e:
            cli.output.print_error(f"Error listing running models: {e}")
    elif args.command == "rm":
        from .ollama_client import OllamaClient
        from .config import OLLAMA_DEFAULT_HOST
        
        ollama_client = OllamaClient(cli.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
        if ollama_client.delete_model(args.model):
            cli.output.print_success(f"Model '{args.model}' removed successfully.")
        else:
            cli.output.print_error(f"Failed to remove model '{args.model}'.")
    else:
        # If no command is provided, print help
        parser.print_help()



if __name__ == "__main__":
    main()
