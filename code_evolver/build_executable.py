#!/usr/bin/env python3
"""
mostlylucid DiSE - Tree-Shaking Build Script

Builds minimal, self-contained executable with only required tools.

Features:
- Tree shaking: Includes only referenced tools
- Tool inlining: All tools in single file with ID comments
- Multi-platform support: Windows, Mac, Linux
- Minimal size: Only necessary code
- Config generation: Minimal settings + comprehensive docs

USAGE:
    python build_executable.py                    # Build for current platform
    python build_executable.py --platform windows # Build for specific platform
    python build_executable.py --all              # Build for all platforms
    python build_executable.py --analyze          # Show what would be included

REQUIREMENTS:
    pip install pyinstaller

OUTPUT:
    dist/code_evolver.exe       (Windows)
    dist/code_evolver           (Linux/Mac)
    dist/config.yaml            (Minimal config with docs)
"""

import os
import sys
import ast
import json
import yaml
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Set, Dict, List, Any, Optional
from collections import defaultdict


class ToolDependencyAnalyzer:
    """
    Analyzes tool dependencies to determine which tools to include.

    Performs static analysis of workflow definitions to find all
    referenced tools recursively.
    """

    def __init__(self, tools_dir: Path = Path("tools")):
        """
        Initialize analyzer.

        Args:
            tools_dir: Directory containing tool definitions
        """
        self.tools_dir = tools_dir
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)

    def load_all_tools(self):
        """Load all tool definitions from YAML files."""
        print("[1/7] Loading tool definitions...")

        for yaml_file in self.tools_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    tool_def = yaml.safe_load(f)

                if tool_def and "name" in tool_def:
                    tool_id = tool_def.get("name", "").replace(" ", "_").lower()
                    self.tools[tool_id] = {
                        "definition": tool_def,
                        "path": yaml_file,
                        "type": tool_def.get("type", "unknown")
                    }

            except Exception as e:
                print(f"  Warning: Failed to load {yaml_file}: {e}")

        print(f"  Loaded {len(self.tools)} tools")

    def analyze_dependencies(self):
        """Analyze dependencies for all tools."""
        print("[2/7] Analyzing dependencies...")

        for tool_id, tool_info in self.tools.items():
            tool_def = tool_info["definition"]

            # Check workflow steps
            workflow = tool_def.get("workflow", {})
            steps = workflow.get("steps", [])

            for step in steps:
                if isinstance(step, dict) and "tool" in step:
                    dep_tool = step["tool"]
                    self.dependencies[tool_id].add(dep_tool)

            # Check metadata dependencies
            metadata = tool_def.get("metadata", {})
            deps = metadata.get("dependencies", [])
            self.dependencies[tool_id].update(deps)

        total_deps = sum(len(deps) for deps in self.dependencies.values())
        print(f"  Found {total_deps} total dependencies")

    def get_required_tools(self, entry_points: List[str]) -> Set[str]:
        """
        Get all tools required by entry points (recursive).

        Args:
            entry_points: Starting tools (e.g., ["content_summarizer"])

        Returns:
            Set of all required tool IDs
        """
        required = set()
        queue = list(entry_points)

        while queue:
            tool_id = queue.pop(0)

            if tool_id in required:
                continue

            required.add(tool_id)

            # Add dependencies
            for dep in self.dependencies.get(tool_id, []):
                if dep not in required:
                    queue.append(dep)

        return required


