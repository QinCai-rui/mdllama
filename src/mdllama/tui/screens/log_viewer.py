"""Log viewer screen"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Label, RichLog


class LogViewer(ModalScreen[str]):
    """Simple log viewer screen"""
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def action_cancel(self) -> None:
        self.dismiss()

    async def on_screen_resume(self) -> None:
        """Update logs when screen is shown"""
        widget = self.query_one(RichLog)
        widget.write("mdllama TUI log viewer")
        widget.write("This is a placeholder for application logs")

    def compose(self) -> ComposeResult:
        with Container(id="log-viewer", classes="screen-container full-height"):
            yield Label("mdllama logs", classes="title")
            yield RichLog(
                highlight=True,
                markup=True,
                auto_scroll=True,
                wrap=True,
            )
