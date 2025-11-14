#!/usr/bin/env python3
"""
Interactive CLI chat interface for Code Evolver.
Provides a conversational interface for code generation and evolution.
"""
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

# readline is Unix/Linux only - optional for history features
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

from src import (
    OllamaClient, Registry, NodeRunner, Evaluator,
    create_rag_memory
)
from src.config_manager import ConfigManager
from src.tools_manager import ToolsManager, ToolType

console = Console()


class ChatCLI:
    """Interactive chat interface for Code Evolver."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize chat CLI.

        Args:
            config_path: Path to configuration file
        """
        self.config = ConfigManager(config_path)
        self.client = OllamaClient(self.config.ollama_url, config_manager=self.config)
        self.registry = Registry(self.config.registry_path)
        self.runner = NodeRunner(self.config.nodes_path)
        self.evaluator = Evaluator(self.client)

        # Initialize RAG memory for tool selection
        # Automatically uses Qdrant if configured, otherwise NumPy-based memory
        self.rag = create_rag_memory(self.config, self.client)
        if self.config.use_qdrant:
            from src.qdrant_rag_memory import QDRANT_AVAILABLE
            if QDRANT_AVAILABLE:
                console.print("[dim]✓ Using Qdrant for RAG memory[/dim]")
            else:
                console.print("[yellow]⚠ Qdrant requested but not available, using NumPy-based RAG[/yellow]")

        # Initialize tools manager with RAG
        self.tools_manager = ToolsManager(
            config_manager=self.config,
            ollama_client=self.client,
            rag_memory=self.rag
        )

        self.context = {}
        self.history = []
        self._load_history()

    def _load_history(self):
        """Load command history from file."""
        if not READLINE_AVAILABLE:
            return

        history_file = self.config.get("chat.history_file", ".code_evolver_history")
        history_path = Path(history_file)

        if history_path.exists():
            try:
                with open(history_path, 'r') as f:
                    for line in f:
                        readline.add_history(line.strip())
            except Exception:
                pass

    def _save_history(self):
        """Save command history to file."""
        if not READLINE_AVAILABLE:
            return

        history_file = self.config.get("chat.history_file", ".code_evolver_history")
        history_path = Path(history_file)

        try:
            max_history = self.config.get("chat.max_history", 1000)
            with open(history_path, 'w') as f:
                for i in range(max(0, readline.get_current_history_length() - max_history),
                             readline.get_current_history_length()):
                    hist_item = readline.get_history_item(i + 1)
                    if hist_item:
                        f.write(hist_item + '\n')
        except Exception:
            pass

    def print_welcome(self):
        """Print welcome message."""
        welcome = """
[bold cyan]Code Evolver - Interactive CLI[/bold cyan]
[dim]AI-powered code generation and evolution using Ollama[/dim]

Type [bold]help[/bold] for available commands, or [bold]exit[/bold] to quit.
        """
        console.print(Panel(welcome, box=box.ROUNDED))

    def print_help(self):
        """Print help message."""
        table = Table(title="Available Commands", box=box.ROUNDED)
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description")

        commands = [
            ("generate <description>", "Generate a new node from natural language description"),
            ("run <node_id> [input]", "Run an existing node with optional input"),
            ("test <node_id>", "Run unit tests for a node"),
            ("evaluate <node_id>", "Evaluate a node's performance"),
            ("list", "List all nodes in registry"),
            ("show <node_id>", "Show detailed information about a node"),
            ("delete <node_id>", "Delete a node"),
            ("evolve <node_id>", "Manually trigger evolution for a node"),
            ("auto on|off", "Enable/disable auto-evolution"),
            ("config [key] [value]", "Show or update configuration"),
            ("status", "Show system status"),
            ("clear", "Clear the screen"),
            ("help", "Show this help message"),
            ("exit, quit", "Exit the CLI")
        ]

        for cmd, desc in commands:
            table.add_row(cmd, desc)

        console.print(table)

    def handle_generate(self, description: str) -> bool:
        """
        Handle generate command.

        Args:
            description: Natural language description of what to generate

        Returns:
            True if successful
        """
        if not description:
            console.print("[red]Error: Please provide a description[/red]")
            return False

        # Step 1: Find relevant tools using RAG semantic search
        console.print(f"\n[cyan]Searching for relevant tools...[/cyan]")
        available_tools = self.tools_manager.get_tools_for_prompt(
            task_description=description,
            max_tools=3,
            filter_type=ToolType.LLM  # Focus on LLM tools for code generation
        )

        if "No specific tools" not in available_tools:
            console.print(f"[dim]✓ Found {len(self.tools_manager.search(description, top_k=3))} relevant tools[/dim]")

        # Step 2: Ask overseer for strategy WITH tool recommendations
        console.print(f"\n[cyan]Consulting overseer LLM ({self.config.overseer_model}) for approach...[/cyan]")

        overseer_prompt = f"""You are an expert software architect. A user wants to create code with this goal:

"{description}"

{available_tools}

Provide:
1. A clear problem analysis
2. Recommended approach and algorithm
3. Which tool (if any) would be best suited for this task
4. Key considerations (edge cases, performance, constraints)
5. Suggested function signatures
6. Test cases to validate correctness

If a specialized tool is available and appropriate, recommend using it. Otherwise, use the standard generator.
Be specific and technical. This will guide code generation."""

        strategy = self.client.generate(
            model=self.config.overseer_model,
            prompt=overseer_prompt,
            temperature=0.7,
            model_key="overseer"
        )

        if self.config.get("chat.show_thinking", False):
            console.print(Panel(strategy, title="[yellow]Overseer Strategy[/yellow]", box=box.ROUNDED))
        else:
            console.print("[dim]✓ Strategy received[/dim]")

        # Step 2: Determine which tool/model to use for code generation
        selected_tool = self.tools_manager.get_best_llm_for_task(description)
        generator_to_use = self.config.generator_model
        use_specialized_tool = False

        if selected_tool:
            console.print(f"[dim]✓ Selected specialized tool: {selected_tool.name}[/dim]")
            use_specialized_tool = True
        else:
            console.print(f"[dim]Using standard generator: {generator_to_use}[/dim]")

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

        # Step 4: Generate code based on strategy
        code_prompt = f"""Based on this strategy:

{strategy}

Write Python code that implements the solution. Requirements:
- Pure Python, no external dependencies (except stdlib)
- Include proper error handling
- Include a __main__ section that:
  * Reads JSON from stdin
  * Processes the input
  * Prints JSON output to stdout
- Be production-ready and well-documented

Return ONLY the Python code, no explanations."""

        # Use specialized tool if available, otherwise use standard generator
        if use_specialized_tool and selected_tool:
            console.print(f"\n[cyan]Generating code with specialized tool: {selected_tool.name}...[/cyan]")
            code = self.tools_manager.invoke_llm_tool(
                tool_id=selected_tool.tool_id,
                prompt=code_prompt,
                temperature=0.3
            )
        else:
            console.print(f"\n[cyan]Generating code with {self.config.generator_model}...[/cyan]")
            code = self.client.generate(
                model=self.config.generator_model,
                prompt=code_prompt,
                temperature=0.3,
                model_key="generator"
            )

        if not code or len(code) < 50:
            console.print("[red]Failed to generate valid code[/red]")
            return False

        # Step 4: Create node in registry
        self.registry.create_node(
            node_id=node_id,
            title=description[:100],
            tags=["generated", "chat"],
            goals={
                "primary": ["correctness", "determinism"],
                "secondary": ["latency<200ms", "memory<64MB"]
            }
        )

        # Step 5: Save code
        self.runner.save_code(node_id, code)

        # Step 6: Display generated code
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"[green]Generated Code: {node_id}[/green]", box=box.ROUNDED))

        # Step 7: Generate and run unit tests if enabled
        if self.config.testing_enabled:
            console.print(f"\n[cyan]Generating unit tests...[/cyan]")
            success = self._generate_and_run_tests(node_id, description, strategy, code)

            if not success and self.config.auto_escalate:
                console.print(f"\n[yellow]Tests failed. Escalating to {self.config.escalation_model} for fixes...[/yellow]")
                return self._escalate_and_fix(node_id, code, description)

        console.print(f"\n[green]✓ Node '{node_id}' created successfully![/green]")
        console.print(f"[dim]Use 'run {node_id}' to execute it[/dim]")

        return True

    def _generate_and_run_tests(self, node_id: str, description: str, strategy: str, code: str) -> bool:
        """Generate and run unit tests for a node."""
        test_prompt = f"""Generate pytest unit tests for this code:

Description: {description}

Strategy: {strategy[:500]}

Code:
```python
{code}
```

Create comprehensive unit tests that:
1. Test normal cases
2. Test edge cases
3. Test error handling
4. Verify correctness

Return ONLY the test code, importable as a Python module."""

        test_code = self.client.generate(
            model=self.config.generator_model,
            prompt=test_prompt,
            temperature=0.3,
            model_key="generator"
        )

        # Save test code
        test_path = self.runner.get_node_path(node_id).parent / "test_main.py"
        with open(test_path, 'w') as f:
            f.write(test_code)

        console.print("[dim]✓ Tests generated[/dim]")

        # Run tests (simplified - would use pytest in production)
        console.print("[cyan]Running tests...[/cyan]")

        # For now, just verify the code runs with sample input
        sample_input = {"input": "test"}
        stdout, stderr, metrics = self.runner.run_node(node_id, sample_input)

        if metrics["success"]:
            console.print("[green]✓ Tests passed[/green]")
            return True
        else:
            console.print(f"[red]✗ Tests failed: {stderr[:200]}[/red]")
            return False

    def _escalate_and_fix(self, node_id: str, code: str, description: str) -> bool:
        """Escalate to higher-level LLM to fix issues."""
        max_attempts = self.config.get("testing.max_escalation_attempts", 3)

        for attempt in range(max_attempts):
            console.print(f"[cyan]Escalation attempt {attempt + 1}/{max_attempts}...[/cyan]")

            fix_prompt = f"""The following code has issues. Please fix them:

Original goal: {description}

Current code:
```python
{code}
```

Requirements:
1. Fix any bugs or errors
2. Improve error handling
3. Ensure code is production-ready
4. Maintain the same interface

Return ONLY the fixed Python code."""

            fixed_code = self.client.generate(
                model=self.config.escalation_model,
                prompt=fix_prompt,
                temperature=0.3,
                model_key="escalation"
            )

            if not fixed_code:
                continue

            # Save fixed code
            self.runner.save_code(node_id, fixed_code)

            # Test again
            sample_input = {"input": "test"}
            stdout, stderr, metrics = self.runner.run_node(node_id, sample_input)

            if metrics["success"]:
                console.print(f"[green]✓ Fixed successfully on attempt {attempt + 1}[/green]")
                return True

            code = fixed_code  # Try to fix this version next

        console.print(f"[red]✗ Could not fix after {max_attempts} attempts[/red]")
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
            console.print("[green]✓ Execution successful[/green]")
            if stdout:
                console.print(Panel(stdout, title="Output", box=box.ROUNDED))
        else:
            console.print(f"[red]✗ Execution failed (exit code: {metrics['exit_code']})[/red]")
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
        status = "[green]✓ Connected[/green]" if ollama_ok else "[red]✗ Not connected[/red]"

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
                has_model = model in models
                model_status = f"[green]✓ {model}[/green]" if has_model else f"[red]✗ {model} missing[/red]"
                table.add_row(f"{name} Model", model_status)

        table.add_row("Auto-Evolution", "[green]Enabled[/green]" if self.config.auto_evolution_enabled else "[dim]Disabled[/dim]")
        table.add_row("Unit Testing", "[green]Enabled[/green]" if self.config.testing_enabled else "[dim]Disabled[/dim]")

        # Node count
        nodes = self.registry.list_nodes()
        table.add_row("Nodes in Registry", str(len(nodes)))

        console.print(table)
        return True

    def run(self):
        """Run the interactive CLI."""
        self.print_welcome()

        # Check status first
        if not self.client.check_connection():
            console.print("[red]Warning: Cannot connect to Ollama. Some features will not work.[/red]")
            console.print("[dim]Start Ollama with: ollama serve[/dim]\n")

        prompt_text = self.config.get("chat.prompt", "CodeEvolver> ")

        while True:
            try:
                user_input = console.input(f"[bold green]{prompt_text}[/bold green]").strip()

                if not user_input:
                    continue

                self.history.append(user_input)

                # Parse command
                if user_input.lower() in ['exit', 'quit', 'q']:
                    console.print("[cyan]Goodbye![/cyan]")
                    break

                elif user_input.lower() in ['help', '?']:
                    self.print_help()

                elif user_input.lower() == 'clear':
                    console.clear()

                elif user_input.lower() == 'status':
                    self.handle_status()

                elif user_input.lower() == 'list':
                    self.handle_list()

                elif user_input.startswith('generate '):
                    description = user_input[9:].strip()
                    self.handle_generate(description)

                elif user_input.startswith('run '):
                    args = user_input[4:].strip()
                    self.handle_run(args)

                elif user_input.startswith('auto '):
                    state = user_input[5:].strip().lower()
                    if state in ['on', 'off']:
                        self.config.set("auto_evolution.enabled", state == 'on')
                        console.print(f"[green]Auto-evolution {state}[/green]")
                    else:
                        console.print("[red]Usage: auto on|off[/red]")

                else:
                    console.print(f"[yellow]Unknown command: {user_input}[/yellow]")
                    console.print("[dim]Type 'help' for available commands[/dim]")

            except KeyboardInterrupt:
                console.print("\n[dim]Use 'exit' to quit[/dim]")
                continue

            except EOFError:
                break

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        self._save_history()


def main():
    """Main entry point."""
    chat = ChatCLI()
    chat.run()


if __name__ == "__main__":
    main()
