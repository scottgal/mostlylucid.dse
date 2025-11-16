#!/usr/bin/env python3
"""
SignalR Tool Trigger

Listens to SignalR endpoint and dynamically triggers tools based on incoming messages.
Supports both direct tool invocation and workflow generation.

Message Format:
{
    "action": "trigger_tool",  // or "generate_workflow"
    "tool_id": "some_tool",
    "parameters": {...},
    "task_id": "unique-id"  // optional
}
"""
import json
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
    USE_SIGNALRCORE = True
except ImportError:
    print(json.dumps({
        "error": "signalrcore package not installed",
        "success": False,
        "install_command": "pip install signalrcore"
    }))
    sys.exit(1)


class SignalRToolTrigger:
    """
    SignalR listener that dynamically triggers tools based on messages.
    """

    def __init__(self, hub_url: str, hub_method: str = "ToolTrigger"):
        self.hub_url = hub_url
        self.hub_method = hub_method
        self.connection = None
        self.messages_received = []
        self.results = []
        self.errors = []
        self.processing_queue = asyncio.Queue()
        self.is_running = False

    def build_connection(self):
        """Build SignalR connection with auto-reconnect."""
        self.connection = HubConnectionBuilder() \
            .with_url(self.hub_url) \
            .with_automatic_reconnect({
                "type": "interval",
                "keep_alive_interval": 10,
                "intervals": [0, 2, 5, 10, 20, 30]
            }) \
            .build()

        # Event handlers
        self.connection.on_open(self.on_connected)
        self.connection.on_close(self.on_disconnected)
        self.connection.on_error(self.on_error)

        # Message handler
        self.connection.on(self.hub_method, self.on_message)

    def on_connected(self):
        """Called when connection is established."""
        self.log_event("connected", {
            "hub_url": self.hub_url,
            "hub_method": self.hub_method,
            "status": "listening"
        })

    def on_disconnected(self):
        """Called when connection is closed."""
        self.log_event("disconnected", {
            "total_messages": len(self.messages_received),
            "results": len(self.results)
        })

    def on_error(self, error):
        """Called on connection error."""
        error_msg = str(error)
        self.errors.append(error_msg)
        self.log_event("error", {"error": error_msg})

    def on_message(self, message: Dict[str, Any]):
        """
        Called when message received from SignalR.

        Message format options:

        1. Trigger Tool:
        {
            "action": "trigger_tool",
            "tool_id": "nmt_translator",
            "parameters": {"text": "Hello", "target_lang": "es"},
            "task_id": "task-123"
        }

        2. Generate Workflow:
        {
            "action": "generate_workflow",
            "description": "Translate blog posts to Spanish",
            "task_id": "task-456"
        }

        3. Create Tool:
        {
            "action": "create_tool",
            "tool_spec": {...},  // OpenAPI or tool definition
            "task_id": "task-789"
        }
        """
        self.messages_received.append(message)

        self.log_event("message_received", {
            "message_number": len(self.messages_received),
            "action": message.get("action", "unknown"),
            "task_id": message.get("task_id", "none")
        })

        # Add to processing queue (async processing)
        asyncio.create_task(self.process_message(message))

    async def process_message(self, message: Dict[str, Any]):
        """
        Process a received message by triggering appropriate action.

        Args:
            message: Message from SignalR containing action and parameters
        """
        try:
            action = message.get("action", "trigger_tool")
            task_id = message.get("task_id", f"msg_{len(self.messages_received)}")

            self.log_event("processing_message", {
                "task_id": task_id,
                "action": action
            })

            # Import here to avoid circular deps
            from node_runtime import call_tool

            if action == "trigger_tool":
                # Direct tool invocation
                tool_id = message.get("tool_id")
                parameters = message.get("parameters", {})

                if not tool_id:
                    raise ValueError("tool_id is required for trigger_tool action")

                self.log_event("triggering_tool", {
                    "task_id": task_id,
                    "tool_id": tool_id,
                    "parameters": parameters
                })

                # Call the tool
                result = call_tool(tool_id, json.dumps(parameters))

                self.results.append({
                    "task_id": task_id,
                    "action": action,
                    "tool_id": tool_id,
                    "success": True,
                    "result": result
                })

                self.log_event("tool_completed", {
                    "task_id": task_id,
                    "tool_id": tool_id,
                    "result_length": len(result)
                })

            elif action == "generate_workflow":
                # Generate workflow from description
                description = message.get("description", "")

                if not description:
                    raise ValueError("description is required for generate_workflow action")

                self.log_event("generating_workflow", {
                    "task_id": task_id,
                    "description": description[:100]
                })

                # Use workflow router
                result = call_tool("task_to_workflow_router", json.dumps(message))

                workflow_data = json.loads(result)

                # Save workflow as node
                from src.node_runner import NodeRunner
                from src.registry import Registry

                runner = NodeRunner()
                registry = Registry()

                node_id = workflow_data.get("suggested_node_id", f"workflow_{task_id}")
                workflow_code = workflow_data.get("workflow_code", "")

                runner.save_code(node_id, workflow_code)
                registry.create_node(
                    node_id=node_id,
                    title=workflow_data.get("workflow_name", "Generated Workflow"),
                    tags=["signalr", "generated", "dynamic"]
                )

                self.results.append({
                    "task_id": task_id,
                    "action": action,
                    "success": True,
                    "node_id": node_id,
                    "workflow_name": workflow_data.get("workflow_name")
                })

                self.log_event("workflow_created", {
                    "task_id": task_id,
                    "node_id": node_id
                })

            elif action == "create_tool":
                # Create new tool from OpenAPI spec or definition
                tool_spec = message.get("tool_spec", {})

                if not tool_spec:
                    raise ValueError("tool_spec is required for create_tool action")

                self.log_event("creating_tool", {
                    "task_id": task_id,
                    "spec_type": tool_spec.get("type", "unknown")
                })

                # Use smart API parser to create tool from OpenAPI
                if "openapi" in tool_spec or "swagger" in tool_spec:
                    result = call_tool("smart_api_parser", json.dumps({
                        "openapi_spec": tool_spec,
                        "make_requests": False  # Just parse, don't test yet
                    }))

                    api_data = json.loads(result)

                    self.results.append({
                        "task_id": task_id,
                        "action": action,
                        "success": True,
                        "api_info": api_data.get("api_info"),
                        "endpoints": api_data.get("total_endpoints")
                    })

                    self.log_event("tool_created_from_api", {
                        "task_id": task_id,
                        "endpoints": api_data.get("total_endpoints")
                    })

                else:
                    # Generic tool creation - save as YAML
                    tool_id = tool_spec.get("name", f"tool_{task_id}").lower().replace(" ", "_")

                    # Save tool definition
                    tool_path = Path("tools/llm") / f"{tool_id}.yaml"
                    tool_path.write_text(json.dumps(tool_spec, indent=2))

                    self.results.append({
                        "task_id": task_id,
                        "action": action,
                        "success": True,
                        "tool_id": tool_id,
                        "tool_path": str(tool_path)
                    })

                    self.log_event("tool_created", {
                        "task_id": task_id,
                        "tool_id": tool_id
                    })

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            error_msg = str(e)
            self.errors.append({
                "task_id": task_id,
                "error": error_msg,
                "message": message
            })

            self.log_event("processing_error", {
                "task_id": task_id,
                "error": error_msg
            })

    def log_event(self, event: str, data: Dict[str, Any]):
        """Log event to stderr."""
        print(json.dumps({
            "event": event,
            **data
        }), file=sys.stderr)

    async def listen(self, duration_seconds: int = None):
        """
        Start listening to SignalR hub.

        Args:
            duration_seconds: How long to listen (None = forever)
        """
        self.build_connection()
        self.is_running = True

        # Start connection
        self.connection.start()

        # Listen for specified duration or forever
        try:
            if duration_seconds:
                await asyncio.sleep(duration_seconds)
            else:
                # Run forever (until Ctrl+C)
                while self.is_running:
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            self.log_event("shutdown_requested", {})

        finally:
            # Stop connection
            self.connection.stop()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all processing."""
        return {
            "success": True,
            "hub_url": self.hub_url,
            "hub_method": self.hub_method,
            "total_messages": len(self.messages_received),
            "successful_results": len(self.results),
            "errors": len(self.errors),
            "results": self.results,
            "error_details": self.errors
        }


async def main():
    """
    Main entry point.

    Input JSON:
    {
        "hub_url": "http://localhost:5000/toolhub",
        "hub_method": "ToolTrigger",  // optional, default: "ToolTrigger"
        "duration_seconds": 60  // optional, default: run forever
    }
    """
    try:
        input_data = json.load(sys.stdin)

        hub_url = input_data.get("hub_url", "")
        if not hub_url:
            print(json.dumps({
                "error": "hub_url is required",
                "success": False,
                "example": {
                    "hub_url": "http://localhost:5000/toolhub",
                    "duration_seconds": 60
                }
            }))
            return

        hub_method = input_data.get("hub_method", "ToolTrigger")
        duration = input_data.get("duration_seconds", None)

        # Create trigger and listen
        trigger = SignalRToolTrigger(hub_url, hub_method)
        await trigger.listen(duration)

        # Output summary
        print(json.dumps(trigger.get_summary(), indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "success": False
        }))


if __name__ == "__main__":
    asyncio.run(main())
