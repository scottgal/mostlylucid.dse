#!/usr/bin/env python3
"""
Interactive Workflow Runner

Runs a workflow interactively, prompting the user for inputs using
LLM-generated natural language questions.

Usage:
    python run_workflow.py workflows/simple_summarizer.json
    python run_workflow.py workflows/web_scraper_workflow.json --input '{"url": "https://example.com"}'
    python run_workflow.py workflows/data_analysis_workflow.json --interactive
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.table import Table
from rich import box

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ollama_client import OllamaClient
from src.interactive_input_collector import InteractiveInputCollector
from src.docker_workflow_builder import DockerWorkflowBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowRunner:
    """
    Interactive workflow runner with LLM-powered input collection.
    """

    def __init__(self, code_evolver_root: Path = None):
        """
        Initialize the workflow runner.

        Args:
            code_evolver_root: Root directory of code_evolver (auto-detected if None)
        """
        if code_evolver_root is None:
            code_evolver_root = Path(__file__).parent

        self.code_evolver_root = code_evolver_root
        self.console = Console()
        self.client = None
        self.input_collector = None

    def _init_client(self):
        """Lazily initialize the Ollama client."""
        if self.client is None:
            self.client = OllamaClient()
            self.input_collector = InteractiveInputCollector(self.client)

    def load_workflow(self, workflow_path: Path) -> Dict[str, Any]:
        """
        Load workflow specification from JSON file.

        Args:
            workflow_path: Path to workflow JSON file

        Returns:
            Workflow specification dict
        """
        self.console.print(f"\n[cyan]Loading workflow from:[/cyan] {workflow_path}")

        with open(workflow_path) as f:
            workflow_spec = json.load(f)

        workflow_id = workflow_spec.get("workflow_id", "unknown")
        description = workflow_spec.get("description", "No description")
        version = workflow_spec.get("version", "1.0.0")

        self.console.print(Panel(
            f"[bold]{workflow_id}[/bold] (v{version})\n{description}",
            title="Workflow Loaded",
            border_style="green",
            box=box.ROUNDED
        ))

        return workflow_spec

    def collect_inputs_interactive(
        self,
        workflow_spec: Dict[str, Any],
        provided_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Collect workflow inputs interactively.

        Args:
            workflow_spec: Workflow specification
            provided_inputs: Optional pre-provided inputs

        Returns:
            Complete inputs dict
        """
        self._init_client()

        # Use the interactive input collector
        inputs = self.input_collector.collect_inputs_sync(
            workflow_spec,
            provided_inputs
        )

        return inputs

    def execute_workflow(
        self,
        workflow_spec: Dict[str, Any],
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the workflow with the provided inputs.

        Args:
            workflow_spec: Workflow specification
            inputs: Input parameters

        Returns:
            Workflow execution results
        """
        workflow_id = workflow_spec.get("workflow_id", "workflow")
        steps = workflow_spec.get("steps", [])

        self.console.print()
        self.console.print(Panel(
            f"[bold cyan]Executing {len(steps)} steps...[/bold cyan]",
            title=f"Running: {workflow_id}",
            border_style="cyan",
            box=box.ROUNDED
        ))
        self.console.print()

        # Create a table to show workflow progress
        table = Table(title="Workflow Execution", box=box.SIMPLE)
        table.add_column("Step", style="cyan", no_wrap=True)
        table.add_column("Type", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Tool", style="magenta")

        results = {
            "inputs": inputs,
            "steps": {}
        }

        # Execute each step
        for i, step in enumerate(steps, 1):
            step_id = step.get("step_id", f"step_{i}")
            step_type = step.get("type", step.get("step_type", "unknown"))
            tool_name = step.get("tool", step.get("tool_name", "N/A"))

            self.console.print(f"[bold]Step {i}/{len(steps)}:[/bold] {step_id}")

            try:
                # Execute the step
                step_result = self._execute_step(step, inputs, results["steps"])
                results["steps"][step_id] = step_result

                table.add_row(
                    f"{i}. {step_id}",
                    step_type,
                    "[green]✓ Complete[/green]",
                    tool_name
                )

            except Exception as e:
                logger.error(f"Step {step_id} failed: {e}")
                results["steps"][step_id] = {
                    "success": False,
                    "error": str(e)
                }

                table.add_row(
                    f"{i}. {step_id}",
                    step_type,
                    f"[red]✗ Failed: {e}[/red]",
                    tool_name
                )

        self.console.print()
        self.console.print(table)
        self.console.print()

        # Collect workflow outputs
        outputs = self._collect_outputs(workflow_spec, results["steps"])
        results["outputs"] = outputs

        return results

    def _execute_step(
        self,
        step: Dict[str, Any],
        inputs: Dict[str, Any],
        step_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step.

        Args:
            step: Step specification
            inputs: Workflow inputs
            step_outputs: Outputs from previous steps

        Returns:
            Step execution result
        """
        step_type = step.get("type", step.get("step_type", ""))
        step_id = step.get("step_id")

        # For now, this is a placeholder implementation
        # In a full implementation, this would:
        # 1. Map inputs using input_mapping
        # 2. Execute the tool (LLM call, Python execution, etc.)
        # 3. Return the results

        if step_type in ("llm_call", "LLM_CALL"):
            return self._execute_llm_step(step, inputs, step_outputs)
        elif step_type in ("python_tool", "PYTHON_TOOL", "executable"):
            return self._execute_python_step(step, inputs, step_outputs)
        else:
            return {
                "success": False,
                "error": f"Unknown step type: {step_type}"
            }

    def _execute_llm_step(
        self,
        step: Dict[str, Any],
        inputs: Dict[str, Any],
        step_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an LLM-based step."""
        self._init_client()

        # Map inputs
        step_inputs = self._map_inputs(step.get("input_mapping", {}), inputs, step_outputs)

        # Get prompt template
        prompt_template = step.get("prompt_template", "")

        # Expand template with inputs
        prompt = self._expand_template(prompt_template, step_inputs)

        # Get tool specification
        tool_name = step.get("tool")

        self.console.print(f"  [dim]Calling LLM tool: {tool_name}[/dim]")

        try:
            # Call LLM
            output = self.client.generate(
                model="llama3",  # Default model
                prompt=prompt,
                temperature=0.7
            )

            return {
                "success": True,
                "output": output,
                "prompt": prompt
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _execute_python_step(
        self,
        step: Dict[str, Any],
        inputs: Dict[str, Any],
        step_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Python tool step."""
        return {
            "success": False,
            "error": "Python tool execution not yet implemented in interactive runner"
        }

    def _map_inputs(
        self,
        input_mapping: Dict[str, Any],
        inputs: Dict[str, Any],
        step_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map inputs from references to actual values.

        Args:
            input_mapping: Input mapping specification
            inputs: Workflow inputs
            step_outputs: Previous step outputs

        Returns:
            Mapped inputs
        """
        mapped = {}

        for key, ref in input_mapping.items():
            if isinstance(ref, str):
                if ref.startswith("inputs."):
                    input_key = ref.replace("inputs.", "")
                    mapped[key] = inputs.get(input_key)
                elif ref.startswith("steps."):
                    # Parse "steps.step_id.output_key"
                    parts = ref.split(".")
                    if len(parts) >= 2:
                        step_id = parts[1]
                        output_key = parts[2] if len(parts) > 2 else "output"
                        mapped[key] = step_outputs.get(step_id, {}).get(output_key)
                else:
                    # Literal value or template
                    mapped[key] = ref
            else:
                # Literal value
                mapped[key] = ref

        return mapped

    def _expand_template(self, template: str, values: Dict[str, Any]) -> str:
        """
        Expand template variables.

        Args:
            template: Template string with {var} placeholders
            values: Values to substitute

        Returns:
            Expanded string
        """
        import re

        result = template
        for match in re.finditer(r'\{([^}]+)\}', template):
            var_name = match.group(1)
            if var_name in values:
                result = result.replace(match.group(0), str(values[var_name]))

        return result

    def _collect_outputs(
        self,
        workflow_spec: Dict[str, Any],
        step_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Collect workflow outputs from step results.

        Args:
            workflow_spec: Workflow specification
            step_outputs: Step execution results

        Returns:
            Workflow outputs
        """
        outputs = {}
        output_specs = workflow_spec.get("outputs", {})

        for output_name, output_spec in output_specs.items():
            source_ref = output_spec.get("source_reference", "")
            if source_ref:
                # Parse source reference (e.g., "steps.final_step.output")
                parts = source_ref.split(".")
                if len(parts) >= 2 and parts[0] == "steps":
                    step_id = parts[1]
                    output_key = parts[2] if len(parts) > 2 else "output"
                    outputs[output_name] = step_outputs.get(step_id, {}).get(output_key)

        return outputs

    def run(
        self,
        workflow_path: Path,
        provided_inputs: Optional[Dict[str, Any]] = None,
        interactive: bool = True
    ) -> Dict[str, Any]:
        """
        Run a workflow from start to finish.

        Args:
            workflow_path: Path to workflow JSON
            provided_inputs: Optional pre-provided inputs
            interactive: Whether to prompt for missing inputs

        Returns:
            Workflow execution results
        """
        # Load workflow
        workflow_spec = self.load_workflow(workflow_path)

        # Collect inputs
        if interactive:
            inputs = self.collect_inputs_interactive(workflow_spec, provided_inputs)
        else:
            inputs = provided_inputs or {}

        # Display collected inputs
        if inputs:
            self.console.print("\n[bold]Inputs collected:[/bold]")
            for key, value in inputs.items():
                self.console.print(f"  [cyan]{key}:[/cyan] {value}")

        # Execute workflow
        results = self.execute_workflow(workflow_spec, inputs)

        # Display outputs
        if results.get("outputs"):
            self.console.print()
            self.console.print(Panel(
                self._format_outputs(results["outputs"]),
                title="[bold green]Workflow Outputs[/bold green]",
                border_style="green",
                box=box.ROUNDED
            ))

        return results

    def _format_outputs(self, outputs: Dict[str, Any]) -> str:
        """Format outputs for display."""
        lines = []
        for key, value in outputs.items():
            lines.append(f"[bold cyan]{key}:[/bold cyan]")

            # Format value based on type
            if isinstance(value, str):
                if len(value) > 200:
                    lines.append(f"{value[:200]}...")
                else:
                    lines.append(value)
            else:
                lines.append(str(value))

            lines.append("")

        return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive Workflow Runner with LLM-powered input collection",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "workflow",
        type=Path,
        help="Path to workflow JSON file"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="Pre-provided inputs as JSON string"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        default=True,
        help="Prompt for missing inputs interactively (default: True)"
    )
    parser.add_argument(
        "--no-interactive",
        dest="interactive",
        action="store_false",
        help="Don't prompt for inputs, only use provided --input"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Save results to JSON file"
    )

    args = parser.parse_args()

    # Validate workflow path
    if not args.workflow.exists():
        print(f"Error: Workflow file not found: {args.workflow}", file=sys.stderr)
        return 1

    # Parse provided inputs
    provided_inputs = None
    if args.input:
        try:
            provided_inputs = json.loads(args.input)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --input: {e}", file=sys.stderr)
            return 1

    # Run workflow
    try:
        runner = WorkflowRunner()
        results = runner.run(
            workflow_path=args.workflow,
            provided_inputs=provided_inputs,
            interactive=args.interactive
        )

        # Save results if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {args.output}")

        return 0

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
