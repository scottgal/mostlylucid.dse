# Unified LLM Configuration System

## Overview

The Code Evolver now uses a **unified, role-based, level-based LLM configuration system** that makes it incredibly easy to:

1. **Define models once** - Each model is defined once with all its metadata (context size, cost, speed, quality)
2. **Set defaults** - Configure defaults that cascade to all roles
3. **Override per role** - Only override what's different for specific roles
4. **Switch backends easily** - Change from Ollama to Anthropic with minimal config changes
5. **Protect critical settings** - Embedding models require explicit force override

---

## Quick Start

### Using Local Ollama Models

```bash
python chat_cli.py --config config.yaml
```

### Using Anthropic Claude Models

```bash
export ANTHROPIC_API_KEY='sk-ant-api03-...'
python chat_cli.py --config config.anthropic.yaml
```

---

## Configuration Structure

### 1. Model Registry

Define each model **once** with all its metadata:

```yaml
llm:
  models:
    llama3:
      name: "llama3"
      backend: "ollama"
      context_window: 8192
      cost: "medium"
      speed: "fast"
      quality: "excellent"
      timeout: 120

    codellama_7b:
      name: "codellama:7b"
      backend: "ollama"
      context_window: 16384
      cost: "medium"
      speed: "fast"
      quality: "excellent"
      timeout: 120
      specialization: "code"

    claude_sonnet:
      name: "claude-3-5-sonnet-20241022"
      backend: "anthropic"
      context_window: 200000
      cost: "medium"
      speed: "fast"
      quality: "exceptional"
      timeout: 120
```

**Key** (e.g., `llama3`, `codellama_7b`, `claude_sonnet`) is what you reference in defaults and roles.

**Name** (e.g., `"llama3"`, `"codellama:7b"`) is the actual model name passed to the backend.

---

### 2. Defaults (Cascading)

Set defaults that automatically apply to **ALL roles**:

```yaml
llm:
  defaults:
    god: deepseek_16b          # Most powerful model
    escalation: qwen_14b       # Strong model for complex issues
    general: llama3            # General purpose model
    fast: gemma3_4b            # Fast for simple tasks
    veryfast: tinyllama        # Extremely fast for triage
```

**Every role** (default, code, content, analysis) will inherit these unless explicitly overridden.

---

### 3. Role-Specific Overrides

Only override what's **different** from defaults:

```yaml
llm:
  roles:
    # Default role - inherits everything from defaults
    default:
      # No overrides needed

    # Code role - override with code-specialized models
    code:
      general: codellama_7b    # Override general for code
      fast: qwen_3b            # Override fast for code
      # god, escalation, veryfast inherit from defaults

    # Content role - override god for long-form writing
    content:
      god: mistral_nemo        # Override: use 128K context
      # All others inherit from defaults
```

---

### 4. Resolution Order

When you request a model via `config.get_model(role, level)`:

```
1. Check llm.roles.{role}.{level} → Use if found
2. Else check llm.defaults.{level} → Use if found
3. Else error (not configured)
```

**Examples:**

- `get_model("code", "general")` → `codellama_7b` (from code role override)
- `get_model("code", "god")` → `deepseek_16b` (inherited from defaults)
- `get_model("default", "general")` → `llama3` (from defaults)
- `get_model("content", "god")` → `mistral_nemo` (from content role override)

---

## Backend Switching

### Ollama → Anthropic (Local to Cloud)

**Before (Ollama config.yaml):**

```yaml
llm:
  models:
    # ... Ollama models defined ...

  defaults:
    god: deepseek_16b
    escalation: qwen_14b
    general: llama3
    fast: gemma3_4b
    veryfast: tinyllama
```

**After (config.anthropic.yaml):**

```yaml
llm:
  models:
    # Define Anthropic models
    claude_haiku: ...
    claude_sonnet: ...
    claude_opus: ...

    # Keep embedding and veryfast on Ollama
    tinyllama: ...
    nomic_embed: ...

  # Just override defaults - ALL roles automatically use Anthropic!
  defaults:
    god: claude_opus
    escalation: claude_sonnet
    general: claude_sonnet
    fast: claude_haiku
    veryfast: tinyllama  # Keep local

  backends:
    anthropic:
      enabled: true
      api_key: "${ANTHROPIC_API_KEY}"
```

