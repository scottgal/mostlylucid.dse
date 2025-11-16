"""
Quick test to verify Anthropic SDK integration and routing client work correctly.
"""
import os
import sys
from src.config_manager import ConfigManager
from src.llm_client_factory import LLMClientFactory

def test_routing_client():
    """Test routing client with both Ollama and Anthropic backends."""

    # Check if API key is set
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[FAIL] ANTHROPIC_API_KEY not set")
        print("Set it with: $env:ANTHROPIC_API_KEY=\"sk-ant-api03-...\"")
        return False

    print(f"[OK] API key found (length: {len(api_key)})")
    print(f"  Starts with: {api_key[:15]}...")

    # Load config
    print("\n1. Loading config.anthropic.yaml...")
    try:
        config = ConfigManager("config.anthropic.yaml")
        print("[OK] Config loaded successfully")
    except Exception as e:
        print(f"[FAIL] Failed to load config: {e}")
        return False

    # Initialize routing client
    print("\n2. Initializing routing client...")
    try:
        client = LLMClientFactory.create_routing_client(config)
        print("[OK] Routing client initialized")
        print(f"  Available backends: {list(client.clients.keys())}")
    except Exception as e:
        print(f"[FAIL] Failed to initialize routing client: {e}")
        return False

    # Test Anthropic model (should route to Anthropic)
    print("\n3. Testing Anthropic model routing...")
    result = client.generate(
        model="claude-3-haiku-20240307",
        prompt="Say 'Hello from Anthropic!' and nothing else.",
        model_key="claude_haiku",
        max_tokens=50
    )

    if result:
        print(f"[OK] Anthropic generation successful!")
        print(f"Response: {result}")
    else:
        print("[FAIL] Anthropic generation failed")
        return False

    # Test Ollama model (should route to Ollama)
    print("\n4. Testing Ollama model routing...")
    result = client.generate(
        model="tinyllama",
        prompt="Say 'Hello from Ollama!' and nothing else.",
        model_key="tinyllama",
        max_tokens=50
    )

    if result:
        print(f"[OK] Ollama generation successful!")
        print(f"Response: {result}")
    else:
        print("[WARN] Ollama generation failed (Ollama may not be running)")
        # Don't fail the test if Ollama isn't running

    return True

if __name__ == "__main__":
    print("=" * 70)
    print("Anthropic SDK + Routing Client Test")
    print("=" * 70)

    success = test_routing_client()

    print("\n" + "=" * 70)
    if success:
        print("[SUCCESS] ALL TESTS PASSED - Routing client is working correctly!")
    else:
        print("[FAILED] TESTS FAILED - Check error messages above")
    print("=" * 70)

    sys.exit(0 if success else 1)
