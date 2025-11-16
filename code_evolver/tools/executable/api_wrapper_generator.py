#!/usr/bin/env python3
"""
API Wrapper Generator
Generates a Flask API wrapper script for any tool or workflow
"""
import json
import sys
from typing import Dict, Any


def generate_api_wrapper(config: Dict[str, Any]) -> str:
    """
    Generate a Flask API wrapper script for a tool/workflow

    Args:
        config: Configuration dictionary with:
            - tool_id: ID of the tool/workflow to wrap
            - port: Port to run on (default: 8080)
            - host: Host to bind to (default: 0.0.0.0)
            - enable_cors: Whether to enable CORS (default: true)

    Returns:
        Generated Python Flask API script
    """
    tool_id = config.get('tool_id', 'unknown')
    port = config.get('port', 8080)
    host = config.get('host', '0.0.0.0')
    enable_cors = config.get('enable_cors', True)

    api_script = f'''#!/usr/bin/env python3
"""
Auto-generated Flask API wrapper for tool/workflow: {tool_id}
"""
import os
import sys
import json
import logging
from flask import Flask, request, jsonify
{"from flask_cors import CORS" if enable_cors else ""}

# Add code_evolver to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code_evolver'))

from src.tools_manager import ToolsManager
from src.llm_client_factory import LLMClientFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
{"CORS(app)" if enable_cors else ""}

# Initialize ToolsManager
config_path = os.path.join(os.path.dirname(__file__), 'code_evolver', 'config.yaml')
llm_client_factory = LLMClientFactory(config_path=config_path)
tools_manager = ToolsManager(llm_client_factory=llm_client_factory, config_path=config_path)

# Target tool/workflow ID
TARGET_TOOL_ID = "{tool_id}"


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({{
        'status': 'healthy',
        'tool_id': TARGET_TOOL_ID,
        'version': '1.0.0'
    }})


@app.route('/api/info', methods=['GET'])
def info():
    """Get tool/workflow information"""
    try:
        # Try to get tool info
        tool_info = tools_manager.get_tool(TARGET_TOOL_ID)
        if tool_info:
            return jsonify({{
                'tool_id': TARGET_TOOL_ID,
                'name': tool_info.get('name', 'Unknown'),
                'type': tool_info.get('type', 'Unknown'),
                'description': tool_info.get('description', ''),
                'input_schema': tool_info.get('input_schema', {{}}),
                'output_schema': tool_info.get('output_schema', {{}})
            }})
        else:
            return jsonify({{
                'error': f'Tool {{TARGET_TOOL_ID}} not found'
            }}), 404
    except Exception as e:
        logger.error(f"Error getting tool info: {{e}}")
        return jsonify({{'error': str(e)}}), 500


@app.route('/api/invoke', methods=['POST'])
def invoke():
    """Invoke the tool/workflow"""
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({{'error': 'Request body must be JSON'}}), 400

        logger.info(f"Invoking {{TARGET_TOOL_ID}} with input: {{data}}")

        # Get tool info to determine type
        tool_info = tools_manager.get_tool(TARGET_TOOL_ID)
        if not tool_info:
            return jsonify({{'error': f'Tool {{TARGET_TOOL_ID}} not found'}}), 404

        tool_type = tool_info.get('type', '').lower()

        # Invoke based on tool type
        result = None
        if tool_type == 'llm':
            # For LLM tools, extract prompt from data
            prompt = data.get('prompt', '')
            temperature = data.get('temperature', 0.7)
            result = tools_manager.invoke_llm_tool(
                tool_id=TARGET_TOOL_ID,
                prompt=prompt,
                temperature=temperature
            )
        elif tool_type == 'executable':
            # For executable tools, pass data as kwargs
            result = tools_manager.invoke_executable_tool(
                tool_id=TARGET_TOOL_ID,
                **data
            )
        elif tool_type == 'workflow':
            # For workflows, pass data as input
            result = tools_manager.execute_workflow(
                workflow_id=TARGET_TOOL_ID,
                input_data=data
            )
        else:
            return jsonify({{
                'error': f'Unsupported tool type: {{tool_type}}'
            }}), 400

        logger.info(f"Successfully invoked {{TARGET_TOOL_ID}}")

        return jsonify({{
            'success': True,
            'tool_id': TARGET_TOOL_ID,
            'result': result
        }})

    except Exception as e:
        logger.error(f"Error invoking tool: {{e}}", exc_info=True)
        return jsonify({{
            'success': False,
            'error': str(e)
        }}), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API documentation"""
    return jsonify({{
        'service': 'Tool API Wrapper',
        'tool_id': TARGET_TOOL_ID,
        'endpoints': {{
            'GET /': 'API documentation (this page)',
            'GET /api/health': 'Health check',
            'GET /api/info': 'Get tool information',
            'POST /api/invoke': 'Invoke the tool (JSON body with tool-specific parameters)'
        }}
    }})


if __name__ == '__main__':
    logger.info(f"Starting API wrapper for tool: {{TARGET_TOOL_ID}}")
    logger.info(f"Listening on {{'{host}:{port}'}}")
    app.run(host='{host}', port={port}, debug=False)
'''

    return api_script


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({{
            'error': 'Missing configuration JSON argument'
        }}))
        sys.exit(1)

    try:
        # Parse configuration from command line argument
        config = json.loads(sys.argv[1])

        # Generate API wrapper
        api_script = generate_api_wrapper(config)

        # Output result
        print(json.dumps({
            'success': True,
            'api_script': api_script
        }))

    except json.JSONDecodeError as e:
        print(json.dumps({
            'error': f'Invalid JSON configuration: {e}'
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            'error': f'Error generating API wrapper: {e}'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
