"""Chat input widget with flexible input handling"""

from textual import on
from textual.containers import Container
from textual.widgets import Input
from textual.widget import Widget
from textual.message import Message


class FlexibleInput(Widget):
    """Input widget that can handle both single line and multiline input"""
    
    class Submitted(Message):
        """Message sent when input is submitted"""
        
        def __init__(self, value: str) -> None:
            self.value = value
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._multiline_mode = False

    def compose(self):
        yield Input(id="prompt", placeholder="Type your message...")

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission"""
        if event.value.strip():
            self.post_message(self.Submitted(event.value))
            event.input.value = ""

    def focus(self) -> None:
        """Focus the input"""
        prompt_input = self.query_one("#prompt", Input)
        prompt_input.focus()

    def clear(self) -> None:
        """Clear the input"""
        prompt_input = self.query_one("#prompt", Input)
        prompt_input.value = ""
