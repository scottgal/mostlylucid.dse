# Import Strategy for Generated Code

## Problem

Generated nodes currently create code with `from node_runtime import call_tool` which:
1. Doesn't exist in the node's import path
2. Causes tests to fail
3. Is a "phantom import" - the LLM invented it

## Solutions

### Option 1: Declare Requirements (Recommended)
When generating code, output a `requirements.txt` or `metadata.json` per node:

```json
{
  "node_id": "write_a_haiku",
  "imports": {
    "stdlib": ["json", "sys"],
    "pip": [],
    "local": [
      {
        "module": "node_runtime",
        "path": "../../node_runtime.py",
        "setup": "sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))"
      }
    ]
  },
  "generated_by": "claude-3-5-sonnet-20241022",
  "timestamp": "2025-01-15T..."
}
```

Then the test runner can:
- Auto-add the path setup code
- Verify all imports are resolvable
- Install pip requirements

### Option 2: Make node_runtime a Pip Package
Create a proper Python package:

```
code_evolver/
├── pyproject.toml
├── src/
│   └── code_evolver/
│       ├── __init__.py
│       └── node_runtime.py
```

Then `pip install -e .` makes it importable everywhere.

**Benefits:**
- Clean imports: `from code_evolver.node_runtime import call_tool`
- Works in tests automatically
- Proper packaging

**Drawbacks:**
- Requires package installation
- More setup for users

### Option 3: Self-Contained Nodes (Simplest)
Generate code that doesn't need external imports:

```python
import json
import sys

def main():
    input_data = json.load(sys.stdin)

    # All logic here - no external calls
    result = input_data.get('a', 0) + input_data.get('b', 0)

    print(json.dumps({"result": result}))

if __name__ == "__main__":
    main()
```

**Benefits:**
- No import issues
- Standalone - easy to test
- Fast validation

**Drawbacks:**
- Can't call other tools/nodes
- Duplicate code if logic is shared

### Option 4: Auto-Path Setup
Add path setup automatically to every generated node:

```python
import os
import sys
# Auto-generated path setup
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Now imports work
from node_runtime import call_tool
import json

def main():
    # ...
```

## Recommendation

**Use Option 1 (Declare Requirements) + Option 4 (Auto-Path Setup):**

1. **During code generation:**
   - Detect what imports the code needs
   - Output `metadata.json` with requirements
   - Auto-add path setup if using local modules

2. **During validation:**
   - Read `metadata.json`
   - Use `interface_validator.py` to check all imports resolve
   - Fail fast if phantom imports detected

3. **During test execution:**
   - Read `metadata.json`
   - Auto-install pip requirements if needed
   - Verify path setup is correct

## Implementation

Add to code generation prompt:
```
When generating code:
1. Only import from:
   - Python stdlib (json, sys, os, etc.)
   - Explicitly available tools in this environment
   - Pip-installed packages you explicitly declare

2. If you need a local module like node_runtime:
   - Add path setup: sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
   - Document it in metadata

3. Output metadata.json with:
   {
     "imports": {
       "stdlib": ["json", "sys"],
       "pip": [],
       "local": [{"module": "node_runtime", "setup": "..."}]
     }
   }

4. NEVER invent imports that don't exist
```

## Validation

Use the enhanced `interface_validator.py`:

```bash
# Validate node before running
python src/interface_validator.py nodes/my_node/main.py

# If it passes, imports are all resolvable
```

The validator checks:
- ✓ Python stdlib imports (built-in)
- ✓ Pip-installed packages (via importlib)
- ✓ Local files in same directory
- ✓ Files in parent with path setup
- ✗ Phantom imports (invented by LLM)
