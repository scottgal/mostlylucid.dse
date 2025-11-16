#!/usr/bin/env python3
"""
Buffer Tool

Buffers data to smooth fast traffic. Batches items and flushes based on
size, time, or manual trigger.
"""

import json
import sys
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
import pickle

# Persistent buffer storage directory
_BUFFER_DIR = Path("./temp/buffers")
_BUFFER_DIR.mkdir(parents=True, exist_ok=True)

# Global buffer storage (persists across calls within same process)
_buffers: Dict[str, Dict[str, Any]] = {}
_buffers_lock = threading.Lock()


class Buffer:
    """Buffer for smoothing fast data traffic."""

    def __init__(
        self,
        buffer_id: str,
        max_size: int = 100,
        flush_interval_seconds: float = 5.0,
        flush_strategy: str = "batched",
        pass_through_tool: Optional[str] = None,
        pass_through_input: Optional[Dict] = None
    ):
        self.buffer_id = buffer_id
        self.max_size = max_size
        self.flush_interval_seconds = flush_interval_seconds
        self.flush_strategy = flush_strategy
        self.pass_through_tool = pass_through_tool
        self.pass_through_input = pass_through_input or {}

        self.items: List[Any] = []
        self.last_flush_time = time.time()
        self.total_flushed = 0

    def save_to_disk(self):
        """Save buffer state to disk."""
        state_file = _BUFFER_DIR / f"{self.buffer_id}.pkl"
        state = {
            'items': self.items,
            'last_flush_time': self.last_flush_time,
            'total_flushed': self.total_flushed,
            'max_size': self.max_size,
            'flush_interval_seconds': self.flush_interval_seconds,
            'flush_strategy': self.flush_strategy,
            'pass_through_tool': self.pass_through_tool,
            'pass_through_input': self.pass_through_input
        }
        with open(state_file, 'wb') as f:
            pickle.dump(state, f)

    @classmethod
    def load_from_disk(cls, buffer_id: str) -> Optional['Buffer']:
        """Load buffer state from disk."""
        state_file = _BUFFER_DIR / f"{buffer_id}.pkl"
        if not state_file.exists():
            return None

        try:
            with open(state_file, 'rb') as f:
                state = pickle.load(f)

            buffer = cls(
                buffer_id=buffer_id,
                max_size=state.get('max_size', 100),
                flush_interval_seconds=state.get('flush_interval_seconds', 5.0),
                flush_strategy=state.get('flush_strategy', 'batched'),
                pass_through_tool=state.get('pass_through_tool'),
                pass_through_input=state.get('pass_through_input', {})
            )
            buffer.items = state.get('items', [])
            buffer.last_flush_time = state.get('last_flush_time', time.time())
            buffer.total_flushed = state.get('total_flushed', 0)

            return buffer
        except Exception as e:
            print(f"Warning: Failed to load buffer state: {e}", file=sys.stderr)
            return None

    def should_auto_flush(self) -> bool:
        """Check if buffer should auto-flush."""
        if self.flush_strategy == "manual":
            return False

        if self.flush_strategy == "immediate":
            return len(self.items) > 0

        # Batched strategy
        # Flush if size limit reached
        if len(self.items) >= self.max_size:
            return True

        # Flush if time interval exceeded
        time_since_flush = time.time() - self.last_flush_time
        if time_since_flush >= self.flush_interval_seconds and len(self.items) > 0:
            return True

        return False

    def write(self, data: Any) -> Dict[str, Any]:
        """Write item to buffer."""
        self.items.append(data)

        # Check if should auto-flush
        if self.should_auto_flush():
            result = self.flush()
            # Save state after flush
            self.save_to_disk()
            return result

        # Save state after write
        self.save_to_disk()

        return {
            "operation": "write",
            "buffer_id": self.buffer_id,
            "buffered_count": len(self.items),
            "flushed": False,
            "message": f"Item buffered ({len(self.items)}/{self.max_size})"
        }

    def flush(self) -> Dict[str, Any]:
        """Flush buffer to pass_through_tool."""
        if len(self.items) == 0:
            return {
                "operation": "flush",
                "buffer_id": self.buffer_id,
                "flushed": False,
                "flushed_count": 0,
                "message": "Buffer empty, nothing to flush"
            }

        flushed_count = len(self.items)
        items_to_flush = self.items.copy()
        self.items.clear()
        self.last_flush_time = time.time()
        self.total_flushed += flushed_count

        # Call pass_through_tool if specified
        pass_through_result = None
        if self.pass_through_tool:
            try:
                pass_through_result = self._call_pass_through_tool(items_to_flush)
            except Exception as e:
                # Restore items to buffer if pass_through fails
                self.items = items_to_flush + self.items
                self.save_to_disk()  # Save restored state
                return {
                    "operation": "flush",
                    "buffer_id": self.buffer_id,
                    "flushed": False,
                    "error": f"Pass-through tool failed: {str(e)}",
                    "message": f"Failed to flush {flushed_count} items"
                }

        # Save state after successful flush
        self.save_to_disk()

        return {
            "operation": "flush",
            "buffer_id": self.buffer_id,
            "flushed": True,
            "flushed_count": flushed_count,
            "pass_through_result": pass_through_result,
            "message": f"Flushed {flushed_count} items" +
                       (f" to {self.pass_through_tool}" if self.pass_through_tool else "")
        }

    def _call_pass_through_tool(self, items: List[Any]) -> Any:
        """Call pass_through_tool with buffered items."""
        sys.path.insert(0, '.')
        from node_runtime import call_tool

        # Prepare input for pass_through_tool
        tool_input = {
            **self.pass_through_input,
            "buffered_items": items,
            "buffer_metadata": {
                "buffer_id": self.buffer_id,
                "count": len(items),
                "flushed_at": datetime.utcnow().isoformat() + "Z"
            }
        }

        # Call the tool
        result = call_tool(
            self.pass_through_tool,
            json.dumps(tool_input),
            disable_tracking=True  # Don't track buffer internal operations
        )

        # Try to parse as JSON
        try:
            return json.loads(result)
        except:
            return result

    def status(self) -> Dict[str, Any]:
        """Get buffer status."""
        time_since_flush = time.time() - self.last_flush_time

        return {
            "operation": "status",
            "buffer_id": self.buffer_id,
            "buffered_count": len(self.items),
            "max_size": self.max_size,
            "flush_interval_seconds": self.flush_interval_seconds,
            "flush_strategy": self.flush_strategy,
            "time_since_last_flush": round(time_since_flush, 2),
            "total_flushed": self.total_flushed,
            "pass_through_tool": self.pass_through_tool,
            "message": f"Buffer: {len(self.items)}/{self.max_size} items " +
                       f"({round(time_since_flush, 1)}s since last flush)"
        }

    def clear(self) -> Dict[str, Any]:
        """Clear buffer without flushing."""
        cleared_count = len(self.items)
        self.items.clear()

        # Save state after clear
        self.save_to_disk()

        return {
            "operation": "clear",
            "buffer_id": self.buffer_id,
            "buffered_count": 0,
            "cleared_count": cleared_count,
            "message": f"Cleared {cleared_count} items from buffer"
        }


