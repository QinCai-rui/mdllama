"""Session management utilities for mdllama"""

from .history import HistoryManager
from .output import OutputFormatter
from .colors import Colors
from typing import Optional, Dict, Any, List

class SessionManager:
    def __init__(self, output: OutputFormatter, use_colors: bool = True):
        self.history = HistoryManager()
        self.output = output
        self.use_colors = use_colors
        self.current_context: List[Dict[str, Any]] = []

    def list_sessions(self):
        sessions = self.history.list_sessions()
        if not sessions:
            self.output.print_info("No session history found.")
            return
        self.output.print_info("Available sessions:")
        for session in sessions:
            session_id = session['id']
            if session['corrupted']:
                if self.use_colors:
                    print(f"- {Colors.YELLOW}{session_id}{Colors.RESET} {Colors.RED}(corrupted){Colors.RESET}")
                else:
                    print(f"- {session_id} (corrupted)")
            else:
                date = session['date']
                message_count = session['message_count']
                if self.use_colors:
                    print(f"- {Colors.YELLOW}{session_id}{Colors.RESET}: {Colors.WHITE}{date.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET} ({message_count} messages)")
                else:
                    print(f"- {session_id}: {date.strftime('%Y-%m-%d %H:%M:%S')} ({message_count} messages)")

    def load_session(self, session_id: str) -> bool:
        try:
            self.current_context = self.history.load_history(session_id)
            self.history.current_session_id = session_id
            self.output.print_success(f"Loaded history from session {session_id}")
            return True
        except (FileNotFoundError, ValueError) as e:
            self.output.print_error(f"Error loading history: {e}")
            return False

    def clear_context(self):
        self.current_context = []
        self.output.print_success("Context cleared.")
    
    def prepare_messages(self, prompt: str, system_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Prepare messages for completion, including context."""
        messages = self.current_context.copy()

        # Add system prompt if provided
        if system_prompt:
            # Insert at the beginning to ensure it's processed first
            messages.insert(0, {"role": "system", "content": system_prompt})
            
        # Add the text prompt
        messages.append({"role": "user", "content": prompt})
            
        return messages
    
    def update_context(self, user_message: Dict[str, Any], assistant_response: str):
        """Update context with new user message and assistant response."""
        self.current_context.append(user_message)
        self.current_context.append({"role": "assistant", "content": assistant_response})
    
    def save_history_if_requested(self, save_history: bool):
        """Save conversation history if requested."""
        if save_history:
            self.history.save_history(self.current_context)
            return self.history.current_session_id
        return None
