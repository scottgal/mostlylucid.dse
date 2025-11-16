#!/usr/bin/env python3
"""
Test the buffer tool functionality.
Demonstrates batching and auto-flush behavior.
"""

import sys
sys.path.insert(0, '.')

from node_runtime import call_tool
import json
import time


def test_buffer_batching():
    """Test buffer batching behavior."""
    print("=== Test 1: Buffer Batching ===\n")

    buffer_id = "test_batch"

    # Write items to buffer (max_size=5)
    for i in range(1, 8):
        result = call_tool("buffer", json.dumps({
            "operation": "write",
            "buffer_id": buffer_id,
            "data": {"item_number": i, "value": f"item_{i}"},
            "max_size": 5,
            "flush_strategy": "batched"
        }), disable_tracking=True)

        result_data = json.loads(result)
        print(f"Write item {i}: buffered={result_data['buffered_count']}, " +
              f"flushed={result_data.get('flushed', False)}")

        # Item 5 should trigger auto-flush
        if result_data.get('flushed'):
            print(f"  -> AUTO-FLUSH! Flushed {result_data.get('flushed_count', 0)} items\n")

    print()


def test_buffer_time_flush():
    """Test buffer time-based flush."""
    print("=== Test 2: Time-Based Flush ===\n")

    buffer_id = "test_time"

    # Write a few items
    for i in range(1, 4):
        result = call_tool("buffer", json.dumps({
            "operation": "write",
            "buffer_id": buffer_id,
            "data": {"item": i},
            "max_size": 100,  # High limit
            "flush_interval_seconds": 2.0,  # But short time
            "flush_strategy": "batched"
        }), disable_tracking=True)

        result_data = json.loads(result)
        print(f"Write item {i}: buffered={result_data['buffered_count']}")

    print("Waiting 3 seconds for time-based flush...")
    time.sleep(3)

    # Next write should trigger time-based flush
    result = call_tool("buffer", json.dumps({
        "operation": "write",
        "buffer_id": buffer_id,
        "data": {"item": 4},
        "max_size": 100,
        "flush_interval_seconds": 2.0,
        "flush_strategy": "batched"
    }), disable_tracking=True)

    result_data = json.loads(result)
    if result_data.get('flushed'):
        print(f"  -> TIME-BASED FLUSH! Flushed {result_data.get('flushed_count', 0)} items\n")
    else:
        print(f"  -> Not flushed yet (buffered={result_data['buffered_count']})\n")

    print()


def test_buffer_status():
    """Test buffer status."""
    print("=== Test 3: Buffer Status ===\n")

    buffer_id = "test_status"

    # Write some items
    for i in range(1, 4):
        call_tool("buffer", json.dumps({
            "operation": "write",
            "buffer_id": buffer_id,
            "data": {"item": i},
            "max_size": 10
        }), disable_tracking=True)

    # Check status
    result = call_tool("buffer", json.dumps({
        "operation": "status",
        "buffer_id": buffer_id
    }), disable_tracking=True)

    status = json.loads(result)
    print(f"Buffer ID: {status['buffer_id']}")
    print(f"Items buffered: {status['buffered_count']}/{status['max_size']}")
    print(f"Flush strategy: {status['flush_strategy']}")
    print(f"Time since last flush: {status['time_since_last_flush']}s")
    print()


def test_buffer_manual_flush():
    """Test manual flush."""
    print("=== Test 4: Manual Flush ===\n")

    buffer_id = "test_manual"

    # Write items with manual strategy
    for i in range(1, 4):
        result = call_tool("buffer", json.dumps({
            "operation": "write",
            "buffer_id": buffer_id,
            "data": {"item": i},
            "max_size": 5,
            "flush_strategy": "manual"  # No auto-flush
        }), disable_tracking=True)

        result_data = json.loads(result)
        print(f"Write item {i}: buffered={result_data['buffered_count']}")

    print("\nManually flushing buffer...")
    result = call_tool("buffer", json.dumps({
        "operation": "flush",
        "buffer_id": buffer_id
    }), disable_tracking=True)

    flush_data = json.loads(result)
    print(f"  -> Flushed {flush_data.get('flushed_count', 0)} items")
    print()


def test_buffer_clear():
    """Test buffer clear."""
    print("=== Test 5: Clear Buffer ===\n")

    buffer_id = "test_clear"

    # Write some items
    for i in range(1, 4):
        call_tool("buffer", json.dumps({
            "operation": "write",
            "buffer_id": buffer_id,
            "data": {"item": i}
        }), disable_tracking=True)

    print("Buffer has 3 items")

    # Clear buffer
    result = call_tool("buffer", json.dumps({
        "operation": "clear",
        "buffer_id": buffer_id
    }), disable_tracking=True)

    clear_data = json.loads(result)
    print(f"Cleared {clear_data['cleared_count']} items")
    print(f"Buffer now has {clear_data['buffered_count']} items")
    print()


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("BUFFER TOOL TESTS")
    print("="*60 + "\n")

    try:
        test_buffer_batching()
        test_buffer_time_flush()
        test_buffer_status()
        test_buffer_manual_flush()
        test_buffer_clear()

        print("="*60)
        print("[PASS] ALL TESTS PASSED")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