def get_or_create_buffer(
    buffer_id: str,
    max_size: int = 100,
    flush_interval_seconds: float = 5.0,
    flush_strategy: str = "batched",
    pass_through_tool: Optional[str] = None,
    pass_through_input: Optional[Dict] = None
) -> Buffer:
    """Get existing buffer or create new one."""
    with _buffers_lock:
        if buffer_id not in _buffers:
            # Try to load from disk first
            buffer = Buffer.load_from_disk(buffer_id)

            if buffer is None:
                # Create new buffer
                buffer = Buffer(
                    buffer_id=buffer_id,
                    max_size=max_size,
                    flush_interval_seconds=flush_interval_seconds,
                    flush_strategy=flush_strategy,
                    pass_through_tool=pass_through_tool,
                    pass_through_input=pass_through_input
                )

            _buffers[buffer_id] = buffer
        else:
            buffer = _buffers[buffer_id]

        # Update configuration if provided (and not default values)
        if max_size != 100:  # Not default
            buffer.max_size = max_size
        if flush_interval_seconds != 5.0:  # Not default
            buffer.flush_interval_seconds = flush_interval_seconds
        if flush_strategy != "batched":  # Not default
            buffer.flush_strategy = flush_strategy
        if pass_through_tool:
            buffer.pass_through_tool = pass_through_tool
        if pass_through_input:
            buffer.pass_through_input = pass_through_input

        return buffer


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
        operation = input_data.get("operation", "write")
        buffer_id = input_data.get("buffer_id", "default")
        data = input_data.get("data")
        max_size = input_data.get("max_size", 100)
        flush_interval_seconds = input_data.get("flush_interval_seconds", 5.0)
        flush_strategy = input_data.get("flush_strategy", "batched")
        pass_through_tool = input_data.get("pass_through_tool")
        pass_through_input = input_data.get("pass_through_input", {})

        # Get or create buffer
        buffer = get_or_create_buffer(
            buffer_id=buffer_id,
            max_size=max_size,
            flush_interval_seconds=flush_interval_seconds,
            flush_strategy=flush_strategy,
            pass_through_tool=pass_through_tool,
            pass_through_input=pass_through_input
        )

        # Execute operation
        if operation == "write":
            if data is None:
                print(json.dumps({
                    "error": "Missing required parameter: data",
                    "success": False
                }))
                sys.exit(1)

            result = buffer.write(data)

        elif operation == "flush":
            result = buffer.flush()

        elif operation == "status":
            result = buffer.status()

        elif operation == "clear":
            result = buffer.clear()

        else:
            print(json.dumps({
                "error": f"Unknown operation: {operation}",
                "success": False
            }))
            sys.exit(1)

        # Output result
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": f"Fatal error: {str(e)}",
            "success": False
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
