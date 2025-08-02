"""Splash screen for mdllama TUI"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Label


class SplashScreen(ModalScreen[str]):
    """Splash screen shown on startup"""
    
    BINDINGS = [
        ("escape", "dismiss", "Dismiss"),
    ]

    def action_dismiss(self) -> None:
        self.dismiss("")

    def compose(self) -> ComposeResult:
        with Container(id="splash"):
            yield Label("mdllama", id="title")
            yield Label("TUI LLM Client with Ollama & OpenAI Support", id="subtitle")
            yield Label("Press any key to continue...", id="continue")

    async def on_mount(self) -> None:
        # Auto-dismiss after 2 seconds
        self.set_timer(2.0, self.action_dismiss)

    def on_key(self, event) -> None:
        # Dismiss on any key press
        self.action_dismiss()


# Create splash screen instance
splash = SplashScreen()
