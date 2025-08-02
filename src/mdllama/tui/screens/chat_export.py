"""Chat export functionality"""

import re
from typing import Sequence

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, Label

from ..store.store import Store
from ..types import MessageModel


def slugify(text: str) -> str:
    """Convert text to a filename-safe slug"""
    # Remove or replace special characters
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces with hyphens
    text = re.sub(r'[-\s]+', '-', text)
    # Convert to lowercase
    return text.lower().strip('-')


class ChatExport(ModalScreen[str]):
    """Modal screen for exporting chat as markdown"""
    
    chat_id: int
    file_name: str = ""
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, chat_id: int, file_name: str = "") -> None:
        super().__init__()
        self.chat_id = chat_id
        self.file_name = file_name

    def action_cancel(self) -> None:
        self.dismiss()

    @on(Input.Submitted)
    async def on_submit(self, event: Input.Submitted) -> None:
        """Handle file name submission and export chat"""
        store = await Store.get_store()

        if not event.value:
            return

        messages: Sequence[MessageModel] = await store.get_messages(self.chat_id)
        try:
            with open(event.value, "w", encoding="utf-8") as file:
                file.write(f"# Chat Export\n\n")
                for message in messages:
                    file.write(f"## {message.role.title()}\n\n")
                    file.write(f"{message.text}\n\n")
                    file.write("---\n\n")
            self.app.notify(f"Chat exported to {event.value}")
            self.dismiss()
        except Exception as e:
            self.app.notify(f"Error exporting chat: {e}", severity="error")

    def compose(self) -> ComposeResult:
        with Container(classes="screen-container short"):
            yield Label("Export chat", classes="title")
            yield Input(id="chat-name-input", value=self.file_name, placeholder="Enter filename...")
