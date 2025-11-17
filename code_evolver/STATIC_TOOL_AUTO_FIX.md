# Static Tool Auto-Fix System

**RAG-Based Learning for Missing Dependencies**

## Overview

The static tool auto-fix system automatically handles missing dependencies for static analysis tools (like autopep8, ruff, flake8, etc.) using a RAG-based learning approach.

Instead of just showing a warning, the system:
1. **Searches RAG** for known fixes
2. **Applies the fix** (pip install)
3. **Reruns the tool**
4. **Records success/failure** for future learning

## How It Works

### Example: autopep8 Missing

**Before (Manual):**
```
Warning: autopep8 not installed - skipping auto-formatting
Install with: pip install autopep8
```
User has to manually run pip install and restart the process.

**After (Automatic):**
```
→ No fix found in RAG, attempting install: pip install autopep8
→ Installing autopep8...
✓ autopep8 installed successfully
→ Running autopep8 on code...
✓ autopep8 successfully processed code
Recorded fix result in RAG (success rate: 100%)
```
System automatically installs, runs, and learns from the result!

## Architecture

### Method: `_auto_fix_static_tool_dependency()`

**Location**: `chat_cli.py:3899-4052`

**Parameters:**
- `tool_name`: Name of the missing tool (e.g., "autopep8")
- `install_command`: Install command (e.g., "pip install autopep8")
- `code`: Code to process
- `fix_function`: Callable that processes code after install

**Flow:**

```python
# 1. Search RAG for known fixes
existing_fixes = rag.find_by_tags(
    tags=["static_tool_fix", "dependency", tool_name],
    limit=1
)

# Show success rate from past attempts
if existing_fixes:
    success_rate = fix.metadata["success_rate"]
    console.print(f"Found fix in RAG (success rate: {success_rate:.0%})")

# 2. Install the package
result = subprocess.run(
    install_command.split(),
    capture_output=True,
    timeout=120
)

# 3. Rerun the tool
if install_success:
    fixed_code = fix_function(code)

# 4. Record result in RAG
rag.store_artifact(
    artifact_id=f"static_tool_dependency_{tool_name}",
    metadata={
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": success_rate
    },
    tags=["static_tool_fix", "dependency", tool_name]
)
```

## Learning Over Time

### First Attempt (No RAG Data)
```
→ No fix found in RAG, attempting install: pip install autopep8
→ Installing autopep8...
✓ autopep8 installed successfully
Recorded fix result in RAG (success rate: 100%)
```

### Second Attempt (With RAG Data)
```
→ Found fix in RAG: 'pip install autopep8' (success rate: 100%, 1/1 attempts)
→ Installing autopep8...
✓ autopep8 already satisfied
Recorded fix result in RAG (success rate: 100%)
```

### After Multiple Successes
```
→ Found fix in RAG: 'pip install autopep8' (success rate: 95%, 19/20 attempts)
```

The system builds confidence in fixes over time!

## Extending to Other Tools

### Example: Adding ruff support

```python
# In your static analysis code:
try:
    import ruff
    # Run ruff analysis
except ImportError:
    # Auto-fix missing dependency
    code = self._auto_fix_static_tool_dependency(
        tool_name="ruff",
        install_command="pip install ruff",
        code=code,
        fix_function=lambda c: run_ruff_on_code(c)
    )
```

### Example: Adding flake8 support

```python
try:
    import flake8
    # Run flake8
except ImportError:
    self._auto_fix_static_tool_dependency(
        tool_name="flake8",
        install_command="pip install flake8",
        code=code,
        fix_function=lambda c: run_flake8(c)
    )
```

## RAG Storage Format

Each fix is stored with comprehensive metadata:

```yaml
Artifact:
  artifact_id: "static_tool_dependency_autopep8"
  type: PATTERN
  name: "Static Tool Fix: autopep8"
  tags: [static_tool_fix, dependency, autopep8, auto_fix]

  content: |
    Fix for missing static tool: autopep8

    Install Command: pip install autopep8
    Success Rate: 95.0% (19/20 attempts)
    Last Updated: 2025-11-17T22:15:00

    This fix automatically installs the missing package and reruns the tool.

  metadata:
    tool_name: "autopep8"
    install_command: "pip install autopep8"
    success_count: 19
    failure_count: 1
    success_rate: 0.95
    last_attempt: "2025-11-17T22:15:00"
    last_success: true

  auto_embed: true  # Enables semantic search
```

