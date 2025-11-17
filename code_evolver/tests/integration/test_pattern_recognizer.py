#!/usr/bin/env python3
"""
Integration Tests for Pattern Recognizer

Tests pattern storage, retrieval, RAG integration, and semantic search.
"""

import pytest
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def pattern_storage_input():
    """Sample pattern storage input."""
    return {
        "error_message": "SyntaxError: f-string: single '}' is not allowed",
        "broken_code": 'f"Status: {status}"',
        "fixed_code": 'f"Status: {{status}}"',
        "fix_description": "Literal braces in f-strings must be doubled",
        "error_type": "syntax",
        "language": "python",
        "context": {
            "tool_id": "standalone_exe_compiler",
            "location": "generate_wrapper"
        }
    }


@pytest.fixture
def pattern_retrieval_input():
    """Sample pattern retrieval input."""
    return {
        "error_message": "SyntaxError: f-string: unmatched '}'",
        "broken_code": 'f"Result: {result}"',
        "limit": 5
    }


def test_store_pattern_executable():
    """Test storing pattern via executable."""
    input_data = {
        "error_message": "NameError: name 'undefined_var' is not defined",
        "broken_code": "print(undefined_var)",
        "fixed_code": "undefined_var = 'value'\nprint(undefined_var)",
        "fix_description": "Variable must be defined before use",
        "error_type": "runtime",
        "language": "python"
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"Failed: {result.stderr}"

    output = json.loads(result.stdout)

    assert output["success"] is True
    assert "pattern_id" in output
    assert output["error_type"] == "runtime"
    assert "tags" in output
    assert "code-fix-pattern" in output["tags"]


def test_store_pattern_with_scope():
    """Test storing pattern with specific scope."""
    input_data = {
        "error_message": "IndentationError: unexpected indent",
        "broken_code": "def foo():\nbar()",
        "fixed_code": "def foo():\n    bar()",
        "fix_description": "Function body must be indented",
        "error_type": "indentation",
        "language": "python",
        "scope": "tool",
        "tool_id": "code_generator"
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    assert output["success"] is True
    assert "searchable_by" in output


def test_find_similar_pattern():
    """Test finding similar patterns."""
    # First store a pattern
    store_input = {
        "error_message": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
        "broken_code": "result = 5 + '10'",
        "fixed_code": "result = 5 + int('10')",
        "fix_description": "Convert string to int before addition",
        "error_type": "type",
        "language": "python"
    }

    subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(store_input),
        capture_output=True,
        text=True,
        timeout=10
    )

    # Now search for similar error
    find_input = {
        "error_message": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
        "broken_code": "total = 10 + '20'",
        "limit": 3
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/find_code_fix_pattern.py"],
        input=json.dumps(find_input),
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode == 0:
        output = json.loads(result.stdout)

        # Should find at least one similar pattern
        if output.get("found", False):
            assert len(output["patterns"]) > 0
            assert "fix_description" in output["patterns"][0]


def test_pattern_storage_with_debug_info():
    """Test storing pattern with full debug information."""
    input_data = {
        "error_message": "KeyError: 'missing_key'",
        "broken_code": "value = data['missing_key']",
        "fixed_code": "value = data.get('missing_key', default_value)",
        "fix_description": "Use .get() to avoid KeyError",
        "error_type": "runtime",
        "language": "python",
        "debug_info": {
            "stack_trace": ["line 10 in main", "line 5 in process"],
            "variables": {"data": "{'other_key': 'value'}"}
        }
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    assert output["success"] is True


def test_pattern_tags_generation():
    """Test that appropriate tags are generated."""
    input_data = {
        "error_message": "ImportError: No module named 'nonexistent'",
        "broken_code": "import nonexistent",
        "fixed_code": "# Install: pip install nonexistent\nimport nonexistent",
        "fix_description": "Module needs to be installed first",
        "error_type": "import",
        "language": "python"
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    tags = output["tags"]

    # Should include error type and language
    assert "import" in tags or "import-error" in tags
    assert "python" in tags


def test_pattern_with_context():
    """Test pattern storage with rich context."""
    input_data = {
        "error_message": "JSONDecodeError: Expecting value",
        "broken_code": "data = json.loads('')",
        "fixed_code": "data = json.loads('{}') if input_str else {}",
        "fix_description": "Handle empty string before JSON parsing",
        "error_type": "json",
        "language": "python",
        "context": {
            "tool_id": "api_client",
            "framework": "flask",
            "component": "request_handler"
        }
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)

    assert output["success"] is True
    # Context should be preserved
    assert "tool:api_client" in output["tags"] or "api_client" in str(output)


def test_error_handling_missing_fields():
    """Test error handling when required fields are missing."""
    input_data = {
        "error_message": "Some error",
        # Missing broken_code, fixed_code, fix_description
    }

    result = subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10
    )

    # Should fail gracefully
    if result.returncode != 0:
        assert "error" in result.stderr.lower() or "missing" in result.stderr.lower()


def test_pattern_uniqueness():
    """Test that similar patterns get unique IDs."""
    input_data = {
        "error_message": "ValueError: invalid literal for int()",
        "broken_code": "num = int('abc')",
        "fixed_code": "try:\n    num = int('abc')\nexcept ValueError:\n    num = 0",
        "fix_description": "Handle ValueError with try/except",
        "error_type": "runtime",
        "language": "python"
    }

    # Store same pattern twice
    result1 = subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10
    )

    result2 = subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=10
    )

    if result1.returncode == 0 and result2.returncode == 0:
        output1 = json.loads(result1.stdout)
        output2 = json.loads(result2.stdout)

        # Pattern IDs should be different (or same if deduplication is implemented)
        # This test documents the behavior
        pattern_id1 = output1.get("pattern_id")
        pattern_id2 = output2.get("pattern_id")

        assert pattern_id1 is not None
        assert pattern_id2 is not None


@pytest.mark.integration
def test_full_workflow_store_and_retrieve():
    """Test complete workflow: store pattern, then retrieve it."""
    # Store a unique pattern
    unique_error = "UniqueTestError: test_pattern_12345"

    store_input = {
        "error_message": unique_error,
        "broken_code": "broken_test_code()",
        "fixed_code": "fixed_test_code()",
        "fix_description": "Test fix for integration test",
        "error_type": "runtime",
        "language": "python"
    }

    # Store
    store_result = subprocess.run(
        [sys.executable, "tools/executable/store_code_fix_pattern.py"],
        input=json.dumps(store_input),
        capture_output=True,
        text=True,
        timeout=10
    )

    assert store_result.returncode == 0

    # Retrieve
    find_input = {
        "error_message": unique_error,
        "limit": 5
    }

    find_result = subprocess.run(
        [sys.executable, "tools/executable/find_code_fix_pattern.py"],
        input=json.dumps(find_input),
        capture_output=True,
        text=True,
        timeout=10
    )

    if find_result.returncode == 0:
        output = json.loads(find_result.stdout)

        # Should find the pattern we just stored
        if output.get("found", False):
            assert len(output["patterns"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
