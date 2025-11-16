"""Test CLI startup performance and non-blocking behavior."""
import time
import sys
from pathlib import Path

# Add code_evolver to path
sys.path.insert(0, str(Path(__file__).parent / 'code_evolver'))

def test_cli_startup():
    """Test that CLI starts quickly without blocking on tools."""

    print("="*70)
    print("CLI STARTUP TEST")
    print("="*70)
    print()
    print("Testing that CLI initialization is non-blocking...")
    print("(Tools should load in background with live progress indicator)")
    print()

    start = time.time()

    # Import and initialize CLI
    print("[1] Importing ChatCLI...")
    from chat_cli import ChatCLI

    print("[2] Creating ChatCLI instance...")
    init_start = time.time()

    cli = ChatCLI()

    init_elapsed = time.time() - init_start

    print(f"\n[3] CLI initialized in {init_elapsed:.2f}s")

    # Check if it was fast (should be < 2 seconds if truly non-blocking)
    if init_elapsed < 2.0:
        print(f"[OK] Fast startup! ({init_elapsed:.2f}s < 2.0s)")
    elif init_elapsed < 5.0:
        print(f"[WARNING] Moderate startup time ({init_elapsed:.2f}s)")
    else:
        print(f"[SLOW] Slow startup! ({init_elapsed:.2f}s > 5.0s)")
        print("Tools may be loading synchronously instead of in background")

    # Check tools loading status
    print(f"\n[4] Checking tools loading status...")
    if cli._tools_loader.is_ready_sync():
        print(f"[OK] Tools already loaded")
    else:
        print(f"[OK] Tools still loading in background (as expected)")

    # Wait for tools to finish loading
    print(f"\n[5] Waiting for tools to finish loading...")
    tools_start = time.time()
    tools_manager = cli.tools_manager  # This will wait
    tools_elapsed = time.time() - tools_start

    print(f"[OK] Tools loaded ({len(tools_manager.tools)} tools in {tools_elapsed:.2f}s)")

    total_elapsed = time.time() - start

    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"CLI initialization: {init_elapsed:.2f}s")
    print(f"Tools loading:      {tools_elapsed:.2f}s")
    print(f"Total time:         {total_elapsed:.2f}s")
    print()

    if init_elapsed < 2.0:
        print("[SUCCESS] CLI starts immediately, tools load in background!")
    else:
        print("[NEEDS IMPROVEMENT] CLI initialization took too long")

    return init_elapsed < 2.0

if __name__ == "__main__":
    try:
        success = test_cli_startup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
