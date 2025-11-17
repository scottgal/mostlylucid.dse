# Backend Configuration Guide

Complete guide to configuring LLM backends in mostlylucid DiSE.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Supported Backends](#supported-backends)
4. [Configuration Format](#configuration-format)
5. [Backend-Specific Setup](#backend-specific-setup)
6. [Tools Configuration](#tools-configuration)
7. [Model Selector Tool](#model-selector-tool)
8. [Advanced Patterns](#advanced-patterns)
9. [Troubleshooting](#troubleshooting)

---

## Overview

mostlylucid DiSE supports **5 LLM backends**:

- **Ollama** - Local/self-hosted models (free)
- **OpenAI** - GPT-4, GPT-3.5, etc. (paid)
- **Anthropic** - Claude 3.5, Opus, Haiku (paid)
- **Azure OpenAI** - Azure-hosted OpenAI models (paid)
- **LM Studio** - Local models with OpenAI-compatible API (free)

You can:
- Use a single backend for all operations
- Mix multiple backends (e.g., Anthropic for reasoning, Ollama for cheap tasks)
- Set up automatic fallbacks
- Switch backends per tool or per workflow step

---

## Quick Start

### Simplest Setup (Ollama)

```yaml
llm:
  backend: "ollama"
  ollama:
    base_url: "http://localhost:11434"
```

### All Anthropic Setup

```yaml
llm:
  backend: "anthropic"
  global_defaults:
    default_backend: "anthropic"
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
```

See `config.anthropic-simple.yaml` for a complete minimal example.

### Multi-Backend Setup

```yaml
llm:
  backend: "anthropic"
  fallback_backends: ["openai", "ollama"]
  # If Anthropic fails, tries OpenAI, then Ollama
```

---

## Supported Backends

### Backend Comparison

| Backend | Cost | Speed | Context | Setup Difficulty | Best For |
|---------|------|-------|---------|------------------|----------|
| **Ollama** | Free | Medium-Fast | 8k-128k | Easy | Local development, privacy |
| **OpenAI** | Paid | Fast | 8k-128k | Easy | Production, quality |
| **Anthropic** | Paid | Fast | 200k | Easy | Long context, reasoning |
| **Azure** | Paid | Fast | 8k-128k | Medium | Enterprise, compliance |
| **LM Studio** | Free | Varies | Varies | Easy | Local experimentation |

### Model Recommendations by Backend

**Ollama (Local):**
- Code: `qwen2.5-coder:14b`, `codellama`
- General: `llama3`, `mistral-nemo`
- Fast: `tinyllama`, `gemma2:2b`
- Long context: `mistral-nemo` (128k)

**OpenAI:**
- Best: `gpt-4`, `gpt-4-turbo`, `gpt-4o`
- Fast/Cheap: `gpt-3.5-turbo`
- Code: `gpt-4` (all models can code)

**Anthropic:**
- Best: `claude-3-5-sonnet-20241022`
- Expensive: `claude-3-opus-20240229`
- Fast/Cheap: `claude-3-haiku-20240307`

**Azure:**
- Depends on your deployments
- Same models as OpenAI but enterprise-hosted

**LM Studio:**
- Any model you load
- Supports GGUF format models

---

## Configuration Format

### Top-Level LLM Config

```yaml
llm:
  # Primary backend
  backend: "ollama"

  # Optional fallback chain
  fallback_backends: ["openai"]

  # Global defaults for ALL tools
  global_defaults:
    default_backend: "ollama"
    default_embedding_backend: "openai"
    temperature: 0.7
    max_tokens: 4096

  # Backend-specific configs below
  ollama: { ... }
  openai: { ... }
  anthropic: { ... }
  azure: { ... }
  lmstudio: { ... }
```

### Key Concepts

**`backend`** - Primary backend to use by default

**`fallback_backends`** - Automatic fallback if primary fails

**`global_defaults.default_backend`** - Backend for ALL tools (unless overridden)

**This is the magic**: Set `global_defaults.default_backend` to make ALL tools use that backend without configuring each tool individually!

---

## Backend-Specific Setup

### Ollama

```yaml
ollama:
  # Base URL for Ollama server
  base_url: "http://localhost:11434"

  # Model assignments for different roles
  models:
    overseer: "llama3"
    generator: "qwen2.5-coder:14b"
    evaluator: "llama3"
    triage: "tinyllama"

  # Multi-endpoint load balancing (optional)
  endpoints:
    overseer:
      - "http://localhost:11434"
      - "http://server2:11434"

  # Context windows
  context_windows:
    llama3: 8192
    "qwen2.5-coder:14b": 131072
```

**Setup:**
1. Install Ollama: https://ollama.ai
2. Pull models: `ollama pull llama3`
3. Start server: `ollama serve`
4. Use config above

### OpenAI

```yaml
openai:
  # API key (use env var recommended)
  api_key: "${OPENAI_API_KEY}"

  # Base URL (default or custom)
  base_url: "https://api.openai.com/v1"

  # Optional organization
  organization: null

  # Model assignments
  models:
    overseer: "gpt-4"
    generator: "gpt-4"
    evaluator: "gpt-4"
    triage: "gpt-3.5-turbo"

  # Embedding model
  embedding_model: "text-embedding-3-small"

  # Context windows
  context_windows:
    gpt-4: 8192
    gpt-4-turbo: 128000
```

**Setup:**
1. Get API key: https://platform.openai.com/api-keys
2. Set environment variable: `export OPENAI_API_KEY="sk-..."`
3. Use config above

### Anthropic

```yaml
anthropic:
  # API key
  api_key: "${ANTHROPIC_API_KEY}"

  # Base URL
  base_url: "https://api.anthropic.com"

  # Model assignments
  models:
    overseer: "claude-3-5-sonnet-20241022"
    generator: "claude-3-5-sonnet-20241022"
    evaluator: "claude-3-5-sonnet-20241022"
    triage: "claude-3-haiku-20240307"

  # Context windows (all 200k for Claude 3)
  context_windows:
    "claude-3-5-sonnet-20241022": 200000
    "claude-3-opus-20240229": 200000
```

**Setup:**
1. Get API key: https://console.anthropic.com/
2. Set environment variable: `export ANTHROPIC_API_KEY="sk-ant-..."`
3. Use config above

**Note:** Anthropic doesn't provide embedding models. Use OpenAI or Ollama for embeddings.

### Azure OpenAI

```yaml
azure:
  # API key
  api_key: "${AZURE_OPENAI_API_KEY}"

  # Your Azure endpoint
  endpoint: "${AZURE_OPENAI_ENDPOINT}"

  # Default deployment
  deployment_name: "gpt-4"

  # API version
  api_version: "2024-02-15-preview"

  # Deployment assignments
  deployments:
    overseer:
      deployment: "gpt-4"
      model: "gpt-4"
    generator:
      deployment: "gpt-4-code"
      model: "gpt-4"

  # Context windows
  context_windows:
    gpt-4: 8192
    gpt-35-turbo: 16385
```

**Setup:**
1. Create Azure OpenAI resource
2. Deploy models (create deployments)
3. Get endpoint and API key from Azure portal
4. Set environment variables:
   ```bash
   export AZURE_OPENAI_API_KEY="..."
   export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
   ```

**Important:** Azure uses "deployments" not model names. Each deployment is an instance of a model.

### LM Studio

```yaml
lmstudio:
  # Base URL for LM Studio server
  base_url: "http://localhost:1234/v1"

  # Model assignments (use loaded model name)
  models:
    overseer: "local-model"
    generator: "local-model"
    evaluator: "local-model"

  # Context windows
  context_windows:
    "local-model": 8192
```

**Setup:**
1. Download LM Studio: https://lmstudio.ai
2. Load a model (e.g., Llama 3, Mistral, etc.)
3. Start the local server (⌘+R or Ctrl+R)
4. Use config above

---

## Tools Configuration

### Option 1: Global Backend (Recommended)

Set once, applies to all tools:

```yaml
llm:
  backend: "anthropic"
  global_defaults:
    default_backend: "anthropic"  # ALL tools use this!

tools:
  my_tool:
    type: "llm"
    llm:
      model_key: "generator"  # Uses anthropic.models.generator
```

**Benefit:** Add 100 tools, all automatically use Anthropic. No per-tool config!

### Option 2: Override Per Tool

```yaml
llm:
  backend: "ollama"  # Default

tools:
  expensive_tool:
    type: "llm"
    backend: "anthropic"  # Override for this tool only
    llm:
      model: "claude-3-opus-20240229"
```

### Option 3: Mixed Backends

```yaml
llm:
  global_defaults:
    default_backend: "ollama"  # Cheap default

tools:
  cheap_tool:
    type: "llm"
    # Uses ollama (global default)

  expensive_tool:
    type: "llm"
    backend: "openai"
    llm:
      model: "gpt-4"
```

### Model Keys vs Direct Models

**Model Key (recommended):**
```yaml
llm:
  anthropic:
    models:
      generator: "claude-3-5-sonnet-20241022"

tools:
  my_tool:
    llm:
      model_key: "generator"  # References anthropic.models.generator
```

**Direct Model:**
```yaml
tools:
  my_tool:
    llm:
      model: "claude-3-5-sonnet-20241022"  # Hardcoded
```

Use model keys for flexibility - change the model once and all tools update!

---

## Model Selector Tool

The model selector tool enables **natural language model selection**:

```python
# In a workflow:
"Using my OpenAPI settings use gpt-4 for this operation"
"Select the best model for code generation"
"Use Anthropic Claude for this analysis"
```

### Configuration

```yaml
model_selector:
  enabled: true

  # Scoring weights
  weights:
    context_window: 30
    speed: 25
    cost: 15
    quality: 15
    specialization: 15
```

### Usage Examples

**From Python:**
```python
from src.model_selector_tool import ModelSelectorTool

selector = ModelSelectorTool(config_manager)

# Select best model for a task
recommendations = selector.select_model(
    task_description="Generate complex Python code with type hints",
    constraints={"max_cost": "medium"},
    top_k=3
)

# Use the top recommendation
best = recommendations[0]
client = selector.get_client_for_selection(best)
result = client.generate(
    model=best["model"],
    prompt="Write a binary search function"
)
```

**Natural Language Selection:**
```python
# These phrases are automatically parsed:
"use gpt-4" -> backend=openai, model=gpt-4
"use claude" -> backend=anthropic
"use anthropic opus" -> backend=anthropic, model=opus
"use my openapi settings" -> backend=openai
```

---

## Advanced Patterns

### Pattern 1: Cost Optimization

Use cheap models for triage, expensive for important tasks:

```yaml
llm:
  backend: "ollama"  # Cheap default

  ollama:
    models:
      triage: "tinyllama"  # Super fast/cheap
      evaluator: "llama3"

tools:
  critical_analysis:
    backend: "anthropic"  # Override for critical task
    llm:
      model: "claude-3-opus-20240229"
```

### Pattern 2: Speed Optimization

```yaml
llm:
  backend: "openai"

  openai:
    models:
      triage: "gpt-3.5-turbo"  # Fast
      generator: "gpt-4-turbo"  # Balanced
```

### Pattern 3: Privacy-First

```yaml
llm:
  backend: "ollama"  # All local, no external APIs

  ollama:
    base_url: "http://localhost:11434"
    models:
      overseer: "llama3"
      generator: "qwen2.5-coder:14b"
```

### Pattern 4: Enterprise Hybrid

```yaml
llm:
  backend: "azure"  # Enterprise primary
  fallback_backends: ["ollama"]  # Local fallback

  azure:
    endpoint: "${AZURE_OPENAI_ENDPOINT}"
    # ...

  ollama:
    base_url: "http://internal-ollama:11434"
    # ...
```

### Pattern 5: Multi-Region Azure

```yaml
llm:
  backend: "azure"

  azure:
    deployments:
      us_east:
        deployment: "gpt-4-us-east"
        endpoint: "https://us-east.openai.azure.com"
      eu_west:
        deployment: "gpt-4-eu-west"
        endpoint: "https://eu-west.openai.azure.com"
```

---

## Environment Variables

### Recommended Setup

Create `.env` file:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com

# Optional
CODE_EVOLVER_DEBUG=0  # Set to 1 for debug logging
```

Load with:
```bash
export $(cat .env | xargs)
```

Or use in config:
```yaml
openai:
  api_key: "${OPENAI_API_KEY}"
```

---

## Troubleshooting

### Connection Issues

**Ollama:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Pull a model
ollama pull llama3
```

**OpenAI:**
```bash
# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Anthropic:**
```bash
# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-haiku-20240307","max_tokens":1,"messages":[{"role":"user","content":"Hi"}]}'
```

### Common Errors

**"No API key provided"**
- Set environment variable or add to config
- Check spelling: `OPENAI_API_KEY` not `OPENAI_KEY`

**"Model not found"**
- For Ollama: `ollama pull <model-name>`
- For Azure: Check deployment name (not model name!)
- For OpenAI/Anthropic: Check model ID spelling

**"Timeout"**
- Increase timeout in config
- Check network/firewall
- For Ollama: Check if model is loaded (`ollama ps`)

**"Context length exceeded"**
- Reduce prompt length
- Use model with larger context window
- Enable prompt truncation in config

---

## Migration Guide

### From Ollama-Only to Multi-Backend

**Before:**
```yaml
# Old config (Ollama only)
ollama:
  base_url: "http://localhost:11434"
```

**After:**
```yaml
llm:
  backend: "ollama"
  global_defaults:
    default_backend: "ollama"

  ollama:
    base_url: "http://localhost:11434"
    models:
      overseer: "llama3"
      generator: "qwen2.5-coder:14b"

  # Add Anthropic for complex tasks
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      overseer: "claude-3-5-sonnet-20241022"
```

Then override per tool:
```yaml
tools:
  complex_reasoning:
    backend: "anthropic"
```

---

## Best Practices

1. **Use environment variables for API keys** - Never commit keys to git
2. **Start with one backend** - Add more as needed
3. **Use global defaults** - Easier to maintain
4. **Test with cheap models first** - Debug with `gpt-3.5-turbo` or `tinyllama`
5. **Monitor costs** - Set up billing alerts
6. **Cache results** - Enable RAG caching for repeated queries
7. **Use model keys** - More flexible than hardcoded models

---

## Examples

See:
- `config.example.yaml` - All backends demonstrated
- `config.anthropic-simple.yaml` - Minimal Anthropic setup
- `config.yaml` - Your live config (customize from examples)

---

## Support

- GitHub Issues: https://github.com/scottgal/mostlylucid.dse/issues
- Documentation: `/docs`
- Examples: `/examples`
