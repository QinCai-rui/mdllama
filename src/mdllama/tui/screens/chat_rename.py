"""Chat renaming functionality"""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class ChatRename(ModalScreen[str]):
    """Modal screen for renaming chats"""
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, current_name: str) -> None:
        super().__init__()
        self.current_name = current_name

    def action_cancel(self) -> None:
        self.dismiss()

    @on(Input.Submitted)
    async def on_submit(self, event: Input.Submitted) -> None:
        """Handle name submission"""
        if event.value.strip():
            self.dismiss(event.value.strip())
        else:
            self.dismiss()

    def compose(self) -> ComposeResult:
        with Container(classes="screen-container short"):
            yield Label("Rename chat", classes="title")
            yield Input(value=self.current_name, placeholder="Enter new name...")
