# Mantras - Personality Traits for Operations

**Give each operation its own character**

---

## What Are Mantras?

Mantras are **personality traits** that define HOW an operation should approach a task. Different operations have different mantras - different "characters" in how they work.

Think of mantras as **meta-instructions** that influence everything about execution:
- Which models to use
- How creative to be
- How much time to take
- How strict validation should be
- How many retries to attempt

---

## Pre-Defined Mantras

### Speed-Focused

**"Lightning Fast"** - `very quickly, accurately`
- Speed priority: 90%
- Quality floor: 40%
- Temperature: 0.3
- Max time: 10 seconds
- Use case: Simple utilities, quick fixes

**"Quick & Accurate"** - `quickly, accurately`
- Speed priority: 70%
- Quality floor: 60%
- Temperature: 0.4
- Max time: 20 seconds
- Use case: Interactive mode, user waiting

### Quality-Focused

**"Carefully Diligent"** - `carefully, diligently`
- Speed priority: 30%
- Quality floor: 80%
- Temperature: 0.2
- Max time: 60 seconds
- Use case: Production code, critical systems

**"Thoroughly Precise"** - `thoroughly, precisely`
- Speed priority: 10%
- Quality floor: 90%
- Temperature: 0.1
- Max time: 120 seconds
- Use case: Security, finance, medical

### Creative

**"Experimentally Creative"** - `experimentally, creatively`
- Speed priority: 40%
- Quality floor: 50%
- Temperature: 0.9
- Max time: 90 seconds
- Use case: Prototypes, R&D, new approaches

**"Boldly Innovative"** - `boldly, creatively`
- Speed priority: 50%
- Quality floor: 40%
- Temperature: 1.0
- Max time: 60 seconds
- Use case: Exploration, novel solutions

### Safe/Conservative

**"Conservatively Safe"** - `conservatively, safely`
- Speed priority: 30%
- Quality floor: 90%
- Temperature: 0.1
- Max time: 90 seconds
- Use case: API integrations, databases, critical systems

**"Cautiously Precise"** - `cautiously, precisely`
- Speed priority: 20%
- Quality floor: 85%
- Temperature: 0.15
- Max time: 75 seconds
- Use case: Data integrity, validation, compliance

### Balanced

**"Pragmatically Effective"** - `pragmatically, accurately`
- Speed priority: 50%
- Quality floor: 70%
- Temperature: 0.4
- Max time: 40 seconds
- Use case: General purpose, balanced needs

**"Deliberately Thorough"** - `deliberately, thoroughly`
- Speed priority: 25%
- Quality floor: 85%
- Temperature: 0.2
- Max time: 100 seconds
- Use case: Important features, long-lived code

---

## How Mantras Work

### Example: Same Task, Different Mantras

**Task**: "Create an email validator"

#### With "Lightning Fast" Mantra
```python
# Model: codellama (fast, 7B)
# Temperature: 0.3 (conservative)
# Max time: 10 seconds

import re

def validate_email(email: str) -> bool:
    # Simple regex - FAST
    return bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', email))

# Generated in: 6 seconds
# Quality: 0.65
# Tests: Pass
```

#### With "Carefully Diligent" Mantra
```python
# Model: deepseek-coder:16b (powerful)
# Temperature: 0.2 (precise)
# Max time: 60 seconds

from email_validator import validate_email as lib_validate, EmailNotValidError
import re

def validate_email(email: str) -> bool:
    """
    Validate email address using RFC 5322 standards.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False

    # Basic format check
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False

    # Use proper RFC validation library
    try:
        lib_validate(email)
        return True
    except EmailNotValidError:
        return False
    except Exception:
        # Fallback to regex if library fails
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

# Generated in: 42 seconds
# Quality: 0.92
# Tests: Pass + comprehensive edge cases
```

