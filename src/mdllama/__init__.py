"""
mdllama - A command-line interface for Ollama API and OpenAI-compatible endpoints
"""

from .version import __version__
from .cli import LLM_CLI
from .main import main

__all__ = ['__version__', 'LLM_CLI', 'main']
