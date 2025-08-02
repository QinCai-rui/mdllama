"""Model pulling functionality"""

import asyncio
from typing import Any, Dict, Optional

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, TextArea


class PullModel(ModalScreen[str]):
    """Modal screen for pulling/downloading models"""
    
    model: str = ""
    provider: str = "ollama"
    config: Dict[str, Any] = {}
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, model: str, provider: str = "ollama", config: Optional[Dict[str, Any]] = None) -> None:
        self.model = model
        self.provider = provider
        self.config = config or {}
        super().__init__()

    def action_cancel(self) -> None:
        self.dismiss()

    @work
    async def pull_model(self) -> None:
        """Pull the model from the provider"""
        log = self.query_one(".log", TextArea)
        
        if self.provider == "ollama":
            await self._pull_ollama_model(log)
        else:
            log.text += "OpenAI models don't need to be pulled - they're available via API\n"
            await asyncio.sleep(1.0)
            
        self.app.notify("Model pull completed")

    async def _pull_ollama_model(self, log: TextArea) -> None:
        """Pull model from Ollama"""
        try:
            from ...ollama_client import OllamaClient
            from ...config import OLLAMA_DEFAULT_HOST
            
            client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
            
            log.text += f"Pulling model: {self.model}\n"
            
            # Use the pull_model method
            success = client.pull_model(self.model)
            
            if success:
                log.text += f"Successfully pulled model: {self.model}\n"
            else:
                log.text += f"Failed to pull model: {self.model}\n"
                
        except Exception as e:
            log.text += f"Error: {e}\n"

    @on(Input.Changed)
    async def on_model_change(self, ev: Input.Changed) -> None:
        """Handle model name changes"""
        self.model = ev.value

    @on(Button.Pressed)
    @on(Input.Submitted)
    async def on_pull(self, ev) -> None:
        """Handle pull button press or input submission"""
        if self.model.strip():
            self.pull_model()

    def compose(self) -> ComposeResult:
        with Container(
            id="pull-model-container", classes="screen-container full-height"
        ):
            yield Label("Pull model", classes="title")
            with Horizontal():
                yield Input(self.model, placeholder="Enter model name...")
                yield Button("Pull", variant="primary")
            yield TextArea(classes="parameters log", read_only=True)