#### With "Experimentally Creative" Mantra
```python
# Model: qwen2.5-coder:14b (creative)
# Temperature: 0.9 (experimental)
# Max time: 90 seconds

import re
from typing import Tuple
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Structured validation result with details."""
    is_valid: bool
    reason: str = ""
    suggestions: list = None

class EmailValidator:
    """Advanced email validator with learning capabilities."""

    def __init__(self):
        self.common_typos = {
            'gamil.com': 'gmail.com',
            'yahooo.com': 'yahoo.com',
            'hotmial.com': 'hotmail.com'
        }

    def validate(self, email: str) -> ValidationResult:
        """Validate with auto-correction suggestions."""

        if not email or '@' not in email:
            return ValidationResult(False, "Missing @ symbol")

        local, domain = email.rsplit('@', 1)

        # Check for common typos
        if domain in self.common_typos:
            return ValidationResult(
                False,
                f"Possible typo detected",
                suggestions=[f"{local}@{self.common_typos[domain]}"]
            )

        # RFC 5322 validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(pattern, email))

        return ValidationResult(is_valid, "" if is_valid else "Invalid format")

def validate_email(email: str) -> bool:
    """Simple wrapper for backward compatibility."""
    return EmailValidator().validate(email).is_valid

# Generated in: 68 seconds
# Quality: 0.78
# Tests: Pass + novel typo detection feature!
```

---

## Specifying Mantras in Tools

### Tool Definition with Mantra

```yaml
# tools/llm/security_auditor.yaml
name: "Security Auditor"
type: "llm"
description: "Audits code for security vulnerabilities"

# SPECIFY MANTRA
mantra: "conservatively_safe"

llm:
  role: "powerful"

tags:
  - "security"
  - "audit"
```

### Workflow with Mantra

```yaml
# tools/workflow/api_integration.yaml
name: "API Integration Builder"
type: "workflow"

# This workflow requires careful, safe approach
mantra: "conservatively_safe"

steps:
  - tool: "api_client_generator"
    # This step inherits mantra from parent workflow

  - tool: "error_handler_generator"
    # Override with different mantra for this step
    mantra: "thoroughly_precise"
```

---

## Detecting Mantras from User Input

The system automatically detects mantras from natural language:

```python
# User input → Detected mantra

"Quickly write a CSV parser"
→ "lightning_fast"

"Carefully create a database migration"
→ "carefully_diligent"

"Safely implement authentication"
→ "conservatively_safe"

"Experimentally try a new approach to caching"
→ "experimentally_creative"
```

---

## Mantra in Action

### Phase 1 (Interactive) - User Waiting

```
User: "Quickly write an email validator"
  ↓
Sentinel detects: "quickly" → "lightning_fast" mantra
  ↓
Execution configured:
  - Model: codellama (fast)
  - Temperature: 0.3
  - Max time: 10s
  - Retries: 1
  ↓
Result in 6 seconds, quality: 0.65
User gets answer NOW
```

### Phase 2 (Optimize) - Background

```
Background optimizer runs at 6 PM
  ↓
Re-run with: "carefully_diligent" mantra
  ↓
Execution configured:
  - Model: deepseek-coder:16b (powerful)
  - Temperature: 0.2
  - Max time: 60s
  - Retries: 5
  - Parallel experiments: 5 variants
  ↓
Result in 42 seconds, quality: 0.92
Updated for next user
```

**Next user gets 0.92 quality from Phase 1!**

---

## Task Type → Mantra Mapping

System recommends mantras based on task type:

```python
# Interactive mode (user waiting)
simple_function    → "lightning_fast"
validation         → "quick_and_accurate"
data_processing    → "pragmatically_effective"

# Optimize mode (background)
api_integration    → "conservatively_safe"
database           → "conservatively_safe"
security           → "thoroughly_precise"
algorithm          → "deliberately_thorough"
prototype          → "experimentally_creative"
```

---

## System Prompt with Mantra

Mantras influence the system prompt sent to the LLM:

### "Lightning Fast" System Prompt
```
You are a code generation assistant with this approach:

GET RESULT ASAP, MAINTAIN BASIC ACCURACY

Your operating principles:
1. Work VERY QUICKLY. Prioritize speed above all.
2. Focus on correctness and accuracy.

Quality floor: 40%
Time budget: 10 seconds
```

### "Carefully Diligent" System Prompt
```
You are a code generation assistant with this approach:

THOROUGH, METHODICAL, HIGH QUALITY

Your operating principles:
1. Work carefully and pay attention to details.
2. Be thorough and diligent in your approach.

Quality floor: 80%
Time budget: 60 seconds
```

