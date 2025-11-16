#!/usr/bin/env python3
"""
Stream Processor

Connects a stream producer to a consumer tool with filtering and transformation.
"""

import json
import sys
import subprocess
import time
import signal
from datetime import datetime
from typing import Optional, Dict, Any, Callable


class StreamProcessor:
    """Stream processor that connects producers to consumers."""

    def __init__(
        self,
        producer: str,
        producer_input: Dict[str, Any],
        consumer: str,
        filter_expr: Optional[str] = None,
        transform_expr: Optional[str] = None,
        sequential: bool = True,
        max_items: int = 0,
        timeout_seconds: int = 0
    ):
        self.producer = producer
        self.producer_input = producer_input
        self.consumer = consumer
        self.filter_expr = filter_expr
        self.transform_expr = transform_expr
        self.sequential = sequential
        self.max_items = max_items
        self.timeout_seconds = timeout_seconds

        # Statistics
        self.total_events = 0
        self.filtered_events = 0
        self.processed_events = 0
        self.failed_events = 0
        self.start_time = time.time()

        self.running = True

    def evaluate_filter(self, event: Dict[str, Any]) -> bool:
        """Evaluate filter expression against event."""
        if not self.filter_expr:
            return True

        try:
            # Create evaluation context with event fields
            context = {
                'event_type': event.get('event_type'),
                'event_name': event.get('event_name'),
                'data': event.get('data'),
                'id': event.get('id'),
                'timestamp': event.get('timestamp'),
                'sequence': event.get('sequence')
            }

            # Evaluate filter expression
            result = eval(self.filter_expr, {"__builtins__": {}}, context)
            return bool(result)

        except Exception as e:
            print(f"Filter error: {e}", file=sys.stderr)
            return False

    def evaluate_transform(self, event: Dict[str, Any]) -> Any:
        """Evaluate transform expression against event."""
        if not self.transform_expr:
            return event

        try:
            # Create evaluation context with event fields
            context = {
                'event_type': event.get('event_type'),
                'event_name': event.get('event_name'),
                'data': event.get('data'),
                'id': event.get('id'),
                'timestamp': event.get('timestamp'),
                'sequence': event.get('sequence'),
                'event': event  # Full event available as 'event'
            }

            # Evaluate transform expression
            result = eval(self.transform_expr, {"__builtins__": {}}, context)
            return result

        except Exception as e:
            print(f"Transform error: {e}", file=sys.stderr)
            return event

    def call_consumer(self, data: Any) -> bool:
        """Call consumer tool with data."""
        try:
            # Import node_runtime to call tools
            sys.path.insert(0, '.')
            from node_runtime import call_tool

            # Prepare consumer input
            consumer_input = json.dumps(data)

            # Call consumer tool
            result = call_tool(self.consumer, consumer_input)

            print(f"Consumer result: {result[:200]}", file=sys.stderr)
            return True

        except Exception as e:
            print(f"Consumer error: {e}", file=sys.stderr)
            return False

    def check_limits(self) -> Optional[str]:
        """Check if processing limits have been reached."""
        # Check max items
        if self.max_items > 0 and self.processed_events >= self.max_items:
            return "max_items_reached"

        # Check timeout
        if self.timeout_seconds > 0:
            elapsed = time.time() - self.start_time
            if elapsed >= self.timeout_seconds:
                return "timeout_reached"

        return None

    def process_stream(self):
        """Process stream from producer."""
        try:
            # Prepare producer command
            # Assume tools are in tools/executable/ directory
            producer_script = f"tools/executable/{self.producer}.py"

            # Start producer process
            producer_proc = subprocess.Popen(
                ["python", producer_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )

            # Send producer input
            producer_input_json = json.dumps(self.producer_input)
            producer_proc.stdin.write(producer_input_json)
            producer_proc.stdin.close()

            # Process stream output
            for line in producer_proc.stdout:
                if not self.running:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse event
                    event = json.loads(line)
                    self.total_events += 1

                    # Check filter
                    if not self.evaluate_filter(event):
                        continue

                    self.filtered_events += 1

                    # Transform data
                    transformed_data = self.evaluate_transform(event)

                    # Call consumer
                    success = self.call_consumer(transformed_data)

                    if success:
                        self.processed_events += 1
                    else:
                        self.failed_events += 1

                    # Check limits
                    limit_reason = self.check_limits()
                    if limit_reason:
                        self.shutdown(limit_reason)
                        break

                except json.JSONDecodeError as e:
                    print(f"Invalid JSON from producer: {line}", file=sys.stderr)
                    continue

                except Exception as e:
                    print(f"Error processing event: {e}", file=sys.stderr)
                    self.failed_events += 1

            # Wait for producer to finish
            producer_proc.wait(timeout=5)

        except subprocess.TimeoutExpired:
            producer_proc.kill()
            self.shutdown("producer_timeout")

        except Exception as e:
            print(f"Stream processing error: {e}", file=sys.stderr)
            self.shutdown("error")

    def shutdown(self, reason: str):
        """Shutdown processor and output summary."""
        self.running = False

        duration = time.time() - self.start_time

        summary = {
            "total_events": self.total_events,
            "filtered_events": self.filtered_events,
            "processed_events": self.processed_events,
            "failed_events": self.failed_events,
            "duration_seconds": round(duration, 2),
            "shutdown_reason": reason
        }

        print(json.dumps(summary, indent=2))

    def run(self):
        """Run the stream processor."""
        try:
            self.process_stream()

            # Normal shutdown
            if self.running:
                self.shutdown("stream_ended")

        except KeyboardInterrupt:
            self.shutdown("interrupted")

        except Exception as e:
            print(f"Fatal error: {e}", file=sys.stderr)
            self.shutdown("fatal_error")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(json.dumps({
        "total_events": 0,
        "filtered_events": 0,
        "processed_events": 0,
        "failed_events": 0,
        "duration_seconds": 0,
        "shutdown_reason": f"signal_{signum}"
    }), flush=True)
    sys.exit(0)


def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Read input from stdin
        input_text = sys.stdin.read().strip()

        # Parse input JSON
        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "error": f"Invalid JSON input: {str(e)}"
            }), file=sys.stderr)
            sys.exit(1)

        # Extract parameters
        producer = input_data.get("producer")
        producer_input = input_data.get("producer_input")
        consumer = input_data.get("consumer")

        if not producer or not producer_input or not consumer:
            print(json.dumps({
                "error": "Missing required parameters: producer, producer_input, consumer"
            }), file=sys.stderr)
            sys.exit(1)

        # Create processor
        processor = StreamProcessor(
            producer=producer,
            producer_input=producer_input,
            consumer=consumer,
            filter_expr=input_data.get("filter"),
            transform_expr=input_data.get("transform"),
            sequential=input_data.get("sequential", True),
            max_items=input_data.get("max_items", 0),
            timeout_seconds=input_data.get("timeout_seconds", 0)
        )

        # Run processor
        processor.run()

    except Exception as e:
        print(json.dumps({
            "error": f"Fatal error: {str(e)}"
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
