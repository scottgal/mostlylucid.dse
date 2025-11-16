"""
Live status manager for showing real-time updates of HTTP calls and tool execution.
Uses Rich's Live display to create a non-blocking, auto-updating status line.
"""
import threading
from typing import Optional
from rich.console import Console
from rich.text import Text
from datetime import datetime


class StatusManager:
    """
    Manages a live status line that shows real-time updates.

    Thread-safe and non-blocking. Updates overwrite themselves on the same line.
    """

    _instance: Optional['StatusManager'] = None
    _lock = threading.Lock()

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize status manager.

        Args:
            console: Rich Console instance (creates new one if not provided)
        """
        self.console = console or Console()
        self._current_status = ""
        self._enabled = True
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls, console: Optional[Console] = None) -> 'StatusManager':
        """
        Get singleton instance of StatusManager.

        Args:
            console: Rich Console instance (only used on first call)

        Returns:
            StatusManager instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(console)
        return cls._instance

    def set_enabled(self, enabled: bool):
        """Enable or disable status updates."""
        with self._lock:
            self._enabled = enabled

    def update(self, message: str, style: str = "cyan"):
        """
        Update the status line.

        Args:
            message: Status message to display
            style: Rich style (color) for the message
        """
        if not self._enabled:
            return

        with self._lock:
            self._current_status = message
            # Use \r to overwrite the current line
            text = Text()
            text.append(">> ", style="yellow")  # Use ASCII instead of emoji
            text.append(message, style=style)

            # Print with end='\r' to overwrite the line
            try:
                self.console.print(text, end='\r', highlight=False)
            except UnicodeEncodeError:
                # Fallback for systems that can't handle unicode
                self.console.print(f">> {message}", end='\r', highlight=False)

    def clear(self):
        """Clear the status line."""
        if not self._enabled:
            return

        with self._lock:
            self._current_status = ""
            # Print spaces to clear the line, then return to start
            self.console.print(" " * 100, end='\r', highlight=False)

    def http_call(self, method: str, url: str, backend: str = None):
        """
        Show status for an HTTP call.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL being called
            backend: Backend name (ollama, anthropic, etc.)
        """
        # Shorten URL for display
        display_url = url
        if len(url) > 50:
            display_url = url[:47] + "..."

        if backend:
            message = f"{method} {backend} -> {display_url}"
        else:
            message = f"{method} -> {display_url}"

        self.update(message, style="cyan")

    def tool_call(self, tool_name: str, model: str = None):
        """
        Show status for a tool call.

        Args:
            tool_name: Name of the tool being called
            model: Model being used (if applicable)
        """
        if model:
            message = f"Tool: {tool_name} (model: {model})"
        else:
            message = f"Tool: {tool_name}"

        self.update(message, style="magenta")

    def llm_call(self, model: str, backend: str, operation: str = "generate"):
        """
        Show status for an LLM generation call.

        Args:
            model: Model name
            backend: Backend name (ollama, anthropic, etc.)
            operation: Operation type (generate, embed, etc.)
        """
        # Shorten model name if too long
        display_model = model
        if len(model) > 30:
            display_model = model[:27] + "..."

        message = f"{backend}/{display_model} -> {operation}"
        self.update(message, style="blue")

    def embedding_call(self, model: str, backend: str):
        """
        Show status for an embedding call.

        Args:
            model: Model name
            backend: Backend name
        """
        message = f"{backend}/{model} -> embedding"
        self.update(message, style="green")

    def processing(self, message: str):
        """
        Show generic processing status.

        Args:
            message: Status message
        """
        self.update(message, style="yellow")


# Global singleton instance
_global_status_manager: Optional[StatusManager] = None


def get_status_manager(console: Optional[Console] = None) -> StatusManager:
    """
    Get the global status manager instance.

    Args:
        console: Rich Console instance (only used on first call)

    Returns:
        StatusManager instance
    """
    return StatusManager.get_instance(console)


def set_status(message: str, style: str = "cyan"):
    """
    Convenience function to update status.

    Args:
        message: Status message
        style: Rich style (color)
    """
    get_status_manager().update(message, style)


def clear_status():
    """Convenience function to clear status."""
    get_status_manager().clear()
