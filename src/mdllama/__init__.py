"""
mdllama - A command-line interface for Ollama API and OpenAI-compatible endpoints
"""

from .version import __version__
from .cli import LLM_CLI
from .main import main
from .session import SessionManager
from .model_manager import ModelManager
from .output import OutputFormatter
from .colors import Colors

__all__ = ['__version__', 'LLM_CLI', 'main', 'SessionManager', 'ModelManager', 'OutputFormatter', 'Colors']
