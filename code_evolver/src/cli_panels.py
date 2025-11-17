"""
CLI Visualization Panels

Modular, extensible panel system for real-time workflow and tool visualization.
Beautiful ASCII art flowcharts and animated tool assembly displays.
"""

import time
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich import box
from rich.align import Align


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Represents a step in a workflow visualization."""
    id: str
    name: str
    status: StepStatus = StepStatus.PENDING
    tool_name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Get step duration if completed."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class ToolComponent:
    """Represents a component being assembled in a tool."""
    name: str
    type: str  # "function", "import", "class", "validation", etc.
    status: StepStatus = StepStatus.PENDING
    lines_of_code: int = 0


class WorkflowFlowchartPanel:
    """
    ASCII art flowchart visualization for workflows.

    Shows workflow steps as a connected flowchart with boxes and arrows.
    """

    def __init__(self, title: str = "Workflow"):
        self.title = title
        self.steps: List[WorkflowStep] = []
        self._lock = threading.Lock()

    def add_step(self, step: WorkflowStep):
        """Add a step to the workflow."""
        with self._lock:
            self.steps.append(step)

    def update_step(self, step_id: str, status: StepStatus, **kwargs):
        """Update a step's status and metadata."""
        with self._lock:
            for step in self.steps:
                if step.id == step_id:
                    step.status = status
                    if status == StepStatus.ACTIVE and not step.start_time:
                        step.start_time = time.time()
                    elif status in (StepStatus.COMPLETED, StepStatus.FAILED) and not step.end_time:
                        step.end_time = time.time()
                    for key, value in kwargs.items():
                        setattr(step, key, value)
                    break

    def render(self) -> Panel:
        """Render the flowchart as a Rich Panel."""
        with self._lock:
            if not self.steps:
                content = Text("No workflow steps", style="dim")
                return Panel(content, title=f"[bold cyan]{self.title}[/bold cyan]", box=box.ROUNDED)

            lines = []

            for i, step in enumerate(self.steps):
                # Draw box for step
                lines.extend(self._render_step_box(step, i))

                # Draw arrow to next step (if not last)
                if i < len(self.steps) - 1:
                    lines.append(self._render_arrow(step))

            content = Text("\n".join(lines))
            return Panel(
                content,
                title=f"[bold cyan]{self.title}[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2)
            )

    def _render_step_box(self, step: WorkflowStep, index: int) -> List[str]:
        """Render a single step as a box."""
        # Determine box style and icon based on status
        if step.status == StepStatus.PENDING:
            border_char = "."
            icon = "○"
            style = "dim"
        elif step.status == StepStatus.ACTIVE:
            border_char = "="
            icon = "⚙"
            style = "bold yellow"
        elif step.status == StepStatus.COMPLETED:
            border_char = "─"
            icon = "✓"
            style = "green"
        elif step.status == StepStatus.FAILED:
            border_char = "x"
            icon = "✗"
            style = "red"
        else:  # SKIPPED
            border_char = "-"
            icon = "⊝"
            style = "dim"

        # Create box content
        width = 60
        step_num = f"Step {index + 1}"

        # Top border
        lines = [f"╔{'═' * (width - 2)}╗"]

        # Header line with step number and icon
        header = f" {icon} {step_num}: {step.name}"
        header_padded = header + " " * (width - len(header) - 2)
        lines.append(f"║{header_padded}║")

        # Tool name if present
        if step.tool_name:
            tool_line = f"   Tool: {step.tool_name}"
            tool_padded = tool_line + " " * (width - len(tool_line) - 2)
            lines.append(f"║{tool_padded}║")

        # Description if present
        if step.description:
            desc_line = f"   {step.description[:width-6]}"
            desc_padded = desc_line + " " * (width - len(desc_line) - 2)
            lines.append(f"║{desc_padded}║")

        # Duration if completed
        if step.duration is not None:
            duration_line = f"   Duration: {step.duration:.2f}s"
            duration_padded = duration_line + " " * (width - len(duration_line) - 2)
            lines.append(f"║{duration_padded}║")

        # Bottom border
        lines.append(f"╚{'═' * (width - 2)}╝")

        return lines

    def _render_arrow(self, step: WorkflowStep) -> str:
        """Render an arrow connecting steps."""
        if step.status == StepStatus.COMPLETED:
            return "     ║\n     ▼"
        elif step.status == StepStatus.ACTIVE:
            return "     ║\n     ▽"
        else:
            return "     ┆\n     :"


