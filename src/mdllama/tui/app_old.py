"""Main TUI application for mdllama"""

from collections.abc import Iterable
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .screens.chat_edit import ChatEdit
from .screens.chat_export import ChatExport, slugify
from .screens.pull_model import PullModel
from .screens.splash import splash
from .widgets.chat import ChatContainer
from ..config import load_config
from .store.store import Store
from .types import ChatModel


class MDLlamaApp(App):
    """Main TUI application class for mdllama - exactly like oterm"""
    
    TITLE = "mdllama"
    SUB_TITLE = "the TUI LLM client with Ollama & OpenAI support."
    CSS_PATH = None  # We'll add CSS later if needed
    BINDINGS = [
        Binding("ctrl+tab", "cycle_chat(+1)", "next chat", id="next.chat"),
        Binding("ctrl+shift+tab", "cycle_chat(-1)", "prev chat", id="prev.chat"),
        Binding("ctrl+backspace", "delete_chat", "delete chat", id="delete.chat"),
        Binding("ctrl+n", "new_chat", "new chat", id="new.chat"),
        Binding("ctrl+l", "show_logs", "show logs", id="show.logs"),
        Binding("ctrl+q", "quit", "quit", id="quit"),
    ]

    def __init__(self, provider: str = "ollama", openai_api_base: Optional[str] = None):
        super().__init__()
        self.provider = provider
        self.openai_api_base = openai_api_base
        self.config = load_config()

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        yield SystemCommand("New chat", "Creates a new chat", self.action_new_chat)
        yield SystemCommand(
            "Edit chat parameters",
            "Allows to redefine model parameters and system prompt",
            self.action_edit_chat,
        )
        yield SystemCommand(
            "Rename chat", "Renames the current chat", self.action_rename_chat
        )
        yield SystemCommand(
            "Clear chat", "Clears the current chat", self.action_clear_chat
        )
        yield SystemCommand(
            "Delete chat", "Deletes the current chat", self.action_delete_chat
        )
        yield SystemCommand(
            "Export chat",
            "Exports the current chat as Markdown (in the current working directory)",
            self.action_export_chat,
        )
        yield SystemCommand(
            "Regenerate last message",
            "Regenerates the last message (setting a random seed for the message)",
            self.action_regenerate_last_message,
        )
        yield SystemCommand(
            "Pull model",
            "Pulls (or updates) the model from the server",
            self.action_pull_model,
        )
        yield SystemCommand(
            "Show logs", "Shows the logs of the app", self.action_show_logs
        )

    async def action_quit(self) -> None:
        self.log("Quitting...")
        return self.exit()

    async def action_cycle_chat(self, change: int) -> None:
        tabs = self.query_one(TabbedContent)
        store = await Store.get_store()
        saved_chats = await store.get_chats()
        if tabs.active_pane is None:
            return
        active_id = int(str(tabs.active_pane.id).split("-")[1])
        for chat_model in saved_chats:
            if chat_model.id == active_id:
                next_index = (saved_chats.index(chat_model) + change) % len(saved_chats)
                next_id = saved_chats[next_index].id
                if next_id is not None:  # Ensure we have a valid ID
                    tabs.active = f"chat-{next_id}"
                break

    @work
    async def action_new_chat(self) -> None:
        store = await Store.get_store()
        model_info: str | None = await self.push_screen_wait(
            ChatEdit(provider=self.provider, config=self.config)
        )
        if not model_info:
            return

        chat_model = ChatModel.model_validate_json(model_info)
        tabs = self.query_one(TabbedContent)
        tab_count = tabs.tab_count

        name = f"chat #{tab_count + 1} - {chat_model.model}"
        chat_model.name = name

        id = await store.save_chat(chat_model)
        chat_model.id = id

        pane = TabPane(name, id=f"chat-{id}")
        pane.compose_add_child(
            ChatContainer(
                chat_model=chat_model,
                messages=[],
                provider=self.provider,
                config=self.config,
            )
        )
        await tabs.add_pane(pane)
        tabs.active = f"chat-{id}"

    async def action_edit_chat(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active_pane is None:
            return
        chat = tabs.active_pane.query_one(ChatContainer)
        chat.action_edit_chat()

    async def action_rename_chat(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active_pane is None:
            return
        chat = tabs.active_pane.query_one(ChatContainer)
        chat.action_rename_chat()

    async def action_clear_chat(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active_pane is None:
            return
        chat = tabs.active_pane.query_one(ChatContainer)
        await chat.action_clear_chat()

    async def action_delete_chat(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active_pane is None:
            return
        chat = tabs.active_pane.query_one(ChatContainer)
        store = await Store.get_store()

        if chat.chat_model.id is not None:
            await store.delete_chat(chat.chat_model.id)
            await tabs.remove_pane(tabs.active)
            self.notify(f"Deleted {chat.chat_model.name}", severity="information")

    async def action_export_chat(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active_pane is None:
            return
        chat = tabs.active_pane.query_one(ChatContainer)

        if chat.chat_model.id is not None:
            screen = ChatExport(
                chat_id=chat.chat_model.id,
                file_name=f"{slugify(chat.chat_model.name)}.md",
            )
            self.push_screen(screen)

    async def action_regenerate_last_message(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active_pane is None:
            return
        chat = tabs.active_pane.query_one(ChatContainer)
        await chat.action_regenerate_message()

    async def action_pull_model(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active_pane is None:
            screen = PullModel("", provider=self.provider, config=self.config)
        else:
            chat = tabs.active_pane.query_one(ChatContainer)
            screen = PullModel(chat.model, provider=self.provider, config=self.config)
        self.push_screen(screen)

    async def action_show_logs(self) -> None:
        from .screens.log_viewer import LogViewer
        screen = LogViewer()
        self.push_screen(screen)

    @work(exclusive=True)
    async def perform_checks(self) -> None:
        # Check if provider is available
        if self.provider == "ollama":
            from ..ollama_client import OllamaClient
            from ..config import OLLAMA_DEFAULT_HOST
            client = OllamaClient(self.config.get('ollama_host', OLLAMA_DEFAULT_HOST))
            if not client.is_available():
                self.notify("Ollama not available", severity="warning")
        elif self.provider == "openai":
            from ..openai_client import OpenAIClient
            client = OpenAIClient(self.openai_api_base or self.config.get('openai_api_base'), self.config)
            if not client.test_connection():
                self.notify("OpenAI endpoint not available", severity="warning")

    async def on_mount(self) -> None:
        store = await Store.get_store()
        saved_chats = await store.get_chats()

        async def on_splash_done(message) -> None:
            if not saved_chats:
                self.action_new_chat()  # type: ignore
            else:
                tabs = self.query_one(TabbedContent)
                for chat_model in saved_chats:
                    # Only process chats with a valid ID
                    if chat_model.id is not None:
                        messages = await store.get_messages(chat_model.id)
                        container = ChatContainer(
                            chat_model=chat_model,
                            messages=messages,
                            provider=self.provider,
                            config=self.config,
                        )
                        pane = TabPane(
                            chat_model.name, container, id=f"chat-{chat_model.id}"
                        )
                        tabs.add_pane(pane)
            self.perform_checks()

        # Show splash screen
        self.push_screen(splash, callback=on_splash_done)

    @work
    @on(TabbedContent.TabActivated)
    async def on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        container = event.pane.query_one(ChatContainer)
        await container.load_messages()

    def compose(self) -> ComposeResult:
        yield Header()
        yield TabbedContent(id="tabs")
        yield Footer()


app = MDLlamaApp()
