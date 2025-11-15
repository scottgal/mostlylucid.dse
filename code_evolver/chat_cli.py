#!/usr/bin/env python3
"""
Interactive CLI chat interface for Code Evolver.
Provides a conversational interface for code generation and evolution.
"""
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box
from rich.live import Live
from rich.spinner import Spinner
from datetime import datetime

# Disable all debug/info logging for clean chat experience
logging.basicConfig(level=logging.ERROR)
logging.getLogger("src").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("src.ollama_client").setLevel(logging.ERROR)
logging.getLogger("src.node_runner").setLevel(logging.ERROR)
logging.getLogger("src.tools_manager").setLevel(logging.ERROR)
logging.getLogger("src.qdrant_rag_memory").setLevel(logging.ERROR)

# readline is Unix/Linux only - optional for history features
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

console = Console()


class WorkflowDisplay:
    """Clean workflow stage display for modern chat experience."""

    def __init__(self, console: Console):
        self.console = console
        self.current_stage = None
        self.stages = []

    def start_workflow(self, description: str):
        """Start a new workflow."""
        self.console.print(f"\n[bold cyan]{description}[/bold cyan]\n")
        self.stages = []

    def add_stage(self, stage_name: str):
        """Add a stage to the workflow."""
        self.stages.append(stage_name)

    def show_stages(self):
        """Show workflow stages as a pipeline."""
        if not self.stages:
            return
        pipeline = " → ".join(self.stages)
        self.console.print(f"[dim]{pipeline}[/dim]\n")

    def start_stage(self, stage_name: str, status_text: str = None):
        """Start a stage with a simple status message (no spinner to avoid Unicode issues)."""
        self.current_stage = stage_name
        display_text = status_text or stage_name
        self.console.print(f"[cyan]> {display_text}...[/cyan]")

        # Return a dummy context manager that does nothing
        class DummyContext:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return DummyContext()

    def complete_stage(self, stage_name: str, result: str = None):
        """Mark a stage as complete."""
        if result:
            self.console.print(f"[green]OK[/green] {stage_name}: {result}")
        else:
            self.console.print(f"[green]OK[/green] {stage_name}")

    def show_tool_call(self, tool_name: str, model: str = None, endpoint: str = None, tool_type: str = None):
        """Show a tool being called elegantly."""
        parts = [f"[bold cyan]{tool_name}[/bold cyan]"]
        if model:
            parts.append(f"model: [yellow]{model}[/yellow]")
        if endpoint:
            parts.append(f"endpoint: [dim]{endpoint}[/dim]")
        if tool_type:
            parts.append(f"type: [dim]{tool_type}[/dim]")

        self.console.print(f"  >> Using {', '.join(parts)}")

    def show_result(self, title: str, content: str, syntax: str = None):
        """Show a result in a panel."""
        if syntax:
            syntax_obj = Syntax(content, syntax, theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax_obj, title=f"[cyan]{title}[/cyan]", box=box.ROUNDED))
        else:
            self.console.print(Panel(content, title=f"[cyan]{title}[/cyan]", box=box.ROUNDED))


class ChatCLI:
    """Interactive chat interface for Code Evolver."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize chat CLI.

        Args:
            config_path: Path to configuration file
        """
        self.config = ConfigManager(config_path)

        # Use LLM client factory if backend is configured, otherwise default to Ollama
        try:
            from src.llm_client_factory import LLMClientFactory
            backend = self.config.config.get("llm", {}).get("backend", "ollama")
            self.client = LLMClientFactory.create_from_config(self.config, backend)
            console.print(f"[dim]Using {backend} backend for LLM[/dim]")
        except (ImportError, KeyError, ValueError) as e:
            # Fall back to Ollama if factory not available or config incomplete
            console.print(f"[yellow]Falling back to Ollama backend: {e}[/yellow]")
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
                console.print("[dim]OK Using Qdrant for RAG memory[/dim]")
            else:
                console.print("[yellow]WARNING Qdrant requested but not available, using NumPy-based RAG[/yellow]")

        # Initialize tools manager with RAG
        self.tools_manager = ToolsManager(
            config_manager=self.config,
            ollama_client=self.client,
            rag_memory=self.rag
        )

        # Register model selector tool if multi-backend support is enabled
        try:
            from src.model_selector_tool import create_model_selector_tool
            if self.config.config.get("model_selector", {}).get("enabled", True):
                create_model_selector_tool(self.config, self.tools_manager)
                console.print("[dim]Registered model selector tool[/dim]")
        except (ImportError, Exception) as e:
            console.print(f"[dim]Model selector not available: {e}[/dim]")

        self.context = {}
        self.history = []
        self.display = WorkflowDisplay(console)
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
            model_key="generator"
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
                if similarity > 0.6:  # Only show reasonably similar workflows
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
- "and" → SEPARATE operations (create SEPARATE steps)
- "then" → SEQUENTIAL operations (create SEPARATE steps)
- "translate" → SEPARATE translation step
- "convert" → SEPARATE conversion step

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
1. If step B uses output from step A → B depends_on: ["stepA"]
2. If steps B and C are independent → they can run in parallel (same parallel_group)
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
                model_key="overseer"
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
                console.print(f"[dim]Generating node for: {node_task}[/dim]")

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
            ("clear_rag", "Clear RAG memory and reset test data (WARNING: destructive!)"),
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

        # Initialize workflow tracker
        show_workflow = self.config.get("chat.show_workflow", True)
        workflow = WorkflowTracker(
            workflow_id=f"gen_{int(__import__('time').time()*1000)}",
            description=description,
            context=self.config.get("chat.default_workflow_context", {})
        )

        # Start clean workflow display
        self.display.start_workflow(description)

        # Step 0: Check for existing solutions in RAG (both code and workflows)
        workflow.add_step("check_existing", "rag", "Check for existing solutions in RAG")
        from src.rag_memory import ArtifactType

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
            # Lower threshold to 70% for better reuse (was 85%)
            if similarity > 0.70:
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
                        # - High similarity (>90%): Check semantic equivalence, then reuse as-is
                        # - Medium similarity (70-90%): Check semantic equivalence, then use as template
                        # - Low similarity (<70%): Generate from scratch

                        # CRITICAL: Use tinyllama to check relationship between tasks
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
- "fibonacci sequence" vs "fibonaccie sequence and output result" → SAME (typo, same task)
- "add 10 and 20" vs "sum 10 and 20" → SAME (synonym)
- "fibonacci sequence" vs "fibonacci backwards" → RELATED (same algorithm, different direction)
- "write a story" vs "write a technical article" → RELATED (same domain, different style)
- "fibonacci" vs "prime numbers" → DIFFERENT (different algorithms)
- "calculate primes" vs "find prime numbers" → SAME (synonym)