class ToolAssemblyPanel:
    """
    Real-time visualization of tool development/assembly.

    Shows components being built with progress indicators.
    """

    def __init__(self, tool_name: str = "Tool"):
        self.tool_name = tool_name
        self.components: List[ToolComponent] = []
        self.progress_message: str = "Initializing..."
        self.total_lines: int = 0
        self._lock = threading.Lock()

    def add_component(self, component: ToolComponent):
        """Add a component to the tool."""
        with self._lock:
            self.components.append(component)

    def update_component(self, name: str, status: StepStatus, **kwargs):
        """Update a component's status."""
        with self._lock:
            for comp in self.components:
                if comp.name == name:
                    comp.status = status
                    for key, value in kwargs.items():
                        setattr(comp, key, value)
                    break

    def set_progress(self, message: str):
        """Set progress message."""
        with self._lock:
            self.progress_message = message

    def render(self) -> Panel:
        """Render the tool assembly visualization."""
        with self._lock:
            content_parts = []

            # Header with tool name
            header = Text()
            header.append("🔧 Building: ", style="cyan")
            header.append(self.tool_name, style="bold yellow")
            content_parts.append(header)
            content_parts.append(Text())  # Blank line

            # Progress message
            progress_text = Text(f"⚡ {self.progress_message}", style="cyan")
            content_parts.append(progress_text)
            content_parts.append(Text())  # Blank line

            if not self.components:
                content_parts.append(Text("Analyzing requirements...", style="dim"))
            else:
                # Component assembly visualization
                content_parts.append(Text("Components:", style="bold"))
                content_parts.append(Text())

                total_lines = sum(c.lines_of_code for c in self.components)

                for comp in self.components:
                    comp_text = self._render_component(comp)
                    content_parts.append(comp_text)

                # Statistics
                content_parts.append(Text())
                completed = sum(1 for c in self.components if c.status == StepStatus.COMPLETED)
                stats = Text()
                stats.append(f"Progress: {completed}/{len(self.components)} components", style="cyan")
                stats.append(f"  |  Total Lines: {total_lines}", style="dim")
                content_parts.append(stats)

            group = Group(*content_parts)
            return Panel(
                group,
                title=f"[bold magenta]Tool Assembly[/bold magenta]",
                border_style="magenta",
                box=box.ROUNDED,
                padding=(1, 2)
            )

    def _render_component(self, comp: ToolComponent) -> Text:
        """Render a single component."""
        text = Text()

        # Status icon
        if comp.status == StepStatus.PENDING:
            icon = "⬜"
            style = "dim"
        elif comp.status == StepStatus.ACTIVE:
            icon = "🔄"
            style = "yellow"
        elif comp.status == StepStatus.COMPLETED:
            icon = "✅"
            style = "green"
        elif comp.status == StepStatus.FAILED:
            icon = "❌"
            style = "red"
        else:
            icon = "⊝"
            style = "dim"

        text.append(f"  {icon} ", style=style)
        text.append(f"{comp.type.upper():<12}", style="cyan")
        text.append(f" {comp.name}", style=style)

        if comp.lines_of_code > 0:
            text.append(f"  ({comp.lines_of_code} lines)", style="dim")

        return text


class CompositePanelView:
    """
    Combines multiple panels into a unified display.

    Uses Rich Layout for sophisticated panel arrangements.
    """

    def __init__(self, console: Console):
        self.console = console
        self.panels: Dict[str, Any] = {}  # panel_id -> panel object
        self._lock = threading.Lock()

    def add_panel(self, panel_id: str, panel: Any):
        """Add a panel to the view."""
        with self._lock:
            self.panels[panel_id] = panel

    def remove_panel(self, panel_id: str):
        """Remove a panel from the view."""
        with self._lock:
            if panel_id in self.panels:
                del self.panels[panel_id]

    def render(self) -> Layout:
        """Render all panels in a layout."""
        with self._lock:
            if not self.panels:
                return Layout(Panel("No active panels", title="[dim]Display[/dim]"))

            # Create layout based on number of panels
            panel_list = list(self.panels.values())

            if len(panel_list) == 1:
                # Single panel - full width
                return Layout(panel_list[0].render())

            elif len(panel_list) == 2:
                # Two panels - side by side
                layout = Layout()
                layout.split_row(
                    Layout(panel_list[0].render(), name="left"),
                    Layout(panel_list[1].render(), name="right")
                )
                return layout

            else:
                # Multiple panels - grid layout
                layout = Layout()

                # Top panel (if workflow)
                if "workflow" in self.panels:
                    layout.split_column(
                        Layout(self.panels["workflow"].render(), name="top"),
                        Layout(name="bottom")
                    )

                    # Bottom panels side by side
                    bottom_panels = [p for pid, p in self.panels.items() if pid != "workflow"]
                    if len(bottom_panels) == 1:
                        layout["bottom"].update(bottom_panels[0].render())
                    else:
                        layout["bottom"].split_row(
                            *[Layout(p.render()) for p in bottom_panels]
                        )
                else:
                    # No workflow, just split panels
                    layout.split_row(
                        *[Layout(p.render()) for p in panel_list]
                    )

                return layout


