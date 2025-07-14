"""OpenAI-compatible API client for mdllama"""

import json
import requests
from typing import List, Dict, Any, Optional, Generator, Tuple
from .config import get_openai_headers

class OpenAIClient:
    """Client for interacting with OpenAI-compatible APIs."""
    
    def __init__(self, api_base: str, config: Dict[str, Any]):
        self.api_base = api_base.rstrip('/')
        self.config = config
        
    def get_models(self) -> Tuple[List[str], Optional[str]]:
        """Get available models from OpenAI-compatible API."""
        models = []
        error = None
        
        endpoints_to_try = [
            self.config.get('openai_model_list_endpoint', None), 
            '/v1/models', 
            '/models', 
            '/model'
        ]
        endpoints_to_try = [e for e in endpoints_to_try if e]
        
        headers = get_openai_headers(self.config)
        
        for endpoint in endpoints_to_try:
            try:
                resp = requests.get(self.api_base + endpoint, headers=headers)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if 'data' in data:
                            models = [model.get('id', 'Unknown') for model in data['data']]
                        elif 'models' in data:
                            models = [model.get('id', 'Unknown') for model in data['models']]
                        else:
                            models = list(data.keys()) if isinstance(data, dict) else []
                    except json.JSONDecodeError:
                        # Handle plain text response (e.g., from /model endpoint)
                        model_name = resp.text.strip()
                        if model_name:
                            models = [model_name]
                        else:
                            models = []
                    break
                elif resp.status_code == 404:
                    continue
                else:
                    error = f"HTTP {resp.status_code}"
                    break
            except Exception as e:
                error = str(e)
                break
        else:
            if not error:
                error = "No valid model endpoint found"
                
        return models, error
        
    def test_connection(self) -> bool:
        """Test connection to OpenAI-compatible API."""
        models, error = self.get_models()
        return error is None
        
    def chat(self, 
             messages: List[Dict[str, Any]], 
             model: str,
             stream: bool = False,
             temperature: float = 0.7,
             max_tokens: Optional[int] = None) -> Any:
        """Generate a chat completion using OpenAI-compatible API."""
        
        url = f"{self.api_base}/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        headers = get_openai_headers(self.config)
        
        if stream:
            return self._stream_response(url, payload, headers)
        else:
            return self._non_stream_response(url, payload, headers)
            
    def _stream_response(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Generator[Dict[str, Any], None, None]:
        """Handle streaming response from OpenAI-compatible API."""
        response = requests.post(url, json=payload, headers=headers, stream=True)
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
        else:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
    def _non_stream_response(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handle non-streaming response from OpenAI-compatible API."""
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