Answer with ONLY ONE WORD: SAME, RELATED, or DIFFERENT
Answer:"""

                        semantic_response = self.client.generate(
                            model=self.config.triage_model,
                            prompt=semantic_check_prompt,
                            temperature=0.1,  # Low temperature for consistent classification
                            model_key="triage"
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
                                input_data = {"input": description}
                                stdout, stderr, metrics = self.runner.run_node(node_id, input_data)

                            # Display results prominently
                            if metrics["success"]:
                                self.display.complete_stage("Execute", "Success")

                                if stdout and stdout.strip():
                                    # Try to extract and show the actual result prominently
                                    result_extracted = False
                                    try:
                                        # Try to parse as JSON first
                                        output_data = json.loads(stdout.strip())
                                        if isinstance(output_data, dict):
                                            # Show the actual result clearly
                                            if 'result' in output_data:
                                                console.print(f"\n[bold green]RESULT:[/bold green] [bold white]{output_data['result']}[/bold white]")
                                                result_extracted = True
                                            elif 'output' in output_data:
                                                console.print(f"\n[bold green]RESULT:[/bold green] [bold white]{output_data['output']}[/bold white]")
                                                result_extracted = True
                                            elif 'answer' in output_data:
                                                console.print(f"\n[bold green]RESULT:[/bold green] [bold white]{output_data['answer']}[/bold white]")
                                                result_extracted = True
                                            elif 'content' in output_data:
                                                console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['content']}")
                                                result_extracted = True
                                    except:
                                        pass

                                    # If we couldn't extract a specific result, show full output
                                    if not result_extracted:
                                        # Check if it's plain text (like an article or story)
                                        if not stdout.strip().startswith('{'):
                                            console.print(f"\n[bold green]RESULT:[/bold green]")
                                            console.print(Panel(stdout, box=box.ROUNDED, border_style="green"))
                                        else:
                                            console.print(Panel(stdout, title="[green]Output[/green]", box=box.ROUNDED, border_style="green"))
                                else:
                                    console.print("[yellow]Note: Code executed successfully but produced no output[/yellow]")
                            else:
                                self.display.complete_stage("Execute", f"Failed (exit code: {metrics['exit_code']})")
                                if stderr:
                                    console.print(Panel(stderr, title="[red]Error[/red]", border_style="red", box=box.ROUNDED))

                            if self.config.get("chat.show_metrics", True):
                                self._display_metrics(metrics)

                            return True

                        else:
                            # Medium similarity (70-90%) - use as template and modify
                            self.display.complete_stage("Search RAG", f"Using as template ({similarity:.0%} match)")
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
            # Lower threshold to 75% for workflows (was 85%)
            if similarity > 0.75:
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
- "fibonacci sequence" vs "fibonaccie sequence and output result" → SAME (typo, same task)
- "add 10 and 20" vs "sum 10 and 20" → SAME (synonym)
- "fibonacci sequence" vs "fibonacci backwards" → RELATED (same algorithm, different direction)
- "write a story" vs "write a technical article" → RELATED (same domain, different style)
- "fibonacci" vs "prime numbers" → DIFFERENT (different algorithms)
- "calculate primes" vs "find prime numbers" → SAME (synonym)

Answer with ONLY ONE WORD: SAME, RELATED, or DIFFERENT
Answer:"""

                semantic_response = self.client.generate(
                    model=self.config.triage_model,
                    prompt=semantic_check_prompt,
                    temperature=0.1,
                    model_key="triage"
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
                            input_data = {"input": description}
                            stdout, stderr, metrics = self.runner.run_node(node_id, input_data)

                        # Display results - ALWAYS show output prominently
                        if metrics["success"]:
                            self.display.complete_stage("Execute", "Success")

                            if stdout and stdout.strip():
                                # Try to extract and show the actual result prominently
                                result_extracted = False
                                try:
                                    # Try to parse as JSON first
                                    output_data = json.loads(stdout.strip())
                                    if isinstance(output_data, dict):
                                        # Show the actual result clearly
                                        if 'result' in output_data:
                                            console.print(f"\n[bold green]RESULT:[/bold green] [bold white]{output_data['result']}[/bold white]")
                                            result_extracted = True
                                        elif 'output' in output_data:
                                            console.print(f"\n[bold green]RESULT:[/bold green] [bold white]{output_data['output']}[/bold white]")
                                            result_extracted = True
                                        elif 'answer' in output_data:
                                            console.print(f"\n[bold green]RESULT:[/bold green] [bold white]{output_data['answer']}[/bold white]")
                                            result_extracted = True
                                        elif 'content' in output_data:
                                            console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['content']}")
                                            result_extracted = True
                                except:
                                    pass

                                # If we couldn't extract a specific result, show full output
                                if not result_extracted:
                                    # Check if it's plain text (like an article or story)
                                    if not stdout.strip().startswith('{'):
                                        console.print(f"\n[bold green]RESULT:[/bold green]")
                                        console.print(Panel(stdout, box=box.ROUNDED, border_style="green"))
                                    else:
                                        console.print(Panel(stdout, title="[green]Output[/green]", box=box.ROUNDED, border_style="green"))
                            else:
                                console.print("[yellow]Note: Code executed successfully but produced no output[/yellow]")
                        else:
                            self.display.complete_stage("Execute", f"Failed (exit code: {metrics['exit_code']})")
                            if stderr:
                                console.print(Panel(stderr, title="[red]Error[/red]", border_style="red", box=box.ROUNDED))

                        if self.config.get("chat.show_metrics", True):
                            self._display_metrics(metrics)

                        return True

        # Step 1: Find relevant tools using RAG semantic search
        workflow.add_step("find_tools", "rag", "Search for relevant tools")
        workflow.start_step("find_tools")

        with self.display.start_stage("Planning", "Searching for relevant tools"):
            available_tools = self.tools_manager.get_tools_for_prompt(
                task_description=description,
                max_tools=3,
                filter_type=ToolType.LLM  # Focus on LLM tools for code generation
            )

        # Get the actual tool objects to show their names
        found_tools = self.tools_manager.search(description, top_k=3)
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
            self.display.add_stage(" → ".join(stages))

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

            # Smarter keyword detection - avoid false positives for arithmetic
            is_multi_step = False
            description_lower = description.lower()

            # Exclude arithmetic operations
            arithmetic_keywords = ["add", "subtract", "multiply", "divide", "calculate", "compute", "sum"]
            is_arithmetic = any(kw in description_lower for kw in arithmetic_keywords)

            if not is_arithmetic:
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
                if similarity >= 0.80:  # High similarity threshold for specs
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

