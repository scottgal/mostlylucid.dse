#!/usr/bin/env python3
"""
HTTP Server Tool - Demonstration

This demonstrates how to use the HTTP server tool to expose workflows as APIs.

Features demonstrated:
1. Creating an HTTP server
2. Adding JSON API endpoints
3. Adding HTML endpoints
4. Serving workflow results via HTTP
5. Handling GET and POST requests
"""

import sys
import time
import json
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.http_server_tool import HTTPServerTool, WorkflowHTTPAdapter


def demo_basic_server():
    """Demo 1: Basic HTTP server with simple endpoints."""
    print("=== Demo 1: Basic HTTP Server ===\n")

    # Create server
    server = HTTPServerTool(host="127.0.0.1", port=8080)

    # Add a simple JSON API endpoint
    def hello_handler(request_data):
        return {
            "message": "Hello from DSE HTTP Server!",
            "timestamp": time.time(),
            "request": request_data
        }

    server.add_route(
        path="/api/hello",
        methods=["GET", "POST"],
        handler=hello_handler,
        response_type="json",
        description="Simple hello endpoint"
    )

    # Add an HTML endpoint
    def homepage_handler(request_data):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>DSE Workflow API</title>
            <style>
                body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
                h1 { color: #333; }
                .endpoint { background: #f4f4f4; padding: 10px; margin: 10px 0; border-radius: 5px; }
                code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>DSE Workflow HTTP Server</h1>
            <p>Welcome to the DSE workflow HTTP server! This server allows workflows to be exposed as APIs.</p>

            <h2>Available Endpoints:</h2>
            <div class="endpoint">
                <strong>GET/POST /api/hello</strong>
                <p>Simple hello endpoint that returns JSON</p>
                <code>curl http://127.0.0.1:8080/api/hello</code>
            </div>

            <div class="endpoint">
                <strong>POST /api/echo</strong>
                <p>Echo endpoint that returns what you send</p>
                <code>curl -X POST http://127.0.0.1:8080/api/echo -H "Content-Type: application/json" -d '{"text": "hello"}'</code>
            </div>

            <div class="endpoint">
                <strong>GET /</strong>
                <p>This page</p>
            </div>
        </body>
        </html>
        """

    server.add_route(
        path="/",
        methods=["GET"],
        handler=homepage_handler,
        response_type="html",
        description="Homepage"
    )

    # Add echo endpoint
    def echo_handler(request_data):
        return {
            "echo": request_data.get("data", {}),
            "received_at": time.time()
        }

    server.add_route(
        path="/api/echo",
        methods=["POST"],
        handler=echo_handler,
        response_type="json",
        description="Echo endpoint"
    )

    # Print server info
    info = server.get_server_info()
    print(f"Server configured:")
    print(f"  URL: {info['url']}")
    print(f"  Routes: {info['routes_count']}")
    print(f"\nRegistered routes:")
    for route in server.list_routes():
        print(f"  {route['methods']} {route['path']} ({route['response_type']}) - {route['description']}")

    # Start server (non-blocking)
    print(f"\nStarting server on {info['url']}...")
    server.start(blocking=False)

    print("\nServer is running! Try these commands:")
    print(f"  curl http://127.0.0.1:8080/api/hello")
    print(f"  curl -X POST http://127.0.0.1:8080/api/echo -H 'Content-Type: application/json' -d '{{\"text\": \"hello\"}}'")
    print(f"  curl http://127.0.0.1:8080/")
    print("\nPress Ctrl+C to stop the server...\n")

    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping server...")
        server.stop()
        print("Server stopped.\n")


def demo_workflow_api():
    """Demo 2: Exposing workflows as API endpoints."""
    print("=== Demo 2: Workflow API Endpoints ===\n")

    # Create server
    server = HTTPServerTool(host="127.0.0.1", port=8081)

    # Simulate workflow handlers
    def text_summarizer_workflow(request_data):
        """Simulated workflow: text summarization."""
        text = request_data.get("data", {}).get("text", "")

        if not text:
            return {"error": "No text provided"}

        # Simulated summarization (in real usage, this would call actual workflow)
        summary = f"Summary of {len(text)} characters: {text[:100]}..."

        return {
            "workflow": "text_summarizer",
            "input_length": len(text),
            "summary": summary,
            "processed_at": time.time()
        }

    def sentiment_analyzer_workflow(request_data):
        """Simulated workflow: sentiment analysis."""
        text = request_data.get("data", {}).get("text", "")

        if not text:
            return {"error": "No text provided"}

        # Simulated sentiment analysis
        sentiment = "positive" if "good" in text.lower() or "great" in text.lower() else "neutral"

        return {
            "workflow": "sentiment_analyzer",
            "text": text,
            "sentiment": sentiment,
            "confidence": 0.85,
            "processed_at": time.time()
        }

    def code_generator_workflow(request_data):
        """Simulated workflow: code generation."""
        task = request_data.get("data", {}).get("task", "")

        if not task:
            return {"error": "No task provided"}

        # Simulated code generation
        code = f"# Generated code for: {task}\ndef solution():\n    # TODO: Implement\n    pass\n"

        return {
            "workflow": "code_generator",
            "task": task,
            "code": code,
            "language": "python",
            "processed_at": time.time()
        }

    # Add workflow endpoints
    server.add_route(
        path="/api/summarize",
        methods=["POST"],
        handler=text_summarizer_workflow,
        response_type="json",
        description="Text summarization workflow"
    )

    server.add_route(
        path="/api/sentiment",
        methods=["POST"],
        handler=sentiment_analyzer_workflow,
        response_type="json",
        description="Sentiment analysis workflow"
    )

    server.add_route(
        path="/api/generate-code",
        methods=["POST"],
        handler=code_generator_workflow,
        response_type="json",
        description="Code generation workflow"
    )

    # Add API documentation endpoint
    def api_docs_handler(request_data):
        return {
            "api": "DSE Workflow API",
            "version": "1.0",
            "endpoints": [
                {
                    "path": "/api/summarize",
                    "method": "POST",
                    "description": "Summarize text",
                    "input": {"text": "string"},
                    "output": {"summary": "string", "input_length": "int"}
                },
                {
                    "path": "/api/sentiment",
                    "method": "POST",
                    "description": "Analyze sentiment",
                    "input": {"text": "string"},
                    "output": {"sentiment": "string", "confidence": "float"}
                },
                {
                    "path": "/api/generate-code",
                    "method": "POST",
                    "description": "Generate code",
                    "input": {"task": "string"},
                    "output": {"code": "string", "language": "string"}
                }
            ]
        }

    server.add_route(
        path="/api/docs",
        methods=["GET"],
        handler=api_docs_handler,
        response_type="json",
        description="API documentation"
    )

    # Print info
    info = server.get_server_info()
    print(f"Workflow API Server configured:")
    print(f"  URL: {info['url']}")
    print(f"  Routes: {info['routes_count']}")
    print(f"\nAvailable workflow endpoints:")
    for route in server.list_routes():
        print(f"  {route['methods']} {route['path']} - {route['description']}")

    # Start server
    print(f"\nStarting server on {info['url']}...")
    server.start(blocking=False)

    print("\nWorkflow API is running! Try these examples:")
    print(f"\n1. Summarize text:")
    print(f"   curl -X POST http://127.0.0.1:8081/api/summarize -H 'Content-Type: application/json' -d '{{\"text\": \"This is a long text that needs to be summarized...\"}}'")
    print(f"\n2. Analyze sentiment:")
    print(f"   curl -X POST http://127.0.0.1:8081/api/sentiment -H 'Content-Type: application/json' -d '{{\"text\": \"This is a great day!\"}}'")
    print(f"\n3. Generate code:")
    print(f"   curl -X POST http://127.0.0.1:8081/api/generate-code -H 'Content-Type: application/json' -d '{{\"task\": \"fibonacci sequence\"}}'")
    print(f"\n4. View API docs:")
    print(f"   curl http://127.0.0.1:8081/api/docs")
    print("\nPress Ctrl+C to stop the server...\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping server...")
        server.stop()
        print("Server stopped.\n")


def demo_workflow_adapter():
    """Demo 3: Using WorkflowHTTPAdapter for integration."""
    print("=== Demo 3: Workflow HTTP Adapter ===\n")

    # Mock workflow and tools managers (in real usage, these would be actual instances)
    class MockWorkflowManager:
        pass

    class MockToolsManager:
        pass

    workflow_manager = MockWorkflowManager()
    tools_manager = MockToolsManager()

    # Create adapter
    adapter = WorkflowHTTPAdapter(workflow_manager, tools_manager)

    # Create server
    server = adapter.create_server(
        server_id="main_api",
        host="127.0.0.1",
        port=8082
    )

    # Register workflow endpoints
    adapter.register_workflow_endpoint(
        server_id="main_api",
        workflow_id="text_processor",
        path="/api/process-text",
        methods=["POST"],
        response_type="json"
    )

    adapter.register_workflow_endpoint(
        server_id="main_api",
        workflow_id="data_analyzer",
        path="/api/analyze",
        methods=["POST"],
        response_type="json"
    )

    # List all servers
    print("Registered servers:")
    for server_info in adapter.list_servers():
        print(f"\n  Server: {server_info['server_id']}")
        print(f"    URL: {server_info['url']}")
        print(f"    Running: {server_info['is_running']}")
        print(f"    Routes:")
        for route in server_info['routes']:
            print(f"      {route['methods']} {route['path']}")

    # Start server
    print(f"\nStarting server...")
    adapter.start_server("main_api", blocking=False)

    print("\nAdapter-managed server is running!")
    print("Press Ctrl+C to stop...\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping server...")
        adapter.stop_server("main_api")
        print("Server stopped.\n")


def main():
    """Run demonstrations."""
    demos = {
        "1": ("Basic HTTP Server", demo_basic_server),
        "2": ("Workflow API Endpoints", demo_workflow_api),
        "3": ("Workflow HTTP Adapter", demo_workflow_adapter)
    }

    print("\nHTTP Server Tool Demonstrations")
    print("=" * 50)
    print("\nAvailable demos:")
    for key, (name, _) in demos.items():
        print(f"  {key}. {name}")
    print("  q. Quit")

    choice = input("\nSelect demo (1-3, or q to quit): ").strip()

    if choice == "q":
        print("Goodbye!")
        return

    if choice in demos:
        name, demo_func = demos[choice]
        print(f"\nRunning: {name}\n")
        demo_func()
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    # Check if Flask is installed
    try:
        import flask
    except ImportError:
        print("Error: Flask is not installed.")
        print("Please install it with: pip install flask")
        sys.exit(1)

    main()
