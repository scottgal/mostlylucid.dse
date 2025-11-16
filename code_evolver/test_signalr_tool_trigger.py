#!/usr/bin/env python3
"""
Test SignalR Tool Trigger functionality (without requiring actual SignalR connection)

This tests the message processing logic.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_message_processing():
    """
    Test that the tool can process different message types correctly.
    """
    print("=" * 60)
    print("SignalR Tool Trigger - Message Processing Tests")
    print("=" * 60)

    # Test messages (what would come from SignalR hub)
    test_messages = [
        {
            "name": "Trigger Tool - Fake Data Generator",
            "message": {
                "action": "trigger_tool",
                "tool_id": "fake_data_generator",
                "parameters": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string", "format": "email"}
                        }
                    },
                    "count": 1
                },
                "task_id": "test-fake-data"
            }
        },
        {
            "name": "Trigger Tool - Smart API Parser (Dry Run)",
            "message": {
                "action": "trigger_tool",
                "tool_id": "smart_api_parser",
                "parameters": {
                    "openapi_spec": {
                        "openapi": "3.0.0",
                        "info": {"title": "Test API", "version": "1.0"},
                        "servers": [{"url": "http://localhost:3000"}],
                        "paths": {
                            "/users": {
                                "get": {
                                    "operationId": "getUsers",
                                    "summary": "Get all users",
                                    "responses": {"200": {"description": "Success"}}
                                }
                            }
                        }
                    },
                    "make_requests": False
                },
                "task_id": "test-api-parser"
            }
        },
        {
            "name": "Trigger Tool - LLM Data Generator",
            "message": {
                "action": "trigger_tool",
                "tool_id": "llm_fake_data_generator",
                "parameters": {
                    "schema_json": json.dumps({
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string"},
                            "price": {"type": "number"}
                        }
                    }),
                    "additional_context": "E-commerce product catalog"
                },
                "task_id": "test-llm-data"
            }
        }
    ]

    # Simulate processing each message
    from node_runtime import call_tool

    results = []

    for test_case in test_messages:
        print(f"\n{'-' * 60}")
        print(f"Test: {test_case['name']}")
        print(f"{'  ' * 60}")

        message = test_case['message']
        action = message.get('action')
        task_id = message.get('task_id')

        try:
            if action == 'trigger_tool':
                tool_id = message.get('tool_id')
                parameters = message.get('parameters', {})

                print(f"  Action: {action}")
                print(f"  Tool: {tool_id}")
                print(f"  Task ID: {task_id}")

                # Trigger the tool
                print(f"\n  Triggering tool '{tool_id}'...")

                result = call_tool(tool_id, json.dumps(parameters), disable_tracking=True)

                # Parse result
                try:
                    result_data = json.loads(result)
                    success = result_data.get('success', True)

                    print(f"  Result: {'SUCCESS' if success else 'FAILED'}")

                    # Show sample of result
                    if isinstance(result_data, dict):
                        keys = list(result_data.keys())[:5]
                        print(f"  Output keys: {keys}")

                        # Show data if available
                        if 'data' in result_data:
                            data = result_data['data']
                            if isinstance(data, str):
                                print(f"  Data (truncated): {data[:100]}...")
                            elif isinstance(data, dict):
                                print(f"  Data: {json.dumps(data, indent=4)[:200]}...")
                            elif isinstance(data, list):
                                print(f"  Data: {len(data)} items")
                                if data:
                                    print(f"  First item: {json.dumps(data[0], indent=4)[:150]}...")

                        # Show API info if available
                        if 'api_info' in result_data:
                            api_info = result_data['api_info']
                            print(f"  API: {api_info.get('title', 'Unknown')}")

                        if 'total_endpoints' in result_data:
                            print(f"  Endpoints: {result_data['total_endpoints']}")

                    results.append({
                        "test": test_case['name'],
                        "task_id": task_id,
                        "tool_id": tool_id,
                        "success": success,
                        "result_length": len(result)
                    })

                except json.JSONDecodeError:
                    # Non-JSON result
                    print(f"  Result (text): {result[:200]}...")
                    results.append({
                        "test": test_case['name'],
                        "task_id": task_id,
                        "tool_id": tool_id,
                        "success": True,
                        "result_length": len(result)
                    })

            elif action == 'generate_workflow':
                # Would call task_to_workflow_router
                print(f"  Action: {action}")
                print(f"  (Skipping workflow generation test for now)")

            elif action == 'create_tool':
                # Would parse OpenAPI and create tool
                print(f"  Action: {action}")
                print(f"  (Skipping tool creation test for now)")

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "test": test_case['name'],
                "task_id": task_id,
                "success": False,
                "error": str(e)
            })

    # Summary
    print(f"\n{'=' * 60}")
    print("Test Summary")
    print(f"{'=' * 60}")

    successful = sum(1 for r in results if r.get('success', False))
    failed = len(results) - successful

    print(f"\nTotal tests: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if successful == len(results):
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed")
        for result in results:
            if not result.get('success', False):
                print(f"  - {result['test']}: {result.get('error', 'Unknown error')}")

    print(f"\n{'=' * 60}")
    print("Note: This test simulates SignalR message processing")
    print("To test with real SignalR hub:")
    print("  1. Set up SignalR hub on your server")
    print("  2. Run: echo '{\"hub_url\": \"http://localhost:5000/toolhub\"}' | python tools/executable/signalr_tool_trigger.py")
    print("  3. Send messages from your hub")
    print(f"{'=' * 60}")

    return results


if __name__ == "__main__":
    try:
        test_message_processing()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
