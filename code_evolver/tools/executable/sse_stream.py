#!/usr/bin/env python3
"""
SSE (Server-Sent Events) Stream Producer

Connects to an SSE endpoint and streams events continuously.
Each event is output as a JSON line to stdout.
"""

import json
import sys
import time
import signal
from datetime import datetime
from typing import Optional, Dict, Any
import urllib.request
import urllib.error


class SSEStreamProducer:
    """SSE stream producer."""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        reconnect: bool = True,
        max_reconnect_attempts: int = 10,
        reconnect_delay_seconds: int = 2
    ):
        self.url = url
        self.headers = headers or {}
        self.reconnect = reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay_seconds = reconnect_delay_seconds

        self.sequence = 0
        self.running = True
        self.reconnect_count = 0
        self.last_event_id = None

    def emit_event(self, event_type: str, event_name: Optional[str] = None,
                   data: Optional[Any] = None, event_id: Optional[str] = None):
        """Emit a stream event to stdout."""
        event = {
            "event_type": event_type,
            "event_name": event_name,
            "data": data,
            "id": event_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sequence": self.sequence
        }
        self.sequence += 1

        print(json.dumps(event), flush=True)

    def parse_sse_line(self, line: str, current_event: Dict[str, Any]):
        """Parse a single SSE line and update current event."""
        line = line.rstrip('\n\r')

        if not line:
            # Empty line = end of event
            return True

        if line.startswith(':'):
            # Comment line, ignore
            return False

        if ':' in line:
            field, _, value = line.partition(':')
            value = value.lstrip(' ')  # Remove leading space after colon

            if field == 'event':
                current_event['event_name'] = value
            elif field == 'data':
                # Accumulate data (multi-line data support)
                if 'data' in current_event:
                    current_event['data'] += '\n' + value
                else:
                    current_event['data'] = value
            elif field == 'id':
                current_event['id'] = value
                self.last_event_id = value
            elif field == 'retry':
                try:
                    self.reconnect_delay_seconds = int(value) // 1000  # Convert ms to seconds
                except ValueError:
                    pass

        return False

    def connect(self):
        """Connect to SSE endpoint and process events."""
        try:
            # Prepare request
            req = urllib.request.Request(self.url)
            req.add_header('Accept', 'text/event-stream')
            req.add_header('Cache-Control', 'no-cache')

            # Add custom headers
            for key, value in self.headers.items():
                req.add_header(key, value)

            # Add Last-Event-ID if we're reconnecting
            if self.last_event_id:
                req.add_header('Last-Event-ID', self.last_event_id)

            # Open connection
            response = urllib.request.urlopen(req, timeout=None)

            # Emit connected event
            self.emit_event("connected", data={
                "url": self.url,
                "status": response.status
            })
            self.reconnect_count = 0

            # Process stream
            current_event = {}

            for line in response:
                if not self.running:
                    break

                line = line.decode('utf-8')

                # Parse line
                is_complete = self.parse_sse_line(line, current_event)

                if is_complete and current_event:
                    # Event complete, emit it
                    event_name = current_event.get('event_name', 'message')
                    raw_data = current_event.get('data', '')
                    event_id = current_event.get('id')

                    # Try to parse data as JSON
                    try:
                        data = json.loads(raw_data)
                    except (json.JSONDecodeError, TypeError):
                        data = raw_data

                    self.emit_event(
                        event_type="data",
                        event_name=event_name,
                        data=data,
                        event_id=event_id
                    )

                    # Reset for next event
                    current_event = {}

        except urllib.error.HTTPError as e:
            self.emit_event("error", data={
                "error": f"HTTP {e.code}: {e.reason}",
                "url": self.url
            })
            raise

        except urllib.error.URLError as e:
            self.emit_event("error", data={
                "error": f"Connection error: {str(e.reason)}",
                "url": self.url
            })
            raise

        except KeyboardInterrupt:
            self.emit_event("shutdown", data={"reason": "Interrupted by user"})
            self.running = False
            raise

        except Exception as e:
            self.emit_event("error", data={
                "error": f"Stream error: {str(e)}",
                "url": self.url
            })
            raise

        finally:
            try:
                response.close()
            except:
                pass

    def run(self):
        """Run the stream with reconnection logic."""
        while self.running:
            try:
                self.connect()

                # If we get here, connection closed gracefully
                self.emit_event("disconnected", data={
                    "reconnect_count": self.reconnect_count
                })

                # Check if we should reconnect
                if not self.reconnect:
                    break

                if self.max_reconnect_attempts > 0 and \
                   self.reconnect_count >= self.max_reconnect_attempts:
                    self.emit_event("shutdown", data={
                        "reason": "Max reconnect attempts reached",
                        "attempts": self.reconnect_count
                    })
                    break

                # Wait before reconnecting (exponential backoff)
                self.reconnect_count += 1
                wait_time = min(
                    self.reconnect_delay_seconds * (2 ** (self.reconnect_count - 1)),
                    30  # Max 30 seconds
                )

                self.emit_event("reconnecting", data={
                    "attempt": self.reconnect_count,
                    "wait_seconds": wait_time
                })

                time.sleep(wait_time)

            except KeyboardInterrupt:
                break

            except Exception as e:
                if not self.reconnect:
                    break

                # Error already emitted in connect(), just handle reconnection
                if self.max_reconnect_attempts > 0 and \
                   self.reconnect_count >= self.max_reconnect_attempts:
                    self.emit_event("shutdown", data={
                        "reason": "Max reconnect attempts reached after error",
                        "attempts": self.reconnect_count,
                        "last_error": str(e)
                    })
                    break

                # Wait before reconnecting
                self.reconnect_count += 1
                wait_time = min(
                    self.reconnect_delay_seconds * (2 ** (self.reconnect_count - 1)),
                    30
                )

                self.emit_event("reconnecting", data={
                    "attempt": self.reconnect_count,
                    "wait_seconds": wait_time,
                    "after_error": str(e)
                })

                time.sleep(wait_time)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(json.dumps({
        "event_type": "shutdown",
        "event_name": None,
        "data": {"reason": "Signal received", "signal": signum},
        "id": None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sequence": -1
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
                "event_type": "error",
                "event_name": None,
                "data": {"error": f"Invalid JSON input: {str(e)}"},
                "id": None,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sequence": 0
            }), file=sys.stderr)
            sys.exit(1)

        # Extract parameters
        url = input_data.get("url")

        if not url:
            print(json.dumps({
                "event_type": "error",
                "event_name": None,
                "data": {"error": "Missing required parameter: url"},
                "id": None,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sequence": 0
            }), file=sys.stderr)
            sys.exit(1)

        # Create stream
        stream = SSEStreamProducer(
            url=url,
            headers=input_data.get("headers", {}),
            reconnect=input_data.get("reconnect", True),
            max_reconnect_attempts=input_data.get("max_reconnect_attempts", 10),
            reconnect_delay_seconds=input_data.get("reconnect_delay_seconds", 2)
        )

        # Run stream
        stream.run()

    except Exception as e:
        print(json.dumps({
            "event_type": "error",
            "event_name": None,
            "data": {"error": f"Fatal error: {str(e)}"},
            "id": None,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sequence": -1
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
