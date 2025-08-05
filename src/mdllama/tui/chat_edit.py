from ollama import Options, ShowResponse
from pydantic import ValidationError
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import (
    Container,
    Horizontal,
    Vertical,
)
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, OptionList, TextArea
from typing import Union, Any

from .widgets.caps import Capabilities
from .widgets.tool_select import ToolSelector
from .ollamaclient import (
    OllamaLLM,
    jsonify_options,
    parse_format,
    parse_ollama_parameters,
)
from .openai_llm import OpenAILLM
from .types import ChatModel, OtermOllamaOptions, Tool


class ChatEdit(ModalScreen[str]):
    models = []
    models_info: dict[str, Union[ShowResponse, dict[str, Any]]] = {}

    model_name: reactive[str] = reactive("")
    tag: reactive[str] = reactive("")
    bytes: reactive[int] = reactive(0)
    model_info: Union[ShowResponse, dict[str, Any]]
    system: reactive[str] = reactive("")
    parameters: reactive[Options] = reactive(Options())
    format: reactive[str] = reactive("")
    keep_alive: reactive[int] = reactive(5)
    last_highlighted_index = None
    tools: reactive[list[Tool]] = reactive([])
    edit_mode: reactive[bool] = reactive(False)
    thinking: reactive[bool] = reactive(False)

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "save", "Save"),
    ]

    def __init__(
        self,
        chat_model: ChatModel | None = None,
        edit_mode: bool = False,
        provider: str = "ollama",
        openai_api_base: str | None = None,
    ) -> None:
        super().__init__()

        self.provider = provider
        self.openai_api_base = openai_api_base

        if chat_model is None:
            chat_model = ChatModel()

        self.chat_model = chat_model
        self.model_name, self.tag = (
            chat_model.model.split(":") if chat_model.model else ("", "")
        )
        self.system = chat_model.system or ""
        self.parameters = chat_model.parameters
        self.format = chat_model.format
        self.keep_alive = chat_model.keep_alive
        self.tools = chat_model.tools
        self.edit_mode = edit_mode
        self.thinking = chat_model.thinking

    def _return_chat_meta(self) -> None:
        model = f"{self.model_name}:{self.tag}"
        system = self.query_one(".system", TextArea).text
        system = system if system != self.model_info.get("system", "") else None
        keep_alive = int(self.query_one(".keep-alive", Input).value)
        p_area = self.query_one(".parameters", TextArea)
        try:
            parameters = OtermOllamaOptions.model_validate_json(
                p_area.text, strict=True
            )

            if isinstance(parameters.stop, str):
                parameters.stop = [parameters.stop]

        except ValidationError:
            self.app.notify("Error validating parameters", severity="error")
            p_area = self.query_one(".parameters", TextArea)
            p_area.styles.animate("opacity", 0.0, final_value=1.0, duration=0.5)
            return

        f_area = self.query_one(".format", TextArea)
        try:
            parse_format(f_area.text)
            format_text = f_area.text
        except (ValueError, TypeError):
            self.app.notify("Error parsing format", severity="error")
            f_area.styles.animate("opacity", 0.0, final_value=1.0, duration=0.5)
            return

        self.tools = self.query_one(ToolSelector).selected
        self.thinking = self.query_one("#thinking-checkbox", Checkbox).value

        # Create updated chat model
        updated_chat_model = ChatModel(
            id=self.chat_model.id,
            name=self.chat_model.name,
            model=model,
            system=system,
            format=format_text,
            parameters=parameters,
            keep_alive=keep_alive,
            tools=self.tools,
            thinking=self.thinking,
        )

        self.dismiss(updated_chat_model.model_dump_json(exclude_none=True))

    def action_cancel(self) -> None:
        self.dismiss()

    def action_save(self) -> None:
        self._return_chat_meta()

    def select_model(self, model: str) -> None:
        select = self.query_one("#model-select", OptionList)
        # Try to find and select the model
        try:
            for index in range(select.option_count):
                try:
                    option = select.get_option_at_index(index)
                    if option and str(option.prompt) == model:
                        select.highlighted = index
                        break
                except (AttributeError, IndexError):
                    # Fallback: just use the first option if methods don't exist
                    if index == 0:
                        select.highlighted = 0
                    break
        except AttributeError:
            # If option_count doesn't exist, set to first option
            select.highlighted = 0

    async def on_mount(self) -> None:
        if self.provider == "openai":
            # Handle OpenAI models
            try:
                models_response = OpenAILLM.list()
                openai_models = models_response.get("models", [])
                
                # Convert OpenAI model format to match Ollama's expected structure
                self.models = []
                for model_info in openai_models:
                    model_name = model_info.get("name", "")
                    # Create a pseudo-model object that matches expected structure
                    pseudo_model = type('Model', (), {
                        'model': model_name,
                        'name': model_name,
                        'size': 0
                    })()
                    self.models.append(pseudo_model)
                    
                    # Create simplified model info for OpenAI
                    self.models_info[model_name] = {
                        'modelfile': f"# Model: {model_name}",
                        'parameters': "temperature 0.7\nmax_tokens 2048",
                        'system': None,
                    }
                    
            except (ImportError, AttributeError, KeyError) as e:
                self.app.notify(f"Error loading OpenAI models: {e}", severity="error")
                self.models = []
        else:
            # Handle Ollama models (existing behavior)
            try:
                list_response = OllamaLLM.list()
                self.models = list_response.models
                models = [model.model or "" for model in self.models]
                for model in models:
                    info = OllamaLLM.show(model)
                    self.models_info[model] = info
            except (ConnectionError, AttributeError) as e:
                self.app.notify(f"Error loading Ollama models: {e}", severity="error")
                self.models = []

        option_list = self.query_one("#model-select", OptionList)
        option_list.clear_options()
        
        models = [model.model or "" for model in self.models]
        for model in models:
            option_list.add_option(option=self.model_option(model))
        option_list.highlighted = self.last_highlighted_index
        if self.model_name and self.tag:
            self.select_model(f"{self.model_name}:{self.tag}")

        # Disable the model select widget if we are in edit mode.
        widget = self.query_one("#model-select", OptionList)
        widget.disabled = self.edit_mode

    def on_option_list_option_highlighted(
        self, option: OptionList.OptionHighlighted
    ) -> None:
        model = option.option.prompt
        model_meta = next((m for m in self.models if m.model == str(model)), None)
        if model_meta:
            name, tag = (model_meta.model or "").split(":")
            self.model_name = name
            widget = self.query_one(".name", Label)
            widget.update(f"{self.model_name}")

            self.tag = tag
            widget = self.query_one(".tag", Label)
            widget.update(f"{self.tag}")

            self.bytes = model_meta["size"]
            widget = self.query_one(".size", Label)
            widget.update(f"{(self.bytes / 1.0e9):.2f} GB")

            meta = self.models_info.get(model_meta.model or "")
            self.model_info = meta  # type: ignore
            if not self.edit_mode:
                # Handle both ShowResponse and dict types
                if isinstance(self.model_info, dict):
                    parameters_text = self.model_info.get('parameters', '')
                else:
                    parameters_text = self.model_info.parameters or ""
                self.parameters = parse_ollama_parameters(parameters_text)
            widget = self.query_one(".parameters", TextArea)
            widget.load_text(jsonify_options(self.parameters))
            widget = self.query_one(".system", TextArea)

            # Handle system field for both ShowResponse and dict types
            if isinstance(self.model_info, dict):
                system_text = self.model_info.get('system', '')
            else:
                system_text = getattr(self.model_info, 'system', '')
            
            if system_text and not self.edit_mode:
                widget.load_text(system_text)
            elif not self.edit_mode:
                widget.load_text(self.system)

            capabilities: list[str] = self.model_info.get("capabilities", [])
            tools_supported = "tools" in capabilities
            tool_selector = self.query_one(ToolSelector)
            tool_selector.disabled = not tools_supported

            thinking_checkbox = self.query_one("#thinking-checkbox", Checkbox)
            thinking_checkbox.disabled = "thinking" not in capabilities

            if "completion" in capabilities:
                capabilities.remove("completion")  #
            if "embedding" in capabilities:
                capabilities.remove("embedding")

            widget = self.query_one(".caps", Capabilities)
            widget.caps = capabilities  # type: ignore

        # Now that there is a model selected we can save the chat.
        save_button = self.query_one("#save-btn", Button)
        save_button.disabled = False
        ChatEdit.last_highlighted_index = option.option_index

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name == "save":
            self._return_chat_meta()
        else:
            self.dismiss()

    @staticmethod
    def model_option(model: str) -> Text:
        return Text(model)

    def compose(self) -> ComposeResult:
        with Container(classes="screen-container full-height"):
            with Horizontal():
                with Vertical():
                    with Horizontal(id="model-info"):
                        yield Label("Model:", classes="title")
                        yield Label(f"{self.model_name}", classes="name")
                        yield Label("Tag:", classes="title")
                        yield Label(f"{self.tag}", classes="tag")
                        yield Label("Size:", classes="title")
                        yield Label(f"{self.size}", classes="size")
                        yield Label("Caps:", classes="title")
                        yield Capabilities([], classes="caps")
                    yield OptionList(id="model-select")
                    yield Label("Tools:", classes="title")
                    yield ToolSelector(
                        id="tool-selector-container", selected=self.tools
                    )

                with Vertical():
                    yield Label("System:", classes="title")
                    yield TextArea(self.system, classes="system log")
                    yield Label("Parameters:", classes="title")
                    yield TextArea(
                        jsonify_options(self.parameters),
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