### "Experimentally Creative" System Prompt
```
You are a code generation assistant with this approach:

TRY NOVEL APPROACHES, EXPLORE SOLUTIONS

Your operating principles:
1. Try experimental approaches.
2. Think creatively and explore novel solutions.

Quality floor: 50%
Time budget: 90 seconds
```

---

## Creating Custom Mantras

```python
from src.mantras import Mantra, MantraTrait

# Define custom mantra
custom_mantra = Mantra(
    name="Database Specialist",
    traits=[
        MantraTrait.CAUTIOUSLY,
        MantraTrait.PRECISELY,
        MantraTrait.THOROUGHLY
    ],
    description="Database operations require extreme care",
    speed_priority=0.15,  # Very slow, very careful
    quality_floor=0.95,   # Extremely high quality
    temperature=0.05,     # Almost deterministic
    max_time=180.0,       # 3 minutes allowed
    validation_strictness=0.95,
    retry_attempts=10
)

# Use in workflow
config = MantraApplicator.apply_to_workflow(
    mantra=custom_mantra,
    workflow_config=base_config
)
```

---

## Mantra Traits Reference

### Speed Traits
- **VERY_QUICKLY**: Maximum speed, minimal overhead
- **QUICKLY**: Fast but not reckless
- **DELIBERATELY**: Take time, no rushing
- **METHODICALLY**: Step-by-step, systematic

### Quality Traits
- **ACCURATELY**: Focus on correctness
- **PRECISELY**: Exact, no approximations
- **CAREFULLY**: Pay attention to details
- **DILIGENTLY**: Thorough, conscientious
- **THOROUGHLY**: Comprehensive, complete

### Approach Traits
- **CONSERVATIVELY**: Proven, safe approaches
- **CREATIVELY**: Novel, innovative solutions
- **EXPERIMENTALLY**: Try new things
- **PRAGMATICALLY**: What works, not perfect

### Risk Traits
- **SAFELY**: Minimize risk, maximize safety
- **BOLDLY**: Take risks, push boundaries
- **CAUTIOUSLY**: Proceed with care

---

## Benefits of Mantras

### 1. Different Operations Have Different Characters

```python
# Security audit: VERY careful
security_tool.mantra = "conservatively_safe"

# Quick prototype: VERY fast
prototype_tool.mantra = "lightning_fast"

# Critical database migration: EXTREMELY precise
migration_tool.mantra = "thoroughly_precise"
```

### 2. Natural Language Control

```bash
# User can specify approach naturally
"Quickly write a helper function"      # Fast
"Carefully create an API client"       # Quality
"Safely implement authentication"      # Conservative
"Experimentally try a new algorithm"   # Creative
```

### 3. Consistent Behavior

Same mantra → same approach across all tools:
- Model selection
- Temperature
- Time budgets
- Validation
- Retry logic

### 4. Automatic Optimization

Phase 1: Use "quick" mantra for user
Phase 2: Use "careful" mantra for optimization

System automatically adjusts personality based on phase.

---

## Examples by Domain

### Web API Integration
```yaml
mantra: "conservatively_safe"
# → Proven patterns, extensive error handling, safe
```

### Data Science Prototype
```yaml
mantra: "experimentally_creative"
# → Try novel approaches, explore, iterate
```

### Financial Calculation
```yaml
mantra: "thoroughly_precise"
# → Maximum precision, no approximations, exhaustive testing
```

### Simple Utility Function
```yaml
mantra: "lightning_fast"
# → Get it done NOW, basic quality is fine
```

### Security Feature
```yaml
mantra: "cautiously_precise"
# → Careful validation, high standards, no shortcuts
```

---

## Summary

Mantras give **personality and character** to operations:

- **"quickly, accurately"** → Fast and correct
- **"carefully, diligently"** → Thorough and methodical
- **"experimentally, creatively"** → Novel and innovative
- **"conservatively, safely"** → Proven and safe

Each mantra translates to concrete execution parameters:
- Model selection
- Temperature
- Time budget
- Validation strictness
- Retry attempts

**Different operations can have different characters**, making the system more expressive and adaptive.

---

**Generated:** 2025-11-17
**Status:** ✓ System Complete
