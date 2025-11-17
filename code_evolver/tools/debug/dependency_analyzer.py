#!/usr/bin/env python3
"""
Dependency Analyzer Tool
Analyzes tool dependencies using RAG and metadata for tree shaking
"""
import json
import sys
import os
import re
import ast
from typing import Dict, Any, Set, List
from pathlib import Path


class DependencyAnalyzer:
    """Analyzes dependencies for tools and workflows"""

    def __init__(self, tools_root: str):
        self.tools_root = Path(tools_root)
        self.analyzed = set()  # Prevent circular dependencies

    def analyze_tool(self, tool_id: str) -> Dict[str, Any]:
        """
        Analyze a tool and all its dependencies

        Returns:
            Dictionary with:
            - tools: Set of required tool IDs
            - tool_files: Set of tool YAML file paths
            - python_files: Set of Python script paths
            - python_packages: Set of required Python packages
            - core_modules: Set of required core modules
            - llm_providers: Set of LLM providers needed
        """
        dependencies = {
            'tools': set(),
            'tool_files': set(),
            'python_files': set(),
            'python_packages': set(['pyyaml']),  # Always needed for config
            'core_modules': set(['tools_manager', 'llm_client_factory', 'registry']),
            'llm_providers': set(),
            'config_files': set(['config.yaml'])
        }

        # Prevent circular dependencies
        if tool_id in self.analyzed:
            return dependencies

        self.analyzed.add(tool_id)

        # Find tool definition file
        tool_file = self.find_tool_file(tool_id)
        if not tool_file:
            return dependencies

        # Add tool file
        dependencies['tool_files'].add(str(tool_file.relative_to(self.tools_root.parent)))
        dependencies['tools'].add(tool_id)

        # Load and analyze tool
        try:
            import yaml
            with open(tool_file, 'r') as f:
                tool_def = yaml.safe_load(f)

            tool_type = tool_def.get('type', '').lower()

            if tool_type == 'executable':
                self._analyze_executable(tool_def, dependencies)
            elif tool_type == 'llm':
                self._analyze_llm(tool_def, dependencies)
            elif tool_type == 'workflow':
                self._analyze_workflow(tool_def, dependencies)
            elif tool_type == 'openapi':
                self._analyze_openapi(tool_def, dependencies)

        except Exception as e:
            print(f"Warning: Error analyzing {tool_id}: {e}", file=sys.stderr)

        return dependencies

    def _analyze_executable(self, tool_def: Dict, dependencies: Dict):
        """Analyze executable tool dependencies"""
        executable = tool_def.get('executable', {})

        # Get script path
        if 'command' in executable:
            args = executable.get('args', [])
            for arg in args:
                # Check for Python scripts referenced
                if arg.endswith('.py'):
                    # Handle different path formats
                    if '{tool_dir}' in arg:
                        # Replace {tool_dir} with actual tools path
                        if self.tools_root.endswith('tools'):
                            script_path = arg.replace('{tool_dir}/', f"{self.tools_root}/executable/")
                        else:
                            script_path = arg.replace('{tool_dir}/', 'tools/executable/')
                    elif arg.startswith('tools/'):
                        # Already has tools/ prefix, use as-is if it exists,
                        # otherwise try with code_evolver/ prefix
                        if os.path.exists(arg):
                            script_path = arg
                        else:
                            script_path = f"code_evolver/{arg}"
                    else:
                        script_path = arg

                    if os.path.exists(script_path):
                        dependencies['python_files'].add(script_path)

                        # Analyze Python script imports
                        self._analyze_python_imports(script_path, dependencies)

    def _analyze_llm(self, tool_def: Dict, dependencies: Dict):
        """Analyze LLM tool dependencies"""
        llm_config = tool_def.get('llm', {})
        tier = llm_config.get('tier', 'coding.tier_2')

        # Determine provider from tier or direct config
        # This would need to be mapped from your config.yaml
        # For now, we'll include all LLM clients or make it configurable
        dependencies['core_modules'].add('llm_client_ollama')
        dependencies['llm_providers'].add('ollama')

        # Add common LLM packages
        dependencies['python_packages'].update(['requests', 'httpx'])

    def _analyze_workflow(self, tool_def: Dict, dependencies: Dict):
        """Analyze workflow dependencies"""
        steps = tool_def.get('steps', [])

        for step in steps:
            step_tool = step.get('tool')
            if step_tool:
                # Recursively analyze step tool
                sub_deps = self.analyze_tool(step_tool)

                # Merge dependencies
                for key in ['tools', 'tool_files', 'python_files', 'python_packages', 'core_modules', 'llm_providers']:
                    if key in sub_deps:
                        dependencies[key].update(sub_deps[key])

        # Add workflow support
        dependencies['core_modules'].add('workflow_manager')

    def _analyze_openapi(self, tool_def: Dict, dependencies: Dict):
        """Analyze OpenAPI tool dependencies"""
        dependencies['python_packages'].update(['requests', 'openapi-core'])
        dependencies['core_modules'].add('openapi_tool')

    def _analyze_python_imports(self, script_path: str, dependencies: Dict):
        """Analyze Python script for import statements"""
        try:
            with open(script_path, 'r') as f:
                content = f.read()

            # Parse AST to find imports
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        pkg = alias.name.split('.')[0]
                        if not self._is_stdlib(pkg):
                            dependencies['python_packages'].add(pkg)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        pkg = node.module.split('.')[0]
                        if not self._is_stdlib(pkg):
                            dependencies['python_packages'].add(pkg)

        except Exception as e:
            print(f"Warning: Could not parse {script_path}: {e}", file=sys.stderr)

    def _is_stdlib(self, module_name: str) -> bool:
        """Check if module is part of Python standard library"""
        stdlib_modules = {
            'os', 'sys', 're', 'json', 'ast', 'typing', 'pathlib',
            'subprocess', 'argparse', 'logging', 'datetime', 'time',
            'collections', 'itertools', 'functools', 'hashlib',
            'urllib', 'http', 'email', 'xml', 'csv', 'io', 'tempfile'
        }
        return module_name in stdlib_modules

    def find_tool_file(self, tool_id: str) -> Path:
        """Find tool YAML file by ID"""
        # Search in tools/ directory
        for tool_type in ['llm', 'executable', 'openapi', 'workflow']:
            yaml_path = self.tools_root / tool_type / f"{tool_id}.yaml"
            if yaml_path.exists():
                return yaml_path

        # Search in workflows/
        workflow_path = self.tools_root.parent / 'workflows' / f"{tool_id}.json"
        if workflow_path.exists():
            return workflow_path

        return None

    def generate_requirements_txt(self, dependencies: Dict) -> str:
        """Generate requirements.txt from dependencies"""
        packages = sorted(dependencies['python_packages'])

        # Map import names to package names
        package_mappings = {
            'yaml': 'pyyaml',
            'PIL': 'pillow',
            'cv2': 'opencv-python',
            'sklearn': 'scikit-learn',
            'flask_cors': 'flask-cors',
            'bs4': 'beautifulsoup4',
        }

        requirements = []
        for pkg in packages:
            # Map to correct package name
            pkg_name = package_mappings.get(pkg, pkg)
            requirements.append(pkg_name)

        return '\n'.join(requirements) + '\n'

    def generate_file_list(self, dependencies: Dict) -> List[str]:
        """Generate list of files to copy"""
        files = []

        # Core modules
        for module in dependencies['core_modules']:
            files.append(f"code_evolver/src/{module}.py")

        # Tool files
        files.extend(dependencies['tool_files'])

        # Python scripts
        files.extend(dependencies['python_files'])

        # Config files
        files.extend([f"code_evolver/{f}" for f in dependencies['config_files']])

        # Always include essential files
        files.extend([
            'code_evolver/__init__.py',
            'code_evolver/src/__init__.py',
        ])

        return sorted(set(files))


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
        tool_id = config.get('tool_id')

        # Auto-detect tools_root based on current directory
        default_tools_root = 'tools' if os.path.exists('tools') else 'code_evolver/tools'
        tools_root = config.get('tools_root', default_tools_root)
        include_rag = config.get('include_rag', False)

        if not tool_id:
            print(json.dumps({
                'error': 'tool_id is required'
            }))
            sys.exit(1)

        # Analyze dependencies
        analyzer = DependencyAnalyzer(tools_root)
        dependencies = analyzer.analyze_tool(tool_id)

        # Convert sets to lists for JSON serialization
        deps_serializable = {
            'tools': sorted(dependencies['tools']),
            'tool_files': sorted(dependencies['tool_files']),
            'python_files': sorted(dependencies['python_files']),
            'python_packages': sorted(dependencies['python_packages']),
            'core_modules': sorted(dependencies['core_modules']),
            'llm_providers': sorted(dependencies['llm_providers']),
            'config_files': sorted(dependencies['config_files'])
        }

        # Generate artifacts
        requirements_txt = analyzer.generate_requirements_txt(dependencies)
        file_list = analyzer.generate_file_list(dependencies)

        # Calculate stats
        stats = {
            'total_tools': len(deps_serializable['tools']),
            'total_files': len(file_list),
            'total_packages': len(deps_serializable['python_packages']),
            'estimated_size_kb': len(file_list) * 10  # Rough estimate
        }

        # Output result
        print(json.dumps({
            'success': True,
            'tool_id': tool_id,
            'dependencies': deps_serializable,
            'requirements_txt': requirements_txt,
            'file_list': file_list,
            'stats': stats
        }))

    except Exception as e:
        print(json.dumps({
            'error': f'Error analyzing dependencies: {e}'
        }))
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
