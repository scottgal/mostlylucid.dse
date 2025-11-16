"""
Background Tools Loader

Loads tools asynchronously in the background to avoid blocking CLI startup.
"""

import threading
import logging
from typing import Optional, Callable
from src.tools_manager import ToolsManager

logger = logging.getLogger(__name__)


class BackgroundToolsLoader:
    """
    Loads ToolsManager in a background thread.

    Usage:
        loader = BackgroundToolsLoader(config, client, rag)
        loader.start()

        # CLI can start immediately
        # ...

        # When tools are needed:
        tools = loader.get_tools()  # Waits if still loading
    """

    def __init__(self, config_manager, ollama_client, rag_memory):
        """
        Initialize background loader.

        Args:
            config_manager: ConfigManager instance
            ollama_client: OllamaClient instance
            rag_memory: RAGMemory instance
        """
        self.config_manager = config_manager
        self.ollama_client = ollama_client
        self.rag_memory = rag_memory

        self.tools_manager: Optional[ToolsManager] = None
        self.loading_thread: Optional[threading.Thread] = None
        self.is_loading = False
        self.is_ready = False
        self.error: Optional[Exception] = None

        self._lock = threading.Lock()
        self._ready_callbacks = []

    def start(self):
        """Start loading tools in background."""
        if self.loading_thread is not None:
            return  # Already started

        self.is_loading = True
        self.loading_thread = threading.Thread(
            target=self._load_tools,
            daemon=True,
            name="ToolsLoader"
        )
        self.loading_thread.start()

    def _load_tools(self):
        """Background thread function to load tools with live progress."""
        try:
            import time
            import sys
            start = time.time()
            logger.debug("Background: Loading tools...")

            # Show initial loading message with spinner
            sys.stderr.write("\r\033[2K")  # Clear line
            sys.stderr.write("\033[?25l")  # Hide cursor
            sys.stderr.flush()

            spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            spinner_idx = 0

            # Start progress thread
            progress_running = True
            def show_progress():
                nonlocal spinner_idx
                while progress_running:
                    elapsed = time.time() - start
                    sys.stderr.write("\r\033[2K")  # Clear line
                    sys.stderr.write(f"\033[36m{spinner_chars[spinner_idx % len(spinner_chars)]}\033[0m ")
                    sys.stderr.write(f"\033[2mLoading tools... {elapsed:.1f}s\033[0m")
                    sys.stderr.flush()
                    spinner_idx += 1
                    time.sleep(0.1)

            import threading
            progress_thread = threading.Thread(target=show_progress, daemon=True)
            progress_thread.start()

            # This is the slow part - loads all YAML files
            self.tools_manager = ToolsManager(
                config_manager=self.config_manager,
                ollama_client=self.ollama_client,
                rag_memory=self.rag_memory
            )

            # Stop progress and show completion
            progress_running = False
            progress_thread.join(timeout=0.5)

            elapsed = time.time() - start
            with self._lock:
                self.is_ready = True
                self.is_loading = False

            # Clear progress line and show result
            sys.stderr.write("\r\033[2K")  # Clear line
            sys.stderr.write(f"\033[32m✓\033[0m \033[2mLoaded {len(self.tools_manager.tools)} tools in {elapsed:.1f}s\033[0m\n")
            sys.stderr.write("\033[?25h")  # Show cursor
            sys.stderr.flush()

            logger.debug(f"Background: Loaded {len(self.tools_manager.tools)} tools in {elapsed:.2f}s")

            # Call ready callbacks
            for callback in self._ready_callbacks:
                try:
                    callback(self.tools_manager)
                except Exception as e:
                    logger.error(f"Ready callback error: {e}")

        except Exception as e:
            # Stop progress and show error
            import sys
            progress_running = False
            if 'progress_thread' in locals():
                progress_thread.join(timeout=0.5)

            sys.stderr.write("\r\033[2K")  # Clear line
            sys.stderr.write(f"\033[31m✗\033[0m \033[2mFailed to load tools: {str(e)[:60]}\033[0m\n")
            sys.stderr.write("\033[?25h")  # Show cursor
            sys.stderr.flush()

            logger.error(f"Failed to load tools in background: {e}")
            with self._lock:
                self.error = e
                self.is_loading = False
                self.is_ready = False

    def get_tools(self, wait: bool = True) -> Optional[ToolsManager]:
        """
        Get tools manager.

        Args:
            wait: If True, blocks until tools are loaded. If False, returns None if not ready.

        Returns:
            ToolsManager instance, or None if not ready and wait=False

        Raises:
            Exception: If loading failed
        """
        if wait and self.loading_thread:
            # Wait for loading to complete
            self.loading_thread.join()

        with self._lock:
            if self.error:
                raise self.error
            return self.tools_manager

    def on_ready(self, callback: Callable[[ToolsManager], None]):
        """
        Register callback to be called when tools are ready.

        Args:
            callback: Function that takes ToolsManager as argument
        """
        with self._lock:
            if self.is_ready and self.tools_manager:
                # Already ready, call immediately
                callback(self.tools_manager)
            else:
                # Register for later
                self._ready_callbacks.append(callback)

    def is_ready_sync(self) -> bool:
        """Check if tools are ready (non-blocking)."""
        with self._lock:
            return self.is_ready

    def get_status(self) -> str:
        """Get loading status string."""
        with self._lock:
            if self.error:
                return f"Error: {self.error}"
            elif self.is_ready:
                tool_count = len(self.tools_manager.tools) if self.tools_manager else 0
                return f"Ready ({tool_count} tools)"
            elif self.is_loading:
                return "Loading..."
            else:
                return "Not started"
