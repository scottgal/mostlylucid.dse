#!/usr/bin/env python3
"""
SignalR LLMApi Skill

Orchestrates SignalR LLMApi operations by:
1. Using signalr_llmapi_management (LLM) to plan operations
2. Executing HTTP operations
3. Calling sse_stream for streaming
4. Optionally routing to consumer via stream_processor
"""

import json
import sys
import urllib.request
import urllib.error


def call_management_tool(request, base_url):
    """Call the LLM management tool to get execution plan."""
    try:
        # Import node_runtime
        sys.path.insert(0, '.')
        from node_runtime import call_tool

        # Call management LLM tool
        management_input = json.dumps({
            "request": request,
            "base_url": base_url
        })

        result = call_tool("signalr_llmapi_management", management_input)

        # Parse result
        plan = json.loads(result)
        return plan

    except Exception as e:
        return {
            "error": f"Failed to get execution plan: {str(e)}",
            "operations": [],
            "streaming": False
        }


def execute_http_operation(operation):
    """Execute an HTTP operation by calling http_request tool."""
    try:
        sys.path.insert(0, '.')
        from node_runtime import call_tool

        # Prepare HTTP request tool input
        http_input = {
            "method": operation.get("method", "GET"),
            "url": operation["url"],
            "headers": {"Content-Type": "application/json"}
        }

        # Add body if present
        if operation.get("body"):
            http_input["body"] = operation["body"]

        # Call HTTP tool
        result = call_tool("http_request", json.dumps(http_input))

        try:
            result_data = json.loads(result)
        except:
            result_data = {"data": result}

        return {
            "operation": operation.get("description", "HTTP operation"),
            "data": result_data,
            "success": True
        }

    except Exception as e:
        return {
            "operation": operation.get("description", "HTTP operation"),
            "error": str(e),
            "success": False
        }


def execute_signalr_stream(operation, consumer, max_items, timeout_seconds):
    """Execute SignalR/SSE streaming operation by calling stream tools."""
    try:
        sys.path.insert(0, '.')
        from node_runtime import call_tool

        # Determine which stream tool to use based on URL/context
        # For LLMApi SignalR simulator, use SSE stream
        stream_producer = "sse_stream"

        # Prepare stream input
        stream_input = {
            "url": operation["url"],
            "reconnect": False  # Don't auto-reconnect for this use case
        }

        # If consumer specified, use stream_processor to route
        if consumer:
            # Use stream processor to connect producer to consumer
            processor_input = {
                "producer": stream_producer,
                "producer_input": stream_input,
                "consumer": consumer,
                "filter": "event_type == 'data'",  # Only pass data events
                "max_items": max_items,
                "timeout_seconds": timeout_seconds
            }

            result = call_tool("stream_processor", json.dumps(processor_input))
            summary = json.loads(result)

        else:
            # Just run stream directly (will output events to stdout)
            # Limit to avoid infinite streaming
            if max_items == 0:
                max_items = 10  # Default limit

            processor_input = {
                "producer": stream_producer,
                "producer_input": stream_input,
                "consumer": "json_logger",  # Simple logger (or create one)
                "max_items": max_items,
                "timeout_seconds": timeout_seconds if timeout_seconds > 0 else 30
            }

            result = call_tool("stream_processor", json.dumps(processor_input))
            summary = json.loads(result)

        return summary

    except Exception as e:
        return {
            "error": f"Streaming failed: {str(e)}",
            "total_events": 0,
            "success": False
        }


def main():
    """Main entry point."""
    try:
        # Read input
        input_text = sys.stdin.read().strip()

        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "error": f"Invalid JSON input: {str(e)}",
                "success": False
            }))
            sys.exit(1)

        # Extract parameters
        request = input_data.get("request")
        base_url = input_data.get("base_url", "http://127.0.0.1:5116")
        consumer = input_data.get("consumer")
        max_stream_items = input_data.get("max_stream_items", 0)
        stream_timeout_seconds = input_data.get("stream_timeout_seconds", 0)

        if not request:
            print(json.dumps({
                "error": "Missing required parameter: request",
                "success": False
            }))
            sys.exit(1)

        # Step 1: Get execution plan from management LLM
        plan = call_management_tool(request, base_url)

        if "error" in plan:
            print(json.dumps({
                "error": plan["error"],
                "success": False
            }))
            sys.exit(1)

        # Step 2: Execute operations
        operations_executed = []
        http_results = []
        stream_summary = None

        for operation in plan.get("operations", []):
            op_type = operation.get("type", "http")

            if op_type == "http":
                # Execute HTTP operation
                result = execute_http_operation(operation)
                http_results.append(result)
                operations_executed.append(
                    f"{operation['method']} {operation['url']}"
                )

                # Log result
                print(f"[HTTP] {operation.get('description')}: " +
                      f"{'SUCCESS' if result.get('success') else 'FAILED'}",
                      file=sys.stderr)

            elif op_type == "sse_stream":
                # Execute SignalR/SSE streaming
                print(f"[Stream] Starting stream from {operation['url']}...",
                      file=sys.stderr)

                stream_summary = execute_signalr_stream(
                    operation,
                    consumer,
                    max_stream_items,
                    stream_timeout_seconds
                )
                operations_executed.append(f"stream:{operation['url']}")

                print(f"[Stream] Stream ended. Events: " +
                      f"{stream_summary.get('total_events', 0)}",
                      file=sys.stderr)

        # Step 3: Build result
        result = {
            "operations_executed": operations_executed,
            "http_results": http_results,
            "stream_summary": stream_summary,
            "success": all(r.get("success", False) for r in http_results) if http_results else True,
            "message": f"Executed {len(operations_executed)} operations successfully"
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": f"Fatal error: {str(e)}",
            "success": False
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
