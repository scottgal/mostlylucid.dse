#!/usr/bin/env python3
"""
Simple mock SSE server for testing stream tools.
Runs on http://127.0.0.1:5116/api/mock/contexts
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading


class SSEHandler(BaseHTTPRequestHandler):
    """Handle SSE requests."""

    def do_GET(self):
        """Handle GET request."""
        if self.path == '/api/mock/contexts':
            # Send SSE headers
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()

            # Send test events
            for i in range(10):
                # Event with data
                event_data = {
                    "id": f"task-{i+1}",
                    "type": ["summarize", "translate", "generate"][i % 3],
                    "priority": ["low", "medium", "high"][i % 3],
                    "content": f"Test task {i+1}"
                }

                # Send SSE event
                self.wfile.write(f"event: TaskReceived\n".encode())
                self.wfile.write(f"data: {json.dumps(event_data)}\n".encode())
                self.wfile.write(f"id: {i+1}\n".encode())
                self.wfile.write(b"\n")
                self.wfile.flush()

                time.sleep(1)

            # Send completion event
            self.wfile.write(b"event: StreamEnd\n")
            self.wfile.write(b"data: {\"status\": \"complete\"}\n")
            self.wfile.write(b"\n")
            self.wfile.flush()

        else:
            self.send_error(404)

    def log_message(self, format, *args):
        """Suppress request logs."""
        pass


def run_server(port=8765):
    """Run the mock SSE server."""
    server = HTTPServer(('127.0.0.1', port), SSEHandler)
    print(f"Mock SSE server running on http://127.0.0.1:{port}/api/mock/contexts")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    run_server()
