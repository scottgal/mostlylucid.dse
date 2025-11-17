# Deterministic Python Tools - Interface Documentation

This document describes the interface and usage for all deterministic Python static analysis tools in the pipeline.

## Overview

All deterministic tools follow a consistent interface pattern:

### Exit Codes
- **0**: No issues found (or all successfully fixed)
- **1**: Issues found (check mode) or unable to fix all issues
- **2**: Error (file not found, tool not installed, invalid arguments)

### Common Flags
- `--fix`: Apply automatic fixes (where supported)
- `--json`: Output results in JSON format
- `--install`: Auto-install the tool if not found

### JSON Output Schema
All tools with `--json` support return:
```json
{
  "success": boolean,
  "issues_found": integer,
  "output": string,
  "errors": [...]  // Tool-specific details
}
```

---

## 1. Ruff Checker

### Purpose
Fast Python linter and formatter that replaces flake8, isort, pyupgrade, and more.

### Installation
```bash
pip install ruff
```

### Usage
```bash
# Check only
python ruff_checker.py <file_path>

# Check and auto-fix
python ruff_checker.py <file_path> --fix

# Check, fix, and format
python ruff_checker.py <file_path> --fix --format

# JSON output
python ruff_checker.py <file_path> --json
```

### Parameters
- `file_path` (required): Path to Python file
- `--fix`: Apply safe auto-fixes
- `--format`: Also run code formatting
- `--json`: Output results as JSON
- `--install`: Install ruff if not found

### Output Schema (JSON)
```json
{
  "file": "path/to/file.py",
  "check": {
    "success": true|false,
    "issues_found": 0,
    "issues_fixed": 0,
    "output": "...",
    "issues": [
      {
        "code": "F401",
        "message": "...",
        "location": {"row": 10, "column": 5}
      }
    ]
  },
  "format": {
    "success": true|false,
    "formatted": true|false,
    "needs_formatting": true|false,
    "output": "..."
  }
}
```

### Integration
- **Pipeline Priority**: 135
- **Auto-fix**: ✅ Yes
- **Category**: code-quality
- **Replaces**: flake8, isort, black (partially)

---

## 2. Autoflake Checker

### Purpose
Removes unused imports and unused variables from Python code.

### Installation
```bash
pip install autoflake
```

### Usage
```bash
# Check only
python autoflake_checker.py <file_path>

# Check and fix
python autoflake_checker.py <file_path> --fix

# Aggressive mode (remove all unused imports)
python autoflake_checker.py <file_path> --fix --aggressive
```

### Parameters
- `file_path` (required): Path to Python file
- `--fix`: Apply fixes in-place
- `--aggressive`: Remove all unused imports (not just stdlib)
- `--install`: Install autoflake if not found

### Output Schema
```json
{
  "success": true|false,
  "changes_needed": true|false,
  "output": "...",
  "diff": "..."  // Only in check mode
}
```

### Integration
- **Pipeline Priority**: 130
- **Auto-fix**: ✅ Yes
- **Category**: code-cleanup
- **Runs After**: ruff

---

## 3. Pyupgrade Checker

### Purpose
Automatically upgrades Python syntax for newer versions (f-strings, type hints, etc.)

### Installation
```bash
pip install pyupgrade
```

### Usage
```bash
# Check only
python pyupgrade_checker.py <file_path>

# Check and fix (default: Python 3.8+)
python pyupgrade_checker.py <file_path> --fix

# Target specific Python version
python pyupgrade_checker.py <file_path> --fix --py39-plus
python pyupgrade_checker.py <file_path> --fix --py310-plus
python pyupgrade_checker.py <file_path> --fix --py311-plus

# Keep runtime typing annotations
python pyupgrade_checker.py <file_path> --fix --keep-runtime-typing
```

### Parameters
- `file_path` (required): Path to Python file
- `--fix`: Apply fixes in-place
- `--py36-plus`, `--py37-plus`, `--py38-plus`, `--py39-plus`, `--py310-plus`, `--py311-plus`: Target Python version
- `--keep-runtime-typing`: Keep runtime type annotations
- `--install`: Install pyupgrade if not found

### Output Schema
```json
{
  "success": true|false,
  "changes_needed": true|false,
  "output": "...",
  "original": "...",  // Original code
  "upgraded": "..."   // Upgraded code
}
```

### Transformations
- ` '%s' % x` → `f'{x}'`
- `'{}'.format(x)` → `f'{x}'`
- `dict()` → `{}`
- `set([1, 2])` → `{1, 2}`
- Old-style type annotations → Modern syntax

### Integration
- **Pipeline Priority**: 125
- **Auto-fix**: ✅ Yes
- **Category**: code-modernization
- **Runs After**: autoflake

---

## 4. MyPy Type Checker

### Purpose
Static type checker that finds type errors before runtime.

### Installation
```bash
pip install mypy
```

### Usage
```bash
# Check with strict mode (default)
python mypy_checker.py <file_path>

# Check without strict mode
python mypy_checker.py <file_path> --no-strict

# Ignore missing imports
python mypy_checker.py <file_path> --ignore-missing-imports

# JSON output
python mypy_checker.py <file_path> --json
```

### Parameters
- `file_path` (required): Path to Python file
- `--no-strict`: Disable strict mode
- `--ignore-missing-imports`: Ignore missing import stubs
- `--json`: Output results as JSON
- `--install`: Install mypy if not found

