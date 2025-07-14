"""Input utilities for mdllama including readline support"""

import atexit
import os
from .config import CONFIG_DIR

# Handle readline import and setup
try:
    import readline
    READLINE_AVAILABLE = True
    
    HISTORY_FILE = str(CONFIG_DIR / "input_history")
    
    def setup_readline():
        """Setup readline for command history."""
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
        if os.path.exists(HISTORY_FILE):
            try:
                readline.read_history_file(HISTORY_FILE)
            except (PermissionError, OSError):
                # Ignore permission errors when reading history file (common on macOS)
                pass
                
        def safe_write_history():
            try:
                readline.write_history_file(HISTORY_FILE)
            except (PermissionError, OSError):
                # Ignore permission errors when writing history file (common on macOS)
                pass
                
        atexit.register(safe_write_history)
        readline.set_history_length(1000)
        
    # Initialize readline on import
    setup_readline()
    
except ImportError:
    READLINE_AVAILABLE = False

def input_with_history(prompt: str) -> str:
    """Input function with readline history support if available."""
    if READLINE_AVAILABLE:
        try:
            return input(prompt)
        except KeyboardInterrupt:
            raise
    else:
        return input(prompt)

def read_multiline_input() -> str:
    """Read multiline input from the user, ending with triple quotes."""
    lines = []
    print('Enter your multiline input (end with """ on a new line):')
    
    while True:
        try:
            line = input()
            if line.strip() == '"""':
                break
            lines.append(line)
        except EOFError:
            break
            
    return "\n".join(lines)
