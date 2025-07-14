"""History and session management for mdllama"""

import json
import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import HISTORY_DIR

class HistoryManager:
    """Manages conversation history and sessions."""
    
    def __init__(self):
        self.current_session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def save_history(self, messages: List[Dict[str, Any]], session_id: Optional[str] = None):
        """Save conversation history to file."""
        if not session_id:
            session_id = self.current_session_id
            
        history_file = HISTORY_DIR / f"session_{session_id}.json"
        
        # Ensure history directory exists
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(history_file, 'w') as f:
            json.dump(messages, f, indent=2)
            
        return history_file

    def load_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Load conversation history from file."""
        history_file = HISTORY_DIR / f"session_{session_id}.json"
        
        if not history_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")
            
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid session file format: {e}")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all saved conversation sessions."""
        if not HISTORY_DIR.exists():
            return []
            
        sessions = []
        for session_file in HISTORY_DIR.glob("session_*.json"):
            session_id = session_file.stem.replace("session_", "")
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    message_count = len(data)
                    date = datetime.datetime.strptime(session_id, "%Y%m%d_%H%M%S")
                    sessions.append({
                        'id': session_id,
                        'date': date,
                        'message_count': message_count,
                        'corrupted': False
                    })
            except (json.JSONDecodeError, ValueError):
                sessions.append({
                    'id': session_id,
                    'date': None,
                    'message_count': 0,
                    'corrupted': True
                })
                
        return sorted(sessions, key=lambda x: x['date'] or datetime.datetime.min, reverse=True)
