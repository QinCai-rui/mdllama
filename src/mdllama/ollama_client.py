"""Ollama API client for mdllama"""

import json
import requests
from typing import List, Dict, Any, Optional, Generator
from .config import OLLAMA_DEFAULT_HOST

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, host: str = OLLAMA_DEFAULT_HOST):
        self.host = host
        self.client = None
        
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
            
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            url = f"{self.host}/api/pull"
            response = requests.post(url, json={"name": model_name})
            return response.status_code == 200
        except Exception:
            return False
            
    def delete_model(self, model_name: str) -> bool:
        """Delete a model from Ollama."""
        try:
            url = f"{self.host}/api/delete"
            response = requests.delete(url, json={"name": model_name})
            return response.status_code == 200
        except Exception:
            return False
            
    def list_running_models(self) -> List[Dict[str, Any]]:
        """List running model processes."""
        try:
            url = f"{self.host}/api/ps"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json().get('models', [])
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"Error listing running models: {e}")
            
    def chat(self, 
             messages: List[Dict[str, Any]], 
             model: str,
             stream: bool = False,
             temperature: float = 0.7,
             max_tokens: Optional[int] = None) -> Any:
        """Generate a chat completion using Ollama."""
        
        # Set up completion parameters for Ollama API
        completion_params = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        
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
            return self._stream_response(api_endpoint, payload)
        else:
            return self._non_stream_response(api_endpoint, payload)
            
    def _stream_response(self, api_endpoint: str, payload: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """Handle streaming response from Ollama."""
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
        """Handle non-streaming response from Ollama."""
        response = requests.post(api_endpoint, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