**That's it!** All roles automatically use Anthropic except `veryfast` which stays on tinyllama.

---

## Usage in Code

### Old Way (Legacy)

```python
# Old properties still work for backward compatibility
config.overseer_model  # → "llama3"
config.generator_model  # → "codellama"
config.escalation_model  # → "qwen2.5-coder:14b"
```

### New Way (Unified)

```python
from src.config_manager import ConfigManager

config = ConfigManager("config.yaml")

# Get model key for role + level
model_key = config.get_model("code", "general")
# → "codellama_7b"

# Get full metadata for a model
metadata = config.get_model_metadata("codellama_7b")
# → {
#   "name": "codellama:7b",
#   "backend": "ollama",
#   "context_window": 16384,
#   "cost": "medium",
#   "speed": "fast",
#   "quality": "excellent",
#   "specialization": "code",
#   "timeout": 120
# }

# Resolve role + level to full metadata (one call)
metadata = config.resolve_model("code", "general")
# → {
#   "model_key": "codellama_7b",
#   "name": "codellama:7b",
#   "backend": "ollama",
#   ...
# }

# Get context window for a model name
context = config.get_context_window("codellama:7b")
# → 16384
```

---

## Roles and Levels

### Roles

- **default** - General purpose tasks
- **code** - Code generation, refactoring, debugging
- **content** - Writing, articles, creative content
- **analysis** - Planning, evaluation, quality assessment

### Levels (Hierarchy)

1. **god** - Most powerful model, last resort, complex reasoning
2. **escalation** - Strong model for fixing issues after failures
3. **general** - Default model for most tasks
4. **fast** - Faster model for simple tasks
5. **veryfast** - Extremely fast model for triage/validation

### Example Workflow

```python
# Start with fast model for triage
triage_model = config.resolve_model("code", "fast")  # qwen_3b

# Use general model for implementation
impl_model = config.resolve_model("code", "general")  # codellama_7b

# Tests fail → escalate
escalation_model = config.resolve_model("code", "escalation")  # qwen_14b

# Still failing → god mode
god_model = config.resolve_model("code", "god")  # deepseek_16b
```

---

## Protected Settings

### Embedding Models

Embedding models are **protected** and require explicit `override: force`:

```yaml
llm:
  embedding:
    default: nomic_embed
    allow_override: "force"  # Must explicitly force
```

**Why?** Embedding models must stay consistent for RAG memory. Changing them invalidates all stored embeddings.

To override (not recommended):

```yaml
llm:
  embedding:
    default: some_other_model
    override: force  # Explicit force required
```

---

## Config Files

| File | Purpose |
|------|---------|
| `config.yaml` | Main local Ollama configuration |
| `config.local.yaml` | Same as config.yaml (emphasizes local-only) |
| `config.anthropic.yaml` | Anthropic Claude override |
| `config.unified.yaml` | Template showing unified structure |
| `config.anthropic.unified.yaml` | Template for Anthropic override |

**Old configs** (deprecated but still work):
- `config.tiered.yaml` - Old tiered system (replaced by unified)
- `model_tiers.yaml` - Old tiers (replaced by unified)

---

## Examples

### Example 1: Add a new local model

```yaml
llm:
  models:
    # Add new model
    my_custom_model:
      name: "my-custom-model:7b"
      backend: "ollama"
      context_window: 16384
      cost: "low"
      speed: "fast"
      quality: "good"
      timeout: 90

  # Use it in defaults or roles
  defaults:
    fast: my_custom_model  # Use for all "fast" tasks
```

### Example 2: Use different models for code vs content

```yaml
llm:
  defaults:
    general: llama3  # Default for all roles

  roles:
    code:
      general: codellama_7b  # Override for code

    content:
      general: mistral_nemo  # Override for content
```

### Example 3: Hybrid (mostly Anthropic, some local)

```yaml
llm:
  models:
    claude_sonnet: ...
    claude_haiku: ...
    tinyllama: ...  # Keep local for triage
    nomic_embed: ...  # Keep local for embeddings

  defaults:
    god: claude_sonnet
    escalation: claude_sonnet
    general: claude_sonnet
    fast: claude_haiku
    veryfast: tinyllama  # Fast local triage

  embedding:
    default: nomic_embed  # Local embeddings
```

