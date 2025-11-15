# Model Tiers System

## Overview

The tiered model system provides a clean, hierarchical approach to model selection with automatic escalation and context management.

## Concept

Instead of hardcoding models everywhere, define **tiers** for different purposes:
- **Coding tiers**: Simple → General → Complex → God-level
- **Content tiers**: Quick → Quality → Long-form
- **Validation tiers**: Fast → Thorough
- **Quality tiers**: Basic → Comprehensive

Each tier automatically gets:
- Appropriate model
- Correct context window size
- Proper timeout
- Escalation path to next tier

## Configuration

```yaml
# Define model tiers by purpose
model_tiers:

  # CODING TIERS - For code generation and debugging
  coding:
    tier_1:  # Fast, simple tasks
      name: "Simple Coding"
      model: "phi3:mini"
      context_window: 4096
      timeout: 60
      use_for: ["simple", "basic", "quick", "triage"]
      escalates_to: "tier_2"

    tier_2:  # General coding (DEFAULT)
      name: "General Coding"
      model: "codellama"
      context_window: 16384
      timeout: 120
      use_for: ["general", "moderate", "standard", "default"]
      escalates_to: "tier_3"

    tier_3:  # Complex coding
      name: "Advanced Coding"
      model: "qwen2.5-coder:14b"
      context_window: 32768
      timeout: 600  # 10 minutes - large model
      use_for: ["complex", "advanced", "escalation", "hard"]
      escalates_to: "tier_4"

    tier_4:  # God-level (last resort)
      name: "God-Level Coding"
      model: "deepseek-coder:33b"
      context_window: 65536
      timeout: 900  # 15 minutes - very large
      use_for: ["god-level", "last-resort", "impossible"]
      escalates_to: null  # No further escalation

  # CONTENT TIERS - For creative writing, articles, stories
  content:
    tier_1:  # Quick content
      name: "Quick Content"
      model: "phi3:mini"
      context_window: 4096
      timeout: 60
      use_for: ["quick", "simple", "short"]
      escalates_to: "tier_2"

    tier_2:  # Quality content (DEFAULT)
      name: "Quality Content"
      model: "llama3"
      context_window: 8192
      timeout: 120
      use_for: ["general", "default", "standard"]
      escalates_to: "tier_3"

    tier_3:  # Long-form content
      name: "Long-Form Content"
      model: "mistral-nemo"
      context_window: 128000  # Massive context for novels
      timeout: 240
      use_for: ["long-form", "novel", "book", "article"]
      escalates_to: null

  # VALIDATION TIERS - For quick checks and validation
  validation:
    tier_1:  # Fast validation
      name: "Fast Validation"
      model: "tinyllama"
      context_window: 2048
      timeout: 30
      use_for: ["quick", "simple", "fast"]
      escalates_to: "tier_2"

    tier_2:  # Thorough validation
      name: "Thorough Validation"
      model: "phi3:mini"
      context_window: 4096
      timeout: 60
      use_for: ["thorough", "detailed"]
      escalates_to: null

  # QUALITY TIERS - For evaluation and assessment
  quality:
    tier_1:  # Basic quality check
      name: "Basic Quality"
      model: "gemma2:2b"
      context_window: 8192
      timeout: 45
      use_for: ["basic", "quick", "simple"]
      escalates_to: "tier_2"

    tier_2:  # Comprehensive quality
      name: "Comprehensive Quality"
      model: "llama3"
      context_window: 8192
      timeout: 120
      use_for: ["comprehensive", "detailed", "thorough"]
      escalates_to: null

  # PLANNING TIERS - For strategy and planning
  planning:
    tier_1:  # Quick planning
      name: "Quick Planning"
      model: "phi3:mini"
      context_window: 4096
      timeout: 60
      use_for: ["quick", "simple"]
      escalates_to: "tier_2"

    tier_2:  # Strategic planning (DEFAULT)
      name: "Strategic Planning"
      model: "llama3"
      context_window: 8192
      timeout: 120
      use_for: ["general", "default", "strategic"]
      escalates_to: null

# Map old role system to new tiers
role_to_tier_mapping:
  fast: "coding.tier_1"
  base: "coding.tier_2"
  powerful: "coding.tier_3"
  god_level: "coding.tier_4"
```

## Usage in Tools

Tools reference tiers instead of specific models:

```yaml
tools:
  general:
    name: "General Code Generator"
    model_tier: "coding.tier_2"  # Uses codellama with 16K context

  content_generator:
    name: "Content Generator"
    model_tier: "content.tier_2"  # Uses llama3 with 8K context

  quick_feedback:
    name: "Quick Feedback"
    model_tier: "validation.tier_1"  # Uses tinyllama with 2K context
```

## Escalation Flow

When a tier fails or needs more power:

```
coding.tier_1 (phi3:mini, 4K context)
    ↓ [escalate]
coding.tier_2 (codellama, 16K context) ← DEFAULT
    ↓ [escalate]
coding.tier_3 (qwen2.5-coder:14b, 32K context) ← Gets FULL context from tier_2
    ↓ [escalate]
coding.tier_4 (deepseek-coder:33b, 64K context) ← Gets FULL context from tier_3
```

**Key feature**: When escalating, the more powerful model receives ALL context from previous attempts, not just the original prompt.

## Context Escalation Example

```python
# Tier 1 attempt (phi3:mini with 4K context)
attempt_1 = {
    "prompt": "Fix this bug: ...",
    "context_used": 3500  # tokens
}
# FAILS

# Tier 2 escalation (codellama with 16K context)
attempt_2 = {
    "prompt": "Fix this bug: ...",
    "previous_attempt": attempt_1["prompt"],
    "previous_error": "Syntax error on line 5",
    "context_used": 8000  # More context available
}
# FAILS

# Tier 3 escalation (qwen2.5-coder:14b with 32K context)
attempt_3 = {
    "prompt": "Fix this bug: ...",
    "tier_1_attempt": attempt_1,
    "tier_2_attempt": attempt_2,
    "all_errors": ["...", "..."],
    "full_code": "... entire file ...",  # Can fit more context
    "context_used": 28000  # Much more context
}
# SUCCESS
```

## Benefits

✅ **Simple Configuration**: Define tiers once, use everywhere
✅ **Automatic Context Scaling**: Higher tiers get bigger context windows
✅ **Automatic Timeout Scaling**: Larger models get longer timeouts
✅ **Clear Escalation Path**: tier_1 → tier_2 → tier_3 → tier_4
✅ **Purpose-Based**: Different tiers for coding, content, validation, quality
✅ **Easy Model Swapping**: Change model in one place, affects all tools using that tier
✅ **Full Context on Escalation**: More powerful models get complete history

## Backend-Specific Tiers

Different backends can have different tier implementations:

```yaml
# config.local.minimal.yaml (Ollama)
model_tiers:
  coding:
    tier_2:
      model: "codellama"  # Local model

# config.anthropic.minimal.yaml (Claude)
model_tiers:
  coding:
    tier_2:
      model: "claude-3-5-sonnet-20241022"  # Cloud model
```

Same tier references, different models per backend!

## Migration from Old System

Old system (hardcoded models):
```yaml
tools:
  general:
    llm:
      model: "codellama"  # Hardcoded
```

New system (tier-based):
```yaml
tools:
  general:
    model_tier: "coding.tier_2"  # References tier
```

Benefits:
- Swap all "coding.tier_2" models at once
- Automatic context/timeout management
- Clear escalation paths
