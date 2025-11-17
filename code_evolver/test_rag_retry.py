#!/usr/bin/env python3
"""
Test RAG retry logic with exponential backoff.

This test verifies that RAG initialization properly retries with exponential
backoff when failures occur.
"""

import sys
import os
import time
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def test_rag_retry_logic():
    """Test that RAG initialization retries with exponential backoff."""
    print("=" * 60)
    print("Testing RAG Retry Logic")
    print("=" * 60)

    from src import create_rag_memory
    from src.config_manager import ConfigManager

    # Create mock config and client
    mock_config = Mock(spec=ConfigManager)
    mock_config.use_qdrant = False
    mock_config.rag_memory_path = "./test_rag_memory"
    mock_config.get.return_value = "nomic_embed"
    mock_config.get_model_metadata.return_value = {"name": "nomic-embed-text"}

    mock_client = Mock()

    # Test 1: Successful initialization on first try
    print("\n[TEST 1] Successful initialization on first try")
    try:
        with patch('src.RAGMemory') as mock_rag:
            mock_rag.return_value = Mock()
            start = time.time()
            rag = create_rag_memory(mock_config, mock_client)
            elapsed = time.time() - start

            if elapsed < 1:  # Should succeed immediately
                print("[PASS] RAG initialized immediately (no retry needed)")
            else:
                print(f"[FAIL] Took {elapsed:.2f}s (should be < 1s)")
                return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return False

    # Test 2: Retry on transient failure
    print("\n[TEST 2] Retry on transient failure (fails once, then succeeds)")
    try:
        attempt = [0]

        def failing_init(*args, **kwargs):
            attempt[0] += 1
            if attempt[0] == 1:
                raise ConnectionError("Simulated transient failure")
            return Mock()

        with patch('src.RAGMemory', side_effect=failing_init):
            start = time.time()
            rag = create_rag_memory(mock_config, mock_client)
            elapsed = time.time() - start

            if 2 <= elapsed <= 4:  # Should retry once with ~2s delay
                print(f"[PASS] Retried once with exponential backoff ({elapsed:.2f}s)")
                print(f"       Attempts: {attempt[0]}")
            else:
                print(f"[FAIL] Unexpected timing: {elapsed:.2f}s (expected 2-4s)")
                return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Complete failure after all retries
    print("\n[TEST 3] Complete failure after all retries")
    try:
        with patch('src.RAGMemory', side_effect=ConnectionError("Persistent failure")):
            start = time.time()
            try:
                rag = create_rag_memory(mock_config, mock_client)
                print("[FAIL] Should have raised RuntimeError")
                return False
            except RuntimeError as e:
                elapsed = time.time() - start
                if 6 <= elapsed <= 10:  # 3 attempts: 0s + 2s + 4s = ~6s
                    print(f"[PASS] Failed after all retries ({elapsed:.2f}s)")
                    print(f"       Error: {str(e)[:60]}...")
                else:
                    print(f"[FAIL] Unexpected timing: {elapsed:.2f}s (expected 6-10s)")
                    return False
    except Exception as e:
        print(f"[FAIL] Unexpected error type: {type(e).__name__}")
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] All RAG retry tests passed!")
    print("=" * 60)
    print("\nRetry Strategy Summary:")
    print("  - Max retries: 3")
    print("  - Base delay: 2 seconds")
    print("  - Backoff: Exponential (2^attempt)")
    print("  - Delays: 2s, 4s (total ~6s for 3 failures)")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_rag_retry_logic()
    sys.exit(0 if success else 1)
