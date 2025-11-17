# Adaptive Fix Validation System - Codegen Approach

**Date:** 2025-11-17
**Status:** 🔬 Design Proposal
**Priority:** HIGH

---

## Problem

Current fix validation is **hardcoded** for specific patterns:
- ModuleNotFoundError validation
- Import removal validation
- Addition validation

**Issues:**
1. Not scalable - need to manually add validation for each fix type
2. Not adaptive - can't learn new validation patterns
3. Not extensible - no way for users to add custom validations

---

## Solution: Fix Validation as Executable Tools

### Core Idea

Create **validator tools** that can:
1. Be **generated** by LLMs (codegen)
2. Be **stored** in RAG (reusable)
3. Be **executed** to validate fixes (automated)
4. Be **learned** from successful/failed fixes (self-improving)

---

## Architecture

### 1. Validator Tool Structure

Each validator is an executable tool that:
- Takes: original code, fixed code, fix description, error
- Returns: validation result (passed/failed + reason)

**Example: ModuleNotFoundError Validator**

```python
#!/usr/bin/env python3
"""Validates that ModuleNotFoundError fixes are actually applied."""

import sys, json, re

def validate_fix(original_code, fixed_code, fix_description, error_message):
    """
    Validate that a claimed ModuleNotFoundError fix was actually applied.

    Args:
        original_code: Code before fix
        fixed_code: Code after fix
        fix_description: What the LLM claims it did
        error_message: The error being fixed

    Returns:
        {
            "valid": bool,
            "reason": str,
            "confidence": float (0-1)
        }
    """
    fix_lower = fix_description.lower()

    # Check if this validator applies
    if 'modulenotfounderror' not in error_message.lower():
        return {"valid": True, "reason": "Not applicable", "confidence": 0.0}

    # Extract module name from error
    module_match = re.search(r"No module named '(\w+)'", error_message)
    if not module_match:
        return {"valid": True, "reason": "Cannot parse error", "confidence": 0.0}

    module_name = module_match.group(1)

    # If fix claims to add path setup, verify it's there
    if 'path setup' in fix_lower or 'sys.path' in fix_lower:
        if 'sys.path.insert' in fixed_code or 'sys.path.append' in fixed_code:
            return {
                "valid": True,
                "reason": f"sys.path setup found for {module_name}",
                "confidence": 0.9
            }
        else:
            return {
                "valid": False,
                "reason": f"Claimed to add path setup but sys.path not in code",
                "confidence": 0.95
            }

    # If fix claims to remove import, verify it's gone
    if 'removed import' in fix_lower or 'unused import' in fix_lower:
        import_pattern = f"from {module_name} import|import {module_name}"
        if re.search(import_pattern, fixed_code):
            return {
                "valid": False,
                "reason": f"Claimed to remove {module_name} import but it's still there",
                "confidence": 0.95
            }
        else:
            return {
                "valid": True,
                "reason": f"Import {module_name} successfully removed",
                "confidence": 0.9
            }

    # Default: can't validate, allow it
    return {"valid": True, "reason": "No specific validation rule", "confidence": 0.5}

# Main
if __name__ == "__main__":
    input_data = json.loads(sys.stdin.read())
    result = validate_fix(
        input_data["original_code"],
        input_data["fixed_code"],
        input_data["fix_description"],
        input_data["error_message"]
    )
    print(json.dumps(result))
```

**YAML Definition:**

```yaml
name: "ModuleNotFoundError Fix Validator"
type: "executable"
description: |
  Validates that claimed ModuleNotFoundError fixes are actually applied to code.

  Checks:
  - If path setup claimed, verify sys.path.insert/append in code
  - If import removal claimed, verify import is gone
  - If module install claimed, verify requirements.txt updated

command: "python"
args:
  - "tools/executable/validators/module_not_found_validator.py"

input_format: "json"
output_format: "json"

tags:
  - "validator"
  - "fix_validator"
  - "module_error"
  - "import_error"

metadata:
  validates_error_type: "ModuleNotFoundError"
  confidence_threshold: 0.7  # Only fail validation if confidence > 0.7
  category: "fix_validator"
  priority: "high"
  auto_apply: true
```

---

## Integration with Fix System

### Current Flow (Hardcoded)

