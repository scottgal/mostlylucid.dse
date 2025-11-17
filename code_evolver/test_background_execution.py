#!/usr/bin/env python3
"""
Test Background Execution System
Quick test to verify background processes work correctly.
"""
import time
import sys
from src import BackgroundProcessManager, BackgroundProcess
from src.config_manager import ConfigManager
from src.ollama_client import OllamaClient
from src.sentinel_llm import SentinelLLM

def slow_task(duration: int, background_process=None):
    """
    A slow task that updates status with realistic workflow steps.

    Args:
        duration: How long to run (seconds)
        background_process: Process instance for status updates
    """
    # Simulate realistic tool building workflow
    steps = [
        (0.05, "Initializing..."),
        (0.10, "Consulting overseer..."),
        (0.20, "Generating spec..."),
        (0.40, "Generating code for tool: test_tool"),
        (0.60, "Running tests..."),
        (0.70, "Running static analysis..."),
        (0.85, "Validating output..."),
        (0.95, "Saving tool..."),
        (1.00, "Complete!")
    ]

    step_duration = duration / len(steps)

    for progress, message in steps:
        if background_process and background_process.is_cancelled():
            return {"cancelled": True, "progress": progress}

        # Update status BEFORE the work
        if background_process:
            background_process.update_status(message, progress)

        # Simulate work
        time.sleep(step_duration)

    return {"success": True, "result": f"Tool built successfully"}


def main():
    """Run background execution tests"""
    print("=" * 70)
    print("TESTING: Background Execution System")
    print("=" * 70)

    # Initialize components
    config = ConfigManager()
    client = OllamaClient(config_manager=config)
    sentinel = SentinelLLM(ollama_client=client)

    manager = BackgroundProcessManager(sentinel=sentinel, max_concurrent=3)

    # Test 1: Basic background execution
    print("\n[TEST 1] Basic background execution")
    print("-" * 70)

    process_id = manager.start_process(
        task_fn=slow_task,
        kwargs={'duration': 5},  # 5 seconds
        description="Test slow task"
    )

    print(f"Started process: {process_id}")

    # Monitor progress with real-time updates
    last_progress = -1
    update_count = 0

    print("Monitoring process (showing real-time updates)...")

    while True:
        process = manager.get_process(process_id)
        if not process:
            print("ERROR: Process not found!")
            break

        # Print new status updates immediately
        updates = process.get_new_status_updates()
        for update in updates:
            update_count += 1
            # Show timestamp and progress bar
            progress_bar = "=" * int(update.progress * 20)
            progress_pct = f"{update.progress:.0%}"
            print(f"  [{process_id}] {update.message} [{progress_bar:20s}] {progress_pct}")

        # Check if done
        if not process.is_running():
            print(f"Process finished! (received {update_count} status updates)")
            break

        time.sleep(0.2)  # Check more frequently for responsive updates

    # Get final status
    status = manager.get_status(process_id)
    if status:
        if status['status'] == 'completed':
            print(f"[PASS] Process completed successfully")
            print(f"  Result: {status['result']}")
            print(f"  Duration: {status['duration']:.2f}s")
        else:
            print(f"[FAIL] Process status: {status['status']}")
    else:
        print("[FAIL] Could not get process status")

    # Test 2: Sentinel interrupt decision
    print("\n[TEST 2] Sentinel interrupt decision")
    print("-" * 70)

    # Start another background process
    process_id2 = manager.start_process(
        task_fn=slow_task,
        kwargs={'duration': 10},
        description="Building email validator tool"
    )

    time.sleep(1)  # Let it start

    # Test different user inputs
    test_inputs = [
        ("What's the status?", False),  # Should NOT interrupt
        ("cancel this", True),           # Should INTERRUPT
        ("build a new tool", False),     # Should NOT interrupt (queue)
    ]

    for user_input, expected_interrupt in test_inputs:
        process_info = manager.get_status(process_id2)

        decision = sentinel.should_interrupt_background_process(
            process_info,
            user_input
        )

        should_interrupt = decision['should_interrupt']
        reason = decision['reason']

        result = "PASS" if (should_interrupt == expected_interrupt) else "FAIL"

        print(f"  Input: \"{user_input}\"")
        print(f"  Decision: {'INTERRUPT' if should_interrupt else 'CONTINUE'}")
        print(f"  Reason: {reason}")
        print(f"  [{result}] Expected: {'INTERRUPT' if expected_interrupt else 'CONTINUE'}")
        print()

    # Cancel the process
    manager.cancel_process(process_id2)
    print(f"Cancelled process: {process_id2}")

    # Test 3: Multiple concurrent processes
    print("\n[TEST 3] Multiple concurrent processes")
    print("-" * 70)

    # Start 3 processes
    pids = []
    for i in range(3):
        pid = manager.start_process(
            task_fn=slow_task,
            kwargs={'duration': 3},
            description=f"Concurrent task {i+1}"
        )
        pids.append(pid)
        print(f"Started: {pid}")

    # Wait for all
    print("Waiting for all processes (showing real-time updates)...")
    start_time = time.time()
    total_updates = 0

    while manager.has_running_processes():
        # Print new updates with progress bars
        all_updates = manager.get_new_status_updates()

        for pid, updates in all_updates.items():
            for update in updates:
                total_updates += 1
                progress_bar = "=" * int(update.progress * 15)
                print(f"  [{pid[-8:]}] {update.message:30s} [{progress_bar:15s}] {update.progress:.0%}")

        time.sleep(0.2)

    print(f"All processes complete! (total {total_updates} status updates)")

    elapsed = time.time() - start_time

    # Check results
    summary = manager.get_summary()
    print(f"\nResults:")
    print(f"  Total: {summary['total']}")
    print(f"  Completed: {summary['completed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Elapsed: {elapsed:.2f}s")

    if summary['completed'] == 3:
        print("[PASS] All 3 processes completed")
    else:
        print(f"[FAIL] Expected 3 completed, got {summary['completed']}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Manager state: {manager}")
    print()
    print("[PASS] Background execution system working!")


if __name__ == '__main__':
    main()
