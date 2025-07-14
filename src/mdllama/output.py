"""Output formatting and printing utilities for mdllama"""

import re
from typing import Optional
from .colors import Colors

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

class OutputFormatter:
    """Handles output formatting and printing with colors and markdown support."""
    
    def __init__(self, use_colors: bool = True, render_markdown: bool = True):
        self.use_colors = use_colors
        self.render_markdown = render_markdown
        self.console = Console() if RICH_AVAILABLE else None
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!$&\'()*+,;=:@/~]+)*(?:\?[-\w%!$&\'()*+,;=:@/~]*)?(?:#[-\w%!$&\'()*+,;=:@/~]*)?'
        )
    
    def print_error(self, message: str):
        """Print an error message with color if enabled."""
        if self.use_colors:
            print(f"{Colors.RED}{message}{Colors.RESET}")
        else:
            print(f"Error: {message}")
            
    def print_success(self, message: str):
        """Print a success message with color if enabled."""
        if self.use_colors:
            print(f"{Colors.GREEN}{message}{Colors.RESET}")
        else:
            print(message)
            
    def print_info(self, message: str):
        """Print an info message with color if enabled."""
        if self.use_colors:
            print(f"{Colors.CYAN}{message}{Colors.RESET}")
        else:
            print(message)
            
    def print_command(self, message: str):
        """Print a command reference with color if enabled."""
        if self.use_colors:
            print(f"{Colors.YELLOW}{message}{Colors.RESET}")
        else:
            print(message)
            
    def format_links(self, text: str) -> str:
        """Format links in text to be clickable in the terminal."""
        if not self.use_colors:
            return text
            
        # Find all URLs in the text
        position = 0
        formatted_text = ""
        
        for match in self.url_pattern.finditer(text):
            start, end = match.span()
            url = text[start:end]
            
            # Add text before the URL
            formatted_text += text[position:start]
            
            # Add the formatted URL
            formatted_text += f"{Colors.LINK}{url}{Colors.LINK_END}{Colors.BLUE}{Colors.UNDERLINE}{url}{Colors.RESET}"
            
            position = end
            
        # Add remaining text after the last URL
        formatted_text += text[position:]
        
        return formatted_text
    
    def print_with_links(self, text: str, color: Optional[str] = None):
        """Print text with formatted, clickable links."""
        if RICH_AVAILABLE and self.console:
            # Use Rich to format text with clickable links
            rich_text = Text.from_markup(text)
            
            # Style links in the text
            for match in self.url_pattern.finditer(text):
                url = match.group(0)
                start, end = match.span()
                rich_text.stylize(f"link {url}", start, end)
                rich_text.stylize("bold blue underline", start, end)
                
            self.console.print(rich_text)
        else:
            # Fall back to ANSI escape sequences
            formatted_text = self.format_links(text)
            if color and self.use_colors:
                print(f"{color}{formatted_text}{Colors.RESET}")
            else:
                print(formatted_text)
                
    def process_links_in_markdown(self, text: str) -> str:
        """Process markdown links to make them clickable in terminal."""
        # Process [text](url) style markdown links
        md_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        def replace_with_clickable(match):
            text_part, url = match.groups()
            if self.use_colors:
                return f"{Colors.LINK}{url}{Colors.LINK_END}{Colors.BLUE}{Colors.UNDERLINE}{text_part}{Colors.RESET}"
            else:
                return f"{text_part} ({url})"
                
        processed_text = md_link_pattern.sub(replace_with_clickable, text)
        
        # Also process plain URLs that aren't part of markdown links
        return self.format_links(processed_text)
        
    def render_markdown(self, text: str):
        """Render markdown text if rich is available, otherwise just print it."""
        if not self.render_markdown:
            return
            
        if RICH_AVAILABLE and self.console:
            print("\n--- Rendered Markdown ---")
            # Use Rich's Markdown renderer which automatically formats links
            self.console.print(Markdown(text))
            print("-------------------------")
        else:
            # If rich is not available, we can still try a simple markdown rendering
            # using ANSI escape codes, but for now we'll just skip rendering
            if self.render_markdown:
                self.print_info("Rich library not available. Install it with: pip install rich")
                
    def stream_response(self, content: str, color: Optional[str] = None):
        """Stream response content with link processing."""
        if self.use_colors and color:
            processed_content = self.process_links_in_markdown(content)
            print(f"{color}{processed_content}{Colors.RESET}", end="", flush=True)
        else:
            print(content, end="", flush=True)
