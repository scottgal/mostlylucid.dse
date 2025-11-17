#!/usr/bin/env python3
"""
Flask Web UI for Code Evolver
Interactive chat interface with real-time workflow visualization
"""

import sys
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Add code_evolver to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'code_evolver'))

from src.config_manager import ConfigManager
from src.tools_manager import ToolsManager
from src.workflow_builder import WorkflowBuilder
from src.task_evaluator import TaskEvaluator
from src.llm_client_factory import LLMClientFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'code-evolver-web-ui-secret-key-change-in-production'
app.config['JSON_SORT_KEYS'] = False

# Enable CORS
CORS(app)

# Initialize SocketIO with async mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize Code Evolver components
config_path = Path(__file__).parent.parent / 'code_evolver' / 'config.yaml'
config_manager = ConfigManager(str(config_path))
tools_manager = ToolsManager(config_manager)
llm_client_factory = LLMClientFactory(config_manager)
workflow_builder = WorkflowBuilder(tools_manager)
task_evaluator = TaskEvaluator(config_manager, tools_manager)

# Global state for sessions
sessions: Dict[str, Dict[str, Any]] = {}


@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'tools_loaded': len(tools_manager.list_tools()),
        'models_available': list(config_manager.available_backends.keys())
    })


@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get list of available tools."""
    try:
        tools = tools_manager.list_tools()
        tool_list = []

        for tool_id, tool in tools.items():
            tool_list.append({
                'id': tool_id,
                'name': tool.name,
                'type': tool.tool_type.value,
                'description': tool.description,
                'tags': tool.tags
            })

        return jsonify({
            'success': True,
            'tools': tool_list,
            'total': len(tool_list)
        })
    except Exception as e:
        logger.exception("Error fetching tools")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tool/<tool_id>', methods=['GET'])
def get_tool_details(tool_id: str):
    """Get detailed information about a specific tool."""
    try:
        tool = tools_manager.get_tool(tool_id)

        if not tool:
            return jsonify({
                'success': False,
                'error': f'Tool {tool_id} not found'
            }), 404

        return jsonify({
            'success': True,
            'tool': {
                'id': tool_id,
                'name': tool.name,
                'type': tool.tool_type.value,
                'description': tool.description,
                'tags': tool.tags,
                'parameters': tool.parameters,
                'metadata': tool.metadata,
                'usage_count': tool.usage_count
            }
        })
    except Exception as e:
        logger.exception(f"Error fetching tool {tool_id}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    session_id = request.sid
    sessions[session_id] = {
        'created_at': datetime.now().isoformat(),
        'messages': [],
        'workflows': []
    }

    logger.info(f"Client connected: {session_id}")

    emit('connected', {
        'session_id': session_id,
        'message': 'Connected to Code Evolver Web UI',
        'timestamp': datetime.now().isoformat()
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    session_id = request.sid

    if session_id in sessions:
        del sessions[session_id]

    logger.info(f"Client disconnected: {session_id}")


@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle incoming chat message and process request."""
    session_id = request.sid
    message = data.get('message', '').strip()

    if not message:
        emit('error', {'message': 'Empty message'})
        return

    logger.info(f"Received message from {session_id}: {message}")

    # Store user message
    if session_id in sessions:
        sessions[session_id]['messages'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })

    # Echo user message
    emit('user_message', {
        'message': message,
        'timestamp': datetime.now().isoformat()
    })

    # Process the request
    try:
        process_user_request(session_id, message)
    except Exception as e:
        logger.exception("Error processing request")
        emit('error', {
            'message': f'Error processing request: {str(e)}',
            'timestamp': datetime.now().isoformat()
        })


