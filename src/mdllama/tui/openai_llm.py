import inspect
import json
from ast import literal_eval
from collections.abc import AsyncGenerator, AsyncIterator, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic.json_schema import JsonSchemaValue

from .config import envConfig
from .log import log
from .types import ToolCall
from ..openai_client import OpenAIClient as BaseOpenAIClient


def parse_format(format_text: str) -> JsonSchemaValue | Literal["", "json"]:
    try:
        jsn = json.loads(format_text)
        if isinstance(jsn, dict):
            return jsn
    except json.JSONDecodeError:
        if format_text in ("", "json"):
            return format_text
    raise Exception(f"Invalid format: '{format_text}'")


class OpenAILLM:
    def __init__(
        self,
        model="gpt-3.5-turbo",
        system: str | None = None,
        history: Sequence[Mapping[str, Any]] = [],
        format: str = "",
        keep_alive: int = 5,
        tool_defs: Sequence[ToolCall] = [],
        thinking: bool = False,
        api_base: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ):
        self.model = model
        self.system = system
        self.history = list(history)
        self.format = format
        self.keep_alive = keep_alive
        self.tool_defs = tool_defs
        self.tools = [tool["tool"] for tool in tool_defs]
        self.thinking = thinking
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize OpenAI client
        config = {
            'openai_api_base': api_base,
            'openai_api_key': api_key
        }
        self.client = BaseOpenAIClient(api_base, config)
        
        if system:
            system_message = {"role": "system", "content": system}
            self.history = [system_message] + self.history

    async def stream(
        self,
        prompt: str = "",
        images: list[Path | bytes | str] = [],
        additional_options: dict = {},
        tool_call_messages: list = [],
    ) -> AsyncGenerator[tuple[str, str], Any]:
        """Stream a chat response with support for tool calls."""
        
        # Add user prompt to history if provided
        if prompt:
            user_message = {"role": "user", "content": prompt}
            # Note: OpenAI API handles images differently than Ollama
            if images:
                # Convert images to base64 if needed (simplified for now)
                log.info(f"Images provided but not yet implemented for OpenAI: {len(images)} images")
            self.history.append(user_message)

        # Prepare messages
        messages = self.history + tool_call_messages

        # Stream the response
        text = ""
        thought = ""
        
        try:
            # Use the OpenAI client to stream responses
            for chunk in self.client.chat(
                messages=messages,
                model=self.model,
                stream=True,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            ):
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    delta = chunk['choices'][0].get('delta', {})
                    if 'content' in delta and delta['content']:
                        content = delta['content']
                        text += content
                        yield thought, text
                        
        except Exception as e:
            log.error(f"Error during OpenAI streaming: {e}")
            return

        # Add response to history
        if text:
            self.history.append({"role": "assistant", "content": text})

    @staticmethod
    def list():
        """List available models - placeholder implementation"""
        # This would require API call to list models
        return {
            "models": [
                {"name": "gpt-3.5-turbo"},
                {"name": "gpt-4"},
                {"name": "gpt-4-turbo"},
            ]
        }

    @staticmethod
    def show(model: str):
        """Show model details - placeholder implementation"""
        return {
            "modelfile": f"# Model: {model}",
            "parameters": "temperature 0.7\nmax_tokens 2048",
        }

    @staticmethod
    def pull(model: str) -> Iterator[dict]:
        """Pull model - placeholder for OpenAI (models are cloud-based)"""
        yield {"status": "success", "message": f"Model {model} is available via API"}


def parse_openai_parameters(parameter_text: str) -> dict:
    """Parse OpenAI parameters from text format"""
    lines = parameter_text.split("\n")
    params = {}
    for line in lines:
        if line.strip():
            try:
                key, value = line.split(maxsplit=1)
                try:
                    value = literal_eval(value)
                except (SyntaxError, ValueError):
                    pass
                params[key] = value
            except ValueError:
                continue
    return params


def jsonify_options(options: dict) -> str:
    """Convert options dict to JSON string"""
    return json.dumps(
        {key: value for key, value in options.items() if value is not None},
        indent=2,
    )