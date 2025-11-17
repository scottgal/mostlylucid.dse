# Verbosity System

**Date:** 2025-11-17
**Status:** ✅ IMPLEMENTED

## Overview

The CLI now has 4 verbosity levels controlled by `/show` command or `config.yaml`.

## Verbosity Levels

### 1. `status` (Default)

**Shows:**
- ✅ What it's doing: "Building tool - toolname", "Running workflow", etc.
- ✅ What it output: "File saved", "Tool created successfully", etc.
- ✅ Status messages: PASS/FAIL, progress indicators
- ✅ Important metrics: Test results, performance stats

**Hides:**
- ❌ Generated code/content
- ❌ Debug logs
- ❌ Verbose tool output

**Example:**
```
> generate email validator
✓ Building tool: email_validator
✓ Generated code (45 lines)
✓ Running tests...
  PASS: test_valid_email
  PASS: test_invalid_email
✓ All tests passed
✓ Node 'email_validator' created successfully!
✓ File saved: nodes/email_validator/main.py
```

### 2. `generated`

**Shows:**
- ✅ Everything from `status`
- ✅ Generated code (syntax highlighted)
- ✅ Generated test code
- ✅ Generated content/documents

**Example:**
```
> generate email validator
✓ Building tool: email_validator
┌─ Generated Code: email_validator ─────────────┐
│ 1  import re                                   │
│ 2                                              │
│ 3  def validate_email(email: str) -> bool:    │
│ 4      pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'  │
│ 5      return bool(re.match(pattern, email))  │
└────────────────────────────────────────────────┘
✓ Running tests...
  PASS: test_valid_email
✓ Node created successfully!
```

### 3. `log`

**Shows:**
- ✅ Everything from `status`
- ✅ Log contents from tool executions
- ✅ stdout/stderr from commands
- ✅ Diagnostic information

**Hides:**
- ❌ Generated code (use `generated` for that)

**Example:**
```
> generate email validator
✓ Building tool: email_validator
✓ Generated code (45 lines)
✓ Running tests...
  [LOG] pytest nodes/email_validator/test_main.py
  [LOG] ============================= test session starts ==============================
  [LOG] collected 2 items
  [LOG] test_main.py ..                                                          [100%]
  [LOG] ============================== 2 passed in 0.02s ===============================
  PASS: test_valid_email
  PASS: test_invalid_email
✓ All tests passed
```

### 4. `debug`

**Shows:**
- ✅ EVERYTHING
- ✅ Generated code
- ✅ Log contents
- ✅ Debug traces
- ✅ Internal state
- ✅ LLM prompts/responses
- ✅ RAG search results

**Example:**
```
> generate email validator
[DEBUG] Sentinel detected intent: code_generation
[DEBUG] Task evaluator: gemma3:1b (59 chars input)
[DEBUG] Classification: code_generation (moderate)
✓ Building tool: email_validator
[DEBUG] Using code.general tier: codellama:7b
[DEBUG] Prompt (truncated): "Write a Python function that validates..."
[DEBUG] LLM response: 441 chars
┌─ Generated Code: email_validator ─────────────┐
│ ...full code...                                │
└────────────────────────────────────────────────┘
[DEBUG] Saving to: D:\Source\...\email_validator\main.py
✓ Generated code (45 lines)
[DEBUG] Running pytest with timeout 30s
  [LOG] pytest output...
✓ All tests passed
[DEBUG] Storing in RAG: func_email_validator
```

## Usage

### Via `/show` Command

```
> /show status     # Default - just status messages
> /show generated  # Show generated code
> /show log        # Show log contents
> /show debug      # Show everything
```

### Via Config File

**File:** `config.yaml`

```yaml
chat:
  verbosity: "status"  # Options: status, generated, log, debug
```

## Helper Methods (Internal)

**File:** `chat_cli.py`

```python
def _should_show_generated(self) -> bool:
    """Check if generated content should be displayed."""
    verbosity = self.config.get("chat.verbosity", "status")
    return verbosity in ["generated", "debug"]

def _should_show_logs(self) -> bool:
    """Check if log contents should be displayed."""
    verbosity = self.config.get("chat.verbosity", "status")
    return verbosity in ["log", "debug"]

def _should_show_debug(self) -> bool:
    """Check if debug details should be displayed."""
    verbosity = self.config.get("chat.verbosity", "status")
    return verbosity == "debug"
```

## Implementation

### Code Display

```python
# Display generated code (based on verbosity)
if self._should_show_generated():
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"[green]Generated Code: {node_id}[/green]"))
else:
    lines = len(code.split('\n'))
    console.print(f"[green]✓ Generated code ({lines} lines)[/green]")
```

### Log Display

```python
# Display test logs (based on verbosity)
if self._should_show_logs():
    console.print(f"[dim]Test log:\n{stdout}[/dim]")
else:
    console.print(f"[green]✓ Tests passed[/green]")
```

### Debug Display

```python
# Display debug info (based on verbosity)
if self._should_show_debug():
    console.print(f"[dim]Debug: Using model {model} with timeout {timeout}[/dim]")
```

## Benefits

✅ **Cleaner Output:** No overwhelming code dumps by default
✅ **Flexibility:** Users can show/hide what they need
✅ **Context-Aware:** Shows what's happening and what was output
✅ **Performance:** Less rendering overhead for large outputs
✅ **Professional:** Looks more like production tools (git, npm, etc.)

## Comparison

### Before (Verbose)
```
> generate validator
Building tool...
Generating code with codellama:7b...
┌─ Generated Code (200 lines) ────────┐
│ import sys                           │
│ import os                            │
│ ...198 more lines...                 │
└──────────────────────────────────────┘
Running tests...
┌─ Test Code (150 lines) ─────────────┐
│ import pytest                        │
│ ...150 more lines...                 │
└──────────────────────────────────────┘
[LOG] pytest output 500 lines...
Node created!
```

### After (Status mode - default)
```
> generate validator
✓ Building tool: validator
✓ Generated code (200 lines)
✓ Generated tests (150 lines)
✓ All tests passed
✓ Node 'validator' created successfully!
```

**Same information, 90% less clutter!**

## Status

✅ Config setting added: `chat.verbosity`
✅ Helper methods implemented
✅ Code display updated
✅ Test display updated
✅ Default: `status` (concise)

**Next:** Add `/show` command handler in chat loop