class LivePanelDisplay:
    """
    Live updating display manager for CLI panels.

    Manages Rich Live display with automatic refresh for real-time updates.
    """

    def __init__(self, console: Console, refresh_per_second: int = 4):
        self.console = console
        self.refresh_per_second = refresh_per_second
        self.composite_view = CompositePanelView(console)
        self.live: Optional[Live] = None
        self._active = False
        self._lock = threading.Lock()

    def add_panel(self, panel_id: str, panel: Any):
        """Add a panel to the live display."""
        self.composite_view.add_panel(panel_id, panel)

    def remove_panel(self, panel_id: str):
        """Remove a panel from the live display."""
        self.composite_view.remove_panel(panel_id)

    def start(self):
        """Start the live display."""
        with self._lock:
            if not self._active:
                self.live = Live(
                    self.composite_view.render(),
                    console=self.console,
                    refresh_per_second=self.refresh_per_second,
                    screen=False
                )
                self.live.start()
                self._active = True

    def stop(self):
        """Stop the live display."""
        with self._lock:
            if self._active and self.live:
                self.live.stop()
                self._active = False
                self.live = None

    def update(self):
        """Manually trigger a display update."""
        if self._active and self.live:
            try:
                self.live.update(self.composite_view.render())
            except Exception:
                pass  # Ignore update errors

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


# Convenience factory functions

def create_workflow_panel(title: str = "Workflow") -> WorkflowFlowchartPanel:
    """Create a workflow flowchart panel."""
    return WorkflowFlowchartPanel(title)


def create_tool_assembly_panel(tool_name: str = "Tool") -> ToolAssemblyPanel:
    """Create a tool assembly panel."""
    return ToolAssemblyPanel(tool_name)


def create_live_display(console: Console, refresh_per_second: int = 4) -> LivePanelDisplay:
    """Create a live panel display."""
    return LivePanelDisplay(console, refresh_per_second)


# Example usage demonstration (not executed unless run as main)
if __name__ == "__main__":
    import time

    console = Console()

    # Demo 1: Workflow Flowchart
    console.print("\n[bold]Demo 1: Workflow Flowchart[/bold]\n")

    workflow_panel = create_workflow_panel("Code Generation Workflow")

    # Add steps
    workflow_panel.add_step(WorkflowStep(
        id="step1",
        name="Analyze Requirements",
        tool_name="task_analyzer",
        description="Parse user requirements and extract key features"
    ))
    workflow_panel.add_step(WorkflowStep(
        id="step2",
        name="Search RAG",
        tool_name="rag_search",
        description="Find similar solutions in knowledge base"
    ))
    workflow_panel.add_step(WorkflowStep(
        id="step3",
        name="Generate Code",
        tool_name="code_generator",
        description="Generate Python code based on requirements"
    ))
    workflow_panel.add_step(WorkflowStep(
        id="step4",
        name="Test & Validate",
        tool_name="test_runner",
        description="Run tests and validate outputs"
    ))

    with Live(workflow_panel.render(), console=console, refresh_per_second=4) as live:
        # Simulate workflow execution
        for step_id in ["step1", "step2", "step3", "step4"]:
            workflow_panel.update_step(step_id, StepStatus.ACTIVE)
            live.update(workflow_panel.render())
            time.sleep(1.5)

            workflow_panel.update_step(step_id, StepStatus.COMPLETED)
            live.update(workflow_panel.render())
            time.sleep(0.5)

    time.sleep(1)

    # Demo 2: Tool Assembly
    console.print("\n[bold]Demo 2: Tool Assembly[/bold]\n")

    tool_panel = create_tool_assembly_panel("UserDataValidator")

    # Add components
    components = [
        ToolComponent("imports", "import", lines_of_code=5),
        ToolComponent("validate_email", "function", lines_of_code=12),
        ToolComponent("validate_phone", "function", lines_of_code=15),
        ToolComponent("ValidationResult", "class", lines_of_code=20),
        ToolComponent("main", "function", lines_of_code=8),
    ]

    for comp in components:
        tool_panel.add_component(comp)

    with Live(tool_panel.render(), console=console, refresh_per_second=4) as live:
        # Simulate tool assembly
        for i, comp in enumerate(components):
            tool_panel.set_progress(f"Building component {i+1}/{len(components)}: {comp.name}")
            tool_panel.update_component(comp.name, StepStatus.ACTIVE)
            live.update(tool_panel.render())
            time.sleep(1)

            tool_panel.update_component(comp.name, StepStatus.COMPLETED)
            live.update(tool_panel.render())
            time.sleep(0.3)

        tool_panel.set_progress("Tool assembly complete!")
        live.update(tool_panel.render())
        time.sleep(2)

    console.print("\n[bold green]✓ All demos completed![/bold green]\n")
