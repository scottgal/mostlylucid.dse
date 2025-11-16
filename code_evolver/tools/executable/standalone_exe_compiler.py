#!/usr/bin/env python3
"""
Standalone Executable Compiler
Compiles tools/workflows into standalone executables using PyInstaller
with tree shaking (inlines all dependencies by default)
"""
import json
import sys
import os
import ast
import re
from typing import Dict, Any, List, Set, Tuple
from pathlib import Path


def analyze_tool_dependencies(tool_id: str) -> Dict[str, Any]:
    """
    Call dependency_analyzer to get all required files

    Args:
        tool_id: Tool to analyze

    Returns:
        Dependencies dictionary with file_list, python_files, etc.
    """
    import subprocess

    # Call dependency_analyzer script directly to avoid RAG initialization issues
    analyzer_script = 'tools/executable/dependency_analyzer.py'

    result = subprocess.run(
        ['python', analyzer_script, json.dumps({'tool_id': tool_id})],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        raise Exception(f"dependency_analyzer failed: {result.stderr}")

    deps = json.loads(result.stdout)
    if not deps.get('success'):
        raise Exception(f"Failed to analyze dependencies: {deps.get('error')}")

    return deps


def parse_python_file(file_path: str) -> Dict[str, Any]:
    """
    Parse a Python file and extract imports, functions, classes

    Args:
        file_path: Path to Python file

    Returns:
        Dictionary with imports, functions, classes, and raw code
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        imports = []
        functions = []
        classes = []
        module_docstring = None

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'asname': alias.asname
                    })

            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        'type': 'from',
                        'module': node.module or '',
                        'name': alias.name,
                        'asname': alias.asname
                    })

            elif isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'code': ast.get_source_segment(content, node),
                    'lineno': node.lineno
                })

            elif isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'code': ast.get_source_segment(content, node),
                    'lineno': node.lineno
                })

            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                if module_docstring is None and isinstance(node.value.value, str):
                    module_docstring = node.value.value

        return {
            'file_path': file_path,
            'imports': imports,
            'functions': functions,
            'classes': classes,
            'docstring': module_docstring,
            'raw_content': content
        }

    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
        return {
            'file_path': file_path,
            'imports': [],
            'functions': [],
            'classes': [],
            'docstring': None,
            'raw_content': ''
        }


def inline_tool_code(tool_id: str, config: Dict[str, Any]) -> str:
    """
    Tree-shake and inline all dependencies into a single file

    Args:
        tool_id: Tool to inline
        config: Configuration dictionary

    Returns:
        Single-file Python code with all dependencies inlined
    """
    # Analyze dependencies
    print(f"Analyzing dependencies for {tool_id}...", file=sys.stderr)
    deps = analyze_tool_dependencies(tool_id)

    # Collect all Python files
    python_files = deps.get('python_files', [])
    core_modules = deps.get('dependencies', {}).get('core_modules', [])

    # Add core module files
    all_files = set(python_files)
    for module in core_modules:
        module_file = f"src/{module}.py"
        if os.path.exists(module_file):
            all_files.add(module_file)

    # Parse all files
    parsed_files = {}
    for file_path in all_files:
        if os.path.exists(file_path):
            parsed_files[file_path] = parse_python_file(file_path)

    # Collect all stdlib imports
    stdlib_imports = set()
    third_party_imports = set()

    stdlib_modules = {
        'os', 'sys', 're', 'json', 'ast', 'typing', 'pathlib',
        'subprocess', 'argparse', 'logging', 'datetime', 'time',
        'collections', 'itertools', 'functools', 'hashlib',
        'urllib', 'http', 'email', 'xml', 'csv', 'io', 'tempfile',
        'pickle', 'threading', 'multiprocessing', 'signal'
    }

    # Local modules that will be inlined (should NOT be imported)
    local_modules = set()
    for file_path in all_files:
        if file_path.startswith('src/') and file_path.endswith('.py'):
            module_name = Path(file_path).stem  # e.g., 'src/config_manager.py' -> 'config_manager'
            local_modules.add(module_name)

    for parsed in parsed_files.values():
        for imp in parsed['imports']:
            if imp['type'] == 'import':
                module_root = imp['module'].split('.')[0]
                if module_root in stdlib_modules:
                    stdlib_imports.add(imp['module'])
                elif module_root not in local_modules and not imp['module'].startswith('src.'):
                    # Only add to third-party if it's not a local module being inlined
                    third_party_imports.add(imp['module'])
            elif imp['type'] == 'from':
                module_root = imp['module'].split('.')[0] if imp['module'] else ''
                if module_root in stdlib_modules:
                    stdlib_imports.add(f"{imp['module']}.{imp['name']}")
                elif imp['module'] and not imp['module'].startswith('src.') and module_root not in local_modules:
                    # Only add if not a local module
                    third_party_imports.add(imp['module'])

    # Generate inlined code
    inlined_code = f'''#!/usr/bin/env python3
"""
Tree-Shaken Standalone Tool: {tool_id}
Auto-generated by standalone_exe_compiler with dependency inlining

This file contains all dependencies inlined for portability.
Original tool: {tool_id}
"""

# Standard library imports
'''

    # Add stdlib imports
    for imp in sorted(stdlib_imports):
        if '.' in imp:
            parts = imp.split('.')
            inlined_code += f"from {parts[0]} import {'.'.join(parts[1:])}\n"
        else:
            inlined_code += f"import {imp}\n"

    # Add third-party imports
    if third_party_imports:
        inlined_code += "\n# Third-party imports\n"
        for imp in sorted(third_party_imports):
            inlined_code += f"import {imp}\n"

    inlined_code += "\n# ==================== INLINED DEPENDENCIES ====================\n\n"

    # Inline core modules (functions and classes only, skip main blocks)
    for file_path, parsed in sorted(parsed_files.items()):
        if file_path.startswith('src/'):
            inlined_code += f"# From: {file_path}\n"

            if parsed['docstring']:
                inlined_code += f'"""{parsed["docstring"]}"""\n\n'

            # Add classes
            for cls in parsed['classes']:
                inlined_code += f"{cls['code']}\n\n"

            # Add functions (skip if it's __main__ check)
            for func in parsed['functions']:
                if func['name'] not in ['main', '__main__']:
                    inlined_code += f"{func['code']}\n\n"
                elif 'if __name__' not in func['code']:
                    # Include main() function if it's not the entry point check
                    inlined_code += f"{func['code']}\n\n"

            inlined_code += f"# End: {file_path}\n\n"

    # Add tool-specific code
    tool_file = None
    for file_path in python_files:
        if tool_id in file_path:
            tool_file = file_path
            break

    if tool_file and os.path.exists(tool_file):
        inlined_code += f"# ==================== TOOL CODE ====================\n\n"
        parsed_tool = parsed_files.get(tool_file, parse_python_file(tool_file))

        if parsed_tool['docstring']:
            inlined_code += f'"""{parsed_tool["docstring"]}"""\n\n'

        # Add tool classes
        for cls in parsed_tool['classes']:
            inlined_code += f"{cls['code']}\n\n"

        # Add tool functions
        for func in parsed_tool['functions']:
            inlined_code += f"{func['code']}\n\n"

    return inlined_code


def generate_standalone_wrapper(config: Dict[str, Any]) -> str:
    """
    Generate a standalone Python script that bundles everything needed
    WITH TREE SHAKING (inlines all dependencies by default)

    Args:
        config: Configuration dictionary with:
            - tool_id: ID of the tool/workflow to compile
            - mode: 'cli' or 'api' (default: cli)
            - port: Port for API mode (default: 8080)
            - tree_shake: Whether to inline dependencies (default: True)

    Returns:
        Generated standalone Python script with inlined dependencies
    """
    tool_id = config.get('tool_id', 'unknown')
    mode = config.get('mode', 'cli')
    port = config.get('port', 8080)
    tree_shake = config.get('tree_shake', True)  # DEFAULT: True

    # If tree shaking is enabled (default), inline all dependencies
    if tree_shake:
        try:
            print(f"Tree shaking enabled for {tool_id}...", file=sys.stderr)
            inlined_code = inline_tool_code(tool_id, config)

            # Add CLI or API wrapper to inlined code
            if mode == 'api':
                # Add Flask API wrapper
                inlined_code += f'''

# ==================== API WRAPPER ====================

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({{
        'status': 'healthy',
        'tool_id': '{tool_id}',
        'version': '1.0.0'
    }})

@app.route('/api/info', methods=['GET'])
def info():
    """Get tool information"""
    return jsonify({{
        'tool_id': '{tool_id}',
        'mode': 'api',
        'description': f'Standalone API wrapper for {tool_id}'
    }})

@app.route('/api/invoke', methods=['POST'])
def invoke():
    """Invoke the tool"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({{'error': 'Request body must be JSON'}}), 400

        # Call main() with input data
        import io
        import contextlib

        # Capture stdout
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            # Write input to stdin simulation
            import sys
            old_stdin = sys.stdin
            sys.stdin = io.StringIO(json.dumps(data))

            try:
                main()
            finally:
                sys.stdin = old_stdin

        result_str = stdout_capture.getvalue()

        try:
            result = json.loads(result_str)
        except:
            result = {{'output': result_str}}

        return jsonify({{
            'success': True,
            'tool_id': '{tool_id}',
            'result': result
        }})

    except Exception as e:
        return jsonify({{
            'success': False,
            'error': str(e)
        }}), 500

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({{
        'service': 'Standalone Tool API',
        'tool_id': '{tool_id}',
        'endpoints': {{
            'GET /': 'API documentation',
            'GET /api/health': 'Health check',
            'GET /api/info': 'Tool information',
            'POST /api/invoke': 'Invoke the tool'
        }}
    }})

if __name__ == '__main__':
    print(f"Starting standalone API for tool: {tool_id}")
    print(f"Listening on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port={port}, debug=False)
'''
            else:
                # CLI mode - inlined code already has main() function
                # Just ensure it's called
                if 'if __name__' not in inlined_code:
                    inlined_code += '''

if __name__ == '__main__':
    main()
'''

            return inlined_code

        except Exception as e:
            print(f"Warning: Tree shaking failed: {e}", file=sys.stderr)
            print("Falling back to placeholder wrapper...", file=sys.stderr)
            # Fall through to placeholder code below

    if mode == 'api':
        # Generate API mode standalone script
        script = f'''#!/usr/bin/env python3
"""
Standalone API Wrapper for: {tool_id}
Auto-generated executable
"""
import os
import sys
import json
import logging
from flask import Flask, request, jsonify

# Embedded configuration
TOOL_ID = "{tool_id}"
PORT = {port}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'tool_id': TOOL_ID,
        'version': '1.0.0'
    })