class ToolInliner:
    """
    Inlines all tools into a single Python file.

    Creates a standalone module with all tool code and definitions.
    """

    def __init__(self, tools: Dict[str, Dict[str, Any]], required_tools: Set[str]):
        """
        Initialize inliner.

        Args:
            tools: All available tools
            required_tools: Tools to include
        """
        self.tools = tools
        self.required_tools = required_tools

    def inline_tools(self, output_path: Path):
        """
        Inline all required tools into single file.

        Args:
            output_path: Path to write inlined tools
        """
        print("[3/7] Inlining tools into single file...")

        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write('#!/usr/bin/env python3\n')
            f.write('"""\n')
            f.write('mostlylucid DiSE - Inlined Tools\n')
            f.write('\n')
            f.write('All tool definitions and code in single file.\n')
            f.write('Generated by tree-shaking build process.\n')
            f.write('"""\n\n')

            f.write('import json\n')
            f.write('import sys\n')
            f.write('from typing import Dict, Any\n\n')

            # Write tool definitions as JSON
            f.write('# Tool Definitions\n')
            f.write('TOOL_DEFINITIONS = {\n')

            for tool_id in sorted(self.required_tools):
                if tool_id not in self.tools:
                    continue

                tool_info = self.tools[tool_id]
                tool_def = tool_info["definition"]

                f.write(f'    # TOOL_ID: {tool_id}\n')
                f.write(f'    "{tool_id}": {json.dumps(tool_def, indent=8)},\n\n')

            f.write('}\n\n')

            # Write tool code for executable tools
            f.write('# Tool Implementations\n\n')

            for tool_id in sorted(self.required_tools):
                if tool_id not in self.tools:
                    continue

                tool_info = self.tools[tool_id]

                if tool_info["type"] == "executable":
                    # Find corresponding .py file
                    yaml_path = tool_info["path"]
                    py_path = yaml_path.with_suffix('.py')

                    if py_path.exists():
                        f.write(f'# ===== TOOL: {tool_id} =====\n')

                        with open(py_path, 'r', encoding='utf-8') as py_file:
                            code = py_file.read()
                            # Remove shebang
                            if code.startswith('#!'):
                                code = '\n'.join(code.split('\n')[1:])
                            f.write(code)

                        f.write(f'\n# ===== END TOOL: {tool_id} =====\n\n')

            # Write tool registry
            f.write('# Tool Registry\n')
            f.write('def get_tool_definition(tool_id: str) -> Dict[str, Any]:\n')
            f.write('    """Get tool definition by ID."""\n')
            f.write('    return TOOL_DEFINITIONS.get(tool_id)\n\n')

            f.write('def list_tools() -> list:\n')
            f.write('    """List all available tools."""\n')
            f.write('    return list(TOOL_DEFINITIONS.keys())\n')

        print(f"  Inlined {len(self.required_tools)} tools to {output_path}")


