"""
Compilation Module for Tools and Workflows

Handles compilation of tools and workflows to various formats:
- Executable (--app): Platform-specific executables
- Script (--script): Python scripts (single file or modular)
"""

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
import yaml


class CompilationError(Exception):
    """Raised when compilation fails."""
    pass


class Compiler:
    """
    Handles compilation of tools and workflows to different formats.
    """

    def __init__(self, tools_manager=None):
        """
        Initialize compiler.

        Args:
            tools_manager: Optional ToolsManager instance for tool definitions
        """
        self.tools_manager = tools_manager
        self.platform = platform.system().lower()  # 'linux', 'windows', 'darwin'

    def get_platform_executable_extension(self, target_platform: Optional[str] = None) -> str:
        """
        Get the executable extension for a platform.

        Args:
            target_platform: Target platform (windows, linux, darwin). Uses current if None.

        Returns:
            Extension ('.exe' for Windows, '' for Linux/Mac)
        """
        if target_platform:
            return ".exe" if target_platform.lower() == "windows" else ""
        return ".exe" if self.platform == "windows" else ""

    def compile_tool_to_app(
        self,
        tool_id: str,
        output_path: Optional[Path] = None,
        target_platform: Optional[str] = None,
        app_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compile a tool to a platform-specific executable.

        Args:
            tool_id: Tool identifier
            output_path: Output directory (default: ./dist/)
            target_platform: Target platform (windows/linux/darwin). Uses current if None.
            app_name: Custom app name. Uses tool_id if None.

        Returns:
            Dict with compilation result info

        Raises:
            CompilationError: If compilation fails
        """
        if not self.tools_manager:
            raise CompilationError("ToolsManager not available")

        # Get tool definition
        tool_def = self._get_tool_definition(tool_id)
        if not tool_def:
            raise CompilationError(f"Tool '{tool_id}' not found")

        # Setup paths
        output_path = output_path or Path("./dist")
        output_path.mkdir(parents=True, exist_ok=True)

        app_name = app_name or tool_id
        target_platform = target_platform or self.platform

        # Generate standalone script first
        script_path = output_path / f"{app_name}_temp.py"
        self.compile_tool_to_script(
            tool_id=tool_id,
            output_path=script_path,
            script_type="single"
        )

        # Use PyInstaller to build executable
        exe_name = f"{app_name}{self.get_platform_executable_extension(target_platform)}"
        exe_path = output_path / exe_name

        try:
            # Check if PyInstaller is available
            result = subprocess.run(
                ["pyinstaller", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise CompilationError("PyInstaller not found. Install with: pip install pyinstaller")

            # Build executable
            cmd = [
                "pyinstaller",
                "--onefile",  # Single executable
                "--name", app_name,
                "--distpath", str(output_path),
                "--workpath", str(output_path / "build"),
                "--specpath", str(output_path / "spec"),
                "--clean",
                str(script_path)
            ]

            # Cross-compilation note (PyInstaller limitation)
            if target_platform and target_platform.lower() != self.platform:
                raise CompilationError(
                    f"Cross-compilation to {target_platform} not supported. "
                    f"PyInstaller must be run on the target platform."
                )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode != 0:
                raise CompilationError(f"PyInstaller failed: {result.stderr}")

        finally:
            # Clean up temp script
            if script_path.exists():
                script_path.unlink()

        return {
            "tool_id": tool_id,
            "app_name": app_name,
            "output_path": str(exe_path),
            "platform": target_platform,
            "size_bytes": exe_path.stat().st_size if exe_path.exists() else 0,
            "executable": True
        }

    def compile_tool_to_script(
        self,
        tool_id: str,
        output_path: Optional[Path] = None,
        script_type: Literal["single", "tools"] = "single"
    ) -> Dict[str, Any]:
        """
        Compile a tool to a Python script.

        Args:
            tool_id: Tool identifier
            output_path: Output file path. Defaults to ./output/{tool_id}.py
            script_type:
                - "single": Single file with all tools inlined
                - "tools": Modular structure with separate tool files

        Returns:
            Dict with compilation result info

        Raises:
            CompilationError: If compilation fails
        """
        if not self.tools_manager:
            raise CompilationError("ToolsManager not available")

        # Get tool definition
        tool_def = self._get_tool_definition(tool_id)
        if not tool_def:
            raise CompilationError(f"Tool '{tool_id}' not found")

        # Setup paths
        if output_path is None:
            output_path = Path("./output") / f"{tool_id}.py"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if script_type == "single":
            return self._compile_single_script(tool_id, tool_def, output_path)
        elif script_type == "tools":
            return self._compile_modular_script(tool_id, tool_def, output_path)
        else:
            raise CompilationError(f"Unknown script type: {script_type}")

    def _compile_single_script(
        self,
        tool_id: str,
        tool_def: Dict[str, Any],
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Compile tool to a single standalone script with all dependencies inlined.
        """
        # Start building the script
        script_lines = [
            "#!/usr/bin/env python3",
            '"""',
            f"Standalone script for tool: {tool_id}",
            f"Generated from tool definition: {tool_def.get('name', tool_id)}",
            '"""',
            "",
            "import sys",
            "import json",
            "from typing import Dict, Any",
            "",
        ]

        # Add tool implementation
        tool_type = tool_def.get("type", "unknown")

        if tool_type == "executable":
            # For executable tools, inline the Python code
            code = tool_def.get("implementation", {}).get("code", "")
            if not code:
                raise CompilationError(f"Tool '{tool_id}' has no implementation code")

            script_lines.append("# Tool Implementation")
            script_lines.append(code)
            script_lines.append("")

        elif tool_type == "llm":
            # For LLM tools, create a wrapper that calls an LLM
            script_lines.extend([
                "# LLM Tool Wrapper",
                "def execute_llm_tool(input_data: Dict[str, Any]) -> Dict[str, Any]:",
                "    '''Executes LLM-based tool.'''",
                f"    # Tool: {tool_id}",
                f"    # Prompt: {tool_def.get('prompt', {}).get('template', '')}",
                "    print('LLM tools require an LLM backend to run.', file=sys.stderr)",
                "    return {'error': 'LLM backend not available in standalone script'}",
                "",
            ])

        # Add main execution block
        script_lines.extend([
            "def main():",
            "    '''Main entry point.'''",
            "    if len(sys.argv) > 1:",
            "        # Read input from command line argument (JSON)",
            "        try:",
            "            input_data = json.loads(sys.argv[1])",
            "        except json.JSONDecodeError:",
            "            print('Error: Input must be valid JSON', file=sys.stderr)",
            "            sys.exit(1)",
            "    else:",
            "        # Read from stdin",
            "        input_data = {}",
            "",
            "    # Execute the tool",
            "    try:",
            f"        if '{tool_type}' == 'executable':",
            "            # Find and call the main function",
            "            result = execute(input_data) if 'execute' in dir() else {}",
            "        else:",
            "            result = execute_llm_tool(input_data)",
            "        ",
            "        # Output result as JSON",
            "        print(json.dumps(result, indent=2))",
            "    except Exception as e:",
            "        print(f'Error: {e}', file=sys.stderr)",
            "        sys.exit(1)",
            "",
            "if __name__ == '__main__':",
            "    main()",
        ])

        # Write the script
        script_content = "\n".join(script_lines)
        output_path.write_text(script_content)

        # Make executable on Unix
        if self.platform != "windows":
            output_path.chmod(0o755)

        return {
            "tool_id": tool_id,
            "output_path": str(output_path),
            "script_type": "single",
            "size_bytes": output_path.stat().st_size,
            "lines": len(script_lines)
        }

    def _compile_modular_script(
        self,
        tool_id: str,
        tool_def: Dict[str, Any],
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Compile tool to modular structure with separate tool directories.
        """
        # Create output directory structure
        base_dir = output_path.parent / output_path.stem
        base_dir.mkdir(parents=True, exist_ok=True)

        tools_dir = base_dir / "tools"
        tools_dir.mkdir(exist_ok=True)

        # Create main script
        main_script = base_dir / "main.py"
        main_lines = [
            "#!/usr/bin/env python3",
            '"""',
            f"Main script for tool: {tool_id}",
            "Tool implementation is in ./tools/ directory",
            '"""',
            "",
            "import sys",
            "import json",
            "from pathlib import Path",
            "",
            "# Add tools directory to path",
            "sys.path.insert(0, str(Path(__file__).parent / 'tools'))",
            "",
            f"# Import the tool",
            f"from {tool_id} import execute",
            "",
            "def main():",
            "    '''Main entry point.'''",
            "    if len(sys.argv) > 1:",
            "        try:",
            "            input_data = json.loads(sys.argv[1])",
            "        except json.JSONDecodeError:",
            "            print('Error: Input must be valid JSON', file=sys.stderr)",
            "            sys.exit(1)",
            "    else:",
            "        input_data = {}",
            "",
            "    # Execute the tool",
            "    try:",
            "        result = execute(input_data)",
            "        print(json.dumps(result, indent=2))",
            "    except Exception as e:",
            "        print(f'Error: {e}', file=sys.stderr)",
            "        sys.exit(1)",
            "",
            "if __name__ == '__main__':",
            "    main()",
        ]
        main_script.write_text("\n".join(main_lines))

        # Create tool directory
        tool_dir = tools_dir / tool_id
        tool_dir.mkdir(exist_ok=True)

        # Write tool implementation
        tool_impl = tool_dir / "__init__.py"
        code = tool_def.get("implementation", {}).get("code", "")
        if not code:
            code = "def execute(input_data):\n    return {'error': 'No implementation'}"

        tool_impl.write_text(code)

        # Write tool metadata
        metadata_file = tool_dir / "metadata.json"
        metadata = {
            "tool_id": tool_id,
            "name": tool_def.get("name", tool_id),
            "description": tool_def.get("description", ""),
            "version": tool_def.get("version", "1.0"),
            "type": tool_def.get("type", "unknown"),
        }
        metadata_file.write_text(json.dumps(metadata, indent=2))

        # Write README
        readme_file = tool_dir / "README.md"
        readme_content = f"""# {tool_def.get('name', tool_id)}

{tool_def.get('description', '')}

## Type
{tool_def.get('type', 'unknown')}

## Usage

```bash
python main.py '{{"key": "value"}}'
```
"""
        readme_file.write_text(readme_content)

        return {
            "tool_id": tool_id,
            "output_path": str(base_dir),
            "script_type": "tools",
            "main_script": str(main_script),
            "tool_directory": str(tool_dir),
            "files_created": [
                str(main_script),
                str(tool_impl),
                str(metadata_file),
                str(readme_file)
            ]
        }

    def compile_workflow_to_app(
        self,
        workflow_id: str,
        output_path: Optional[Path] = None,
        target_platform: Optional[str] = None,
        app_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compile a workflow to a platform-specific executable.

        Args:
            workflow_id: Workflow identifier
            output_path: Output directory
            target_platform: Target platform
            app_name: Custom app name

        Returns:
            Dict with compilation result

        Raises:
            CompilationError: If compilation fails
        """
        # Load workflow definition
        workflow_def = self._get_workflow_definition(workflow_id)
        if not workflow_def:
            raise CompilationError(f"Workflow '{workflow_id}' not found")

        # Setup paths
        output_path = output_path or Path("./dist")
        output_path.mkdir(parents=True, exist_ok=True)

        app_name = app_name or workflow_id
        target_platform = target_platform or self.platform

        # Generate standalone script first
        script_path = output_path / f"{app_name}_temp.py"
        self.compile_workflow_to_script(
            workflow_id=workflow_id,
            output_path=script_path,
            script_type="single"
        )

        # Use PyInstaller to build executable
        exe_name = f"{app_name}{self.get_platform_executable_extension(target_platform)}"
        exe_path = output_path / exe_name

        try:
            # Check if PyInstaller is available
            result = subprocess.run(
                ["pyinstaller", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise CompilationError("PyInstaller not found. Install with: pip install pyinstaller")

            # Build executable
            cmd = [
                "pyinstaller",
                "--onefile",
                "--name", app_name,
                "--distpath", str(output_path),
                "--workpath", str(output_path / "build"),
                "--specpath", str(output_path / "spec"),
                "--clean",
                str(script_path)
            ]

            if target_platform and target_platform.lower() != self.platform:
                raise CompilationError(
                    f"Cross-compilation to {target_platform} not supported. "
                    f"PyInstaller must be run on the target platform."
                )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise CompilationError(f"PyInstaller failed: {result.stderr}")

        finally:
            # Clean up temp script
            if script_path.exists():
                script_path.unlink()

        return {
            "workflow_id": workflow_id,
            "app_name": app_name,
            "output_path": str(exe_path),
            "platform": target_platform,
            "size_bytes": exe_path.stat().st_size if exe_path.exists() else 0,
            "executable": True
        }

    def compile_workflow_to_script(
        self,
        workflow_id: str,
        output_path: Optional[Path] = None,
        script_type: Literal["single", "tools"] = "single"
    ) -> Dict[str, Any]:
        """
        Compile a workflow to a Python script.

        Args:
            workflow_id: Workflow identifier
            output_path: Output file path
            script_type: "single" or "tools"

        Returns:
            Dict with compilation result

        Raises:
            CompilationError: If compilation fails
        """
        # Load workflow definition
        workflow_def = self._get_workflow_definition(workflow_id)
        if not workflow_def:
            raise CompilationError(f"Workflow '{workflow_id}' not found")

        # Setup paths
        if output_path is None:
            output_path = Path("./output") / f"{workflow_id}_workflow.py"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if script_type == "single":
            return self._compile_workflow_single_script(workflow_id, workflow_def, output_path)
        elif script_type == "tools":
            return self._compile_workflow_modular_script(workflow_id, workflow_def, output_path)
        else:
            raise CompilationError(f"Unknown script type: {script_type}")

    def _compile_workflow_single_script(
        self,
        workflow_id: str,
        workflow_def: Dict[str, Any],
        output_path: Path
    ) -> Dict[str, Any]:
        """Compile workflow to single standalone script."""
        script_lines = [
            "#!/usr/bin/env python3",
            '"""',
            f"Standalone workflow script: {workflow_id}",
            f"Workflow: {workflow_def.get('name', workflow_id)}",
            f"Description: {workflow_def.get('description', '')}",
            '"""',
            "",
            "import sys",
            "import json",
            "from typing import Dict, Any",
            "",
            "def execute_workflow(inputs: Dict[str, Any]) -> Dict[str, Any]:",
            "    '''Execute the workflow.'''",
            "    results = {}",
            "    context = inputs.copy()",
            "",
        ]

        # Add each workflow step
        steps = workflow_def.get("steps", [])
        for i, step in enumerate(steps):
            step_id = step.get("step_id", f"step_{i}")
            tool = step.get("tool", "unknown")
            description = step.get("description", "")

            script_lines.extend([
                f"    # Step {i + 1}: {description}",
                f"    print(f'Executing step {i + 1}: {step_id}...', file=sys.stderr)",
                f"    # Tool: {tool}",
                f"    # TODO: Implement tool '{tool}' execution",
                f"    results['{step_id}'] = {{'status': 'not_implemented'}}",
                "",
            ])

        script_lines.extend([
            "    return results",
            "",
            "def main():",
            "    '''Main entry point.'''",
            "    if len(sys.argv) > 1:",
            "        try:",
            "            inputs = json.loads(sys.argv[1])",
            "        except json.JSONDecodeError:",
            "            print('Error: Input must be valid JSON', file=sys.stderr)",
            "            sys.exit(1)",
            "    else:",
            "        inputs = {}",
            "",
            "    try:",
            "        results = execute_workflow(inputs)",
            "        print(json.dumps(results, indent=2))",
            "    except Exception as e:",
            "        print(f'Error: {e}', file=sys.stderr)",
            "        sys.exit(1)",
            "",
            "if __name__ == '__main__':",
            "    main()",
        ])

        script_content = "\n".join(script_lines)
        output_path.write_text(script_content)

        # Make executable on Unix
        if self.platform != "windows":
            output_path.chmod(0o755)

        return {
            "workflow_id": workflow_id,
            "output_path": str(output_path),
            "script_type": "single",
            "size_bytes": output_path.stat().st_size,
            "steps": len(steps),
            "lines": len(script_lines)
        }

    def _compile_workflow_modular_script(
        self,
        workflow_id: str,
        workflow_def: Dict[str, Any],
        output_path: Path
    ) -> Dict[str, Any]:
        """Compile workflow to modular structure."""
        # Similar to modular tool compilation
        base_dir = output_path.parent / output_path.stem
        base_dir.mkdir(parents=True, exist_ok=True)

        # Create main script and workflow definition
        main_script = base_dir / "main.py"
        workflow_file = base_dir / "workflow.json"

        # Write workflow definition
        workflow_file.write_text(json.dumps(workflow_def, indent=2))

        # Create main script that loads workflow
        main_lines = [
            "#!/usr/bin/env python3",
            '"""',
            f"Workflow executor: {workflow_id}",
            '"""',
            "import sys",
            "import json",
            "from pathlib import Path",
            "",
            "def main():",
            "    workflow_file = Path(__file__).parent / 'workflow.json'",
            "    with open(workflow_file) as f:",
            "        workflow = json.load(f)",
            "",
            "    print(f'Workflow: {workflow[\"name\"]}', file=sys.stderr)",
            "    print(f'Steps: {len(workflow[\"steps\"])}', file=sys.stderr)",
            "    # TODO: Implement workflow execution",
            "",
            "if __name__ == '__main__':",
            "    main()",
        ]
        main_script.write_text("\n".join(main_lines))

        return {
            "workflow_id": workflow_id,
            "output_path": str(base_dir),
            "script_type": "tools",
            "main_script": str(main_script),
            "workflow_file": str(workflow_file)
        }

    def _get_tool_definition(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get tool definition from tools manager or YAML files."""
        if self.tools_manager:
            # Try to get from tools manager
            try:
                tool = self.tools_manager.get_tool(tool_id)
                if tool:
                    return tool
            except Exception:
                pass

        # Try to load from YAML files
        tool_dirs = [
            Path("code_evolver/tools/llm"),
            Path("code_evolver/tools/executable"),
            Path("code_evolver/tools/custom"),
        ]

        for tool_dir in tool_dirs:
            if not tool_dir.exists():
                continue

            tool_file = tool_dir / f"{tool_id}.yaml"
            if tool_file.exists():
                with open(tool_file, 'r') as f:
                    return yaml.safe_load(f)

        return None

    def _get_workflow_definition(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow definition from JSON files."""
        workflows_dir = Path("code_evolver/workflows")

        if not workflows_dir.exists():
            return None

        workflow_file = workflows_dir / f"{workflow_id}.json"
        if workflow_file.exists():
            with open(workflow_file, 'r') as f:
                return json.load(f)

        return None