```
LLM generates fix
  ↓
Hardcoded validation checks
  ↓
If validation fails → retry
  ↓
Save code
```

### New Flow (Adaptive)

```
LLM generates fix
  ↓
Search RAG for validators matching error type
  ↓
Execute validators in parallel
  ↓
Aggregate validation results
  ↓
If ANY validator fails with confidence > threshold → retry
  ↓
Save code
```

---

## Code Changes

### 1. Validator Manager (`src/fix_validator_manager.py`)

```python
class FixValidatorManager:
    """Manages fix validators stored in RAG."""

    def __init__(self, rag_memory, tools_manager):
        self.rag = rag_memory
        self.tools = tools_manager
        self._index_validators()

    def _index_validators(self):
        """Index all validator tools from tools/executable/validators/"""
        for tool_id, tool in self.tools.tools.items():
            if tool.type == "executable" and "validator" in tool.tags:
                self.rag.store_artifact(
                    artifact_id=f"validator_{tool_id}",
                    artifact_type=ArtifactType.TOOL,
                    name=tool.name,
                    description=f"{tool.description}\n\nValidates: {error_type}",
                    content=json.dumps({
                        "tool_id": tool_id,
                        "error_type": tool.metadata.get("validates_error_type"),
                        "confidence_threshold": tool.metadata.get("confidence_threshold", 0.7)
                    }),
                    tags=["validator", "fix_validator"],
                    auto_embed=True
                )

    def find_validators(self, error_message: str, error_type: str):
        """Find validators that can validate this error type."""
        query = f"{error_type}: {error_message}"
        results = self.rag.find_similar(
            query=query,
            artifact_type=ArtifactType.TOOL,
            top_k=5
        )

        return [
            r for r in results
            if "validator" in r.tags
        ]

    def validate_fix(
        self,
        original_code: str,
        fixed_code: str,
        fix_description: str,
        error_message: str,
        error_type: str
    ) -> Dict[str, Any]:
        """
        Run all applicable validators on a fix.

        Returns:
            {
                "valid": bool,
                "failed_validators": List[str],
                "reasons": List[str],
                "confidence": float
            }
        """
        validators = self.find_validators(error_message, error_type)

        if not validators:
            # No validators found - allow by default
            return {"valid": True, "failed_validators": [], "confidence": 0.0}

        failed_validators = []
        reasons = []
        max_confidence = 0.0

        for validator_artifact in validators:
            validator_data = json.loads(validator_artifact.content)
            tool_id = validator_data["tool_id"]
            threshold = validator_data.get("confidence_threshold", 0.7)

            # Execute validator
            from node_runtime import call_tool

            validator_input = json.dumps({
                "original_code": original_code,
                "fixed_code": fixed_code,
                "fix_description": fix_description,
                "error_message": error_message
            })

            result = call_tool(tool_id, validator_input)

            if isinstance(result, str):
                result = json.loads(result)

            # Check if validator failed with high confidence
            if not result.get("valid") and result.get("confidence", 0) > threshold:
                failed_validators.append(validator_artifact.name)
                reasons.append(result.get("reason", "Unknown"))
                max_confidence = max(max_confidence, result.get("confidence", 0))

        return {
            "valid": len(failed_validators) == 0,
            "failed_validators": failed_validators,
            "reasons": reasons,
            "confidence": max_confidence
        }
```

### 2. Integration in `chat_cli.py`

Replace hardcoded validation with:

```python
# ==================== ADAPTIVE FIX VALIDATION ====================
fix_validation_failed = False

# Universal validation: code must be different
if 'fixes' in locals() and fixes and len(fixes) > 0:
    original_stripped = code.strip().replace(' ', '').replace('\n', '')
    fixed_stripped = fixed_code.strip().replace(' ', '').replace('\n', '')

    if original_stripped == fixed_stripped:
        console.print(f"[bold red]✗ Code unchanged despite claiming fixes![/bold red]")
        fix_validation_failed = True

# Adaptive validation: use validator tools
if not fix_validation_failed and self._fix_validator_manager:
    import re
    error_type_match = re.match(r'(\w+Error|Exception)', error_output)
    error_type = error_type_match.group(1) if error_type_match else "Unknown"

    validation_result = self._fix_validator_manager.validate_fix(
        original_code=code,
        fixed_code=fixed_code,
        fix_description=', '.join(fixes),
        error_message=error_output,
        error_type=error_type
    )

    if not validation_result["valid"]:
        console.print(f"[bold red]✗ Validation failed:[/bold red]")
        for i, (validator, reason) in enumerate(zip(
            validation_result["failed_validators"],
            validation_result["reasons"]
        )):
            console.print(f"  [{i+1}] {validator}: {reason}")

        fix_validation_failed = True

if fix_validation_failed:
    # Track and retry...
    continue
# ==================== END ADAPTIVE FIX VALIDATION ====================
```

