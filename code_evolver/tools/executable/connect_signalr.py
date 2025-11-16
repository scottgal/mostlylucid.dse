#!/usr/bin/env python3
"""
Connect SignalR (Natural Language)

Simple wrapper that lets you connect to SignalR hubs using natural language.

Just say: "connect to http://localhost:5000/hub and create workflows"
"""
import json
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """
    Connect to SignalR hub using natural language request.

    Input JSON:
    {
        "request": "connect to http://localhost:5000/taskhub with hub context TaskHub and create workflows"
    }

    Or simple string:
    "connect to http://localhost:5000/taskhub and create workflows"
    """
    try:
        # Read input
        input_text = sys.stdin.read().strip()

        # Try to parse as JSON first
        try:
            input_data = json.loads(input_text)
            request = input_data.get("request", input_text)
        except json.JSONDecodeError:
            # Treat as plain text request
            request = input_text

        if not request:
            print(json.dumps({
                "error": "No request provided",
                "success": False,
                "usage": "Provide a natural language request like: 'connect to http://localhost:5000/hub and create workflows'"
            }))
            return

        # Step 1: Parse natural language request
        print(json.dumps({
            "step": 1,
            "action": "parsing_request",
            "request": request
        }), file=sys.stderr)

        from node_runtime import call_tool

        # Parse with LLM
        config_json = call_tool("signalr_connection_parser", request)

        print(json.dumps({
            "step": 2,
            "action": "parsed_config",
            "config": json.loads(config_json)
        }), file=sys.stderr)

        # Step 2: Connect to SignalR hub
        print(json.dumps({
            "step": 3,
            "action": "connecting_to_hub"
        }), file=sys.stderr)

        # Call SignalR connector with parsed config
        result = call_tool("signalr_hub_connector", config_json)

        # Output result
        print(result)

    except KeyboardInterrupt:
        print(json.dumps({
            "event": "interrupted",
            "success": False
        }))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "success": False
        }))


if __name__ == "__main__":
    main()
