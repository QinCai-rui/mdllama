"""Individual chat message item widget"""

from rich.console import RenderableType
from rich.markdown import Markdown
from textual.reactive import reactive
from textual.widget import Widget


class ChatItem(Widget):
    """Widget representing a single chat message"""
    
    text: reactive[str] = reactive("")
    author: reactive[str] = reactive("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def render(self) -> RenderableType:
        """Render the chat message"""
        if not self.text:
            return ""
            
        # Format based on author
        if self.author == "user":
            return f"[bold blue]You:[/bold blue] {self.text}"
        elif self.author == "assistant":
            # Render as markdown for assistant messages
            try:
                return Markdown(self.text)
            except:
                return f"[bold green]Assistant:[/bold green] {self.text}"
        elif self.author == "system":
            return f"[bold magenta]System:[/bold magenta] {self.text}"
        else:
            return f"[bold]{self.author}:[/bold] {self.text}"

    def on_click(self) -> None:
        """Copy message to clipboard when clicked"""
        try:
            import pyperclip
            pyperclip.copy(self.text)
            self.app.notify("Message copied to clipboard")
        except ImportError:
            # Fallback - just notify that copying is not available
            self.app.notify("Clipboard copy not available")
