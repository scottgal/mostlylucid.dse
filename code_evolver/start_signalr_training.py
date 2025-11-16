#!/usr/bin/env python3
"""
SignalR Training Launcher

Simple script to start SignalR training - just configure and run!

Usage:
    python start_signalr_training.py

Or with custom settings:
    python start_signalr_training.py --hub-url http://localhost:5000/taskhub --duration 300
"""
import asyncio
import json
import sys
from pathlib import Path
import argparse

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def main():
    """Start SignalR training with configuration."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Start SignalR training for Code Evolver',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Connect to local hub and train forever
  python start_signalr_training.py

  # Connect with custom URL
  python start_signalr_training.py --hub-url http://prod:8080/llmhub

  # Train for 5 minutes only
  python start_signalr_training.py --duration 300

  # Specify hub context
  python start_signalr_training.py --hub-name LLMTasks

  # Save received tasks to file
  python start_signalr_training.py --output tasks.json

  # All together
  python start_signalr_training.py \\
    --hub-url http://prod:8080/llmhub \\
    --hub-name LLMTasks \\
    --duration 300 \\
    --output tasks.json
        '''
    )

    parser.add_argument(
        '--hub-url',
        type=str,
        default='http://localhost:5000/taskhub',
        help='SignalR hub URL (default: http://localhost:5000/taskhub)'
    )

    parser.add_argument(
        '--hub-name',
        type=str,
        default='TaskHub',
        help='Hub method/context name (default: TaskHub)'
    )

    parser.add_argument(
        '--duration',
        type=int,
        default=None,
        help='How long to listen in seconds (default: forever)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Save received tasks to JSON file (optional)'
    )

    parser.add_argument(
        '--no-auto-generate',
        action='store_true',
        help='Disable automatic workflow generation (just receive tasks)'
    )

    args = parser.parse_args()

    # Display welcome banner
    print("=" * 70)
    print("  SignalR Training Launcher for Code Evolver")
    print("=" * 70)
    print()
    print(f"Hub URL:          {args.hub_url}")
    print(f"Hub Name:         {args.hub_name}")
    print(f"Duration:         {'Forever (Ctrl+C to stop)' if args.duration is None else f'{args.duration} seconds'}")
    print(f"Auto-Generate:    {'Yes' if not args.no_auto_generate else 'No (receive only)'}")
    print(f"Save Tasks:       {args.output if args.output else 'No'}")
    print()
    print("=" * 70)
    print()

    # Import SignalR connector
    try:
        sys.path.insert(0, str(Path(__file__).parent / "tools" / "executable"))
        from signalr_hub_connector import connect_to_hub, Queue
        from node_runtime import call_tool
        from src.node_runner import NodeRunner
        from src.registry import Registry
    except ImportError as e:
        print(f"❌ Error: Failed to import required modules: {e}")
        print()
        print("Make sure you're running this from the code_evolver directory!")
        return

    # Create task queue and state
    received_tasks = []
    task_queue = asyncio.Queue()
    processing_active = True

    # Task processor
    async def process_task_queue():
        """Process tasks sequentially."""
        task_count = 0

        while processing_active:
            try:
                message = await task_queue.get()

                if message is None:  # Shutdown signal
                    break

                task_count += 1
                task_id = message.get("id", f"task-{task_count}")

                print()
                print(f"[Task {task_count}] Processing: {task_id}")
                print(f"              Type: {message.get('llmTaskType', 'unknown')}")
                print(f"              Queue: {task_queue.qsize()} waiting")
                print()

                # Generate workflow
                print("  → Step 1: Generating workflow code...")
                workflow_result = call_tool(
                    "task_to_workflow_router",
                    json.dumps(message)
                )

                workflow_data = json.loads(workflow_result)
                node_id = workflow_data.get("suggested_node_id", f"task_{task_id}")
                workflow_name = workflow_data.get("workflow_name", "Generated Workflow")

                print(f"  → Step 2: Saving node '{node_id}'...")

                # Save workflow
                runner = NodeRunner()
                registry = Registry()

                runner.save_code(node_id, workflow_data.get("workflow_code", ""))
                registry.create_node(
                    node_id=node_id,
                    title=workflow_name,
                    tags=["signalr", "generated", message.get("llmTaskType", "unknown")]
                )

                print(f"  ✓ Completed: Workflow saved as 'nodes/{node_id}/main.py'")
                print()

                task_queue.task_done()

            except Exception as e:
                print(f"  ❌ Error processing task: {e}")
                print()

    # Message handler
    async def on_message(message):
        """Handle incoming messages."""
        received_tasks.append(message)

        if not args.no_auto_generate:
            await task_queue.put(message)

            print(f"[New Task] ID: {message.get('id', 'unknown')}")
            print(f"           Type: {message.get('llmTaskType', 'unknown')}")
            print(f"           Queue Size: {task_queue.qsize()}")

    # Connect to hub
    print("Connecting to SignalR hub...")
    print()

    try:
        connection, state = await connect_to_hub(
            args.hub_url,
            args.hub_name,
            on_message
        )

        # Start queue processor
        queue_processor = None
        if not args.no_auto_generate:
            queue_processor = asyncio.create_task(process_task_queue())
            print("✓ Workflow generator started (processing one task at a time)")
            print()

        print("✓ Connected! Listening for tasks...")
        print("  (Press Ctrl+C to stop)")
        print()

        # Listen for duration or forever
        try:
            if args.duration:
                await asyncio.sleep(args.duration)
            else:
                while True:
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            print()
            print("Shutdown requested...")

        # Stop
        print("Disconnecting...")
        # connection.stop() # Will be handled by connector

        # Stop queue processor
        if queue_processor:
            processing_active = False
            await task_queue.put(None)
            print("Waiting for current task to finish...")
            await queue_processor

        # Save tasks if requested
        if args.output and received_tasks:
            output_path = Path(args.output)
            output_path.write_text(
                json.dumps(received_tasks, indent=2),
                encoding='utf-8'
            )
            print(f"✓ Saved {len(received_tasks)} tasks to {args.output}")

        # Summary
        print()
        print("=" * 70)
        print("  Training Session Complete")
        print("=" * 70)
        print(f"  Total Tasks Received: {len(received_tasks)}")
        print(f"  Workflows Generated: {len(received_tasks) if not args.no_auto_generate else 0}")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Common issues:")
        print("  - Hub URL incorrect or unreachable")
        print("  - Hub not running")
        print("  - Missing dependencies: pip install signalr-client aiohttp")
        sys.exit(1)


if __name__ == "__main__":
    # Check dependencies
    try:
        import signalr
    except ImportError:
        try:
            import signalrcore
        except ImportError:
            print("❌ Error: SignalR client library not installed")
            print()
            print("Install with:")
            print("  pip install signalr-client aiohttp")
            print("  OR")
            print("  pip install signalrcore")
            sys.exit(1)

    # Run
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted!")