---

## Codegen: Auto-Creating Validators

### When to Generate a Validator

Generate a new validator when:

1. **New error type** encountered (e.g., first time seeing TypeError)
2. **Repeated validation failures** for an error type
3. **Successful manual fix** that should be validated in future

### How to Generate

Use LLM to generate validator code:

```python
def generate_validator_for_error(error_type: str, error_message: str, successful_fix: str):
    """Generate a new validator tool for this error type."""

    prompt = f"""Create a Python validator tool that checks if fixes for {error_type} are actually applied.

ERROR TYPE: {error_type}
EXAMPLE ERROR: {error_message}
SUCCESSFUL FIX EXAMPLE: {successful_fix}

Create a validator that:
1. Takes original_code, fixed_code, fix_description, error_message as input
2. Returns {{valid: bool, reason: str, confidence: float}}
3. Checks if the claimed fix is actually in the code
4. Has high confidence (>0.8) when certain

Return ONLY the Python code for the validator function."""

    # Generate validator code
    validator_code = llm.generate(prompt)

    # Save as new validator tool
    save_validator_tool(error_type, validator_code)
```

---

## Benefits

### 1. **Adaptive**
- System learns new validators automatically
- No manual coding for each error type

### 2. **Extensible**
- Users can add custom validators
- Validators stored in RAG, available to all workflows

### 3. **Self-Improving**
- Generate validators from successful fixes
- Track validator accuracy and improve them

### 4. **Modular**
- Each validator is independent
- Easy to test, debug, and improve

---

## Implementation Plan

### Phase 1: Core Infrastructure ✓ (Today)
- [x] Universal validation (code must change)
- [x] Specific validations (ModuleNotFoundError, etc.)
- [x] Validation feedback loop

### Phase 2: Validator Manager (Next)
- [ ] Create `FixValidatorManager` class
- [ ] Index validator tools in RAG
- [ ] Execute validators dynamically
- [ ] Aggregate validation results

### Phase 3: Codegen Validators (Future)
- [ ] LLM generates validator code
- [ ] Auto-create validators from successful fixes
- [ ] Test and improve generated validators
- [ ] Track validator accuracy metrics

---

## Example: Complete Flow

```
1. Code fails with: ModuleNotFoundError: No module named 'node_runtime'

2. LLM generates fix:
   {
     "code": "<original code without sys.path>",
     "fixes_applied": ["Added path setup for node_runtime"],
     "analysis": "Missing path setup"
   }

3. Universal validation: FAIL (code identical)
   → Reject, add to all_attempts

4. LLM retries with warning:
   {
     "code": "<code WITH sys.path.insert()>",
     "fixes_applied": ["Added path setup for node_runtime"],
     "analysis": "Added sys.path setup before import"
   }

5. Universal validation: PASS (code changed)

6. Search RAG for validators:
   → Found: "ModuleNotFoundError Fix Validator"

7. Execute validator:
   → Result: {"valid": true, "confidence": 0.9, "reason": "sys.path setup found"}

8. All validations passed → Save code → Re-test → SUCCESS!
```

---

## Summary

This approach makes fix validation:
- **Adaptive:** Learns from experience
- **Scalable:** No manual coding for each error type
- **Accurate:** High-confidence validations
- **Extensible:** Users can add custom validators

**Next Steps:**
1. Implement `FixValidatorManager`
2. Create first validator tool (ModuleNotFoundError)
3. Test with real errors
4. Add codegen for auto-creating validators

---

**Generated:** 2025-11-17
**Version:** 1.0
**Status:** 🔬 Design Ready for Implementation
