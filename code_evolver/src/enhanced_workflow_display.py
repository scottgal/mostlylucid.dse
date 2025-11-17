"""
Enhanced Workflow Display

Drop-in replacement for WorkflowDisplay with advanced visualization panels.
Backward compatible with existing CLI code while adding rich visualizations.
"""

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

from .cli_panels import (
    WorkflowFlowchartPanel,
    ToolAssemblyPanel,
    LivePanelDisplay,
    WorkflowStep,
    ToolComponent,
    StepStatus,
    create_workflow_panel,
    create_tool_assembly_panel,
    create_live_display
)


class EnhancedWorkflowDisplay:
    """
    Enhanced workflow display with real-time visualization panels.

    Backward compatible with the original WorkflowDisplay interface,
    but adds beautiful ASCII art flowcharts and tool assembly animations.

    Usage:
        # Drop-in replacement - existing code works as-is
        display = EnhancedWorkflowDisplay(console)
        display.start_workflow("Generate code")
        display.start_stage("Planning", "Analyzing requirements")
        display.complete_stage("Planning", "Found 5 relevant tools")

        # New features - optional visualization panels
        display.enable_live_panels()  # Turn on real-time visualization
        display.show_workflow_flowchart()  # Show ASCII art flowchart
        display.show_tool_assembly("MyTool")  # Show tool being built
    """

    def __init__(self, console: Console, enable_panels: bool = False):
        """
        Initialize enhanced workflow display.

        Args:
            console: Rich Console instance
            enable_panels: Whether to enable live panel visualizations (default: False for compatibility)
        """
        self.console = console
        self.current_stage = None
        self.stages = []

        # Panel system (opt-in for backward compatibility)
        self._panels_enabled = enable_panels
        self._live_display: Optional[LivePanelDisplay] = None
        self._workflow_panel: Optional[WorkflowFlowchartPanel] = None
        self._tool_panel: Optional[ToolAssemblyPanel] = None
        self._current_workflow_step_id: Optional[str] = None

    def enable_live_panels(self, refresh_per_second: int = 4):
        """
        Enable live panel visualizations.

        Args:
            refresh_per_second: How often to refresh the display
        """
        if not self._panels_enabled:
            self._panels_enabled = True
            self._live_display = create_live_display(self.console, refresh_per_second)
            self._live_display.start()

    def disable_live_panels(self):
        """Disable live panel visualizations."""
        if self._live_display:
            self._live_display.stop()
            self._live_display = None
        self._panels_enabled = False

    def show_workflow_flowchart(self, title: str = "Workflow"):
        """
        Show workflow as ASCII art flowchart.

        Args:
            title: Title for the workflow panel
        """
        if not self._panels_enabled:
            self.enable_live_panels()

        self._workflow_panel = create_workflow_panel(title)
        if self._live_display:
            self._live_display.add_panel("workflow", self._workflow_panel)
            self._live_display.update()

    def show_tool_assembly(self, tool_name: str):
        """
        Show tool assembly visualization.

        Args:
            tool_name: Name of the tool being built
        """
        if not self._panels_enabled:
            self.enable_live_panels()

        self._tool_panel = create_tool_assembly_panel(tool_name)
        if self._live_display:
            self._live_display.add_panel("tool", self._tool_panel)
            self._live_display.update()

    def hide_workflow_flowchart(self):
        """Hide the workflow flowchart panel."""
        if self._live_display:
            self._live_display.remove_panel("workflow")
            self._live_display.update()
        self._workflow_panel = None

    def hide_tool_assembly(self):
        """Hide the tool assembly panel."""
        if self._live_display:
            self._live_display.remove_panel("tool")
            self._live_display.update()
        self._tool_panel = None

    # ==============================================
    # Original WorkflowDisplay Interface (Backward Compatible)
    # ==============================================

    def start_workflow(self, description: str):
        """
        Start a new workflow.

        Args:
            description: Workflow description
        """
        self.console.print(f"\n[bold cyan]{description}[/bold cyan]\n")
        self.stages = []

        # If panels enabled, show workflow flowchart
        if self._panels_enabled and not self._workflow_panel:
            self.show_workflow_flowchart(description)

    def add_stage(self, stage_name: str):
        """
        Add a stage to the workflow.

        Args:
            stage_name: Name of the stage
        """
        self.stages.append(stage_name)

    def show_stages(self):
        """Show workflow stages as a pipeline."""
        if not self.stages:
            return
        pipeline = " → ".join(self.stages)
        self.console.print(f"[dim]{pipeline}[/dim]\n")

    def start_stage(self, stage_name: str, status_text: str = None):
        """
        Start a stage with a simple status message.

        Args:
            stage_name: Name of the stage
            status_text: Optional status text (defaults to stage_name)
        """
        self.current_stage = stage_name
        display_text = status_text or stage_name
        self.console.print(f"[cyan]> {display_text}...[/cyan]")

        # Add to workflow flowchart if enabled
        if self._workflow_panel:
            step_id = f"step_{len(self._workflow_panel.steps)}"
            self._current_workflow_step_id = step_id

            step = WorkflowStep(
                id=step_id,
                name=stage_name,
                description=display_text if display_text != stage_name else None,
                status=StepStatus.ACTIVE
            )
            self._workflow_panel.add_step(step)
            if self._live_display:
                self._live_display.update()

        # Return a dummy context manager that does nothing
        class DummyContext:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass

        return DummyContext()

    def complete_stage(self, stage_name: str, result: str = None):
        """
        Mark a stage as complete.

        Args:
            stage_name: Name of the stage
            result: Optional result message
        """
        if result:
            self.console.print(f"[green]✓[/green] {stage_name}: {result}")
        else:
            self.console.print(f"[green]✓[/green] {stage_name}")

        # Update workflow flowchart if enabled
        if self._workflow_panel and self._current_workflow_step_id:
            self._workflow_panel.update_step(
                self._current_workflow_step_id,
                StepStatus.COMPLETED
            )
            if self._live_display:
                self._live_display.update()

    def fail_stage(self, stage_name: str, error: str = None):
        """
        Mark a stage as failed.

        Args:
            stage_name: Name of the stage
            error: Optional error message
        """
        if error:
            self.console.print(f"[red]✗[/red] {stage_name}: {error}")
        else:
            self.console.print(f"[red]✗[/red] {stage_name}")

        # Update workflow flowchart if enabled
        if self._workflow_panel and self._current_workflow_step_id:
            self._workflow_panel.update_step(
                self._current_workflow_step_id,
                StepStatus.FAILED
            )
            if self._live_display:
                self._live_display.update()

    def show_tool_call(self, tool_name: str, model: str = None, endpoint: str = None, tool_type: str = None):
        """
        Show a tool being called elegantly.

        Args:
            tool_name: Name of the tool
            model: Optional model name
            endpoint: Optional endpoint
            tool_type: Optional tool type
        """
        parts = [f"[bold cyan]{tool_name}[/bold cyan]"]
        if model:
            parts.append(f"model: [yellow]{model}[/yellow]")
        if endpoint:
            parts.append(f"endpoint: [dim]{endpoint}[/dim]")
        if tool_type:
            parts.append(f"type: [dim]{tool_type}[/dim]")

        self.console.print(f"  >> Using {', '.join(parts)}")

        # Update workflow step if enabled
        if self._workflow_panel and self._current_workflow_step_id:
            self._workflow_panel.update_step(
                self._current_workflow_step_id,
                StepStatus.ACTIVE,
                tool_name=tool_name
            )
            if self._live_display:
                self._live_display.update()

    def show_result(self, title: str, content: str, syntax: str = None):
        """
        Show a result in a panel.

        Args:
            title: Panel title
            content: Content to display
            syntax: Optional syntax highlighting (e.g., "python")
        """
        if syntax:
            syntax_obj = Syntax(content, syntax, theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax_obj, title=f"[cyan]{title}[/cyan]", box=box.ROUNDED))
        else:
            self.console.print(Panel(content, title=f"[cyan]{title}[/cyan]", box=box.ROUNDED))

    # ==============================================
    # New Enhanced Methods
    # ==============================================

    def add_workflow_step(
        self,
        step_id: str,
        name: str,
        tool_name: Optional[str] = None,
        description: Optional[str] = None
    ):
        """
        Add a step to the workflow flowchart (enhanced method).

        Args:
            step_id: Unique step identifier
            name: Step name
            tool_name: Optional tool name
            description: Optional description
        """
        if not self._workflow_panel:
            self.show_workflow_flowchart()

        if self._workflow_panel:
            step = WorkflowStep(
                id=step_id,
                name=name,
                tool_name=tool_name,
                description=description,
                status=StepStatus.PENDING
            )
            self._workflow_panel.add_step(step)
            if self._live_display:
                self._live_display.update()

    def update_workflow_step(self, step_id: str, status: StepStatus, **kwargs):
        """
        Update a workflow step's status.

        Args:
            step_id: Step identifier
            status: New status
            **kwargs: Additional attributes to update
        """
        if self._workflow_panel:
            self._workflow_panel.update_step(step_id, status, **kwargs)
            if self._live_display:
                self._live_display.update()

    def add_tool_component(
        self,
        name: str,
        component_type: str,
        lines_of_code: int = 0
    ):
        """
        Add a component to the tool assembly visualization.

        Args:
            name: Component name
            component_type: Component type (function, class, import, etc.)
            lines_of_code: Number of lines of code
        """
        if not self._tool_panel:
            return

        component = ToolComponent(
            name=name,
            type=component_type,
            lines_of_code=lines_of_code
        )
        self._tool_panel.add_component(component)
        if self._live_display:
            self._live_display.update()

    def update_tool_component(self, name: str, status: StepStatus, **kwargs):
        """
        Update a tool component's status.

        Args:
            name: Component name
            status: New status
            **kwargs: Additional attributes to update
        """
        if self._tool_panel:
            self._tool_panel.update_component(name, status, **kwargs)
            if self._live_display:
                self._live_display.update()

    def set_tool_progress(self, message: str):
        """
        Set tool assembly progress message.

        Args:
            message: Progress message
        """
        if self._tool_panel:
            self._tool_panel.set_progress(message)
            if self._live_display:
                self._live_display.update()

    def cleanup(self):
        """Clean up resources."""
        if self._live_display:
            self._live_display.stop()
            self._live_display = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
        return False


