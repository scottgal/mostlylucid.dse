#!/usr/bin/env python3
"""
SignalR Hub Connector

Connects to a SignalR hub and receives streaming task data.
Routes each task to the workflow generator for automatic workflow creation.
"""
import json
import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from signalr import Connection
except ImportError:
    try:
        # Fallback to signalrcore if signalr not available
        from signalrcore.hub_connection_builder import HubConnectionBuilder
        USE_SIGNALRCORE = True
    except ImportError:
        print(json.dumps({
            "error": "SignalR package not installed",
            "success": False,
            "install_options": [
                "pip install signalr-client",
                "pip install signalrcore"
            ],
            "recommended": "pip install signalr-client"
        }))
        sys.exit(1)
else:
    USE_SIGNALRCORE = False


async def connect_to_hub(hub_url, hub_name="TaskHub", on_message_callback=None):
    """
    Connect to SignalR hub and listen for messages with automatic reconnection.

    Args:
        hub_url: Full URL to SignalR hub (e.g., "http://localhost:5000/taskhub")
        hub_name: Name of the hub method to subscribe to
        on_message_callback: Async function to call when message received
    """
    # Track connection state
    connection_state = {
        "connected": False,
        "message_count": 0,
        "errors": [],
        "reconnect_attempts": 0
    }

    if USE_SIGNALRCORE:
        # Use signalrcore library
        connection = HubConnectionBuilder() \
            .with_url(hub_url) \
            .with_automatic_reconnect({
                "type": "interval",
                "keep_alive_interval": 10,
                "intervals": [0, 2, 5, 10, 20, 30]
            }) \
            .build()

        def on_open():
            connection_state["connected"] = True
            print(json.dumps({
                "event": "connected",
                "hub_url": hub_url,
                "status": "listening",
                "library": "signalrcore"
            }), file=sys.stderr)

        def on_close():
            connection_state["connected"] = False
            print(json.dumps({
                "event": "disconnected",
                "hub_url": hub_url,
                "total_messages": connection_state["message_count"]
            }), file=sys.stderr)

        def on_error(error):
            connection_state["errors"].append(str(error))
            print(json.dumps({
                "event": "error",
                "error": str(error)
            }), file=sys.stderr)

        connection.on_open(on_open)
        connection.on_close(on_close)
        connection.on_error(on_error)

        async def handle_message(message):
            connection_state["message_count"] += 1
            print(json.dumps({
                "event": "message_received",
                "message_number": connection_state["message_count"],
                "data": message
            }), file=sys.stderr)

            if on_message_callback:
                try:
                    await on_message_callback(message)
                except Exception as e:
                    connection_state["errors"].append(str(e))
                    print(json.dumps({
                        "event": "callback_error",
                        "error": str(e),
                        "message": message
                    }), file=sys.stderr)

        connection.on(hub_name, handle_message)
        connection.start()

    else:
        # Use signalr-client library (more reliable async)
        import aiohttp

        # Custom connection with retry logic
        max_retries = 10
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # Create connection
                session = aiohttp.ClientSession()
                connection = Connection(hub_url, session)

                # Set up message handler
                def handle_message(*args):
                    """Handle incoming SignalR message."""
                    try:
                        message = args[0] if args else {}
                        connection_state["message_count"] += 1

                        print(json.dumps({
                            "event": "message_received",
                            "message_number": connection_state["message_count"],
                            "data": message
                        }), file=sys.stderr)

                        # Call callback (sync wrapper for async)
                        if on_message_callback:
                            asyncio.create_task(on_message_callback(message))

                    except Exception as e:
                        connection_state["errors"].append(str(e))
                        print(json.dumps({
                            "event": "message_handler_error",
                            "error": str(e)
                        }), file=sys.stderr)

                # Register hub method
                connection.received += handle_message

                # Start connection
                await connection.start()

                connection_state["connected"] = True
                print(json.dumps({
                    "event": "connected",
                    "hub_url": hub_url,
                    "status": "listening",
                    "library": "signalr-client",
                    "attempt": attempt + 1
                }), file=sys.stderr)

                break

            except Exception as e:
                connection_state["reconnect_attempts"] = attempt + 1
                connection_state["errors"].append(f"Connection attempt {attempt + 1}: {str(e)}")

                if attempt < max_retries - 1:
                    print(json.dumps({
                        "event": "connection_failed",
                        "attempt": attempt + 1,
                        "error": str(e),
                        "retry_in": retry_delay
                    }), file=sys.stderr)

                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)  # Exponential backoff
                else:
                    print(json.dumps({
                        "event": "connection_failed_permanently",
                        "total_attempts": max_retries,
                        "error": str(e)
                    }), file=sys.stderr)
                    raise

    return connection, connection_state


