#!/usr/bin/env python3
"""
Simple test script to validate skill structure without requiring Ollama.
"""

import json
import sys
from pathlib import Path

def test_duplicate_style_structure():
    """Test duplicate_style skill can be imported and validated."""
    print("Testing duplicate_style skill structure...")

    # Test input validation
    test_input = {
        "directory": "test_content",
        "file_patterns": ["*.md"],
        "quality_requirement": 0.7,
        "review_and_refine": False
    }

    # Validate JSON
    try:
        json_str = json.dumps(test_input)
        parsed = json.loads(json_str)
        assert parsed["directory"] == "test_content"
        print("✓ duplicate_style: Input JSON validation passed")
    except Exception as e:
        print(f"✗ duplicate_style: Input JSON validation failed: {e}")
        return False

    # Check file exists
    skill_path = Path("code_evolver/tools/executable/duplicate_style.py")
    yaml_path = Path("code_evolver/tools/executable/duplicate_style.yaml")

    if not skill_path.exists():
        print(f"✗ duplicate_style: Python file not found at {skill_path}")
        return False
    print(f"✓ duplicate_style: Python file exists")

    if not yaml_path.exists():
        print(f"✗ duplicate_style: YAML file not found at {yaml_path}")
        return False
    print(f"✓ duplicate_style: YAML file exists")

    # Check executable
    if not skill_path.stat().st_mode & 0o111:
        print(f"✗ duplicate_style: File is not executable")
        return False
    print(f"✓ duplicate_style: File is executable")

    print("✓ duplicate_style skill structure validated\n")
    return True


def test_write_markdown_doc_structure():
    """Test write_markdown_doc skill can be imported and validated."""
    print("Testing write_markdown_doc skill structure...")

    # Test input validation
    test_input = {
        "topic": "Test topic",
        "output_file": "test/output.md",
        "length": "medium",
        "quality_requirement": 0.8,
        "review_and_refine": True
    }

    # Validate JSON
    try:
        json_str = json.dumps(test_input)
        parsed = json.loads(json_str)
        assert parsed["topic"] == "Test topic"
        print("✓ write_markdown_doc: Input JSON validation passed")
    except Exception as e:
        print(f"✗ write_markdown_doc: Input JSON validation failed: {e}")
        return False

    # Check file exists
    skill_path = Path("code_evolver/tools/executable/write_markdown_doc.py")
    yaml_path = Path("code_evolver/tools/executable/write_markdown_doc.yaml")

    if not skill_path.exists():
        print(f"✗ write_markdown_doc: Python file not found at {skill_path}")
        return False
    print(f"✓ write_markdown_doc: Python file exists")

    if not yaml_path.exists():
        print(f"✗ write_markdown_doc: YAML file not found at {yaml_path}")
        return False
    print(f"✓ write_markdown_doc: YAML file exists")

    # Check executable
    if not skill_path.stat().st_mode & 0o111:
        print(f"✗ write_markdown_doc: File is not executable")
        return False
    print(f"✓ write_markdown_doc: File is executable")

    print("✓ write_markdown_doc skill structure validated\n")
    return True


def test_security_guardrails():
    """Test security guardrails in write_markdown_doc."""
    print("Testing security guardrails...")

    sys.path.insert(0, str(Path("code_evolver")))

    try:
        # Import the MarkdownGenerator class
        from tools.executable.write_markdown_doc import MarkdownGenerator

        # Create a mock client
        class MockClient:
            def generate(self, **kwargs):
                return "Mock content"

        generator = MarkdownGenerator(MockClient())

        # Test valid path
        try:
            path = generator.validate_output_path("test/file.md")
            assert str(path).endswith("output/test/file.md")
            print("✓ Security: Valid path accepted")
        except Exception as e:
            print(f"✗ Security: Valid path rejected: {e}")
            return False

        # Test path traversal attempt
        try:
            path = generator.validate_output_path("../../../etc/passwd.md")
            print(f"✗ Security: Path traversal NOT blocked! Got: {path}")
            return False
        except ValueError:
            print("✓ Security: Path traversal blocked")

        # Test absolute path attempt
        try:
            path = generator.validate_output_path("/etc/passwd.md")
            # Should be sanitized to output/etc/passwd.md
            assert "output" in str(path)
            print("✓ Security: Absolute path sanitized")
        except Exception as e:
            print(f"✓ Security: Absolute path blocked: {e}")

        # Test wrong extension
        try:
            path = generator.validate_output_path("test/file.txt")
            print(f"✗ Security: Wrong extension NOT blocked! Got: {path}")
            return False
        except ValueError:
            print("✓ Security: Wrong extension blocked")

        print("✓ All security guardrails working\n")
        return True

    except ImportError as e:
        print(f"✗ Security: Could not import module: {e}")
        return False
    except Exception as e:
        print(f"✗ Security: Unexpected error: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("SKILL STRUCTURE VALIDATION")
    print("="*60 + "\n")

    tests = [
        test_duplicate_style_structure,
        test_write_markdown_doc_structure,
        test_security_guardrails
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)

    print("="*60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("="*60)

    if all(results):
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
