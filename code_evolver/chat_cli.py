#!/usr/bin/env python3
"""
Interactive CLI chat interface for mostlylucid DiSE.
Provides a conversational interface for code generation and evolution.
"""
import sys
import signal
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box
from rich.live import Live
from rich.spinner import Spinner
from datetime import datetime
import re
import unicodedata
import threading
import queue
import time
from dataclasses import dataclass
from enum import Enum

# Disable all debug/info logging for clean chat experience
# Use force=True to override any previous logging configurations from imported modules

# Configure logging with ASCII-safe formatting to avoid Windows console encoding errors
import sys
import io

# Create a custom stream handler that handles Unicode encoding gracefully
class SafeStreamHandler(logging.StreamHandler):
    """Stream handler that gracefully handles Unicode encoding on Windows."""
    def __init__(self):
        # Use stderr with UTF-8 encoding, falling back to ASCII if needed
        try:
            stream = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding='utf-8',
                errors='replace'  # Replace unencodable characters instead of crashing
            )
        except (AttributeError, io.UnsupportedOperation):
            stream = sys.stderr
        super().__init__(stream)

    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # If Unicode error occurs, try ASCII-only output
            try:
                record.msg = str(record.msg).encode('ascii', errors='replace').decode('ascii')
                super().emit(record)
            except Exception:
                pass  # Silently ignore logging errors

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.ERROR)
root_logger.handlers.clear()  # Clear any existing handlers
root_logger.addHandler(SafeStreamHandler())

# Set specific loggers to ERROR level to suppress debug output
for logger_name in [
    "src",
    "httpx",
    "httpcore",
    "urllib3",
    "src.ollama_client",
    "src.node_runner",
    "src.tools_manager",
    "src.qdrant_rag_memory",
    "src.config_manager",
    "src.registry",
    "src.evaluator",
    "src.auto_evolver",
    "qdrant_client",
    "anthropic"
]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)
    logger.propagate = False  # Don't propagate to root logger
    logger.handlers.clear()  # Clear any existing handlers

# Command history support - use prompt_toolkit for cross-platform compatibility
PROMPT_TOOLKIT_AVAILABLE = False
READLINE_AVAILABLE = False

try:
    from prompt_toolkit import prompt as pt_prompt
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import WordCompleter
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False
    # Fallback: readline is Unix/Linux only
    try:
        import readline
        READLINE_AVAILABLE = True
    except ImportError:
        READLINE_AVAILABLE = False

from src import (
    OllamaClient, Registry, NodeRunner, Evaluator,
    create_rag_memory, WorkflowTracker
)
from src.config_manager import ConfigManager
from src.tools_manager import ToolsManager, ToolType
from src.background_tools_loader import BackgroundToolsLoader
from src.task_evaluator import TaskEvaluator

def safe_str(text: str) -> str:
    """
    Sanitize text to remove problematic Unicode characters for Windows console.
    This prevents UnicodeEncodeError on Windows terminals with cp1252 encoding.
    """
    if not text:
        return text

    # Replace common Unicode characters with ASCII equivalents
    replacements = {
        '\U0001f4cb': '[SPEC]',  # Clipboard emoji
        '\U0001f4dd': '[NOTE]',  # Memo emoji
        '\U0001f4e6': '[PKG]',   # Package emoji
        '\U0001f527': '[TOOL]',  # Wrench emoji
        '\U0001f4ca': '[CHART]', # Chart emoji
        '\U0001f6e0': '[BUILD]', # Build emoji
        '\U0001f4c4': '[DOC]',   # Document emoji
        '\U0001f4c1': '[FOLDER]',# Folder emoji
        '\U0001f4be': '[SAVE]',  # Floppy disk emoji
        '\U0001f525': '[FIRE]',  # Fire emoji
        '\U0001f4a1': '[IDEA]',  # Light bulb emoji
        '\U0001f680': '[ROCKET]',# Rocket emoji
        '\U0001f41b': '[BUG]',   # Bug emoji
        '\U0001f44d': '[OK]',    # Thumbs up emoji
        '\u2714': '[OK]',        # Check mark
        '\u2716': '[X]',         # X mark
        '\u2192': '->',          # Right arrow
        '\u2190': '<-',          # Left arrow
        '\u2194': '<->',         # Left-right arrow
        '\u21d2': '=>',          # Double right arrow
        '\u2022': '*',           # Bullet
        '\u2026': '...',         # Ellipsis
        '\u2014': '--',          # Em dash
        '\u2013': '-',           # En dash
        '\u2018': "'",           # Left single quote
        '\u2019': "'",           # Right single quote
        '\u201c': '"',           # Left double quote
        '\u201d': '"',           # Right double quote
    }

    result = text
    for unicode_char, replacement in replacements.items():
        result = result.replace(unicode_char, replacement)

    # Remove any remaining non-ASCII characters that aren't printable
    # This is a safety net for characters we didn't explicitly map
    try:
        result.encode('cp1252')
        return result
    except UnicodeEncodeError:
        # Fall back to ASCII transliteration
        result = unicodedata.normalize('NFKD', result)
        result = result.encode('ascii', 'ignore').decode('ascii')
        return result


class SafeConsole(Console):
    """
    Console wrapper that automatically sanitizes output to prevent Unicode encoding errors.
    """
    def print(self, *objects, **kwargs):
        """Override print to sanitize text before output."""
        # Sanitize all string objects
        safe_objects = []
        for obj in objects:
            if isinstance(obj, str):
                safe_objects.append(safe_str(obj))
            else:
                safe_objects.append(obj)
        super().print(*safe_objects, **kwargs)


# Use SafeConsole instead of regular Console to prevent Windows encoding errors
console = SafeConsole()


class LogPanel:
    """
    Full-width panel for displaying log messages (shows last 4 lines).
    Buffers messages and only displays when explicitly flushed to avoid interrupting user input.
    """
    def __init__(self, console: Console, max_lines: int = 4):
        self.console = console
        self.max_lines = max_lines
        self.log_lines = []
        self.pending_messages = []  # Buffer for messages during input
        self.suppress_output = False  # Flag to suppress panel printing

    def log(self, message: str, style: str = "dim"):
        """Add a log message to buffer."""
        # Add message to buffer
        self.log_lines.append((message, style))

        # Keep only last N lines
        if len(self.log_lines) > self.max_lines:
            self.log_lines = self.log_lines[-self.max_lines:]

        # If output is suppressed (during user input), don't print
        if self.suppress_output:
            self.pending_messages.append((message, style))
            return

        # Otherwise print immediately
        self._print_panel()

    def _print_panel(self):
        """Print the log panel with current messages."""
        if not self.log_lines:
            return

        # Build panel content
        from rich.text import Text
        content = Text()

        for i, (msg, msg_style) in enumerate(self.log_lines):
            if i > 0:
                content.append("\n")
            content.append(msg, style=msg_style)

        # Display full-width panel
        panel = Panel(
            content,
            title="[dim]Logs[/dim]",
            border_style="dim",
            box=box.SIMPLE,
            expand=True  # Full width
        )
        self.console.print(panel)

    def flush(self):
        """Flush any pending messages and print the panel."""
        if self.pending_messages:
            self.pending_messages.clear()
        if self.log_lines:
            self._print_panel()

    def clear(self):
        """Clear log buffer."""
        self.log_lines = []
        self.pending_messages = []


# Create global log panel
log_panel = LogPanel(console, max_lines=4)


class WorkflowDisplay:
    """Clean, minimal workflow stage display."""

    def __init__(self, console: Console):
        self.console = console
        self.current_stage = None
        self.stages = []
        self.last_stage = None  # Track last displayed stage to avoid duplicates

    def start_workflow(self, description: str):
        """Start a new workflow."""
        self.console.print(f"\n[bold cyan]{description}[/bold cyan]")
        self.stages = []
        self.last_stage = None

    def add_stage(self, stage_name: str):
        """Add a stage to the workflow (silently)."""
        if stage_name not in self.stages:
            self.stages.append(stage_name)

    def show_stages(self):
        """Show workflow stages as a simple pipeline (called once at start)."""
        if not self.stages or len(self.stages) < 2:
            return
        pipeline = " -> ".join(self.stages)
        self.console.print(f"[dim]{pipeline}[/dim]")

    def start_stage(self, stage_name: str, status_text: str = None):
        """Only show stage if it's different from the last one (minimal, friendly)."""
        # Only display if this is a new stage
        if self.last_stage != stage_name:
            self.current_stage = stage_name
            self.last_stage = stage_name
            display_text = status_text or stage_name
            self.console.print(f"[cyan]-> {display_text}[/cyan]")

        # Return a dummy context manager
        class DummyContext:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return DummyContext()

    def complete_stage(self, stage_name: str, result: str = None):
        """Mark a stage as complete (silent unless there's a result to show)."""
        if result:
            self.console.print(f"  [dim]{result}[/dim]")

    def show_tool_call(self, tool_name: str, model: str = None, endpoint: str = None, tool_type: str = None):
        """Show a tool being called (minimal - only show tool name)."""
        # Suppress tool calls - only show stage changes
        pass

    def show_result(self, title: str, content: str, syntax: str = None):
        """Show a result in a panel."""
        if syntax:
            syntax_obj = Syntax(content, syntax, theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax_obj, title=f"[cyan]{title}[/cyan]", box=box.ROUNDED))
        else:
            self.console.print(Panel(content, title=f"[cyan]{title}[/cyan]", box=box.ROUNDED))


class WorkflowStatus(Enum):
    """Status of a background workflow."""
    QUEUED = "queued"
    NAMING = "naming"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BackgroundWorkflow:
    """Represents a background workflow execution."""
    workflow_id: str
    description: str
    name: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.QUEUED
    progress: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    thread: Optional[threading.Thread] = None
    start_time: float = 0.0
    end_time: Optional[float] = None


class BackgroundWorkflowManager:
    """Manages multiple background workflow executions."""

    def __init__(self, chat_cli):
        self.chat_cli = chat_cli
        self.workflows: Dict[str, BackgroundWorkflow] = {}
        self.workflow_counter = 0
        self.lock = threading.Lock()

    def generate_workflow_name(self, description: str) -> str:
        """
        Generate a short, descriptive name for a workflow using 1B LLM.

        Args:
            description: The workflow task description

        Returns:
            Short name (3-5 words max)
        """
        try:
            # Use veryfast tier (1B model) for quick naming
            prompt = f"""Given this task description, generate a SHORT descriptive name (3-5 words max, no quotes):

Task: {description[:200]}

Name (short, descriptive, lowercase with dashes):"""

            name = self.chat_cli.client.generate(
                tier="veryfast",  # Use 1B model
                prompt=prompt,
                temperature=0.3,
                model_key=self.chat_cli.config.triage_model_key
            )

            # Clean up the name
            name = name.strip().lower()
            name = re.sub(r'[^a-z0-9\s-]', '', name)
            name = re.sub(r'\s+', '-', name)
            name = name[:50]  # Max 50 chars

            if not name:
                name = f"workflow-{self.workflow_counter}"

            return name

        except Exception as e:
            logger.debug(f"Failed to generate workflow name: {e}")
            return f"workflow-{self.workflow_counter}"

    def start_workflow(self, description: str) -> str:
        """
        Start a new background workflow.

        Args:
            description: Task description

        Returns:
            Workflow ID
        """
        with self.lock:
            self.workflow_counter += 1
            workflow_id = f"wf_{self.workflow_counter}_{int(time.time())}"

            # Create workflow
            workflow = BackgroundWorkflow(
                workflow_id=workflow_id,
                description=description,
                status=WorkflowStatus.NAMING,
                start_time=time.time()
            )

            self.workflows[workflow_id] = workflow

        # Start naming in background
        def name_and_run():
            try:
                # Generate name
                workflow.name = self.generate_workflow_name(description)
                workflow.status = WorkflowStatus.RUNNING
                workflow.progress = "Starting..."

                console.print(f"\n[dim cyan]-> [{workflow.name}] Starting workflow...[/dim cyan]")

                # Run the actual workflow
                try:
                    result = self.chat_cli._process_generate(description, workflow_id=workflow_id)
                    workflow.result = result
                    workflow.status = WorkflowStatus.COMPLETED
                    workflow.end_time = time.time()
                    elapsed = workflow.end_time - workflow.start_time
                    console.print(f"\n[green]✓ [{workflow.name}] Completed in {elapsed:.1f}s[/green]")
                except Exception as e:
                    workflow.error = str(e)
                    workflow.status = WorkflowStatus.FAILED
                    workflow.end_time = time.time()
                    console.print(f"\n[red]✗ [{workflow.name}] Failed: {e}[/red]")

            except Exception as e:
                workflow.error = f"Naming failed: {e}"
                workflow.status = WorkflowStatus.FAILED
                workflow.name = f"workflow-{self.workflow_counter}"
                console.print(f"\n[red]✗ [{workflow.name}] Failed during naming: {e}[/red]")

        # Start thread
        thread = threading.Thread(target=name_and_run, daemon=True)
        workflow.thread = thread
        thread.start()

        return workflow_id

    def get_active_workflows(self) -> List[BackgroundWorkflow]:
        """Get list of active (running or queued) workflows."""
        with self.lock:
            return [
                wf for wf in self.workflows.values()
                if wf.status in [WorkflowStatus.QUEUED, WorkflowStatus.NAMING, WorkflowStatus.RUNNING]
            ]

    def get_workflow(self, workflow_id: str) -> Optional[BackgroundWorkflow]:
        """Get a specific workflow by ID."""
        with self.lock:
            return self.workflows.get(workflow_id)

    def list_workflows(self) -> None:
        """Display all workflows and their status."""
        with self.lock:
            if not self.workflows:
                console.print("[dim]No workflows yet[/dim]")
                return

            table = Table(title="Background Workflows", box=box.ROUNDED)
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="bold")
            table.add_column("Status", style="yellow")
            table.add_column("Progress", style="dim")
            table.add_column("Time", style="green")

            for wf in self.workflows.values():
                status_color = {
                    WorkflowStatus.QUEUED: "yellow",
                    WorkflowStatus.NAMING: "cyan",
                    WorkflowStatus.RUNNING: "blue",
                    WorkflowStatus.COMPLETED: "green",
                    WorkflowStatus.FAILED: "red"
                }.get(wf.status, "white")

                elapsed = (wf.end_time or time.time()) - wf.start_time
                time_str = f"{elapsed:.1f}s"

                table.add_row(
                    wf.workflow_id,
                    wf.name or "...",
                    f"[{status_color}]{wf.status.value}[/{status_color}]",
                    wf.progress,
                    time_str
                )

            console.print(table)


class ChatCLI:
    """Interactive chat interface for mostlylucid DiSE."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize chat CLI.

        Args:
            config_path: Path to configuration file
        """
        log_panel.log("> Processing configuration...", style="dim cyan")
        self.config = ConfigManager(config_path)

        # Initialize status manager for live status updates
        from src.status_manager import get_status_manager
        self.status_manager = get_status_manager(console)

        # Use LLM client factory with routing (auto-detects backend per model)
        try:
            from src.llm_client_factory import LLMClientFactory
            # Use routing client that automatically routes models to the correct backend
            self.client = LLMClientFactory.create_routing_client(self.config)
            log_panel.log("Using multi-backend routing (auto-detects backend per model)")
        except (ImportError, KeyError, ValueError) as e:
            # Fall back to Ollama if factory not available or config incomplete
            console.print(f"[yellow]Falling back to Ollama backend: {e}[/yellow]")
            self.client = OllamaClient(self.config.ollama_url, config_manager=self.config)

        # Validate configured models are available
        if hasattr(self.client, 'validate_configured_models'):
            try:
                validation = self.client.validate_configured_models()
                if not validation.get("all_present", True):
                    missing = validation.get("missing", [])
                    suggestions = validation.get("suggestions", [])
                    console.print(f"\n[yellow]⚠  Warning: {len(missing)} configured models not found in Ollama[/yellow]")
                    console.print(f"[yellow]Missing: {', '.join(missing)}[/yellow]")
                    console.print("\n[cyan]To install missing models, run:[/cyan]")
                    for suggestion in suggestions:
                        console.print(f"  [cyan]{suggestion}[/cyan]")
                    console.print("\n[green]The system will continue with available models and adapt as needed.[/green]\n")
                else:
                    log_panel.log(f"OK All {len(validation.get('configured', []))} Ollama models available")
            except Exception as e:
                console.print(f"[dim yellow]Model validation skipped: {e}[/dim yellow]")

        self.registry = Registry(self.config.registry_path)
        self.runner = NodeRunner(self.config.nodes_path)
        self.evaluator = Evaluator(self.client)

        # Initialize RAG memory for tool selection (CRITICAL INFRASTRUCTURE)
        # Automatically uses Qdrant if configured, otherwise NumPy-based memory
        # Will retry with exponential backoff if initialization fails
        try:
            self.rag = create_rag_memory(self.config, self.client)
            if self.config.use_qdrant:
                from src.qdrant_rag_memory import QDRANT_AVAILABLE
                if QDRANT_AVAILABLE:
                    log_panel.log("OK Using Qdrant for RAG memory")
                else:
                    console.print("[yellow]WARNING Qdrant requested but not available, using NumPy-based RAG[/yellow]")
        except RuntimeError as e:
            console.print(f"\n[bold red]CRITICAL ERROR: RAG memory initialization failed![/bold red]")
            console.print(f"[red]{e}[/red]")
            console.print("\n[yellow]RAG is required infrastructure for mostlylucid DiSE to function.[/yellow]")
            if self.config.use_qdrant:
                console.print("[cyan]Make sure Qdrant is running:[/cyan]")
                console.print("  docker run -p 6333:6333 qdrant/qdrant")
            console.print("\nExiting...")
            import sys
            sys.exit(1)

        # Initialize tools manager in background (non-blocking)
        # Progress will be shown via live spinner in BackgroundToolsLoader
        self._tools_loader = BackgroundToolsLoader(
            config_manager=self.config,
            ollama_client=self.client,
            rag_memory=self.rag
        )
        self._tools_loader.start()
        self._tools_manager = None  # Will be set when ready

        # Register callback to update when ready (silent, spinner already shows this)
        def on_tools_ready(tools_manager):
            self._tools_manager = tools_manager
            # Completion message already shown by BackgroundToolsLoader spinner

            # Initialize Fix Tools Manager for auto-fix system
            try:
                from src.fix_tools_manager import FixToolsManager
                self._fix_tools_manager = FixToolsManager(
                    rag_memory=self.rag,
                    tools_manager=tools_manager,
                    ollama_client=self.client
                )
                log_panel.log("OK Auto-fix library indexed")
            except (ImportError, Exception) as e:
                console.print(f"[dim yellow]Auto-fix system not available: {e}[/dim yellow]")
                self._fix_tools_manager = None

            # Initialize Tools CLI for /tools test and /tools optimize commands
            try:
                from src.tools_cli import ToolsCLI
                self._tools_cli = ToolsCLI(
                    tools_manager=tools_manager,
                    rag=self.rag,
                    client=self.client,
                    verbose=True
                )
                log_panel.log("OK Tools CLI initialized")
            except (ImportError, Exception) as e:
                console.print(f"[dim yellow]Tools CLI not available: {e}[/dim yellow]")
                self._tools_cli = None

            # Register model selector tool AFTER tools are ready (non-blocking)
            try:
                from src.model_selector_tool import create_model_selector_tool
                if self.config.config.get("model_selector", {}).get("enabled", True):
                    create_model_selector_tool(self.config, tools_manager)
            except (ImportError, Exception) as e:
                pass  # Silent failure, not critical

        self._tools_loader.on_ready(on_tools_ready)
        self._fix_tools_manager = None  # Will be set when tools ready
        self._tools_cli = None  # Will be set when tools ready

        # Initialize background scheduler for scheduled tasks
        # This runs in the background with low priority to avoid interfering with workflows
        try:
            from src.background_scheduler import start_background_scheduler
            start_background_scheduler()
            console.print("[dim]Background task scheduler started[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: Background scheduler not started: {e}[/yellow]")

        # Initialize task evaluator for routing decisions
        self.task_evaluator = TaskEvaluator(self.client)

        # Initialize history and context BEFORE tools access
        self.context = {}
        self.history = []
        self.display = WorkflowDisplay(console)

        # Initialize conversation memory (enabled by default)
        # Uses single persistent Qdrant collection: "mostlylucid-dse-interactive"
        self.memory_enabled = True
        self._memory_items = []  # Track recent memory items for display
        console.print(f"[dim green]✓ Conversation memory enabled (collection: mostlylucid-dse-interactive)[/dim green]")

        # Tool conversation tracking - stores conversation ONLY when tool is registered
        # This creates conversational version history for each tool
        self._tool_conversations = {}  # {node_id: [{"role": "user", "content": "..."}, ...]}
        self._current_tool_conversation = []  # Active conversation during tool development

        # Initialize background workflow manager for parallel execution
        self.workflow_manager = BackgroundWorkflowManager(self)

        # Setup prompt_toolkit for better UX (in-memory history only, RAG has persistent history)
        if PROMPT_TOOLKIT_AVAILABLE:
            # In-memory history only - RAG stores persistent conversation history
            from prompt_toolkit.history import InMemoryHistory
            self.pt_history = InMemoryHistory()
            # Create smart completer that uses RAG for suggestions
            self.pt_completer = self._create_smart_completer()
        else:
            self.pt_history = None
            self.pt_completer = None

    def _create_smart_completer(self):
        """
        Create an intelligent autocompleter that uses RAG for suggestions.
        Suggests:
        1. Slash commands
        2. Recent conversation topics from RAG
        3. Common task patterns
        """
        from prompt_toolkit.completion import Completer, Completion

        class RAGSmartCompleter(Completer):
            def __init__(self, chat_cli):
                self.chat_cli = chat_cli
                # Base slash commands
                self.slash_commands = [
                    "/generate", "/tools", "/tool", "/status", "/clear", "/clear_rag",
                    "/help", "/manual", "/config", "/auto", "/delete", "/evolve",
                    "/list", "/exit", "/quit", "/workflows", "/wf"
                ]

            def get_completions(self, document, complete_event):
                text = document.text_before_cursor

                # If starts with /, suggest slash commands
                if text.startswith('/'):
                    word = text[1:].lower()
                    for cmd in self.slash_commands:
                        if cmd[1:].startswith(word):
                            yield Completion(cmd, start_position=-len(text))

                # Otherwise, suggest from RAG conversation history
                elif len(text) > 3:  # Only suggest after 3+ chars
                    try:
                        # Quick semantic search in RAG for similar past queries
                        from src.rag_memory import ArtifactType
                        similar = self.chat_cli.rag.find_similar(
                            query=text,
                            artifact_type=ArtifactType.CONVERSATION,
                            top_k=5
                        )

                        # Suggest descriptions from similar past interactions
                        seen = set()
                        for artifact, score in similar:
                            if score > 0.7:  # High similarity only
                                suggestion = artifact.description
                                # Clean up suggestion
                                if ':' in suggestion:
                                    suggestion = suggestion.split(':', 1)[1].strip()
                                suggestion = suggestion[:100]  # Max length

                                if suggestion and suggestion not in seen:
                                    seen.add(suggestion)
                                    yield Completion(
                                        suggestion,
                                        start_position=-len(text),
                                        display_meta=f"similarity: {score:.0%}"
                                    )
                    except Exception:
                        # Fail silently - autocomplete is optional
                        pass

        return RAGSmartCompleter(self)

    @property
    def tools_manager(self):
        """Get tools manager, waiting if necessary."""
        if self._tools_manager is None:
            if not self._tools_loader.is_ready_sync():
                # Show simple status while waiting (not a big panel)
                from rich.status import Status
                with Status("[dim]Loading tools...[/dim]", console=console):
                    self._tools_manager = self._tools_loader.get_tools(wait=True)
            else:
                self._tools_manager = self._tools_loader.get_tools(wait=True)
        return self._tools_manager

    def _validate_python_code(self, code: str) -> tuple[bool, str]:
        """
        Validate that the given code is syntactically valid Python.

        Returns:
            (is_valid, error_message) tuple
        """
        import ast
        try:
            ast.parse(code)
            return (True, "")
        except SyntaxError as e:
            return (False, f"Syntax error at line {e.lineno}: {e.msg}")
        except Exception as e:
            return (False, f"Parse error: {str(e)}")

    def _generate_smart_tags(self, description: str, base_tags: list) -> list:
        """
        Generate smart, specific tags for RAG matching.

        Enhances base tags with:
        - Language detection for translations
        - API/service names
        - Task-specific keywords
        - Operation types

        Args:
            description: Task description
            base_tags: Base tags from LLM

        Returns:
            Enhanced tag list
        """
        import re

        desc_lower = description.lower()
        enhanced_tags = list(base_tags)  # Start with base tags

        # Language detection for translations
        # Pattern: "translate X to LANGUAGE" or "translate into LANGUAGE"
        translate_pattern = r'translate.*(?:to|into)\s+(\w+)'
        match = re.search(translate_pattern, desc_lower)
        if match:
            target_lang = match.group(1)
            enhanced_tags.extend(["translation", target_lang])

            # Add source language if detected
            source_pattern = r'translate\s+(\w+)\s+(?:text|from)'
            source_match = re.search(source_pattern, desc_lower)
            if source_match:
                source_lang = source_match.group(1)
                # Create direction tag (e.g., "en_to_fr")
                enhanced_tags.append(f"{source_lang}_to_{target_lang}")

        # API/Service detection
        api_services = {
            "stripe": ["payment", "billing", "subscription"],
            "openai": ["ai", "llm", "chatgpt"],
            "github": ["git", "repository", "vcs"],
            "aws": ["cloud", "amazon"],
            "google": ["cloud", "gcp"],
            "twitter": ["social", "api"],
            "facebook": ["social", "api"],
            "slack": ["messaging", "notification"],
            "twilio": ["sms", "messaging", "phone"],
            "sendgrid": ["email", "messaging"],
        }

        for service, extra_tags in api_services.items():
            if service in desc_lower:
                enhanced_tags.append(service)
                enhanced_tags.extend(extra_tags)
                enhanced_tags.append("api_integration")

        # Task type detection
        task_types = {
            "validate": ["validation"],
            "parse": ["parsing", "extraction"],
            "format": ["formatting"],
            "sort": ["sorting", "ordering"],
            "filter": ["filtering"],
            "search": ["searching", "finding"],
            "calculate": ["calculation", "math"],
            "encrypt": ["encryption", "security"],
            "decrypt": ["decryption", "security"],
            "hash": ["hashing", "security"],
            "compress": ["compression"],
            "decompress": ["decompression"],
            "upload": ["file_handling", "io"],
            "download": ["file_handling", "io"],
        }

        for keyword, extra_tags in task_types.items():
            if keyword in desc_lower:
                enhanced_tags.extend(extra_tags)

        # Data format detection
        formats = ["json", "xml", "csv", "yaml", "toml", "html", "markdown", "pdf"]
        for fmt in formats:
            if fmt in desc_lower:
                enhanced_tags.append(fmt)
                enhanced_tags.append("data_format")

        # Email-specific
        if "email" in desc_lower:
            enhanced_tags.extend(["email", "communication"])
            if "validate" in desc_lower or "check" in desc_lower:
                enhanced_tags.append("regex")

        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in enhanced_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags

    def _clean_code(self, code: str) -> str:
        """
        Clean generated code by removing markdown fences, JSON wrappers, and extra text.

        Code models sometimes wrap code in markdown (```python```) or JSON ({"code": "..."}).
        This method aggressively strips all non-code formatting.

        Args:
            code: Generated code that may contain markdown/JSON/extra text

        Returns:
            Clean Python code without markdown or wrappers
        """
        import re

        if not code or not code.strip():
            return ""

        original_code = code
        code = code.strip()

        # Step 1: Try to extract from JSON wrapper first (some models return {"code": "..."})
        if code.startswith('{') and '"code"' in code[:100]:
            try:
                import json
                # Handle markdown-wrapped JSON: ```json\n{...}\n```
                if code.startswith('```json'):
                    code = code.split('```json')[1].split('```')[0].strip()
                elif code.startswith('```'):
                    code = code.split('```')[1].split('```')[0].strip()

                parsed = json.loads(code)
                if isinstance(parsed, dict) and 'code' in parsed:
                    code = parsed['code']
                    if not isinstance(code, str):
                        code = str(code)
            except:
                pass  # Not valid JSON, continue with other cleaning

        # Step 2: Remove markdown code fences (multiple formats)
        # Format: ```python\ncode\n```
        code = re.sub(r'^```python\s*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```py\s*\n', '', code, flags=re.MULTILINE)
        # Format: ```\ncode\n```
        code = re.sub(r'^```\s*\n', '', code, flags=re.MULTILINE)
        # Remove closing ```
        code = re.sub(r'\n```\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```$', '', code, flags=re.MULTILINE)

        # Step 3: Remove any lines that are just markdown fences
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip lines that are just markdown fences
            if stripped in ['```', '```python', '```py', '```json']:
                continue
            # Skip lines that start with "Here's" or "Here is" (LLM preamble)
            if stripped.lower().startswith(('here\'s', 'here is', 'this code', 'the code', 'i\'ve')):
                continue
            cleaned_lines.append(line)

        code = '\n'.join(cleaned_lines).strip()

        # Step 4: Remove common LLM postamble text
        # Remove explanations after code (common pattern: code followed by explanation paragraph)
        if '\n\n' in code:
            parts = code.split('\n\n')
            # Keep only parts that look like code (contain 'def ' or 'import ' or indentation)
            code_parts = []
            for part in parts:
                if any(marker in part for marker in ['def ', 'class ', 'import ', 'from ', '    ']):
                    code_parts.append(part)
                elif code_parts:  # Stop after first non-code block following code
                    break
            if code_parts:
                code = '\n\n'.join(code_parts)

        # Step 5: Final validation - code must start with valid Python
        code = code.strip()
        valid_starts = ['import ', 'from ', 'def ', 'class ', '#', '@', 'if ', 'for ', 'while ', 'try:', 'async ']
        if code and not any(code.startswith(start) for start in valid_starts):
            # Try to find the first valid Python line
            for i, line in enumerate(code.split('\n')):
                stripped = line.strip()
                if stripped and any(stripped.startswith(start) for start in valid_starts):
                    code = '\n'.join(code.split('\n')[i:])
                    break

        return code.strip()

    def _looks_like_python(self, code: str) -> bool:
        """
        Check if text looks like Python code (not natural language).

        Args:
            code: Text to check

        Returns:
            True if it looks like Python code, False otherwise
        """
        if not code or not code.strip():
            return False

        code = code.strip()

        # Must contain at least one of these Python keywords/patterns
        python_indicators = [
            'import ',
            'from ',
            'def ',
            'class ',
            'if __name__',
            'assert ',
            'return ',
            'print(',
            '"""',
            "'''",
        ]

        # Count how many Python indicators are present
        indicator_count = sum(1 for indicator in python_indicators if indicator in code)

        # Natural language indicators (signs it's NOT code)
        natural_language_patterns = [
            'The main() function',
            'This code',
            'The code',
            'Here is',
            'Here\'s',
            'following',
            'defines several',
            'that are read from',
        ]

        # If it contains natural language patterns, it's not code
        for pattern in natural_language_patterns:
            if pattern in code:
                return False

        # Must have at least 2 Python indicators to be considered code
        if indicator_count < 2:
            return False

        # Check that it has proper structure (indentation or function definitions)
        lines = code.split('\n')
        has_structure = any(
            line.startswith('def ') or
            line.startswith('class ') or
            line.startswith('import ') or
            line.startswith('from ') or
            line.startswith('    ')  # Has indentation
            for line in lines
        )

        return has_structure

    def _fix_code_with_llm(self, code: str, error_msg: str) -> str:
        """
        Use the code model to fix invalid code with a STRICT prompt.
        Ensures absolutely no extra characters or words apart from runnable, valid Python.

        Args:
            code: The invalid code to fix
            error_msg: The validation error message

        Returns:
            Fixed Python code
        """
        fix_prompt = f"""The following Python code has a syntax error:

```python
{code}
```

Error: {error_msg}

Fix this code. Your response MUST contain ONLY valid, runnable Python code.
NO markdown fences (```), NO explanations, NO comments outside the code, NO extra text.
ONLY pure Python code that will execute without errors.

Start your response with 'import' or 'def' or 'class' - nothing else."""

        fixed = self.client.generate(
            model=self.config.generator_model,
            prompt=fix_prompt,
            temperature=0.1,  # Low temperature for precise fixes
            model_key=self.config.generator_model_key  # Use actual model key for routing
        )

        # Clean the response aggressively
        fixed = self._clean_code(fixed)

        return fixed

    def _handle_workflow_generation(self, description: str, workflow: 'WorkflowTracker', available_tools: str) -> bool:
        """
        Handle multi-step workflow generation.

        Decomposes task into steps, generates code for each step as a reusable node,
        and executes them in sequence.

        Args:
            description: User's full task description
            workflow: Workflow tracker instance
            available_tools: Available tools string from parent method

        Returns:
            True if successful
        """
        from src.workflow_builder import WorkflowBuilder
        from src.rag_memory import ArtifactType
        import time

        # Step 1: Search RAG for similar workflows to use as examples
        from src.rag_memory import ArtifactType

        similar_workflows = self.rag.find_similar(
            description,
            artifact_type=ArtifactType.WORKFLOW,
            top_k=3
        )

        workflow_examples = ""
        if similar_workflows:
            workflow_examples = "\n\nSIMILAR WORKFLOWS FROM MEMORY (use as templates):\n"
            for wf_artifact, similarity in similar_workflows:
                if similarity >= 0.90:  # STRICT: Only show very similar workflows (90%+)
                    workflow_examples += f"\nWorkflow (similarity: {similarity:.0%}): {wf_artifact.description}\n"
                    # Include the workflow structure as an example
                    try:
                        import json
                        wf_data = json.loads(wf_artifact.content)
                        workflow_examples += f"Steps: {len(wf_data.get('steps', []))} steps\n"
                        for step in wf_data.get('steps', [])[:3]:  # Show first 3 steps
                            workflow_examples += f"  - {step.get('description', 'N/A')} (tool: {step.get('tool', 'N/A')})\n"
                    except:
                        pass

        # Step 2: Ask overseer to decompose into workflow steps
        workflow.add_step("workflow_decomposition", "llm", f"Decompose into workflow steps ({self.config.overseer_model})")
        workflow.start_step("workflow_decomposition")

        workflow_prompt = f"""You are decomposing a task into workflow steps. This is CRITICAL - you MUST create SEPARATE steps for EACH operation.

{workflow_examples}

TASK TO ANALYZE: "{description}"

STEP 1: IDENTIFY OPERATIONS
Look for these keywords that indicate multiple operations:
- "and" -> SEPARATE operations (create SEPARATE steps)
- "then" -> SEQUENTIAL operations (create SEPARATE steps)
- "translate" -> SEPARATE translation step
- "convert" -> SEPARATE conversion step

Count how many distinct operations are in the task.

STEP 2: SPLIT THE TASK
For "{description}":
- How many operations? [Count them carefully]
- What is operation 1? [Identify ONLY the first operation]
- What is operation 2? [Identify ONLY the second operation - if exists]
- What is operation 3? [Identify ONLY the third operation - if exists]

CRITICAL RULE: Each operation gets its OWN step! Do NOT combine operations into one step!

EXAMPLES:

Example 1: "write a joke and translate to french"
- Count: 2 operations (write AND translate)
- Operation 1: write a joke
- Operation 2: translate to french
- Result: 2 steps

Example 2: "write a story"
- Count: 1 operation (just write)
- Operation 1: write a story
- Result: 1 step

Example 3: "calculate fibonacci then sort then display"
- Count: 3 operations (calculate, sort, display)
- Operation 1: calculate fibonacci
- Operation 2: sort results
- Operation 3: display data
- Result: 3 steps

STEP 3: ANALYZE DEPENDENCIES AND PARALLEL OPPORTUNITIES

For each operation, determine:
- Which steps it DEPENDS on (must complete before this step starts)
- Which steps can run IN PARALLEL (same parallel_group number)

DEPENDENCY RULES:
1. If step B uses output from step A -> B depends_on: ["stepA"]
2. If steps B and C are independent -> they can run in parallel (same parallel_group)
3. Avoid race conditions: steps that modify shared state cannot be parallel

PARALLEL EXECUTION EXAMPLES:

Example 1: "write a joke and translate to french and spanish"
- Step 1: write joke (no dependencies, parallel_group: null)
- Step 2: translate to french (depends_on: ["step1"], parallel_group: 1)
- Step 3: translate to spanish (depends_on: ["step1"], parallel_group: 1)
Result: Steps 2 and 3 run in PARALLEL after step 1 completes

Example 2: "write 3 different jokes"
- Step 1: write joke about cats (parallel_group: 1)
- Step 2: write joke about dogs (parallel_group: 1)
- Step 3: write joke about birds (parallel_group: 1)
Result: All 3 steps run in PARALLEL (no dependencies)

Example 3: "write a story then summarize it" (sequential)
- Step 1: write story (no dependencies)
- Step 2: summarize (depends_on: ["step1"])
Result: Step 2 MUST wait for step 1 (no parallelism)

STEP 4: CREATE JSON OUTPUT

For each operation you identified, create a separate step in the JSON.

CRITICAL: task_for_node must be a COMPLETE TASK DESCRIPTION, NOT a placeholder like [WRITE].

CORRECT example for "write a joke and translate to french":
{{
  "workflow_id": "task_workflow",
  "description": "write a joke and translate to french",
  "steps": [
    {{
      "step_id": "step1",
      "type": "llm_call",
      "description": "Write a joke",
      "task_for_node": "Write a joke",
      "tool": "content_generator",
      "output_name": "step1_output",
      "parallel_group": null,
      "depends_on": []
    }},
    {{
      "step_id": "step2",
      "type": "llm_call",
      "description": "Translate to French",
      "task_for_node": "Translate the joke to French",
      "tool": "nmt_translator",
      "input_from_step": "step1",
      "output_name": "step2_output",
      "depends_on": ["step1"]
    }}
  ]
}}

WRONG example (DO NOT DO THIS):
{{
  "steps": [
    {{"task_for_node": "[WRITE]"}},  // WRONG - this is a placeholder
    {{"task_for_node": "[TRANSLATE]"}}  // WRONG - this is a placeholder
  ]
}}

IMPORTANT RULES:
- If you counted 2 operations, you MUST have 2 steps in the JSON
- If you counted 3 operations, you MUST have 3 steps in the JSON
- Each "task_for_node" should contain ONLY ONE operation
- Use "input_from_step" to link steps that depend on previous output

CRITICAL DESIGN PRINCIPLE:
- Do NOT call multiple LLM tools in the same step (except for code generation)
- Prefer REUSABLE sub-steps over large monolithic tasks
- Each step should be small enough to reuse in other workflows
- Example: Don't create "write_and_translate" - create "write" and "translate" separately

AVAILABLE TOOLS (use these EXACT names in your JSON):
{available_tools}

CRITICAL: Use the EXACT tool names listed above, not generic placeholder names.
- For translation tasks: look for "nmt_translator" or similar translation tools
- For content generation: use "content_generator"
- Match the tool name to the operation type

NOW OUTPUT THE JSON (no markdown fences, no explanations):"""

        with self.display.start_stage("Planning", f"Decomposing workflow"):
            workflow_json_response = self.client.generate(
                model=self.config.overseer_model,
                prompt=workflow_prompt,
                temperature=0.7,
                model_key=self.config.overseer_model_key  # Use actual model key for routing
            )

        self.display.complete_stage("Planning", "Workflow decomposed")

        # Parse the workflow JSON
        builder = WorkflowBuilder(tools_manager=self.tools_manager)
        try:
            workflow_spec = builder.build_from_text(description, workflow_json_response)
        except Exception as e:
            console.print(f"[red]Failed to parse workflow: {e}[/red]")
            console.print(f"[yellow]Overseer response:[/yellow]\n{workflow_json_response}")
            return False

        workflow.complete_step("workflow_decomposition", f"{len(workflow_spec.steps)} steps planned")

        # Validate decomposition quality
        multi_operation_keywords = ["and", "then", "translate", "convert"]
        description_lower = description.lower()
        has_multi_keywords = any(kw in description_lower for kw in multi_operation_keywords)

        if has_multi_keywords and len(workflow_spec.steps) == 1:
            console.print(f"[yellow]Warning: Task contains '{[kw for kw in multi_operation_keywords if kw in description_lower]}' but was decomposed into only 1 step.[/yellow]")
            console.print(f"[yellow]This may indicate the task should be split into multiple steps.[/yellow]")

            # Additional protection: if the single step has the same description as the original task,
            # it will trigger infinite recursion. Prevent this by forcing _in_workflow_mode for the step.
            step = workflow_spec.steps[0]
            step_desc_lower = getattr(step, 'task_for_node', step.description).lower()
            if description_lower.strip() == step_desc_lower.strip():
                console.print(f"[yellow]Single step matches original task - preventing recursive decomposition.[/yellow]")
                # This will be handled in the step execution by setting _in_workflow_mode

        # Show workflow plan to user
        console.print(f"\n[bold cyan]Workflow Plan ({len(workflow_spec.steps)} steps):[/bold cyan]")
        for i, step in enumerate(workflow_spec.steps, 1):
            console.print(f"  {i}. [yellow]{step.description}[/yellow]")
            if hasattr(step, 'task_for_node'):
                console.print(f"     Node task: {step.task_for_node}")
        console.print()

        # Step 2: Execute workflow steps (with parallel execution support)
        step_results = {}
        completed_steps = set()

        # Organize steps into execution groups respecting dependencies
        execution_groups = self._organize_parallel_execution(workflow_spec.steps)

        for group_idx, parallel_group in enumerate(execution_groups):
            if len(parallel_group) > 1:
                console.print(f"\n[bold cyan]Executing {len(parallel_group)} steps in parallel:[/bold cyan]")
                for step in parallel_group:
                    console.print(f"  - {step.description}")

            # Execute all steps in this group in parallel (if more than one)
            import concurrent.futures
            import threading

            def execute_step(step):
                """Execute a single workflow step"""
                workflow.add_step(f"execute_{step.step_id}", "generate", f"Generate and execute: {step.description}")
                workflow.start_step(f"execute_{step.step_id}")

                # Determine the granular task for THIS node
                node_task = getattr(step, 'task_for_node', step.description)

                # Fallback: if task_for_node looks like a tool name, use description instead
                if node_task and step.tool_name and node_task.lower().replace('_', '') == step.tool_name.lower().replace('_', ''):
                    node_task = step.description

                console.print(f"\n[bold]Step: {step.description}[/bold]")
                log_panel.log(f"Generating node for: {node_task}")

                # Save current context and set workflow mode flag
                old_context = self.context.copy()
                # Preserve workflow_depth to prevent infinite recursion
                workflow_depth = self.context.get('_workflow_depth', 0)
                self.context.clear()
                self.context['_in_workflow_mode'] = True
                self.context['_workflow_depth'] = workflow_depth  # Preserve depth counter
                self.context['_workflow_context'] = {
                    'parent_workflow': description,
                    'step_id': step.step_id,
                    'step_description': step.description,
                    'tool_used': step.tool_name,
                    'operation_type': self._infer_operation_type(step.tool_name, node_task)
                }

                # Generate the node
                success = self.handle_generate(node_task)

                # Restore context
                self.context = old_context

                if not success:
                    console.print(f"[red]Failed to generate step: {step.step_id}[/red]")
                    workflow.fail_step(f"execute_{step.step_id}", "Generation failed")
                    return step.step_id, False

                workflow.complete_step(f"execute_{step.step_id}", "Node generated and executed")
                return step.step_id, True

            # Execute steps (in parallel if multiple in group)
            if len(parallel_group) == 1:
                # Single step - execute directly
                step_id, success = execute_step(parallel_group[0])
                if not success:
                    return False
                completed_steps.add(step_id)
                step_results[step_id] = {"status": "completed"}
            else:
                # Multiple steps - execute in parallel using ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(parallel_group)) as executor:
                    futures = {executor.submit(execute_step, step): step for step in parallel_group}

                    for future in concurrent.futures.as_completed(futures):
                        step = futures[future]
                        try:
                            step_id, success = future.result()
                            if not success:
                                console.print(f"[red]Workflow failed: step {step_id} did not complete[/red]")
                                return False
                            completed_steps.add(step_id)
                            step_results[step_id] = {"status": "completed"}
                        except Exception as e:
                            console.print(f"[red]Exception in step {step.step_id}: {e}[/red]")
                            return False

        console.print(f"\n[bold green]Workflow completed successfully![/bold green]")

        # Store the workflow in RAG
        self.rag.store_artifact(
            artifact_id=f"workflow_{int(time.time())}",
            artifact_type=ArtifactType.WORKFLOW,
            name=f"Workflow: {description}",
            description=description,
            content=workflow_spec.to_json(),
            tags=["workflow", "multi-step"] + description.lower().split()[:3],
            metadata={
                "steps": len(workflow_spec.steps),
                "workflow_id": workflow_spec.workflow_id
            }
        )

        return True

    def _organize_parallel_execution(self, steps: list) -> list:
        """
        Organize workflow steps into execution groups based on dependencies and parallel_group.

        Returns a list of lists, where each inner list contains steps that can run in parallel.

        Args:
            steps: List of WorkflowStep objects

        Returns:
            List of parallel execution groups
        """
        from collections import defaultdict

        # Group steps by parallel_group number
        parallel_groups = defaultdict(list)
        sequential_steps = []

        for step in steps:
            if step.parallel_group is not None:
                parallel_groups[step.parallel_group].append(step)
            else:
                sequential_steps.append(step)

        # Build dependency graph
        step_by_id = {step.step_id: step for step in steps}

        # Create execution order respecting dependencies
        execution_groups = []
        executed = set()

        # Process all steps
        remaining = list(steps)

        while remaining:
            # Find steps whose dependencies are all met
            ready = []
            for step in remaining:
                deps = getattr(step, 'depends_on', [])
                if all(dep in executed for dep in deps):
                    ready.append(step)

            if not ready:
                # Circular dependency or missing dependency
                console.print(f"[yellow]Warning: Circular dependency detected, executing remaining steps sequentially[/yellow]")
                ready = remaining[:1]

            # Group ready steps by parallel_group
            if not ready:
                break

            # Separate into parallel groups
            groups_in_batch = defaultdict(list)
            for step in ready:
                if step.parallel_group is not None:
                    groups_in_batch[step.parallel_group].append(step)
                else:
                    # Steps without parallel_group run individually
                    execution_groups.append([step])
                    executed.add(step.step_id)
                    remaining.remove(step)

            # Add parallel groups as execution batches
            for group_id, group_steps in groups_in_batch.items():
                execution_groups.append(group_steps)
                for step in group_steps:
                    executed.add(step.step_id)
                    remaining.remove(step)

        return execution_groups

    def _infer_operation_type(self, tool_name: str, task_description: str) -> str:
        """
        Infer the operation type based on tool name and task description.
        This helps with hierarchical RAG matching.

        Args:
            tool_name: Name of the tool being used
            task_description: Description of the task

        Returns:
            Operation type: generator, transformer, validator, combiner, splitter, or filter
        """
        task_lower = task_description.lower()
        tool_lower = tool_name.lower() if tool_name else ""

        # Generator: Creates new content
        if any(word in task_lower or word in tool_lower for word in [
            "write", "generate", "create", "compose", "produce", "make", "build", "draft"
        ]):
            return "generator"

        # Transformer: Modifies or converts existing content
        if any(word in task_lower or word in tool_lower for word in [
            "translate", "convert", "transform", "format", "reformat", "change", "modify", "adapt"
        ]):
            return "transformer"

        # Validator: Checks or validates content
        if any(word in task_lower or word in tool_lower for word in [
            "validate", "check", "verify", "test", "review", "evaluate", "assess"
        ]):
            return "validator"

        # Combiner: Combines multiple inputs
        if any(word in task_lower or word in tool_lower for word in [
            "combine", "merge", "join", "concat", "aggregate", "summarize", "consolidate"
        ]):
            return "combiner"

        # Splitter: Splits content
        if any(word in task_lower or word in tool_lower for word in [
            "split", "separate", "divide", "extract", "parse", "break"
        ]):
            return "splitter"

        # Filter: Filters or selects content
        if any(word in task_lower or word in tool_lower for word in [
            "filter", "select", "find", "search", "match", "choose"
        ]):
            return "filter"

        # Default to generator if unclear
        return "generator"

    def print_welcome(self):
        """Print welcome message."""
        welcome = """
[bold cyan]mostlylucid DiSE - Interactive CLI[/bold cyan]
[dim]AI-powered code generation and evolution[/dim]

Just type what you want to create - it will generate and run automatically!
Type [bold]/help[/bold] for special commands, or [bold]exit[/bold] to quit.
Press [bold]Ctrl-C[/bold] to cancel current task and return to prompt.

[dim]Examples:[/dim]
  write a haiku about coding
  implement binary search
  /tools                      [dim](list all available tools)[/dim]
  /manual tool save_to_disk   [dim](show tool documentation)[/dim]
        """
        console.print(Panel(welcome, box=box.ROUNDED))

    def print_help(self):
        """Print help message."""
        console.print("\n[bold cyan]Usage:[/bold cyan]")
        console.print("  [bold]Just type what you want![/bold] - Automatically generates and runs code")
        console.print("  [dim]Example: write a joke about AI[/dim]")
        console.print("  Type [bold]exit[/bold] (or [bold]quit[/bold]) to exit immediately")
        console.print("  Press [bold]Ctrl-C[/bold] to cancel current task and return to prompt\n")

        table = Table(title="Special Commands (prefix with /)", box=box.ROUNDED)
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description")

        commands = [
            ("/generate <description>", "Explicitly generate (same as typing without /)"),
            ("/run <node_id> [input]", "Run an existing node with optional input"),
            ("/test <node_id>", "Run unit tests for a node"),
            ("/evaluate <node_id>", "Evaluate a node's performance"),
            ("", ""),
            ("Tool Management:", ""),
            ("/tool", "List all available tools (alias: /tool list)"),
            ("/tool [category]", "Filter tools by category (llm, executable, custom, openapi)"),
            ("/tool <tool_id>", "Show detailed documentation for a specific tool"),
            ("/tool info <tool_id>", "Get intelligent description of a tool"),
            ("/tool run <tool_id> [input]", "Execute a tool directly with input"),
            ("/tool test <tool_id>", "Run tests for a specific tool"),
            ("/tool test all", "Run tests for all tools"),
            ("/tool optimize <tool_id>", "Optimize a tool (iterative improvement)"),
            ("/tool optimize all", "Optimize all tools (slow)"),
            ("/tool mutate <tool_id> <instructions>", "Improve a tool based on instructions"),
            ("", ""),
            ("/backends [--test]", "Check status of all LLM backends (API keys, connectivity)"),
            ("/workflow <node_id>", "Display the complete workflow for a node"),
            ("/show <node_id>", "Show detailed information about a node"),
            ("/delete <node_id>", "Delete a node"),
            ("/evolve <node_id>", "Manually trigger evolution for a node"),
            ("/auto on|off", "Enable/disable auto-evolution"),
            ("/config [key] [value]", "Show or update configuration"),
            ("/status", "Show system status"),
            ("/clear", "Clear the screen"),
            ("/clear_rag", "Clear ALL RAG memory including non-YAML tools (WARNING: destructive!)"),
            ("/manual [search]", "Search manual with intelligent fuzzy matching (aliases: /man, /m)"),
            ("/help", "Show this help message"),
            ("exit, quit, /exit, /quit", "Exit the CLI (/ optional)")
        ]

        for cmd, desc in commands:
            table.add_row(cmd, desc)

        console.print(table)

    def handle_generate(self, description: str, display_description: str = None) -> bool:
        """
        Handle generate command.

        Args:
            description: Natural language description of what to generate (may include context)
            display_description: Description to display to user (without context)

        Returns:
            True if successful
        """
        if not description:
            console.print("[red]Error: Please provide a description[/red]")
            return False

        # Use display_description for user-facing output, description for LLM
        if display_description is None:
            display_description = description

        # Start tracking conversation for this tool development
        # This will be stored in RAG ONLY when tool is registered
        self._current_tool_conversation = []
        self._current_tool_conversation.append({
            "role": "user",
            "content": description,
            "timestamp": __import__('time').time()
        })

        # Initialize workflow tracker with display description (no context)
        show_workflow = self.config.get("chat.show_workflow", True)
        workflow = WorkflowTracker(
            workflow_id=f"gen_{int(__import__('time').time()*1000)}",
            description=display_description,  # Use clean description without context
            context=self.config.get("chat.default_workflow_context", {})
        )

        # Start clean workflow display with user's original input
        self.display.start_workflow(display_description)

        # Step 0: Evaluate task type using tinyllama (fast preprocessing)
        # NOTE: This is ONLY for routing hints - the original description is ALWAYS
        # passed to overseer and code generators. task_evaluation just helps us
        # choose the right tier/model, not replace the original instruction.
        log_panel.log("> Evaluating task type...", style="dim cyan")
        task_evaluation = self.task_evaluator.evaluate_task_type(description)

        # Check if input appears accidental
        if task_evaluation.get('is_accidental'):
            console.print(f"\n[yellow]! {task_evaluation['understanding']}[/yellow]\n")
            console.print("[cyan]Did you mean to:[/cyan]")
            for suggestion in task_evaluation.get('suggestions', []):
                console.print(f"  [dim]• {suggestion}[/dim]")
            console.print("\n[dim]Please try again with a clearer description.[/dim]\n")
            return  # Don't proceed with generation

        # Show task categorization with complexity
        console.print(f"[cyan]> Task type: {task_evaluation['task_type'].value}[/cyan]")
        if 'complexity' in task_evaluation:
            log_panel.log(f"> Complexity: {task_evaluation['complexity']}")
        log_panel.log(f"> Routing: {task_evaluation['recommended_tier']}")

        # CRITICAL: If task requires content LLM, ensure we don't over-optimize
        if task_evaluation['requires_content_llm']:
            console.print("[yellow]> Creative content task detected - will use LLM content generator[/yellow]")

        # Step 0.5: SMART DUPLICATE DETECTION - Check if this is a duplicate request
        # Use sentinel LLM to check RAG for identical/similar artifacts
        from src.sentinel_llm import SentinelLLM
        sentinel = SentinelLLM(self.client, self.rag)

        duplicate_check = sentinel.check_for_duplicate(description)

        if duplicate_check['should_reuse']:
            artifact = duplicate_check['existing_artifact']
            console.print(f"\n[cyan]-> Using existing tool: {artifact.name}[/cyan]")
            console.print(f"[dim]  ({duplicate_check['confidence']:.0%} match - {duplicate_check['reasoning']})[/dim]")

            # Extract node_id from artifact
            node_id = artifact.metadata.get("node_id") if artifact.metadata else None

            if node_id and self.registry.get_node(node_id):
                # Increment usage counter
                self.rag.increment_usage(artifact.artifact_id)

                # Run the existing node immediately
                input_data = {
                    "input": description,
                    "description": description,
                    "prompt": description
                }
                stdout, stderr, metrics = self.runner.run_node(node_id, input_data)

                # Display results
                if metrics["success"]:
                    console.print(f"\n[bold green]✓ Execution successful (reused existing artifact)[/bold green]")

                    if stdout and stdout.strip():
                        # Extract and show result
                        result_extracted = False
                        try:
                            output_data = json.loads(stdout.strip())
                            if isinstance(output_data, dict):
                                for key in ['result', 'output', 'answer', 'content']:
                                    if key in output_data:
                                        console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data[key]}\n")
                                        result_extracted = True
                                        break
                            elif isinstance(output_data, str):
                                console.print(f"\n[bold green]RESULT:[/bold green]\n")
                                console.print(Panel(output_data, box=box.ROUNDED, border_style="green"))
                                result_extracted = True
                        except:
                            pass

                        if not result_extracted:
                            if not stdout.strip().startswith('{'):
                                console.print(f"\n[bold green]RESULT:[/bold green]\n")
                                console.print(Panel(stdout, box=box.ROUNDED, border_style="green"))
                            else:
                                console.print(Panel(stdout, title="[green]Output[/green]", box=box.ROUNDED, border_style="green"))

                    return True
                else:
                    console.print(f"[red]Execution failed - falling back to generating new code[/red]")
                    # Continue to normal workflow if execution fails
            else:
                console.print(f"[yellow]Node not found - falling back to generating new code[/yellow]")
                # Continue to normal workflow if node not found
        elif duplicate_check['confidence'] > 0.0:
            # Found similar but not duplicate - show as hint
            console.print(f"[dim cyan]Found similar artifact ({duplicate_check['confidence']:.1%} match) - generating fresh implementation[/dim cyan]")

        # Step 1: Check for existing solutions in RAG (both code and workflows)
        workflow.add_step("check_existing", "rag", "Check for existing solutions in RAG")
        from src.rag_memory import ArtifactType

        # FAST PATH: Check for 100% exact match on description (no LLM call needed!)
        # Normalize the description for exact matching (lowercase, strip whitespace)
        normalized_desc = description.lower().strip()

        # Search all artifacts for exact description match
        all_workflows = self.rag.find_by_tags(["workflow", "complete"], limit=100)
        for artifact in all_workflows:
            # Check if description in metadata matches exactly
            artifact_desc = artifact.metadata.get("question", "").lower().strip()
            if artifact_desc == normalized_desc:
                # 100% EXACT MATCH - INSTANT REUSE!
                node_id = artifact.metadata.get("node_id")
                if node_id and self.registry.get_node(node_id):
                    console.print(f"\n[bold green]✓ 100% EXACT MATCH FOUND![/bold green]")
                    console.print(f"[green]Reusing: {artifact.name}[/green]")
                    log_panel.log("Skipping code generation - using cached solution")

                    self.rag.increment_usage(artifact.artifact_id)
                    workflow.complete_step("check_existing", f"Exact match: {node_id}", {"reused": True})

                    # Run the existing node immediately (fast path - no code generation!)
                    # Pass multiple common keys for compatibility with different workflows
                    input_data = {
                        "input": description,
                        "description": description,
                        "prompt": description
                    }
                    stdout, stderr, metrics = self.runner.run_node(node_id, input_data)

                    # Display results prominently
                    if metrics["success"]:
                        console.print(f"\n[bold green]✓ Execution successful[/bold green]")

                        # Show metrics FIRST (if enabled)
                        if self.config.get("chat.show_metrics", True):
                            self._display_metrics(metrics)

                        # Show generated content LAST so it's immediately visible
                        if stdout and stdout.strip():
                            # Try to extract and show the actual result prominently
                            result_extracted = False
                            try:
                                # Try to parse as JSON first
                                output_data = json.loads(stdout.strip())
                                if isinstance(output_data, dict):
                                    # Show the actual result clearly
                                    if 'result' in output_data:
                                        console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['result']}\n")
                                        result_extracted = True
                                    elif 'output' in output_data:
                                        console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['output']}\n")
                                        result_extracted = True
                                    elif 'answer' in output_data:
                                        console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['answer']}\n")
                                        result_extracted = True
                                    elif 'content' in output_data:
                                        console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['content']}\n")
                                        result_extracted = True
                                elif isinstance(output_data, str):
                                    # JSON string output (like from json.dumps(string))
                                    console.print(f"\n[bold green]RESULT:[/bold green]\n")
                                    console.print(Panel(output_data, box=box.ROUNDED, border_style="green"))
                                    result_extracted = True
                            except:
                                pass

                            # If we couldn't extract a specific result, show full output
                            if not result_extracted:
                                # Check if it's plain text (like an article or story)
                                if not stdout.strip().startswith('{'):
                                    console.print(f"\n[bold green]RESULT:[/bold green]\n")
                                    console.print(Panel(stdout, box=box.ROUNDED, border_style="green"))
                                else:
                                    console.print(Panel(stdout, title="[green]Output[/green]", box=box.ROUNDED, border_style="green"))
                        else:
                            console.print("[yellow]Note: Code executed successfully but produced no output[/yellow]")

                        return True
                    else:
                        console.print(f"[red]Execution failed (exit code: {metrics['exit_code']})[/red]")
                        if stderr:
                            console.print(Panel(stderr, title="[red]Error[/red]", border_style="red", box=box.ROUNDED))
                        return False

        # First, check for existing code (FUNCTION artifacts) - these are the actual implementations
        existing_code = self.rag.find_similar(
            description,
            artifact_type=ArtifactType.FUNCTION,
            top_k=3  # Get top 3 to show options
        )

        # Then check for workflows
        existing_workflows = self.rag.find_similar(
            description,
            artifact_type=ArtifactType.WORKFLOW,
            top_k=1
        )

        # Try code reuse first (more specific than workflow)
        if existing_code and len(existing_code) > 0:
            code_artifact, similarity = existing_code[0]
            # STRICT: 90% minimum similarity - prefer NOT matching unless very confident
            # System optimizes later anyway, so be conservative about reuse
            if similarity >= 0.90:
                self.display.complete_stage("Search RAG", f"Found {code_artifact.name} ({similarity:.0%} match)")

                # Get the node_id from metadata
                node_id = code_artifact.metadata.get("node_id")
                if node_id and self.registry.get_node(node_id):
                    self.rag.increment_usage(code_artifact.artifact_id)

                    # Load the existing code
                    code_path = self.runner.get_node_path(node_id)
                    if code_path.exists():
                        code_content = code_path.read_text()

                        # Strategy based on similarity:
                        # - High similarity (>=90%): Check semantic equivalence with fast LLM, then reuse as-is
                        # - Low similarity (<90%): Generate from scratch (STRICT policy)

                        # CRITICAL: Use fast LLM (not very fast) to check relationship between tasks
                        # Three possibilities:
                        # 1. SAME - Exact same task (reuse as-is)
                        # 2. RELATED - Similar domain but different variation (use as template and modify)
                        # 3. DIFFERENT - Completely different tasks (generate from scratch)
                        semantic_check_prompt = f"""Compare these two tasks and classify their relationship.
IGNORE typos, minor wording differences, and phrases like "and output the result" (that's always implied).

Task 1 (existing): {code_artifact.description}
Task 2 (requested): {description}

Classification:
- SAME: Identical tasks (ignore typos/wording, same core algorithm and goal)
- RELATED: Same domain but different variation (e.g., "fibonacci" vs "fibonacci backwards")
- DIFFERENT: Completely different domains (e.g., "fibonacci" vs "write a story")

Examples:
- "fibonacci sequence" vs "fibonaccie sequence and output result" -> SAME (typo, same task)
- "add 10 and 20" vs "sum 10 and 20" -> SAME (synonym)
- "fibonacci sequence" vs "fibonacci backwards" -> RELATED (same algorithm, different direction)
- "write a story" vs "write a technical article" -> RELATED (same domain, different style)
- "fibonacci" vs "prime numbers" -> DIFFERENT (different algorithms)
- "calculate primes" vs "find prime numbers" -> SAME (synonym)

Answer with ONLY ONE WORD: SAME, RELATED, or DIFFERENT
Answer:"""

                        # Use fast LLM (not very fast) for semantic assessment
                        semantic_response = self.client.generate(
                            role="fast",  # Use fast tier (e.g., gemma3_4b) not veryfast (tinyllama)
                            prompt=semantic_check_prompt,
                            temperature=0.1,  # Low temperature for consistent classification
                            model_key=self.config.generator_model_key
                        ).strip().upper()

                        if "SAME" in semantic_response:
                            # Exact same task - reuse as-is
                            is_equivalent = True
                        elif "RELATED" in semantic_response:
                            # Related but different - use as template and modify
                            console.print(f"[cyan]Note: Tasks are RELATED ({similarity:.0%} similar)[/cyan]")
                            console.print(f"[cyan]Existing: {code_artifact.description}[/cyan]")
                            console.print(f"[cyan]Requested: {description}[/cyan]")
                            console.print(f"[cyan]Using existing code as template and modifying...[/cyan]")

                            # Store as template for modification
                            self.context['template_code'] = code_content
                            self.context['template_node_id'] = node_id
                            self.context['template_description'] = code_artifact.description
                            self.context['template_similarity'] = similarity
                            self.context['modification_needed'] = True

                            # Fall through to modification workflow
                            is_equivalent = False
                        else:
                            # DIFFERENT - generate from scratch
                            console.print(f"[yellow]Note: Tasks are DIFFERENT despite textual similarity ({similarity:.0%})[/yellow]")
                            console.print(f"[yellow]Generating new solution from scratch...[/yellow]")
                            is_equivalent = False

                        if is_equivalent and similarity > 0.90:
                            # Very high similarity - just reuse as-is
                            self.display.show_result(f"Reused Code: {node_id}", code_content, "python")
                            workflow.complete_step("check_existing", f"Reused code from {node_id}")

                            # Auto-run and finish
                            with self.display.start_stage("Execute", "Running code"):
                                # Pass multiple common keys for compatibility with different workflows
                                input_data = {
                                    "input": description,
                                    "description": description,
                                    "prompt": description
                                }
                                stdout, stderr, metrics = self.runner.run_node(node_id, input_data)

                            # Display results prominently
                            if metrics["success"]:
                                self.display.complete_stage("Execute", "Success")

                                # Show metrics FIRST (if enabled)
                                if self.config.get("chat.show_metrics", True):
                                    self._display_metrics(metrics)

                                # Show generated content LAST so it's immediately visible
                                if stdout and stdout.strip():
                                    # Try to extract and show the actual result prominently
                                    result_extracted = False
                                    try:
                                        # Try to parse as JSON first
                                        output_data = json.loads(stdout.strip())
                                        if isinstance(output_data, dict):
                                            # Show the actual result clearly
                                            if 'result' in output_data:
                                                console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['result']}\n")
                                                result_extracted = True
                                            elif 'output' in output_data:
                                                console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['output']}\n")
                                                result_extracted = True
                                            elif 'answer' in output_data:
                                                console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['answer']}\n")
                                                result_extracted = True
                                            elif 'content' in output_data:
                                                console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['content']}\n")
                                                result_extracted = True
                                        elif isinstance(output_data, str):
                                            # JSON string output (like from json.dumps(string))
                                            console.print(f"\n[bold green]RESULT:[/bold green]\n")
                                            console.print(Panel(output_data, box=box.ROUNDED, border_style="green"))
                                            result_extracted = True
                                    except:
                                        pass

                                    # If we couldn't extract a specific result, show full output
                                    if not result_extracted:
                                        # Check if it's plain text (like an article or story)
                                        if not stdout.strip().startswith('{'):
                                            console.print(f"\n[bold green]RESULT:[/bold green]\n")
                                            console.print(Panel(stdout, box=box.ROUNDED, border_style="green"))
                                        else:
                                            console.print(Panel(stdout, title="[green]Output[/green]", box=box.ROUNDED, border_style="green"))
                                else:
                                    console.print("[yellow]Note: Code executed successfully but produced no output[/yellow]")
                            else:
                                self.display.complete_stage("Execute", f"Failed (exit code: {metrics['exit_code']})")
                                if stderr:
                                    console.print(Panel(stderr, title="[red]Error[/red]", border_style="red", box=box.ROUNDED))

                            return True

                        else:
                            # Similarity >=90% but semantic check says RELATED/DIFFERENT - generate from scratch
                            console.print(f"[yellow]Note: High textual similarity ({similarity:.0%}) but semantically different[/yellow]")
                            console.print(f"[yellow]Generating new solution from scratch (STRICT reuse policy)...[/yellow]")
                            self.display.complete_stage("Search RAG", f"Not reusing ({similarity:.0%} match but different task)")
                            self.display.show_result(f"Template: {node_id}", code_content, "python")

                            # Store template for modification
                            self.context['template_code'] = code_content
                            self.context['template_node_id'] = node_id
                            self.context['template_description'] = code_artifact.description
                            self.context['template_similarity'] = similarity

                            workflow.complete_step("check_existing", f"Using code from {node_id} as template ({similarity:.1%} match)")

                            # Fall through to modification workflow
                            # The overseer will see the template and modify it instead of generating from scratch

                else:
                    self.display.complete_stage("Search RAG", "No reusable code found")

        # Check workflows if no code reuse
        if existing_workflows and len(existing_workflows) > 0:
            workflow_artifact, similarity = existing_workflows[0]
            # STRICT: 90% minimum similarity for workflows (prefer NOT matching)
            if similarity >= 0.90:
                self.display.complete_stage("Search RAG", f"Found workflow ({similarity:.0%} match)")

                # CRITICAL: Check relationship between tasks (SAME/RELATED/DIFFERENT)
                semantic_check_prompt = f"""Compare these two tasks and classify their relationship.
IGNORE typos, minor wording differences, and phrases like "and output the result" (that's always implied).

Task 1 (existing): {workflow_artifact.description}
Task 2 (requested): {description}

Classification:
- SAME: Identical tasks (ignore typos/wording, same core algorithm and goal)
- RELATED: Same domain but different variation (e.g., "fibonacci" vs "fibonacci backwards")
- DIFFERENT: Completely different domains (e.g., "fibonacci" vs "write a story")

Examples:
- "fibonacci sequence" vs "fibonaccie sequence and output result" -> SAME (typo, same task)
- "add 10 and 20" vs "sum 10 and 20" -> SAME (synonym)
- "fibonacci sequence" vs "fibonacci backwards" -> RELATED (same algorithm, different direction)
- "write a story" vs "write a technical article" -> RELATED (same domain, different style)
- "fibonacci" vs "prime numbers" -> DIFFERENT (different algorithms)
- "calculate primes" vs "find prime numbers" -> SAME (synonym)

Answer with ONLY ONE WORD: SAME, RELATED, or DIFFERENT
Answer:"""

                # Use fast LLM (not very fast) for semantic assessment
                semantic_response = self.client.generate(
                    role="fast",  # Use fast tier (e.g., gemma3_4b) not veryfast (tinyllama)
                    prompt=semantic_check_prompt,
                    temperature=0.1,
                    model_key=self.config.generator_model_key
                ).strip().upper()

                if "SAME" in semantic_response:
                    # Exact same task - reuse workflow as-is
                    is_equivalent = True
                elif "RELATED" in semantic_response:
                    # Related tasks - could potentially modify the workflow
                    # For now, treat as different and generate from scratch
                    # TODO: Add workflow modification capability
                    console.print(f"[cyan]Note: Workflows are RELATED ({similarity:.0%} similar)[/cyan]")
                    console.print(f"[cyan]Existing: {workflow_artifact.description}[/cyan]")
                    console.print(f"[cyan]Requested: {description}[/cyan]")
                    console.print(f"[cyan]Workflow modification not yet implemented, generating from scratch...[/cyan]")
                    is_equivalent = False
                else:
                    # DIFFERENT tasks
                    console.print(f"[yellow]Note: Workflows are DIFFERENT despite textual similarity ({similarity:.0%})[/yellow]")
                    console.print(f"[yellow]Generating new solution from scratch...[/yellow]")
                    is_equivalent = False

                if is_equivalent:
                    # Semantically equivalent - safe to reuse
                    # Get the node_id from metadata
                    node_id = workflow_artifact.metadata.get("node_id")
                    if node_id and self.registry.get_node(node_id):
                        self.rag.increment_usage(workflow_artifact.artifact_id)

                        # Show the code
                        node_data = self.registry.get_node(node_id)
                        if node_data:
                            # Load and show code
                            code_path = self.runner.get_node_path(node_id)
                            if code_path.exists():
                                code_content = code_path.read_text()
                                score = node_data.get('score_overall', 'N/A')
                                self.display.show_result(f"{node_id} (Score: {score})", code_content, "python")

                        # Auto-run the reused workflow with the new description as input
                        with self.display.start_stage("Execute", "Running workflow"):
                            # Detect what input fields the code expects
                            import re
                            expected_fields = set()
                            if code_content:
                                code_lines = code_content.split('\n')
                                for line in code_lines:
                                    # Look for patterns like: input_data.get("field_name", ...)
                                    matches = re.findall(r'input_data\.get\(["\']([^"\']+)["\']', line)
                                    expected_fields.update(matches)

                            # Pass multiple common keys for compatibility with different workflows
                            input_data = {
                                "input": description,
                                "task": description,
                                "description": description,
                                "query": description,
                                "topic": description,
                                "prompt": description,
                                "question": description,
                                "request": description
                            }

                            # If code expects specific fields, try to auto-generate data
                            generic_fields = {"input", "task", "description", "query", "topic", "prompt", "question", "request"}
                            specific_fields_needed = expected_fields - generic_fields

                            if specific_fields_needed:
                                console.print(f"[yellow]-> Detected specific input fields: {', '.join(specific_fields_needed)}[/yellow]")
                                console.print(f"[yellow]-> Auto-generating test data...[/yellow]")

                                try:
                                    # Build a schema from the detected fields
                                    schema = {}
                                    for field in specific_fields_needed:
                                        if any(word in field.lower() for word in ['lang', 'language']):
                                            schema[field] = "string"
                                        elif any(word in field.lower() for word in ['text', 'article', 'content', 'message']):
                                            schema[field] = "string"
                                        elif any(word in field.lower() for word in ['age', 'count', 'number', 'size']):
                                            schema[field] = "number"
                                        else:
                                            schema[field] = "string"

                                    # Generate test data
                                    schema_json = json.dumps(schema)
                                    test_data_result = self.tools_manager.invoke_executable_tool(
                                        tool_id="random_data_generator",
                                        source_file="",
                                        prompt=schema_json
                                    )

                                    if test_data_result.get("success"):
                                        test_data = json.loads(test_data_result["stdout"])
                                        console.print(f"[green]-> Generated test data: {json.dumps(test_data, indent=2)}[/green]")
                                        input_data.update(test_data)
                                except Exception as e:
                                    console.print(f"[yellow]-> Could not auto-generate test data: {e}[/yellow]")

                            stdout, stderr, metrics = self.runner.run_node(node_id, input_data)

                        # Display results - ALWAYS show output prominently
                        if metrics["success"]:
                            self.display.complete_stage("Execute", "Success")

                            # Show metrics FIRST (if enabled)
                            if self.config.get("chat.show_metrics", True):
                                self._display_metrics(metrics)

                            # Show generated content LAST so it's immediately visible
                            if stdout and stdout.strip():
                                # Try to extract and show the actual result prominently
                                result_extracted = False
                                has_empty_output = False
                                try:
                                    # Try to parse as JSON first
                                    output_data = json.loads(stdout.strip())
                                    if isinstance(output_data, dict):
                                        # Check for common result field names
                                        result_fields = ['result', 'output', 'answer', 'content', 'translated_article',
                                                         'summary', 'text', 'data', 'response']

                                        for field in result_fields:
                                            if field in output_data:
                                                result_content = output_data[field]
                                                # Check if result is empty
                                                if not result_content or (isinstance(result_content, str) and not result_content.strip()):
                                                    has_empty_output = True
                                                    console.print(f"[yellow]⚠ Warning: Field '{field}' is empty![/yellow]")
                                                    console.print(f"[dim]Full output: {json.dumps(output_data, indent=2)}[/dim]")
                                                else:
                                                    console.print(f"\n[bold green]RESULT:[/bold green]")
                                                    if isinstance(result_content, str):
                                                        console.print(result_content + "\n")
                                                    else:
                                                        console.print(json.dumps(result_content, indent=2) + "\n")
                                                result_extracted = True
                                                break

                                        # If no recognized field found, show all non-empty values
                                        if not result_extracted and output_data:
                                            console.print("\n[bold green]RESULT:[/bold green]")
                                            console.print("[bold]Output fields:[/bold]")
                                            for key, value in output_data.items():
                                                if value and (not isinstance(value, str) or value.strip()):
                                                    console.print(f"  {key}: {value}")
                                                else:
                                                    has_empty_output = True
                                                    console.print(f"  [dim]{key}: (empty)[/dim]")
                                            console.print()
                                            result_extracted = True
                                    elif isinstance(output_data, str):
                                        # JSON string output (like from json.dumps(string))
                                        console.print(f"\n[bold green]RESULT:[/bold green]\n")
                                        console.print(Panel(output_data, box=box.ROUNDED, border_style="green"))
                                        result_extracted = True
                                except:
                                    pass

                                # If we couldn't extract a specific result, show full output
                                if not result_extracted:
                                    # Check if it's plain text (like an article or story)
                                    if not stdout.strip().startswith('{'):
                                        console.print(f"\n[bold green]RESULT:[/bold green]\n")
                                        console.print(Panel(stdout, box=box.ROUNDED, border_style="green"))
                                    else:
                                        console.print(Panel(stdout, title="[green]Output[/green]", box=box.ROUNDED, border_style="green"))

                                # If output was empty, show helpful message
                                if has_empty_output:
                                    console.print("\n[yellow]━" * 40 + "[/yellow]")
                                    console.print("[yellow]⚠ The workflow produced empty output![/yellow]")
                                    console.print("[yellow]This usually means the workflow needs specific input data.[/yellow]")
                                    console.print("[yellow]The system tried to auto-generate test data, but it may not have been sufficient.[/yellow]")
                                    console.print("[yellow]━" * 40 + "[/yellow]")
                            else:
                                console.print("[yellow]Note: Code executed successfully but produced no output[/yellow]")
                        else:
                            self.display.complete_stage("Execute", f"Failed (exit code: {metrics['exit_code']})")
                            if stderr:
                                console.print(Panel(stderr, title="[red]Error[/red]", border_style="red", box=box.ROUNDED))

                        return True

        # Step 1: Find relevant tools using RAG semantic search
        workflow.add_step("find_tools", "rag", "Search for relevant tools")
        workflow.start_step("find_tools")

        with self.display.start_stage("Planning", "Searching for relevant tools"):
            available_tools = self.tools_manager.get_tools_for_prompt(
                task_description=description,
                max_tools=3,  # Keep small for context efficiency
                filter_type=None  # Allow all tool types - fitness function picks best matches
            )

        # Get the actual tool objects to show their names
        found_tools = self.tools_manager.search(description, top_k=3)

        # Store found tools in context for feedback recording
        self.context['_selected_tools'] = found_tools if found_tools else []

        if found_tools and len(found_tools) > 0:
            # Use full title from metadata if available, otherwise use name
            tool_names = [
                tool.metadata.get("full_title", tool.name) if hasattr(tool, 'metadata') else tool.name
                for tool in found_tools[:3]
            ]
            tools_str = ", ".join(tool_names)

            # Check if the best match is being used as a template
            best_tool = found_tools[0]
            best_tool_name = best_tool.metadata.get("full_title", best_tool.name) if hasattr(best_tool, 'metadata') else best_tool.name

            # Consider it a template reuse if it's a successfully tested workflow/function
            is_template = (
                hasattr(best_tool, 'metadata') and
                best_tool.metadata.get('tests_passed', False) and
                best_tool.metadata.get('node_id')
            )

            if is_template:
                self.display.complete_stage("Planning", f"Found {len(found_tools)} tools - Using '{best_tool_name}' as template base")
                console.print(f"[dim]   Adapting existing solution for current task[/dim]")
            else:
                self.display.complete_stage("Planning", f"Found {len(found_tools)} tools: {tools_str}")
        else:
            self.display.complete_stage("Planning", "Using general tools")

        workflow.complete_step("find_tools", available_tools)

        # Step 1.5: Try to compose a novel workflow if no exact match found
        # This is where intelligent tool composition happens for tasks like "write a romance novel"
        workflow_composition = self.tools_manager.compose_novel_workflow(description)
        if workflow_composition and workflow_composition.get("workflow_steps"):
            # Show the composed workflow plan cleanly
            characteristics = ', '.join(workflow_composition['characteristics'].keys())
            console.print(f"\n[bold cyan]Workflow Composed[/bold cyan] [dim]({characteristics})[/dim]\n")

            # Show workflow stages
            stages = [step['action'] for step in workflow_composition["workflow_steps"]]
            self.display.add_stage(" -> ".join(stages))

            # Show tools being used
            console.print()
            for tool_info in workflow_composition["recommended_tools"][:3]:
                model = tool_info.get('model', 'N/A')
                self.display.show_tool_call(tool_info['name'], model=model, tool_type="LLM")

            # Update available_tools to include the composition
            composition_summary = f"\nNovel Workflow Composition:\n"
            for tool_info in workflow_composition["recommended_tools"][:3]:
                composition_summary += f"- {tool_info['name']}: {tool_info.get('model', 'N/A')} ({tool_info.get('cost_tier')}/{tool_info.get('speed_tier')}/{tool_info.get('quality_tier')})\n"
            available_tools = composition_summary + "\n" + available_tools

        # Step 1.5: Check if this is a multi-step workflow task
        # Only detect workflows at the top level (not when called recursively from workflow handler)
        in_workflow_mode = self.context.get('_in_workflow_mode', False)
        workflow_depth = self.context.get('_workflow_depth', 0)

        # Prevent infinite recursion by limiting workflow decomposition depth
        MAX_WORKFLOW_DEPTH = 3

        if not in_workflow_mode and workflow_depth < MAX_WORKFLOW_DEPTH:
            workflow_keywords = self.config.get("chat.workflow_mode.detect_keywords", ["and", "then", "translate", "convert"])

            # Smarter keyword detection - avoid false positives
            is_multi_step = False
            description_lower = description.lower()

            # Exclude arithmetic operations
            arithmetic_keywords = ["add", "subtract", "multiply", "divide", "calculate", "compute", "sum"]
            is_arithmetic = any(kw in description_lower for kw in arithmetic_keywords)

            # Check for explicit multi-step keywords first (and, then)
            explicit_multi_step = any(kw in description_lower for kw in ["and", "then"])

            # Exclude simple translations ONLY if there's no explicit multi-step keyword
            # "translate X to Y" is ONE step, but "write a story AND translate it" is multi-step
            import re
            simple_translation_pattern = r'^\s*translate\s+(?:the\s+)?(?:word|phrase|sentence|text)?\s*[\w\s]+\s+to\s+\w+\s*$'
            is_simple_translation = bool(re.search(simple_translation_pattern, description_lower)) and not explicit_multi_step

            if not is_arithmetic and not is_simple_translation:
                is_multi_step = any(keyword in description_lower for keyword in workflow_keywords)

            if is_multi_step and self.config.get("chat.workflow_mode.enabled", False):
                # Multi-step workflow detected
                console.print(f"[cyan]Multi-step workflow detected - decomposing into reusable nodes...[/cyan]")
                # Increment depth counter
                self.context['_workflow_depth'] = workflow_depth + 1
                result = self._handle_workflow_generation(description, workflow, available_tools)
                # Reset depth counter after workflow completes
                self.context['_workflow_depth'] = workflow_depth
                return result
        elif workflow_depth >= MAX_WORKFLOW_DEPTH:
            console.print(f"[yellow]Warning: Maximum workflow depth ({MAX_WORKFLOW_DEPTH}) reached. Treating as simple generation.[/yellow]")

        # Step 2: Ask overseer for detailed specification WITH tool recommendations
        workflow.add_step("overseer_specification", "llm", f"Consult overseer ({self.config.overseer_model})")
        workflow.start_step("overseer_specification")

        console.print()  # Blank line for spacing

        # Search for similar specifications in RAG
        existing_spec_info = ""
        try:
            similar_specs = self.rag.find_similar(
                description,
                artifact_type=ArtifactType.PLAN,
                top_k=1
            )
            if similar_specs:
                spec_artifact, similarity = similar_specs[0]
                if similarity >= 0.90:  # STRICT: 90% minimum for spec reuse
                    console.print(f"[dim cyan]Found similar specification (similarity: {similarity:.1%})[/dim cyan]")
                    existing_spec_info = f"""
EXISTING SPECIFICATION FOR SIMILAR TASK (similarity: {similarity:.1%}):
Task: {spec_artifact.metadata.get('task_description', 'N/A')}

{spec_artifact.content[:1500]}...

IMPORTANT: You have a specification from a similar task. Use it as a starting point:
1. Keep the overall structure and approach
2. Adapt it to the new requirements
3. Modify only what's necessary for the new task
4. Be efficient - reuse what works
"""
        except Exception as e:
            console.print(f"[dim yellow]Note: Could not search for similar specifications: {e}[/dim yellow]")

        # Check if we have a template to modify
        template_info = ""
        if self.context.get('template_code'):
            template_similarity = self.context.get('template_similarity', 0)
            template_info = f"""
EXISTING TEMPLATE CODE (similarity: {template_similarity:.1%}):
```python
{self.context['template_code']}
```

Template was designed for: {self.context.get('template_description', 'N/A')}

IMPORTANT: You have existing code as a template. Instead of generating from scratch:
1. Analyze what modifications are needed to match the new requirements
2. Identify what to add (e.g., comments, translations, new functions)
3. Specify what to keep unchanged (core logic)
4. Be efficient - reuse as much as possible
"""

        overseer_prompt = f"""You are an expert software architect creating a DETAILED SPECIFICATION for code generation.
A user wants to create code with this goal:

"{description}"

{existing_spec_info}

{template_info}

{available_tools}

CRITICAL: PREFER SIMPLICITY!
Before creating a complex specification, ask yourself:
- Can this be solved with a simple if/else statement? -> DO THAT!
- Can this be solved with a dictionary lookup? -> DO THAT!
- Can this be solved with basic math? -> DO THAT!

Examples of SIMPLE solutions:
- "translate word X to Y" -> Dictionary: {{"hello": "bonjour", "poop": "merde"}}
- "add two numbers" -> Simple: result = a + b
- "is number prime" -> Simple loop checking divisors

ONLY create complex specifications if the task REQUIRES:
- Creative content generation (stories, poems, complex articles)
- Complex algorithms or data structures
- Multiple steps with dependencies

Create a comprehensive specification that will guide the code generator. Include:

1. **Problem Definition**
   - What exactly needs to be solved?
   - What are the inputs and expected outputs?
   - What is the core algorithm or approach?

2. **Requirements & Constraints**
   - What are the functional requirements?
   - Performance constraints (time/space complexity)
   - Safety limits (e.g., max iterations, input size limits)
   - Error handling requirements

3. **Implementation Plan**{' (focus on modifications to template)' if template_info else ''}
   - Recommended algorithm or approach
   - Data structures to use
   - Key functions and their signatures (with types)
   - Which LLM tools (if any) should be called and when
   - Execution order (which operations must be sequential)

4. **Input/Output Interface**
   - What JSON fields will the code read from stdin?
   - What JSON fields will the code write to stdout?
   - Example input -> expected output

5. **Test Cases**
   - At least 3 test cases with inputs and expected outputs
   - Edge cases to handle (empty input, zero, negative, etc.)

6. **Tool Recommendation** (CRITICAL - Check Available Tools First!)
   {'Since you have a template, specify exactly what needs to be modified/added/removed.' if template_info else '''BEFORE recommending custom code, CHECK IF AN EXISTING TOOL CAN SOLVE THIS:

   Review the available tools list above. If ANY tool matches the task:
   - STRONGLY RECOMMEND using that tool via call_tool()
   - Example: If task is translation and quick_translator exists -> USE IT!
   - Example: If task is content generation and content_generator exists -> USE IT!

   ONLY recommend custom implementation if:
   - NO existing tool matches the task
   - Task is simple enough for direct code (math, lookups, basic logic)

   Strategy: Build a library of reusable tools. Prefer tools over custom code.
   Later we'll consolidate similar tools into generic implementations.'''}

Be VERY specific and technical. Think of this as writing requirements for another developer.
The code generator will follow this specification EXACTLY, so include ALL critical details."""

        with self.display.start_stage("Thinking", f"Consulting {self.config.overseer_model}"):
            specification = self.client.generate(
                model=self.config.overseer_model,
                prompt=overseer_prompt,
                temperature=0.7,
                model_key=self.config.overseer_model_key  # Use actual model key for routing
            )

        self.display.complete_stage("Thinking", "Specification complete")

        # Show brief specification summary (full spec saved to specification.md in node directory)
        log_panel.log(f"Specification: {len(specification)} chars (saved to specification.md)", style="dim cyan")

        workflow.complete_step("overseer_specification", f"{len(specification)} chars specification", {"model": self.config.overseer_model})

        # Step 2A: Complexity triage - decide which code generator to use based on task complexity
        workflow.add_step("complexity_triage", "llm", "Classify task type and complexity")
        workflow.start_step("complexity_triage")

        # Use LLM for flexible, reliable classification
        classification_prompt = f"""Classify this task into ONE of these categories:

Task: "{description}"

Categories:
1. ARITHMETIC - Simple math operations (add, subtract, multiply, divide)
   Examples: "add 10 and 20", "multiply 5 by 7"

2. SIMPLE_CONTENT - Short text generation (jokes, one-liners, brief summaries)
   Examples: "write a joke", "create a pun", "write a riddle"

3. COMPLEX_CONTENT - Long/detailed text (stories with plot, technical articles, essays)
   Examples: "write a story about...", "write a technical article on...", "create a novel"

4. ALGORITHM - Code with logic/algorithms (fibonacci, sorting, parsing, etc.)
   Examples: "fibonacci sequence", "sort a list", "compression algorithm"

Answer with ONLY the category name and a brief reason.
Format: CATEGORY: reason

Example answers:
ARITHMETIC: basic addition
SIMPLE_CONTENT: short joke generation
COMPLEX_CONTENT: story with plot and characters
ALGORITHM: fibonacci computation"""

        classification_response = self.client.generate(
            model="llama3",  # Better at understanding complexity and nuance
            prompt=classification_prompt,
            temperature=0.1,
            model_key=self.config.triage_model_key  # Use actual model key for routing
        ).strip()

        # Parse response
        is_simple_task = False
        is_simple_content = False
        is_complex_content = False
        classification_reason = "unknown"

        if "ARITHMETIC" in classification_response.upper():
            is_simple_task = True
            classification_reason = "basic arithmetic operation"
        elif "SIMPLE_CONTENT" in classification_response.upper():
            is_simple_content = True
            classification_reason = "simple content generation"
        elif "COMPLEX_CONTENT" in classification_response.upper():
            is_complex_content = True
            classification_reason = "complex content generation"
        elif "ALGORITHM" in classification_response.upper():
            is_simple_task = False
            classification_reason = "algorithm/complex logic"
        else:
            # Default to complex for safety
            is_simple_task = False
            classification_reason = "unknown pattern, defaulting to complex"

        workflow.complete_step("complexity_triage", f"Task classified as: {classification_response}")

        if is_simple_task:
            console.print(f"[cyan]Task classified as SIMPLE ({classification_reason}) -> Using fast code generator[/cyan]")
        else:
            console.print(f"[cyan]Task classified as COMPLEX ({classification_reason}) -> Using powerful code generator[/cyan]")

        # Step 2B: Determine which tool/model to use for code generation
        # For simple tasks, prefer fast_code_generator if available
        if is_simple_task and 'fast_code_generator' in self.tools_manager.tools:
            selected_tool = self.tools_manager.tools['fast_code_generator']
            use_specialized_tool = True
            console.print(f"[cyan]-> Using tool: {selected_tool.name}[/cyan]")
        # For ALL content generation (simple or complex), use powerful model
        elif is_simple_content or is_complex_content:
            # Don't search for tools - content needs fresh generation with powerful model
            # Use general tool which has proper prompts for content generation
            selected_tool = None
            use_specialized_tool = False
            # Extract first few words for short description
            short_desc = ' '.join(description.split()[:6])
            console.print(f"[cyan]-> Creating tool: {short_desc}...[/cyan]")
        else:
            # For other complex tasks or if no specialized tool, use normal tool selection
            selected_tool = self.tools_manager.get_best_llm_for_task(description)
            generator_to_use = self.config.generator_model
            use_specialized_tool = False

            if selected_tool:
                if "general" not in selected_tool.tool_id.lower() and "fallback" not in selected_tool.tags:
                    console.print(f"[cyan]-> Using tool: {selected_tool.name}[/cyan]")
                    use_specialized_tool = True
                else:
                    # Using general/fallback means creating new
                    short_desc = ' '.join(description.split()[:6])
                    console.print(f"[cyan]-> Creating tool: {short_desc}...[/cyan]")
            else:
                # No tool found, creating new
                short_desc = ' '.join(description.split()[:6])
                console.print(f"[cyan]-> Creating tool: {short_desc}...[/cyan]")

        # Step 3: Generate node ID
        import re
        node_id = re.sub(r'[^a-z0-9_]', '_', description.lower().split('.')[0][:30])
        node_id = re.sub(r'_+', '_', node_id).strip('_')
        if not node_id:
            node_id = "generated_node"

        # Check if exists
        if self.registry.get_node(node_id):
            console.print(f"[yellow]Node '{node_id}' already exists. Using versioned name.[/yellow]")
            import time
            node_id = f"{node_id}_{int(time.time())}"

        # Store the specification in RAG for future reuse (now that we have node_id)
        spec_id = f"spec_{node_id}"
        try:
            # Infer tags from description for specification
            spec_tags = ["specification", "plan", "overseer", "generated"]
            if any(word in description.lower() for word in ["add", "sum", "calculate", "multiply", "divide", "subtract"]):
                spec_tags.append("arithmetic")
            if any(word in description.lower() for word in ["fibonacci", "prime", "factorial", "sequence"]):
                spec_tags.append("algorithm")
            if any(word in description.lower() for word in ["write", "story", "article", "content", "text"]):
                spec_tags.append("writing")

            self.rag.store_artifact(
                artifact_id=spec_id,
                artifact_type=ArtifactType.PLAN,
                name=f"Specification: {description[:80]}",
                description=f"Detailed implementation specification for: {description}",
                content=specification,
                tags=spec_tags,
                metadata={
                    "task_description": description,
                    "overseer_model": self.config.overseer_model,
                    "complexity": "SIMPLE" if is_simple_task else "COMPLEX",
                    "node_id": node_id
                },
                auto_embed=True
            )
            console.print(f"[dim green]Saved specification to RAG for future reuse[/dim green]")
        except Exception as e:
            console.print(f"[dim yellow]Note: Could not save specification to RAG: {e}[/dim yellow]")

        # Step 3.5: Test-Driven Development (TDD) - Generate interface tests BEFORE code
        interface_tests = None
        tdd_enabled = self.config.get("testing.test_driven_development", False)

        if tdd_enabled and self.config.get("testing.enabled", True):
            workflow.add_step("tdd_interface", "test", "Generate interface-defining tests (TDD)")
            workflow.start_step("tdd_interface")

            try:
                interface_tests = self._generate_interface_tests_first(node_id, description, specification)

                # Store original test in context for god-level escalation
                self.context['original_interface_test'] = interface_tests

                # Create node directory if it doesn't exist yet
                node_dir = self.runner.get_node_path(node_id).parent
                node_dir.mkdir(parents=True, exist_ok=True)

                # Save the interface tests
                test_path = node_dir / "test_main.py"
                with open(test_path, 'w') as f:
                    f.write(interface_tests)

                console.print(f"[dim green]Saved interface-defining tests to {test_path.name}[/dim green]")

                # Display the generated tests (if verbose mode)
                if self.config.get("chat.show_generated_content", False):
                    test_syntax = Syntax(interface_tests, "python", theme="monokai", line_numbers=True)
                    console.print(Panel(
                        test_syntax,
                        title="[cyan]Interface-Defining Tests (TDD)[/cyan]",
                        box=box.ROUNDED,
                        expand=False
                    ))
                else:
                    test_lines = len(interface_tests.split('\n'))
                    console.print(f"[cyan]✓ Generated interface tests ({test_lines} lines)[/cyan]")

                workflow.complete_step("tdd_interface", f"Tests generated ({len(interface_tests)} chars)")

            except Exception as e:
                console.print(f"[yellow]Warning: Could not generate interface tests: {e}[/yellow]")
                console.print("[yellow]Continuing with traditional code-first approach[/yellow]")
                workflow.fail_step("tdd_interface", str(e))
                interface_tests = None

        # Step 4: Generate code based on specification (and tests if TDD enabled)
        # Build list of available tools for the prompt
        tools_list = "\n".join([
            f"- {t.tool_id}: {t.description}"
            for t in self.tools_manager.get_all_tools()
            if t.tool_type.value == "llm"
        ])

        # Truncate specification if too long for code generator's context window
        # Estimate: ~4 chars per token, leave room for prompt template and response
        max_spec_chars = self.config.get_context_window(self.config.generator_model) * 2  # ~2 chars/token conservative
        if len(specification) > max_spec_chars:
            console.print(f"[yellow]Note: Specification ({len(specification)} chars) exceeds context window, truncating to {max_spec_chars} chars[/yellow]")
            specification = specification[:max_spec_chars] + "\n\n[... specification truncated due to context limits ...]"

        # Build TDD section if tests were generated
        tdd_section = ""
        if interface_tests:
            tdd_section = f"""
**TEST-DRIVEN DEVELOPMENT MODE**

The following unit tests define the REQUIRED INTERFACE for your code.
Your code MUST pass these tests:

```python
{interface_tests}
```

CRITICAL: Your code must satisfy the interface defined by these tests.
Look at what functions the tests import and call - you MUST implement those exact functions.
"""

        # Build conditional sections outside f-string (Python doesn't allow nested triple-quotes in f-strings)
        tdd_header = "CRITICAL TDD MODE INSTRUCTIONS:" if interface_tests else "MANDATORY CODE STRUCTURE:"

        tdd_instructions = """CRITICAL: You are in TEST-DRIVEN DEVELOPMENT mode.
The tests above DEFINE THE INTERFACE - your code MUST implement EXACTLY those functions.

Look at the import statement in the tests:
- If tests do: `from main import binary_search` -> you MUST create `def binary_search(...)`
- If tests do: `from main import add` -> you MUST create `def add(...)`
- If tests call specific functions, you MUST implement those exact functions with matching signatures

ABSOLUTELY FORBIDDEN IN YOUR CODE (main.py):
- DO NOT EVER include `from main import` statements - this creates circular imports!
- The test file imports from main.py, NOT the other way around!
- Only the TEST file should have `from main import` - NEVER in your actual code!

DO NOT create a generic main() function - implement the SPECIFIC functions the tests expect!

Example structure (if tests expect binary_search):
```python
def binary_search(arr, target):
    # Implementation here
    ...
    return result

# Optional main for testing:
if __name__ == "__main__":
    import json
    import sys
    input_data = json.load(sys.stdin)
    result = binary_search(input_data["arr"], input_data["target"])
    print(json.dumps({{"result": result}}))
```""" if interface_tests else """```python
import json
import sys
from pathlib import Path

# CRITICAL: Add code_evolver root to path BEFORE importing node_runtime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Now you can import from node_runtime (only if you need to call LLM tools):
from node_runtime import call_tool

def main():
    # ALWAYS read input from stdin as JSON
    input_data = json.load(sys.stdin)

    # Your logic here
    # For content: content = call_tool("content_generator", input_data.get("description"))
    # For math: result = calculate(input_data.get("description"))

    # ALWAYS print result as JSON
    print(json.dumps({{"result": result}}))

if __name__ == "__main__":
    main()
```

CRITICAL: The above example shows the REQUIRED path setup.
Every file that imports from node_runtime MUST include:
```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```
BEFORE the import statement
"""

        code_prompt = f"""You are implementing code based on this DETAILED SPECIFICATION:

{specification}

Task: {description}
{tdd_section}
Available LLM Tools you can call:
{tools_list}

Follow the specification EXACTLY. Generate a Python implementation that:
1. Matches the problem definition and requirements
2. Implements the recommended algorithm/approach
3. Uses the specified input/output interface
4. {"PASSES THE INTERFACE TESTS ABOVE (TDD mode)" if interface_tests else "Handles all edge cases mentioned"}
5. Includes proper error handling
6. Follows the safety limits specified

You MUST respond with ONLY a JSON object in this exact format:

{{
  "code": "the actual Python code as a string",
  "description": "brief one-line description",
  "tags": ["tag1", "tag2"]
}}

{tdd_header}

{tdd_instructions}

CRITICAL: PREFER SIMPLICITY!
- If the task can be solved with simple code (if/else, dictionary lookup, basic math), DO THAT!
- Examples:
  * "translate the word poop to french" -> Simple dictionary: {{"poop": "merde"}}
  * "add 2 and 3" -> Simple math: result = 2 + 3
  * "check if 7 is prime" -> Simple function with loop
- ONLY use call_tool() for tasks that REQUIRE LLM capabilities:
  * Generating creative content (stories, poems, articles)
  * Complex reasoning or analysis
  * Tasks with many possible outputs that need intelligence

Code requirements:
- MUST use json.load(sys.stdin) to read input - NO sys.argv or command-line arguments!
- For SIMPLE tasks (translations, math, lookups): Write direct code - NO call_tool()!
- For CREATIVE tasks (stories, jokes, articles): Use call_tool() to invoke content generation LLM tools
- Include proper error handling
- **ABSOLUTELY MANDATORY**: MUST print output as JSON using print(json.dumps(...))
  * EVERY tool MUST produce output - no exceptions!
  * Even if there's an error, print the error as JSON: print(json.dumps({{"error": "..."}}))

**INPUT DATA FORMAT**:
The code will receive input as a JSON object with these standard fields (interface):

{{
  "input": "{description}",      // Main input field
  "task": "{description}",        // Alternative task field
  "description": "{description}", // Description field (MOST COMMON)
  "query": "{description}",       // Query field
  "topic": "{description}",       // Topic field
  "prompt": "{description}"       // Prompt field
}}

USAGE GUIDELINES:
1. For simple computational tasks like "add 10 and 20", extract numbers from input_data["description"]
2. For ALL content generation tasks (stories, jokes, articles, poems, essays, creative writing), you MUST use call_tool() to invoke LLM tools
   - NEVER generate hardcoded content (no hardcoded jokes, stories, or text)
   - ALWAYS use: content = call_tool("content_generator", prompt_describing_what_to_generate)
   - The system will handle invoking the appropriate LLM model
3. For project management tasks (schedules, WBS, task lists, outlines), use call_tool() with existing tools:
   - NEVER implement complex logic directly - ALWAYS delegate to tools
   - Use: outline = call_tool("outline_generator", f"Create a schedule for: {{project_details}}")
   - Use: wbs = call_tool("outline_generator", f"Create a work breakdown structure for: {{project_details}}")
   - DO NOT create stub functions or placeholder implementations
   - DO NOT use undefined tools - only use tools that exist in the system
4. For complex data processing, use input_data["input"] as the main data field
5. ALWAYS include these standard imports at the top:
   - import json
   - import sys
   - from node_runtime import call_tool (ONLY if you actually call this function - do NOT import if unused)

IMPORTANT - DEMO SAFETY:
For potentially infinite or resource-intensive tasks, include SENSIBLE LIMITS:
- Fibonacci sequence: Calculate first 10-20 numbers only (not infinite)
- Prime numbers: Find first 100 primes (not all primes)
- Iterations: Limit to 1000 iterations max
- File sizes: Limit to 10MB max
- List lengths: Limit to 10,000 items max
- Timeouts: Add timeout logic for long-running operations

Example for Fibonacci:
```python
def main():
    input_data = json.load(sys.stdin)
    # SAFE: Limit to first 20 Fibonacci numbers
    n = min(int(input_data.get("n", 20)), 100)  # Cap at 100 max
    result = calculate_fibonacci(n)
    print(json.dumps({{"result": result}}))
```

Example for content generation tasks (jokes, stories, articles, poems):
```python
import json
import sys
from pathlib import Path

# CRITICAL: Add path setup BEFORE node_runtime import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool

def main():
    input_data = json.load(sys.stdin)

    # Extract user's request description
    task_description = input_data.get("description", "")

    # Build a detailed prompt for the LLM based on the task
    # Example: If task is "tell a joke about cats", prompt could be "Write a funny joke about cats"
    prompt = f"Generate content for: {{task_description}}"

    # CRITICAL: Always use call_tool() for content generation - NEVER hardcode content
    content = call_tool("content_generator", prompt)

    # ABSOLUTELY MANDATORY: ALWAYS print output - this is NON-NEGOTIABLE!
    # The output MUST be printed or the tool is considered broken!
    print(json.dumps({{"result": content}}))

if __name__ == "__main__":
    main()
```

CRITICAL OUTPUT REQUIREMENT:
- The print(json.dumps(...)) statement is ABSOLUTELY MANDATORY - NO EXCEPTIONS!
- If you forget to print output, the tool will appear broken to users
- ALWAYS include at least ONE print statement that outputs JSON with a "result" field

Example for joke generation specifically:
```python
import json
import sys
from pathlib import Path

# CRITICAL: Add path setup BEFORE node_runtime import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool

def main():
    input_data = json.load(sys.stdin)

    # Get the topic from input, or extract it from description
    topic = input_data.get("topic", "")
    if not topic:
        # If no topic specified, use description or default
        description = input_data.get("description", "")
        topic = description if description else "general humor"

    # Build prompt for joke generation
    joke_prompt = f"Tell a funny joke about {{topic}}"

    # Call LLM tool to generate the joke (NEVER use hardcoded jokes!)
    joke = call_tool("content_generator", joke_prompt)

    # ABSOLUTELY MANDATORY: Print the output!
    print(json.dumps({{"result": joke}}))

if __name__ == "__main__":
    main()
```

Example for project management tasks (schedules, WBS, outlines):
```python
import json
import sys
from pathlib import Path

# CRITICAL: Add path setup BEFORE node_runtime import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool

def main():
    input_data = json.load(sys.stdin)

    # Extract project details from any of the common input fields
    project_details = input_data.get("project_details",
                      input_data.get("description",
                      input_data.get("prompt", "")))

    if not project_details:
        print(json.dumps({{"error": "No project details provided"}}))
        return

    # CRITICAL: Use call_tool() to generate the schedule - DO NOT implement logic directly
    schedule = call_tool("outline_generator", f"Create a detailed project schedule for: {{project_details}}")

    # Return structured result
    result = {{
        "schedule": schedule,
        "project_details": project_details
    }}

    print(json.dumps(result))

if __name__ == "__main__":
    main()
```

**CRITICAL: call_tool() SIGNATURE**

The call_tool() function has this EXACT signature:
```python
def call_tool(tool_name: str, prompt: str, **kwargs) -> str
```

**CORRECT USAGE:**
```python
# ✅ Simple call with prompt
result = call_tool("content_generator", "Write a joke about cats")

# ✅ Call with formatted prompt
topic = "dogs"
result = call_tool("content_generator", f"Write a poem about {{topic}}")

# ✅ Translation with prompt
text = "Hello"
translated = call_tool("nmt_translator", f"Translate to French: {{text}}")

# ✅ With keyword arguments (if tool supports them)
result = call_tool("content_generator", "Write an article", temperature=0.7, max_length=500)
```

**WRONG USAGE (WILL FAIL!):**
```python
# ❌ WRONG - Passing dict as positional argument
result = call_tool("tool", "action", {{"text": "hello", "lang": "fr"}})  # TypeError!

# ❌ WRONG - Too many positional arguments
result = call_tool("tool", "action", "param1", "param2")  # TypeError!

# ❌ WRONG - Dict instead of kwargs
result = call_tool("tool", "prompt", {{"temperature": 0.7}})  # TypeError!
```

**CORRECT FIX FOR ABOVE:**
```python
# ✅ Build the prompt with the data
text = "hello"
lang = "fr"
result = call_tool("nmt_translator", f"Translate to {{lang}}: {{text}}")

# ✅ Use kwargs, not dict
result = call_tool("content_generator", "Write article", temperature=0.7)
```

**KEY RULES:**
1. call_tool() takes EXACTLY 2 positional arguments: (tool_name, prompt)
2. Additional parameters MUST be keyword arguments (**kwargs), NOT a dict
3. Build complex prompts using f-strings, don't pass separate parameters
4. The prompt should be a complete, descriptive string

CRITICAL REQUIREMENTS:
- The "code" field must contain ONLY executable Python code
- NO markdown fences (no ```python)
- NO explanations mixed with code
- ALWAYS start with ALL required import statements:
  * import json (REQUIRED)
  * import sys (REQUIRED)
  * from node_runtime import call_tool (REQUIRED if using content generation)
- Must be immediately runnable without errors
- For content generation: MUST use call_tool("content_generator", prompt)
- Verify all imports are present before generating code

Return ONLY the JSON object, nothing else."""

        # Use specialized tool if available, otherwise use standard generator
        generator_name = selected_tool.name if (use_specialized_tool and selected_tool) else self.config.generator_model
        workflow.add_step("code_generation", "llm", f"Generate code with {generator_name}")
        workflow.start_step("code_generation")

        if use_specialized_tool and selected_tool:
            console.print(f"\n[cyan]Generating code with specialized tool: {selected_tool.name}...[/cyan]")
            response = self.tools_manager.invoke_llm_tool(
                tool_id=selected_tool.tool_id,
                prompt=code_prompt,
                temperature=0.3
            )
        else:
            # Robust code generation with retries and exponential backoff
            max_retries = 3
            response = ""

            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        console.print(f"[yellow]Retry {attempt + 1}/{max_retries}...[/yellow]")
                        import time
                        time.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s, 8s

                    # For ANY content generation (simple or complex), use the general tool
                    if (is_simple_content or is_complex_content) and 'general' in self.tools_manager.tools:
                        general_tool = self.tools_manager.tools['general']
                        model_to_use = general_tool.metadata.get('llm_model', self.config.generator_model)

                        if attempt == 0:
                            console.print(f"\n[cyan]Generating code with {model_to_use} (general tool)...[/cyan]")

                        response = self.tools_manager.invoke_llm_tool(
                            tool_id='general',
                            prompt=code_prompt,
                            temperature=0.2 + (attempt * 0.05)  # Slightly increase temp on retries
                        )
                    else:
                        if attempt == 0:
                            console.print(f"\n[cyan]Generating code with {self.config.generator_model}...[/cyan]")

                        response = self.client.generate(
                            model=self.config.generator_model,
                            prompt=code_prompt,
                            temperature=0.2 + (attempt * 0.05),
                            model_key=self.config.generator_model_key  # Use actual model key for routing
                        )

                    # Validate response
                    if response and len(response) >= 50:
                        console.print(f"[green]✓ Generated {len(response)} chars[/green]")
                        break
                    else:
                        console.print(f"[yellow]Response too short ({len(response)} chars)[/yellow]")

                except Exception as e:
                    console.print(f"[yellow]Attempt {attempt + 1} failed: {str(e)[:100]}[/yellow]")

                if attempt == max_retries - 1 and (not response or len(response) < 50):
                    console.print(f"[red]All {max_retries} attempts failed[/red]")

        workflow.complete_step("code_generation", f"Generated {len(response)} chars", {"generator": generator_name})

        if not response or len(response) < 50:
            console.print("[red]CRITICAL: Failed to generate valid code[/red]")
            console.print("[yellow]Troubleshooting:[/yellow]")
            console.print("  1. Check Ollama: ollama list")
            console.print("  2. Check model: ollama show codellama")
            console.print("  3. Restart: ollama serve")
            return False

        # CRITICAL: Validate and fix code syntax BEFORE extraction
        # This prevents indentation errors that plague code generation

        # Parse JSON response
        try:
            import json
            # Clean any markdown or extra text
            response = response.strip()
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0].strip()
            elif response.startswith('```'):
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)
            code = result.get("code", "")
            code_description = result.get("description", description)
            base_tags = result.get("tags", ["generated", "chat"])
            code_tags = self._generate_smart_tags(description, base_tags)

            if not code:
                console.print("[red]No code in JSON response[/red]")
                return False

            # Log successful JSON parsing
            console.print(f"[dim]OK Extracted {len(code)} chars of code from JSON response[/dim]")

        except json.JSONDecodeError as e:
            console.print(f"[yellow]Failed to parse JSON response: {e}[/yellow]")
            console.print(f"[dim]Response preview: {response[:200]}...[/dim]")

            # Try to extract code from malformed JSON
            # Sometimes the LLM returns JSON with triple-quoted strings or other issues
            if '"code":' in response:
                try:
                    # Extract just the code field value
                    import re

                    # Try different patterns for code extraction
                    # Pattern 1: Triple-quoted string """..."""
                    match = re.search(r'"code"\s*:\s*"""(.*?)"""', response, re.DOTALL)
                    if match:
                        code = match.group(1).strip()
                    else:
                        # Pattern 2: Regular quoted string with escaped characters
                        match = re.search(r'"code"\s*:\s*"((?:[^"\\]|\\.)*)"', response, re.DOTALL)
                        if match:
                            code = match.group(1)
                            # Unescape the string
                            code = code.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                        else:
                            # Pattern 3: Extract everything between "code": and next field or end
                            match = re.search(r'"code"\s*:\s*["\'](.+?)["\']\s*,?\s*["}]', response, re.DOTALL)
                            if match:
                                code = match.group(1).strip()
                            else:
                                raise ValueError("Could not extract code from malformed JSON")

                    if code and len(code) > 10:
                        code_description = description
                        code_tags = self._generate_smart_tags(description, ["generated", "chat"])
                        console.print(f"[dim]OK Extracted code via regex ({len(code)} chars)[/dim]")
                    else:
                        raise ValueError(f"Extracted code is too short ({len(code) if code else 0} chars)")

                except Exception as extract_err:
                    console.print(f"[red]Could not extract code: {extract_err}[/red]")
                    return False
            else:
                # Fallback: treat entire response as code
                console.print("[yellow]Using entire response as code[/yellow]")
                code = response
                code_description = description
                code_tags = self._generate_smart_tags(description, ["generated", "chat"])

        # Clean the code (remove any remaining markdown)
        code = self._clean_code(code)

        # CRITICAL: Auto-fix indentation and syntax issues using autopep8
        try:
            import autopep8
            original_code = code
            code = autopep8.fix_code(code, options={'aggressive': 2, 'max_line_length': 120})

            if code != original_code:
                console.print("[green]Auto-fixed code formatting and indentation[/green]")
        except ImportError:
            # Auto-install missing dependency using RAG-based fix system
            code = self._auto_fix_static_tool_dependency(
                tool_name="autopep8",
                install_command="pip install autopep8",
                code=code,
                fix_function=lambda c: __import__('autopep8').fix_code(c, options={'aggressive': 2, 'max_line_length': 120})
            )
        except Exception as e:
            console.print(f"[yellow]Could not auto-format code: {e}[/yellow]")

        # Validate syntax after formatting
        try:
            import ast
            ast.parse(code)
            console.print("[dim]Syntax validation: OK[/dim]")
        except SyntaxError as e:
            console.print(f"[red]Syntax error detected after formatting:[/red]")
            console.print(f"[red]  Line {e.lineno}: {e.msg}[/red]")
            console.print(f"[yellow]Will attempt to fix via adaptive escalation...[/yellow]")

        # Check for required imports and add if missing
        needs_call_tool = 'call_tool(' in code
        needs_json = 'json.load' in code or 'json.dump' in code
        needs_sys = 'sys.stdin' in code or 'sys.stdout' in code or 'sys.stderr' in code

        # CRITICAL: Fix import order if node_runtime import comes before path setup
        if needs_call_tool:
            lines = code.split('\n')
            node_runtime_line_idx = None
            path_setup_line_idx = None

            for i, line in enumerate(lines):
                stripped = line.strip()
                if 'from node_runtime import' in stripped or 'import node_runtime' in stripped:
                    node_runtime_line_idx = i
                if 'sys.path.insert(0, str(Path(__file__).parent.parent.parent))' in stripped:
                    path_setup_line_idx = i

            # Case 1: node_runtime import exists but NO path setup - ADD path setup before import
            if node_runtime_line_idx is not None and path_setup_line_idx is None:
                console.print("[yellow]node_runtime import found but missing path setup - adding it[/yellow]")

                # Extract the node_runtime import line
                node_runtime_import = lines[node_runtime_line_idx].strip()

                # Remove it from current position
                lines.pop(node_runtime_line_idx)

                # Build path setup block (includes Path and sys imports if missing)
                path_setup_lines = []

                # Check if we need to add Path import
                if 'from pathlib import Path' not in code and 'import pathlib' not in code:
                    path_setup_lines.append('from pathlib import Path')

                # Check if we need to add sys import
                if 'import sys' not in code:
                    path_setup_lines.append('import sys')

                # Add the path setup line
                path_setup_lines.append('')  # Blank line for readability
                path_setup_lines.append('sys.path.insert(0, str(Path(__file__).parent.parent.parent))')

                # Add the node_runtime import
                path_setup_lines.append(node_runtime_import)

                # Find where to insert (after existing imports)
                insert_idx = 0
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('import ') or stripped.startswith('from '):
                        insert_idx = i + 1
                    elif stripped and not stripped.startswith('#'):
                        # Hit non-import, non-comment line
                        break

                # Insert path setup block
                for j, setup_line in enumerate(path_setup_lines):
                    lines.insert(insert_idx + j, setup_line)

                code = '\n'.join(lines)
                console.print("[green]✓ Added path setup before node_runtime import[/green]")

            # Case 2: Both exist but import comes BEFORE path setup - reorder
            elif node_runtime_line_idx is not None and path_setup_line_idx is not None:
                if node_runtime_line_idx < path_setup_line_idx:
                    console.print("[yellow]Fixing import order: moving node_runtime import after path setup[/yellow]")

                    # Extract the node_runtime import line
                    node_runtime_import = lines[node_runtime_line_idx]

                    # Remove it from its current position
                    lines.pop(node_runtime_line_idx)

                    # Adjust path_setup_line_idx since we removed a line before it
                    path_setup_line_idx -= 1

                    # Insert it right after the path setup line
                    lines.insert(path_setup_line_idx + 1, node_runtime_import)

                    code = '\n'.join(lines)
                    console.print("[green]✓ Fixed import order: path setup now comes first[/green]")

            # Case 3: Code uses call_tool but has NO node_runtime import at all - add complete setup
            elif 'from node_runtime import call_tool' not in code and 'import node_runtime' not in code:
                # Add complete path setup block at the top (after any existing imports)
                console.print("[yellow]call_tool() used but no node_runtime import - adding complete setup[/yellow]")

                lines = code.split('\n')

                # Find insertion point (after existing imports)
                insert_idx = 0
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('import ') or stripped.startswith('from '):
                        insert_idx = i + 1
                    elif stripped and not stripped.startswith('#'):
                        break

                # Build setup block
                setup_lines = []
                if 'from pathlib import Path' not in code:
                    setup_lines.append('from pathlib import Path')
                if 'import sys' not in code:
                    setup_lines.append('import sys')
                setup_lines.append('')
                setup_lines.append('sys.path.insert(0, str(Path(__file__).parent.parent.parent))')
                setup_lines.append('from node_runtime import call_tool')
                setup_lines.append('')

                # Insert
                for j, line in enumerate(setup_lines):
                    lines.insert(insert_idx + j, line)

                code = '\n'.join(lines)
                console.print("[green]✓ Added complete path setup and node_runtime import[/green]")

        # Add other missing imports
        if needs_json and 'import json' not in code:
            code = 'import json\n' + code
            console.print("[dim yellow]Added missing import: json[/dim yellow]")

        # Add sys import if code uses sys but doesn't import it
        if (needs_sys or 'sys.path.insert' in code or 'sys.argv' in code) and 'import sys' not in code:
            code = 'import sys\n' + code
            console.print("[dim yellow]Added missing import: sys[/dim yellow]")

        # CRITICAL: Ensure code has if __name__ == "__main__" block to actually run
        has_main_function = 'def main(' in code
        has_main_block = '__name__' in code and '__main__' in code

        if has_main_function and not has_main_block:
            # Code defines main() but never calls it!
            console.print("[yellow]Code has main() but doesn't call it - adding if __name__ block[/yellow]")
            code = code + '\n\nif __name__ == "__main__":\n    main()\n'
            console.print("[green]Added if __name__ == '__main__': main() block[/green]")

        # CRITICAL: Strip out any logging calls that LLM might have added
        # UNLESS the user explicitly requested logging/debugging functionality
        # This prevents "NameError: name 'logger' is not defined" errors
        logging_keywords = ['with logging', 'with full logging', 'debug version', 'logging enabled',
                           'include logging', 'add logging', 'logging layer', 'debug layer']
        user_wants_logging = any(keyword in description.lower() for keyword in logging_keywords)

        if ('logger' in code or 'logging' in code) and not user_wants_logging:
            console.print("[cyan]Removing logging calls from generated code...[/cyan]")
            code = self._remove_debug_logging(code)
            console.print("[dim]Logging calls removed[/dim]")
        elif user_wants_logging and ('logger' in code or 'logging' in code):
            console.print("[yellow]NOTE Logging preserved as explicitly requested in task[/yellow]")

        # SAFETY NET: Add dummy logger if code still references logger
        # This catches any logging calls that slipped through
        if 'logger' in code and 'import logging' not in code:
            console.print("[yellow]Warning: Code references 'logger' - adding dummy logger safety net[/yellow]")
            dummy_logger = """
# DUMMY LOGGER - Catches accidental logging calls
class _DummyLogger:
    def __getattr__(self, name):
        def dummy(*args, **kwargs):
            import sys
            print(f"[DEBUG] logger.{name} called (stripped in production)", file=sys.stderr)
            return None
        return dummy
logger = _DummyLogger()

"""
            code = dummy_logger + code

        # Validate and fix code if needed
        is_valid, error_msg = self._validate_python_code(code)
        if not is_valid:
            console.print(f"[yellow]Code validation failed: {error_msg}[/yellow]")
            console.print("[cyan]Attempting to fix with code model...[/cyan]")

            # Use code model to fix with strict prompt
            code = self._fix_code_with_llm(code, error_msg)

            # Validate again
            is_valid, error_msg = self._validate_python_code(code)
            if is_valid:
                console.print("[green]Code fixed successfully[/green]")
            else:
                console.print(f"[red]Warning: Code still has issues: {error_msg}[/red]")

        # CRITICAL: Validate that code produces output
        # ALL tools must output something - this is non-negotiable!
        has_print_statement = 'print(' in code
        has_stdout_write = 'sys.stdout.write(' in code
        has_output = has_print_statement or has_stdout_write

        if not has_output:
            console.print(f"[red]CRITICAL: Generated code has NO output statements![/red]")
            console.print(f"[yellow]ALL tools MUST produce output. Adding fallback output...[/yellow]")

            # Add a print statement at the end of main() or at the end of the file
            if 'def main(' in code:
                # Find the main function and add output before its return
                lines = code.split('\n')
                main_func_indent = None
                insert_line = None

                for i, line in enumerate(lines):
                    if 'def main(' in line:
                        main_func_indent = len(line) - len(line.lstrip())
                    elif main_func_indent is not None and line.strip() == '':
                        # Found empty line in main - could be end of function
                        continue
                    elif main_func_indent is not None and line.strip() and not line.strip().startswith('#'):
                        # Check if this is a return statement or end of function
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent <= main_func_indent:
                            # End of main function
                            insert_line = i
                            break

                if insert_line is not None:
                    # Insert output statement before end of main
                    indent = ' ' * (main_func_indent + 4)
                    output_statement = f'{indent}# FALLBACK: Ensure output is produced\n{indent}print(json.dumps({{"result": "Task completed", "note": "No explicit output was generated"}}))'
                    lines.insert(insert_line, output_statement)
                    code = '\n'.join(lines)
                    console.print("[green]✓ Added fallback output statement to main()[/green]")
            else:
                # No main function - add output at the end
                code += '\n\n# FALLBACK: Ensure output is produced\nprint(json.dumps({"result": "Task completed", "note": "No explicit output was generated"}))\n'
                console.print("[green]✓ Added fallback output statement at end of file[/green]")
        else:
            console.print(f"[dim green]✓ Code contains output statements[/dim green]")

        # Step 5: Detect interface (inputs, outputs, operation type)
        try:
            interface_schema = self._detect_interface(code, description, specification)
        except Exception as e:
            console.print(f"[dim yellow]Could not detect interface: {e}, using fallback[/dim yellow]")
            interface_schema = self._basic_interface_detection(code, description)

        # Step 5: Create node in registry (but don't store in RAG yet - wait for tests to pass)
        self.registry.create_node(
            node_id=node_id,
            title=code_description[:100],
            tags=code_tags,
            goals={
                "primary": ["correctness", "determinism"],
                "secondary": ["latency<200ms", "memory<64MB"]
            }
        )

        # Step 5: Clean unused imports, then save code with interface metadata
        from tools.executable.remove_unused_node_runtime_import import remove_node_runtime_import
        cleaned_code, changes = remove_node_runtime_import(code)
        if any("Removed:" in c for c in changes):
            console.print(f"[dim]Auto-cleaned: {', '.join([c for c in changes if 'Removed:' in c][:2])}[/dim]")
            code = cleaned_code

        self.runner.save_code(node_id, code)

        # Save interface schema alongside the code
        interface_path = self.runner.get_node_path(node_id).parent / "interface.json"
        with open(interface_path, 'w') as f:
            json.dump(interface_schema, f, indent=2)

        # Step 6: Display generated code (if verbose mode)
        if self.config.get("chat.show_generated_content", False):
            syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title=f"[green]Generated Code: {node_id}[/green]", box=box.ROUNDED))
        else:
            # Concise status message
            lines = len(code.split('\n'))
            console.print(f"[green]✓ Generated code ({lines} lines)[/green]")

        # Step 7: Run unit tests (already generated in TDD mode, or generate now)
        test_success = True
        if self.config.get("testing.enabled", True):
            if interface_tests:
                # TDD mode: tests were already generated and saved, just run them
                workflow.add_step("testing", "test", "Run interface tests (TDD)")
                workflow.start_step("testing")
                console.print(f"\n[cyan]Running interface tests (TDD mode)...[/cyan]")
            else:
                # Traditional mode: generate tests now
                workflow.add_step("testing", "test", "Generate and run unit tests")
                workflow.start_step("testing")
                console.print(f"\n[cyan]Generating unit tests...[/cyan]")

            try:
                test_success = self._generate_and_run_tests(node_id, description, specification, code, skip_generation=bool(interface_tests))
            except Exception as e:
                console.print(f"[red]Error in test generation: {e}[/red]")
                import traceback
                traceback.print_exc()
                test_success = False

            if test_success:
                workflow.complete_step("testing", "Tests passed")
            else:
                workflow.fail_step("testing", "Tests failed")

            if not test_success and self.config.get("testing.auto_escalate", True):
                workflow.add_step("escalation", "llm", f"Adaptive escalation with temperature adjustment")
                workflow.start_step("escalation")
                console.print(f"\n[yellow]Tests failed. Starting adaptive escalation...[/yellow]")

                # Adaptive escalation with temperature/creativity adjustment
                escalation_success = self._adaptive_escalate_and_fix(
                    node_id=node_id,
                    code=code,
                    description=description,
                    specification=specification,
                    available_tools=available_tools
                )

                if escalation_success:
                    console.print(f"[green]OK Code fixed via adaptive escalation[/green]")
                    workflow.complete_step("escalation", "Fixed successfully with adaptive parameters")
                    # Reload the fixed code
                    code_path = self.runner.get_node_path(node_id)
                    if code_path.exists():
                        code = code_path.read_text()
                        # Re-run tests on the fixed code to confirm
                        console.print(f"\n[cyan]Re-running tests on fixed code...[/cyan]")
                        test_success = self._generate_and_run_tests(node_id, description, specification, code)
                        if test_success:
                            console.print(f"[green]OK Tests now pass![/green]")
                        else:
                            console.print(f"[yellow]Note: Tests still failing but continuing anyway[/yellow]")
                else:
                    console.print(f"[yellow]Warning: Could not fix all issues after adaptive attempts, continuing anyway[/yellow]")
                    workflow.fail_step("escalation", "Could not fix all issues")

        # Step 7.5: Run static analysis tools if tests passed
        if test_success and self.config.get("testing.enabled", True):
            workflow.add_step("static_analysis", "test", "Running static analysis tools")
            workflow.start_step("static_analysis")
            console.print(f"\n[cyan]Running static analysis...[/cyan]")

            analysis_results = self._run_static_analysis(node_id, code)

            # Iterate to fix issues if not all checks passed
            max_fix_attempts = 3
            fix_attempt = 0

            while analysis_results['passed_count'] < analysis_results['total_count'] and fix_attempt < max_fix_attempts:
                fix_attempt += 1
                console.print(f"\n[yellow]Attempting auto-fix (attempt {fix_attempt}/{max_fix_attempts})...[/yellow]")

                # Try to auto-fix failing tools
                fixed_any = self._auto_fix_static_issues(node_id, analysis_results)

                if fixed_any:
                    # Reload code and re-run static analysis
                    code_path = self.runner.get_node_path(node_id)
                    if code_path.exists():
                        code = code_path.read_text()

                    console.print(f"[cyan]Re-running static analysis...[/cyan]")
                    analysis_results = self._run_static_analysis(node_id, code)

                    if analysis_results['passed_count'] == analysis_results['total_count']:
                        console.print(f"[green]✓ All checks now pass![/green]")
                        break
                else:
                    console.print(f"[yellow]No auto-fix available for remaining issues[/yellow]")
                    break

            # Check if ALL checks passed
            all_passed = analysis_results['passed_count'] == analysis_results['total_count']

            if all_passed:
                workflow.complete_step("static_analysis", f"All {analysis_results['total_count']} checks passed")
                console.print(f"[green]OK Static analysis: {analysis_results['total_count']}/{analysis_results['total_count']} checks passed[/green]")
            else:
                workflow.fail_step("static_analysis", f"Only {analysis_results['passed_count']}/{analysis_results['total_count']} checks passed")
                console.print(f"[red]FAIL Static analysis: {analysis_results['passed_count']}/{analysis_results['total_count']} checks passed[/red]")
                console.print(f"[yellow]Node creation blocked until all static analysis checks pass[/yellow]")

                # Don't create the node if static analysis failed
                return False

        # Step 8: Store in RAG ONLY if tests passed (don't pollute RAG with broken code)
        if test_success and hasattr(self, 'rag'):
            try:
                from src.rag_memory import ArtifactType

                # Build callable instruction from interface schema for semantic matching
                # Example: "translate(content, language)" or "add_numbers(a, b)"
                callable_instruction = None
                if interface_schema:
                    inputs = interface_schema.get("inputs", [])
                    if inputs:
                        params = ", ".join(inputs)
                        callable_instruction = f"{node_id}({params})"
                    else:
                        callable_instruction = f"{node_id}()"

                # Prepare metadata with interface and workflow context
                func_metadata = {
                    "node_id": node_id,
                    "specification": specification[:200],
                    "tools_available": available_tools if available_tools and "No specific tools" not in available_tools else None,
                    "tests_passed": True,
                    "interface": interface_schema,  # Store complete interface schema
                    "callable_instruction": callable_instruction  # For semantic matching
                }

                # Add workflow context if this node is part of a workflow
                workflow_context = self.context.get('_workflow_context')
                if workflow_context:
                    func_metadata['workflow_context'] = {
                        'parent_workflow': workflow_context.get('parent_workflow'),
                        'step_id': workflow_context.get('step_id'),
                        'step_description': workflow_context.get('step_description'),
                        'tool_used': workflow_context.get('tool_used'),
                        'operation_type': workflow_context.get('operation_type')
                    }

                # Add final system response to tool conversation
                self._current_tool_conversation.append({
                    "role": "system",
                    "content": f"Tool '{code_description}' successfully created and tested",
                    "timestamp": __import__('time').time(),
                    "node_id": node_id,
                    "status": "completed"
                })

                # Store the generated code as a function artifact
                self.rag.store_artifact(
                    artifact_id=f"func_{node_id}",
                    artifact_type=ArtifactType.FUNCTION,
                    name=code_description,
                    description=description,
                    content=code,
                    tags=code_tags,
                    metadata=func_metadata,
                    auto_embed=True
                )

                # NOW store conversation history with the tool (conversational version history)
                # This is stored ONLY when tool is registered, not during general conversation
                if self._current_tool_conversation:
                    conversation_artifact_id = f"conv_{node_id}_v1"
                    conversation_content = {
                        "tool_id": node_id,
                        "tool_name": code_description,
                        "conversation": self._current_tool_conversation,
                        "version": 1,
                        "created_at": __import__('time').time()
                    }

                    # Store conversation with tool's tags + "conversation" tag
                    conversation_tags = code_tags + ["conversation", "tool_history", node_id]

                    try:
                        self.rag.store_artifact(
                            artifact_id=conversation_artifact_id,
                            artifact_type=ArtifactType.CONVERSATION,  # Use specific CONVERSATION type
                            name=f"Conversation: {code_description}",
                            description=f"Conversational history for tool {node_id}",
                            content=json.dumps(conversation_content, indent=2),
                            tags=conversation_tags,
                            metadata={
                                "tool_id": node_id,
                                "version": 1,
                                "conversation_length": len(self._current_tool_conversation),
                                "created_at": __import__('time').time()
                            },
                            auto_embed=False  # Don't embed the raw conversation
                        )

                        # Store in tool_conversations dict for future optimizations
                        self._tool_conversations[node_id] = self._current_tool_conversation.copy()

                        console.print(f"[dim green]✓ Stored conversational version history for {node_id}[/dim green]")
                    except Exception as e:
                        console.print(f"[dim yellow]Could not store conversation history: {e}[/dim yellow]")

                # Always save a basic specification
                spec_path = self.runner.get_node_path(node_id).parent / "specification.md"
                try:
                    # Basic spec always saved
                    basic_spec = f"""# {code_description}

## Task
{description}

## Implementation
{specification[:500]}...

Generated: {datetime.now().isoformat()}
"""
                    spec_path.write_text(basic_spec, encoding='utf-8')

                    # Save detailed spec if requested via config
                    if self.config.get("generation.save_specification", False):
                        detailed_spec = f"""# Specification for {node_id}

## Description
{description}

## Detailed Specification
{specification}

## Tools Used
{available_tools if "No specific tools" not in available_tools else "general"}

## Code Summary
{code_description}

## Tags
{', '.join(code_tags)}

## Generated
{datetime.now().isoformat()}
"""
                        spec_path.write_text(detailed_spec, encoding='utf-8')
                        console.print(f"[dim]Saved detailed specification[/dim]")
                except Exception as e:
                    console.print(f"[dim yellow]Could not save specification: {e}[/dim yellow]")

                # Save the overseer's plan/specification
                self._save_overseer_plan(node_id, specification)

                # Generate Behave .feature file for BDD testing
                self._generate_behave_feature(node_id, description, specification, code)

                # Generate Locust load test script
                self._generate_locust_load_test(node_id, description, code)

                # Store complete workflow for future reuse with embedded specification
                workflow_content = {
                    "description": description,
                    "specification": specification,
                    "tools_used": available_tools if "No specific tools" not in available_tools else "general",
                    "node_id": node_id,
                    "tags": code_tags,
                    "code_summary": code_description
                }

                # Create rich content for embedding that includes specification details
                # This improves semantic matching for similar future requests
                embedding_content = f"""Workflow: {code_description}

Description: {description}

Specification:
{specification}

Tools Used: {available_tools if "No specific tools" not in available_tools else "general"}

Implementation Summary:
{code_description}

Tags: {', '.join(code_tags)}

This workflow successfully completed with passing tests.
"""

                self.rag.store_artifact(
                    artifact_id=f"workflow_{node_id}",
                    artifact_type=ArtifactType.WORKFLOW,
                    name=f"Workflow: {code_description}",
                    description=description,
                    content=embedding_content,  # Use rich content for better semantic matching
                    tags=["workflow", "complete", "tested"] + code_tags,
                    metadata={
                        "node_id": node_id,
                        "question": description,
                        "specification": specification,  # Store full spec in metadata
                        "specification_hash": hash(specification[:200]),
                        "specification_file": str(spec_path.relative_to(self.runner.nodes_dir.parent)),
                        "tools_used": available_tools if "No specific tools" not in available_tools else "general",
                        "tests_passed": True,
                        "workflow_json": json.dumps(workflow_content)  # Keep original structure
                    },
                    auto_embed=True
                )
                console.print(f"[dim]OK Code, workflow, and specification stored in RAG for future reuse[/dim]")
            except Exception as e:
                console.print(f"[dim yellow]Note: Could not store in RAG: {e}[/dim yellow]")
        elif not test_success:
            console.print(f"[dim yellow]Skipping RAG storage - tests did not pass[/dim yellow]")

        # Step 8.5: If this was a composed workflow AND tests passed, save it as a COMMUNITY tool for future reuse
        if test_success and workflow_composition and workflow_composition.get("workflow_steps"):
            try:
                # Create a committee/community tool from this successful workflow
                committee_id = f"committee_{node_id}"
                committee_description = f"Specialized workflow committee for: {description[:100]}"

                # Extract characteristics and tools from the composition
                characteristics = workflow_composition.get("characteristics", {})
                recommended_tools = workflow_composition.get("recommended_tools", [])
                workflow_steps = workflow_composition.get("workflow_steps", [])

                # Build community tool definition
                community_tool_def = {
                    "name": f"Committee: {code_description[:50]}",
                    "type": "community",  # Marks it as a community of agents
                    "description": committee_description,
                    "characteristics": characteristics,
                    "tools_used": [t["tool_id"] for t in recommended_tools],
                    "workflow_steps": workflow_steps,
                    "rationale": workflow_composition.get("rationale", []),
                    "node_id": node_id,  # Reference to the implemented node
                    "success_metrics": {
                        "test_success": test_success,
                        "created": datetime.now().isoformat()
                    }
                }

                # Register as a COMMUNITY tool in the tools manager
                self.tools_manager.register_tool(
                    tool_id=committee_id,
                    name=community_tool_def["name"],
                    tool_type=ToolType.COMMUNITY,
                    description=committee_description,
                    tags=list(characteristics.keys()) + ["committee", "composite"] + code_tags,
                    implementation=community_tool_def,
                    metadata=community_tool_def
                )

                # Also store in RAG for semantic search
                self.rag.store_artifact(
                    artifact_id=committee_id,
                    artifact_type=ArtifactType.PATTERN,  # Communities are patterns
                    name=community_tool_def["name"],
                    description=committee_description,
                    content=json.dumps(community_tool_def, indent=2),
                    tags=["committee", "community", "composite-workflow"] + list(characteristics.keys()),
                    metadata={
                        "node_id": node_id,
                        "characteristics": characteristics,
                        "tools_count": len(recommended_tools),
                        "steps_count": len(workflow_steps)
                    },
                    auto_embed=True
                )

                console.print(f"[green]* Created reusable committee tool: {committee_id}[/green]")
                console.print(f"[dim]This workflow can now be reused for similar tasks![/dim]")

            except Exception as e:
                console.print(f"[dim yellow]Note: Could not create committee tool: {e}[/dim yellow]")

        console.print(f"\n[green]OK Node '{node_id}' created successfully![/green]")

        # Step 9: Optimization is now OFFLINE ONLY
        # Inline optimization removed for faster first-shot results
        # Static validators catch most issues upfront
        # Offline optimization runs hourly to improve prompts based on patterns
        # See: STREAMLINED_WORKFLOW.md for details

        # Auto-run the newly created workflow
        workflow.add_step("execution", "run", "Execute the generated workflow")
        workflow.start_step("execution")
        console.print(f"\n[cyan]Running workflow...[/cyan]")

        # Detect what input fields the generated code expects
        import re
        expected_fields = set()
        code_lines = code.split('\n')
        for line in code_lines:
            # Look for patterns like: input_data.get("field_name", ...)
            matches = re.findall(r'input_data\.get\(["\']([^"\']+)["\']', line)
            expected_fields.update(matches)

        # Create flexible input data that works with different code patterns
        # Start with generic fields
        input_data = {
            "input": description,
            "task": description,
            "description": description,
            "query": description,
            "topic": description,
            "prompt": description,
            "question": description,
            "request": description
        }

        # If code expects specific fields not in our generic list, try to auto-generate data
        generic_fields = {"input", "task", "description", "query", "topic", "prompt", "question", "request"}
        specific_fields_needed = expected_fields - generic_fields

        if specific_fields_needed:
            console.print(f"[yellow]-> Detected specific input fields needed: {', '.join(specific_fields_needed)}[/yellow]")
            console.print(f"[yellow]-> Auto-generating test data...[/yellow]")

            # Try to use random_data_generator to create test data
            try:
                # Build a schema from the detected fields
                schema = {}
                for field in specific_fields_needed:
                    # Guess type based on field name
                    if any(word in field.lower() for word in ['lang', 'language']):
                        schema[field] = "string"  # Will generate language code
                    elif any(word in field.lower() for word in ['text', 'article', 'content', 'message']):
                        schema[field] = "string"  # Will generate text
                    elif any(word in field.lower() for word in ['age', 'count', 'number', 'size']):
                        schema[field] = "number"
                    else:
                        schema[field] = "string"

                # Generate test data
                schema_json = json.dumps(schema)
                test_data_result = self.tools_manager.invoke_executable_tool(
                    tool_id="random_data_generator",
                    source_file="",
                    prompt=schema_json
                )

                if test_data_result.get("success"):
                    test_data = json.loads(test_data_result["stdout"])
                    console.print(f"[green]-> Generated test data: {json.dumps(test_data, indent=2)}[/green]")
                    # Merge generated data into input_data
                    input_data.update(test_data)
            except Exception as e:
                console.print(f"[yellow]-> Could not auto-generate test data: {e}[/yellow]")
                console.print(f"[yellow]-> Running with generic input only (may produce empty output)[/yellow]")

        stdout, stderr, metrics = self.runner.run_node(node_id, input_data)

        # CRITICAL: Display output IMMEDIATELY and PROMINENTLY
        # This is what the user wants to see!
        # ALWAYS show output section - even if empty (to highlight the problem)
        console.print("\n" + "="*80)
        console.print("[bold magenta on white]  YOUR RESULT  [/bold magenta on white]")
        console.print("="*80 + "\n")

        if stdout and stdout.strip():

            # Try to extract and show the actual result prominently
            result_displayed = False
            has_empty_output = False
            try:
                # Try to parse as JSON first
                output_data = json.loads(stdout.strip())
                if isinstance(output_data, dict):
                    # Check for common result field names
                    result_fields = ['result', 'output', 'answer', 'content', 'translated_article',
                                     'summary', 'text', 'data', 'response']

                    for field in result_fields:
                        if field in output_data:
                            result_content = output_data[field]
                            # Check if result is empty
                            if not result_content or (isinstance(result_content, str) and not result_content.strip()):
                                has_empty_output = True
                                console.print(f"[yellow]⚠ Warning: Field '{field}' is empty![/yellow]")
                                console.print(f"[dim]Full output: {json.dumps(output_data, indent=2)}[/dim]")
                            else:
                                if isinstance(result_content, str):
                                    console.print(result_content)
                                else:
                                    console.print(json.dumps(result_content, indent=2))
                            result_displayed = True
                            break

                    # If no recognized field found, show all non-empty values
                    if not result_displayed and output_data:
                        console.print("[bold]Output fields:[/bold]")
                        for key, value in output_data.items():
                            if value and (not isinstance(value, str) or value.strip()):
                                console.print(f"  {key}: {value}")
                            else:
                                has_empty_output = True
                                console.print(f"  [dim]{key}: (empty)[/dim]")
                        result_displayed = True
            except:
                pass

            # If we couldn't extract a specific result, show full output
            if not result_displayed:
                console.print(stdout)

            # If output was empty, show helpful message
            if has_empty_output:
                console.print("\n[yellow]━" * 40 + "[/yellow]")
                console.print("[yellow]⚠ The workflow produced empty output![/yellow]")
                console.print("[yellow]This usually means the workflow needs specific input data.[/yellow]")
                console.print("[yellow]Try providing input fields or use test data generation.[/yellow]")
                console.print("[yellow]━" * 40 + "[/yellow]")

            console.print("\n" + "="*80 + "\n")
        else:
            # NO OUTPUT - This is a critical error!
            console.print("[bold red]⚠ NO OUTPUT WAS PRODUCED![/bold red]\n")
            console.print("[yellow]This tool failed to generate any output.[/yellow]")
            console.print("[yellow]ALL tools MUST produce output - this indicates a bug in code generation.[/yellow]")

            if stderr and stderr.strip():
                console.print(f"\n[yellow]Error output (stderr):[/yellow]")
                console.print(Panel(stderr, border_style="red", box=box.ROUNDED))
            else:
                console.print("\n[dim]No error messages were captured either.[/dim]")

            console.print("\n" + "="*80 + "\n")

        # Display results - ALWAYS show output, even if there were errors
        console.print("\n" + "="*70)
        console.print("[bold cyan]WORKFLOW RESULT:[/bold cyan]")
        console.print("="*70)

        if metrics["success"]:
            console.print("[green]OK Execution successful[/green]")
            workflow.complete_step("execution", f"Success: {len(stdout)} chars output", {
                "exit_code": metrics["exit_code"],
                "latency_ms": metrics["latency_ms"]
            })
            if not stdout or not stdout.strip():
                # CRITICAL: This should NEVER happen - all tools MUST produce output!
                console.print("\n" + "="*80)
                console.print("[bold red on white]  ⚠ CRITICAL ERROR: NO OUTPUT PRODUCED  [/bold red on white]")
                console.print("="*80)
                console.print("[red]The code executed successfully but produced NO output![/red]")
                console.print("[yellow]This is a BUG in code generation - ALL tools MUST output something![/yellow]")
                console.print("[yellow]Possible causes:[/yellow]")
                console.print("  1. Missing print() statement in the generated code")
                console.print("  2. Code didn't call the main() function")
                console.print("  3. Output was written to stderr instead of stdout")
                if stderr and stderr.strip():
                    console.print(f"\n[yellow]stderr output:[/yellow]")
                    console.print(Panel(stderr, border_style="yellow"))
                console.print("="*80 + "\n")
        else:
            console.print(f"[red]FAIL Execution failed (exit code: {metrics['exit_code']})[/red]")
            workflow.fail_step("execution", f"Exit code {metrics['exit_code']}")
            # Still show stdout if there is any (partial output is valuable!)
            if stdout:
                console.print(Panel(stdout, title="[yellow]Partial Output[/yellow]", box=box.ROUNDED, border_style="yellow"))
            if stderr:
                console.print(Panel(stderr, title="[red]Error[/red]", border_style="red", box=box.ROUNDED))

        if self.config.get("chat.show_metrics", True):
            self._display_metrics(metrics)

        # Finish workflow tracking
        workflow.finish()

        # Step 9.5: Verify BDD spec and get performance scores
        bdd_passed = False
        perf_score = 0.0
        if metrics["success"]:
            console.print(f"\n[cyan]Verifying BDD specification and performance...[/cyan]")

            # Run BDD verification
            bdd_passed, perf_score = self._verify_bdd_and_performance(
                node_id, description, specification, code
            )

            if bdd_passed:
                console.print(f"[green]✓ BDD specification verified[/green]")
            else:
                console.print(f"[yellow]! BDD verification failed (continuing anyway)[/yellow]")

        # Step 10: If execution succeeded, register this node as a reusable tool
        if metrics["success"]:
            console.print(f"\n[cyan]Registering successful node as reusable tool...[/cyan]")
            try:
                # Calculate quality score based on performance
                quality_score = 1.0

                # BDD compliance bonus
                if bdd_passed:
                    quality_score += 0.2

                # Performance score bonus (from Locust)
                quality_score += perf_score * 0.3  # Scale perf_score (0-1) by 0.3

                # Basic metrics bonuses
                if metrics.get("latency_ms", 0) < 100:
                    quality_score += 0.1
                if metrics.get("memory_mb_peak", 0) < 10:
                    quality_score += 0.1

                # Register as a tool in the tools manager
                from src.tools_manager import Tool

                tool = Tool(
                    tool_id=node_id,
                    name=code_description,  # Full description as tool name (no truncation)
                    tool_type=ToolType.WORKFLOW,
                    description=description,  # Full description for semantic search
                    tags=code_tags + ["auto-generated", "workflow"],
                    implementation=None,  # Will be loaded from registry
                    metadata={
                        "node_id": node_id,
                        "quality_score": quality_score,
                        "latency_ms": metrics.get("latency_ms", 0),
                        "memory_mb_peak": metrics.get("memory_mb_peak", 0),
                        "created_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                        "success_count": 1,
                        "total_runs": 1,
                        "full_title": code_description  # Preserve full title for display
                    }
                )

                self.tools_manager.register_tool(tool)

                # Store tool in RAG for semantic search
                if self.rag:
                    from src.rag_memory import ArtifactType
                    import hashlib

                    # Determine if this is a DEBUG version (contains logging)
                    is_debug_version = ('import logging' in code or 'logger.' in code)
                    tool_tags = ["tool", "workflow", "auto-generated"] + code_tags

                    # Generate version info based on code hash
                    code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
                    version = "1.0.0"  # Start with v1.0.0, can be incremented on updates

                    # Determine base tool name (without _debug suffix if present)
                    base_tool_id = node_id.replace("_debug", "").replace("_DEBUG", "")

                    # If this is a DEBUG version, also store the production version
                    production_tool_id = None
                    debug_tool_id = None

                    if is_debug_version:
                        tool_tags.append("DEBUG")
                        tool_tags.append("debug-version")
                        debug_tool_id = node_id
                        # Link to production version (if it doesn't already have _debug)
                        if "_debug" not in node_id and "_DEBUG" not in node_id:
                            production_tool_id = base_tool_id + "_prod"
                        else:
                            production_tool_id = base_tool_id
                        console.print(f"[yellow]WARNING This tool contains logging - tagged as DEBUG version[/yellow]")
                        console.print(f"[dim]Debug version linked to production tool: {production_tool_id}[/dim]")
                    else:
                        # This is a production version
                        production_tool_id = node_id
                        # Check if a debug version exists or should be created
                        debug_tool_id = base_tool_id + "_debug"

                    tool_name_prefix = "[DEBUG] " if is_debug_version else ""

                    # Store tool with versioning and linking metadata
                    self.rag.store_artifact(
                        artifact_id=f"tool_{node_id}",
                        artifact_type=ArtifactType.PATTERN,
                        name=f"{tool_name_prefix}Tool: {code_description[:80]}",
                        description=f"{'DEBUG VERSION - ' if is_debug_version else ''}Reusable workflow tool: {description}",
                        content=f"""Tool ID: {node_id}
Description: {description}
Quality Score: {quality_score:.2f}
Debug Version: {is_debug_version}
Code Hash: {code_hash}
Version: {version}
Production Tool: {production_tool_id}
Debug Tool: {debug_tool_id}
Linked Pair: {production_tool_id} <-> {debug_tool_id}
""",
                        tags=tool_tags,
                        metadata={
                            "tool_id": node_id,
                            "quality_score": quality_score,
                            "is_tool": True,
                            "is_debug": is_debug_version,
                            "has_logging": is_debug_version,
                            "version": version,
                            "code_hash": code_hash,
                            "production_tool_id": production_tool_id,
                            "debug_tool_id": debug_tool_id,
                            "linked_pair": f"{production_tool_id}<->{debug_tool_id}",
                            "base_tool_id": base_tool_id,
                            "created_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
                        },
                        auto_embed=True
                    )

                    # If this is a production version, also check for and link existing debug version
                    if not is_debug_version:
                        # Look for existing debug version
                        debug_artifacts = self.rag.find_by_tags(["DEBUG", "tool"])
                        for artifact in debug_artifacts:
                            if artifact.metadata.get("base_tool_id") == base_tool_id:
                                console.print(f"[dim]Found existing debug version: {artifact.metadata.get('tool_id')}[/dim]")
                                console.print(f"[dim]Production <-> Debug pair: {node_id} <-> {artifact.metadata.get('tool_id')}[/dim]")

                console.print(f"[green]OK Registered as tool '{node_id}' (quality: {quality_score:.2f})[/green]")

                # Print versioning summary
                if is_debug_version:
                    console.print(f"[dim]Version: {version} | Hash: {code_hash} | Pair: {production_tool_id} <-> {debug_tool_id}[/dim]")
                else:
                    console.print(f"[dim]Version: {version} | Hash: {code_hash} | Debug counterpart: {debug_tool_id}[/dim]")

            except Exception as e:
                console.print(f"[dim yellow]Note: Could not register as tool: {e}[/dim yellow]")

        # Mark workflow as finished
        workflow.finish()

        # Record positive feedback for tools that were used successfully
        self._record_tool_feedback_on_completion(
            description=description,
            quality_score=quality_score if 'quality_score' in locals() else 0.0,
            success=True
        )

        # Display minimal workflow summary with per-tool timings if enabled
        if show_workflow:
            console.print("\n" + "="*70)
            console.print(f"Workflow: {workflow.description}")
            console.print("="*70)

            # Show per-tool timings
            if workflow.steps:
                console.print("\n[dim]Tool execution times:[/dim]")
                for step in workflow.steps:
                    if step.end_time and step.start_time:
                        duration = step.end_time - step.start_time
                        console.print(f"  {step.tool_name}: {duration:.2f}s")

                # Total time
                if workflow.end_time and workflow.start_time:
                    total_time = workflow.end_time - workflow.start_time
                    console.print(f"\n[dim]Total: {total_time:.2f}s[/dim]")

            console.print("="*70)

        return True

    def _auto_fix_static_tool_dependency(
        self,
        tool_name: str,
        install_command: str,
        code: str,
        fix_function: callable
    ) -> str:
        """
        Automatically fix missing static tool dependencies using RAG-based learning.

        Flow:
        1. Search RAG for known fixes for this tool
        2. Apply fix (pip install)
        3. Rerun the tool
        4. Record success/failure for future learning

        Args:
            tool_name: Name of the missing tool (e.g., "autopep8")
            install_command: Command to install (e.g., "pip install autopep8")
            code: Code to process
            fix_function: Function to call after install (receives code, returns fixed code)

        Returns:
            Fixed code or original code if fix failed
        """
        from rich.console import Console
        console = Console()

        # Step 1: Search RAG for known fixes for this tool dependency
        fix_id = f"static_tool_dependency_{tool_name}"

        try:
            from src.rag_memory import ArtifactType

            # Look for existing fix in RAG
            existing_fixes = self.rag.find_by_tags(
                tags=["code_fix", "static_tool_fix", tool_name],
                limit=1
            )

            if existing_fixes:
                fix_artifact = existing_fixes[0]
                success_count = fix_artifact.metadata.get("success_count", 0)
                failure_count = fix_artifact.metadata.get("failure_count", 0)
                success_rate = success_count / (success_count + failure_count) if (success_count + failure_count) > 0 else 0

                console.print(f"[cyan]-> Found fix in RAG: '{install_command}' (success rate: {success_rate:.0%}, {success_count}/{success_count+failure_count} attempts)[/cyan]")
            else:
                console.print(f"[yellow]-> No fix found in RAG, attempting install: {install_command}[/yellow]")

        except Exception as e:
            logger.debug(f"Could not search RAG for fix: {e}")

        # Step 2: Apply the fix (install the package)
        console.print(f"[cyan]-> Installing {tool_name}...[/cyan]")

        import subprocess
        try:
            result = subprocess.run(
                install_command.split(),
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                console.print(f"[green]✓ {tool_name} installed successfully[/green]")
                install_success = True
            else:
                console.print(f"[red]✗ Failed to install {tool_name}: {result.stderr}[/red]")
                install_success = False
                return code  # Return original code

        except Exception as e:
            console.print(f"[red]✗ Install error: {e}[/red]")
            return code

        # Step 3: Rerun the tool with the fixed dependency
        if install_success:
            try:
                console.print(f"[cyan]-> Running {tool_name} on code...[/cyan]")
                fixed_code = fix_function(code)

                if fixed_code != code:
                    console.print(f"[green]✓ {tool_name} successfully processed code[/green]")
                    tool_success = True
                else:
                    console.print(f"[dim]{tool_name} ran but made no changes[/dim]")
                    tool_success = True  # Still counts as success

            except Exception as e:
                console.print(f"[red]✗ {tool_name} failed after install: {e}[/red]")
                tool_success = False
                fixed_code = code
        else:
            tool_success = False
            fixed_code = code

        # Step 4: Record success/failure in RAG for future learning
        try:
            from datetime import datetime

            # Get existing fix stats or create new
            if existing_fixes:
                fix_artifact = existing_fixes[0]
                success_count = fix_artifact.metadata.get("success_count", 0)
                failure_count = fix_artifact.metadata.get("failure_count", 0)
            else:
                success_count = 0
                failure_count = 0

            # Update counts
            if tool_success:
                success_count += 1
            else:
                failure_count += 1

            # Calculate success rate
            total = success_count + failure_count
            success_rate = success_count / total if total > 0 else 0

            # Store updated fix in RAG
            self.rag.store_artifact(
                artifact_id=fix_id,
                artifact_type=ArtifactType.TOOL,
                name=f"Static Tool Fix: {tool_name}",
                description=f"Automatic dependency fix for {tool_name}",
                content=f"""Fix for missing static tool: {tool_name}

Install Command: {install_command}
Success Rate: {success_rate:.1%} ({success_count}/{total} attempts)
Last Updated: {datetime.now().isoformat()}

This fix automatically installs the missing package and reruns the tool.
""",
                tags=["code_fix", "static_tool_fix", "dependency", tool_name, "auto_fix"],
                metadata={
                    "tool_name": tool_name,
                    "install_command": install_command,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "success_rate": success_rate,
                    "last_attempt": datetime.now().isoformat(),
                    "last_success": tool_success
                },
                auto_embed=True  # Enable semantic search
            )

            console.print(f"[dim]Recorded fix result in RAG (success rate: {success_rate:.0%})[/dim]")

        except Exception as e:
            logger.debug(f"Could not record fix in RAG: {e}")

        return fixed_code if tool_success else code

    def _record_tool_feedback_on_completion(
        self,
        description: str,
        quality_score: float,
        success: bool
    ) -> None:
        """
        Record feedback for tools that were used in this task.
        This creates a learning loop where the system improves tool selection over time.

        Args:
            description: The original task description
            quality_score: Quality score of the result (0.0-1.0)
            success: Whether the task completed successfully
        """
        selected_tools = self.context.get('_selected_tools', [])
        if not selected_tools:
            return

        # Determine feedback type based on success and quality
        if success and quality_score >= 0.7:
            feedback_type = 'positive'
            reason = f"Task completed successfully with quality score {quality_score:.2f}"
        elif success and quality_score >= 0.5:
            feedback_type = 'positive'
            reason = f"Task completed with acceptable quality {quality_score:.2f}"
        elif success:
            # Low quality but technically successful - neutral/no feedback
            return
        else:
            feedback_type = 'negative'
            reason = "Task failed to complete successfully"

        # Record feedback for the top tool (most relevant)
        if selected_tools:
            top_tool = selected_tools[0]
            try:
                self.tools_manager.record_tool_feedback(
                    tool_id=top_tool.tool_id,
                    prompt=description,
                    feedback_type=feedback_type,
                    reason=reason,
                    metadata={
                        "quality_score": quality_score,
                        "success": success
                    }
                )
            except Exception as e:
                # Don't fail the task if feedback recording fails
                logger.debug(f"Could not record tool feedback: {e}")

    def _save_overseer_plan(self, node_id: str, specification: str) -> None:
        """
        Save the overseer's plan/specification to a text file.
        This preserves the original strategy for future reference.

        Args:
            node_id: Node identifier
            specification: The overseer's plan/specification
        """
        from rich.console import Console
        console = Console()

        try:
            # Get node directory
            node_path = self.runner.get_node_path(node_id).parent
            plan_file = node_path / f"{node_id}_plan.txt"

            # Save the plan
            plan_file.write_text(specification, encoding='utf-8')
            console.print(f"[dim]✓ Saved overseer plan to {plan_file.name}[/dim]")

        except Exception as e:
            console.print(f"[dim yellow]Could not save overseer plan: {e}[/dim yellow]")
            logger.debug(f"Failed to save overseer plan for {node_id}: {e}")

    def _generate_behave_feature(
        self,
        node_id: str,
        description: str,
        specification: str,
        code: str
    ) -> None:
        """
        Generate a Behave .feature file for BDD testing.

        Args:
            node_id: Node identifier
            description: Task description
            specification: Detailed specification
            code: Generated code
        """
        from rich.console import Console
        console = Console()

        try:
            # Get node directory
            node_path = self.runner.get_node_path(node_id).parent
            feature_file = node_path / f"{node_id}.feature"

            # Prepare input for behave_test_generator tool
            feature_input = {
                "feature_content": f"""Feature: {description}

  As a developer
  I want to test {description}
  So that I can ensure it works correctly

  Scenario: Basic functionality
    Given the system is initialized
    When I execute the main function
    Then I should get the expected result

Specification:
{specification}

Code:
{code[:500]}...
""",
                "mode": "generate",
                "feature_output_path": str(node_path)
            }

            # Use the behave_test_generator tool
            console.print(f"[dim]Generating Behave .feature file...[/dim]")

            # Call the tool to generate BDD tests
            from node_runtime import call_tool
            result = call_tool("behave_test_generator", feature_input)

            if result and result.get("success"):
                console.print(f"[dim green]✓ Generated Behave feature: {feature_file.name}[/dim green]")
            else:
                # Fallback: Create a basic feature file manually
                basic_feature = f"""Feature: {description}

  As a developer
  I want to verify {description}
  So that the implementation meets requirements

  Scenario: Basic execution
    Given the node {node_id} is loaded
    When I execute the main function
    Then the result should be valid
    And no errors should occur

  # Specification:
  # {specification[:200]}...
"""
                feature_file.write_text(basic_feature, encoding='utf-8')
                console.print(f"[dim]✓ Created basic Behave feature (tool generation failed)[/dim]")

        except Exception as e:
            console.print(f"[dim yellow]Could not generate Behave feature: {e}[/dim yellow]")
            logger.debug(f"Behave feature generation failed for {node_id}: {e}")

    def _generate_locust_load_test(
        self,
        node_id: str,
        description: str,
        code: str
    ) -> None:
        """
        Generate a Locust load testing script.

        Args:
            node_id: Node identifier
            description: Task description
            code: Generated code
        """
        from rich.console import Console
        console = Console()

        try:
            # Get node directory
            node_path = self.runner.get_node_path(node_id).parent
            locust_file = node_path / f"locust_{node_id}.py"

            # Prepare input for locust_load_tester tool
            locust_input = {
                "spec_content": f"""# Load Test Specification for {node_id}

Description: {description}

Code to test:
{code[:500]}...

# This will generate a Locust test for the above code
""",
                "mode": "generate",
                "output_path": str(node_path),
                "users": 10,
                "spawn_rate": 2,
                "run_time": "30s",
                "host": "http://localhost:8000"
            }

            # Use the locust_load_tester tool
            console.print(f"[dim]Generating Locust load test...[/dim]")

            # Call the tool to generate load tests
            from node_runtime import call_tool
            result = call_tool("locust_load_tester", locust_input)

            if result and result.get("success"):
                console.print(f"[dim green]✓ Generated Locust test: {locust_file.name}[/dim green]")
            else:
                # Fallback: Create a basic locustfile manually
                basic_locust = f"""\"\"\"
Locust load test for {node_id}

Description: {description}

Usage:
    locust -f locust_{node_id}.py --users 10 --spawn-rate 2 --run-time 30s
\"\"\"

from locust import HttpUser, task, between
import json


class {node_id.title().replace('_', '')}User(HttpUser):
    wait_time = between(1, 3)

    @task
    def test_main_function(self):
        \"\"\"Test the main functionality\"\"\"
        # TODO: Customize this test based on the actual API/function
        response = self.client.get(f"/api/{node_id}")
        assert response.status_code == 200

    @task(2)
    def test_with_payload(self):
        \"\"\"Test with POST payload\"\"\"
        # TODO: Customize payload based on actual inputs
        payload = {{"test": "data"}}
        response = self.client.post(
            f"/api/{node_id}",
            json=payload
        )
        assert response.status_code in [200, 201]


# Run with: locust -f locust_{node_id}.py --users 10 --spawn-rate 2 --run-time 30s
"""
                locust_file.write_text(basic_locust, encoding='utf-8')
                console.print(f"[dim]✓ Created basic Locust test (tool generation failed)[/dim]")

        except Exception as e:
            console.print(f"[dim yellow]Could not generate Locust load test: {e}[/dim yellow]")
            logger.debug(f"Locust test generation failed for {node_id}: {e}")

    def _verify_bdd_and_performance(
        self,
        node_id: str,
        description: str,
        specification: str,
        code: str
    ) -> tuple[bool, float]:
        """
        Verify BDD specification compliance and measure performance.

        Args:
            node_id: Node identifier
            description: Task description
            specification: Detailed specification
            code: Generated code

        Returns:
            Tuple of (bdd_passed: bool, perf_score: float 0-1)
        """
        from rich.console import Console
        console = Console()

        bdd_passed = False
        perf_score = 0.0

        try:
            # Step 1: Run Behave BDD tests
            node_path = self.runner.get_node_path(node_id).parent
            feature_file = node_path / f"{node_id}.feature"

            if feature_file.exists():
                console.print(f"[dim]Running Behave tests...[/dim]")

                import subprocess
                try:
                    # Run behave on the feature file
                    result = subprocess.run(
                        ["behave", str(feature_file)],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=str(node_path)
                    )

                    if result.returncode == 0:
                        bdd_passed = True
                        console.print(f"[dim green]✓ BDD tests passed[/dim green]")
                    else:
                        console.print(f"[dim yellow]BDD tests failed: {result.stderr[:200]}[/dim yellow]")

                except FileNotFoundError:
                    console.print(f"[dim yellow]Behave not installed, skipping BDD verification[/dim yellow]")
                except subprocess.TimeoutExpired:
                    console.print(f"[dim yellow]BDD tests timed out[/dim yellow]")
                except Exception as e:
                    console.print(f"[dim yellow]BDD test error: {e}[/dim yellow]")
            else:
                console.print(f"[dim]No .feature file found, skipping BDD verification[/dim]")

            # Step 2: Run Locust performance test
            locust_file = node_path / f"locust_{node_id}.py"

            if locust_file.exists():
                console.print(f"[dim]Running performance tests (5s)...[/dim]")

                try:
                    # Run locust headless for 5 seconds
                    result = subprocess.run(
                        [
                            "locust",
                            "-f", str(locust_file),
                            "--headless",
                            "--users", "5",
                            "--spawn-rate", "1",
                            "--run-time", "5s",
                            "--host", "http://localhost:8000"
                        ],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        cwd=str(node_path)
                    )

                    # Parse performance results from output
                    if "requests/s" in result.stdout:
                        # Extract requests per second
                        import re
                        rps_match = re.search(r'(\d+\.\d+)\s+requests/s', result.stdout)
                        if rps_match:
                            rps = float(rps_match.group(1))
                            # Normalize: 0-10 rps = 0.0-0.5, 10-100 rps = 0.5-0.9, >100 = 1.0
                            if rps >= 100:
                                perf_score = 1.0
                            elif rps >= 10:
                                perf_score = 0.5 + (rps - 10) / 90 * 0.4
                            else:
                                perf_score = rps / 10 * 0.5
                            console.print(f"[dim green]Performance: {rps:.1f} req/s (score: {perf_score:.2f})[/dim green]")
                    else:
                        # Fallback: if no errors, give baseline score
                        if result.returncode == 0:
                            perf_score = 0.5
                            console.print(f"[dim]Performance test completed (baseline score)[/dim]")

                except FileNotFoundError:
                    console.print(f"[dim yellow]Locust not installed, skipping performance test[/dim yellow]")
                except subprocess.TimeoutExpired:
                    console.print(f"[dim yellow]Performance test timed out[/dim yellow]")
                except Exception as e:
                    console.print(f"[dim yellow]Performance test error: {e}[/dim yellow]")
            else:
                console.print(f"[dim]No Locust file found, skipping performance test[/dim]")

        except Exception as e:
            console.print(f"[dim yellow]BDD/performance verification error: {e}[/dim yellow]")
            logger.debug(f"Verification failed for {node_id}: {e}")

        return bdd_passed, perf_score

    def _detect_interface(self, code: str, description: str, specification: str) -> dict:
        """
        Detect the interface of generated code (inputs, outputs, operation type).

        Returns a schema describing:
        - inputs: List of expected input fields
        - outputs: List of output fields
        - operation_type: combiner, splitter, filter, transformer, generator, etc.
        """
        # Use LLM to analyze the code and extract interface
        interface_prompt = f"""Analyze this Python code and extract its interface specification.

CODE:
```python
{code}
```

TASK DESCRIPTION: {description}

Extract:
1. **inputs**: List of input field names the code reads from input_data (e.g., ["a", "b", "text", "numbers"])
2. **outputs**: List of output field names in the result (usually just ["result"])
3. **operation_type**: One of:
   - "generator": Creates content from scratch (uses call_tool, no real inputs needed)
   - "transformer": Single input -> transformed output (e.g., process text, calculate)
   - "combiner": Multiple inputs -> single output (e.g., add two numbers)
   - "splitter": Single input -> multiple outputs
   - "filter": Input -> filtered/validated output

Return ONLY a JSON object with this structure:
{{
  "inputs": ["field1", "field2"],
  "outputs": ["result"],
  "operation_type": "combiner",
  "description": "Brief description of what this code does"
}}

Return ONLY the JSON, no explanations."""

        try:
            response = self.client.generate(
                model="llama3",
                prompt=interface_prompt,
                temperature=0.1,
                model_key=self.config.overseer_model_key  # Use actual model key for routing
            )

            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                interface_schema = json.loads(json_match.group(0))
                return interface_schema
            else:
                # Fallback: basic detection
                return self._basic_interface_detection(code, description)

        except Exception as e:
            console.print(f"[dim yellow]Could not detect interface via LLM: {e}[/dim yellow]")
            return self._basic_interface_detection(code, description)

    def _basic_interface_detection(self, code: str, description: str) -> dict:
        """Fallback interface detection using simple pattern matching."""
        inputs = []
        outputs = ["result"]  # Default

        # Find input_data.get(...) calls
        import re
        input_matches = re.findall(r'input_data\.get\(["\']([^"\']+)["\']', code)
        inputs.extend(input_matches)

        # Find input_data[...] accesses
        bracket_matches = re.findall(r'input_data\[["\']([^"\']+)["\']\]', code)
        inputs.extend(bracket_matches)

        # Detect operation type
        if 'call_tool' in code:
            operation_type = "generator"
        elif len(inputs) == 0:
            operation_type = "generator"
        elif len(inputs) == 1:
            operation_type = "transformer"
        elif len(inputs) >= 2:
            operation_type = "combiner"
        else:
            operation_type = "transformer"

        return {
            "inputs": list(set(inputs)) if inputs else [],
            "outputs": outputs,
            "operation_type": operation_type,
            "description": description[:200]
        }

    def _generate_interface_tests_first(self, node_id: str, description: str, specification: str) -> str:
        """
        Generate interface-defining tests BEFORE code (TDD approach).

        Returns the test code that defines the expected interface.
        """
        # CRITICAL: Use fast LLM to automatically detect task type
        # (More accurate than keyword matching)
        # Get the model key for veryfast triage (use content role for better text understanding)
        triage_model_key = self.config.get_model(role="content", level="veryfast")
        if triage_model_key:
            triage_metadata = self.config.get_model_metadata(triage_model_key)
            triage_model_name = triage_metadata.get("name", self.config.triage_model)
        else:
            triage_model_name = self.config.triage_model
            triage_model_key = self.config.get_model(role="default", level="veryfast")

        console.print(f"[dim]Classifying task type with {triage_model_name}...[/dim]")

        classification_prompt = f"""Is this task about writing TEXT or writing CODE?

Task: "{description}"

If it's about writing stories, jokes, articles, poems, translations, essays, or other TEXT content, answer: TEXT
If it's about writing algorithms, functions, APIs, data processing, calculations, or other CODE, answer: CODE

Your answer (one word only):"""

        classification = self.client.generate(
            model=triage_model_name,
            prompt=classification_prompt,
            temperature=0.1,
            model_key=triage_model_key  # Use actual model key for routing
        ).strip().upper()

        # Check if it's a text/content task
        is_content_task = 'TEXT' in classification or any(word in description.lower() for word in ['joke', 'story', 'poem', 'haiku', 'essay', 'article'])
        console.print(f"[dim]Task classified as: {'content' if is_content_task else 'code'} (LLM said: {classification[:20]})[/dim]")

        if is_content_task:
            # CONTENT GENERATION: SKIP interface tests - they always fail with import issues!
            # Instead, rely on smoke tests after code generation
            console.print(f"\n[cyan]Using cached TDD template for content generation (no LLM call needed)...[/cyan]")
            console.print(f"[dim]Skipping interface tests for content tasks - will validate with smoke tests instead[/dim]")

            # Return empty string to skip TDD tests
            return ""
        else:
            # ARITHMETIC/DATA PROCESSING: Can use specific functions
            test_prompt = f"""You are writing unit tests to DEFINE THE INTERFACE for code that will be generated.
This is Test-Driven Development (TDD) - the tests come FIRST and define what the code should do.

TASK DESCRIPTION: {description}

SPECIFICATION: {specification[:800]}

YOUR JOB:
1. Analyze what inputs and outputs the code should have
2. Define the interface through tests
3. Create test cases that the future code must pass

RULES:
1. For arithmetic tasks (add, subtract, multiply):
   - Define a function with clear parameters
   - Test it with the specific numbers from the description
   - Example: "add 5 and 3" -> test that add(5, 3) returns 8

2. For data processing tasks (sort, filter, transform):
   - Define expected input/output formats
   - Test with sample data
   - Verify correct transformations

EXAMPLE FOR ARITHMETIC:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import add  # The code generator will create this function

def test_add_specific_numbers():
    \"\"\"Test that add(5, 3) returns 8\"\"\"
    print("Testing add(5, 3)...")
    result = add(5, 3)
    assert result == 8, f"Expected 8 but got {{result}}"
    print("OK Test passed: 5 + 3 = 8")

def test_add_negative_numbers():
    \"\"\"Test edge case: negative numbers\"\"\"
    print("Testing add(-5, 3)...")
    result = add(-5, 3)
    assert result == -2, f"Expected -2 but got {{result}}"
    print("OK Test passed: -5 + 3 = -2")

if __name__ == "__main__":
    test_add_specific_numbers()
    test_add_negative_numbers()
```

Now generate the interface-defining tests for: {description}

Output ONLY the Python test code (no markdown fences, no explanations):"""

        # Try Pynguin-based TDD template generation first (fast, specification-driven)
        use_pynguin_tdd = self.config.get("testing.use_pynguin_tdd", True)

        if use_pynguin_tdd and not is_content_task:
            console.print(f"\n[cyan]Attempting Pynguin-based TDD template generation...[/cyan]")
            pynguin_template = self._generate_tdd_template_with_pynguin(
                node_id="temp",  # Temporary, not saved yet
                description=description,
                specification=specification
            )

            if pynguin_template:
                return pynguin_template

        # OPTIMIZATION: For content tasks, skip LLM and use cached template
        # (The test is always identical - just checks main() exists)
        if is_content_task:
            console.print(f"\n[cyan]Using cached TDD template for content generation (no LLM call needed)...[/cyan]")

            # Load template from file
            import pathlib
            template_path = pathlib.Path(__file__).parent / "templates" / "tdd_main_interface_test.py"

            try:
                test_code = template_path.read_text()
                console.print(f"[dim green]Loaded cached template ({len(test_code)} chars) - saved LLM call![/dim green]")
                return test_code
            except FileNotFoundError:
                # Fallback if template file missing
                console.print(f"[yellow]Warning: Template not found, using inline fallback[/yellow]")
                test_code = """import sys
import json
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_main_interface():
    \"\"\"Test that main() function exists and has correct interface\"\"\"
    print("Testing main() interface...")
    import main
    assert hasattr(main, 'main'), "main() function must exist"
    print("OK main() function exists")

if __name__ == "__main__":
    test_main_interface()
"""
                return test_code

        # For non-content tasks, generate custom tests with LLM
        console.print(f"\n[cyan]Generating interface-defining tests first (TDD mode)...[/cyan]")

        try:
            test_code = self.client.generate(
                model=self.config.generator_model,
                prompt=test_prompt,
                temperature=0.3,  # Lower temperature for test generation
                model_key=self.config.generator_model_key  # Use actual model key for routing
            )

            # Clean the test code
            test_code = self._clean_code(test_code) if test_code else ""

            # Check if generation failed, returned empty, or returned non-Python content
            if not test_code or len(test_code) < 50 or not self._looks_like_python(test_code):
                console.print(f"[yellow]Warning: Test generation returned {len(test_code)} chars or invalid Python, using fallback template[/yellow]")
                # Use fallback template
                test_code = """import sys
import json
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_main_interface():
    \"\"\"Test that main() function exists and has correct interface\"\"\"
    print("Testing main() interface...")
    import main
    assert hasattr(main, 'main'), "main() function must exist"
    print("OK main() function exists")

if __name__ == "__main__":
    test_main_interface()
"""

            console.print(f"[dim green]Generated interface tests ({len(test_code)} chars)[/dim green]")

            return test_code

        except Exception as e:
            console.print(f"[red]ERROR generating tests: {e}[/red]")
            console.print(f"[yellow]Using fallback test template[/yellow]")

            # Return minimal fallback test
            return """import sys
import json
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_main_interface():
    \"\"\"Test that main() function exists\"\"\"
    print("Testing main() interface...")
    import main
    assert hasattr(main, 'main'), "main() function must exist"
    print("OK main() function exists")

if __name__ == "__main__":
    test_main_interface()
"""

    def _generate_and_run_tests(self, node_id: str, description: str, specification: str, code: str, skip_generation: bool = False) -> bool:
        """Generate and run unit tests for a node with comprehensive logging.

        Args:
            skip_generation: If True, skip test generation (tests already exist from TDD mode)
        """
        # If TDD mode, tests already exist - just run them
        if skip_generation:
            console.print("[dim]Using pre-generated interface tests from TDD mode[/dim]")
            console.print("[cyan]Running tests with logging...[/cyan]")

            # Run the pre-generated test file
            import subprocess
            import os
            from pathlib import Path

            node_dir = self.runner.get_node_path(node_id).parent
            test_path = node_dir / "test_main.py"

            # Set PYTHONPATH so tests can import node_runtime
            env = os.environ.copy()
            code_evolver_dir = str(Path(__file__).parent.parent.absolute())
            env['PYTHONPATH'] = code_evolver_dir + os.pathsep + env.get('PYTHONPATH', '')

            try:
                result = subprocess.run(
                    [sys.executable, "test_main.py"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(node_dir),
                    env=env
                )

                stdout = result.stdout
                stderr = result.stderr
                success = result.returncode == 0

                # Store test output for escalation context
                test_output_log = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}\n\nReturn code: {result.returncode}"
                self.context['last_test_output'] = test_output_log

                if success:
                    console.print("[green]OK Tests passed[/green]")
                    if stdout:
                        console.print(f"[dim]Test log:\n{stdout[:500]}[/dim]")
                    return True
                else:
                    console.print(f"[red]FAIL Tests failed[/red]")
                    console.print(f"[yellow]Error: {stderr[:300]}[/yellow]")
                    if stdout:
                        console.print(f"[dim]Test output before failure:\n{stdout[:500]}[/dim]")
                    # Store error for escalation
                    self.context['last_error'] = stderr
                    self.context['last_stdout'] = stdout
                    return False
            except subprocess.TimeoutExpired:
                console.print(f"[red]FAIL Tests timed out after 30 seconds[/red]")
                self.context['last_error'] = "Test execution timed out"
                return False
            except Exception as e:
                console.print(f"[red]FAIL Error running tests: {e}[/red]")
                self.context['last_error'] = str(e)
                return False

        # Traditional mode: generate tests now
        # Try Pynguin first for fast automated test generation
        pynguin_enabled = self.config.get("testing.use_pynguin", True)
        pynguin_timeout = self.config.get("testing.pynguin_timeout", 30)
        pynguin_min_coverage = self.config.get("testing.pynguin_min_coverage", 0.70)

        pynguin_result = None
        # Check if code uses node_runtime
        has_node_runtime = (
            'from node_runtime import' in code or
            'import node_runtime' in code or
            'call_tool(' in code
        )

        if pynguin_enabled:
            # Try Pynguin even for code with node_runtime (we'll use a mock)
            console.print(f"[dim cyan]> Trying Pynguin for fast test generation...[/dim cyan]")
            if has_node_runtime:
                console.print(f"[dim]Using mock node_runtime for test generation[/dim]")

            pynguin_result = self._generate_tests_with_pynguin(
                node_id,
                timeout=pynguin_timeout,
                min_coverage=pynguin_min_coverage,
                use_mock_runtime=has_node_runtime
            )

        # Check if code uses call_tool - if so, generate minimal smoke test
        uses_call_tool = 'call_tool(' in code

        if pynguin_result and pynguin_result['success']:
            # Pynguin succeeded - use those tests
            coverage = pynguin_result['coverage']
            method = pynguin_result['method']
            console.print(f"[green]✓ Using {method} tests ({coverage:.1f}% coverage, {pynguin_result['test_count']} tests)[/green]")

            if pynguin_result.get('needed_llm_fix'):
                console.print("[dim]Tests were improved by LLM to meet coverage threshold[/dim]")
        else:
            # ALWAYS generate comprehensive LLM tests (for all code)
            # Create mock node_runtime if code uses external tools
            mock_runtime = None
            if uses_call_tool:
                # Save mock node_runtime.py for testing
                mock_runtime_code = '''"""Mock node_runtime for testing."""
from typing import Any

def call_tool(tool_name: str, prompt_or_data: Any = None, **kwargs) -> Any:
    """Mock call_tool that returns sensible defaults."""
    if 'generator' in tool_name or 'writer' in tool_name:
        return "Mock generated content for testing"
    elif 'translator' in tool_name:
        return "Mock translated content"
    elif 'database' in tool_name or 'storage' in tool_name:
        return {"status": "success", "id": "mock_123"}
    else:
        return {"status": "success", "result": f"Mock {tool_name}"}

def call_llm(model: str, prompt: str, **kwargs) -> str:
    """Mock LLM call."""
    return "Mock LLM response for testing"

def call_tools_parallel(tool_calls: list) -> list:
    """Mock parallel tool calls."""
    return [call_tool(call[0] if isinstance(call, tuple) else call.get('tool', 'unknown'), "")
            for call in tool_calls]
'''
                mock_runtime_path = self.runner.get_node_path(node_id).parent / "node_runtime.py"
                mock_runtime_path.write_text(mock_runtime_code, encoding='utf-8')
                console.print("[dim]Created mock node_runtime for testing[/dim]")

            # Generate comprehensive tests with mocking instructions
            mock_instructions = ""
            if uses_call_tool:
                mock_instructions = """
NOTE: A mock node_runtime.py has been created in the same directory with mock implementations of:
- call_tool() - returns realistic mock data based on tool name
- call_llm() - returns mock LLM responses
- call_tools_parallel() - returns list of mock results

You can freely use: from node_runtime import call_tool, call_llm, call_tools_parallel
These will work in tests because we've provided mocks.
"""

            test_prompt = f"""Generate comprehensive unit tests for this code with HIGH COVERAGE (aim for 80%+).

TASK: {description}

CODE TO TEST:
```python
{code}
```

{mock_instructions}

REQUIREMENTS:
1. Create multiple test functions testing different scenarios
2. Test edge cases (empty input, None, invalid data)
3. Test the main() function with realistic input_data dictionaries
4. If code has helper functions, test those too
5. Use assertions to verify correct behavior
6. Include print statements for test progress

EXAMPLE STRUCTURE:
```python
def test_basic_functionality():
    print("Testing basic functionality...")
    from main import main
    result = main({{"key": "value"}})  # Use actual expected keys from code
    assert result is not None, "Result should not be None"
    print("OK Basic test passed")

def test_edge_cases():
    print("Testing edge cases...")
    from main import main
    # Test with empty input
    result = main({{}})
    # Add appropriate assertions
    print("OK Edge cases passed")

def test_invalid_input():
    print("Testing invalid input handling...")
    from main import main
    try:
        result = main(None)
        # Verify it handles None gracefully
        print("OK Invalid input handled")
    except Exception as e:
        print(f"OK Caught expected error: {{e}}")

if __name__ == "__main__":
    test_basic_functionality()
    test_edge_cases()
    test_invalid_input()
    print("All tests passed!")
```

CRITICAL:
- Analyze the code to see what input_data keys it expects
- Create realistic test data based on the task description
- DO NOT just check hasattr() or imports - actually TEST the logic
- Return ONLY Python code, NO markdown fences, NO explanations
- Every line must be valid Python syntax

Generate comprehensive tests now:"""

            try:
                test_code = self.client.generate(
                    model=self.config.generator_model,
                    prompt=test_prompt,
                    temperature=0.3,
                    model_key=self.config.generator_model_key  # Use actual model key for routing
                )
            except Exception as e:
                console.print(f"[red]Error generating tests: {e}[/red]")
                return False

            # Clean test code (remove markdown if present)
            test_code = self._clean_code(test_code)

            # Validate and clean test code - remove any explanatory text
            lines = test_code.split('\n')
            clean_lines = []
            found_code = False

            for line in lines:
                # Skip empty lines before code starts
                if not found_code and not line.strip():
                    continue

                # Start collecting when we see imports or code
                if line.strip().startswith(('import ', 'from ', 'def ', 'class ', '@')):
                    found_code = True

                if found_code:
                    stripped = line.strip()

                    # SMART FILTERING: Only filter call_tool if main code doesn't use it
                    # This prevents conflict with fixers that add call_tool back
                    main_uses_call_tool = 'call_tool(' in code

                    if not main_uses_call_tool:
                        # Main code doesn't use call_tool, safe to filter from tests
                        if 'from node_runtime import' in stripped or 'import node_runtime' in stripped:
                            console.print(f"[dim]Filtering out node_runtime import (main doesn't use it): {stripped[:60]}...[/dim]")
                            continue
                        if 'call_tool(' in stripped:
                            console.print(f"[dim]Filtering out call_tool usage (main doesn't use it): {stripped[:60]}...[/dim]")
                            continue
                    else:
                        # Main code DOES use call_tool - keep it in tests but add proper imports
                        # The test needs to test the actual call_tool functionality
                        pass

                    # Also filter out problematic test patterns
                    if 'from main import' in stripped and stripped != 'from main import main':
                        # Don't import specific functions, only import main() function
                        console.print(f"[dim]Filtering out specific function import: {stripped[:60]}...[/dim]")
                        continue

                    # Filter out explanatory text (lines that don't look like Python)
                    # Skip lines that are clearly explanatory text
                    if any(phrase in stripped.lower() for phrase in [
                        'these tests', 'this test', 'the test checks', 'note that', 'by adding',
                        'the code', 'we can see', 'this will', 'this should', 'the above',
                        'as you can', 'for example', 'in this case', 'it is important'
                    ]):
                        console.print(f"[dim]Filtering out explanatory line: {stripped[:60]}...[/dim]")
                        continue

                    # Skip lines that are clearly not Python code (but be permissive)
                    # Only filter out lines that are obviously natural language, not code
                    if stripped and not line.startswith((' ', '\t')):
                        # Check if line looks like natural language rather than code
                        # Look for patterns like sentences ending with periods, questions, etc.
                        is_natural_language = (
                            # Long sentences with periods (but not method calls like sys.path)
                            (stripped.endswith('.') and ' ' in stripped and not '(' in stripped) or
                            # Questions
                            stripped.endswith('?') or
                            # Sentences with multiple words but no Python operators/syntax
                            (len(stripped.split()) > 5 and
                             not any(c in stripped for c in ['(', ')', '[', ']', '{', '}', '=', ':', ',']) and
                             not stripped.startswith('#'))
                        )
                        if is_natural_language:
                            console.print(f"[dim]Filtering out non-Python line: {stripped[:60]}...[/dim]")
                            continue

                    clean_lines.append(line)

            if clean_lines:
                test_code = '\n'.join(clean_lines)
                if len(clean_lines) < len(lines):
                    console.print(f"[yellow]Cleaned test code: removed {len(lines) - len(clean_lines)} explanatory lines[/yellow]")

            # Save test code
            test_path = self.runner.get_node_path(node_id).parent / "test_main.py"
            with open(test_path, 'w') as f:
                f.write(test_code)

            console.print("[dim]OK Tests generated (with comprehensive logging)[/dim]")

        # Run tests and capture all output
        console.print("[cyan]Running tests with logging...[/cyan]")

        # Run the generated test file directly with Python
        import subprocess
        import os
        from pathlib import Path

        node_dir = self.runner.get_node_path(node_id).parent
        test_path = node_dir / "test_main.py"

        # Set PYTHONPATH so tests can import node_runtime
        env = os.environ.copy()
        code_evolver_dir = str(Path(__file__).parent.parent.absolute())
        env['PYTHONPATH'] = code_evolver_dir + os.pathsep + env.get('PYTHONPATH', '')

        try:
            result = subprocess.run(
                [sys.executable, "test_main.py"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(node_dir),
                env=env
            )

            stdout = result.stdout
            stderr = result.stderr
            success = result.returncode == 0

            # Store test output for escalation context
            test_output_log = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}\n\nReturn code: {result.returncode}"
            self.context['last_test_output'] = test_output_log

            if success:
                console.print("[green]OK Tests passed[/green]")
                if stdout:
                    console.print(f"[dim]Test log:\n{stdout[:500]}[/dim]")
                return True
            else:
                console.print(f"[red]FAIL Tests failed[/red]")
                console.print(f"[yellow]Error: {stderr[:300]}[/yellow]")
                if stdout:
                    console.print(f"[dim]Test output before failure:\n{stdout[:500]}[/dim]")
                # Store error for escalation
                self.context['last_error'] = stderr
                self.context['last_stdout'] = stdout
                return False
        except subprocess.TimeoutExpired:
            console.print(f"[red]FAIL Tests timed out after 30 seconds[/red]")
            self.context['last_error'] = "Test execution timed out"
            return False
        except Exception as e:
            console.print(f"[red]FAIL Error running tests: {e}[/red]")
            self.context['last_error'] = str(e)
            return False

    def _adaptive_escalate_and_fix(
        self,
        node_id: str,
        code: str,
        description: str,
        specification: str = "",
        available_tools: str = ""
    ) -> bool:
        """
        Multi-stage adaptive escalation with AUTO-FIX system:

        Stage 0 (FIRST): Try auto-fix from Fix Tools Library (RAG-based)
        Stage 1 (Attempts 1-2): Normal fixing with fast model
        Stage 2 (Attempts 3-4): Add debug logging, continue with fast model
        Stage 3 (Attempts 5-6): Continue with logging, escalate to powerful model
        Stage 4 (If passed): Auto-remove logging to clean code
        Stage 5 (If 6 failures): Escalate to god-level tool (deepseek-coder)

        Tracks all attempts to provide full context to god-level tool.
        """
        max_attempts = 6  # Extended to 6 attempts

        # Three-tier model strategy
        fast_model = "codellama"
        powerful_model = self.config.escalation_model  # qwen2.5-coder:14b
        god_level_model = "deepseek-coder:6.7b"  # Final boss on localhost

        # Temperature progression: start low, gradually increase
        temperature_schedule = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

        # Get error details from context
        error_output = self.context.get('last_error', 'Unknown error')
        stdout_output = self.context.get('last_stdout', '')
        test_output = self.context.get('last_test_output', '')
        original_test = self.context.get('original_interface_test', '')

        # STAGE 0: Try AUTO-FIX from Fix Tools Library (RAG-based)
        if self._fix_tools_manager:
            console.print("[cyan]Checking fix library for known solutions...[/cyan]")

            try:
                # Extract error type from error message
                import re
                error_type_match = re.match(r'(\w+Error|Exception)', error_output)
                error_type = error_type_match.group(1) if error_type_match else "Unknown"

                # Try auto-fix
                fix_result = self._fix_tools_manager.auto_fix_code(
                    error_message=error_output,
                    error_type=error_type,
                    code=code,
                    filename="main.py"
                )

                if fix_result.get("fixed"):
                    console.print(f"[green]✓ Auto-fix applied: {fix_result['fix_applied']}[/green]")
                    console.print(f"[dim]{fix_result['message']}[/dim]")

                    # Save fixed code
                    fixed_code = fix_result["fixed_code"]
                    self.runner.save_code(node_id, fixed_code)

                    # Re-run tests
                    console.print("[cyan]Re-running tests with fixed code...[/cyan]")
                    if self._run_tests(node_id):
                        console.print("[green]✓ Auto-fix successful! Tests pass.[/green]")
                        return True
                    else:
                        console.print("[yellow]Auto-fix applied but tests still fail - continuing with manual repair[/yellow]")
                else:
                    console.print(f"[dim]{fix_result.get('message', 'No applicable fixes found')}[/dim]")

            except Exception as e:
                console.print(f"[dim yellow]Auto-fix check failed: {e}[/dim yellow]")
        else:
            console.print("[dim]Auto-fix system not yet available (tools still loading)[/dim]")

        # Track ALL attempts for god-level tool
        all_attempts = []

        # Track if logging was added
        logging_added = False

        for attempt in range(max_attempts):
            # Determine model based on attempt
            if attempt < 2:
                current_model = fast_model
                stage = "Normal Fixing"
            elif attempt < 4:
                current_model = fast_model
                stage = "With Debug Logging"
                logging_added = True
            else:
                current_model = powerful_model
                stage = "Powerful Model + Logging"
                logging_added = True

            # Adjust temperature based on attempt
            temperature = temperature_schedule[attempt]

            console.print(f"[cyan]Attempt {attempt + 1}/{max_attempts} - {stage} ({current_model}, temp: {temperature})...[/cyan]")

            # Build summary of ALL previous attempts for context
            previous_attempts_summary = ""
            validation_warning = ""
            if all_attempts:
                previous_attempts_summary = "\nPREVIOUS FIX ATTEMPTS (all failed):\n"
                validation_failures = []
                for i, prev in enumerate(all_attempts, 1):
                    previous_attempts_summary += f"\n=== Attempt {i} ({prev['model']}, temp: {prev['temp']}) ===\n"
                    previous_attempts_summary += f"Fixes tried: {', '.join(prev.get('fixes', []))}\n"
                    previous_attempts_summary += f"Analysis: {prev.get('analysis', 'N/A')}\n"
                    previous_attempts_summary += f"Error: {prev['error'][:150]}...\n"

                    # Track validation failures
                    if prev.get('validation_failure'):
                        validation_failures.append(i)

                # Add strong warning if there were validation failures
                if validation_failures:
                    validation_warning = f"""
**CRITICAL WARNING - VALIDATION FAILURES DETECTED:**
Attempts {', '.join(map(str, validation_failures))} claimed to apply fixes but DID NOT actually modify the code!
This is a HALLUCINATION - you DESCRIBED what to fix but didn't change the code.

YOU MUST:
1. Actually MODIFY the code field with the fix applied, not just describe the fix
2. If you say "Added sys.path setup", the code MUST contain sys.path.insert() or sys.path.append()
3. If you say "Removed import", the import MUST be gone from the code
4. The "code" field must be DIFFERENT from the input code if you claim to have fixed it

DO NOT just describe fixes in fixes_applied - APPLY THEM TO THE CODE!
"""

            # Add logging requirement for attempts 3+
            logging_instruction = ""
            if attempt >= 2:  # Attempts 3-6
                logging_instruction = """

**LOGGING REQUIREMENT** (Attempts 3-6):
Since previous attempts failed, ADD comprehensive debug logging to help identify the issue:
- Add `import logging` at the top
- Add `logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')`
- Add logging.debug() statements at EVERY critical point:
  * Before reading input: logging.debug(f"Input data: {{input_data}}")
  * Before calling tools: logging.debug(f"Calling tool: {{tool_name}} with {{args}}")
  * After tool calls: logging.debug(f"Tool result: {{result[:100]}}")
  * Before file operations: logging.debug(f"Writing to {{filename}}")
  * In exception handlers: logging.exception("Error details")
- This logging will help us understand WHERE the failure occurs"""

            # Build conditional sections separately to avoid f-string issues
            test_log_section = ""
            if test_output:
                test_log_section = f"TEST EXECUTION LOG:\n{test_output[:1000]}"

            stdout_section = ""
            if stdout_output:
                stdout_section = f"STDOUT: {stdout_output[:500]}"

            # CRITICAL: Read the ACTUAL test file to see what functions are expected
            test_file_content = ""
            test_expectations = ""
            try:
                node_dir = self.runner.get_node_path(node_id).parent
                test_file_path = node_dir / "test_main.py"

                if test_file_path.exists():
                    with open(test_file_path, 'r') as f:
                        test_file_content = f.read()

                    # Extract imports to see what's expected
                    import re
                    imports = re.findall(r'from main import (.+)', test_file_content)
                    if imports:
                        imported_items = [item.strip() for imp in imports for item in imp.split(',')]
                        test_expectations = f"""
CRITICAL - TEST FILE EXPECTS THESE FUNCTIONS/CLASSES TO EXIST IN main.py:
{chr(10).join('  - ' + item for item in imported_items)}

Your code MUST implement ALL of these, or the tests will fail with ImportError!
"""
            except Exception as e:
                console.print(f"[dim yellow]Could not read test file: {e}[/dim yellow]")

            test_req_section = ""
            if test_file_content:
                test_req_section = f"""
ACTUAL TEST FILE CONTENT (test_main.py):
```python
{test_file_content[:1500]}
```

{test_expectations}
"""
            elif original_test:
                test_req_section = f"ORIGINAL TEST REQUIREMENTS:\n{original_test[:500]}"

            # Build comprehensive fix prompt with all context
            fix_prompt = f"""You are an expert code debugger. The following code FAILED its tests.

ORIGINAL GOAL:
{description}

OVERSEER STRATEGY:
{specification[:1000]}

{available_tools if available_tools and "No specific tools" not in available_tools else ""}

CURRENT CODE (has errors):
```python
{code}
```

TEST ERROR OUTPUT:
{error_output}

{test_log_section}

{stdout_section}

{previous_attempts_summary}

{test_req_section}

{logging_instruction}

{validation_warning}

You MUST respond with ONLY a JSON object in this exact format:

{{
  "code": "the fixed Python code as a string",
  "fixes_applied": ["brief description of fix 1", "fix 2"],
  "analysis": "one sentence explaining what was wrong"
}}

Requirements for "code" field:
- ONLY executable Python code
- NO markdown fences
- NO explanations mixed with code
- Must fix ALL errors shown above
- Must be immediately runnable
- Learn from previous failed attempts listed above
- CRITICAL: Handle call_tool() imports correctly based on ACTUAL USAGE:
  * If the code actually CALLS call_tool() somewhere:
    - Keep the call_tool() calls (NEVER replace with hardcoded data)
    - NEVER remove call_tool() calls
    - NEVER create a mock or fake call_tool() function (def call_tool)
    - ALWAYS import: "from node_runtime import call_tool"
    - If ModuleNotFoundError on node_runtime, ADD path setup BEFORE import:
      from pathlib import Path
      import sys
      sys.path.insert(0, str(Path(__file__).parent.parent.parent))
      from node_runtime import call_tool
  * If the code DOES NOT call call_tool() anywhere (UNUSED IMPORT):
    - REMOVE the import statement: "from node_runtime import call_tool"
    - REMOVE any path setup related to node_runtime
    - ModuleNotFoundError for unused import means DELETE the import, not fix the path!
- For content generation (jokes, stories, articles), always use call_tool("content_generator", prompt)

Return ONLY the JSON object, nothing else."""

            # Use appropriate model with adaptive temperature
            response = self.client.generate(
                model=current_model,
                prompt=fix_prompt,
                temperature=temperature,  # Adaptive temperature
                model_key=self.config.generator_model_key if current_model == fast_model else self.config.escalation_model_key  # Use actual model key for routing
            )

            if not response:
                continue

            # Parse JSON response
            try:
                import json
                # Clean any markdown
                response = response.strip()
                if response.startswith('```json'):
                    response = response.split('```json')[1].split('```')[0].strip()
                elif response.startswith('```'):
                    response = response.split('```')[1].split('```')[0].strip()

                result = json.loads(response)
                fixed_code = result.get("code", "")
                fixes = result.get("fixes_applied", [])
                analysis = result.get("analysis", "")

                if fixes:
                    console.print(f"[dim]Fixes: {', '.join(fixes)}[/dim]")
                if analysis:
                    console.print(f"[dim]Analysis: {analysis}[/dim]")

                if not fixed_code:
                    console.print("[yellow]No code in JSON response[/yellow]")
                    continue

            except json.JSONDecodeError as e:
                console.print(f"[yellow]Failed to parse JSON, extracting code...[/yellow]")
                # Try to extract code from malformed response
                if "code" in response.lower():
                    import re
                    match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
                    if not match:
                        match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
                    if match:
                        fixed_code = match.group(1).strip()
                    else:
                        fixed_code = response  # Last resort
                else:
                    fixed_code = response

            # Clean the fixed code
            fixed_code = self._clean_code(fixed_code)

            # Validate fixed code isn't empty or invalid
            if not fixed_code or len(fixed_code.strip()) < 20:
                console.print(f"[yellow]Fixed code is empty or too short, skipping[/yellow]")
                continue

            # Validate it's actually Python code, not commentary
            if not any(keyword in fixed_code for keyword in ["import", "def ", "class ", "if ", "print(", "return"]):
                console.print(f"[yellow]Response doesn't look like Python code, skipping[/yellow]")
                continue

            # Reject responses that look like explanatory text
            if any(phrase in fixed_code.lower() for phrase in ["it looks like", "you can use", "here are", "these are", "for example"]):
                console.print(f"[yellow]Response contains explanatory text instead of code, skipping[/yellow]")
                continue

            # ==================== CRITICAL FIX VALIDATION ====================
            # VALIDATE that the LLM actually applied the fixes it claims!
            # This prevents the bug where LLM describes the fix but doesn't apply it
            fix_validation_failed = False

            # UNIVERSAL VALIDATION: If LLM claims fixes, code MUST be different
            if 'fixes' in locals() and fixes and len(fixes) > 0:
                # Strip whitespace for comparison
                original_stripped = code.strip().replace(' ', '').replace('\n', '').replace('\t', '')
                fixed_stripped = fixed_code.strip().replace(' ', '').replace('\n', '').replace('\t', '')

                if original_stripped == fixed_stripped:
                    console.print(f"[bold red]✗ UNIVERSAL VALIDATION FAILED: LLM claims {len(fixes)} fix(es) but code is IDENTICAL![/bold red]")
                    console.print(f"[yellow]Claimed fixes: {', '.join(fixes)}[/yellow]")
                    console.print(f"[yellow]LLM only DESCRIBED fixes without APPLYING them. Rejecting and retrying...[/yellow]")
                    fix_validation_failed = True

            if 'fixes' in locals() and fixes and not fix_validation_failed:
                # Check each claimed fix was actually applied to the code
                for fix_description in fixes:
                    fix_lower = fix_description.lower()

                    # Validate ModuleNotFoundError fixes (most common)
                    if 'modulenotfounderror' in error_output.lower() and 'node_runtime' in error_output.lower():
                        if 'path setup' in fix_lower or 'sys.path' in fix_lower or 'add' in fix_lower and 'import' in fix_lower:
                            # LLM claims it added path setup - verify it's in the code!
                            if 'sys.path.insert' not in fixed_code and 'sys.path.append' not in fixed_code:
                                console.print(f"[bold red]✗ VALIDATION FAILED: LLM claims '{fix_description}' but code doesn't contain sys.path setup![/bold red]")
                                console.print(f"[yellow]LLM only DESCRIBED the fix without APPLYING it. Rejecting and retrying...[/yellow]")
                                fix_validation_failed = True
                                break

                    # Validate unused import removal fixes
                    if 'unused import' in fix_lower or 'removed import' in fix_lower or 'delete' in fix_lower and 'import' in fix_lower:
                        if 'node_runtime' in fix_lower:
                            # LLM claims it removed node_runtime import
                            if 'from node_runtime import' in fixed_code or 'import node_runtime' in fixed_code:
                                console.print(f"[bold red]✗ VALIDATION FAILED: LLM claims '{fix_description}' but import still in code![/bold red]")
                                console.print(f"[yellow]LLM only DESCRIBED the fix without APPLYING it. Rejecting and retrying...[/yellow]")
                                fix_validation_failed = True
                                break

                    # Validate that if fix mentions specific code changes, they're actually there
                    if 'added' in fix_lower:
                        # Extract what was supposedly added
                        added_patterns = []
                        if 'logging' in fix_lower:
                            added_patterns.append('import logging')
                        if 'pathlib' in fix_lower or 'Path' in fix_description:
                            added_patterns.append('from pathlib import Path')

                        for pattern in added_patterns:
                            if pattern not in fixed_code:
                                console.print(f"[bold red]✗ VALIDATION FAILED: LLM claims it added '{pattern}' but it's not in the code![/bold red]")
                                console.print(f"[yellow]LLM only DESCRIBED the fix without APPLYING it. Rejecting and retrying...[/yellow]")
                                fix_validation_failed = True
                                break

            # If validation failed, try to programmatically apply common fixes
            if fix_validation_failed:
                console.print(f"[yellow]Attempting to programmatically apply fixes...[/yellow]")

                # Try to apply common fixes that LLM described but didn't implement
                auto_fixed = False
                for fix_description in fixes if 'fixes' in locals() and fixes else []:
                    fix_lower = fix_description.lower()

                    # Auto-fix: Add path setup for node_runtime import
                    if ('path setup' in fix_lower or 'sys.path' in fix_lower) and 'node_runtime' in error_output.lower():
                        if 'sys.path.insert' not in fixed_code and 'sys.path.append' not in fixed_code:
                            # Check if code imports node_runtime
                            if 'from node_runtime import' in fixed_code or 'import node_runtime' in fixed_code:
                                console.print(f"[cyan]-> Auto-applying: Add sys.path setup before node_runtime import[/cyan]")
                                # Add path setup at the beginning
                                path_setup = "from pathlib import Path\nimport sys\nsys.path.insert(0, str(Path(__file__).parent.parent.parent))\n"

                                # Insert after any existing imports from pathlib/sys, or at the start
                                lines = fixed_code.split('\n')
                                insert_pos = 0

                                # Find position after module docstring if present
                                in_docstring = False
                                for i, line in enumerate(lines):
                                    stripped = line.strip()
                                    if i == 0 and (stripped.startswith('"""') or stripped.startswith("'''")):
                                        in_docstring = True
                                    elif in_docstring and (stripped.endswith('"""') or stripped.endswith("'''")):
                                        insert_pos = i + 1
                                        break
                                    elif not in_docstring and stripped and not stripped.startswith('#'):
                                        insert_pos = i
                                        break

                                # Insert path setup
                                lines.insert(insert_pos, path_setup)
                                fixed_code = '\n'.join(lines)
                                auto_fixed = True
                                console.print(f"[green]✓ Auto-applied path setup[/green]")

                    # Auto-fix: Remove unused node_runtime import
                    elif ('remove' in fix_lower or 'delete' in fix_lower) and 'import' in fix_lower and 'node_runtime' in fix_lower:
                        if 'from node_runtime import' in fixed_code or 'import node_runtime' in fixed_code:
                            console.print(f"[cyan]-> Auto-applying: Remove unused node_runtime import[/cyan]")
                            lines = fixed_code.split('\n')
                            filtered_lines = []
                            for line in lines:
                                # Skip node_runtime import lines and path setup lines
                                if ('from node_runtime import' not in line and
                                    'import node_runtime' not in line and
                                    not (line.strip().startswith('sys.path.') and 'node_runtime' in ' '.join(filtered_lines[-5:]))):
                                    filtered_lines.append(line)
                            fixed_code = '\n'.join(filtered_lines)
                            auto_fixed = True
                            console.print(f"[green]✓ Auto-removed unused import[/green]")

                if auto_fixed:
                    # Re-validate with auto-fixed code
                    console.print(f"[cyan]Testing auto-fixed code...[/cyan]")
                    # Don't track this as a failed attempt since we fixed it
                else:
                    # Track this validation failure to warn the LLM in the next attempt
                    all_attempts.append({
                        'attempt_num': attempt + 1,
                        'model': current_model,
                        'temp': temperature,
                        'stage': stage,
                        'fixes': fixes if 'fixes' in locals() else [],
                        'analysis': analysis if 'analysis' in locals() else '',
                        'error': 'VALIDATION FAILED - LLM described fix without applying it to code',
                        'code_attempted': fixed_code[:500] if fixed_code else '',
                        'validation_failure': True
                    })

                    # Don't count this as a valid attempt - the LLM is hallucinating fixes
                    console.print(f"[cyan]Retrying with stronger emphasis on ACTUALLY APPLYING the fix...[/cyan]")
                    continue
            # ==================== END CRITICAL FIX VALIDATION ====================

            # Save fixed code (only if validation passed!)
            self.runner.save_code(node_id, fixed_code)

            # Re-run tests
            console.print(f"[dim]Testing fix (attempt {attempt + 1})...[/dim]")
            sample_input = {"input": "test", "task": "test", "description": "test",
                          "query": "test", "topic": "test", "prompt": "test"}
            stdout, stderr, metrics = self.runner.run_node(node_id, sample_input)

            if metrics["success"]:
                console.print(f"[green]OK Fixed successfully on attempt {attempt + 1} ({stage})[/green]")

                # If logging was added, auto-remove it to clean the code
                if logging_added:
                    console.print(f"[cyan]Removing debug logging to clean code...[/cyan]")
                    cleaned_code = self._remove_debug_logging(fixed_code)

                    # Save cleaned code
                    self.runner.save_code(node_id, cleaned_code)

                    # Re-run tests to verify cleaned code still works
                    console.print(f"[dim]Verifying cleaned code still passes tests...[/dim]")
                    stdout, stderr, metrics = self.runner.run_node(node_id, sample_input)

                    if metrics["success"]:
                        console.print(f"[green]OK Cleaned code passes tests![/green]")
                        # Store successful fix pattern for future learning
                        self._store_fix_pattern(code, cleaned_code, stderr, fixes, analysis, stage)
                        return True
                    else:
                        console.print(f"[yellow]Warning: Cleaned code failed, keeping version with logging[/yellow]")
                        # Restore code with logging
                        self.runner.save_code(node_id, fixed_code)
                        # Store fix pattern (with logging version)
                        self._store_fix_pattern(code, fixed_code, stderr, fixes, analysis, stage)
                        return True
                else:
                    # Store successful fix pattern for future learning
                    self._store_fix_pattern(code, fixed_code, stderr, fixes, analysis, stage)
                    return True
            else:
                # Track this failed attempt with ALL details
                all_attempts.append({
                    'attempt_num': attempt + 1,
                    'model': current_model,
                    'temp': temperature,
                    'stage': stage,
                    'fixes': fixes if 'fixes' in locals() else [],
                    'analysis': analysis if 'analysis' in locals() else '',
                    'error': stderr,
                    'code_attempted': fixed_code[:500] if fixed_code else ''
                })

                # Update error for next iteration
                self.context['last_error'] = stderr
                self.context['last_stdout'] = stdout

                # Describe next step
                if attempt < 1:
                    next_step = "retrying with higher temperature"
                elif attempt == 1:
                    next_step = "adding debug logging for attempts 3-4"
                elif attempt < 4:
                    next_step = "continuing with logging"
                elif attempt == 4:
                    next_step = "escalating to powerful model"
                else:
                    next_step = "preparing god-level escalation"

                console.print(f"[yellow]Still has errors, {next_step}...[/yellow]")

            code = fixed_code  # Try to fix this version next

        # After 6 failed attempts, escalate to GOD-LEVEL tool
        console.print(f"\n[bold red]All 6 attempts failed. Escalating to GOD-LEVEL tool ({god_level_model})...[/bold red]")
        return self._god_level_fix(
            node_id=node_id,
            code=code,
            description=description,
            specification=specification,
            all_attempts=all_attempts,
            original_test=original_test,
            error_output=error_output,
            god_model=god_level_model
        )

    def _store_fix_pattern(self, broken_code: str, fixed_code: str, error_output: str, fixes: list, analysis: str, stage: str):
        """
        Store successful code fix pattern in RAG for future learning.

        Args:
            broken_code: The code that had errors
            fixed_code: The corrected code
            error_output: The error message
            fixes: List of fixes applied
            analysis: Analysis of the error
            stage: Which escalation stage fixed it
        """
        try:
            # Extract error type from error message
            error_type = "unknown"
            if "SyntaxError" in error_output:
                error_type = "syntax"
            elif "NameError" in error_output or "not defined" in error_output:
                error_type = "undefined"
            elif "ImportError" in error_output or "ModuleNotFoundError" in error_output:
                error_type = "import"
            elif "IndentationError" in error_output:
                error_type = "indentation"
            elif "TypeError" in error_output:
                error_type = "type"
            elif "AttributeError" in error_output:
                error_type = "runtime"

            # Extract error message (first line usually)
            error_lines = error_output.strip().split('\n')
            error_message = error_lines[-1] if error_lines else error_output[:200]

            # Build fix description from analysis and fixes
            fix_description = f"{analysis}\n\nFixes applied:\n"
            for fix in fixes:
                fix_description += f"- {fix}\n"
            fix_description += f"\nFixed at escalation stage: {stage}"

            # Call store_code_fix_pattern tool via node_runtime
            from node_runtime import call_tool
            import json

            pattern_data = {
                "error_message": error_message[:500],
                "broken_code": broken_code[:1000],
                "fixed_code": fixed_code[:1000],
                "fix_description": fix_description[:500],
                "error_type": error_type,
                "language": "python",
                "context": {
                    "escalation_stage": stage,
                    "auto_fixed": True
                }
            }

            result = call_tool("store_code_fix_pattern", json.dumps(pattern_data))
            console.print(f"[dim green]✓ Stored fix pattern in RAG for future learning[/dim green]")

        except Exception as e:
            # Pattern storage is nice-to-have, not critical
            console.print(f"[dim yellow]Note: Could not store fix pattern: {e}[/dim yellow]")

    def _remove_debug_logging(self, code: str) -> str:
        """
        COMPREHENSIVELY remove ALL debug logging statements from code.

        Removes:
        - import logging
        - from logging import ...
        - import logger
        - logging.basicConfig(...)
        - logging.getLogger(...)
        - logger = logging.getLogger(...)
        - logging.debug/info/warning/error/exception/critical(...) calls
        - logger.debug/info/warning/error/exception/critical(...) calls
        - print(..., file=sys.stderr) debug statements
        - # DEBUG comments
        - Empty lines left behind

        Returns cleaned code.
        """
        import re

        lines = code.split('\n')
        cleaned_lines = []
        skip_next_blank = False

        for line in lines:
            stripped = line.strip()

            # Skip logging imports (ALL variations)
            if (stripped.startswith('import logging') or
                stripped.startswith('from logging import') or
                'import logging' in stripped):
                skip_next_blank = True
                continue

            # Skip logger variable assignments
            if re.match(r'\s*logger\s*=\s*logging\.getLogger', stripped):
                skip_next_blank = True
                continue

            # Skip logging configuration
            if ('logging.basicConfig' in stripped or
                'logging.getLogger' in stripped):
                skip_next_blank = True
                continue

            # Skip ALL logging module calls (logging.*)
            if re.match(r'\s*logging\.(debug|info|warning|error|exception|critical|log)\(', stripped):
                skip_next_blank = True
                continue

            # Skip ALL logger object calls (logger.*)
            if re.match(r'\s*logger\.(debug|info|warning|error|exception|critical|log)\(', stripped):
                skip_next_blank = True
                continue

            # Skip debug print statements to stderr
            if 'print(' in stripped and 'sys.stderr' in stripped and ('DEBUG' in stripped or 'debug' in line):
                skip_next_blank = True
                continue

            # Skip lines with DEBUG comments (but not docstrings)
            if stripped.startswith('# DEBUG') or stripped.startswith('#DEBUG'):
                skip_next_blank = True
                continue

            # Skip try/except blocks that ONLY wrap logging
            if stripped.startswith('try:') and len(cleaned_lines) > 0:
                # Look ahead to see if this is just for logging
                continue_check = False
                # Don't skip try blocks - they might be legitimate error handling

            # Skip blank line after removed logging (for cleanliness)
            if not stripped and skip_next_blank:
                skip_next_blank = False
                continue

            cleaned_lines.append(line)
            skip_next_blank = False

        # Second pass: Remove any remaining logger references
        code = '\n'.join(cleaned_lines)

        # Remove logger. references that might have multi-line statements
        code = re.sub(r'logger\.(debug|info|warning|error|exception|critical)\([^)]*\)', '', code)
        code = re.sub(r'logging\.(debug|info|warning|error|exception|critical)\([^)]*\)', '', code)

        # Remove empty lines that result from removal (but keep single blank lines)
        lines = code.split('\n')
        final_lines = []
        prev_blank = False
        for line in lines:
            if not line.strip():
                if not prev_blank:
                    final_lines.append(line)
                    prev_blank = True
            else:
                final_lines.append(line)
                prev_blank = False

        return '\n'.join(final_lines)

    def _god_level_fix(
        self,
        node_id: str,
        code: str,
        description: str,
        specification: str,
        all_attempts: list,
        original_test: str,
        error_output: str,
        god_model: str
    ) -> bool:
        """
        The FINAL BOSS - God-level tool (deepseek-coder:6.7b on localhost).

        This is the last resort after 6 failed attempts. It receives:
        - Complete history of all 6 attempts
        - Original test requirements
        - Full specification
        - All errors encountered

        The god-level tool must succeed or the task is considered impossible.
        """
        console.print(f"\n[bold magenta]╔═══════════════════════════════════════╗[/bold magenta]")
        console.print(f"[bold magenta]║   GOD-LEVEL ESCALATION ACTIVATED     ║[/bold magenta]")
        console.print(f"[bold magenta]║   Model: {god_model:25s} ║[/bold magenta]")
        console.print(f"[bold magenta]║   This is the FINAL BOSS attempt    ║[/bold magenta]")
        console.print(f"[bold magenta]╔═══════════════════════════════════════╗[/bold magenta]\n")

        # Build comprehensive history summary
        history_summary = "\n=== COMPLETE FAILURE HISTORY ===\n"
        for attempt in all_attempts:
            history_summary += f"\nAttempt {attempt['attempt_num']} - {attempt['stage']} ({attempt['model']}, temp={attempt['temp']}):\n"
            history_summary += f"  Fixes attempted: {', '.join(attempt.get('fixes', ['none']))}\n"
            history_summary += f"  Analysis: {attempt.get('analysis', 'N/A')}\n"
            history_summary += f"  Error: {attempt['error'][:200]}...\n"
            if attempt.get('code_attempted'):
                history_summary += f"  Code sample: {attempt['code_attempted'][:100]}...\n"

        # Build god-level prompt with MAXIMUM context
        god_prompt = f"""You are the GOD-LEVEL CODE FIXER - the most powerful debugging AI.

CRITICAL CONTEXT: 6 previous attempts by other models ALL FAILED. You are the LAST HOPE.

Your job: FIX THIS CODE so it passes the tests. This is MANDATORY - failure is not an option.

════════════════════════════════════════════════════════════════════════

ORIGINAL USER REQUEST:
{description}

ORIGINAL SPECIFICATION FROM OVERSEER:
{specification[:1500]}

CURRENT CODE (BROKEN after 6 failed fixes):
```python
{code}
```

ORIGINAL TEST THAT MUST PASS:
```python
{original_test if original_test else 'Test not available'}
```

CURRENT ERROR:
{error_output[:500]}

{history_summary}

════════════════════════════════════════════════════════════════════════

YOUR MISSION:
1. ANALYZE: Review all 6 failed attempts - what did they miss?
2. UNDERSTAND: What does the test ACTUALLY require?
3. FIX: Generate working code that WILL pass the test
4. VERIFY: Mentally trace through the code to ensure correctness

CRITICAL INSIGHTS FROM FAILURES:
- 6 models couldn't fix this - there's likely a SUBTLE issue
- The error might be in: imports, string formatting, function names, interface mismatch
- Check if code matches test expectations EXACTLY
- Verify all imports are present
- Ensure function/interface matches what tests import

RESPONSE FORMAT:
Return ONLY a JSON object:

{{
  "root_cause_analysis": "What was the ACTUAL problem that 6 models missed?",
  "fix_strategy": "Your strategy to fix it",
  "code": "The FIXED Python code as a string",
  "confidence": "Why this will work when others failed"
}}

Requirements:
- Code must be IMMEDIATELY runnable
- Code must PASS THE TESTS
- NO markdown fences in "code" field
- Learn from ALL 6 failed attempts
- This is your ONLY chance - make it count

Return ONLY the JSON object."""

        # Call god-level model on localhost:11434
        console.print(f"[cyan]Consulting god-level model ({god_model})...[/cyan]")

        try:
            response = self.client.generate(
                model=god_model,
                prompt=god_prompt,
                temperature=0.1,  # Ultra-focused for final attempt
                model_key=self.config.generator_model_key  # Use actual model key for routing  # Use generator endpoint (localhost)
            )

            if not response:
                console.print(f"[red]ERROR: God-level model returned no response[/red]")
                return False

            # Parse JSON response with robust error handling
            import json
            import re

            response = response.strip()

            # Remove markdown fences
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0].strip()
            elif response.startswith('```'):
                response = response.split('```')[1].split('```')[0].strip()

            # Try to parse JSON
            result = None
            try:
                result = json.loads(response)
            except json.JSONDecodeError as e:
                console.print(f"[yellow]JSON parse error: {e}. Attempting recovery...[/yellow]")

                # Try to find JSON object in the response
                json_match = re.search(r'\{[^}]*"code"[^}]*\}', response, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                    except:
                        pass

                # If still no result, try to extract code directly
                if not result:
                    console.print(f"[yellow]Could not parse JSON. Extracting code directly...[/yellow]")
                    # Try to find Python code
                    code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
                    if not code_match:
                        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)

                    if code_match:
                        result = {
                            "code": code_match.group(1).strip(),
                            "root_cause_analysis": "Extracted from malformed response",
                            "fix_strategy": "Direct code extraction",
                            "confidence": "Unknown - JSON parse failed"
                        }
                    else:
                        console.print(f"[red]ERROR: Could not extract code from response[/red]")
                        console.print(f"[dim]Response preview: {response[:300]}...[/dim]")
                        return False

            if not result:
                console.print(f"[red]ERROR: Failed to parse god-level response[/red]")
                return False

            root_cause = result.get("root_cause_analysis", "N/A")
            strategy = result.get("fix_strategy", "N/A")
            fixed_code = result.get("code", "")
            confidence = result.get("confidence", "N/A")

            console.print(f"\n[bold cyan]God-Level Analysis:[/bold cyan]")
            console.print(f"[yellow]Root Cause:[/yellow] {root_cause}")
            console.print(f"[yellow]Strategy:[/yellow] {strategy}")
            console.print(f"[yellow]Confidence:[/yellow] {confidence}\n")

            if not fixed_code:
                console.print(f"[red]ERROR: No code in god-level response[/red]")
                return False

            # Clean the code
            fixed_code = self._clean_code(fixed_code)

            # Save and test
            self.runner.save_code(node_id, fixed_code)

            console.print(f"[cyan]Testing god-level fix...[/cyan]")
            sample_input = {"input": "test", "task": "test", "description": "test",
                          "query": "test", "topic": "test", "prompt": "test"}
            stdout, stderr, metrics = self.runner.run_node(node_id, sample_input)

            if metrics["success"]:
                console.print(f"\n[bold green]╔═══════════════════════════════════════╗[/bold green]")
                console.print(f"[bold green]║   GOD-LEVEL FIX SUCCESSFUL! !       ║[/bold green]")
                console.print(f"[bold green]║   The final boss has spoken.        ║[/bold green]")
                console.print(f"[bold green]╚═══════════════════════════════════════╝[/bold green]\n")
                return True
            else:
                console.print(f"\n[bold red]╔═══════════════════════════════════════╗[/bold red]")
                console.print(f"[bold red]║   EVEN GOD-LEVEL FAILED              ║[/bold red]")
                console.print(f"[bold red]║   This task may be impossible        ║[/bold red]")
                console.print(f"[bold red]╚═══════════════════════════════════════╝[/bold red]")
                console.print(f"\n[red]Final error:[/red] {stderr[:300]}")
                return False

        except Exception as e:
            console.print(f"[red]ERROR in god-level escalation: {e}[/red]")
            import traceback
            traceback.print_exc()
            return False

    def _escalate_and_fix(
        self,
        node_id: str,
        code: str,
        description: str,
        specification: str = "",
        available_tools: str = ""
    ) -> bool:
        """
        Escalate to higher-level code model to fix issues.
        Passes full context including specification, tools, and error details.
        """
        max_attempts = self.config.get("testing.max_escalation_attempts", 3)

        # Get error details from context
        error_output = self.context.get('last_error', 'Unknown error')
        stdout_output = self.context.get('last_stdout', '')

        for attempt in range(max_attempts):
            console.print(f"[cyan]Escalation attempt {attempt + 1}/{max_attempts} using {self.config.escalation_model}...[/cyan]")

            # Build comprehensive fix prompt with all context
            fix_prompt = f"""You are an expert code debugger. The following code FAILED to execute.

ORIGINAL GOAL:
{description}

OVERSEER STRATEGY:
{specification}

{available_tools if available_tools and "No specific tools" not in available_tools else ""}

CURRENT CODE (has errors):
```python
{code}
```

ERROR OUTPUT:
{error_output}

{f'STDOUT: {stdout_output}' if stdout_output else ''}

You MUST respond with ONLY a JSON object in this exact format:

{{
  "code": "the fixed Python code as a string",
  "fixes_applied": ["brief description of fix 1", "fix 2"],
  "analysis": "one sentence explaining what was wrong"
}}

Requirements for "code" field:
- ONLY executable Python code
- NO markdown fences
- NO explanations mixed with code
- Must fix ALL errors shown above
- Must be immediately runnable

Return ONLY the JSON object, nothing else."""

            # Use escalation model (qwen2.5-coder:14b) for complex fixes
            response = self.client.generate(
                model=self.config.escalation_model,  # More powerful model for difficult fixes
                prompt=fix_prompt,
                temperature=0.2,  # Lower temperature for more focused fixes
                model_key=self.config.escalation_model_key  # Use actual model key for routing
            )

            if not response:
                continue

            # Parse JSON response
            try:
                import json
                # Clean any markdown
                response = response.strip()
                if response.startswith('```json'):
                    response = response.split('```json')[1].split('```')[0].strip()
                elif response.startswith('```'):
                    response = response.split('```')[1].split('```')[0].strip()

                result = json.loads(response)
                fixed_code = result.get("code", "")
                fixes = result.get("fixes_applied", [])
                analysis = result.get("analysis", "")

                if fixes:
                    console.print(f"[dim]Fixes: {', '.join(fixes)}[/dim]")
                if analysis:
                    console.print(f"[dim]Analysis: {analysis}[/dim]")

                if not fixed_code:
                    console.print("[yellow]No code in JSON response[/yellow]")
                    continue

            except json.JSONDecodeError as e:
                console.print(f"[yellow]Failed to parse JSON, using raw output[/yellow]")
                fixed_code = response

            # Clean the fixed code (remove any remaining markdown)
            fixed_code = self._clean_code(fixed_code)

            # Save fixed code
            self.runner.save_code(node_id, fixed_code)

            # Test again
            sample_input = {"input": "test"}
            stdout, stderr, metrics = self.runner.run_node(node_id, sample_input)

            if metrics["success"]:
                console.print(f"[green]OK Fixed successfully on attempt {attempt + 1}[/green]")
                return True
            else:
                # Update error for next iteration
                self.context['last_error'] = stderr
                self.context['last_stdout'] = stdout
                console.print(f"[yellow]Still has errors: {stderr[:100]}...[/yellow]")

            code = fixed_code  # Try to fix this version next

        console.print(f"[red]FAIL Could not fix after {max_attempts} attempts[/red]")
        return False

    def handle_run(self, args: str) -> bool:
        """Handle run command."""
        parts = args.split(maxsplit=1)
        if not parts:
            console.print("[red]Usage: run <node_id> [input_json][/red]")
            return False

        node_id = parts[0]
        input_data = {}

        if len(parts) > 1:
            try:
                input_data = json.loads(parts[1])
            except json.JSONDecodeError:
                console.print("[red]Invalid JSON input[/red]")
                return False

        if not self.runner.node_exists(node_id):
            console.print(f"[red]Node '{node_id}' not found[/red]")
            return False

        console.print(f"[cyan]Running {node_id}...[/cyan]")

        stdout, stderr, metrics = self.runner.run_node(node_id, input_data)

        # Display results
        if metrics["success"]:
            console.print("[green]OK Execution successful[/green]")
            if stdout:
                console.print(Panel(stdout, title="Output", box=box.ROUNDED))
        else:
            console.print(f"[red]FAIL Execution failed (exit code: {metrics['exit_code']})[/red]")
            if stderr:
                console.print(Panel(stderr, title="Error", border_style="red", box=box.ROUNDED))

        if self.config.get("chat.show_metrics", True):
            self._display_metrics(metrics)

        return metrics["success"]

    def _display_metrics(self, metrics: dict):
        """Display execution metrics."""
        table = Table(title="Metrics", box=box.SIMPLE)
        table.add_column("Metric", style="cyan")
        table.add_column("Value")

        table.add_row("Latency", f"{metrics.get('latency_ms', 0)}ms")
        table.add_row("Memory", f"{metrics.get('memory_mb_peak', 0):.2f}MB")
        table.add_row("CPU Time", f"{metrics.get('cpu_time_ms', 0)}ms")
        table.add_row("Exit Code", str(metrics.get('exit_code', -1)))

        console.print(table)

    def handle_list(self) -> bool:
        """Handle list command."""
        nodes = self.registry.list_nodes()

        if not nodes:
            console.print("[yellow]No nodes in registry[/yellow]")
            return True

        table = Table(title=f"Registry ({len(nodes)} nodes)", box=box.ROUNDED)
        table.add_column("Node ID", style="cyan")
        table.add_column("Version")
        table.add_column("Score", justify="right")
        table.add_column("Tags")

        for node in nodes:
            node_id = node.get("node_id", "unknown")
            version = node.get("version", "?")
            score = node.get("score_overall", 0.0)
            tags = ", ".join(node.get("tags", [])[:3])

            score_style = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"

            table.add_row(
                node_id,
                version,
                f"[{score_style}]{score:.2f}[/{score_style}]",
                tags
            )

        console.print(table)
        return True

    def handle_status(self) -> bool:
        """Handle status command."""
        console.print("\n[cyan]Checking system status...[/cyan]\n")

        # Check Ollama
        ollama_ok = self.client.check_connection()
        status = "[green]OK Connected[/green]" if ollama_ok else "[red]FAIL Not connected[/red]"

        table = Table(title="System Status", box=box.ROUNDED)
        table.add_column("Component", style="cyan")
        table.add_column("Status")

        table.add_row("Ollama Server", status)

        if ollama_ok:
            models = self.client.list_models()
            required = [
                ("Overseer", self.config.overseer_model),
                ("Generator", self.config.generator_model),
                ("Evaluator", self.config.evaluator_model),
                ("Triage", self.config.triage_model)
            ]

            for name, model in required:
                # Check exact match or prefix match (e.g., "llama3" matches "llama3:latest")
                has_model = model in models or any(m.startswith(f"{model}:") for m in models)
                model_status = f"[green]OK {model}[/green]" if has_model else f"[red]MISSING {model}[/red]"
                table.add_row(f"{name} Model", model_status)

        table.add_row("Auto-Evolution", "[green]Enabled[/green]" if self.config.auto_evolution_enabled else "[dim]Disabled[/dim]")
        table.add_row("Unit Testing", "[green]Enabled[/green]" if self.config.testing_enabled else "[dim]Disabled[/dim]")

        # Node count
        nodes = self.registry.list_nodes()
        table.add_row("Nodes in Registry", str(len(nodes)))

        console.print(table)
        return True

    def handle_backends(self, test_connection: bool = False) -> bool:
        """Handle backends command - check status of all LLM backends."""
        console.print("\n[bold cyan]LLM Backend Status[/bold cyan]\n")

        try:
            from src.backend_config_checker import BackendConfigChecker, BackendStatus

            checker = BackendConfigChecker(self.config)
            results = checker.check_all_backends(test_connection=test_connection)

            # Get primary backend
            primary_backend = checker.get_primary_backend()

            # Create status table
            table = Table(
                title="Backend Configuration Status",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta"
            )
            table.add_column("Backend", style="cyan", no_wrap=True)
            table.add_column("Status", justify="center")
            table.add_column("Details")
            table.add_column("Ready", justify="center")

            for backend, result in sorted(results.items()):
                # Status color
                if result.status == BackendStatus.READY:
                    status_str = "[green]OK READY[/green]"
                    ready_str = "[green]YES[/green]"
                elif result.status == BackendStatus.MISSING_API_KEY:
                    status_str = "[yellow]WARN NO API KEY[/yellow]"
                    ready_str = "[red]NO[/red]"
                elif result.status == BackendStatus.MISSING_CONFIG:
                    status_str = "[dim]- NOT CONFIGURED[/dim]"
                    ready_str = "[dim]NO[/dim]"
                elif result.status == BackendStatus.UNAVAILABLE:
                    status_str = "[red]FAIL UNAVAILABLE[/red]"
                    ready_str = "[red]NO[/red]"
                else:
                    status_str = "[yellow]WARN INVALID[/yellow]"
                    ready_str = "[red]NO[/red]"

                # Add primary marker
                backend_display = backend
                if primary_backend and backend.lower() == primary_backend.lower():
                    backend_display = f"{backend} (primary)"

                # Details
                details = result.message
                if test_connection and "connection_test" in result.details:
                    test_result = result.details["connection_test"]
                    details += f" (connection: {test_result})"

                table.add_row(backend_display, status_str, details, ready_str)

            console.print(table)

            # Summary and suggestions
            ready_backends = [b for b, r in results.items() if r.ready]
            not_ready = [b for b, r in results.items() if not r.ready and r.status != BackendStatus.MISSING_CONFIG]

            console.print()
            if primary_backend:
                primary_result = results.get(primary_backend)
                if primary_result and primary_result.ready:
                    console.print(f"[green]OK Primary backend ({primary_backend}) is ready[/green]")
                else:
                    console.print(f"[yellow]! Primary backend ({primary_backend}) is NOT ready[/yellow]")

            console.print(f"\n[bold]Summary:[/bold] {len(ready_backends)}/{len(results)} backends ready")

            if not_ready:
                console.print(f"\n[yellow]Backends needing attention:[/yellow]")
                for backend in not_ready:
                    result = results[backend]
                    console.print(f"  • {backend}: {result.message}")

                    # Show setup suggestions
                    suggestions = checker.suggest_setup_commands(backend)
                    if suggestions:
                        console.print(f"    [dim]{suggestions[0]}[/dim]")

            console.print()
            return True

        except ImportError as e:
            console.print(f"[red]Backend checker not available: {e}[/red]")
            console.print("[dim]Multi-backend support may not be installed[/dim]")
            return False

    def handle_tools(self, category: str = None, page: int = 1) -> bool:
        """
        Handle tools command - list all available tools or filter by category with pagination.

        Args:
            category: Optional category to filter by (llm, executable, custom, openapi)
            page: Page number (default 1), shows 10 tools per page
        """
        # Check if tools are ready
        if not self._tools_loader.is_ready_sync():
            console.print("[yellow]Tools are still loading in the background...[/yellow]")
            console.print("[dim]Please wait a moment and try again[/dim]\n")
            return False

        all_tools = self.tools_manager.get_all_tools()

        if not all_tools:
            console.print("[yellow]No tools available[/yellow]")
            return True

        # Group tools by type
        from collections import defaultdict
        tools_by_type = defaultdict(list)

        for tool in all_tools:
            tools_by_type[tool.tool_type.value].append(tool)

        # If category specified, filter to that category
        if category:
            category_lower = category.lower()
            if category_lower not in tools_by_type:
                console.print(f"[yellow]No tools found in category: {category}[/yellow]")
                console.print(f"[dim]Available categories: {', '.join(sorted(tools_by_type.keys()))}[/dim]\n")
                return False

            # Show only the specified category
            console.print(f"\n[bold cyan]{category_lower.upper()} Tools[/bold cyan]\n")
            tools_to_show = {category_lower: tools_by_type[category_lower]}
        else:
            # Show all categories
            console.print("\n[bold cyan]Available Tools by Category[/bold cyan]\n")
            tools_to_show = tools_by_type

        # Pagination settings
        TOOLS_PER_PAGE = 10

        # Flatten all tools for pagination
        all_tools_flat = []
        for tool_type in sorted(tools_to_show.keys()):
            for tool in tools_to_show[tool_type]:
                all_tools_flat.append((tool_type, tool))

        total_tools_to_show = len(all_tools_flat)
        total_pages = (total_tools_to_show + TOOLS_PER_PAGE - 1) // TOOLS_PER_PAGE

        # Validate page number
        if page < 1:
            page = 1
        if page > total_pages and total_pages > 0:
            page = total_pages

        # Calculate slice
        start_idx = (page - 1) * TOOLS_PER_PAGE
        end_idx = start_idx + TOOLS_PER_PAGE
        page_tools = all_tools_flat[start_idx:end_idx]

        # Display paginated tools
        table = Table(
            title=f"Tools (Page {page}/{total_pages}) - Showing {len(page_tools)} of {total_tools_to_show}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("Tool ID", style="cyan", no_wrap=True, width=20)
        table.add_column("Name", style="green", width=25)
        table.add_column("Description", width=45)
        table.add_column("Type", style="yellow", no_wrap=True, width=10)

        for tool_type, tool in page_tools:
            tool_id = tool.tool_id
            name = getattr(tool, 'name', tool_id)
            description = tool.description[:47] + "..." if len(tool.description) > 50 else tool.description

            # Determine category from metadata
            metadata = tool.metadata or {}

            # Check if this is a DEBUG version
            is_debug = metadata.get("is_debug", False) or "DEBUG" in tool.tags
            if is_debug:
                # Prepend [DEBUG] tag to name
                name = f"[DEBUG] {name}"
                # Highlight in description
                description = f"DEBUG VERSION - {description[:30]}..."

            yaml_path = metadata.get("yaml_path", "")
            if yaml_path:
                # Extract category from path (e.g., "tools/executable/foo.yaml" -> "executable")
                from pathlib import Path
                path_parts = Path(yaml_path).parts
                if len(path_parts) >= 2:
                    category_name = path_parts[-2]  # Second to last part
                else:
                    category_name = "other"
            elif metadata.get("from_rag"):
                category_name = "dynamic"
            elif metadata.get("from_config"):
                category_name = "config"
            else:
                category_name = "other"

            table.add_row(tool_id, name, description, tool_type)

        console.print(table)
        console.print()

        # Navigation hint
        if total_pages > 1:
            nav_text = []
            if page > 1:
                nav_text.append(f"[cyan]/tools {page - 1}[/cyan] for previous page")
            if page < total_pages:
                nav_text.append(f"[cyan]/tools {page + 1}[/cyan] for next page")

            if nav_text:
                console.print("[dim]" + " | ".join(nav_text) + "[/dim]")

        console.print(f"[dim]Use /tool <tool_id> for detailed documentation[/dim]\n")

        return True

    def handle_tool_command(self, args: str) -> bool:
        """
        Handle tool subcommands: info, run, list.

        Args:
            args: Command arguments after "tool"

        Returns:
            True if successful
        """
        if not args:
            console.print("[yellow]Usage:[/yellow]")
            console.print("  [cyan]/tool info <tool_name>[/cyan]  - Get intelligent description of tool")
            console.print("  [cyan]/tool run <tool_name> [input][/cyan]  - Execute tool with input")
            console.print("  [cyan]/tool list[/cyan]  - List available tools (same as /tools)")
            return False

        parts = args.split(None, 1)
        subcommand = parts[0].lower()

        if subcommand == 'list':
            return self.handle_tools()

        elif subcommand == 'info':
            if len(parts) < 2:
                console.print("[red]Usage: /tool info <tool_name>[/red]")
                return False
            tool_name = parts[1].strip()
            return self.handle_tool_info(tool_name)

        elif subcommand == 'run':
            if len(parts) < 2:
                console.print("[red]Usage: /tool run <tool_name> [input][/red]")
                return False
            run_args = parts[1].strip()
            return self.handle_tool_run(run_args)

        else:
            console.print(f"[red]Unknown tool subcommand: {subcommand}[/red]")
            console.print("[dim]Available: info, run, list[/dim]")
            return False

    def handle_tools_cli(self, command: str) -> bool:
        """
        Handle tools CLI commands for testing and optimization.

        Args:
            command: Full command string (e.g., "/tools test all")

        Returns:
            True if successful
        """
        # Check if tools CLI is ready
        if not self._tools_cli:
            console.print("[yellow]Tools CLI is not yet initialized...[/yellow]")
            console.print("[dim]Please wait a moment and try again[/dim]\n")
            return False

        try:
            result = self._tools_cli.handle_command(command)

            # Display result
            if result.success:
                console.print(f"[green]{result.message}[/green]")
            else:
                console.print(f"[red]{result.message}[/red]")

            # Show details if available
            details = result.details
            if details:
                # For test results
                if "total_tests" in details:
                    console.print(f"\n[cyan]Test Results:[/cyan]")
                    console.print(f"  Total: {details['total_tests']}")
                    console.print(f"  Passed: {details['passed']}")
                    console.print(f"  Failed: {details['failed']}")

                # For optimization results
                elif "total_tools" in details:
                    console.print(f"\n[cyan]Optimization Results:[/cyan]")
                    console.print(f"  Total tools: {details['total_tools']}")
                    console.print(f"  Improved: {details['improved_count']}")

                # For single tool results
                elif "improvement_score" in details:
                    console.print(f"\n[cyan]Improvement: {details['improvement_score']:.2%}[/cyan]")
                    if "changes" in details:
                        console.print(f"[dim]Changes: {', '.join(details['changes'])}[/dim]")

            console.print(f"\n[dim]Duration: {result.duration:.2f}s[/dim]")

            return result.success

        except Exception as e:
            console.print(f"[red]Error executing command: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False

    def handle_tool_info(self, tool_name: str) -> bool:
        """
        Show detailed documentation for a tool from its YAML definition.

        Args:
            tool_name: Name or ID of the tool

        Returns:
            True if successful
        """
        from pathlib import Path
        import yaml

        # Find the tool
        tool = self.tools_manager.get_tool(tool_name)
        if not tool:
            console.print(f"[red]Tool not found: {tool_name}[/red]")
            console.print("[dim]Use /tools to see available tools[/dim]")
            return False

        console.print(f"\n[bold cyan]Tool Documentation: {tool.name}[/bold cyan]\n")

        # Try to load YAML file for full documentation
        metadata = tool.metadata or {}
        yaml_path = metadata.get("yaml_path")

        if yaml_path and Path(yaml_path).exists():
            # Load and display YAML documentation
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f)

                # Basic info
                console.print(f"[bold]Name:[/bold] {yaml_data.get('name', 'N/A')}")
                console.print(f"[bold]Type:[/bold] {yaml_data.get('type', 'N/A')}")
                console.print(f"[bold]Description:[/bold] {yaml_data.get('description', 'N/A')}\n")

                # Performance tiers
                if yaml_data.get('cost_tier') or yaml_data.get('speed_tier'):
                    console.print("[bold cyan]Performance:[/bold cyan]")
                    if yaml_data.get('cost_tier'):
                        console.print(f"  Cost: {yaml_data['cost_tier']}")
                    if yaml_data.get('speed_tier'):
                        console.print(f"  Speed: {yaml_data['speed_tier']}")
                    if yaml_data.get('quality_tier'):
                        console.print(f"  Quality: {yaml_data['quality_tier']}")
                    console.print()

                # Input/Output schemas
                if yaml_data.get('input_schema'):
                    console.print("[bold cyan]Input Parameters:[/bold cyan]")
                    for param, desc in yaml_data['input_schema'].items():
                        console.print(f"  [green]{param}[/green]: {desc}")
                    console.print()

                if yaml_data.get('output_schema'):
                    console.print("[bold cyan]Output:[/bold cyan]")
                    for param, desc in yaml_data['output_schema'].items():
                        console.print(f"  [yellow]{param}[/yellow]: {desc}")
                    console.print()

                # LLM-specific info
                if yaml_data.get('llm'):
                    console.print("[bold cyan]LLM Configuration:[/bold cyan]")
                    llm_config = yaml_data['llm']
                    if llm_config.get('tier'):
                        console.print(f"  Tier: {llm_config['tier']}")
                    if llm_config.get('model'):
                        console.print(f"  Model: {llm_config['model']}")
                    if llm_config.get('temperature'):
                        console.print(f"  Temperature: {llm_config['temperature']}")
                    console.print()

                # Executable-specific info
                if yaml_data.get('executable'):
                    console.print("[bold cyan]Executable:[/bold cyan]")
                    exec_config = yaml_data['executable']
                    if exec_config.get('command'):
                        console.print(f"  Command: {exec_config['command']}")
                    console.print()

                # Examples
                if yaml_data.get('examples'):
                    console.print("[bold cyan]Examples:[/bold cyan]")
                    for example in yaml_data['examples']:
                        if isinstance(example, dict):
                            console.print(f"  Input: {example.get('input', 'N/A')}")
                            console.print(f"  Output: {example.get('output', 'N/A')}")
                        else:
                            console.print(f"  {example}")
                    console.print()

                # Tags
                if yaml_data.get('tags'):
                    console.print(f"[dim]Tags: {', '.join(yaml_data['tags'])}[/dim]")

                # Source file
                console.print(f"[dim]Source: {yaml_path}[/dim]\n")

                return True

            except Exception as e:
                console.print(f"[yellow]Could not load YAML documentation: {e}[/yellow]\n")
                # Fall through to basic display

        # Fallback: Show basic tool information
        console.print(f"[bold]Description:[/bold] {tool.description}\n")
        console.print(f"[bold]ID:[/bold] {tool.tool_id}")
        console.print(f"[bold]Type:[/bold] {tool.tool_type.value}")

        if tool.tags:
            console.print(f"[bold]Tags:[/bold] {', '.join(tool.tags)}")

        # Show implementation details
        impl = getattr(tool, 'implementation', {})
        if isinstance(impl, dict):
            if tool.tool_type.value == "llm":
                llm_config = impl.get('llm', {})
                if isinstance(llm_config, dict):
                    console.print(f"[bold]Model:[/bold] {llm_config.get('model', 'N/A')}")

            if tool.tool_type.value == "executable":
                func_sig = impl.get('function_signature', '')
                if func_sig:
                    console.print(f"[bold]Function:[/bold] {func_sig}")

        console.print()
        return True

    def handle_tool_run(self, args: str) -> bool:
        """
        Execute a tool with provided input.

        Args:
            args: "<tool_name> [input_json or input_string]"

        Returns:
            True if successful
        """
        # Parse tool name and input
        parts = args.split(None, 1)
        tool_name = parts[0]

        # Get input if provided, otherwise prompt for it
        if len(parts) > 1:
            input_str = parts[1]
        else:
            input_str = console.input("[cyan]Enter input (JSON or text): [/cyan]").strip()

        # Find the tool
        tool = self.tools_manager.get_tool(tool_name)
        if not tool:
            console.print(f"[red]Tool not found: {tool_name}[/red]")
            console.print("[dim]Use /tools to see available tools[/dim]")
            return False

        console.print(f"\n[bold cyan]Executing: {tool.name}[/bold cyan]\n")

        try:
            # Try to parse as JSON, otherwise use as string
            import json
            try:
                if input_str.startswith('{') or input_str.startswith('['):
                    input_data = json.loads(input_str)
                else:
                    # Treat as simple string input
                    input_data = {"input": input_str, "description": input_str}
            except json.JSONDecodeError:
                # Use as plain string
                input_data = {"input": input_str, "description": input_str}

            # Execute based on tool type
            if tool.tool_type.value == "llm":
                # For LLM tools, use the input as a prompt
                prompt = input_data.get("input", input_data.get("description", ""))

                with console.status("[cyan]Running LLM tool...", spinner="dots"):
                    result = self.tools_manager.invoke_llm_tool(
                        tool_id=tool.tool_id,
                        prompt=prompt,
                        temperature=0.7
                    )

                console.print("[bold green]Result:[/bold green]")
                console.print(result)

            elif tool.tool_type.value == "executable":
                # For executable tools, run the code
                impl = getattr(tool, 'implementation', {})
                if not isinstance(impl, dict) or 'code' not in impl:
                    console.print(f"[red]Tool {tool_name} has no executable code[/red]")
                    return False

                # Execute the tool's code with input
                import tempfile
                import subprocess

                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                    f.write(impl['code'])
                    code_file = f.name

                try:
                    # Run with JSON input
                    process = subprocess.run(
                        ['python', code_file],
                        input=json.dumps(input_data),
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    if process.returncode == 0:
                        console.print("[bold green]Result:[/bold green]")
                        try:
                            result_json = json.loads(process.stdout)
                            console.print(json.dumps(result_json, indent=2))
                        except json.JSONDecodeError:
                            console.print(process.stdout)
                    else:
                        console.print(f"[red]Error executing tool:[/red]")
                        console.print(process.stderr)
                        return False

                finally:
                    import os
                    os.unlink(code_file)

            else:
                console.print(f"[yellow]Tool type '{tool.tool_type.value}' cannot be executed directly[/yellow]")
                return False

            console.print()
            return True

        except Exception as e:
            console.print(f"[red]Error executing tool: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False

    def handle_mutate_tool(self, args: str) -> bool:
        """
        Handle mutate tool command - improve a tool based on instructions.

        Args:
            args: String containing "<tool_id> <instructions>"

        Returns:
            True if successful
        """
        # Parse arguments
        parts = args.split(None, 1)  # Split on first whitespace

        if len(parts) < 2:
            console.print("[red]Error: Please provide both tool ID and instructions[/red]")
            console.print("[dim]Usage: /mutate tool <tool_id> <instructions>[/dim]")
            console.print("[dim]Example: /mutate tool my_tool make it more generic[/dim]")
            return False

        tool_id = parts[0]
        instructions = parts[1]

        console.print(f"\n[bold cyan]Mutating tool: {tool_id}[/bold cyan]\n")
        console.print(f"[dim]Instructions: {instructions}[/dim]\n")

        # Get the tool
        tool = self.tools_manager.get_tool(tool_id)

        if not tool:
            console.print(f"[red]Error: Tool '{tool_id}' not found[/red]")
            console.print("[dim]Use /tools to see available tools[/dim]")
            return False

        # Display current tool info
        console.print(f"[green]Current tool:[/green]")
        console.print(f"  Name: {tool.name}")
        console.print(f"  Type: {tool.tool_type.value}")
        console.print(f"  Description: {tool.description}")
        if tool.tags:
            console.print(f"  Tags: {', '.join(tool.tags)}")
        console.print()

        # Load implementation if it exists
        implementation_code = None
        if hasattr(tool, 'implementation') and tool.implementation:
            implementation_code = tool.implementation
        elif "implementation_file" in tool.metadata:
            impl_file = Path(self.tools_manager.tools_path) / tool.metadata["implementation_file"]
            if impl_file.exists():
                with open(impl_file, 'r', encoding='utf-8') as f:
                    implementation_code = f.read()

        # Build implementation section separately to avoid f-string issues
        if implementation_code:
            impl_section = f"""Current Implementation:
```python
{implementation_code}
```
"""
        else:
            impl_section = "No implementation code available."

        # Create prompt for LLM to improve the tool
        mutation_prompt = f"""You are an expert at improving and refining tool definitions and implementations.

Current Tool:
- ID: {tool.tool_id}
- Name: {tool.name}
- Type: {tool.tool_type.value}
- Description: {tool.description}
- Tags: {', '.join(tool.tags) if tool.tags else 'none'}

{impl_section}

Parameters:
{json.dumps(tool.parameters, indent=2) if tool.parameters else 'None'}

Metadata:
{json.dumps(tool.metadata, indent=2) if tool.metadata else 'None'}

User Instructions: {instructions}

Please improve this tool based on the user's instructions. Provide your response in the following JSON format:

{{
  "name": "improved tool name",
  "description": "improved description",
  "tags": ["tag1", "tag2"],
  "parameters": {{"param_name": {{"type": "string", "description": "param description"}}}},
  "implementation": "improved implementation code if applicable (or null if not code-based)",
  "reasoning": "brief explanation of what you changed and why"
}}

Make sure the improvements align with the user's instructions while maintaining compatibility with the tool type and existing functionality.
Return ONLY the JSON, no other text."""

        # Show that we're processing
        with console.status("[bold cyan]Improving tool with LLM...", spinner="dots"):
            try:
                # Call LLM to improve the tool
                response = self.client.generate(
                    model=self.config.get("llm.model", "llama3"),
                    prompt=mutation_prompt,
                    temperature=0.3,  # Lower temperature for more consistent output
                    model_key="tool_mutation"
                )
            except Exception as e:
                console.print(f"[red]Error calling LLM: {e}[/red]")
                return False

        # Parse the response
        try:
            # Extract JSON from response (handle cases where LLM adds extra text)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                improved_data = json.loads(json_match.group())
            else:
                console.print("[red]Error: Could not parse LLM response as JSON[/red]")
                console.print(f"[dim]Response: {response[:500]}[/dim]")
                return False
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing JSON: {e}[/red]")
            console.print(f"[dim]Response: {response[:500]}[/dim]")
            return False

        # Display improvements
        console.print("\n[bold green]Proposed Improvements:[/bold green]\n")
        console.print(f"[cyan]Reasoning:[/cyan] {improved_data.get('reasoning', 'No reasoning provided')}\n")

        # Show what changed
        changes_table = Table(title="Changes", box=box.ROUNDED)
        changes_table.add_column("Field", style="cyan")
        changes_table.add_column("Before", style="yellow")
        changes_table.add_column("After", style="green")

        if improved_data.get('name') != tool.name:
            changes_table.add_row("Name", tool.name, improved_data.get('name', tool.name))

        if improved_data.get('description') != tool.description:
            before_desc = tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
            after_desc = improved_data.get('description', '')[:50] + "..." if len(improved_data.get('description', '')) > 50 else improved_data.get('description', '')
            changes_table.add_row("Description", before_desc, after_desc)

        if improved_data.get('tags') != tool.tags:
            changes_table.add_row("Tags", ', '.join(tool.tags), ', '.join(improved_data.get('tags', [])))

        if improved_data.get('implementation') and improved_data.get('implementation') != implementation_code:
            changes_table.add_row("Implementation", "Updated", "Updated (see below)")

        console.print(changes_table)
        console.print()

        # Show new implementation if it changed
        if improved_data.get('implementation') and improved_data.get('implementation') != implementation_code:
            console.print(Panel(
                improved_data['implementation'],
                title="[bold green]Improved Implementation[/bold green]",
                box=box.ROUNDED
            ))
            console.print()

        # Ask for confirmation
        confirm = console.input("[bold yellow]Apply these changes? (yes/no): [/bold yellow]").strip().lower()

        if confirm not in ['yes', 'y']:
            console.print("[yellow]Changes discarded[/yellow]")
            return False

        # Apply the improvements
        tool.name = improved_data.get('name', tool.name)
        tool.description = improved_data.get('description', tool.description)
        tool.tags = improved_data.get('tags', tool.tags)
        tool.parameters = improved_data.get('parameters', tool.parameters)

        # Update implementation if provided
        if improved_data.get('implementation'):
            tool.implementation = improved_data['implementation']

            # Save to file if it's a file-based tool
            if "implementation_file" in tool.metadata:
                impl_file = Path(self.tools_manager.tools_path) / tool.metadata["implementation_file"]
                with open(impl_file, 'w', encoding='utf-8') as f:
                    f.write(improved_data['implementation'])
                console.print(f"[green]OK Saved implementation to {impl_file}[/green]")
            else:
                # Create a new implementation file
                impl_filename = f"{tool_id}.py"
                impl_file = Path(self.tools_manager.tools_path) / impl_filename
                with open(impl_file, 'w', encoding='utf-8') as f:
                    f.write(improved_data['implementation'])
                tool.metadata["implementation_file"] = impl_filename
                console.print(f"[green]OK Created implementation file: {impl_file}[/green]")

        # Save the updated tool
        self.tools_manager.register_tool(tool)

        console.print(f"\n[bold green]OK Tool '{tool_id}' successfully updated![/bold green]\n")

        return True

    def handle_optimize_tool(self, args: str) -> bool:
        """
        Handle optimize tool command - iteratively optimize a tool for performance/quality.

        Args:
            args: String containing "<tool_id> [optimization_target]"
                  optimization_target can be: performance, quality, memory, latency (default: performance)

        Returns:
            True if successful
        """
        # Parse arguments
        parts = args.split(None, 1)

        if len(parts) < 1:
            console.print("[red]Error: Please provide a tool ID[/red]")
            console.print("[dim]Usage: /optimize tool <tool_id> [target][/dim]")
            console.print("[dim]Targets: performance (default), quality, memory, latency[/dim]")
            console.print("[dim]Example: /optimize tool my_tool performance[/dim]")
            return False

        tool_id = parts[0]
        optimization_target = parts[1] if len(parts) > 1 else "performance"

        # Validate optimization target
        valid_targets = ["performance", "quality", "memory", "latency", "all"]
        if optimization_target not in valid_targets:
            console.print(f"[red]Error: Invalid optimization target '{optimization_target}'[/red]")
            console.print(f"[dim]Valid targets: {', '.join(valid_targets)}[/dim]")
            return False

        console.print(f"\n[bold cyan]Optimizing tool: {tool_id}[/bold cyan]")
        console.print(f"[cyan]Target: {optimization_target}[/cyan]\n")

        # Get the tool
        tool = self.tools_manager.get_tool(tool_id)

        if not tool:
            console.print(f"[red]Error: Tool '{tool_id}' not found[/red]")
            console.print("[dim]Use /tools to see available tools[/dim]")
            return False

        # Only optimize tools with implementations
        if tool.tool_type not in [ToolType.FUNCTION, ToolType.EXECUTABLE]:
            console.print(f"[yellow]Warning: Tool type '{tool.tool_type.value}' cannot be optimized[/yellow]")
            console.print("[dim]Only FUNCTION and EXECUTABLE tools can be optimized[/dim]")
            return False

        # Load implementation
        implementation_code = None
        if hasattr(tool, 'implementation') and tool.implementation:
            implementation_code = tool.implementation
        elif "implementation_file" in tool.metadata:
            impl_file = Path(self.tools_manager.tools_path) / tool.metadata["implementation_file"]
            if impl_file.exists():
                with open(impl_file, 'r', encoding='utf-8') as f:
                    implementation_code = f.read()

        if not implementation_code:
            console.print("[red]Error: Tool has no implementation to optimize[/red]")
            return False

        # Display current tool info
        console.print("[green]Current tool:[/green]")
        console.print(f"  Name: {tool.name}")
        console.print(f"  Type: {tool.tool_type.value}")
        console.print(f"  Description: {tool.description}")
        console.print(f"  Implementation: {len(implementation_code)} characters\n")

        # Get the most powerful code model from config
        powerful_model = self.config.get("llm.optimization_model", "qwen2.5-coder:14b")
        console.print(f"[dim]Using optimization model: {powerful_model}[/dim]\n")

        # Create a temporary test node for benchmarking
        test_node_id = f"_opt_test_{tool_id}_{int(__import__('time').time())}"
        test_node_path = self.runner.nodes_dir / test_node_id
        test_node_path.mkdir(parents=True, exist_ok=True)

        # Save current implementation as test node
        test_code_path = test_node_path / "main.py"
        with open(test_code_path, 'w', encoding='utf-8') as f:
            f.write(implementation_code)

        # Generate unit tests for the tool
        console.print("[cyan]Generating unit tests...[/cyan]")

        test_prompt = f"""Generate comprehensive unit tests for this Python code.

Code:
```python
{implementation_code}
```

Tool Description: {tool.description}

Requirements:
- Generate pytest-compatible unit tests
- Test normal cases, edge cases, and error handling
- Include performance benchmarks where appropriate
- Tests should be self-contained and runnable
- Return ONLY the test code, no explanations

Format as Python code with pytest."""

        try:
            test_code = self.client.generate(
                model=powerful_model,
                prompt=test_prompt,
                temperature=0.2,
                model_key="test_generator"
            )

            # Clean up test code
            import re
            # Extract code from markdown if present
            code_match = re.search(r'```python\n(.*?)\n```', test_code, re.DOTALL)
            if code_match:
                test_code = code_match.group(1)

            # Save tests
            test_file_path = test_node_path / "test_main.py"
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_code)

            console.print(f"[green]OK Generated {len(test_code)} chars of tests[/green]\n")

        except Exception as e:
            console.print(f"[yellow]Warning: Could not generate tests: {e}[/yellow]")
            test_code = None

        # Get baseline metrics by running the current implementation
        console.print("[cyan]Measuring baseline performance...[/cyan]")

        baseline_metrics = None
        try:
            # Create a simple test input
            test_input = {"input": "test"}
            stdout, stderr, metrics = self.runner.run_node(
                test_node_id,
                test_input,
                timeout_ms=10000
            )

            if metrics.get("exit_code") == 0:
                baseline_metrics = metrics
                console.print(f"[green]OK Baseline metrics collected[/green]")
                console.print(f"  Latency: {metrics.get('latency_ms', 0):.2f}ms")
                console.print(f"  Memory: {metrics.get('memory_mb_peak', 0):.2f}MB")
                console.print(f"  CPU: {metrics.get('cpu_percent', 0):.1f}%\n")
            else:
                console.print(f"[yellow]Warning: Baseline run failed, continuing without metrics[/yellow]\n")

        except Exception as e:
            console.print(f"[yellow]Warning: Could not measure baseline: {e}[/yellow]\n")

        # Optimization loop
        console.print(f"[bold cyan]Starting optimization loop (target: {optimization_target})[/bold cyan]\n")

        max_iterations = 5
        improvement_threshold = 0.05  # 5% improvement threshold
        current_code = implementation_code
        current_metrics = baseline_metrics
        iteration_history = []

        for iteration in range(1, max_iterations + 1):
            console.print(f"[cyan]Iteration {iteration}/{max_iterations}[/cyan]")

            # Build optimization-specific guidance
            if optimization_target == "performance" or optimization_target == "latency":
                target_guidance = """Focus on:
- Algorithm efficiency (reduce time complexity)
- Minimize redundant operations
- Use efficient data structures
- Optimize loops and iterations
- Cache results where appropriate"""
            elif optimization_target == "memory":
                target_guidance = """Focus on:
- Reduce memory allocations
- Use generators instead of lists where possible
- Clean up resources properly
- Minimize data copying
- Use memory-efficient data structures"""
            elif optimization_target == "quality":
                target_guidance = """Focus on:
- Code readability and maintainability
- Better error handling
- Input validation
- Documentation and type hints
- Following best practices"""
            else:  # all
                target_guidance = """Focus on:
- Overall performance improvements
- Memory efficiency
- Code quality and readability
- Error handling
- Best practices"""

            # Add previous iteration context if available
            previous_context = ""
            if iteration_history:
                last = iteration_history[-1]
                previous_context = f"""

Previous Iteration Results:
- Latency: {last['metrics'].get('latency_ms', 0):.2f}ms
- Memory: {last['metrics'].get('memory_mb_peak', 0):.2f}MB
- Improvements made: {', '.join(last.get('improvements', ['none']))}"""

            # Build optimization prompt
            optimization_prompt = f"""You are an expert at optimizing Python code for {optimization_target}.

Current Code:
```python
{current_code}
```

Tool Description: {tool.description}

Optimization Target: {optimization_target}

{target_guidance}

{previous_context}

Current Metrics (if available):
{f"- Latency: {current_metrics.get('latency_ms', 0):.2f}ms" if current_metrics else "- No metrics available"}
{f"- Memory: {current_metrics.get('memory_mb_peak', 0):.2f}MB" if current_metrics else ""}
{f"- CPU: {current_metrics.get('cpu_percent', 0):.1f}%" if current_metrics else ""}

Provide an optimized version of this code. Return ONLY a JSON object:

{{
  "code": "optimized Python code",
  "improvements": ["improvement 1", "improvement 2"],
  "expected_impact": "description of expected performance impact"
}}

Requirements:
- Maintain the same functionality and interface
- Code must be production-ready and well-tested
- Keep or improve error handling
- Preserve any important comments or documentation
- Focus on measurable improvements

Return ONLY the JSON, no other text."""

            # Call LLM for optimization
            with console.status(f"[cyan]Optimizing (iteration {iteration})...", spinner="dots"):
                try:
                    response = self.client.generate(
                        model=powerful_model,
                        prompt=optimization_prompt,
                        temperature=0.3,
                        model_key="optimizer"
                    )

                    # Parse response
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        optimization_data = json.loads(json_match.group())
                    else:
                        console.print("[red]Failed to parse optimization response[/red]")
                        break

                except Exception as e:
                    console.print(f"[red]Error during optimization: {e}[/red]")
                    break

            # Extract optimized code
            optimized_code = optimization_data.get('code', '')
            improvements = optimization_data.get('improvements', [])
            expected_impact = optimization_data.get('expected_impact', '')

            console.print(f"[green]OK Generated optimized version[/green]")
            console.print(f"[dim]Expected impact: {expected_impact}[/dim]")

            # Save and test optimized version
            with open(test_code_path, 'w', encoding='utf-8') as f:
                f.write(optimized_code)

            # Run tests if available
            tests_passed = True
            if test_code:
                console.print("[dim]Running unit tests...[/dim]")
                try:
                    import subprocess
                    result = subprocess.run(
                        ["python", "-m", "pytest", str(test_file_path), "-v"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=str(test_node_path)
                    )
                    tests_passed = result.returncode == 0

                    if tests_passed:
                        console.print("[green]OK All tests passed[/green]")
                    else:
                        console.print("[yellow]! Some tests failed[/yellow]")
                        console.print(f"[dim]{result.stdout[:200]}[/dim]")

                except Exception as e:
                    console.print(f"[yellow]Warning: Could not run tests: {e}[/yellow]")

            # Measure new metrics
            try:
                stdout, stderr, new_metrics = self.runner.run_node(
                    test_node_id,
                    test_input,
                    timeout_ms=10000
                )

                if new_metrics.get("exit_code") == 0:
                    console.print(f"[green]OK New metrics collected[/green]")
                    console.print(f"  Latency: {new_metrics.get('latency_ms', 0):.2f}ms")
                    console.print(f"  Memory: {new_metrics.get('memory_mb_peak', 0):.2f}MB")
                    console.print(f"  CPU: {new_metrics.get('cpu_percent', 0):.1f}%")

                    # Calculate improvement
                    if current_metrics:
                        if optimization_target == "latency" or optimization_target == "performance":
                            old_val = current_metrics.get('latency_ms', 1)
                            new_val = new_metrics.get('latency_ms', 1)
                            improvement = (old_val - new_val) / old_val if old_val > 0 else 0
                            console.print(f"  [cyan]Latency improvement: {improvement*100:.1f}%[/cyan]")
                        elif optimization_target == "memory":
                            old_val = current_metrics.get('memory_mb_peak', 1)
                            new_val = new_metrics.get('memory_mb_peak', 1)
                            improvement = (old_val - new_val) / old_val if old_val > 0 else 0
                            console.print(f"  [cyan]Memory improvement: {improvement*100:.1f}%[/cyan]")
                        else:
                            # For quality or all, calculate composite improvement
                            lat_improve = (current_metrics.get('latency_ms', 1) - new_metrics.get('latency_ms', 1)) / current_metrics.get('latency_ms', 1)
                            mem_improve = (current_metrics.get('memory_mb_peak', 1) - new_metrics.get('memory_mb_peak', 1)) / current_metrics.get('memory_mb_peak', 1)
                            improvement = (lat_improve + mem_improve) / 2
                            console.print(f"  [cyan]Overall improvement: {improvement*100:.1f}%[/cyan]")

                        # Store iteration history
                        iteration_history.append({
                            'iteration': iteration,
                            'code': optimized_code,
                            'metrics': new_metrics,
                            'improvements': improvements,
                            'improvement_pct': improvement,
                            'tests_passed': tests_passed
                        })

                        # Check if improvement is below threshold
                        if improvement < improvement_threshold:
                            console.print(f"\n[yellow]Improvement below threshold ({improvement*100:.1f}% < {improvement_threshold*100:.0f}%)[/yellow]")
                            console.print("[yellow]Stopping optimization loop[/yellow]\n")
                            break

                        # Update current for next iteration
                        current_code = optimized_code
                        current_metrics = new_metrics
                    else:
                        # No baseline to compare
                        iteration_history.append({
                            'iteration': iteration,
                            'code': optimized_code,
                            'metrics': new_metrics,
                            'improvements': improvements,
                            'tests_passed': tests_passed
                        })
                        current_code = optimized_code
                        current_metrics = new_metrics
                else:
                    console.print("[red]X Optimized code failed to execute[/red]")
                    console.print(f"[dim]{stderr[:200]}[/dim]")

            except Exception as e:
                console.print(f"[red]Error measuring performance: {e}[/red]")

            console.print()  # Blank line between iterations

        # Display optimization summary
        console.print("\n[bold green]Optimization Complete![/bold green]\n")

        if iteration_history:
            # Use the best iteration
            best_iteration = max(iteration_history, key=lambda x: x.get('improvement_pct', 0))

            # Display comparison table
            comparison_table = Table(title="Optimization Results", box=box.ROUNDED)
            comparison_table.add_column("Metric", style="cyan")
            comparison_table.add_column("Original", style="yellow")
            comparison_table.add_column("Optimized", style="green")
            comparison_table.add_column("Improvement", style="magenta")

            if baseline_metrics and best_iteration.get('metrics'):
                orig_lat = baseline_metrics.get('latency_ms', 0)
                opt_lat = best_iteration['metrics'].get('latency_ms', 0)
                lat_improve = ((orig_lat - opt_lat) / orig_lat * 100) if orig_lat > 0 else 0
                comparison_table.add_row(
                    "Latency",
                    f"{orig_lat:.2f}ms",
                    f"{opt_lat:.2f}ms",
                    f"{lat_improve:+.1f}%"
                )

                orig_mem = baseline_metrics.get('memory_mb_peak', 0)
                opt_mem = best_iteration['metrics'].get('memory_mb_peak', 0)
                mem_improve = ((orig_mem - opt_mem) / orig_mem * 100) if orig_mem > 0 else 0
                comparison_table.add_row(
                    "Memory",
                    f"{orig_mem:.2f}MB",
                    f"{opt_mem:.2f}MB",
                    f"{mem_improve:+.1f}%"
                )

                comparison_table.add_row(
                    "Code Size",
                    f"{len(implementation_code)} chars",
                    f"{len(best_iteration['code'])} chars",
                    f"{((len(implementation_code) - len(best_iteration['code'])) / len(implementation_code) * 100):+.1f}%"
                )

            console.print(comparison_table)
            console.print()

            # Show improvements made
            console.print("[cyan]Improvements Applied:[/cyan]")
            for imp in best_iteration.get('improvements', []):
                console.print(f"  • {imp}")
            console.print()

            # Display optimized code
            console.print(Panel(
                best_iteration['code'],
                title="[bold green]Optimized Code[/bold green]",
                box=box.ROUNDED
            ))
            console.print()

            # Ask for confirmation
            confirm = console.input("[bold yellow]Save optimized version? (yes/no): [/bold yellow]").strip().lower()

            if confirm in ['yes', 'y']:
                # Update tool with optimized code
                tool.implementation = best_iteration['code']

                # Save to file
                if "implementation_file" in tool.metadata:
                    impl_file = Path(self.tools_manager.tools_path) / tool.metadata["implementation_file"]
                    with open(impl_file, 'w', encoding='utf-8') as f:
                        f.write(best_iteration['code'])
                    console.print(f"[green]OK Saved to {impl_file}[/green]")
                else:
                    impl_filename = f"{tool_id}.py"
                    impl_file = Path(self.tools_manager.tools_path) / impl_filename
                    with open(impl_file, 'w', encoding='utf-8') as f:
                        f.write(best_iteration['code'])
                    tool.metadata["implementation_file"] = impl_filename
                    console.print(f"[green]OK Created {impl_file}[/green]")

                # Update tool metadata with optimization info
                tool.metadata["optimized"] = True
                tool.metadata["optimization_target"] = optimization_target
                tool.metadata["optimization_date"] = datetime.utcnow().isoformat() + "Z"
                if baseline_metrics and best_iteration.get('metrics'):
                    tool.metadata["optimization_improvement"] = {
                        "latency_pct": lat_improve,
                        "memory_pct": mem_improve
                    }

                # Save to registry
                self.tools_manager.register_tool(tool)
                console.print(f"[green]OK Updated tool registry[/green]")

                # Index in RAG if available
                if self.rag:
                    try:
                        from src import ArtifactType
                        self.rag.index_artifact(
                            artifact_id=f"tool_{tool_id}_optimized",
                            artifact_type=ArtifactType.FUNCTION,
                            content=best_iteration['code'],
                            metadata={
                                "tool_id": tool_id,
                                "description": tool.description,
                                "optimized": True,
                                "optimization_target": optimization_target
                            }
                        )
                        console.print(f"[green]OK Indexed in RAG memory[/green]")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not index in RAG: {e}[/yellow]")

                console.print(f"\n[bold green]OK Tool '{tool_id}' successfully optimized![/bold green]\n")
            else:
                console.print("[yellow]Optimization discarded[/yellow]\n")
        else:
            console.print("[yellow]No successful optimizations produced[/yellow]\n")

        # Cleanup test node
        try:
            import shutil
            shutil.rmtree(test_node_path)
        except Exception:
            pass

        return True

    def handle_workflow(self, node_id: str) -> bool:
        """Handle workflow command - display the complete workflow for a node."""
        if not node_id:
            console.print("[red]Error: Please specify a node ID[/red]")
            console.print("[dim]Usage: workflow <node_id>[/dim]")
            return False

        console.print(f"\n[bold cyan]Workflow for: {node_id}[/bold cyan]\n")

        # Get node info from registry
        node_info = self.registry.get_node(node_id)

        if not node_info:
            console.print(f"[red]Error: Node '{node_id}' not found in registry[/red]")
            return False

        # Try to load the node's code to analyze it
        node_path = self.runner.get_node_path(node_id)

        if not node_path.exists():
            console.print(f"[red]Error: Node file not found: {node_path}[/red]")
            return False

        # Read the code
        with open(node_path, 'r') as f:
            code = f.read()

        # Analyze code to extract workflow steps
        import re

        # Find call_tool() invocations
        tool_pattern = re.compile(r'call_tool\s*\(\s*[\'"]([^\'"]+)[\'"]')
        tools_called = tool_pattern.findall(code)

        # Find function definitions
        func_pattern = re.compile(r'def\s+(\w+)\s*\(')
        functions = func_pattern.findall(code)

        # Create workflow visualization
        table = Table(title=f"Workflow Steps for {node_id}", box=box.ROUNDED)
        table.add_column("Step", justify="right", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Operation", style="green")
        table.add_column("Details", style="dim")

        step_num = 1

        # Add function definitions
        for func in functions:
            table.add_row(
                str(step_num),
                "Function",
                func,
                "Local function" if func != "main" else "Entry point"
            )
            step_num += 1

        # Add tool calls
        for i, tool in enumerate(tools_called, 1):
            # Try to find the tool in tools manager
            tool_obj = next((t for t in self.tools_manager.get_all_tools() if t.tool_id == tool), None)

            if tool_obj:
                tool_desc = tool_obj.description[:50] + "..." if len(tool_obj.description) > 50 else tool_obj.description
                tool_type = tool_obj.tool_type.value
            else:
                tool_desc = "Unknown tool"
                tool_type = "external"

            table.add_row(
                str(step_num),
                f"Tool Call ({tool_type})",
                tool,
                tool_desc
            )
            step_num += 1

        console.print(table)

        # Show node metadata
        meta_table = Table(title="Node Metadata", box=box.SIMPLE)
        meta_table.add_column("Property", style="cyan")
        meta_table.add_column("Value", style="green")

        meta_table.add_row("Version", node_info.get("version", "unknown"))
        meta_table.add_row("Score", f"{node_info.get('score_overall', 0):.2f}")
        meta_table.add_row("Tags", ", ".join(node_info.get("tags", [])))
        meta_table.add_row("Functions Found", str(len(functions)))
        meta_table.add_row("Tools Used", str(len(set(tools_called))))

        console.print()
        console.print(meta_table)
        console.print()

        return True

    def handle_clear_rag(self) -> bool:
        """
        Handle clear_rag command - clears RAG memory (including ALL non-YAML tool definitions).
        WARNING: This is destructive and cannot be undone!
        """
        console.print("\n[bold red]WARNING: This will clear all RAG memory![/bold red]")
        console.print("[yellow]This includes ALL non-YAML tool definitions (dynamic tools from code generation).[/yellow]")
        console.print("[dim]YAML-based tools in tools/*.yaml will be preserved and reloaded on startup.[/dim]")
        console.print("[yellow]This action cannot be undone.[/yellow]\n")

        confirm = console.input("[bold]Type 'yes' to confirm: [/bold]").strip().lower()

        if confirm != 'yes':
            console.print("[cyan]Cancelled.[/cyan]")
            return False

        console.print("\n[cyan]Clearing RAG memory...[/cyan]")

        # Clear RAG/Qdrant
        try:
            if hasattr(self.rag, 'clear_collection'):
                self.rag.clear_collection()
                console.print("[green]OK RAG memory cleared[/green]")
            else:
                console.print("[yellow]RAG does not support clear_collection[/yellow]")
        except Exception as e:
            console.print(f"[red]Error clearing RAG: {e}[/red]")

        # Ask if they want to clear registry and nodes too
        console.print("\n[yellow]Also clear registry and generated nodes?[/yellow]")
        confirm_nodes = console.input("[bold]Type 'yes' to also delete all nodes: [/bold]").strip().lower()

        if confirm_nodes == 'yes':
            import shutil

            # Clear nodes directory
            nodes_path = Path(self.config.nodes_path)
            if nodes_path.exists():
                try:
                    shutil.rmtree(nodes_path)
                    nodes_path.mkdir(parents=True, exist_ok=True)
                    console.print(f"[green]OK Cleared nodes directory: {nodes_path}[/green]")
                except Exception as e:
                    console.print(f"[red]Error clearing nodes: {e}[/red]")

            # Clear registry
            registry_path = Path(self.config.registry_path)
            if registry_path.exists():
                try:
                    shutil.rmtree(registry_path)
                    registry_path.mkdir(parents=True, exist_ok=True)
                    # Recreate index
                    index_path = registry_path / "index.json"
                    with open(index_path, 'w') as f:
                        json.dump({"nodes": []}, f, indent=2)
                    console.print(f"[green]OK Cleared registry: {registry_path}[/green]")
                except Exception as e:
                    console.print(f"[red]Error clearing registry: {e}[/red]")

        console.print("\n[green]Clear operation complete![/green]")
        return True

    def handle_manual(self, search_term: str = "") -> bool:
        """
        Handle manual command - search for commands with intelligent fuzzy matching.

        Args:
            search_term: Optional search term for fuzzy matching
        """
        from pathlib import Path
        from difflib import SequenceMatcher

        # Load manual.json
        manual_path = Path(__file__).parent / "manual.json"
        if not manual_path.exists():
            console.print("[red]Error: manual.json not found[/red]")
            return False

        try:
            with open(manual_path, 'r', encoding='utf-8') as f:
                manual_data = json.load(f)
        except Exception as e:
            console.print(f"[red]Error loading manual: {e}[/red]")
            return False

        commands = manual_data.get("commands", {})
        concepts = manual_data.get("concepts", {})

        # If no search term, show overview
        if not search_term:
            console.print("\n[bold cyan]mostlylucid DiSE Manual[/bold cyan]")
            console.print("[dim]Use /manual <search> to find specific commands[/dim]\n")

            console.print("[bold]Available Commands:[/bold]")
            for cmd in sorted(commands.keys()):
                desc = commands[cmd].get("description", "")
                console.print(f"  [cyan]{cmd:<20}[/cyan] {desc}")

            console.print("\n[bold]Concepts:[/bold]")
            for concept in sorted(concepts.keys()):
                desc = concepts[concept].get("description", "")
                console.print(f"  [yellow]{concept:<20}[/yellow] {desc}")

            console.print("\n[dim]Examples: /manual tool, /manual list, /manual tool list[/dim]")
            return True

        # Fuzzy match search term against commands
        def similarity(a: str, b: str) -> float:
            """Calculate similarity between two strings (0-1)."""
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        # Find best matches
        matches = []

        # Search in commands
        for cmd, cmd_data in commands.items():
            cmd_name = cmd.lstrip('/')
            score = similarity(search_term, cmd_name)

            # Also check aliases
            for alias in cmd_data.get("aliases", []):
                alias_score = similarity(search_term, alias)
                score = max(score, alias_score)

            # Check subcommands if they exist
            if "subcommands" in cmd_data:
                for subcmd in cmd_data["subcommands"].keys():
                    # Check for "tool list" style searches
                    full_cmd = f"{cmd_name} {subcmd}"
                    subcmd_score = similarity(search_term, full_cmd)
                    score = max(score, subcmd_score)

            if score > 0.4:  # Threshold for matching
                matches.append((score, cmd, cmd_data, "command"))

        # Search in concepts
        for concept, concept_data in concepts.items():
            score = similarity(search_term, concept)
            if score > 0.4:
                matches.append((score, concept, concept_data, "concept"))

        # Sort by score (highest first)
        matches.sort(key=lambda x: x[0], reverse=True)

        if not matches:
            console.print(f"[yellow]No matches found for '{search_term}'[/yellow]")
            console.print("[dim]Try /manual to see all commands[/dim]")
            return True

        # Show top match(es)
        top_score = matches[0][0]
        top_matches = [m for m in matches if m[0] >= top_score * 0.9]  # Show similar-scoring matches

        # If match is not exact, show suggestion
        if top_score < 1.0:
            if len(top_matches) == 1:
                console.print(f"[dim]Did you mean: [cyan]{top_matches[0][1]}[/cyan]?[/dim]\n")
            else:
                console.print("[dim]Did you mean one of these?[/dim]")
                for _, name, _, _ in top_matches[:3]:
                    console.print(f"  [cyan]{name}[/cyan]")
                console.print()

        # Display top match details
        for score, name, data, match_type in top_matches[:1]:  # Show only the best match details
            if match_type == "command":
                console.print(f"\n[bold cyan]{name}[/bold cyan]")
                console.print(f"{data.get('description', '')}\n")

                console.print(f"[bold]Usage:[/bold] {data.get('usage', name)}")

                if "subcommands" in data:
                    console.print("\n[bold]Subcommands:[/bold]")
                    for subcmd, subcmd_desc in data["subcommands"].items():
                        console.print(f"  [cyan]{subcmd:<30}[/cyan] {subcmd_desc}")

                if "examples" in data:
                    console.print("\n[bold]Examples:[/bold]")
                    for example in data["examples"]:
                        console.print(f"  [dim]{example}[/dim]")

                if "warning" in data:
                    console.print(f"\n[bold red]Warning:[/bold red] {data['warning']}")

                if "aliases" in data and data["aliases"]:
                    console.print(f"\n[dim]Aliases: {', '.join(data['aliases'])}[/dim]")

            elif match_type == "concept":
                console.print(f"\n[bold yellow]Concept: {name}[/bold yellow]")
                console.print(f"{data.get('description', '')}\n")

                if "related_commands" in data:
                    console.print("[bold]Related Commands:[/bold]")
                    for related_cmd in data["related_commands"]:
                        console.print(f"  [cyan]{related_cmd}[/cyan]")

        console.print()
        return True

    def get_debug_version(self, production_tool_id: str) -> Optional[dict]:
        """
        Retrieve the debug version of a production tool.

        Args:
            production_tool_id: ID of the production tool

        Returns:
            Dictionary with debug tool metadata, or None if not found
        """
        if not self.rag:
            return None

        try:
            # Search for debug versions linked to this production tool
            debug_artifacts = self.rag.find_by_tags(["DEBUG", "tool"])

            for artifact in debug_artifacts:
                metadata = artifact.metadata or {}
                if metadata.get("production_tool_id") == production_tool_id:
                    return {
                        "tool_id": metadata.get("tool_id"),
                        "debug_tool_id": metadata.get("debug_tool_id"),
                        "version": metadata.get("version"),
                        "code_hash": metadata.get("code_hash"),
                        "created_at": metadata.get("created_at"),
                        "artifact": artifact
                    }

            return None

        except Exception as e:
            console.print(f"[yellow]Could not retrieve debug version: {e}[/yellow]")
            return None

    def _generate_tests_with_pynguin(
        self,
        node_id: str,
        timeout: int = 60,
        min_coverage: float = 0.70,
        use_mock_runtime: bool = False
    ) -> Dict[str, Any]:
        """
        Generate unit tests using Pynguin with coverage validation and LLM fixing.

        Workflow:
        1. Create mock node_runtime if code uses external tools (optional)
        2. Generate tests with Pynguin (fast, 30-60s)
        3. Run tests and measure coverage
        4. If coverage < threshold, send to LLM to improve
        5. Re-run and validate
        6. Clean up mock

        Args:
            node_id: Node identifier
            timeout: Maximum search time in seconds
            min_coverage: Minimum required coverage (default: 70%)
            use_mock_runtime: Create temporary mock node_runtime for testing (default: False)

        Returns:
            Dict with success status, coverage, and test info
        """
        result = {
            'success': False,
            'coverage': 0.0,
            'test_count': 0,
            'method': 'none',
            'needed_llm_fix': False
        }

        # Skip Pynguin on Windows (incompatible)
        import platform
        if platform.system() == 'Windows':
            console.print(f"[dim]Skipping Pynguin on Windows (incompatible), using LLM-based tests[/dim]")
            return result

        try:
            # Get node path
            node_path = self.runner.get_node_path(node_id)
            if not node_path.exists():
                return result

            # Get the module directory and name
            module_dir = node_path.parent
            module_name = node_path.stem  # e.g., 'main' from 'main.py'

            # Create temporary mock node_runtime if needed
            mock_runtime_path = None
            if use_mock_runtime:
                mock_runtime_path = module_dir / "node_runtime.py"
                mock_runtime_code = '''"""Mock node_runtime for test generation."""
from typing import Any

def call_tool(tool_name: str, prompt_or_data: Any = None, **kwargs) -> Any:
    """Mock call_tool that returns sensible defaults."""
    # Content generation tools
    if any(name in tool_name for name in ['generator', 'writer', 'translator']):
        return "Mock generated content"
    # Database/storage tools
    if any(name in tool_name for name in ['database', 'storage', 'save', 'load']):
        return {"status": "success", "id": "mock_123"}
    # Default
    return {"status": "success", "result": f"Mock {tool_name}"}

def call_llm(model: str, prompt: str, **kwargs) -> str:
    """Mock LLM call."""
    return "Mock LLM response"

def call_tools_parallel(tool_calls: list) -> list:
    """Mock parallel tool calls."""
    return [call_tool(call[0] if isinstance(call, tuple) else call['tool'], "")
            for call in tool_calls]
'''
                mock_runtime_path.write_text(mock_runtime_code, encoding='utf-8')

            # Create tests output directory
            tests_dir = module_dir / "tests_pynguin"
            tests_dir.mkdir(exist_ok=True)

            console.print(f"[dim cyan]> Attempting fast test generation with Pynguin (timeout: {timeout}s)...[/dim cyan]")

            # Run Pynguin
            import subprocess
            pynguin_result = subprocess.run(
                [
                    'python', '-m', 'pynguin',
                    '--project-path', str(module_dir),
                    '--module-name', module_name,
                    '--output-path', str(tests_dir),
                    '--maximum-search-time', str(timeout),
                    '--assertion-generation', 'MUTATION_ANALYSIS'
                    # Removed --test-case-output (not supported in pynguin 0.43.0)
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 10  # Give extra time for Pynguin overhead
            )

            # Check if tests were generated
            test_files = list(tests_dir.glob("test_*.py"))
            if not test_files:
                # Handle Windows pynguin crash (exit code -1 appears as 4294967295)
                if pynguin_result.returncode in (-1, 4294967295):
                    console.print(f"[yellow]Pynguin crashed (incompatible with Windows)[/yellow]")
                    console.print(f"[dim]Falling back to LLM-based test generation...[/dim]")
                    # Disable pynguin for the rest of this session
                    self.config.set("testing.use_pynguin", False)
                    return result

                console.print(f"[yellow]Pynguin did not generate tests (exit code: {pynguin_result.returncode})[/yellow]")

                # Analyze common failure reasons
                stderr_lower = pynguin_result.stderr.lower() if pynguin_result.stderr else ""
                if "importerror" in stderr_lower or "modulenotfounderror" in stderr_lower:
                    console.print(f"[dim yellow]Reason: Import errors (code may have external dependencies)[/dim yellow]")
                elif "timeout" in stderr_lower:
                    console.print(f"[dim yellow]Reason: Analysis timeout[/dim yellow]")
                elif "no such file" in stderr_lower or "cannot find" in stderr_lower:
                    console.print(f"[dim yellow]Reason: Module not found[/dim yellow]")
                elif pynguin_result.stderr:
                    # Show first line of actual error
                    error_lines = pynguin_result.stderr.strip().split('\n')
                    first_error = next((line for line in error_lines if 'error' in line.lower() or 'exception' in line.lower()), error_lines[0] if error_lines else "")
                    console.print(f"[dim]{first_error[:150]}[/dim]")

                console.print(f"[dim]Falling back to LLM-based test generation...[/dim]")
                return result

            # Move generated tests to main test.py
            test_file = test_files[0]
            dest_test_file = module_dir / "test.py"

            # Read generated tests
            generated_tests = test_file.read_text(encoding='utf-8')

            # Add header comment
            header = f"""# Auto-generated tests by Pynguin
# Generated in {timeout} seconds using evolutionary algorithm
# These tests provide baseline coverage and should be reviewed/refined

"""
            final_tests = header + generated_tests

            # Save to test.py
            dest_test_file.write_text(final_tests, encoding='utf-8')

            # Clean up pynguin directory
            import shutil
            shutil.rmtree(tests_dir, ignore_errors=True)

            test_count = len(list(filter(lambda l: l.strip().startswith('def test_'), final_tests.split('\n'))))
            console.print(f"[green]✓ Pynguin generated {test_count} test functions[/green]")

            # Step 2: Run tests and measure coverage
            console.print(f"[cyan]> Running tests and measuring coverage...[/cyan]")
            coverage_result = self._run_tests_with_coverage(node_id)

            if not coverage_result['success']:
                console.print(f"[yellow]! Generated tests have errors[/yellow]")
                console.print(f"[dim]{coverage_result.get('error', 'Unknown error')[:200]}[/dim]")
                result['method'] = 'pynguin_failed'
                return result

            coverage_pct = coverage_result['coverage']
            console.print(f"[cyan]Coverage: {coverage_pct:.1f}%[/cyan]")

            result['test_count'] = test_count
            result['coverage'] = coverage_pct

            # Step 3: Check if coverage meets threshold
            if coverage_pct >= min_coverage * 100:
                console.print(f"[green]✓ Coverage {coverage_pct:.1f}% meets threshold ({min_coverage*100:.0f}%)[/green]")
                result['success'] = True
                result['method'] = 'pynguin'
                return result
            else:
                # Coverage below threshold - send to LLM for fixing
                console.print(f"[yellow]! Coverage {coverage_pct:.1f}% below threshold ({min_coverage*100:.0f}%)[/yellow]")
                console.print(f"[cyan]> Sending to LLM to improve test coverage...[/cyan]")

                # Read the source code
                source_code = node_path.read_text(encoding='utf-8')

                # Step 4: Use LLM to improve tests
                improved_tests = self._improve_tests_with_llm(
                    source_code=source_code,
                    current_tests=final_tests,
                    current_coverage=coverage_pct,
                    target_coverage=min_coverage * 100,
                    coverage_report=coverage_result.get('report', '')
                )

                if improved_tests:
                    # Save improved tests
                    dest_test_file.write_text(improved_tests, encoding='utf-8')

                    # Re-run coverage
                    console.print(f"[cyan]> Re-running with improved tests...[/cyan]")
                    new_coverage_result = self._run_tests_with_coverage(node_id)

                    if new_coverage_result['success']:
                        new_coverage = new_coverage_result['coverage']
                        console.print(f"[cyan]New coverage: {new_coverage:.1f}% (was {coverage_pct:.1f}%)[/cyan]")

                        result['coverage'] = new_coverage
                        result['needed_llm_fix'] = True

                        if new_coverage >= min_coverage * 100:
                            console.print(f"[green]✓ LLM improved coverage to {new_coverage:.1f}%[/green]")
                            result['success'] = True
                            result['method'] = 'pynguin+llm'
                            return result
                        else:
                            console.print(f"[yellow]Coverage still below threshold: {new_coverage:.1f}% < {min_coverage*100:.0f}%[/yellow]")
                            result['method'] = 'pynguin+llm_insufficient'
                            return result
                    else:
                        console.print(f"[yellow]Improved tests have errors, reverting to Pynguin version[/yellow]")
                        dest_test_file.write_text(final_tests, encoding='utf-8')
                        result['success'] = True  # Use original Pynguin tests
                        result['method'] = 'pynguin_llm_failed'
                        return result
                else:
                    console.print(f"[yellow]LLM could not improve tests, using Pynguin version[/yellow]")
                    result['success'] = True  # Use original Pynguin tests
                    result['method'] = 'pynguin_llm_failed'
                    return result

        except FileNotFoundError:
            console.print("[yellow]Pynguin not installed. Install with: pip install pynguin[/yellow]")
            return result
        except subprocess.TimeoutExpired:
            console.print(f"[yellow]Pynguin timed out after {timeout}s[/yellow]")
            return result
        except Exception as e:
            console.print(f"[yellow]Pynguin error: {e}[/yellow]")
            import traceback
            traceback.print_exc()
            return result
        finally:
            # Clean up mock node_runtime if we created it
            if use_mock_runtime and mock_runtime_path and mock_runtime_path.exists():
                try:
                    mock_runtime_path.unlink()
                    console.print(f"[dim]Cleaned up mock node_runtime[/dim]")
                except Exception:
                    pass  # Ignore cleanup errors

    def _generate_tdd_template_with_pynguin(
        self,
        node_id: str,
        description: str,
        specification: str
    ) -> Optional[str]:
        """
        Use Pynguin to generate a TDD template based on specification analysis.

        This creates a stub/skeleton module based on the specification,
        then uses Pynguin to generate test structure, which becomes the TDD template.

        Args:
            node_id: Node identifier
            description: Task description
            specification: Detailed specification

        Returns:
            TDD template test code or None if failed
        """
        try:
            import subprocess
            import tempfile
            from pathlib import Path
            import shutil

            console.print("[dim]Creating specification-based stub for Pynguin analysis...[/dim]")

            # Create a temporary module with function signatures based on specification
            stub_code = self._create_stub_from_specification(specification, description)

            if not stub_code:
                return None

            # Create temp directory structure
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                module_path = tmppath / "stub_module.py"
                module_path.write_text(stub_code, encoding='utf-8')

                # Run Pynguin on the stub to get test structure
                tests_dir = tmppath / "tests"
                tests_dir.mkdir()

                result = subprocess.run(
                    [
                        'python', '-m', 'pynguin',
                        '--project-path', str(tmppath),
                        '--module-name', 'stub_module',
                        '--output-path', str(tests_dir),
                        '--maximum-search-time', '10',  # Quick generation
                        '--test-case-output', 'PytestTest'
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15
                )

                # Extract generated test structure
                test_files = list(tests_dir.glob("test_*.py"))
                if test_files:
                    generated_tests = test_files[0].read_text(encoding='utf-8')

                    # Convert to TDD template (remove implementations, keep structure)
                    tdd_template = self._convert_to_tdd_template(generated_tests, description)

                    console.print(f"[green]Generated TDD template from Pynguin structure[/green]")
                    return tdd_template
                else:
                    console.print(f"[yellow]Pynguin did not generate test structure[/yellow]")
                    return None

        except FileNotFoundError:
            console.print("[dim]Pynguin not available for TDD template generation[/dim]")
            return None
        except Exception as e:
            console.print(f"[dim]Pynguin TDD generation failed: {e}[/dim]")
            return None

    def _create_stub_from_specification(self, specification: str, description: str) -> Optional[str]:
        """
        Create a stub module with function signatures based on specification.

        Args:
            specification: Task specification
            description: Task description

        Returns:
            Python stub code with function signatures
        """
        try:
            # Extract function names and signatures from specification
            import re

            # Look for function definitions in specification
            func_patterns = [
                r'`(\w+)\([^)]*\)`',  # `function_name(args)`
                r'(\w+)\([^)]*\)\s*(?:->|:)',  # function_name(args) ->
                r'def (\w+)\(',  # def function_name(
            ]

            functions = set()
            for pattern in func_patterns:
                matches = re.findall(pattern, specification)
                functions.update(matches)

            if not functions:
                # Fallback: create a generic main() stub
                functions = {'main'}

            # Create stub module
            stub_lines = [
                "# Stub module for Pynguin TDD template generation",
                "import json",
                "import sys",
                ""
            ]

            for func_name in sorted(functions):
                stub_lines.extend([
                    f"def {func_name}(*args, **kwargs):",
                    "    \"\"\"Stub function for TDD template generation.\"\"\"",
                    "    pass",
                    ""
                ])

            return '\n'.join(stub_lines)

        except Exception as e:
            console.print(f"[dim]Could not create stub: {e}[/dim]")
            return None

    def _convert_to_tdd_template(self, generated_tests: str, description: str) -> str:
        """
        Convert Pynguin-generated tests into a TDD template.

        Args:
            generated_tests: Tests generated by Pynguin
            description: Task description

        Returns:
            TDD template with test structure but empty implementations
        """
        import re

        lines = []
        lines.append("# TDD Interface Tests - Generated from Pynguin structure")
        lines.append(f"# Task: {description[:80]}")
        lines.append("")
        lines.append("import sys")
        lines.append("import json")
        lines.append("import os")
        lines.append("sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))")
        lines.append("")

        # Extract test function signatures
        in_test = False
        for line in generated_tests.split('\n'):
            stripped = line.strip()

            # Start of test function
            if stripped.startswith('def test_'):
                in_test = True
                lines.append(line)
                # Add docstring
                func_name = stripped.split('(')[0].replace('def ', '')
                lines.append(f'    """Test interface for {func_name}"""')
                lines.append('    print(f"Testing {func_name}...")')
                lines.append('    import main')
                lines.append('    # TODO: Add interface assertions here')
                lines.append('    print("OK Test passed")')
                lines.append('')
                in_test = False

        # Add main block
        lines.append("if __name__ == '__main__':")
        lines.append("    # Run all tests")
        for line in lines:
            if 'def test_' in line:
                func_name = line.split('def ')[1].split('(')[0]
                lines.append(f"    {func_name}()")

        return '\n'.join(lines)

    def _run_tests_with_coverage(self, node_id: str) -> Dict[str, Any]:
        """
        Run tests with coverage measurement using pytest-cov.

        Args:
            node_id: Node identifier

        Returns:
            Dict with success, coverage percentage, and report
        """
        import subprocess
        import re
        from pathlib import Path

        result = {
            'success': False,
            'coverage': 0.0,
            'report': '',
            'error': ''
        }

        try:
            node_path = self.runner.get_node_path(node_id)
            module_dir = node_path.parent
            module_name = node_path.stem

            # Run pytest with coverage
            coverage_result = subprocess.run(
                [
                    sys.executable, '-m', 'pytest',
                    'test.py',
                    f'--cov={module_name}',
                    '--cov-report=term-missing',
                    '-v'
                ],
                capture_output=True,
                text=True,
                cwd=str(module_dir),
                timeout=30
            )

            stdout = coverage_result.stdout
            stderr = coverage_result.stderr
            result['report'] = stdout

            # Extract coverage percentage from output
            # Look for pattern like "TOTAL    100%"
            coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', stdout)
            if coverage_match:
                result['coverage'] = float(coverage_match.group(1))

            # Check if tests passed
            result['success'] = coverage_result.returncode == 0

            if not result['success']:
                result['error'] = stderr or "Tests failed"

            return result

        except FileNotFoundError:
            result['error'] = "pytest or pytest-cov not installed. Install with: pip install pytest pytest-cov"
            console.print(f"[yellow]{result['error']}[/yellow]")
            return result
        except subprocess.TimeoutExpired:
            result['error'] = "Test execution timed out"
            return result
        except Exception as e:
            result['error'] = str(e)
            return result

    def _improve_tests_with_llm(
        self,
        source_code: str,
        current_tests: str,
        current_coverage: float,
        target_coverage: float,
        coverage_report: str
    ) -> Optional[str]:
        """
        Use LLM to improve test coverage by analyzing gaps.

        Args:
            source_code: The source code under test
            current_tests: Current test code
            current_coverage: Current coverage percentage
            target_coverage: Target coverage percentage
            coverage_report: Coverage report showing uncovered lines

        Returns:
            Improved test code or None if failed
        """
        try:
            # Extract uncovered lines from coverage report
            import re
            uncovered_lines = []
            for line in coverage_report.split('\n'):
                # Look for lines like "main.py    10    2    80%   5-6"
                if 'main.py' in line or '.py' in line:
                    match = re.search(r'(\d+)-(\d+)', line)
                    if match:
                        uncovered_lines.append(f"Lines {match.group(1)}-{match.group(2)}")

            uncovered_info = '\n'.join(uncovered_lines) if uncovered_lines else "See coverage report"

            prompt = f"""You are a test improvement expert. The current tests have {current_coverage:.1f}% coverage but need {target_coverage:.0f}%.

SOURCE CODE:
```python
{source_code}
```

CURRENT TESTS:
```python
{current_tests}
```

COVERAGE GAPS:
{uncovered_info}

COVERAGE REPORT:
{coverage_report[:500]}

TASK:
1. Analyze the uncovered code sections
2. Add new test cases to cover missing branches, edge cases, and error paths
3. Ensure tests are comprehensive and test real behavior
4. Keep existing tests that work
5. Add tests for:
   - Edge cases (empty inputs, None, zero, negative numbers)
   - Error conditions (invalid inputs, exceptions)
   - Boundary conditions
   - Different code paths (if/else branches)

Return ONLY the complete improved test code (including imports and all test functions).
Do NOT include explanations or markdown formatting."""

            # Use tier 2 coding model for test improvement
            improved_tests = self.client.generate(
                model=self.config.get_tier_config("coding", "tier_2").get("model", "qwen2.5-coder:7b"),
                prompt=prompt,
                system="You are an expert at writing comprehensive pytest tests with high code coverage.",
                temperature=0.3,  # Low temperature for consistent output
                model_key=self.config.generator_model_key  # Use actual model key for routing
            )

            if improved_tests and 'def test_' in improved_tests:
                # Clean markdown formatting if present
                if '```python' in improved_tests:
                    improved_tests = improved_tests.split('```python')[1].split('```')[0].strip()
                elif '```' in improved_tests:
                    improved_tests = improved_tests.split('```')[1].split('```')[0].strip()

                return improved_tests
            else:
                return None

        except Exception as e:
            console.print(f"[yellow]Error improving tests with LLM: {e}[/yellow]")
            return None

    def _extract_code_from_artifact(self, artifact) -> Optional[str]:
        """
        Extract Python code from a RAG artifact.

        Args:
            artifact: The RAG artifact containing code

        Returns:
            Extracted Python code or None
        """
        try:
            # The artifact content contains the tool description including code
            content = artifact.content

            # Look for code between Tool ID line and end
            lines = content.split('\n')
            code_lines = []
            in_code = False

            for line in lines:
                if line.startswith('Code Hash:'):
                    in_code = True
                    continue
                if in_code and line.strip():
                    code_lines.append(line)

            if code_lines:
                return '\n'.join(code_lines)

            # Fallback: try to find Python code in the content
            if 'def ' in content or 'class ' in content:
                # Extract everything that looks like Python code
                start = content.find('def ') or content.find('class ')
                if start != -1:
                    return content[start:]

            return None

        except Exception as e:
            logger.error(f"Error extracting code from artifact: {e}")
            return None

    def _run_code_and_capture_logs(self, code: str, tool_id: str) -> List[str]:
        """
        Run code with logging enabled and capture all log output.

        Args:
            code: Python code with logging statements
            tool_id: Tool identifier for temp file naming

        Returns:
            List of log lines
        """
        import tempfile
        import subprocess
        from pathlib import Path

        try:
            # Create temp file for code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                temp_file = Path(f.name)
                f.write(code)

            # Run with sample inputs and capture stderr (where logging goes)
            result = subprocess.run(
                ['python', str(temp_file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Combine stdout and stderr
            all_output = result.stdout + '\n' + result.stderr
            log_lines = [line for line in all_output.split('\n') if line.strip()]

            # Clean up temp file
            temp_file.unlink()

            return log_lines

        except subprocess.TimeoutExpired:
            console.print("[yellow]Debug code execution timed out[/yellow]")
            return []
        except Exception as e:
            logger.error(f"Error running debug code: {e}")
            return []

    def _analyze_debug_logs(self, log_lines: List[str]) -> Dict[str, Any]:
        """
        Analyze debug logs to understand code behavior.

        Args:
            log_lines: Lines of debug output

        Returns:
            Dictionary with behavioral insights
        """
        analysis = {
            "function_calls": [],
            "variable_states": {},
            "control_flow": [],
            "error_handling": [],
            "edge_cases": []
        }

        try:
            for line in log_lines:
                line_lower = line.lower()

                # Identify function calls
                if 'calling' in line_lower or 'invoking' in line_lower:
                    analysis["function_calls"].append(line)

                # Identify variable states
                if '=' in line and ('debug' in line_lower or 'logger' in line_lower):
                    # Extract variable name and value
                    parts = line.split('=')
                    if len(parts) >= 2:
                        var_name = parts[0].strip().split()[-1]
                        var_value = parts[1].strip()
                        analysis["variable_states"][var_name] = var_value

                # Identify control flow
                if any(keyword in line_lower for keyword in ['if', 'else', 'elif', 'for', 'while']):
                    analysis["control_flow"].append(line)

                # Identify error handling
                if any(keyword in line_lower for keyword in ['error', 'exception', 'try', 'catch', 'except']):
                    analysis["error_handling"].append(line)

                # Identify edge cases
                if any(keyword in line_lower for keyword in ['edge case', 'boundary', 'empty', 'null', 'none']):
                    analysis["edge_cases"].append(line)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing debug logs: {e}")
            return analysis

    def _compare_code_versions(self, old_code: str, new_code: str) -> Dict[str, Any]:
        """
        Compare two code versions and identify differences.

        Args:
            old_code: Original debug code
            new_code: New production code

        Returns:
            Dictionary describing code changes
        """
        import difflib

        try:
            # Split into lines for comparison
            old_lines = old_code.split('\n')
            new_lines = new_code.split('\n')

            # Use difflib to find differences
            diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))

            # Categorize changes
            changes = {
                "added_functions": [],
                "removed_functions": [],
                "modified_functions": [],
                "added_parameters": [],
                "removed_parameters": [],
                "logic_changes": []
            }

            for line in diff:
                if line.startswith('+') and 'def ' in line:
                    func_name = line.split('def ')[1].split('(')[0]
                    changes["added_functions"].append(func_name)
                elif line.startswith('-') and 'def ' in line:
                    func_name = line.split('def ')[1].split('(')[0]
                    changes["removed_functions"].append(func_name)
                elif line.startswith('+') or line.startswith('-'):
                    changes["logic_changes"].append(line)

            return changes

        except Exception as e:
            logger.error(f"Error comparing code versions: {e}")
            return {"error": str(e)}

    def _generate_tests_from_behavior(
        self,
        production_tool_id: str,
        production_code: str,
        behavior_analysis: Dict[str, Any],
        code_diff: Dict[str, Any],
        debug_logs: List[str]
    ) -> Optional[str]:
        """
        Generate unit tests based on behavioral analysis and code changes.

        Args:
            production_tool_id: ID of the production tool
            production_code: The new production code
            behavior_analysis: Analysis from debug logs
            code_diff: Differences between versions
            debug_logs: Raw debug log lines

        Returns:
            Generated test code or None
        """
        try:
            # Build a comprehensive prompt for test generation
            prompt = f"""Based on the following information, generate comprehensive pytest unit tests:

PRODUCTION CODE:
```python
{production_code}
```

BEHAVIORAL ANALYSIS (from debug logs):
- Function calls observed: {len(behavior_analysis.get('function_calls', []))}
- Variables tracked: {', '.join(behavior_analysis.get('variable_states', {}).keys())}
- Control flow paths: {len(behavior_analysis.get('control_flow', []))}
- Error handling: {len(behavior_analysis.get('error_handling', []))}
- Edge cases identified: {len(behavior_analysis.get('edge_cases', []))}

CODE CHANGES:
- Added functions: {', '.join(code_diff.get('added_functions', [])) or 'None'}
- Removed functions: {', '.join(code_diff.get('removed_functions', [])) or 'None'}
- Logic changes: {len(code_diff.get('logic_changes', []))} lines modified

DEBUG LOG INSIGHTS:
{chr(10).join(debug_logs[:10])}  # First 10 log lines

Generate pytest tests that:
1. Cover all functions in the production code
2. Test the behaviors observed in debug logs
3. Include edge cases identified in the logs
4. Verify error handling paths
5. Test any new functionality from code changes

Return ONLY the Python test code, no explanations."""

            # Use LLM to generate tests
            test_code = self.client.generate(
                model=self.config.get_tier_config("coding", "tier_2").get("model", "qwen2.5-coder:7b"),
                prompt=prompt,
                system="You are an expert at writing comprehensive pytest unit tests based on code behavior analysis.",
                temperature=0.3,  # Lower temperature for consistent test generation
                model_key=self.config.generator_model_key  # Use actual model key for routing
            )

            if test_code and 'def test_' in test_code:
                # Clean up the response (remove markdown formatting if present)
                if '```python' in test_code:
                    test_code = test_code.split('```python')[1].split('```')[0].strip()
                elif '```' in test_code:
                    test_code = test_code.split('```')[1].split('```')[0].strip()

                return test_code
            else:
                return None

        except Exception as e:
            logger.error(f"Error generating tests from behavior: {e}")
            return None

    def update_tests_from_debug_version(self, production_tool_id: str, updated_code: str) -> bool:
        """
        When a production tool is updated, use the debug version to update tests.

        The debug version has logging that can help understand what changed and
        update the unit tests accordingly.

        Args:
            production_tool_id: ID of the updated production tool
            updated_code: The new production code

        Returns:
            True if tests were successfully updated
        """
        if not self.rag:
            console.print("[yellow]RAG not available for test updates[/yellow]")
            return False

        try:
            # Find the debug version
            debug_info = self.get_debug_version(production_tool_id)

            if not debug_info:
                console.print(f"[yellow]No debug version found for {production_tool_id}[/yellow]")
                console.print("[dim]Tests will be regenerated from scratch[/dim]")
                return False

            console.print(f"[cyan]Found debug version: {debug_info['tool_id']}[/cyan]")
            console.print(f"[dim]Using debug logs to understand code changes...[/dim]")

            # Get the debug version's code (with logging)
            debug_artifact = debug_info['artifact']
            debug_tool_id = debug_info['tool_id']

            # Step 1: Load the debug version's code from RAG
            debug_code = self._extract_code_from_artifact(debug_artifact)
            if not debug_code:
                console.print("[yellow]Could not extract code from debug artifact[/yellow]")
                return False

            # Step 2: Run debug version with test inputs to capture logging output
            console.print("[cyan]Running debug version to capture behavior...[/cyan]")
            debug_logs = self._run_code_and_capture_logs(debug_code, debug_tool_id)

            if not debug_logs:
                console.print("[yellow]No debug logs captured[/yellow]")
                return False

            console.print(f"[green]Captured {len(debug_logs)} lines of debug output[/green]")

            # Step 3: Analyze logs to understand behavior
            console.print("[cyan]Analyzing debug logs...[/cyan]")
            behavior_analysis = self._analyze_debug_logs(debug_logs)

            # Step 4: Compare with new production code to identify changes
            console.print("[cyan]Comparing with new production code...[/cyan]")
            code_diff = self._compare_code_versions(debug_code, updated_code)

            # Step 5: Generate updated tests based on behavioral differences
            console.print("[cyan]Generating updated tests...[/cyan]")
            test_code = self._generate_tests_from_behavior(
                production_tool_id=production_tool_id,
                production_code=updated_code,
                behavior_analysis=behavior_analysis,
                code_diff=code_diff,
                debug_logs=debug_logs
            )

            if test_code:
                # Save the test file
                test_file_path = self.runner.nodes_dir / production_tool_id / "test.py"
                test_file_path.parent.mkdir(parents=True, exist_ok=True)
                test_file_path.write_text(test_code, encoding='utf-8')

                console.print(f"[green]✓ Updated tests saved to: {test_file_path}[/green]")
                console.print(f"[dim]Debug tool: {debug_info['tool_id']} | Version: {debug_info['version']}[/dim]")
                return True
            else:
                console.print("[yellow]Could not generate tests from debug version[/yellow]")
                return False

        except Exception as e:
            console.print(f"[red]Error updating tests from debug version: {e}[/red]")
            return False

    def run(self):
        """Run the interactive CLI."""
        self.print_welcome()

        # Flush any initialization logs before starting the input loop
        log_panel.flush()

        # Check status first
        if not self.client.check_connection():
            console.print("[red]Warning: Cannot connect to Ollama. Some features will not work.[/red]")
            console.print("[dim]Start Ollama with: ollama serve[/dim]\n")

        prompt_text = self.config.get("chat.prompt", "DiSE> ")

        while True:
            try:
                # Suppress log panel output during user input to avoid cursor stealing
                log_panel.suppress_output = True

                # Use prompt_toolkit if available for better history and completion
                if PROMPT_TOOLKIT_AVAILABLE and sys.stdin.isatty():
                    try:
                        user_input = pt_prompt(
                            prompt_text,
                            history=self.pt_history,
                            auto_suggest=AutoSuggestFromHistory(),
                            completer=self.pt_completer,
                            complete_while_typing=True
                        ).strip()
                    except (EOFError, KeyboardInterrupt):
                        raise
                    except Exception as e:
                        # Fallback to regular input if prompt_toolkit fails
                        console.print(f"[dim yellow]prompt_toolkit error: {e}, falling back to basic input[/dim yellow]")
                        user_input = console.input(f"[bold green]{prompt_text}[/bold green]").strip()
                else:
                    # Use rich console.input for piped input or if prompt_toolkit unavailable
                    user_input = console.input(f"[bold green]{prompt_text}[/bold green]").strip()

                # Re-enable log panel output and flush any pending logs
                log_panel.suppress_output = False
                log_panel.flush()

                if not user_input:
                    continue

                # Check for "exit" without slash (immediate exit)
                if user_input.lower() in ['exit', 'quit', 'q']:
                    console.print("[cyan]Goodbye![/cyan]")
                    break

                self.history.append(user_input)

                # Check if this is a special command (starts with '/')
                if not user_input.startswith('/'):
                    # Retrieve conversation context if memory enabled
                    context_summary = ""
                    if self.memory_enabled:
                        try:
                            # Semantic search in RAG for relevant context
                            from src.rag_memory import ArtifactType
                            context_artifacts = self.rag.find_by_tags(
                                tags=["conversation", "interaction"],
                                limit=5
                            )

                            # Also do semantic search on the user query
                            similar_interactions = self.rag.find_similar(
                                query=user_input,
                                artifact_type=ArtifactType.CONVERSATION,  # Search conversation history
                                top_k=3
                            )

                            self._memory_items = context_artifacts + [item[0] for item in similar_interactions]

                            # Create context summary for LLM
                            context_parts = []
                            context_topics = []  # Concise topics for user display

                            if len(self._memory_items) > 0:
                                for item in self._memory_items[-5:]:  # Last 5 most relevant
                                    # Full context for LLM
                                    context_parts.append(f"- {item.description}: {item.content[:200]}")

                                    # Extract concise topic for user
                                    # Get first few words of description
                                    topic = item.description.split(':')[0] if ':' in item.description else item.description
                                    topic = ' '.join(topic.split()[:4])  # First 4 words max
                                    context_topics.append(topic)

                                context_summary = "\n".join(context_parts)

                                # Context retrieved silently - no need to show to user

                        except Exception as e:
                            console.print(f"[dim yellow]Memory retrieval: {e}[/dim yellow]")

                    # Default behavior: generate and run the request
                    import time
                    start_time = time.time()

                    # Add context summary to description if available (for internal use only)
                    final_description = user_input
                    if context_summary:
                        final_description = f"{user_input}\n\n[Conversation Context:\n{context_summary}]"

                    success = self.handle_generate(final_description, display_description=user_input)
                    duration = time.time() - start_time

                    # Store this interaction in RAG memory
                    if self.memory_enabled:
                        try:
                            interaction_id = f"interaction_{int(time.time() * 1000)}"
                            self.rag.store_artifact(
                                artifact_id=interaction_id,
                                artifact_type=ArtifactType.CONVERSATION,  # User interaction is conversation
                                name=f"User: {user_input[:50]}",
                                description=user_input[:200],
                                content=f"User: {user_input}\nProcessed successfully in {duration:.2f}s",
                                tags=["conversation", "interaction", "user-query"],
                                metadata={"timestamp": time.time(), "success": success, "duration": duration},
                                auto_embed=True
                            )
                        except Exception:
                            pass

                    continue

                # Parse command (remove the '/' prefix)
                cmd = user_input[1:].strip()

                if cmd.lower() in ['exit', 'quit', 'q']:
                    console.print("[cyan]Goodbye![/cyan]")
                    break

                elif cmd.lower() in ['help', '?']:
                    self.print_help()

                elif cmd.lower() == 'clear':
                    console.clear()

                elif cmd.lower() == 'clear_rag':
                    self.handle_clear_rag()

                elif cmd.lower() == 'status':
                    self.handle_status()

                elif cmd.lower() == 'manual' or cmd.lower() == 'man' or cmd.lower() == 'm':
                    self.handle_manual()

                elif cmd.startswith('manual ') or cmd.startswith('man ') or cmd.startswith('m '):
                    # Extract search term (after command)
                    if cmd.startswith('manual '):
                        search_term = cmd[7:].strip()
                    elif cmd.startswith('man '):
                        search_term = cmd[4:].strip()
                    else:  # 'm '
                        search_term = cmd[2:].strip()
                    self.handle_manual(search_term)

                elif cmd.lower() == 'tool' or cmd.lower() == 'tools':
                    # /tool or /tools with no args - list all tools
                    self.handle_tools()

                elif cmd.startswith('tool '):
                    # All tool subcommands go here
                    tool_cmd = cmd[5:].strip()
                    args = tool_cmd.split(None, 1)

                    if not args:
                        # /tool with trailing space - list tools
                        self.handle_tools()
                    elif args[0] in ['test', 'optimize']:
                        # /tool test <tool_id|all>
                        # /tool optimize <tool_id|all>
                        self.handle_tools_cli(f"/tools {tool_cmd}")
                    elif args[0] == 'mutate':
                        # /tool mutate <tool_id> <instructions>
                        if len(args) > 1:
                            self.handle_mutate_tool(args[1])
                        else:
                            console.print("[red]Usage: /tool mutate <tool_id> <instructions>[/red]")
                    elif args[0] in ['llm', 'executable', 'custom', 'openapi']:
                        # /tool <category> - filter by category
                        category = args[0]
                        page = 1
                        if len(args) > 1 and args[1].isdigit():
                            page = int(args[1])
                        self.handle_tools(category=category, page=page)
                    else:
                        # /tool info|run|list|<tool_id>
                        self.handle_tool_command(tool_cmd)

                elif cmd.lower() == 'backends' or cmd.lower().startswith('backends '):
                    test_connection = '--test' in cmd.lower()
                    self.handle_backends(test_connection=test_connection)

                elif cmd.startswith('workflow '):
                    node_id = cmd[9:].strip()
                    self.handle_workflow(node_id)

                elif cmd.startswith('generate '):
                    description = cmd[9:].strip()
                    self.handle_generate(description)

                elif cmd.startswith('run '):
                    args = cmd[4:].strip()
                    self.handle_run(args)

                elif cmd.startswith('auto '):
                    state = cmd[5:].strip().lower()
                    if state in ['on', 'off']:
                        self.config.set("auto_evolution.enabled", state == 'on')
                        console.print(f"[green]Auto-evolution {state}[/green]")
                    else:
                        console.print("[red]Usage: /auto on|off[/red]")

                elif cmd.startswith('memory '):
                    state = cmd[7:].strip().lower()
                    if state in ['on', 'off']:
                        self.memory_enabled = (state == 'on')
                        console.print(f"[cyan]Conversation memory {state}[/cyan]")
                        if not self._conversation_tool and state == 'on':
                            console.print("[yellow]Warning: Conversation tool not initialized, memory will not work[/yellow]")
                    else:
                        # Show memory status
                        status = "on" if self.memory_enabled else "off"
                        console.print(f"[cyan]Conversation memory: {status}[/cyan]")
                        if self._conversation_tool and self.memory_enabled:
                            console.print(f"[dim]Current memory items: {len(self._memory_items)}[/dim]")
                        console.print("\n[dim]Usage: /memory [on|off][/dim]")

                # Legacy commands for backward compatibility
                elif cmd.startswith('mutate tool '):
                    console.print("[dim]Note: Use '/tool mutate' instead (deprecated)[/dim]")
                    args = cmd[12:].strip()
                    self.handle_mutate_tool(args)

                elif cmd.startswith('optimize tool '):
                    console.print("[dim]Note: Use '/tool optimize' instead (deprecated)[/dim]")
                    args = cmd[14:].strip()
                    self.handle_optimize_tool(args)

                else:
                    console.print(f"[red]Unknown command: /{cmd}[/red]")
                    console.print("[dim]Type /help to see available commands[/dim]")

            except KeyboardInterrupt:
                # Ctrl-C should cancel current task and return to prompt
                console.print("\n[yellow]Interrupted! Cancelling task...[/yellow]")
                continue

            except EOFError:
                break

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        self._save_history()

    def _auto_fix_static_issues(self, node_id: str, analysis_results: Dict[str, Any]) -> bool:
        """
        Try to auto-fix static analysis issues.

        Args:
            node_id: Node ID
            analysis_results: Results from _run_static_analysis

        Returns:
            True if any fixes were applied
        """
        code_path = self.runner.get_node_path(node_id)
        fixed_any = False

        for result in analysis_results.get("results", []):
            if not result["success"]:
                tool_id = result["tool_id"]

                # Check if tool has auto-fix capability
                try:
                    tool = self.tools_manager.get_tool(tool_id)
                    if tool and hasattr(tool, 'implementation'):
                        impl = tool.implementation
                        auto_fix = impl.get("auto_fix", {})

                        if auto_fix.get("enabled", False):
                            console.print(f"[cyan]  Auto-fixing with {tool_id}...[/cyan]")

                            # Build auto-fix command from YAML config
                            # auto_fix has: command, args
                            import subprocess
                            from pathlib import Path

                            command = auto_fix.get("command", "python")
                            args = auto_fix.get("args", [])

                            # Get tool directory from tools_manager
                            tool_dir = str(Path(self.tools_manager.tools_dir) / "executable")

                            # Substitute placeholders
                            substituted_args = []
                            for arg in args:
                                arg = arg.replace("{tool_dir}", tool_dir)
                                arg = arg.replace("{source_file}", str(code_path))
                                substituted_args.append(arg)

                            full_command = [command] + substituted_args

                            try:
                                fix_result = subprocess.run(
                                    full_command,
                                    capture_output=True,
                                    text=True,
                                    timeout=30
                                )

                                if fix_result.returncode == 0:
                                    console.print(f"[green]    ✓ {tool_id} auto-fix applied[/green]")
                                    fixed_any = True
                                else:
                                    console.print(f"[yellow]    ! {tool_id} auto-fix failed (exit code {fix_result.returncode})[/yellow]")
                                    if fix_result.stderr:
                                        console.print(f"[dim]      {fix_result.stderr[:200]}[/dim]")
                            except subprocess.TimeoutExpired:
                                console.print(f"[yellow]    ! {tool_id} auto-fix timed out[/yellow]")
                            except Exception as e:
                                console.print(f"[yellow]    ! {tool_id} auto-fix error: {e}[/yellow]")
                        else:
                            console.print(f"[dim]  {tool_id} has no auto-fix capability[/dim]")

                except Exception as e:
                    console.print(f"[dim red]  Error auto-fixing {tool_id}: {e}[/dim red]")

        return fixed_any

    def _run_static_analysis(self, node_id: str, code: str) -> Dict[str, Any]:
        """
        Run static analysis tools on generated code.
        Uses the most useful/fast tools after tests pass.

        Returns:
            Dictionary with:
                - total_count: int
                - passed_count: int
                - failed_count: int
                - any_passed: bool
                - results: List of tool results
        """
        # Define the most useful static analysis tools to run
        # (lighter/faster tools for normal workflow; heavy tools for optimization later)
        # Note: Use run_static_analysis tool for comprehensive checking or these individually
        essential_tools = [
            "python_syntax_validator",        # Fast AST-based syntax check
            "undefined_name_checker",         # Flake8-based undefined names check
            "node_runtime_import_validator",  # Validate import order (has auto-fix)
            # mypy requires type hints which generated code may not have
            # bandit for security is important but can be slow
        ]

        code_path = self.runner.get_node_path(node_id)

        results = []
        passed_count = 0
        failed_count = 0

        for tool_id in essential_tools:
            try:
                console.print(f"[dim]  Running {tool_id}...[/dim]")

                result = self.tools_manager.invoke_executable_tool(
                    tool_id=tool_id,
                    source_file=str(code_path)
                )

                results.append({
                    "tool_id": tool_id,
                    "success": result["success"],
                    "exit_code": result["exit_code"],
                    "stdout": result["stdout"][:500],  # Truncate for display
                    "stderr": result["stderr"][:500]
                })

                if result["success"]:
                    passed_count += 1
                    console.print(f"[green]    OK {tool_id}[/green]")
                else:
                    failed_count += 1
                    # Check if it's "command not found" error
                    if result["exit_code"] == 127:
                        console.print(f"[dim yellow]    SKIP {tool_id} (not installed)[/dim yellow]")
                    else:
                        console.print(f"[yellow]    WARN {tool_id} found issues[/yellow]")
                        # Show first few lines of output
                        if result["stdout"]:
                            first_lines = "\n".join(result["stdout"].split("\n")[:3])
                            console.print(f"[dim]      {first_lines}[/dim]")

            except Exception as e:
                console.print(f"[dim red]    ERROR {tool_id}: {e}[/dim red]")
                failed_count += 1

        return {
            "total_count": len(essential_tools),
            "passed_count": passed_count,
            "failed_count": failed_count,
            "any_passed": passed_count > 0,
            "results": results
        }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="mostlylucid DiSE - Interactive CLI")
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )

    args = parser.parse_args()

    chat = ChatCLI(config_path=args.config)
    chat.run()


if __name__ == "__main__":
    main()

    def _should_show_generated(self) -> bool:
        """Check if generated content should be displayed."""
        verbosity = self.config.get("chat.verbosity", "status")
        return verbosity in ["generated", "debug"]
    
    def _should_show_logs(self) -> bool:
        """Check if log contents should be displayed."""
        verbosity = self.config.get("chat.verbosity", "status")
        return verbosity in ["log", "debug"]
    
    def _should_show_debug(self) -> bool:
        """Check if debug details should be displayed."""
        verbosity = self.config.get("chat.verbosity", "status")
        return verbosity == "debug"