def process_user_request(session_id: str, message: str):
    """Process user request and generate workflow."""

    # Emit thinking status
    socketio.emit('status', {
        'status': 'thinking',
        'message': 'Analyzing your request...'
    }, room=session_id)

    # Step 1: Evaluate task
    socketio.emit('workflow_step', {
        'step': 'evaluate',
        'message': 'Evaluating task complexity...',
        'progress': 10
    }, room=session_id)

    try:
        task_info = task_evaluator.evaluate_task(message)

        socketio.emit('workflow_step', {
            'step': 'evaluate',
            'message': f'Task classified as: {task_info.get("complexity", "medium")}',
            'progress': 20,
            'data': {
                'complexity': task_info.get('complexity'),
                'category': task_info.get('category')
            }
        }, room=session_id)

    except Exception as e:
        logger.error(f"Task evaluation failed: {e}")
        task_info = {'complexity': 'medium', 'category': 'general'}

    # Step 2: Search for relevant tools
    socketio.emit('workflow_step', {
        'step': 'search_tools',
        'message': 'Searching for relevant tools...',
        'progress': 30
    }, room=session_id)

    # Get all tools for demo
    all_tools = tools_manager.list_tools()
    relevant_tools = list(all_tools.keys())[:5]  # Take first 5 for demo

    socketio.emit('workflow_step', {
        'step': 'search_tools',
        'message': f'Found {len(relevant_tools)} relevant tools',
        'progress': 40,
        'data': {
            'tools': relevant_tools
        }
    }, room=session_id)

    # Animate tool discovery
    for i, tool_id in enumerate(relevant_tools):
        tool = all_tools.get(tool_id)
        if tool:
            socketio.emit('tool_discovered', {
                'tool_id': tool_id,
                'name': tool.name,
                'type': tool.tool_type.value,
                'description': tool.description,
                'index': i,
                'total': len(relevant_tools)
            }, room=session_id)
            socketio.sleep(0.3)  # Animate discovery

    # Step 3: Generate workflow plan
    socketio.emit('workflow_step', {
        'step': 'plan',
        'message': 'Generating workflow plan...',
        'progress': 50
    }, room=session_id)

    # Simulate workflow generation with animation
    workflow_steps = [
        {
            'id': 'step_1',
            'name': 'Input Validation',
            'tool': relevant_tools[0] if relevant_tools else 'validator',
            'status': 'planned'
        },
        {
            'id': 'step_2',
            'name': 'Main Processing',
            'tool': relevant_tools[1] if len(relevant_tools) > 1 else 'processor',
            'status': 'planned'
        },
        {
            'id': 'step_3',
            'name': 'Output Generation',
            'tool': relevant_tools[2] if len(relevant_tools) > 2 else 'output_gen',
            'status': 'planned'
        }
    ]

    # Animate workflow assembly
    for i, step in enumerate(workflow_steps):
        socketio.emit('workflow_step_added', {
            'step': step,
            'index': i,
            'total': len(workflow_steps)
        }, room=session_id)
        socketio.sleep(0.5)

    socketio.emit('workflow_step', {
        'step': 'plan',
        'message': f'Workflow plan created with {len(workflow_steps)} steps',
        'progress': 70,
        'data': {
            'steps': workflow_steps
        }
    }, room=session_id)

    # Step 4: Execute workflow (simulated)
    socketio.emit('workflow_step', {
        'step': 'execute',
        'message': 'Executing workflow...',
        'progress': 80
    }, room=session_id)

    # Simulate execution
    for i, step in enumerate(workflow_steps):
        step['status'] = 'executing'
        socketio.emit('workflow_step_executing', {
            'step': step,
            'index': i
        }, room=session_id)
        socketio.sleep(1.0)

        step['status'] = 'completed'
        socketio.emit('workflow_step_completed', {
            'step': step,
            'index': i,
            'result': {'success': True, 'message': f'Step {i+1} completed'}
        }, room=session_id)

    # Step 5: Complete
    socketio.emit('workflow_step', {
        'step': 'complete',
        'message': 'Workflow completed successfully!',
        'progress': 100
    }, room=session_id)

    # Send final response
    response_message = f"""I've analyzed your request: "{message}"

**Workflow Summary:**
- Task Complexity: {task_info.get('complexity', 'medium')}
- Tools Used: {len(relevant_tools)}
- Steps Executed: {len(workflow_steps)}

**Result:**
All workflow steps completed successfully! The system dynamically assembled and executed a workflow using the most appropriate tools for your request.

This is a demonstration of the dynamic workflow building capabilities. In a full implementation, this would execute real tools and return actual results."""

    socketio.emit('assistant_message', {
        'message': response_message,
        'timestamp': datetime.now().isoformat(),
        'workflow': {
            'steps': workflow_steps,
            'tools_used': relevant_tools,
            'complexity': task_info.get('complexity')
        }
    }, room=session_id)

    # Store assistant message
    if session_id in sessions:
        sessions[session_id]['messages'].append({
            'role': 'assistant',
            'content': response_message,
            'timestamp': datetime.now().isoformat()
        })


@socketio.on('get_history')
def handle_get_history():
    """Get chat history for current session."""
    session_id = request.sid

    if session_id in sessions:
        emit('chat_history', {
            'messages': sessions[session_id]['messages']
        })
    else:
        emit('chat_history', {'messages': []})


if __name__ == '__main__':
    logger.info("Starting Code Evolver Web UI...")
    logger.info(f"Tools loaded: {len(tools_manager.list_tools())}")
    logger.info("Navigate to http://localhost:5000")

    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
