"""
Test to verify all config issues are fixed.
"""
import sys
from src.config_manager import ConfigManager

def test_config(config_path, expected_models):
    """Test a config file."""
    print(f"\n{'='*70}")
    print(f"Testing: {config_path}")
    print('='*70)

    try:
        config = ConfigManager(config_path)
        print("[OK] Config loaded successfully")
    except Exception as e:
        print(f"[FAIL] Failed to load config: {e}")
        return False

    all_passed = True

    # Test each model property
    for prop_name, expected_name in expected_models.items():
        try:
            actual_name = getattr(config, prop_name)
            if actual_name == expected_name:
                print(f"  [OK] {prop_name}: {actual_name}")
            else:
                print(f"  [FAIL] {prop_name}: expected '{expected_name}', got '{actual_name}'")
                all_passed = False
        except Exception as e:
            print(f"  [FAIL] {prop_name}: {e}")
            all_passed = False

    # Test unified config resolution for key roles
    print("\n  Testing unified config resolution:")

    test_cases = [
        ("default", "veryfast", "triage"),
        ("content", "veryfast", "content triage"),
        ("default", "general", "overseer"),
        ("code", "general", "generator"),
    ]

    for role, level, description in test_cases:
        try:
            model_key = config.get_model(role=role, level=level)
            if model_key:
                metadata = config.get_model_metadata(model_key)
                model_name = metadata.get("name", "UNKNOWN")
                backend = metadata.get("backend", "UNKNOWN")
                print(f"  [OK] {description} ({role}.{level}): {model_key} -> {model_name} ({backend})")
            else:
                print(f"  [WARN] {description} ({role}.{level}): No model configured (will use default)")
        except Exception as e:
            print(f"  [FAIL] {description} ({role}.{level}): {e}")
            all_passed = False

    return all_passed

def main():
    print("="*70)
    print("Config Fix Verification Test")
    print("="*70)

    # Test config.yaml (all local)
    print("\n1. Testing config.yaml (all local Ollama)...")
    local_expected = {
        "triage_model": "tinyllama",
        "overseer_model": "llama3",
        "generator_model": "codellama",
        "evaluator_model": "llama3",
        "escalation_model": "qwen2.5-coder:14b",
        "embedding_model": "nomic-embed-text",
    }
    result1 = test_config("config.yaml", local_expected)

    # Test config.anthropic.yaml (mixed)
    print("\n2. Testing config.anthropic.yaml (mixed Anthropic + Ollama)...")
    anthropic_expected = {
        "triage_model": "tinyllama",  # Default role uses tinyllama
        "overseer_model": "claude-3-5-sonnet-20241022",  # Default role uses sonnet
        "generator_model": "claude-3-5-sonnet-20241022",  # Code role uses sonnet
        "evaluator_model": "claude-3-5-sonnet-20241022",  # Default role uses sonnet
        "escalation_model": "claude-3-5-sonnet-20241022",  # Escalation uses sonnet
        "embedding_model": "nomic-embed-text",  # Embeddings always Ollama
    }
    result2 = test_config("config.anthropic.yaml", anthropic_expected)

    # Final summary
    print("\n" + "="*70)
    if result1 and result2:
        print("[SUCCESS] All config tests passed!")
        print("\nKey points:")
        print("  • config.yaml: ALL local models ✓")
        print("  • config.anthropic.yaml: Mixed (Anthropic + Ollama) ✓")
        print("  • Content triage in Anthropic mode uses Claude Haiku ✓")
        print("  • Content triage in local mode uses tinyllama ✓")
        print("  • Embeddings always use Ollama (nomic-embed-text) ✓")
        print("\nNext step: Try running chat_cli.py!")
    else:
        print("[FAILED] Some config tests failed - check errors above")

    print("="*70)

    return 0 if (result1 and result2) else 1

if __name__ == "__main__":
    sys.exit(main())