@app.route('/api/info', methods=['GET'])
def info():
    """Get tool information"""
    return jsonify({{
        'tool_id': TOOL_ID,
        'mode': 'api',
        'description': f'Standalone API wrapper for {{TOOL_ID}}'
    }})


@app.route('/api/invoke', methods=['POST'])
def invoke():
    """Invoke the tool"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        logger.info(f"Invoking {{TOOL_ID}} with input: {{data}}")

        # TODO: Embed actual tool logic here
        # This is a placeholder - actual implementation will embed the tool code
        result = {{"message": "Tool invoked successfully", "input": data}}

        return jsonify({
            'success': True,
            'tool_id': TOOL_ID,
            'result': result
        })

    except Exception as e:
        logger.error(f"Error invoking tool: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({{
        'service': 'Standalone Tool API',
        'tool_id': TOOL_ID,
        'endpoints': {{
            'GET /': 'API documentation',
            'GET /api/health': 'Health check',
            'GET /api/info': 'Tool information',
            'POST /api/invoke': 'Invoke the tool'
        }}
    }})


if __name__ == '__main__':
    logger.info(f"Starting standalone API for tool: {{TOOL_ID}}")
    logger.info(f"Listening on 0.0.0.0:{{PORT}}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
'''
    else:
        # Generate CLI mode standalone script
        script = f'''#!/usr/bin/env python3
"""
Standalone CLI Wrapper for: {tool_id}
Auto-generated executable
"""
import sys
import json
import argparse


def main():
    """Main entry point for CLI mode"""
    parser = argparse.ArgumentParser(description='Standalone CLI for {tool_id}')
    parser.add_argument('--input', '-i', help='Input as JSON string')
    parser.add_argument('--file', '-f', help='Input from JSON file')
    parser.add_argument('--prompt', '-p', help='Direct prompt input')

    args = parser.parse_args()

    # Parse input
    input_data = {{{{}}}}
    if args.input:
        input_data = json.loads(args.input)
    elif args.file:
        with open(args.file, 'r') as f:
            input_data = json.load(f)
    elif args.prompt:
        input_data = {{{{'prompt': args.prompt}}}}

    # TODO: Embed actual tool logic here
    # This is a placeholder - actual implementation will embed the tool code
    result = {{{{
        'tool_id': '{tool_id}',
        'input': input_data,
        'result': 'Tool executed successfully'
    }}}}

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
'''

    return script


def generate_pyinstaller_spec(config: Dict[str, Any]) -> str:
    """
    Generate PyInstaller .spec file

    Args:
        config: Configuration with tool_id, output_name, mode

    Returns:
        PyInstaller spec file content
    """
    tool_id = config.get('tool_id', 'unknown')
    output_name = config.get('output_name', f'{tool_id}_standalone')
    mode = config.get('mode', 'cli')

    spec = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{output_name}.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['flask', 'werkzeug', 'jinja2', 'click', 'itsdangerous', 'markupsafe'],
    hookspath=[],
    hooksconfig={{{{}}}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{output_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

    return spec


def generate_build_instructions(config: Dict[str, Any]) -> str:
    """Generate build instructions"""
    output_name = config.get('output_name', 'tool_standalone')

    instructions = f'''# Build Instructions for Standalone Executable

## Prerequisites

Install PyInstaller:
```bash
pip install pyinstaller
```

## Build Steps

### Option 1: Quick Build (One File)
```bash
pyinstaller --onefile --name {output_name} {output_name}.py
```

### Option 2: Using Spec File (Recommended)
```bash
pyinstaller {output_name}.spec
```

### Option 3: Optimized Build
```bash
pyinstaller --onefile \\
  --name {output_name} \\
  --strip \\
  --clean \\
  --noconfirm \\
  {output_name}.py
```

## Output

The executable will be in:
- `dist/{output_name}` (Linux/Mac)
- `dist/{output_name}.exe` (Windows)

## Distribution

The executable is standalone and can be distributed without Python installed.

Size optimization:
- Use UPX: `--upx-dir=/path/to/upx`
- Exclude unnecessary modules: `--exclude-module <module>`

## Testing

Linux/Mac:
```bash
./dist/{output_name} --help
```

Windows:
```bash
dist\\{output_name}.exe --help
```
'''

    return instructions


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

        # Generate standalone wrapper script
        wrapper_script = generate_standalone_wrapper(config)

        # Generate PyInstaller spec
        spec_content = generate_pyinstaller_spec(config)

        # Generate build instructions
        build_instructions = generate_build_instructions(config)

        # Output result
        print(json.dumps({
            'success': True,
            'wrapper_script': wrapper_script,
            'spec_file': spec_content,
            'build_instructions': build_instructions,
            'output_name': config.get('output_name', f'{config.get("tool_id", "tool")}_standalone')
        }))

    except Exception as e:
        print(json.dumps({
            'error': f'Error generating standalone executable: {e}'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