---

## Migration from Old Config

### Step 1: Identify Current Models

List all models currently in use:

```yaml
# OLD
ollama:
  models:
    overseer: "llama3"
    generator: "codellama"
    escalation: "qwen2.5-coder:14b"
    triage: "tinyllama"
```

### Step 2: Create Model Registry

Define each model once:

```yaml
# NEW
llm:
  models:
    llama3:
      name: "llama3"
      backend: "ollama"
      context_window: 8192
      ...

    codellama:
      name: "codellama"
      backend: "ollama"
      context_window: 16384
      ...
```

### Step 3: Set Defaults

Map old roles to new levels:

```yaml
llm:
  defaults:
    general: llama3        # was: overseer
    fast: llama3           # was: triage
    veryfast: tinyllama    # was: triage

  roles:
    code:
      general: codellama   # was: generator
```

### Step 4: Test

```bash
python -m pytest tests/test_config_unified.py -v
```

---

## Troubleshooting

### Issue: "No model configured for role='X' level='Y'"

**Cause:** Neither `llm.roles.{role}.{level}` nor `llm.defaults.{level}` is set.

**Fix:** Add to defaults or role-specific:

```yaml
llm:
  defaults:
    {level}: {model_key}
```

### Issue: "Model 'X' not found in llm.models registry"

**Cause:** Model key referenced but not defined in registry.

**Fix:** Add model to registry:

```yaml
llm:
  models:
    {model_key}:
      name: "..."
      backend: "..."
      ...
```

### Issue: Context window not recognized

**Cause:** Model name doesn't match registry.

**Fix:** Ensure `get_context_window()` receives the model **name** (e.g., `"codellama:7b"`), not the key (e.g., `"codellama_7b"`).

Or add to registry with matching name.

---

## Best Practices

### 1. Define Models Once

✅ **Good:**

```yaml
llm:
  models:
    llama3:
      name: "llama3"
      context_window: 8192
      ...

  defaults:
    general: llama3  # Reference the key
```

❌ **Bad:**

```yaml
llm:
  defaults:
    general: "llama3"  # Hardcoded name, no metadata
```

### 2. Use Cascading Defaults

✅ **Good:**

```yaml
llm:
  defaults:
    general: llama3  # Set once, applies to all roles
```

❌ **Bad:**

```yaml
llm:
  roles:
    default:
      general: llama3
    code:
      general: llama3  # Repeated
    content:
      general: llama3  # Repeated
```

### 3. Only Override When Necessary

✅ **Good:**

```yaml
llm:
  defaults:
    general: llama3

  roles:
    code:
      general: codellama_7b  # Only override what's different
      # All others inherit from defaults
```

❌ **Bad:**

```yaml
llm:
  roles:
    code:
      god: deepseek_16b      # Unnecessary (same as default)
      escalation: qwen_14b   # Unnecessary
      general: codellama_7b  # Only this needs override
      fast: gemma3_4b        # Unnecessary
      veryfast: tinyllama    # Unnecessary
```

### 4. Keep Backend-Specific Models Separate

✅ **Good:**

- `config.yaml` - Only Ollama models
- `config.anthropic.yaml` - Only Anthropic models (+ necessary Ollama like embeddings)

❌ **Bad:**

- `config.yaml` - Mix of Ollama and Anthropic models

---

## Summary

The unified LLM config system provides:

1. ✅ **Single source of truth** - Models defined once with all metadata
2. ✅ **Cascading defaults** - Set defaults that apply to all roles
3. ✅ **Minimal overrides** - Only specify what's different
4. ✅ **Easy backend switching** - Change from Ollama to Anthropic with minimal changes
5. ✅ **Protected settings** - Critical settings (embeddings) require explicit override
6. ✅ **Backward compatible** - Old configs still work
7. ✅ **Type-safe** - Model metadata includes all necessary info
8. ✅ **Testable** - Comprehensive unit tests ensure correctness

---

## See Also

- `tests/test_config_unified.py` - Unit tests
- `src/config_manager.py` - Implementation
- `config.unified.yaml` - Template for Ollama
- `config.anthropic.unified.yaml` - Template for Anthropic