# Demo if run as main
if __name__ == "__main__":
    import time
    from rich.console import Console

    console = Console()

    # Demo: Enhanced workflow display
    console.print("\n[bold]Enhanced Workflow Display Demo[/bold]\n")

    display = EnhancedWorkflowDisplay(console, enable_panels=True)

    # Start workflow with visualization
    display.start_workflow("Generate and Test Code")
    display.show_workflow_flowchart("Code Generation Pipeline")

    # Add steps manually for better control
    display.add_workflow_step("analyze", "Analyze Requirements", tool_name="task_analyzer")
    display.add_workflow_step("search", "Search RAG", tool_name="rag_search")
    display.add_workflow_step("generate", "Generate Code", tool_name="code_generator")
    display.add_workflow_step("test", "Run Tests", tool_name="test_runner")

    time.sleep(1)

    # Simulate workflow execution
    steps = [
        ("analyze", "Analyzing requirements"),
        ("search", "Searching knowledge base"),
        ("generate", "Generating code"),
        ("test", "Running tests"),
    ]

    for step_id, message in steps:
        display.update_workflow_step(step_id, StepStatus.ACTIVE)
        display.console.print(f"[cyan]> {message}...[/cyan]")
        time.sleep(2)

        display.update_workflow_step(step_id, StepStatus.COMPLETED)
        display.console.print(f"[green]✓ {message} complete[/green]")
        time.sleep(0.5)

    time.sleep(1)

    # Now show tool assembly
    display.show_tool_assembly("DataValidator")

    components = [
        ("imports", "import", 5),
        ("validate_email", "function", 12),
        ("validate_phone", "function", 15),
        ("ValidationResult", "class", 20),
        ("main", "function", 8),
    ]

    for name, comp_type, lines in components:
        display.add_tool_component(name, comp_type, lines)

    time.sleep(1)

    # Simulate assembly
    for name, _, _ in components:
        display.set_tool_progress(f"Building {name}...")
        display.update_tool_component(name, StepStatus.ACTIVE)
        time.sleep(1.5)

        display.update_tool_component(name, StepStatus.COMPLETED)
        time.sleep(0.3)

    display.set_tool_progress("Tool assembly complete!")
    time.sleep(2)

    # Cleanup
    display.cleanup()

    console.print("\n[bold green]✓ Demo complete![/bold green]\n")
