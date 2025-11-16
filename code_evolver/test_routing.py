"""
Quick diagnostic to test model routing.
"""
import sys
from src.config_manager import ConfigManager
from src.llm_client_factory import LLMClientFactory

def test_routing():
    """Test that models are routed to correct backends."""

    print("=" * 70)
    print("Model Routing Diagnostic")
    print("=" * 70)

    # Load config
    print("\n1. Loading config.anthropic.yaml...")
    try:
        config = ConfigManager("config.anthropic.yaml")
        print("[OK] Config loaded")
    except Exception as e:
        print(f"[FAIL] Failed to load config: {e}")
        return False

    # Create routing client
    print("\n2. Creating routing client...")
    try:
        client = LLMClientFactory.create_routing_client(config)
        print(f"[OK] Routing client created")
        print(f"  Available backends: {list(client.clients.keys())}")
    except Exception as e:
        print(f"[FAIL] Failed to create routing client: {e}")
        return False

    # Test backend detection for different models
    print("\n3. Testing backend detection...")

    test_cases = [
        ("tinyllama", "tinyllama", "ollama"),
        ("llama3", "llama3", "ollama"),
        ("claude-3-haiku-20240307", "claude_haiku", "anthropic"),
        ("claude-3-5-sonnet-20241022", "claude_sonnet", "anthropic"),
        ("nomic-embed-text", "nomic_embed", "ollama"),
    ]

    all_passed = True
    for model_name, model_key, expected_backend in test_cases:
        detected = client._get_backend_for_model(model_name, model_key)
        status = "[OK]" if detected == expected_backend else "[FAIL]"
        if detected != expected_backend:
            all_passed = False
        print(f"  {status} {model_name} (key: {model_key})")
        print(f"      Expected: {expected_backend}, Got: {detected}")

    if not all_passed:
        print("\n[FAIL] Some models routed to wrong backend!")
        return False

    print("\n[OK] All models routed correctly!")

    # Test that Ollama client can accept max_tokens
    print("\n4. Testing Ollama client parameter compatibility...")
    if "ollama" in client.clients:
        ollama_client = client.clients["ollama"]
        try:
            # This should not raise an error even though max_tokens is provided
            result = ollama_client.generate(
                model="tinyllama",
                prompt="Say 'test' and nothing else.",
                max_tokens=10,  # This parameter should be accepted
                temperature=0.7
            )
            print("[OK] Ollama client accepts max_tokens parameter")
            print(f"  Response: {result[:50]}..." if len(result) > 50 else f"  Response: {result}")
        except TypeError as e:
            print(f"[FAIL] Ollama client doesn't accept max_tokens: {e}")
            return False
        except Exception as e:
            print(f"[WARN] Ollama client accepts parameter but call failed: {e}")
            print("  (This is OK if Ollama isn't running)")
    else:
        print("[SKIP] Ollama backend not available")

    return True

if __name__ == "__main__":
    print("\n" + "=" * 70)
    success = test_routing()
    print("\n" + "=" * 70)

    if success:
        print("[SUCCESS] Routing diagnostic passed!")
        print("\nNext steps:")
        print("  1. Make sure Ollama is running: ollama serve")
        print("  2. Set ANTHROPIC_API_KEY: $env:ANTHROPIC_API_KEY=\"sk-ant-...\"")
        print("  3. Run chat CLI: python chat_cli.py --config config.anthropic.yaml")
    else:
        print("[FAILED] Routing diagnostic failed - check errors above")

    print("=" * 70)
    sys.exit(0 if success else 1)