async def main():
    """
    Main function - connects to SignalR hub and processes messages.

    Input JSON:
    {
        "hub_url": "http://localhost:5000/taskhub",
        "hub_name": "TaskHub",  // optional, default: "TaskHub"
        "duration_seconds": 60,  // optional, how long to listen (default: run forever)
        "auto_generate_workflows": true,  // optional, default: true
        "output_file": "tasks.json"  // optional, save tasks to file
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
                    "hub_url": "http://localhost:5000/taskhub",
                    "duration_seconds": 60
                }
            }))
            return

        hub_name = input_data.get("hub_name", "TaskHub")
        duration = input_data.get("duration_seconds", None)
        auto_generate = input_data.get("auto_generate_workflows", True)
        output_file = input_data.get("output_file", None)

        # Store received tasks
        received_tasks = []

        # Task queue for sequential processing
        task_queue = asyncio.Queue()
        processing_active = True

        async def process_task_queue():
            """Process tasks sequentially, one at a time."""
            while processing_active:
                try:
                    # Wait for next task
                    message = await task_queue.get()

                    if message is None:  # Shutdown signal
                        break

                    print(json.dumps({
                        "event": "processing_task",
                        "task_id": message.get("id", "unknown"),
                        "queue_size": task_queue.qsize()
                    }), file=sys.stderr)

                    # Import here to avoid circular dependency
                    from node_runtime import call_tool
                    from src.node_runner import NodeRunner
                    from src.registry import Registry

                    try:
                        # Step 1: Route the task to workflow generator
                        workflow_result = call_tool(
                            "task_to_workflow_router",
                            json.dumps(message)
                        )

                        workflow_data = json.loads(workflow_result)

                        print(json.dumps({
                            "event": "workflow_generated",
                            "task_id": message.get("id"),
                            "workflow_name": workflow_data.get("workflow_name"),
                            "node_id": workflow_data.get("suggested_node_id")
                        }), file=sys.stderr)

                        # Step 2: Save the workflow as a node
                        runner = NodeRunner()
                        registry = Registry()

                        node_id = workflow_data.get("suggested_node_id", f"task_{message.get('id', 'unknown')}")
                        workflow_code = workflow_data.get("workflow_code", "")

                        runner.save_code(node_id, workflow_code)
                        registry.create_node(
                            node_id=node_id,
                            title=workflow_data.get("workflow_name", "Generated Workflow"),
                            tags=["signalr", "generated", message.get("llmTaskType", "unknown")]
                        )

                        print(json.dumps({
                            "event": "workflow_saved",
                            "node_id": node_id,
                            "task_id": message.get("id")
                        }), file=sys.stderr)

                        # Step 3: Optionally execute the workflow for testing
                        # (Only if enabled in config - for now just save it)

                    except Exception as e:
                        print(json.dumps({
                            "event": "workflow_processing_failed",
                            "task": message,
                            "error": str(e)
                        }), file=sys.stderr)

                    finally:
                        # Mark task as done
                        task_queue.task_done()

                        print(json.dumps({
                            "event": "task_completed",
                            "task_id": message.get("id", "unknown"),
                            "remaining_queue": task_queue.qsize()
                        }), file=sys.stderr)

                except Exception as e:
                    print(json.dumps({
                        "event": "queue_processor_error",
                        "error": str(e)
                    }), file=sys.stderr)

        async def on_message(message):
            """Handle incoming task messages - add to queue for sequential processing."""
            received_tasks.append(message)

            # Add to queue if auto-generation enabled
            if auto_generate:
                await task_queue.put(message)

                print(json.dumps({
                    "event": "task_queued",
                    "task_id": message.get("id", "unknown"),
                    "queue_size": task_queue.qsize()
                }), file=sys.stderr)

        # Connect to hub
        connection, state = await connect_to_hub(hub_url, hub_name, on_message)

        # Start queue processor task
        queue_processor = None
        if auto_generate:
            queue_processor = asyncio.create_task(process_task_queue())

        # Listen for specified duration or forever
        try:
            if duration:
                await asyncio.sleep(duration)
            else:
                # Run forever (until Ctrl+C)
                while True:
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            print(json.dumps({"event": "shutdown_requested"}), file=sys.stderr)
        finally:
            # Stop connection
            if USE_SIGNALRCORE:
                connection.stop()
            else:
                await connection.stop()

            # Stop queue processor
            if queue_processor:
                processing_active = False
                await task_queue.put(None)  # Send shutdown signal
                await queue_processor  # Wait for processor to finish

        # Save tasks to file if requested
        if output_file and received_tasks:
            output_path = Path(output_file)
            output_path.write_text(json.dumps(received_tasks, indent=2), encoding='utf-8')

        # Output final summary
        print(json.dumps({
            "success": True,
            "hub_url": hub_url,
            "hub_name": hub_name,
            "total_messages": state["message_count"],
            "tasks_received": len(received_tasks),
            "errors": state["errors"],
            "tasks": received_tasks
        }))

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "success": False
        }))


if __name__ == "__main__":
    asyncio.run(main())
