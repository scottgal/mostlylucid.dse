#!/usr/bin/env python3
"""
Workflow Runner Tool

Generates a combined Python script from a workflow with all dependencies inlined.
The goal is to reduce the workflow to JUST the required code with all imports properly resolved.
"""
import json
import sys
import os
import ast
import re
from typing import Dict, Any, Set, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ImportInfo:
    """Information about an import statement"""
    module: str
    names: List[str]  # For 'from X import Y, Z'
    alias: Optional[str] = None
    is_from_import: bool = False


class WorkflowRunner:
    """Generates combined scripts from workflows with all dependencies inlined"""

    def __init__(self, tools_root: str, code_evolver_root: str):
        self.tools_root = Path(tools_root)
        self.code_evolver_root = Path(code_evolver_root)
        self.analyzed_tools = set()  # Prevent circular dependencies
        self.collected_imports = {}  # module -> ImportInfo
        self.collected_code = []  # List of (priority, code_block) tuples
        self.tool_implementations = {}  # tool_id -> implementation code

    def generate_workflow_script(self, workflow_id: str) -> Dict[str, Any]:
        """
        Generate a combined script from a workflow

        Args:
            workflow_id: The workflow ID to generate script for

        Returns:
            Dictionary with:
            - script: The combined Python script
            - workflow_spec: The workflow specification
            - dependencies: List of resolved dependencies
            - stats: Statistics about the generated script
        """
        # Load workflow specification
        workflow_spec = self._load_workflow(workflow_id)
        if not workflow_spec:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        # Analyze all dependencies
        dependencies = self._analyze_workflow_dependencies(workflow_spec)

        # Generate the combined script
        script = self._generate_combined_script(workflow_spec, dependencies)

        # Calculate statistics
        stats = {
            'total_lines': len(script.split('\n')),
            'total_imports': len(self.collected_imports),
            'total_tools': len(dependencies['tools']),
            'has_parallel_tasks': dependencies['has_parallel_tasks']
        }

        # Convert sets to lists for JSON serialization
        dependencies_serializable = {
            'tools': list(dependencies['tools']) if isinstance(dependencies['tools'], set) else dependencies['tools'],
            'tool_types': list(dependencies['tool_types']),
            'has_parallel_tasks': dependencies['has_parallel_tasks'],
            'has_llm_calls': dependencies['has_llm_calls'],
            'step_dependencies': dependencies['step_dependencies']
        }

        return {
            'success': True,
            'workflow_id': workflow_id,
            'script': script,
            'workflow_spec': workflow_spec,
            'dependencies': dependencies_serializable,
            'stats': stats
        }

    def _load_workflow(self, workflow_id: str) -> Optional[Dict]:
        """Load workflow from JSON file"""
        # Try workflows directory first
        workflow_path = self.code_evolver_root / 'workflows' / f'{workflow_id}.json'
        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                return json.load(f)

        # Try tools/workflow directory
        workflow_path = self.tools_root / 'workflow' / f'{workflow_id}.json'
        if workflow_path.exists():
            with open(workflow_path, 'r') as f:
                return json.load(f)

        return None

    def _analyze_workflow_dependencies(self, workflow_spec: Dict) -> Dict[str, Any]:
        """Analyze all dependencies in a workflow"""
        dependencies = {
            'tools': [],
            'tool_types': set(),
            'has_parallel_tasks': False,
            'has_llm_calls': False,
            'step_dependencies': []
        }

        steps = workflow_spec.get('steps', [])

        # Check for parallel tasks
        parallel_groups = set()
        for step in steps:
            if 'parallel_group' in step:
                parallel_groups.add(step['parallel_group'])
                dependencies['has_parallel_tasks'] = True

        # Analyze each step
        for step in steps:
            step_id = step.get('step_id')
            step_type = step.get('type', step.get('step_type', ''))
            tool_name = step.get('tool', step.get('tool_name'))

            step_dep = {
                'step_id': step_id,
                'type': step_type,
                'tool': tool_name,
                'depends_on': step.get('depends_on', []),
                'parallel_group': step.get('parallel_group')
            }
            dependencies['step_dependencies'].append(step_dep)

            if tool_name:
                dependencies['tools'].append(tool_name)

                # Load tool definition and analyze
                tool_def = self._load_tool_definition(tool_name)
                if tool_def:
                    tool_type = tool_def.get('type', '')
                    dependencies['tool_types'].add(tool_type)

                    if tool_type == 'llm':
                        dependencies['has_llm_calls'] = True
                    elif tool_type == 'executable':
                        # Extract Python code from executable tools
                        self._extract_executable_code(tool_name, tool_def)

        return dependencies

    def _load_tool_definition(self, tool_id: str) -> Optional[Dict]:
        """Load tool definition from YAML file"""
        import yaml

        # Try different tool type directories
        for tool_type in ['llm', 'executable', 'openapi', 'workflow']:
            yaml_path = self.tools_root / tool_type / f'{tool_id}.yaml'
            if yaml_path.exists():
                with open(yaml_path, 'r') as f:
                    return yaml.safe_load(f)

        return None

    def _extract_executable_code(self, tool_id: str, tool_def: Dict):
        """Extract Python code from executable tool"""
        if tool_id in self.analyzed_tools:
            return

        self.analyzed_tools.add(tool_id)

        executable = tool_def.get('executable', {})
        args = executable.get('args', [])

        # Find Python script in args
        for arg in args:
            if arg.endswith('.py'):
                script_path = self._resolve_script_path(arg)
                if script_path and script_path.exists():
                    # Read and analyze the Python script
                    with open(script_path, 'r') as f:
                        code = f.read()

                    # Extract imports and code
                    self._analyze_python_code(code, tool_id)

                    # Recursively analyze if this tool calls other tools
                    # Look for subprocess calls or tool references in the code
                    self._find_and_analyze_nested_tools(code)
                    break

    def _find_and_analyze_nested_tools(self, code: str):
        """
        Find and analyze tools that are called from within this tool's code

        Args:
            code: Python source code to analyze
        """
        try:
            tree = ast.parse(code)

            # Look for subprocess calls that might invoke other tools
            for node in ast.walk(tree):
                # Look for subprocess.run() calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if (isinstance(node.func.value, ast.Name) and
                            node.func.value.id == 'subprocess' and
                            node.func.attr in ('run', 'Popen', 'call', 'check_output')):

                            # Try to extract the tool name from the command
                            if node.args:
                                # Look for Python tool invocations
                                for arg in node.args:
                                    if isinstance(arg, ast.List):
                                        # subprocess.run(['python', 'tool.py', ...])
                                        for elem in arg.elts:
                                            if isinstance(elem, ast.Constant):
                                                if isinstance(elem.value, str) and elem.value.endswith('.py'):
                                                    # Extract tool name from path
                                                    tool_path = Path(elem.value)
                                                    potential_tool_id = tool_path.stem

                                                    # Try to load and analyze this tool
                                                    nested_tool_def = self._load_tool_definition(potential_tool_id)
                                                    if nested_tool_def and potential_tool_id not in self.analyzed_tools:
                                                        tool_type = nested_tool_def.get('type', '')
                                                        if tool_type == 'executable':
                                                            self._extract_executable_code(potential_tool_id, nested_tool_def)

        except Exception as e:
            # Don't fail the whole process if nested analysis fails
            print(f"Warning: Could not analyze nested tools: {e}", file=sys.stderr)

    def _resolve_script_path(self, script_arg: str) -> Optional[Path]:
        """Resolve script path from tool argument"""
        # Handle {tool_dir} placeholder
        if '{tool_dir}' in script_arg:
            resolved = script_arg.replace('{tool_dir}/', '')
            return self.tools_root / 'executable' / resolved

        # Handle tools/ prefix
        if script_arg.startswith('tools/'):
            return self.code_evolver_root / script_arg

        # Handle code_evolver/ prefix
        if script_arg.startswith('code_evolver/'):
            return Path(script_arg)

        # Try as relative path
        path = Path(script_arg)
        if path.exists():
            return path

        return None

    def _analyze_python_code(self, code: str, tool_id: str):
        """Analyze Python code to extract imports and main logic"""
        try:
            tree = ast.parse(code)

            # Extract imports
            imports = []
            code_without_imports = []

            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(ast.unparse(node))
                    self._collect_import(node)
                else:
                    # Collect the rest of the code
                    code_without_imports.append(ast.unparse(node))

            # Store the tool implementation (without imports)
            implementation = '\n'.join(code_without_imports)
            self.tool_implementations[tool_id] = implementation

        except Exception as e:
            print(f"Warning: Could not parse code for {tool_id}: {e}", file=sys.stderr)

    def _collect_import(self, node):
        """Collect import information from AST node"""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                import_alias = alias.asname

                if module not in self.collected_imports:
                    self.collected_imports[module] = ImportInfo(
                        module=module,
                        names=[],
                        alias=import_alias,
                        is_from_import=False
                    )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            names = [alias.name for alias in node.names]

            # Group from imports by module
            if module not in self.collected_imports:
                self.collected_imports[module] = ImportInfo(
                    module=module,
                    names=names,
                    is_from_import=True
                )
            else:
                # Merge names if module already exists
                existing = self.collected_imports[module]
                if existing.is_from_import:
                    existing.names.extend(names)
                    existing.names = list(set(existing.names))  # Remove duplicates

    def _generate_combined_script(self, workflow_spec: Dict, dependencies: Dict) -> str:
        """Generate the final combined Python script"""
        sections = []

        # Header
        sections.append(self._generate_header(workflow_spec))

        # Imports
        sections.append(self._generate_imports())

        # Type definitions (if needed for parallel tasks)
        if dependencies['has_parallel_tasks']:
            sections.append(self._generate_parallel_types())

        # Template expansion helper (always include)
        sections.append(self._generate_template_expansion_helper())

        # Tool implementations
        sections.append(self._generate_tool_implementations())

        # Workflow execution logic
        sections.append(self._generate_workflow_logic(workflow_spec, dependencies))

        # Main entry point
        sections.append(self._generate_main(workflow_spec))

        return '\n\n'.join(filter(None, sections))

    def _generate_header(self, workflow_spec: Dict) -> str:
        """Generate script header with docstring"""
        workflow_id = workflow_spec.get('workflow_id', 'unknown')
        description = workflow_spec.get('description', '')
        version = workflow_spec.get('version', '1.0.0')

        return f'''#!/usr/bin/env python3
"""
Generated Workflow Script: {workflow_id}

{description}

Version: {version}
Generated by: mostlylucid DiSE Workflow Runner
"""'''

    def _generate_imports(self) -> str:
        """Generate consolidated imports section"""
        import_lines = []

        # Standard library imports (always needed)
        stdlib_imports = {
            'json', 'sys', 'os', 'pathlib', 'io', 'contextlib', 're'
        }

        # Add imports from collected code
        for module, info in sorted(self.collected_imports.items()):
            if info.is_from_import and info.names:
                names = ', '.join(sorted(info.names))
                import_lines.append(f'from {module} import {names}')
            else:
                if info.alias:
                    import_lines.append(f'import {module} as {info.alias}')
                else:
                    import_lines.append(f'import {module}')

        # Add standard library imports if not already present
        for stdlib in sorted(stdlib_imports):
            if stdlib not in self.collected_imports:
                import_lines.append(f'import {stdlib}')

        # Add typing imports (always needed for workflow execution)
        if 'typing' not in self.collected_imports:
            import_lines.append('from typing import Dict, Any, List, Optional, Tuple')
        else:
            # Check if we need to add more typing imports
            existing_names = set(self.collected_imports['typing'].names)
            needed = {'Dict', 'Any', 'List', 'Optional', 'Tuple'}
            missing = needed - existing_names
            if missing:
                # Update the typing import
                all_names = sorted(existing_names | needed)
                # Find and replace the typing import line
                for i, line in enumerate(import_lines):
                    if line.startswith('from typing import'):
                        import_lines[i] = f'from typing import {", ".join(all_names)}'
                        break

        return '\n'.join(import_lines)

    def _generate_parallel_types(self) -> str:
        """Generate type definitions for parallel task handling"""
        return '''# Parallel task execution support
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from typing import Callable

@dataclass
class TaskResult:
    """Result of a task execution"""
    step_id: str
    success: bool
    output: Any
    error: Optional[str] = None

class ParallelExecutor:
    """Handles parallel task execution"""

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.results = {}
        self.lock = threading.Lock()

    def submit_task(self, step_id: str, func: Callable, *args, **kwargs) -> Future:
        """Submit a task for execution"""
        future = self.executor.submit(func, *args, **kwargs)
        return future

    def wait_for_tasks(self, futures: Dict[str, Future]) -> Dict[str, TaskResult]:
        """Wait for all tasks to complete"""
        results = {}
        for step_id, future in futures.items():
            try:
                output = future.result()
                results[step_id] = TaskResult(step_id, True, output)
            except Exception as e:
                results[step_id] = TaskResult(step_id, False, None, str(e))
        return results

    def shutdown(self):
        """Shutdown the executor"""
        self.executor.shutdown(wait=True)'''

    def _generate_tool_implementations(self) -> str:
        """Generate all tool implementations"""
        if not self.tool_implementations:
            return ''

        sections = ['# Tool Implementations']

        for tool_id, implementation in self.tool_implementations.items():
            sections.append(f'\n# Tool: {tool_id}')

            # Rename main() function to main_{tool_id}() to avoid conflicts
            # This allows each tool to have its own main function
            modified_impl = implementation.replace(
                'def main(',
                f'def main_{tool_id}('
            )

            # Also handle 'if __name__ == "__main__":' blocks - comment them out
            # since they shouldn't run in the combined script
            lines = modified_impl.split('\n')
            processed_lines = []
            in_main_block = False

            for line in lines:
                if "if __name__ == '__main__':" in line or 'if __name__ == "__main__":' in line:
                    in_main_block = True
                    processed_lines.append(f'# {line}  # Disabled in combined script')
                elif in_main_block:
                    # Indent check - if dedented, we're out of the main block
                    if line and not line[0].isspace():
                        in_main_block = False
                        processed_lines.append(line)
                    else:
                        # Still in main block - comment it out
                        processed_lines.append(f'# {line}' if line.strip() else line)
                else:
                    processed_lines.append(line)

            modified_impl = '\n'.join(processed_lines)
            sections.append(modified_impl)

        return '\n'.join(sections)

    def _generate_template_expansion_helper(self) -> str:
        """Generate template expansion helper function"""
        return '''# Template Expansion Helper
import re as _re

def _expand_template(template: str, inputs_dict: Dict[str, Any], outputs_dict: Dict[str, Any]) -> str:
    """Expand {var} templates with values from inputs/outputs"""
    result = template
    # Find all {variable} patterns
    for match in _re.finditer(r'\\{([^}]+)\\}', template):
        var_name = match.group(1)
        if "." in var_name:
            # Handle nested like {dependencies.file_list}
            parts = var_name.split(".")
            value = outputs_dict.get(parts[0], {})
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    value = ""
                    break
            result = result.replace(match.group(0), str(value))
        else:
            # Simple variable from inputs
            value = inputs_dict.get(var_name, "")
            result = result.replace(match.group(0), str(value))
    return result
'''

    def _generate_workflow_logic(self, workflow_spec: Dict, dependencies: Dict) -> str:
        """Generate workflow execution logic"""
        sections = ['# Workflow Execution Logic']

        workflow_id = workflow_spec.get('workflow_id', 'workflow')
        steps = workflow_spec.get('steps', [])

        # Generate workflow execution function
        sections.append(f'\ndef execute_{workflow_id}(inputs: Dict[str, Any]) -> Dict[str, Any]:')
        sections.append('    """Execute the workflow"""')
        sections.append('    step_outputs = {}')
        sections.append('    ')

        # Check if we need parallel execution
        if dependencies['has_parallel_tasks']:
            sections.append('    # Initialize parallel executor')
            sections.append('    executor = ParallelExecutor()')
            sections.append('    ')

        # Group steps by parallel groups
        parallel_groups = {}
        sequential_steps = []

        for step in steps:
            parallel_group = step.get('parallel_group')
            if parallel_group is not None:
                if parallel_group not in parallel_groups:
                    parallel_groups[parallel_group] = []
                parallel_groups[parallel_group].append(step)
            else:
                sequential_steps.append(step)

        # Generate execution code
        if parallel_groups:
            # Execute parallel groups
            for group_id in sorted(parallel_groups.keys()):
                group_steps = parallel_groups[group_id]
                sections.append(f'    # Parallel group {group_id}')
                sections.append('    futures = {}')

                for step in group_steps:
                    step_id = step.get('step_id')
                    sections.append(f'    futures["{step_id}"] = executor.submit_task(')
                    sections.append(f'        "{step_id}",')
                    sections.append(f'        execute_step_{step_id},')
                    sections.append('        inputs, step_outputs')
                    sections.append('    )')

                sections.append('    ')
                sections.append('    # Wait for parallel tasks')
                sections.append('    results = executor.wait_for_tasks(futures)')
                sections.append('    for step_id, result in results.items():')
                sections.append('        if result.success:')
                sections.append('            step_outputs[step_id] = result.output')
                sections.append('        else:')
                sections.append('            raise RuntimeError(f"Step {step_id} failed: {result.error}")')
                sections.append('    ')

        # Execute sequential steps
        for step in sequential_steps:
            step_id = step.get('step_id')
            sections.append(f'    # Step: {step_id}')
            sections.append(f'    step_outputs["{step_id}"] = execute_step_{step_id}(inputs, step_outputs)')
            sections.append('    ')

        # Cleanup parallel executor if used
        if dependencies['has_parallel_tasks']:
            sections.append('    executor.shutdown()')
            sections.append('    ')

        # Return outputs
        sections.append('    # Collect workflow outputs')
        sections.append('    outputs = {}')

        workflow_outputs = workflow_spec.get('outputs', {})
        for output_name, output_spec in workflow_outputs.items():
            source_ref = output_spec.get('source_reference', '')
            if source_ref:
                # Parse source reference (e.g., "steps.final_step.output")
                parts = source_ref.split('.')
                if len(parts) >= 2 and parts[0] == 'steps':
                    step_id = parts[1]
                    output_key = parts[2] if len(parts) > 2 else 'output'
                    sections.append(f'    outputs["{output_name}"] = step_outputs.get("{step_id}", {{}}).get("{output_key}")')

        sections.append('    ')
        sections.append('    return outputs')
        sections.append('    ')

        # Generate individual step execution functions
        for step in steps:
            step_code = self._generate_step_function(step, workflow_spec)
            sections.append(step_code)

        return '\n'.join(sections)

    def _generate_step_function(self, step: Dict, workflow_spec: Dict) -> str:
        """Generate execution function for a single step"""
        step_id = step.get('step_id')
        step_type = step.get('type', step.get('step_type', ''))
        tool_name = step.get('tool', step.get('tool_name'))
        description = step.get('description', '')

        lines = []
        lines.append(f'def execute_step_{step_id}(inputs: Dict[str, Any], step_outputs: Dict[str, Any]) -> Any:')
        lines.append(f'    """{description}"""')

        # Map inputs - handle both 'input_mapping' (new format) and 'input' (old format)
        input_mapping = step.get('input_mapping', step.get('input', {}))
        lines.append('    # Map inputs')
        lines.append('    step_inputs = {}')

        for param_name, source_ref in input_mapping.items():
            if isinstance(source_ref, str):
                if source_ref.startswith('inputs.'):
                    input_key = source_ref.replace('inputs.', '')
                    lines.append(f'    step_inputs["{param_name}"] = inputs.get("{input_key}")')
                elif source_ref.startswith('steps.'):
                    # Parse "steps.step_id.output_name"
                    parts = source_ref.split('.')
                    if len(parts) >= 2:
                        source_step = parts[1]
                        output_key = parts[2] if len(parts) > 2 else 'output'
                        lines.append(f'    step_inputs["{param_name}"] = step_outputs.get("{source_step}", {{}}).get("{output_key}")')
                else:
                    # Handle template variable expansion for literal strings
                    # Check if it contains template variables like {variable}
                    if '{' in source_ref and '}' in source_ref:
                        # It needs runtime template expansion
                        lines.append(f'    # Expand template variables at runtime')
                        lines.append(f'    step_inputs["{param_name}"] = _expand_template({repr(source_ref)}, inputs, step_outputs)')
                    else:
                        # Plain literal value
                        lines.append(f'    step_inputs["{param_name}"] = {repr(source_ref)}')
            else:
                # Literal value - use repr for proper Python syntax
                lines.append(f'    step_inputs["{param_name}"] = {repr(source_ref)}')

        lines.append('    ')

        # Execute step based on type
        if step_type in ('llm_call', 'LLM_CALL'):
            lines.append('    # Execute LLM call')
            lines.append(f'    # Note: LLM tool {tool_name} requires runtime LLM client')
            lines.append('    # This is a placeholder - implement LLM client integration')
            lines.append('    result = {"error": "LLM calls require runtime LLM client integration"}')
        elif step_type in ('python_tool', 'PYTHON_TOOL', 'existing_tool', 'EXISTING_TOOL', 'executable'):
            if tool_name and tool_name in self.tool_implementations:
                lines.append(f'    # Execute tool: {tool_name}')
                lines.append('    # Call the inlined tool\'s main logic')
                lines.append('    try:')
                lines.append('        # Simulate calling the tool\'s main() function')
                lines.append('        import io')
                lines.append('        import contextlib')
                lines.append('        ')
                lines.append('        # Prepare input as JSON string (tool expects JSON from argv)')
                lines.append('        input_json = json.dumps(step_inputs)')
                lines.append('        ')
                lines.append('        # Capture stdout from tool execution')
                lines.append('        stdout_capture = io.StringIO()')
                lines.append('        with contextlib.redirect_stdout(stdout_capture):')
                lines.append('            # Simulate sys.argv for the tool')
                lines.append('            old_argv = sys.argv')
                lines.append('            sys.argv = ["tool", input_json]')
                lines.append('            try:')
                lines.append(f'                # Call {tool_name}\'s main function')
                lines.append(f'                main_{tool_name}()')
                lines.append('            finally:')
                lines.append('                sys.argv = old_argv')
                lines.append('        ')
                lines.append('        # Parse the JSON output from the tool')
                lines.append('        output_str = stdout_capture.getvalue().strip()')
                lines.append('        if output_str:')
                lines.append('            result = json.loads(output_str)')
                lines.append('        else:')
                lines.append('            result = {"success": True}')
                lines.append('    except Exception as e:')
                lines.append('        result = {"success": False, "error": str(e)}')
            else:
                lines.append(f'    # Tool {tool_name} not found in implementations')
                lines.append('    # This may be an external dependency or missing tool')
                lines.append(f'    result = {{"error": "Tool {tool_name} not available in standalone script"}}')
        else:
            # Handle generic step types
            if tool_name and tool_name in self.tool_implementations:
                lines.append(f'    # Execute tool: {tool_name}')
                lines.append('    try:')
                lines.append('        import io')
                lines.append('        import contextlib')
                lines.append('        input_json = json.dumps(step_inputs)')
                lines.append('        stdout_capture = io.StringIO()')
                lines.append('        with contextlib.redirect_stdout(stdout_capture):')
                lines.append('            old_argv = sys.argv')
                lines.append('            sys.argv = ["tool", input_json]')
                lines.append('            try:')
                lines.append(f'                main_{tool_name}()')
                lines.append('            finally:')
                lines.append('                sys.argv = old_argv')
                lines.append('        output_str = stdout_capture.getvalue().strip()')
                lines.append('        if output_str:')
                lines.append('            result = json.loads(output_str)')
                lines.append('        else:')
                lines.append('            result = {"success": True}')
                lines.append('    except Exception as e:')
                lines.append('        result = {"success": False, "error": str(e)}')
            else:
                lines.append(f'    # Step type: {step_type}, tool: {tool_name}')
                lines.append('    result = {}')

        lines.append('    ')
        lines.append('    return result')
        lines.append('')

        return '\n'.join(lines)

    def _expand_template_vars(self, template: str, inputs_var: str, outputs_var: str) -> str:
        """
        Generate code to expand template variables at runtime

        Args:
            template: String with {var} placeholders
            inputs_var: Name of inputs variable
            outputs_var: Name of outputs variable

        Returns:
            String that will be expanded at runtime
        """
        # Template will be expanded at runtime using string formatting
        # Convert {var} to {inputs[var]} syntax for runtime expansion
        # This is returned as a template string that will be formatted at runtime
        return template

    def _generate_main(self, workflow_spec: Dict) -> str:
        """Generate main entry point"""
        workflow_id = workflow_spec.get('workflow_id', 'workflow')
        return f'''# Main entry point
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({{
            'error': 'Missing configuration JSON argument'
        }}))
        sys.exit(1)

    try:
        # Parse configuration
        config = json.loads(sys.argv[1])

        # Execute workflow
        result = execute_{workflow_id}(config)

        # Output result
        print(json.dumps({{
            'success': True,
            'result': result
        }}))

    except Exception as e:
        print(json.dumps({{
            'error': str(e)
        }}))
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)'''


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': 'Missing configuration JSON argument'
        }))
        sys.exit(1)

    try:
        # Parse configuration
        config = json.loads(sys.argv[1])
        workflow_id = config.get('workflow_id')

        if not workflow_id:
            print(json.dumps({
                'error': 'workflow_id is required'
            }))
            sys.exit(1)

        # Auto-detect paths
        default_tools_root = 'tools' if os.path.exists('tools') else 'code_evolver/tools'
        tools_root = config.get('tools_root', default_tools_root)

        default_code_root = '.' if os.path.exists('./workflows') else 'code_evolver'
        code_evolver_root = config.get('code_evolver_root', default_code_root)

        # Generate workflow script
        runner = WorkflowRunner(tools_root, code_evolver_root)
        result = runner.generate_workflow_script(workflow_id)

        # Output result
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'error': f'Error generating workflow script: {e}'
        }))
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