## Success Tracking

The system tracks:
- **Success Count**: How many times the fix worked
- **Failure Count**: How many times it failed
- **Success Rate**: Percentage of successful attempts
- **Last Attempt**: When the fix was last tried
- **Last Success**: Whether the last attempt succeeded

This data informs future decisions and builds confidence.

## Integration Points

### Current Integration

**autopep8** (chat_cli.py:2965-2972):
```python
except ImportError:
    code = self._auto_fix_static_tool_dependency(
        tool_name="autopep8",
        install_command="pip install autopep8",
        code=code,
        fix_function=lambda c: __import__('autopep8').fix_code(c, options={...})
    )
```

### Potential Integrations

1. **Static Analysis Tools**:
   - ruff
   - flake8
   - pylint
   - mypy
   - bandit

2. **Formatters**:
   - black
   - isort
   - yapf

3. **Test Generators**:
   - hypothesis
   - faker

4. **Any Tool with Optional Dependencies**

## Benefits

### 1. Zero Manual Intervention
No more "install this package manually" messages. The system handles it automatically.

### 2. Self-Learning
Success rates build confidence. Fixes that consistently work get prioritized.

### 3. Shared Knowledge
All tasks benefit from fixes learned by previous tasks. One successful install helps all future attempts.

### 4. Transparent
Users see exactly what's happening:
- What fix was found
- Success rate from past attempts
- Install progress
- Tool execution results

### 5. Fail-Safe
If the fix fails, the system:
- Returns original code
- Records the failure
- Doesn't break the workflow

## Example Workflow

**Task**: Generate code that needs formatting

1. **Code Generated** → Contains formatting issues
2. **autopep8 Called** → ImportError: not installed
3. **RAG Searched** → Found fix (95% success rate, 19/20 attempts)
4. **Package Installed** → `pip install autopep8` (success)
5. **Tool Rerun** → Code formatted successfully
6. **Result Recorded** → Success rate now 95.24% (20/21 attempts)
7. **Workflow Continues** → No user intervention needed!

## Monitoring Fix Performance

### View All Static Tool Fixes
```python
fixes = rag.find_by_tags(["static_tool_fix", "dependency"], limit=100)
for fix in fixes:
    print(f"Tool: {fix.metadata['tool_name']}")
    print(f"Success Rate: {fix.metadata['success_rate']:.1%}")
    print(f"Attempts: {fix.metadata['success_count'] + fix.metadata['failure_count']}")
    print()
```

### Check Specific Tool
```python
autopep8_fixes = rag.find_by_tags(["static_tool_fix", "autopep8"], limit=1)
if autopep8_fixes:
    fix = autopep8_fixes[0]
    print(f"autopep8 success rate: {fix.metadata['success_rate']:.0%}")
```

## Future Enhancements

- [ ] Add timeout detection (if install takes too long)
- [ ] Support alternative install methods (conda, apt, brew)
- [ ] Detect version compatibility issues
- [ ] Cache successful installs (don't reinstall if already present)
- [ ] Add rollback on failure
- [ ] Support for tools requiring system-level dependencies
- [ ] Batch install multiple missing tools
- [ ] Expose fix stats in CLI (`/static-tools stats`)

## Technical Notes

- Fixes are stored with embeddings for semantic search
- Success rates are cumulative (all-time tracking)
- Install timeout is 120 seconds
- Original code is always preserved on failure
- Fix application is non-blocking (workflow continues on error)

## Comparison with Manual Approach

| Aspect | Manual | Auto-Fix |
|--------|--------|----------|
| User Action | Install manually, restart | None - automatic |
| Time | 2-5 minutes | 10-30 seconds |
| Learning | None | Builds knowledge base |
| Consistency | Varies | 95%+ success rate |
| Visibility | Error message only | Full progress shown |

---

**Result**: Static tool dependencies are now automatically resolved with learning-based confidence tracking!
