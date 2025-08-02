"""Chat editing screen for model and parameter configuration"""

import json
from typing import Any, Dict, List, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, OptionList, TextArea

from ..types import ChatModel


class ChatEdit(ModalScreen[str]):
    """Modal screen for editing chat parameters"""
    
    models: List[Dict[str, Any]] = []
    model_name: reactive[str] = reactive("")
    tag: reactive[str] = reactive("")
    system: reactive[str] = reactive("")
    parameters: reactive[Dict[str, Any]] = reactive({})
    format: reactive[str] = reactive("")
    keep_alive: reactive[int] = reactive(5)
    thinking: reactive[bool] = reactive(False)
    edit_mode: reactive[bool] = reactive(False)
    last_highlighted_index = None

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "save", "Save"),
    ]

    def __init__(
        self,
        chat_model: Optional[ChatModel] = None,
        edit_mode: bool = False,
        provider: str = "ollama",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()
        
        if chat_model is None:
            chat_model = ChatModel()

        self.chat_model = chat_model
        self.provider = provider
        self.config = config or {}
        self.model_name, self.tag = (
            chat_model.model.split(":") if chat_model.model else ("", "")
        )
        self.system = chat_model.system or ""
        self.parameters = chat_model.parameters
        self.format = chat_model.format
        self.keep_alive = chat_model.keep_alive
        self.edit_mode = edit_mode
        self.thinking = chat_model.thinking

    def _return_chat_meta(self) -> None:
        """Collect and validate chat configuration"""
        model = f"{self.model_name}:{self.tag}" if self.tag else self.model_name
        system = self.query_one(".system", TextArea).text.strip()
        keep_alive = int(self.query_one(".keep-alive", Input).value or "5")
        
        # Get parameters
        p_area = self.query_one(".parameters", TextArea)
        try:
            parameters = json.loads(p_area.text) if p_area.text.strip() else {}
        except json.JSONDecodeError:
            self.app.notify("Error parsing parameters JSON", severity="error")
            p_area.styles.animate("opacity", 0.0, final_value=1.0, duration=0.5)
            return

        # Get format
        f_area = self.query_one(".format", TextArea)
        format_text = f_area.text.strip()

        self.thinking = self.query_one("#thinking-checkbox", Checkbox).value

        # Create updated chat model
        updated_chat_model = ChatModel(
            id=self.chat_model.id,
            name=self.chat_model.name,
            model=model,
            system=system if system else None,
            format=format_text,
            parameters=parameters,
            keep_alive=keep_alive,
            provider=self.provider,
            thinking=self.thinking,
        )

        self.dismiss(updated_chat_model.model_dump_json(exclude_none=True))

    def action_cancel(self) -> None:
        self.dismiss()

    def action_save(self) -> None:
        self._return_chat_meta()

    def select_model(self, model: str) -> None:
        """Select a model in the option list"""
        select = self.query_one("#model-select", OptionList)
        for index, option in enumerate(select._options):
            if str(option.prompt) == model:
                select.highlighted = index
                break

    async def on_mount(self) -> None:
        """Initialize the screen with available models"""
        if self.provider == "ollama":
            await self._load_ollama_models()
        else:
            await self._load_openai_models()

        # Select current model if set
        if self.model_name and self.tag:
            self.select_model(f"{self.model_name}:{self.tag}")
        elif self.model_name:
            self.select_model(self.model_name)

        # Disable the model select widget if we are in edit mode
        widget = self.query_one("#model-select", OptionList)
        widget.disabled = self.edit_mode

    async def _load_ollama_models(self) -> None:
        """Load models from Ollama"""
        try:
            from ...ollama_client import OllamaClient
            from ...config import OLLAMA_DEFAULT_HOST
            
            client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
            models_data = client.list_models()
            
            if models_data and "models" in models_data:
                self.models = models_data["models"]
                
                option_list = self.query_one("#model-select", OptionList)
                option_list.clear_options()
                
                for model in self.models:
                    model_name = model.get("name", "")
                    if model_name:
                        option_list.add_option(model_name)
                        
        except Exception as e:
            self.app.notify(f"Error loading Ollama models: {e}", severity="error")

    async def _load_openai_models(self) -> None:
        """Load models from OpenAI-compatible endpoint"""
        try:
            from ...openai_client import OpenAIClient
            
            client = OpenAIClient(
                self.config.get('openai_api_base') or "https://api.openai.com",
                self.config
            )
            models_data = client.list_models()
            
            if models_data and "data" in models_data:
                self.models = models_data["data"]
                
                option_list = self.query_one("#model-select", OptionList)
                option_list.clear_options()
                
                for model in self.models:
                    model_name = model.get("id", "")
                    if model_name:
                        option_list.add_option(model_name)
                        
        except Exception as e:
            self.app.notify(f"Error loading OpenAI models: {e}", severity="error")

    def on_option_list_option_highlighted(
        self, option: OptionList.OptionHighlighted
    ) -> None:
        """Handle model selection"""
        model = str(option.option.prompt)
        
        if ":" in model:
            name, tag = model.split(":", 1)
        else:
            name, tag = model, "latest"
            
        self.model_name = name
        self.tag = tag
        
        # Update UI labels
        widget = self.query_one(".name", Label)
        widget.update(f"{self.model_name}")
        
        widget = self.query_one(".tag", Label)
        widget.update(f"{self.tag}")

        # Enable save button
        save_button = self.query_one("#save-btn", Button)
        save_button.disabled = False
        ChatEdit.last_highlighted_index = option.option_index

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.name == "save":
            self._return_chat_meta()
        else:
            self.dismiss()

    def compose(self) -> ComposeResult:
        """Compose the chat edit screen layout"""
        with Container(classes="screen-container full-height"):
            with Horizontal():
                with Vertical():
                    with Horizontal(id="model-info"):
                        yield Label("Model:", classes="title")
                        yield Label(f"{self.model_name}", classes="name")
                        yield Label("Tag:", classes="title")
                        yield Label(f"{self.tag}", classes="tag")
                    yield OptionList(id="model-select")

                with Vertical():
                    yield Label("System:", classes="title")
                    yield TextArea(self.system, classes="system log")
                    yield Label("Parameters:", classes="title")
                    yield TextArea(
                        json.dumps(self.parameters, indent=2) if self.parameters else "{}",
                        classes="parameters log",
                        language="json",
                    )
                    yield Label("Format:", classes="title")
                    yield TextArea(
                        self.format or "",
                        classes="format log",
                        language="json",
                    )

                    with Horizontal():
                        yield Checkbox(
                            "Thinking",
                            id="thinking-checkbox",
                            name="thinking",
                            value=self.thinking,
                        )
                        yield Label(
                            "Keep-alive (min)", classes="title keep-alive-label"
                        )
                        yield Input(
                            classes="keep-alive", value=str(self.keep_alive)
                        )

            with Horizontal(classes="button-container"):
                yield Button(
                    "Save",
                    id="save-btn",
                    name="save",
                    disabled=True,
                    variant="primary",
                )
                yield Button("Cancel", name="cancel")
