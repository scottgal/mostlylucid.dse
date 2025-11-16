#!/usr/bin/env python3
"""
SignalR WebSocket Stream Producer

Connects to a SignalR hub via WebSocket and streams data continuously.
Each message is output as a JSON line to stdout.
"""

import json
import sys
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import signal

# Try to import signalrcore (preferred WebSocket library)
try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
    HAS_SIGNALRCORE = True
except ImportError:
    HAS_SIGNALRCORE = False
    print(json.dumps({
        "event_type": "error",
        "data": {"error": "signalrcore not installed. Run: pip install signalrcore"},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sequence": 0
    }), file=sys.stderr)
    sys.exit(1)


class SignalRWebSocketStream:
    """SignalR WebSocket stream producer."""

    def __init__(
        self,
        url: str,
        context_name: str,
        output_format: str = "json",
        reconnect: bool = True,
        max_reconnect_attempts: int = 10
    ):
        self.url = url
        self.context_name = context_name
        self.output_format = output_format
        self.reconnect = reconnect
        self.max_reconnect_attempts = max_reconnect_attempts

        self.connection = None
        self.sequence = 0
        self.running = True
        self.reconnect_count = 0

    def emit_event(self, event_type: str, data: Optional[Any] = None):
        """Emit a stream event to stdout."""
        event = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sequence": self.sequence
        }
        self.sequence += 1

        print(json.dumps(event), flush=True)

    def on_message(self, message):
        """Handle incoming message from SignalR hub."""
        try:
            # Parse message if it's JSON string
            if isinstance(message, str):
                try:
                    message_data = json.loads(message)
                except json.JSONDecodeError:
                    message_data = {"raw": message}
            else:
                message_data = message

            self.emit_event("message", message_data)

        except Exception as e:
            self.emit_event("error", {
                "error": f"Failed to process message: {str(e)}",
                "message": str(message)
            })

    def on_open(self):
        """Handle connection open."""
        self.emit_event("connected", {
            "url": self.url,
            "context": self.context_name
        })
        self.reconnect_count = 0

    def on_close(self):
        """Handle connection close."""
        self.emit_event("disconnected", {
            "reconnect_count": self.reconnect_count
        })

    def on_error(self, error):
        """Handle connection error."""
        self.emit_event("error", {
            "error": str(error),
            "reconnect_count": self.reconnect_count
        })

    async def connect(self):
        """Establish SignalR WebSocket connection."""
        try:
            # Build hub connection
            self.connection = HubConnectionBuilder() \
                .with_url(self.url) \
                .with_automatic_reconnect({
                    "type": "raw",
                    "keep_alive_interval": 10,
                    "reconnect_interval": 5,
                    "max_attempts": self.max_reconnect_attempts if self.reconnect else 0
                }) \
                .build()

            # Register event handlers
            self.connection.on_open(self.on_open)
            self.connection.on_close(self.on_close)
            self.connection.on_error(self.on_error)

            # Subscribe to the specified context/method
            self.connection.on(self.context_name, self.on_message)

            # Start connection
            self.connection.start()

            # Keep connection alive
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            self.emit_event("shutdown", {"reason": "Interrupted by user"})
            self.running = False

        except Exception as e:
            self.emit_event("error", {
                "error": f"Connection failed: {str(e)}",
                "fatal": True
            })
            self.running = False

        finally:
            if self.connection:
                try:
                    self.connection.stop()
                except:
                    pass

    async def run(self):
        """Run the stream."""
        while self.running:
            try:
                await self.connect()

                # If reconnect disabled or max attempts reached, exit
                if not self.reconnect:
                    break

                if self.max_reconnect_attempts > 0 and \
                   self.reconnect_count >= self.max_reconnect_attempts:
                    self.emit_event("shutdown", {
                        "reason": "Max reconnect attempts reached",
                        "attempts": self.reconnect_count
                    })
                    break

                # Wait before reconnecting
                if self.running:
                    self.reconnect_count += 1
                    wait_time = min(2 ** self.reconnect_count, 30)  # Exponential backoff

                    self.emit_event("reconnecting", {
                        "attempt": self.reconnect_count,
                        "wait_seconds": wait_time
                    })

                    await asyncio.sleep(wait_time)

            except Exception as e:
                self.emit_event("error", {
                    "error": f"Stream error: {str(e)}",
                    "fatal": not self.reconnect
                })

                if not self.reconnect:
                    break


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(json.dumps({
        "event_type": "shutdown",
        "data": {"reason": "Signal received", "signal": signum},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sequence": -1
    }), flush=True)
    sys.exit(0)


async def main():
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
                "event_type": "error",
                "data": {"error": f"Invalid JSON input: {str(e)}"},
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sequence": 0
            }), file=sys.stderr)
            sys.exit(1)

        # Extract parameters
        url = input_data.get("url")
        context_name = input_data.get("context_name")

        if not url or not context_name:
            print(json.dumps({
                "event_type": "error",
                "data": {"error": "Missing required parameters: url, context_name"},
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sequence": 0
            }), file=sys.stderr)
            sys.exit(1)

        # Create stream
        stream = SignalRWebSocketStream(
            url=url,
            context_name=context_name,
            output_format=input_data.get("output_format", "json"),
            reconnect=input_data.get("reconnect", True),
            max_reconnect_attempts=input_data.get("max_reconnect_attempts", 10)
        )

        # Run stream
        await stream.run()

    except Exception as e:
        print(json.dumps({
            "event_type": "error",
            "data": {"error": f"Fatal error: {str(e)}"},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sequence": -1
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
