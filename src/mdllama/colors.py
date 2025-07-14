"""Color and formatting utilities for mdllama"""

from colorama import init as colorama_init, Fore, Back, Style

colorama_init(autoreset=True)

class Colors:
    """ANSI color codes for terminal formatting"""
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT
    UNDERLINE = '\033[4m'  # Use ANSI escape code for underline
    
    # Foreground colors
    BLACK = Fore.BLACK
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA
    CYAN = Fore.CYAN
    WHITE = Fore.WHITE
    
    # Background colors
    BG_BLACK = Back.BLACK
    BG_RED = Back.RED
    BG_GREEN = Back.GREEN
    BG_YELLOW = Back.YELLOW
    BG_BLUE = Back.BLUE
    BG_MAGENTA = Back.MAGENTA
    BG_CYAN = Back.CYAN
    BG_WHITE = Back.WHITE
    
    # Bright foreground colors
    BRIGHT_BLACK = Fore.LIGHTBLACK_EX
    BRIGHT_RED = Fore.LIGHTRED_EX
    BRIGHT_GREEN = Fore.LIGHTGREEN_EX
    BRIGHT_YELLOW = Fore.LIGHTYELLOW_EX
    BRIGHT_BLUE = Fore.LIGHTBLUE_EX
    BRIGHT_MAGENTA = Fore.LIGHTMAGENTA_EX
    BRIGHT_CYAN = Fore.LIGHTCYAN_EX
    BRIGHT_WHITE = Fore.LIGHTWHITE_EX
    
    # Special formats for links
    LINK = "\033]8;;"  # OSC 8 hyperlink start
    LINK_END = "\033]8;;\033\\"  # OSC 8 hyperlink end