4. **Input/Output Interface**
   - What JSON fields will the code read from stdin?
   - What JSON fields will the code write to stdout?
   - Example input → expected output

5. **Test Cases**
   - At least 3 test cases with inputs and expected outputs
   - Edge cases to handle (empty input, zero, negative, etc.)

6. **Tool Recommendation**
   {'Since you have a template, specify exactly what needs to be modified/added/removed.' if template_info else 'If a specialized LLM tool is available and appropriate for text generation, recommend using it. Otherwise, recommend direct implementation.'}

Be VERY specific and technical. Think of this as writing requirements for another developer.
The code generator will follow this specification EXACTLY, so include ALL critical details."""

        with self.display.start_stage("Thinking", f"Consulting {self.config.overseer_model}"):
            specification = self.client.generate(
                model=self.config.overseer_model,
                prompt=overseer_prompt,
                temperature=0.7,
                model_key="overseer"
            )

        self.display.complete_stage("Thinking", "Specification complete")
        if self.config.get("chat.show_thinking", False):
            console.print(Panel(specification, title="[yellow]Detailed Specification[/yellow]", box=box.ROUNDED))

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
            model_key="triage"
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
            self.display.show_tool_call(selected_tool.name, model="gemma3:4b", tool_type="Fast")
        # For ALL content generation (simple or complex), use powerful model
        elif is_simple_content or is_complex_content:
            # Don't search for tools - content needs fresh generation with powerful model
            # Use general tool which has proper prompts for content generation
            selected_tool = None
            use_specialized_tool = False
            console.print(f"[yellow]Using powerful model for content generation[/yellow]")
            self.display.show_tool_call("General Code Generator", model=self.config.generator_model, tool_type="Content")
        else:
            # For other complex tasks or if no specialized tool, use normal tool selection
            selected_tool = self.tools_manager.get_best_llm_for_task(description)
            generator_to_use = self.config.generator_model
            use_specialized_tool = False

            if selected_tool:
                if "general" not in selected_tool.tool_id.lower() and "fallback" not in selected_tool.tags:
                    self.display.show_tool_call(selected_tool.name, model=selected_tool.metadata.get('llm_model'), tool_type="Specialized")
                use_specialized_tool = True
            else:
                self.display.show_tool_call("Code Generator", model=generator_to_use, tool_type="Standard")

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

                # Create node directory if it doesn't exist yet
                node_dir = self.runner.get_node_path(node_id).parent
                node_dir.mkdir(parents=True, exist_ok=True)

                # Save the interface tests
                test_path = node_dir / "test_main.py"
                with open(test_path, 'w') as f:
                    f.write(interface_tests)

                console.print(f"[dim green]Saved interface-defining tests to {test_path.name}[/dim green]")

                # Display the generated tests
                test_syntax = Syntax(interface_tests, "python", theme="monokai", line_numbers=True)
                console.print(Panel(
                    test_syntax,
                    title="[cyan]Interface-Defining Tests (TDD)[/cyan]",
                    box=box.ROUNDED,
                    expand=False
                ))

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

MANDATORY CODE STRUCTURE:
```python
import json
import sys

# Only include this if you need to call LLM tools:
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

IMPORTANT: DO NOT use sys.path.insert() - the runtime environment already has the correct path.
```

Code requirements:
- MUST use json.load(sys.stdin) to read input - NO sys.argv or command-line arguments!
- For content generation (stories, jokes, articles): Use call_tool() to invoke content generation LLM tools
- For simple computational tasks (math, algorithms), implement directly without call_tool
- Include proper error handling
- MUST print output as JSON using print(json.dumps(...))
- Be production-ready and well-documented

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
3. For complex data processing, use input_data["input"] as the main data field
4. ALWAYS include these standard imports at the top:
   - import json
   - import sys
   - from node_runtime import call_tool (REQUIRED for any content generation task)

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

    print(json.dumps({{"result": content}}))

if __name__ == "__main__":
    main()
```

Example for joke generation specifically:
```python
import json
import sys
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

    print(json.dumps({{"result": joke}}))

if __name__ == "__main__":
    main()
```

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
            # For complex content, use the general tool's model (qwen2.5-coder:14b)
            # Otherwise use config generator_model (codellama)
            if is_complex_content and 'general' in self.tools_manager.tools:
                general_tool = self.tools_manager.tools['general']
                model_to_use = general_tool.metadata.get('llm_model', self.config.generator_model)
                console.print(f"\n[cyan]Generating code with {model_to_use} (general tool)...[/cyan]")
                response = self.client.generate(
                    model=model_to_use,
                    prompt=code_prompt,
                    temperature=0.2,
                    model_key="generator"
                )
            else:
                console.print(f"\n[cyan]Generating code with {self.config.generator_model}...[/cyan]")
                response = self.client.generate(
                    model=self.config.generator_model,
                    prompt=code_prompt,
                    temperature=0.2,  # Lower temp for more structured output
                    model_key="generator"
                )
        workflow.complete_step("code_generation", f"Generated {len(response)} chars", {"generator": generator_name})

        if not response or len(response) < 50:
            console.print("[red]Failed to generate valid response[/red]")
            return False

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
            code_tags = result.get("tags", ["generated", "chat"])

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
                        code_tags = ["generated", "chat"]
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
                code_tags = ["generated", "chat"]

        # Clean the code (remove any remaining markdown)
        code = self._clean_code(code)

        # Check for required imports and add if missing
        required_imports = []
        if 'json.load' in code or 'json.dump' in code:
            required_imports.append('import json')
        if 'sys.stdin' in code or 'sys.stdout' in code or 'sys.stderr' in code:
            required_imports.append('import sys')
        if 'call_tool(' in code:
            required_imports.append('from node_runtime import call_tool')

        # Add missing imports at the top
        for required in required_imports:
            if required.split()[-1] not in code.split('\n')[0]:  # Simple check
                # More robust check
                if required.startswith('from'):
                    module = required.split()[-1]
                    if f'import {module}' not in code and f'from node_runtime import {module}' not in code:
                        code = required + '\n' + code
                        console.print(f"[dim yellow]Added missing import: {required}[/dim yellow]")
                else:
                    module = required.split()[-1]
                    if f'import {module}' not in code:
                        code = required + '\n' + code
                        console.print(f"[dim yellow]Added missing import: {required}[/dim yellow]")

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

        # Step 5: Save code with interface metadata
        self.runner.save_code(node_id, code)

        # Save interface schema alongside the code
        interface_path = self.runner.get_node_path(node_id).parent / "interface.json"
        with open(interface_path, 'w') as f:
            json.dump(interface_schema, f, indent=2)

        # Step 6: Display generated code
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"[green]Generated Code: {node_id}[/green]", box=box.ROUNDED))

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

            if analysis_results["any_passed"]:
                workflow.complete_step("static_analysis", f"{analysis_results['passed_count']}/{analysis_results['total_count']} tools passed")
                console.print(f"[green]OK Static analysis: {analysis_results['passed_count']}/{analysis_results['total_count']} checks passed[/green]")
            else:
                workflow.fail_step("static_analysis", f"All {analysis_results['total_count']} tools found issues")
                console.print(f"[yellow]Static analysis found issues (not blocking execution)[/yellow]")

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

                # Store complete workflow for future reuse
                workflow_content = {
                    "description": description,
                    "specification": specification,
                    "tools_used": available_tools if "No specific tools" not in available_tools else "general",
                    "node_id": node_id,
                    "tags": code_tags,
                    "code_summary": code_description
                }

                self.rag.store_artifact(
                    artifact_id=f"workflow_{node_id}",
                    artifact_type=ArtifactType.WORKFLOW,
                    name=f"Workflow: {code_description}",
                    description=description,
                    content=json.dumps(workflow_content, indent=2),
                    tags=["workflow", "complete", "tested"] + code_tags,
                    metadata={
                        "node_id": node_id,
                        "question": description,
                        "specification_hash": hash(specification[:200]),
                        "tests_passed": True
                    },
                    auto_embed=True
                )
                console.print(f"[dim]OK Code and workflow stored in RAG for future reuse[/dim]")
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

                console.print(f"[green]✨ Created reusable committee tool: {committee_id}[/green]")
                console.print(f"[dim]This workflow can now be reused for similar tasks![/dim]")

            except Exception as e:
                console.print(f"[dim yellow]Note: Could not create committee tool: {e}[/dim yellow]")

        console.print(f"\n[green]OK Node '{node_id}' created successfully![/green]")

        # Step 9: Initial optimization loop (3 iterations max)
        max_optimization_iterations = self.config.get("testing.initial_optimization_iterations", 3)
        if max_optimization_iterations > 0 and test_success:
            console.print(f"\n[cyan]Starting initial optimization ({max_optimization_iterations} iterations)...[/cyan]")
            workflow.add_step("optimization", "optimize", f"Initial optimization loop (up to {max_optimization_iterations} iterations)")
            workflow.start_step("optimization")

            best_code = code
            best_score = 0.0
            iterations_performed = 0

            for iteration in range(max_optimization_iterations):
                console.print(f"\n[cyan]Optimization iteration {iteration + 1}/{max_optimization_iterations}...[/cyan]")

                # Run the current code
                test_input = {"input": description, "task": description, "description": description,
                             "query": description, "topic": description, "prompt": description}
                stdout, stderr, metrics = self.runner.run_node(node_id, test_input)

                if not metrics["success"]:
                    console.print(f"[yellow]Execution failed, skipping this iteration[/yellow]")
                    continue

                # Evaluate the result
                score = 1.0 if metrics["success"] else 0.0
                # Bonus for good performance
                if metrics.get("latency_ms", 999999) < 100:
                    score += 0.1
                if metrics.get("memory_mb_peak", 999999) < 10:
                    score += 0.1

                console.print(f"[dim]Score: {score:.2f} (latency: {metrics.get('latency_ms', 0)}ms, memory: {metrics.get('memory_mb_peak', 0):.2f}MB)[/dim]")
                iterations_performed += 1

                if score > best_score:
                    best_score = score
                    best_code = code
                    console.print(f"[green]OK New best score: {best_score:.2f}[/green]")

                    # Ask LLM for improvement suggestions
                    if iteration < max_optimization_iterations - 1:  # Don't optimize on last iteration
                        feedback_prompt = f"""Review this code and suggest ONE specific optimization:

