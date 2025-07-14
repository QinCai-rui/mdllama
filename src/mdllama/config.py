"""Configuration management for mdllama"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration paths
CONFIG_DIR = Path.home() / ".mdllama"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_DIR = CONFIG_DIR / "history"
OLLAMA_DEFAULT_HOST = "http://localhost:11434"

def ensure_config_dir():
    """Ensure the configuration directory exists."""
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)
        HISTORY_DIR.mkdir(exist_ok=True)

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    ensure_config_dir()
    
    if not CONFIG_FILE.exists():
        return {}
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_config(config: Dict[str, Any]):
    """Save configuration to file."""
    ensure_config_dir()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_openai_headers(config: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, str]:
    """Get headers for OpenAI-compatible API calls, including API key if available."""
    headers = {"Content-Type": "application/json"}
    
    # Get API key from parameter, environment variable, or config
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY') or config.get('openai_api_key')
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    return headers