class ConfigGenerator:
    """
    Generates minimal config with comprehensive documentation.
    """

    def __init__(self, llm_client=None):
        """
        Initialize config generator.

        Args:
            llm_client: Optional LLM client for doc generation
        """
        self.llm_client = llm_client

    def generate_config(self, output_path: Path, tools_included: Set[str]):
        """
        Generate config.yaml with minimal settings and docs.

        Args:
            output_path: Where to write config
            tools_included: Tools included in build
        """
        print("[4/7] Generating configuration file...")

        config = {
            # === ACTIVE CONFIGURATION (edit these) ===
            "llm": {
                "backend": "ollama",
                "model_roles": {
                    "fast": "gemma2:2b",
                    "base": "codellama:7b",
                    "powerful": "qwen2.5-coder:14b",
                    "embedding": "nomic-embed-text"
                },
                "backends": {
                    "ollama": {
                        "base_url": "http://localhost:11434",
                        "enabled": True
                    }
                }
            },

            "tools": {
                "enabled": list(sorted(tools_included)),
                "auto_load": True
            },

            "rag": {
                "enabled": True,
                "backend": "numpy"  # or "qdrant"
            },

            "chat": {
                "prompt": "DiSE> ",
                "show_workflow": True
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            # Write active config at top
            f.write('# mostlylucid DiSE Configuration\n')
            f.write('# Generated by tree-shaking build\n')
            f.write('#\n')
            f.write('# ACTIVE CONFIGURATION - Edit these values\n')
            f.write('#\n\n')

            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            # Write comprehensive documentation at end
            f.write('\n\n')
            f.write('# ' + '='*70 + '\n')
            f.write('# CONFIGURATION DOCUMENTATION\n')
            f.write('# ' + '='*70 + '\n\n')

            docs = self._generate_config_docs(config, tools_included)
            f.write(docs)

        print(f"  Generated config: {output_path}")

    def _generate_config_docs(self, config: Dict[str, Any], tools: Set[str]) -> str:
        """
        Generate configuration documentation.

        Args:
            config: Current configuration
            tools: Tools included

        Returns:
            Documentation string
        """
        if self.llm_client:
            # Use LLM to generate accurate docs
            return self._llm_generate_docs(config, tools)
        else:
            # Fallback to template docs
            return self._template_docs(config, tools)

    def _template_docs(self, config: Dict[str, Any], tools: Set[str]) -> str:
        """Generate template documentation."""
        return f'''
# LLM Configuration
# -----------------
# backend: Which LLM backend to use (ollama, anthropic, openai)
# model_roles: Abstract roles that map to specific models
#   - fast: Quick tasks (triage, simple validation)
#   - base: Default for most tasks
#   - powerful: Complex reasoning and code generation
#   - embedding: Vector embeddings for RAG

# Tools Configuration
# -------------------
# enabled: List of tools included in this build ({len(tools)} tools)
# auto_load: Automatically load tools on startup

# RAG Configuration
# -----------------
# enabled: Enable RAG memory system (required)
# backend: Storage backend (numpy for local, qdrant for production)

# Chat Configuration
# ------------------
# prompt: Command prompt string
# show_workflow: Show workflow steps during execution

# Tool List ({len(tools)} tools included)
# {''.join(f'#   - {tool}\n' for tool in sorted(tools))}
'''


class ExecutableBuilder:
    """
    Builds standalone executable using PyInstaller.
    """

    def __init__(self, platform: str):
        """
        Initialize builder.

        Args:
            platform: Target platform (windows, linux, macos)
        """
        self.platform = platform

    def build(self, inlined_tools_path: Path, output_dir: Path):
        """
        Build executable.

        Args:
            inlined_tools_path: Path to inlined tools file
            output_dir: Output directory for build
        """
        print(f"[5/7] Building executable for {self.platform}...")

        # Create main entry point
        main_script = output_dir / "main.py"
        self._create_main_script(main_script, inlined_tools_path)

        # PyInstaller command
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",  # Single file
            "--clean",  # Clean cache
            "--name",
            "code_evolver",
            "--add-data",
            f"{inlined_tools_path}{os.pathsep}.",
        ]

        # Platform-specific options
        if self.platform == "windows":
            cmd.append("--console")
        else:
            cmd.append("--console")

        # Add main script
        cmd.append(str(main_script))

        # Run PyInstaller
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"  Build successful!")
                print(f"  Output: dist/code_evolver{'.exe' if self.platform == 'windows' else ''}")
            else:
                print(f"  Build failed:")
                print(result.stderr)

        except Exception as e:
            print(f"  Error building executable: {e}")

    def _create_main_script(self, output_path: Path, inlined_tools_path: Path):
        """Create main entry point script."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('''#!/usr/bin/env python3
"""
mostlylucid DiSE - Main Entry Point
"""

import sys
from pathlib import Path

# Add inlined tools to path
sys.path.insert(0, str(Path(__file__).parent))

# Import chat CLI
from chat_cli import main

if __name__ == "__main__":
    main()
''')


def main():
    """Main build process."""
    parser = argparse.ArgumentParser(description="Build mostlylucid DiSE executable")
    parser.add_argument(
        "--platform",
        choices=["windows", "linux", "macos"],
        default=sys.platform.replace("darwin", "macos").replace("win32", "windows"),
        help="Target platform"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build for all platforms"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze dependencies without building"
    )
    parser.add_argument(
        "--entry-points",
        nargs="+",
        default=["content_summarizer"],
        help="Entry point tools to include"
    )

    args = parser.parse_args()

    # Initialize
    analyzer = ToolDependencyAnalyzer()
    analyzer.load_all_tools()
    analyzer.analyze_dependencies()

    # Get required tools
    required_tools = analyzer.get_required_tools(args.entry_points)
    print(f"\n[Dependency Analysis]")
    print(f"  Entry points: {', '.join(args.entry_points)}")
    print(f"  Required tools: {len(required_tools)}")
    print(f"  Total tools available: {len(analyzer.tools)}")
    print(f"  Reduction: {(1 - len(required_tools)/len(analyzer.tools))*100:.1f}%")

    if args.analyze:
        print(f"\n[Tools to Include]")
        for tool in sorted(required_tools):
            print(f"  - {tool}")
        return

    # Create build directory
    build_dir = Path("build_output")
    build_dir.mkdir(exist_ok=True)

    # Inline tools
    inlined_tools_path = build_dir / "inlined_tools.py"
    inliner = ToolInliner(analyzer.tools, required_tools)
    inliner.inline_tools(inlined_tools_path)

    # Generate config
    config_path = build_dir / "config.yaml"
    config_gen = ConfigGenerator()
    config_gen.generate_config(config_path, required_tools)

    # Build executable
    if args.all:
        platforms = ["windows", "linux", "macos"]
    else:
        platforms = [args.platform]

    for platform in platforms:
        builder = ExecutableBuilder(platform)
        builder.build(inlined_tools_path, build_dir)

    print("\n[6/7] Copying config to dist...")
    dist_config = Path("dist") / "config.yaml"
    shutil.copy(config_path, dist_config)
    print(f"  Copied config to {dist_config}")

    print("\n[7/7] Build complete!")
    print(f"\n[Output Files]")
    print(f"  Executable: dist/code_evolver{'.exe' if args.platform == 'windows' else ''}")
    print(f"  Config: dist/config.yaml")
    print(f"\n[Usage]")
    print(f"  cd dist")
    print(f"  ./code_evolver{'exe' if args.platform == 'windows' else ''}")


if __name__ == "__main__":
    main()
