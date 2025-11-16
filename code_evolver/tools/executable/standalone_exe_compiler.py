#!/usr/bin/env python3
"""
Standalone Executable Compiler
Compiles tools/workflows into standalone executables using PyInstaller
"""
import json
import sys
import os
from typing import Dict, Any


def generate_standalone_wrapper(config: Dict[str, Any]) -> str:
    """
    Generate a standalone Python script that bundles everything needed

    Args:
        config: Configuration dictionary with:
            - tool_id: ID of the tool/workflow to compile
            - mode: 'cli' or 'api' (default: cli)
            - port: Port for API mode (default: 8080)

    Returns:
        Generated standalone Python script
    """
    tool_id = config.get('tool_id', 'unknown')
    mode = config.get('mode', 'cli')
    port = config.get('port', 8080)

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
    return jsonify({{
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
    })


@app.route('/api/invoke', methods=['POST'])
def invoke():
    """Invoke the tool"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({{'error': 'Request body must be JSON'}), 400

        logger.info(f"Invoking {{TOOL_ID}} with input: {{data}}")

        # TODO: Embed actual tool logic here
        # This is a placeholder - actual implementation will embed the tool code
        result = {{"message": "Tool invoked successfully", "input": data}}

        return jsonify({{
            'success': True,
            'tool_id': TOOL_ID,
            'result': result
        })

    except Exception as e:
        logger.error(f"Error invoking tool: {e}", exc_info=True)
        return jsonify({{
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
    })


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
    parser = argparse.ArgumentParser(description=f'Standalone CLI for {{"{tool_id}"}}')
    parser.add_argument('--input', '-i', help='Input as JSON string')
    parser.add_argument('--file', '-f', help='Input from JSON file')
    parser.add_argument('--prompt', '-p', help='Direct prompt input')

    args = parser.parse_args()

    # Parse input
    input_data = {{}}
    if args.input:
        input_data = json.loads(args.input)
    elif args.file:
        with open(args.file, 'r') as f:
            input_data = json.load(f)
    elif args.prompt:
        input_data = {{'prompt': args.prompt}}

    # TODO: Embed actual tool logic here
    # This is a placeholder - actual implementation will embed the tool code
    result = {{
        'tool_id': '{tool_id}',
        'input': input_data,
        'result': 'Tool executed successfully'
    }}

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
    hooksconfig={{}},
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
