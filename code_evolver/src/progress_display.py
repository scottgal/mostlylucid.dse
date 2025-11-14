"""
Progress Display System
Shows clear progress information during code evolution with token estimation and speed metrics.
"""
import time
import logging
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Stage(Enum):
    """Code evolution stages."""
    INITIALIZATION = "Initialization"
    OVERSEER_PLANNING = "Overseer Planning"
    CODE_GENERATION = "Code Generation"
    TESTING = "Testing"
    EVALUATION = "Evaluation"
    RAG_STORAGE = "RAG Storage"
    EVOLUTION = "Evolution"
    COMPLETE = "Complete"


class ProgressDisplay:
    """
    Displays progress information during code evolution.
    Shows stage, estimated tokens, processing speed, and optimization metrics.
    """

    def __init__(self, use_rich: bool = True):
        """
        Initialize progress display.

        Args:
            use_rich: Use rich library for enhanced display (if available)
        """
        self.use_rich = use_rich and RICH_AVAILABLE
        self.console = Console() if self.use_rich else None
        self.current_stage = None
        self.stage_start_time = None
        self.total_start_time = None
        self.metrics = {}
        self.token_estimates = {}
        self.speed_metrics = {}

    def start(self, task_description: str):
        """
        Start progress tracking for a task.

        Args:
            task_description: Description of the task being performed
        """
        self.total_start_time = time.time()
        if self.use_rich:
            self.console.print(Panel(
                f"[bold cyan]{task_description}[/bold cyan]",
                title="Code Evolver",
                border_style="cyan"
            ))
        else:
            print(f"\n{'='*60}")
            print(f"CODE EVOLVER - {task_description}")
            print(f"{'='*60}\n")

    def enter_stage(self, stage: Stage, details: Optional[str] = None):
        """
        Enter a new processing stage.

        Args:
            stage: The stage being entered
            details: Optional additional details about the stage
        """
        self.current_stage = stage
        self.stage_start_time = time.time()

        message = f"[Stage] {stage.value}"
        if details:
            message += f": {details}"

        if self.use_rich:
            self.console.print(f"\n[bold yellow]> {stage.value}[/bold yellow]")
            if details:
                self.console.print(f"  [dim]{details}[/dim]")
        else:
            print(f"\n> {message}")

    def exit_stage(self, success: bool = True):
        """
        Exit the current stage.

        Args:
            success: Whether the stage completed successfully
        """
        if not self.stage_start_time:
            return

        duration = time.time() - self.stage_start_time
        status = "[OK]" if success else "[FAIL]"
        stage_name = self.current_stage.value if self.current_stage else "Unknown"

        if self.use_rich:
            color = "green" if success else "red"
            self.console.print(f"[{color}]{status} {stage_name} completed in {duration:.2f}s[/{color}]")
        else:
            print(f"{status} {stage_name} completed in {duration:.2f}s")

    def update_token_estimate(self, stage: str, estimated_tokens: int, model: str):
        """
        Update token estimation for a stage.

        Args:
            stage: Stage name
            estimated_tokens: Estimated number of tokens
            model: Model being used
        """
        self.token_estimates[stage] = {
            "tokens": estimated_tokens,
            "model": model,
            "timestamp": datetime.now()
        }

        if self.use_rich:
            self.console.print(
                f"  [cyan]> Estimated tokens:[/cyan] ~{estimated_tokens:,} tokens "
                f"[dim]({model})[/dim]"
            )
        else:
            print(f"  > Estimated tokens: ~{estimated_tokens:,} tokens ({model})")

    def update_speed(self, tokens_per_second: float, chars_per_second: float):
        """
        Update processing speed metrics.

        Args:
            tokens_per_second: Tokens processed per second
            chars_per_second: Characters processed per second
        """
        self.speed_metrics = {
            "tokens_per_sec": tokens_per_second,
            "chars_per_sec": chars_per_second,
            "timestamp": datetime.now()
        }

        if self.use_rich:
            self.console.print(
                f"  [cyan]> Speed:[/cyan] {tokens_per_second:.1f} tokens/s, "
                f"{chars_per_second:.1f} chars/s"
            )
        else:
            print(f"  > Speed: {tokens_per_second:.1f} tokens/s, {chars_per_second:.1f} chars/s")

    def show_optimization_progress(self, iteration: int, score: float, improvement: float):
        """
        Show optimization progress.

        Args:
            iteration: Current iteration number
            score: Current quality score
            improvement: Improvement from previous iteration
        """
        if self.use_rich:
            color = "green" if improvement > 0 else "yellow" if improvement == 0 else "red"
            arrow = "^" if improvement > 0 else "-" if improvement == 0 else "v"
            self.console.print(
                f"  [bold]Iteration {iteration}:[/bold] "
                f"Score = {score:.3f} "
                f"[{color}]{arrow} {improvement:+.3f}[/{color}]"
            )
        else:
            arrow = "^" if improvement > 0 else "-" if improvement == 0 else "v"
            print(f"  Iteration {iteration}: Score = {score:.3f} {arrow} {improvement:+.3f}")

    def show_metrics_table(self, metrics: Dict[str, Any]):
        """
        Show a table of metrics.

        Args:
            metrics: Dictionary of metrics to display
        """
        if self.use_rich:
            table = Table(title="Performance Metrics", show_header=True, header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right", style="yellow")

            for key, value in metrics.items():
                if isinstance(value, float):
                    formatted = f"{value:.3f}"
                elif isinstance(value, int):
                    formatted = f"{value:,}"
                else:
                    formatted = str(value)
                table.add_row(key.replace("_", " ").title(), formatted)

            self.console.print(table)
        else:
            print("\nPerformance Metrics:")
            print("-" * 40)
            for key, value in metrics.items():
                if isinstance(value, float):
                    formatted = f"{value:.3f}"
                elif isinstance(value, int):
                    formatted = f"{value:,}"
                else:
                    formatted = str(value)
                print(f"  {key.replace('_', ' ').title():<25} {formatted:>12}")
            print("-" * 40)

    def show_context_info(self, model: str, context_window: int, prompt_length: int):
        """
        Show context window usage information.

        Args:
            model: Model name
            context_window: Total context window size
            prompt_length: Current prompt length in tokens
        """
        usage_percent = (prompt_length / context_window) * 100
        remaining = context_window - prompt_length

        if self.use_rich:
            color = "green" if usage_percent < 70 else "yellow" if usage_percent < 90 else "red"
            self.console.print(
                f"  [cyan]> Context:[/cyan] [{color}]{prompt_length:,} / {context_window:,} tokens "
                f"({usage_percent:.1f}%)[/{color}] - {remaining:,} remaining"
            )
        else:
            print(
                f"  > Context: {prompt_length:,} / {context_window:,} tokens "
                f"({usage_percent:.1f}%) - {remaining:,} remaining"
            )

    def show_summary(self, success: bool, final_metrics: Dict[str, Any]):
        """
        Show final summary.

        Args:
            success: Whether the task completed successfully
            final_metrics: Final metrics to display
        """
        total_time = time.time() - self.total_start_time if self.total_start_time else 0

        if self.use_rich:
            title = "[bold green]SUCCESS[/bold green]" if success else "[bold red]FAILED[/bold red]"
            self.console.print("\n")
            self.console.print(Panel(
                f"{title}\n\nTotal time: {total_time:.2f}s",
                border_style="green" if success else "red"
            ))
            if final_metrics:
                self.show_metrics_table(final_metrics)
        else:
            status = "SUCCESS" if success else "FAILED"
            print(f"\n{'='*60}")
            print(f"{status} - Total time: {total_time:.2f}s")
            print(f"{'='*60}")
            if final_metrics:
                self.show_metrics_table(final_metrics)

    def log_message(self, message: str, level: str = "info"):
        """
        Log a message.

        Args:
            message: Message to log
            level: Log level (info, warning, error, success)
        """
        if self.use_rich:
            colors = {
                "info": "white",
                "warning": "yellow",
                "error": "red",
                "success": "green"
            }
            color = colors.get(level, "white")
            self.console.print(f"[{color}]{message}[/{color}]")
        else:
            print(f"  {message}")

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Uses rough approximation: 1 token ≈ 4 characters.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4


# Global instance for easy access
_progress_display = None


def get_progress_display() -> ProgressDisplay:
    """Get or create global progress display instance."""
    global _progress_display
    if _progress_display is None:
        _progress_display = ProgressDisplay()
    return _progress_display