### Output Schema (JSON)
```json
{
  "success": true|false,
  "errors_found": 0,
  "output": "...",
  "errors": [
    {
      "file": "test.py",
      "line": "10",
      "column": "5",
      "level": "error",
      "message": "Argument 1 has incompatible type..."
    }
  ]
}
```

### Integration
- **Pipeline Priority**: 115
- **Auto-fix**: ❌ No (reports only)
- **Category**: type-checking
- **Runs After**: pyupgrade (sees modernized code)

---

## 5. Bandit Security Scanner

### Purpose
Scans for common security issues in Python code (SQL injection, hardcoded passwords, etc.)

### Installation
```bash
pip install bandit
```

### Usage
```bash
# Scan file or directory
python bandit_checker.py <file_path>

# Filter by severity level
python bandit_checker.py <file_path> --level high
python bandit_checker.py <file_path> --level medium

# Filter by confidence
python bandit_checker.py <file_path> --confidence high

# JSON output
python bandit_checker.py <file_path> --json

# Non-recursive (files only)
python bandit_checker.py <file_path> --no-recursive
```

### Parameters
- `file_path` (required): Path to Python file or directory
- `--json`: Output results as JSON
- `--level`: Minimum severity level (low, medium, high)
- `--confidence`: Minimum confidence level (low, medium, high)
- `--no-recursive`: Don't recursively scan directories
- `--install`: Install bandit if not found

### Output Schema (JSON)
```json
{
  "success": true|false,
  "issues_found": 5,
  "high_severity": 1,
  "medium_severity": 3,
  "low_severity": 1,
  "output": "...",
  "issues": [
    {
      "code": "B608",
      "issue_text": "Possible SQL injection vector...",
      "issue_severity": "MEDIUM",
      "issue_confidence": "HIGH",
      "line_number": 42,
      "filename": "test.py"
    }
  ],
  "metrics": {...}
}
```

### Common Vulnerabilities Detected
- SQL injection (B608)
- Command injection (B602, B605)
- Hardcoded passwords (B105, B106)
- Use of `eval()` (B307)
- Weak crypto (B303, B304, B305)
- Use of `pickle` (B301, B302)
- Insecure random (B311)

### Integration
- **Pipeline Priority**: 105
- **Auto-fix**: ❌ No (reports only)
- **Category**: security
- **Runs After**: mypy

---

## Pipeline Integration

### Execution Order (by Priority)
1. **Syntax validation** (200) - Fast AST check
2. **Main function check** (180) - Structural validation
3. **JSON output check** (150) - Output validation
4. **Stdin usage check** (140) - Input validation
5. **Ruff** (135) - Linting & formatting
6. **Autoflake** (130) - Cleanup
7. **Pyupgrade** (125) - Modernization
8. **MyPy** (115) - Type checking
9. **Bandit** (105) - Security scanning

### Auto-fix Cascade
When `--fix` is enabled:
1. Ruff fixes linting issues and formats code
2. Autoflake removes unused imports/variables
3. Pyupgrade modernizes syntax
4. MyPy checks types (no fix, may fail)
5. Bandit scans security (no fix, may fail)

### Failure Handling
- **Auto-fix tools (ruff, autoflake, pyupgrade)**: Apply fixes, then re-run validation
- **Report-only tools (mypy, bandit)**: Report issues, escalate to AI fix route if failures persist

---

## Error Handling

All tools follow consistent error handling:

### File Not Found
```bash
$ python <tool>_checker.py nonexistent.py
Error: File not found: nonexistent.py
Exit code: 2
```

### Tool Not Installed
```bash
$ python <tool>_checker.py test.py
Error: <tool> is not installed. Run with --install or: pip install <tool>
Exit code: 2
```

### Auto-install
```bash
$ python <tool>_checker.py test.py --install
<Tool> not found. Attempting to install...
<Tool> installed successfully.
[... normal execution ...]
```

---

## Testing

Each tool includes:
- **Behave BDD specs**: `<tool>_checker.feature`
- **Pytest unit tests**: `test_<tool>_checker.py`
- **Test README**: `<tool>_PYTEST_README.md`
- **Mock data**: `<tool>_mocks.py`

See individual pytest READMEs for testing instructions.

---

## Performance Benchmarks

Typical execution times on 1000-line Python file:

| Tool      | Check Time | Fix Time | Memory Usage |
|-----------|-----------|----------|--------------|
| Ruff      | ~200ms    | ~300ms   | ~30 MB       |
| Autoflake | ~500ms    | ~700ms   | ~25 MB       |
| Pyupgrade | ~600ms    | ~800ms   | ~25 MB       |
| MyPy      | ~2s       | N/A      | ~80 MB       |
| Bandit    | ~1.5s     | N/A      | ~60 MB       |

**Total pipeline**: ~5s (sequential), ~3s (with caching)

---

## Version Compatibility

All tools support:
- **Python 3.8+** (recommended)
- **Windows, macOS, Linux**

Individual tool compatibility:
- **Ruff**: Python 3.7+ (written in Rust)
- **Autoflake**: Python 3.6+
- **Pyupgrade**: Python 3.6+
- **MyPy**: Python 3.7+
- **Bandit**: Python 3.6+
