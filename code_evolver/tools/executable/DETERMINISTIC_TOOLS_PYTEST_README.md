# Pytest Testing Guide for Deterministic Python Tools

This guide explains how to test all deterministic Python tools using pytest.

## Table of Contents
1. [Setup](#setup)
2. [Running Tests](#running-tests)
3. [Test Structure](#test-structure)
4. [Mocking](#mocking)
5. [Coverage](#coverage)
6. [Individual Tool Tests](#individual-tool-tests)

---

## Setup

### Install Dependencies
```bash
# Install pytest and required tools
pip install pytest pytest-cov pytest-mock

# Install all deterministic tools
pip install ruff autoflake pyupgrade mypy bandit

# Or use the auto-install feature
python ruff_checker.py --install
python autoflake_checker.py --install
python pyupgrade_checker.py --install
python mypy_checker.py --install
python bandit_checker.py --install
```

### Project Structure
```
code_evolver/tools/executable/
├── ruff_checker.py
├── ruff_checker.yaml
├── ruff_checker.feature              # Behave BDD spec
├── test_ruff_checker.py               # Pytest unit tests
├── ruff_checker_mocks.py              # Mock data/fixtures
├── autoflake_checker.py
├── test_autoflake_checker.py
├── autoflake_checker_mocks.py
├── ... (similar for other tools)
└── conftest.py                        # Shared pytest fixtures
```

---

## Running Tests

### Run All Tool Tests
```bash
# Run all tests
pytest tools/executable/test_*_checker.py -v

# Run with coverage
pytest tools/executable/test_*_checker.py --cov=tools/executable --cov-report=html

# Run specific tool tests
pytest tools/executable/test_ruff_checker.py -v
```

### Run Tests for Specific Tool
```bash
# Ruff
pytest tools/executable/test_ruff_checker.py -v

# Autoflake
pytest tools/executable/test_autoflake_checker.py -v

# Pyupgrade
pytest tools/executable/test_pyupgrade_checker.py -v

# MyPy
pytest tools/executable/test_mypy_checker.py -v

# Bandit
pytest tools/executable/test_bandit_checker.py -v
```

### Run Tests by Category
```bash
# Happy path tests only
pytest -m happy_path

# Auto-fix tests
pytest -m auto_fix

# Integration tests
pytest -m integration

# Performance tests
pytest -m performance
```

### Parallel Execution
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tools/executable/test_*_checker.py -n auto
```

---

## Test Structure

### Test Categories

Each tool test file includes:

1. **Unit Tests** - Test individual functions
2. **Integration Tests** - Test tool execution end-to-end
3. **Mocking Tests** - Test with mocked subprocess calls
4. **Performance Tests** - Test execution speed
5. **Edge Case Tests** - Test error handling

### Test Markers

```python
import pytest

@pytest.mark.happy_path        # Normal successful execution
@pytest.mark.unhappy_path      # Error conditions
@pytest.mark.auto_fix          # Auto-fix functionality
@pytest.mark.integration       # Integration with pipeline
@pytest.mark.performance       # Performance benchmarks
@pytest.mark.edge_case         # Edge cases and error handling
@pytest.mark.mock              # Uses mocks
```

### Example Test Structure

```python
# test_ruff_checker.py
import pytest
from pathlib import Path
from ruff_checker import check_ruff_installed, run_ruff_check

class TestRuffInstallation:
    """Tests for ruff installation check."""

    def test_check_installed_when_available(self, mock_ruff_installed):
        """Test that ruff is detected when installed."""
        assert check_ruff_installed() is True

    def test_check_installed_when_missing(self, mock_ruff_not_installed):
        """Test that missing ruff is detected."""
        assert check_ruff_installed() is False

class TestRuffCheck:
    """Tests for ruff check functionality."""

    @pytest.mark.happy_path
    def test_check_clean_file(self, clean_python_file):
        """Test checking a file with no issues."""
        result = run_ruff_check(clean_python_file)
        assert result['success'] is True
        assert result['issues_found'] == 0

    @pytest.mark.auto_fix
    def test_auto_fix_unused_imports(self, file_with_unused_imports):
        """Test auto-fixing unused imports."""
        result = run_ruff_check(file_with_unused_imports, auto_fix=True)
        assert result['issues_fixed'] > 0
        # Verify file was modified
        content = file_with_unused_imports.read_text()
        assert 'unused_import' not in content
```

---

## Mocking

### Mock Strategy

Each tool has a companion `<tool>_mocks.py` file with:
- Mock subprocess responses
- Sample test files (clean, with issues, edge cases)
- Mock installation responses
- Fixture data

### Shared Fixtures (conftest.py)

```python
# conftest.py
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_python_file():
    """Create a temporary Python file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('print("Hello, World!")\n')
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()

@pytest.fixture
def mock_subprocess_success(mocker):
    """Mock subprocess.run to return success."""
    mock = mocker.patch('subprocess.run')
    mock.return_value.returncode = 0
    mock.return_value.stdout = ''
    mock.return_value.stderr = ''
    return mock

@pytest.fixture
def mock_subprocess_failure(mocker):
    """Mock subprocess.run to return failure."""
    mock = mocker.patch('subprocess.run')
    mock.return_value.returncode = 1
    mock.return_value.stdout = 'Error: issues found'
    mock.return_value.stderr = ''
    return mock
```

### Tool-Specific Mocks

```python
# ruff_checker_mocks.py
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def clean_python_file():
    """Python file with no linting issues."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''#!/usr/bin/env python3
"""Clean Python file."""

def main():
    """Main function."""
    print("Hello, World!")

if __name__ == '__main__':
    main()
''')
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()

@pytest.fixture
def file_with_unused_imports():
    """Python file with unused imports."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''import sys
import os  # unused
import json  # unused

def main():
    print(sys.version)

if __name__ == '__main__':
    main()
''')
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()

@pytest.fixture
def mock_ruff_output():
    """Mock ruff JSON output."""
    return '''[
  {
    "code": "F401",
    "message": "'os' imported but unused",
    "location": {
      "row": 2,
      "column": 1
    },
    "filename": "test.py"
  }
]'''
```

---

## Coverage

### Running Coverage

```bash
# Generate HTML coverage report
pytest tools/executable/test_*_checker.py --cov=tools/executable --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Requirements

Each tool should aim for:
- **Line Coverage**: ≥ 90%
- **Branch Coverage**: ≥ 85%
- **Function Coverage**: 100%

### Key Areas to Cover
- ✅ Installation check
- ✅ Tool execution (success and failure)
- ✅ Auto-fix functionality
- ✅ JSON output parsing
- ✅ Error handling (file not found, tool not installed)
- ✅ Edge cases (empty files, syntax errors)
- ✅ Timeout handling

---

## Individual Tool Tests

### 1. Ruff Checker Tests

**Test File**: `test_ruff_checker.py`
**Mock File**: `ruff_checker_mocks.py`

```bash
pytest tools/executable/test_ruff_checker.py -v
```

**Key Test Cases**:
- ✅ Check clean file (no issues)
- ✅ Detect linting issues
- ✅ Auto-fix issues
- ✅ Format code
- ✅ JSON output parsing
- ✅ Handle syntax errors
- ✅ Performance on large files

**Example Test**:
```python
def test_ruff_auto_fix(file_with_unused_imports, mocker):
    """Test ruff auto-fixes unused imports."""
    # Mock ruff execution
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = ''

    # Run check with auto-fix
    result = run_ruff_check(file_with_unused_imports, auto_fix=True)

    # Verify
    assert result['success'] is True
    assert '--fix' in mock_run.call_args[0][0]
```

---

### 2. Autoflake Checker Tests

**Test File**: `test_autoflake_checker.py`
**Mock File**: `autoflake_checker_mocks.py`

```bash
pytest tools/executable/test_autoflake_checker.py -v
```

**Key Test Cases**:
- ✅ Remove unused stdlib imports
- ✅ Remove unused third-party imports (aggressive)
- ✅ Remove unused variables
- ✅ Remove duplicate dict keys
- ✅ Check mode (no modifications)
- ✅ File modification verification

**Example Test**:
```python
def test_autoflake_removes_unused_imports(file_with_unused_imports):
    """Test autoflake removes unused imports."""
    original_content = file_with_unused_imports.read_text()

    # Run autoflake with fix
    result = run_autoflake(file_with_unused_imports, auto_fix=True)

    # Verify
    assert result['changes_needed'] is True
    new_content = file_with_unused_imports.read_text()
    assert new_content != original_content
    assert 'import os' not in new_content  # unused import removed
```

---

### 3. Pyupgrade Checker Tests

**Test File**: `test_pyupgrade_checker.py`
**Mock File**: `pyupgrade_checker_mocks.py`

```bash
pytest tools/executable/test_pyupgrade_checker.py -v
```

**Key Test Cases**:
- ✅ Upgrade % formatting to f-strings
- ✅ Upgrade .format() to f-strings
- ✅ Upgrade dict() to {}
- ✅ Upgrade set([]) to {}
- ✅ Modernize type annotations
- ✅ Target specific Python versions
- ✅ Keep runtime typing

**Example Test**:
```python
def test_pyupgrade_fstring_conversion():
    """Test pyupgrade converts to f-strings."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('x = "%s %s" % (a, b)\n')
        temp_path = Path(f.name)

    # Run pyupgrade
    result = run_pyupgrade(temp_path, auto_fix=True, python_version='py38-plus')

    # Verify
    assert result['changes_needed'] is True
    new_content = temp_path.read_text()
    assert 'f"' in new_content or "f'" in new_content
    temp_path.unlink()
```

---

### 4. MyPy Checker Tests

**Test File**: `test_mypy_checker.py`
**Mock File**: `mypy_checker_mocks.py`

```bash
pytest tools/executable/test_mypy_checker.py -v
```

**Key Test Cases**:
- ✅ Check well-typed file
- ✅ Detect type errors
- ✅ Parse error messages
- ✅ Strict vs non-strict mode
- ✅ Ignore missing imports
- ✅ JSON output parsing
- ✅ Error code extraction

**Example Test**:
```python
def test_mypy_detects_type_error():
    """Test mypy detects type mismatches."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def add(a: int, b: int) -> int:
    return a + b

result: str = add(1, 2)  # Type error: int assigned to str
''')
        temp_path = Path(f.name)

    # Run mypy
    result = run_mypy(temp_path, strict=True)

    # Verify
    assert result['success'] is False
    assert result['errors_found'] > 0
    temp_path.unlink()
```

---

### 5. Bandit Checker Tests

**Test File**: `test_bandit_checker.py`
**Mock File**: `bandit_checker_mocks.py`

```bash
pytest tools/executable/test_bandit_checker.py -v
```

**Key Test Cases**:
- ✅ Scan secure file
- ✅ Detect SQL injection
- ✅ Detect hardcoded passwords
- ✅ Detect use of eval()
- ✅ Filter by severity level
- ✅ Filter by confidence level
- ✅ JSON output parsing
- ✅ Recursive directory scanning

**Example Test**:
```python
def test_bandit_detects_sql_injection():
    """Test bandit detects SQL injection vulnerability."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()
''')
        temp_path = Path(f.name)

    # Run bandit
    result = run_bandit(temp_path, output_json=True)

    # Verify
    assert result['success'] is False
    assert result['issues_found'] > 0
    assert any('sql' in issue['issue_text'].lower() for issue in result['issues'])
    temp_path.unlink()
```

---

## Performance Testing

### Performance Test Template

```python
import time
import pytest

@pytest.mark.performance
def test_ruff_performance_large_file(large_python_file):
    """Test ruff performance on large file."""
    start_time = time.time()

    result = run_ruff_check(large_python_file)

    execution_time = (time.time() - start_time) * 1000  # ms

    # Verify performance
    assert execution_time < 500, f"Ruff took {execution_time}ms (expected < 500ms)"
    assert result is not None

@pytest.fixture
def large_python_file():
    """Generate large Python file (1000 lines)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('"""Large test file."""\n\n')
        for i in range(1000):
            f.write(f'def function_{i}():\n')
            f.write(f'    return {i}\n\n')
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Deterministic Tools

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          pip install pytest pytest-cov pytest-mock
          pip install ruff autoflake pyupgrade mypy bandit

      - name: Run tests
        run: |
          pytest tools/executable/test_*_checker.py -v --cov=tools/executable --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./coverage.xml
```

---

## Debugging Tests

### Run Single Test
```bash
pytest tools/executable/test_ruff_checker.py::TestRuffCheck::test_check_clean_file -v
```

### Show Print Statements
```bash
pytest tools/executable/test_ruff_checker.py -v -s
```

### Drop into Debugger on Failure
```bash
pytest tools/executable/test_ruff_checker.py -v --pdb
```

### Verbose Output
```bash
pytest tools/executable/test_ruff_checker.py -vv
```

---

## Troubleshooting

### Common Issues

**Issue**: Tool not found in tests
```bash
Solution: Install tool or use --install flag
pip install <tool>
```

**Issue**: Temp files not cleaned up
```bash
Solution: Use pytest fixtures with proper cleanup
yield temp_file
temp_file.unlink()
```

**Issue**: Tests fail on Windows
```bash
Solution: Use Path objects and proper line endings
from pathlib import Path
path = Path('file.py')
```

**Issue**: Mock not working
```bash
Solution: Patch the correct target
# Wrong
mocker.patch('subprocess.run')

# Right (patch where it's used)
mocker.patch('ruff_checker.subprocess.run')
```

---

## Best Practices

1. **Use fixtures** for test data
2. **Mock external dependencies** (subprocess, file I/O when appropriate)
3. **Test edge cases** (empty files, large files, syntax errors)
4. **Verify file modifications** in auto-fix tests
5. **Use markers** to categorize tests
6. **Maintain 90%+ coverage**
7. **Test performance** on realistic file sizes
8. **Clean up temp files** properly

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-mock Documentation](https://pytest-mock.readthedocs.io/)
- [Pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Behave BDD Documentation](https://behave.readthedocs.io/)
