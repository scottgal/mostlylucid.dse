# Minimal Config Guide - Unified LLM System

## Philosophy

**Configs should only contain what they NEED**. Everything else inherits from defaults.

## The Hierarchy

```
DEFAULT_CONFIG (hardcoded)
    ↓
config.yaml (base, complete)
    ↓
config.anthropic.yaml (override, minimal)
```

---

## Minimal Anthropic Config

Here's what you ACTUALLY need for Anthropic:

```yaml
llm:
  # Define ONLY Anthropic models + required Ollama models
  models:
    claude_haiku: { name: "claude-3-haiku-20240307", backend: "anthropic", context_window: 200000, cost: "low", speed: "very-fast", quality: "excellent", timeout: 120 }
    claude_sonnet: { name: "claude-3-5-sonnet-20241022", backend: "anthropic", context_window: 200000, cost: "medium", speed: "fast", quality: "exceptional", timeout: 120 }
    claude_opus: { name: "claude-3-opus-20240229", backend: "anthropic", context_window: 200000, cost: "very-high", speed: "medium", quality: "exceptional", timeout: 120 }

    # Required: Ollama models for embedding and veryfast
    nomic_embed: { name: "nomic-embed-text", backend: "ollama", context_window: 8192, vector_size: 768, cost: "low", speed: "fast", quality: "excellent", specialization: "embedding" }
    tinyllama: { name: "tinyllama", backend: "ollama", context_window: 2048, cost: "very-low", speed: "very-fast", quality: "basic", timeout: 30 }

  # Override ONLY what changes
  defaults:
    god: claude_opus
    escalation: claude_sonnet
    general: claude_sonnet
    fast: claude_haiku
    veryfast: tinyllama  # Keep local for free triage

  embedding:
    default: nomic_embed
    allow_override: "force"

  backends:
    ollama:
      base_url: "http://localhost:11434"
      enabled: true  # Required for embeddings
    anthropic:
      enabled: true
      api_key: "${ANTHROPIC_API_KEY}"

# Essential runtime settings
rag_memory:
  use_qdrant: true
  qdrant_url: "http://192.168.0.76:6333"
  collection_name: "code_evolver_artifacts"

testing:
  enabled: true
  auto_escalate: true
```

**That's it!** Everything else inherits from DEFAULT_CONFIG.

---

## What Gets Inherited

These settings come from DEFAULT_CONFIG automatically:

- `execution.*` - Sandbox settings, timeouts, memory limits
- `auto_evolution.*` - Auto-evolution thresholds
- `quality_evaluation.*` - Quality thresholds
- `registry.*` - Registry paths
- `nodes.*` - Node storage paths
- `logging.*` - Logging configuration
- `chat.*` - Chat interface settings
- `optimization.*` - Optimization settings
- `build.*` - Build settings

**You don't need to specify these unless you want to override them!**

---

## Examples

### Example 1: Just Change the God Model

```yaml
llm:
  models:
    gpt4: { name: "gpt-4", backend: "openai", ... }

  defaults:
    god: gpt4  # Only override god
    # All other levels inherit from base config!
```

### Example 2: Use Different Model for Code

```yaml
llm:
  defaults:
    general: claude_sonnet  # Override general for ALL roles

  roles:
    code:
      general: claude_opus  # But use opus for code specifically
```

### Example 3: Add Custom RAG Settings

```yaml
rag_memory:
  qdrant_url: "http://my-server:6333"
  collection_name: "my_custom_collection"
  # Everything else (path, max_embedding_content_length, etc.) inherits from defaults
```

---

## File Comparison

| File | Purpose | Size | When to Use |
|------|---------|------|-------------|
| `config.yaml` | Base Ollama config | Full | Local development (free) |
| `config.local.yaml` | Same as config.yaml | Full | Emphasis on local-only |
| `config.anthropic.yaml` | Anthropic override | Full | Production with Claude (complete) |
| `config.anthropic.simple.yaml` | Anthropic minimal | Minimal | Shows minimal override pattern |
| `config.unified.yaml` | Template | Full | Reference for structure |

---

## Best Practices

### ✅ DO:
- Only define what changes from base
- Keep configs focused and minimal
- Use comments to explain overrides
- Group related models together

### ❌ DON'T:
- Copy entire config files
- Repeat default values
- Include settings you don't change
- Mix multiple backends in one config (except Ollama for embeddings)

---

## Migration Checklist

Migrating from old config to new minimal config:

- [ ] Identify what's DIFFERENT from base config
- [ ] Create new config with ONLY those differences
- [ ] Add required Ollama models (embedding, veryfast)
- [ ] Add essential runtime settings (rag_memory if custom)
- [ ] Test: `python -c "from src.config_manager import ConfigManager; c = ConfigManager('my_config.yaml'); print(c.get_primary_llm_backend())"`
- [ ] Verify: Should print your intended backend
- [ ] Run: `python chat_cli.py --config my_config.yaml`

---

## Troubleshooting

### Config Too Big?
**Problem:** Your override config is hundreds of lines

**Solution:** Remove everything that's the same as base config. Keep ONLY differences.

### Can't Find Model?
**Problem:** `No model configured for role='X' level='Y'`

**Solution:** Add to defaults or role-specific overrides:
```yaml
llm:
  defaults:
    {level}: {model_key}
```

### Wrong Backend?
**Problem:** Shows "Using ollama backend" when you want Anthropic

**Solution:** Check that your defaults reference Anthropic models:
```yaml
llm:
  defaults:
    general: claude_sonnet  # Must be an Anthropic model
```

---

## Summary

**The new system = YAML inheritance + smart defaults**

1. Define models once in registry
2. Set defaults (applies to all roles)
3. Override specific roles (only if needed)
4. Backend configs override defaults (minimal)

**Result:** Clean, maintainable configs that only show what's different!
