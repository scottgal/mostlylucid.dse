"""
HTTP Server Tool for mostlylucid DiSE.
Allows workflows to serve content via HTTP (HTML/API).
"""
import json
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from flask import Flask, request, jsonify, Response
from werkzeug.serving import make_server
import traceback

logger = logging.getLogger(__name__)


class HTTPServerTool:
    """
    HTTP server tool that enables workflows to serve content via HTTP.

    Features:
    - Start/stop HTTP server on configurable host/port
    - Register routes dynamically
    - Support for GET, POST, PUT, DELETE methods
    - Return HTML or JSON responses
    - Route requests to workflow handlers
    - CORS support
    - Error handling and logging

    Example usage:
        server = HTTPServerTool(host="0.0.0.0", port=8080)

        # Add a JSON API endpoint
        server.add_route(
            path="/api/process",
            methods=["POST"],
            handler=lambda data: {"result": "processed", "data": data},
            response_type="json"
        )

        # Add an HTML endpoint
        server.add_route(
            path="/",
            methods=["GET"],
            handler=lambda: "<h1>Welcome to DSE Workflow API</h1>",
            response_type="html"
        )

        # Start the server (non-blocking)
        server.start()

        # Stop the server when done
        server.stop()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        enable_cors: bool = True,
        debug: bool = False
    ):
        """
        Initialize HTTP server tool.

        Args:
            host: Host to bind to (default: 0.0.0.0)
            port: Port to listen on (default: 8080)
            enable_cors: Enable CORS headers (default: True)
            debug: Enable Flask debug mode (default: False)
        """
        self.host = host
        self.port = port
        self.enable_cors = enable_cors
        self.debug = debug

        # Flask app
        self.app = Flask(__name__)
        self.app.config['JSON_SORT_KEYS'] = False

        # Server instance
        self.server = None
        self.server_thread = None
        self.is_running = False

        # Route registry
        self.routes: Dict[str, Dict[str, Any]] = {}

        # CORS handling
        if self.enable_cors:
            self._setup_cors()

        logger.info(f"HTTPServerTool initialized on {host}:{port}")

    def _setup_cors(self):
        """Setup CORS headers for all responses."""
        @self.app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response

    def add_route(
        self,
        path: str,
        methods: List[str],
        handler: Callable,
        response_type: str = "json",
        description: str = ""
    ):
        """
        Add a route to the HTTP server.

        Args:
            path: URL path (e.g., "/api/process")
            methods: HTTP methods (e.g., ["GET", "POST"])
            handler: Function to handle requests
                - For JSON: handler(request_data) -> dict
                - For HTML: handler(request_data) -> str
            response_type: "json" or "html"
            description: Human-readable description of the endpoint
        """
        route_key = f"{path}::{','.join(methods)}"

        self.routes[route_key] = {
            "path": path,
            "methods": methods,
            "handler": handler,
            "response_type": response_type,
            "description": description
        }

        # Create Flask route
        def route_handler():
            try:
                # Get request data
                if request.method == "GET":
                    request_data = dict(request.args)
                elif request.method in ["POST", "PUT", "PATCH"]:
                    if request.is_json:
                        request_data = request.get_json()
                    else:
                        request_data = dict(request.form)
                else:
                    request_data = {}

                # Add request metadata
                request_data = {
                    "method": request.method,
                    "path": request.path,
                    "headers": dict(request.headers),
                    "data": request_data
                }

                # Call handler
                result = handler(request_data)

                # Format response
                if response_type == "json":
                    return jsonify(result), 200
                elif response_type == "html":
                    return Response(result, mimetype="text/html"), 200
                else:
                    return jsonify({"error": "Invalid response type"}), 500

            except Exception as e:
                logger.error(f"Error handling request to {path}: {e}")
                logger.error(traceback.format_exc())

                if response_type == "json":
                    return jsonify({
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }), 500
                else:
                    return Response(
                        f"<h1>Error</h1><pre>{str(e)}</pre>",
                        mimetype="text/html"
                    ), 500

        # Register with Flask
        endpoint = f"route_{path.replace('/', '_')}_{','.join(methods)}"
        self.app.add_url_rule(
            path,
            endpoint,
            route_handler,
            methods=methods
        )

        logger.info(f"Added route: {methods} {path} -> {response_type}")

    def add_workflow_route(
        self,
        path: str,
        methods: List[str],
        workflow_id: str,
        workflow_executor: Callable,
        response_type: str = "json",
        description: str = ""
    ):
        """
        Add a route that executes a workflow.

        Args:
            path: URL path
            methods: HTTP methods
            workflow_id: ID of workflow to execute
            workflow_executor: Function that executes workflow
                Signature: workflow_executor(workflow_id, input_data) -> result
            response_type: "json" or "html"
            description: Endpoint description
        """
        def workflow_handler(request_data):
            """Handler that executes the workflow."""
            # Extract input data from request
            input_data = request_data.get("data", {})

            # Execute workflow
            logger.info(f"Executing workflow {workflow_id} for {path}")
            result = workflow_executor(workflow_id, input_data)

            return result

        self.add_route(
            path=path,
            methods=methods,
            handler=workflow_handler,
            response_type=response_type,
            description=description or f"Execute workflow: {workflow_id}"
        )

    def start(self, blocking: bool = False):
        """
        Start the HTTP server.

        Args:
            blocking: If True, blocks until server stops.
                     If False, runs in background thread.
        """
        if self.is_running:
            logger.warning("Server is already running")
            return

        # Create server
        self.server = make_server(self.host, self.port, self.app, threaded=True)
        self.is_running = True

        if blocking:
            logger.info(f"Starting HTTP server on {self.host}:{self.port} (blocking)")
            self.server.serve_forever()
        else:
            logger.info(f"Starting HTTP server on {self.host}:{self.port} (background)")
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()

    def stop(self):
        """Stop the HTTP server."""
        if not self.is_running:
            logger.warning("Server is not running")
            return

        logger.info("Stopping HTTP server")

        if self.server:
            self.server.shutdown()
            self.server = None

        if self.server_thread:
            self.server_thread.join(timeout=5)
            self.server_thread = None

        self.is_running = False

    def list_routes(self) -> List[Dict[str, Any]]:
        """
        List all registered routes.

        Returns:
            List of route information dictionaries
        """
        routes = []
        for route_key, route_info in self.routes.items():
            routes.append({
                "path": route_info["path"],
                "methods": route_info["methods"],
                "response_type": route_info["response_type"],
                "description": route_info["description"]
            })
        return routes

    def get_server_info(self) -> Dict[str, Any]:
        """
        Get server information.

        Returns:
            Dictionary with server status and configuration
        """
        return {
            "host": self.host,
            "port": self.port,
            "is_running": self.is_running,
            "enable_cors": self.enable_cors,
            "routes_count": len(self.routes),
            "routes": self.list_routes(),
            "url": f"http://{self.host}:{self.port}"
        }


class WorkflowHTTPAdapter:
    """
    Adapter that connects HTTP server to DSE workflow system.
    Allows workflows to be exposed as HTTP endpoints.
    """

    def __init__(self, workflow_manager, tools_manager):
        """
        Initialize adapter.

        Args:
            workflow_manager: WorkflowManager instance
            tools_manager: ToolsManager instance
        """
        self.workflow_manager = workflow_manager
        self.tools_manager = tools_manager
        self.servers: Dict[str, HTTPServerTool] = {}

    def create_server(
        self,
        server_id: str,
        host: str = "0.0.0.0",
        port: int = 8080,
        enable_cors: bool = True
    ) -> HTTPServerTool:
        """
        Create a new HTTP server instance.

        Args:
            server_id: Unique identifier for this server
            host: Host to bind to
            port: Port to listen on
            enable_cors: Enable CORS

        Returns:
            HTTPServerTool instance
        """
        if server_id in self.servers:
            logger.warning(f"Server {server_id} already exists")
            return self.servers[server_id]

        server = HTTPServerTool(host=host, port=port, enable_cors=enable_cors)
        self.servers[server_id] = server

        logger.info(f"Created HTTP server: {server_id} on {host}:{port}")
        return server

    def register_workflow_endpoint(
        self,
        server_id: str,
        workflow_id: str,
        path: str,
        methods: List[str] = ["POST"],
        response_type: str = "json"
    ):
        """
        Register a workflow as an HTTP endpoint.

        Args:
            server_id: ID of server to add route to
            workflow_id: ID of workflow to expose
            path: URL path for the endpoint
            methods: HTTP methods to support
            response_type: "json" or "html"
        """
        if server_id not in self.servers:
            raise ValueError(f"Server not found: {server_id}")

        server = self.servers[server_id]

        # Create workflow executor
        def execute_workflow(wf_id: str, input_data: dict) -> dict:
            """Execute workflow and return result."""
            try:
                # TODO: Integrate with actual workflow execution
                # For now, return a placeholder response
                return {
                    "workflow_id": wf_id,
                    "status": "success",
                    "input": input_data,
                    "output": "Workflow execution not yet integrated"
                }
            except Exception as e:
                logger.error(f"Error executing workflow {wf_id}: {e}")
                return {
                    "workflow_id": wf_id,
                    "status": "error",
                    "error": str(e)
                }

        # Add route to server
        server.add_workflow_route(
            path=path,
            methods=methods,
            workflow_id=workflow_id,
            workflow_executor=execute_workflow,
            response_type=response_type,
            description=f"Execute workflow: {workflow_id}"
        )

        logger.info(f"Registered workflow {workflow_id} at {methods} {path}")

    def start_server(self, server_id: str, blocking: bool = False):
        """Start an HTTP server."""
        if server_id not in self.servers:
            raise ValueError(f"Server not found: {server_id}")

        self.servers[server_id].start(blocking=blocking)

    def stop_server(self, server_id: str):
        """Stop an HTTP server."""
        if server_id not in self.servers:
            raise ValueError(f"Server not found: {server_id}")

        self.servers[server_id].stop()

    def get_server(self, server_id: str) -> Optional[HTTPServerTool]:
        """Get server instance by ID."""
        return self.servers.get(server_id)

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all servers."""
        return [
            {
                "server_id": server_id,
                **server.get_server_info()
            }
            for server_id, server in self.servers.items()
        ]