Code:
```python
{code}
```

Execution metrics:
- Latency: {metrics.get('latency_ms', 0)}ms
- Memory: {metrics.get('memory_mb_peak', 0):.2f}MB
- Success: {metrics['success']}

Output:
{stdout[:500] if stdout else "No output"}

Suggest ONE concrete improvement for performance, memory usage, or code quality.
Return JSON: {{"improved_code": "...", "change_description": "..."}}"""

                        improvement_response = self.client.generate(
                            model=self.config.generator_model,
                            prompt=feedback_prompt,
                            temperature=0.4,
                            model_key="generator"
                        )

                        # Try to parse improvement
                        try:
                            import json
                            improvement_response = improvement_response.strip()
                            if improvement_response.startswith('```json'):
                                improvement_response = improvement_response.split('```json')[1].split('```')[0].strip()
                            elif improvement_response.startswith('```'):
                                improvement_response = improvement_response.split('```')[1].split('```')[0].strip()

                            improvement_data = json.loads(improvement_response)
                            improved_code = improvement_data.get("improved_code", "")
                            change_desc = improvement_data.get("change_description", "No description")

                            if improved_code and len(improved_code) > 50:
                                console.print(f"[dim]Applying: {change_desc}[/dim]")
                                cleaned_code = self._clean_code(improved_code)
                                # Validate code before saving
                                if cleaned_code and len(cleaned_code.strip()) > 20:
                                    code = cleaned_code
                                    self.runner.save_code(node_id, code)
                                else:
                                    console.print(f"[yellow]Warning: Cleaned code is empty, keeping previous version[/yellow]")
                                    break
                            else:
                                console.print(f"[dim]No valid improvement suggested[/dim]")
                                break  # No more improvements
                        except Exception as e:
                            console.print(f"[dim]Could not parse improvement: {e}[/dim]")
                            break
                else:
                    console.print(f"[dim]No improvement (score: {score:.2f} vs best: {best_score:.2f})[/dim]")
                    # Revert to best code
                    if best_code and len(best_code.strip()) > 20:
                        code = best_code
                        self.runner.save_code(node_id, code)
                    break  # No improvement, stop optimizing

            workflow.complete_step("optimization", f"Completed {iterations_performed} iterations, best score: {best_score:.2f}")
            console.print(f"[green]OK Optimization complete (best score: {best_score:.2f})[/green]")

        # Auto-run the newly created workflow
        workflow.add_step("execution", "run", "Execute the generated workflow")
        workflow.start_step("execution")
        console.print(f"\n[cyan]Running workflow...[/cyan]")

        # Create flexible input data that works with different code patterns
        # Pass the description as "input", "task", "description", "query", "topic", "prompt"
        # so generated code can use whichever field name it expects
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
        stdout, stderr, metrics = self.runner.run_node(node_id, input_data)

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
            if stdout and stdout.strip():
                # Try to extract and show the actual result prominently
                result_extracted = False
                try:
                    # Try to parse as JSON first
                    output_data = json.loads(stdout.strip())
                    if isinstance(output_data, dict):
                        # Show the actual result clearly
                        if 'result' in output_data:
                            console.print(f"\n[bold green]RESULT:[/bold green] [bold white]{output_data['result']}[/bold white]")
                            result_extracted = True
                        elif 'output' in output_data:
                            console.print(f"\n[bold green]RESULT:[/bold green] [bold white]{output_data['output']}[/bold white]")
                            result_extracted = True
                        elif 'answer' in output_data:
                            console.print(f"\n[bold green]RESULT:[/bold green] [bold white]{output_data['answer']}[/bold white]")
                            result_extracted = True
                        elif 'content' in output_data:
                            console.print(f"\n[bold green]RESULT:[/bold green]\n{output_data['content']}")
                            result_extracted = True
                except:
                    pass

                # If we couldn't extract a specific result, show full output
                if not result_extracted:
                    # Check if it's plain text (like an article or story)
                    if not stdout.strip().startswith('{'):
                        console.print(f"\n[bold green]RESULT:[/bold green]")
                        console.print(Panel(stdout, box=box.ROUNDED, border_style="green"))
                    else:
                        console.print(Panel(stdout, title="[green]Output[/green]", box=box.ROUNDED, border_style="green"))
            else:
                console.print("[yellow]Note: Code executed successfully but produced no output[/yellow]")
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

        # Step 10: If execution succeeded, register this node as a reusable tool
        if metrics["success"]:
            console.print(f"\n[cyan]Registering successful node as reusable tool...[/cyan]")
            try:
                # Calculate quality score based on performance
                quality_score = 1.0
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
                    self.rag.store_artifact(
                        artifact_id=f"tool_{node_id}",
                        artifact_type=ArtifactType.PATTERN,
                        name=f"Tool: {code_description[:80]}",
                        description=f"Reusable workflow tool: {description}",
                        content=f"Tool ID: {node_id}\nDescription: {description}\nQuality Score: {quality_score:.2f}",
                        tags=["tool", "workflow", "auto-generated"] + code_tags,
                        metadata={
                            "tool_id": node_id,
                            "quality_score": quality_score,
                            "is_tool": True
                        },
                        auto_embed=True
                    )

                console.print(f"[green]OK Registered as tool '{node_id}' (quality: {quality_score:.2f})[/green]")
            except Exception as e:
                console.print(f"[dim yellow]Note: Could not register as tool: {e}[/dim yellow]")

        # Display complete workflow summary if enabled
        if show_workflow:
            console.print("\n" + "="*70)
            console.print("[bold cyan]WORKFLOW SUMMARY:[/bold cyan]")
            console.print("="*70)
            console.print(workflow.format_text_display())
            console.print("="*70)

        return True

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
   - "transformer": Single input → transformed output (e.g., process text, calculate)
   - "combiner": Multiple inputs → single output (e.g., add two numbers)
   - "splitter": Single input → multiple outputs
   - "filter": Input → filtered/validated output

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
                model_key="overseer"
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
   - Example: "add 5 and 3" → test that add(5, 3) returns 8

2. For content generation tasks (write, generate, create):
   - Tests should validate the structure (main() exists, returns JSON)
   - Don't test the actual content (it's generated by LLM)
   - Focus on interface: input format, output format

3. For data processing tasks (sort, filter, transform):
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

EXAMPLE FOR CONTENT GENERATION:
```python
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_interface():
    \"\"\"Test that main() function exists and returns valid JSON\"\"\"
    print("Testing interface...")
    import main
    assert hasattr(main, 'main'), "main() function must exist"
    print("OK main() function exists")

if __name__ == "__main__":
    test_interface()
```

Now generate the interface-defining tests for: {description}

Output ONLY the Python test code (no markdown fences, no explanations):"""

        console.print(f"\n[cyan]Generating interface-defining tests first (TDD mode)...[/cyan]")

        test_code = self.client.generate(
            model=self.config.generator_model,
            prompt=test_prompt,
            temperature=0.3,  # Lower temperature for test generation
            model_key="generator"
        )

        # Clean the test code
        test_code = self._clean_code(test_code)

        console.print(f"[dim green]Generated interface tests ({len(test_code)} chars)[/dim green]")

        return test_code

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
        # Check if code uses call_tool - if so, generate minimal smoke test
        uses_call_tool = 'call_tool(' in code

        if uses_call_tool:
            # For code that uses external tools, just create a minimal smoke test
            # PYTHONPATH is already set by the test runner, so no need to manipulate sys.path
            test_code = """def test_structure():
    print("Testing code structure...")
    # Verify code can be imported without errors (PYTHONPATH is set by runner)
    try:
        import main
        print("OK Code structure is valid")
        assert hasattr(main, 'main'), "main() function exists"
        print("OK main() function found")
    except Exception as e:
        print("FAIL:", str(e))
        raise

if __name__ == "__main__":
    test_structure()
"""
            # Save and run this simple test
            test_path = self.runner.get_node_path(node_id).parent / "test_main.py"
            with open(test_path, 'w') as f:
                f.write(test_code)

            console.print("[dim]OK Generated smoke test for external tool code[/dim]")

        else:
            # For regular code, generate comprehensive tests
            test_prompt = f"""Generate unit tests for this code by analyzing what the code expects as input.

TASK DESCRIPTION: {description}

SPECIFICATION: {specification[:500]}

CODE TO TEST:
```python
{code}
```

INSTRUCTIONS:
1. Look at the code's main() function to see what fields it reads from input_data
2. Create test cases that match those expected fields
3. For arithmetic tasks like "add X and Y", create tests that call the functions directly with those numbers
4. **CRITICAL**: For code using call_tool(), DO NOT import call_tool, DO NOT call it, just create a simple structure test
5. Focus on testing the logic you CAN test, NOT external dependencies
6. If code only calls external tools, create a minimal smoke test that imports main.py

WHAT NOT TO DO:
- DO NOT write: from node_runtime import call_tool
- DO NOT write: call_tool("anything", ...)
- DO NOT try to test external LLM calls
- DO NOT test things that require network/external services

EXAMPLE FOR ARITHMETIC (if code defines testable functions):
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import add  # If main.py has an add() function

def test_add():
    print("Testing add function...")
    result = add(5, 3)
    assert result == 8, "Expected 8"
    print("OK Test passed")

if __name__ == "__main__":
    test_add()
```

EXAMPLE FOR CONTENT GENERATION (code uses call_tool()):
```python
# For code that uses call_tool(), we can't test the external LLM call
# Instead, just create a simple smoke test that verifies the structure
def test_structure():
    print("Testing code structure...")
    # Just verify the code can be imported without errors
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import main
        print("OK Code structure is valid")
    except Exception as e:
        print("FAIL:", str(e))
        raise

if __name__ == "__main__":
    test_structure()
```

CRITICAL REQUIREMENTS:
- Analyze the code structure to understand what it expects
- If code defines functions (def add(), def process(), etc.), import and test them directly
- If code uses call_tool(), you can mock it or just test the structure
- DO NOT assume generic input like {{"input": "test"}} - look at what the code actually reads!
- Use print() for logging
- Return ONLY executable Python code
- NO markdown fences
- NO explanations WHATSOEVER
- NO commentary like "These tests..." or "The test checks..."
- EVERY LINE must be valid Python syntax

The response must be PURE Python code that can be saved directly to a .py file and executed.
If you include ANY explanatory text, the tests will fail with a syntax error.

Return valid Python test code only - nothing else."""

            try:
                test_code = self.client.generate(
                    model=self.config.generator_model,
                    prompt=test_prompt,
                    temperature=0.3,
                    model_key="generator"
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

                    # CRITICAL: Remove any attempts to import or use call_tool in tests
                    if 'from node_runtime import' in stripped or 'import node_runtime' in stripped:
                        console.print(f"[dim]Filtering out node_runtime import: {stripped[:60]}...[/dim]")
                        continue
                    if 'call_tool(' in stripped:
                        console.print(f"[dim]Filtering out call_tool usage: {stripped[:60]}...[/dim]")
                        continue

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

                    # Skip lines that don't start with valid Python syntax (unless they're indented continuations)
                    if stripped and not line.startswith((' ', '\t')) and not any(stripped.startswith(s) for s in [
                        'import', 'from', 'def', 'class', '@', 'if', 'else', 'elif', 'for', 'while',
                        'try', 'except', 'finally', 'with', 'return', 'raise', 'assert', 'print',
                        '#', '"""', "'''", 'pass', 'break', 'continue', 'yield', 'async', 'await'
                    ]):
                        # This line doesn't look like Python
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
        Adaptive escalation with two-tier model strategy:
        1. Try fast codellama model first (3 attempts with increasing temperature)
        2. If all fail, escalate to powerful qwen2.5-coder model

        Tracks previous fixes to provide context for next iteration.
        """
        max_attempts = self.config.get("testing.max_escalation_attempts", 3)

        # Two-tier model strategy: fast model first, then powerful model
        fast_model = "codellama"
        powerful_model = self.config.escalation_model  # qwen2.5-coder:14b

        # Temperature progression: start low (focused), increase if needed (creative)
        temperature_schedule = [0.1, 0.3, 0.5]

        # Get error details from context
        error_output = self.context.get('last_error', 'Unknown error')
        stdout_output = self.context.get('last_stdout', '')
        test_output = self.context.get('last_test_output', '')

        # Track previous fix attempts
        previous_fixes = []

        for attempt in range(max_attempts):
            # Use fast model for first attempts, escalate to powerful model on last attempt
            current_model = fast_model if attempt < max_attempts - 1 else powerful_model
            model_label = "fast" if current_model == fast_model else "powerful"

            # Adjust temperature based on attempt
            temperature = temperature_schedule[min(attempt, len(temperature_schedule) - 1)]

            console.print(f"[cyan]Adaptive attempt {attempt + 1}/{max_attempts} ({model_label} model, temp: {temperature})...[/cyan]")

            # Build summary of previous attempts
            previous_attempts_summary = ""
            if previous_fixes:
                previous_attempts_summary = "\nPREVIOUS FIX ATTEMPTS (that didn't work):\n"
                for i, prev_fix in enumerate(previous_fixes, 1):
                    previous_attempts_summary += f"\nAttempt {i}:\n"
                    previous_attempts_summary += f"  Fixes tried: {', '.join(prev_fix['fixes'])}\n"
                    previous_attempts_summary += f"  Analysis: {prev_fix['analysis']}\n"
                    previous_attempts_summary += f"  Still failed with: {prev_fix['error'][:200]}\n"

            # Build comprehensive fix prompt with all context
            fix_prompt = f"""You are an expert code debugger. The following code FAILED its tests.

ORIGINAL GOAL:
{description}

OVERSEER STRATEGY:
{specification}

{available_tools if available_tools and "No specific tools" not in available_tools else ""}

CURRENT CODE (has errors):
```python
{code}
```

TEST ERROR OUTPUT:
{error_output}

{f'TEST EXECUTION LOG:\n{test_output}' if test_output else ''}

{f'STDOUT: {stdout_output}' if stdout_output else ''}

{previous_attempts_summary}

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
- CRITICAL: If the original code uses call_tool(), the fixed code MUST also use call_tool()
  * NEVER replace call_tool() with hardcoded data, dictionaries, or lists
  * NEVER remove call_tool() calls
  * NEVER create a mock or fake call_tool() function (def call_tool)
  * ALWAYS import call_tool from node_runtime: "from node_runtime import call_tool"
  * If call_tool() is failing due to missing module, add the import statement
- For content generation (jokes, stories, articles), always use call_tool("content_generator", prompt)

Return ONLY the JSON object, nothing else."""

            # Use appropriate model with adaptive temperature
            response = self.client.generate(
                model=current_model,
                prompt=fix_prompt,
                temperature=temperature,  # Adaptive temperature
                model_key="generator" if current_model == fast_model else "escalation"
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

            # Save fixed code
            self.runner.save_code(node_id, fixed_code)

            # Re-run tests
            console.print(f"[dim]Testing fix (attempt {attempt + 1})...[/dim]")
            sample_input = {"input": "test", "task": "test", "description": "test",
                          "query": "test", "topic": "test", "prompt": "test"}
            stdout, stderr, metrics = self.runner.run_node(node_id, sample_input)

            if metrics["success"]:
                console.print(f"[green]OK Fixed successfully on attempt {attempt + 1} ({model_label} model, temp: {temperature})[/green]")
                return True
            else:
                # Track this failed fix attempt
                previous_fixes.append({
                    'fixes': fixes if 'fixes' in locals() else [],
                    'analysis': analysis if 'analysis' in locals() else '',
                    'error': stderr,
                    'model': current_model,
                    'temperature': temperature
                })

                # Update error for next iteration
                self.context['last_error'] = stderr
                self.context['last_stdout'] = stdout

                next_step = ""
                if attempt < max_attempts - 2:
                    next_step = "trying with higher temperature on fast model"
                elif attempt == max_attempts - 2:
                    next_step = "escalating to powerful model"
                else:
                    next_step = "no more attempts"

                console.print(f"[yellow]Still has errors, {next_step}...[/yellow]")

            code = fixed_code  # Try to fix this version next

        console.print(f"[red]FAIL Could not fix after {max_attempts} adaptive attempts (fast model x{max_attempts-1}, powerful model x1)[/red]")
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
                model_key="escalation"  # Use escalation endpoint
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

    def handle_clear_rag(self) -> bool:
        """
        Handle clear_rag command - clears RAG memory and optionally registry/nodes.
        WARNING: This is destructive and cannot be undone!
        """
        console.print("\n[bold red]WARNING: This will clear all RAG memory and test data![/bold red]")
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

                elif user_input.lower() == 'clear_rag':
                    self.handle_clear_rag()

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
                    # Default behavior: treat as generation request
                    # Anything not recognized as a command is assumed to be a code generation request
                    console.print(f"[dim]Interpreting as: generate {user_input}[/dim]")
                    self.handle_generate(user_input)

            except KeyboardInterrupt:
                console.print("\n[dim]Use 'exit' to quit[/dim]")
                continue

            except EOFError:
                break

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        self._save_history()

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
        essential_tools = [
            "flake8_linter",      # Fast PEP 8 style checker
            "pylint_checker",     # Comprehensive quality checker
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
    chat = ChatCLI()
    chat.run()


if __name__ == "__main__":
    main()
