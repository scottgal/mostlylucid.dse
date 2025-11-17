#!/usr/bin/env python3
"""
Demo script for CLI visualization panels.

Shows how to use the new panel system for workflow flowcharts
and tool assembly animations.
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from src.cli_panels import (
    create_workflow_panel,
    create_tool_assembly_panel,
    WorkflowStep,
    ToolComponent,
    StepStatus
)
from src.enhanced_workflow_display import EnhancedWorkflowDisplay
from rich.live import Live


def demo_workflow_flowchart():
    """Demo: Workflow flowchart visualization."""
    console = Console()
    console.print("\n[bold magenta]═══ Demo 1: Workflow Flowchart ═══[/bold magenta]\n")

    workflow_panel = create_workflow_panel("API Client Generation")

    # Define workflow steps
    steps = [
        WorkflowStep(
            id="step1",
            name="Parse API Specification",
            tool_name="openapi_parser",
            description="Extract endpoints and schemas from OpenAPI spec"
        ),
        WorkflowStep(
            id="step2",
            name="Generate Client Code",
            tool_name="code_generator",
            description="Create Python client with async support"
        ),
        WorkflowStep(
            id="step3",
            name="Add Type Hints",
            tool_name="type_annotator",
            description="Add comprehensive type annotations"
        ),
        WorkflowStep(
            id="step4",
            name="Generate Tests",
            tool_name="test_generator",
            description="Create unit and integration tests"
        ),
        WorkflowStep(
            id="step5",
            name="Validate & Format",
            tool_name="code_validator",
            description="Run linters and formatters"
        )
    ]

    # Add all steps
    for step in steps:
        workflow_panel.add_step(step)

    # Simulate execution with live updates
    with Live(workflow_panel.render(), console=console, refresh_per_second=4) as live:
        for step in steps:
            # Start step
            workflow_panel.update_step(step.id, StepStatus.ACTIVE)
            live.update(workflow_panel.render())
            console.print(f"[cyan]⚙ Executing: {step.name}[/cyan]")
            time.sleep(2.0)

            # Complete step
            workflow_panel.update_step(step.id, StepStatus.COMPLETED)
            live.update(workflow_panel.render())
            console.print(f"[green]✓ Completed: {step.name}[/green]")
            time.sleep(0.5)

    console.print("\n[bold green]✓ Workflow completed successfully![/bold green]\n")
    time.sleep(1)


def demo_tool_assembly():
    """Demo: Tool assembly visualization."""
    console = Console()
    console.print("\n[bold magenta]═══ Demo 2: Tool Assembly ═══[/bold magenta]\n")

    tool_panel = create_tool_assembly_panel("EmailValidator")

    # Define tool components
    components = [
        ToolComponent("standard library imports", "import", lines_of_code=3),
        ToolComponent("third-party imports", "import", lines_of_code=2),
        ToolComponent("EmailValidationError", "class", lines_of_code=8),
        ToolComponent("validate_format", "function", lines_of_code=25),
        ToolComponent("validate_domain", "function", lines_of_code=30),
        ToolComponent("validate_mx_record", "function", lines_of_code=20),
        ToolComponent("EmailValidator", "class", lines_of_code=45),
        ToolComponent("main", "function", lines_of_code=15),
        ToolComponent("docstrings", "documentation", lines_of_code=40),
        ToolComponent("type hints", "validation", lines_of_code=0),
    ]

    # Add all components
    for comp in components:
        tool_panel.add_component(comp)

    # Simulate assembly with live updates
    with Live(tool_panel.render(), console=console, refresh_per_second=4) as live:
        for i, comp in enumerate(components):
            # Set progress
            tool_panel.set_progress(f"Assembling component {i+1}/{len(components)}: {comp.name}")
            live.update(tool_panel.render())
            time.sleep(0.3)

            # Build component
            tool_panel.update_component(comp.name, StepStatus.ACTIVE)
            live.update(tool_panel.render())
            console.print(f"[yellow]🔨 Building: {comp.type} - {comp.name}[/yellow]")
            time.sleep(1.2)

            # Complete component
            tool_panel.update_component(comp.name, StepStatus.COMPLETED)
            live.update(tool_panel.render())
            console.print(f"[green]✓ Complete: {comp.name}[/green]")
            time.sleep(0.2)

        # Final status
        tool_panel.set_progress("Tool assembly complete! Ready for testing.")
        live.update(tool_panel.render())
        time.sleep(2)

    console.print("\n[bold green]✓ Tool assembled successfully![/bold green]\n")
    time.sleep(1)


def demo_enhanced_display():
    """Demo: Enhanced workflow display (drop-in replacement)."""
    console = Console()
    console.print("\n[bold magenta]═══ Demo 3: Enhanced Workflow Display ═══[/bold magenta]\n")
    console.print("[dim]This demo shows the drop-in replacement for WorkflowDisplay[/dim]\n")

    # Use enhanced display with panels enabled
    with EnhancedWorkflowDisplay(console, enable_panels=True) as display:
        # Start workflow (original API - backward compatible)
        display.start_workflow("Database Migration Tool")

        # Show flowchart and tool assembly
        display.show_workflow_flowchart("Migration Pipeline")
        time.sleep(1)

        # Define workflow steps
        steps = [
            ("analyze", "Analyze Schema", "schema_analyzer", "Scan database structure"),
            ("generate", "Generate Migrations", "migration_generator", "Create migration scripts"),
            ("validate", "Validate Scripts", "sql_validator", "Check for errors and conflicts"),
            ("test", "Test Migrations", "test_runner", "Run on test database"),
        ]

        # Add steps to flowchart
        for step_id, name, tool, desc in steps:
            display.add_workflow_step(step_id, name, tool, desc)

        time.sleep(1)

        # Execute workflow
        for step_id, name, tool, desc in steps:
            # Using original API (backward compatible)
            display.start_stage(name, desc)
            display.update_workflow_step(step_id, StepStatus.ACTIVE)
            time.sleep(2)

            display.complete_stage(name, f"Processed with {tool}")
            display.update_workflow_step(step_id, StepStatus.COMPLETED)
            time.sleep(0.5)

        console.print("\n[dim]All stages complete. Building migration tool...[/dim]\n")
        time.sleep(1)

        # Now show tool being assembled
        display.show_tool_assembly("MigrationTool")
        time.sleep(0.5)

        tool_components = [
            ("imports", "import", 8),
            ("DatabaseConnector", "class", 35),
            ("SchemaAnalyzer", "class", 50),
            ("MigrationGenerator", "class", 65),
            ("MigrationRunner", "class", 40),
            ("main", "function", 20),
        ]

        for name, comp_type, lines in tool_components:
            display.add_tool_component(name, comp_type, lines)

        time.sleep(0.5)

        # Assemble tool
        for name, _, _ in tool_components:
            display.set_tool_progress(f"Compiling {name}...")
            display.update_tool_component(name, StepStatus.ACTIVE)
            time.sleep(1)

            display.update_tool_component(name, StepStatus.COMPLETED)
            time.sleep(0.3)

        display.set_tool_progress("✓ Tool ready for deployment!")
        time.sleep(2)

    console.print("\n[bold green]✓ Enhanced workflow display demo complete![/bold green]\n")


def main():
    """Run all demos."""
    console = Console()

    console.print("\n")
    console.print("╔═══════════════════════════════════════════════════════════╗")
    console.print("║                                                           ║")
    console.print("║       Code Evolver - CLI Visualization Panels Demo       ║")
    console.print("║                                                           ║")
    console.print("╚═══════════════════════════════════════════════════════════╝")
    console.print("\n")

    try:
        # Demo 1: Workflow Flowchart
        demo_workflow_flowchart()

        console.print("\n[dim]Press Ctrl+C to skip remaining demos...[/dim]\n")
        time.sleep(2)

        # Demo 2: Tool Assembly
        demo_tool_assembly()

        time.sleep(2)

        # Demo 3: Enhanced Display (Integration)
        demo_enhanced_display()

        # Final message
        console.print("\n")
        console.print("╔═══════════════════════════════════════════════════════════╗")
        console.print("║                                                           ║")
        console.print("║                 ✓ All Demos Complete!                     ║")
        console.print("║                                                           ║")
        console.print("║  These visualizations can be integrated into chat_cli.py  ║")
        console.print("║  by replacing WorkflowDisplay with EnhancedWorkflow       ║")
        console.print("║  Display for a richer, more informative experience.       ║")
        console.print("║                                                           ║")
        console.print("╚═══════════════════════════════════════════════════════════╝")
        console.print("\n")

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Demo interrupted by user.[/yellow]\n")

    except Exception as e:
        console.print(f"\n\n[red]Error: {e}[/red]\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
