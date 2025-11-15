# New Configuration Architecture

## Overview

The configuration system is now **fully decoupled**:

1. **`backends.yaml`** - Defines all AI backends with model metadata (price, context, speed)
2. **`tools/`** - Directory of tool definitions (each tool in its own file)
3. **`config.*.yaml`** - Minimal configs that just select backend + map roles

**No more tool duplication!** Tools are defined once and work with any backend.

## Architecture

```
code_evolver/
├── backends.yaml              # All backends & model metadata
├── tools/                     # Tool definitions (ONE TIME)
│   ├── llm/                   # LLM-based tools
│   │   ├── general.yaml       # References "base" role
│   │   ├── fast_code_generator.yaml  # References "fast" role
│   │   └── security_auditor.yaml     # References "powerful" role
│   ├── executable/            # Non-LLM tools
│   │   └── save_to_disk.yaml
│   └── custom/                # Custom implementation tools
│       └── http_server.yaml
├── config.anthropic.minimal.yaml  # Just role mapping
├── config.openai.minimal.yaml     # Just role mapping
└── config.local.minimal.yaml      # Just role mapping
```

## How It Works

### 1. backends.yaml - Backend Definitions

Defines all available backends with model metadata:

```yaml
backends:
  anthropic:
    type: "anthropic"
    requires_api_key: true
    api_key_env: "ANTHROPIC_API_KEY"

    models:
      "claude-3-haiku-20240307":
        context_window: 200000
        cost_per_1m_input: 0.25
        cost_per_1m_output: 1.25
        speed_tier: "very-fast"
        quality_tier: "good"
        best_for: ["fast-tasks", "simple-code"]

      "claude-3-5-sonnet-20241022":
        context_window: 200000
        cost_per_1m_input: 3.00
        cost_per_1m_output: 15.00
        speed_tier: "fast"
        quality_tier: "excellent"
        best_for: ["general", "code", "base-model"]
```

### 2. tools/ - Tool Definitions (Once!)

Each tool references **abstract roles**, not specific models:

**tools/llm/general.yaml:**
```yaml
name: "General Code Generator"
type: "llm"
description: "General purpose code generation"

llm:
  role: "base"  # NOT a specific model!

  system_prompt: |
    You are an expert software engineer.
    Priority: {priority}

  prompt_template: |
    Generate code for: {task}
```

**tools/llm/security_auditor.yaml:**
```yaml
name: "Security Auditor"
type: "llm"

llm:
  role: "powerful"  # Use most capable model

  prompt_template: |
    Audit for security: {code}
```

### 3. config.*.yaml - Just Role Mapping!

**config.anthropic.minimal.yaml:**
```yaml
llm:
  backend: "anthropic"

  # Map abstract roles to actual Anthropic models
  model_roles:
    fast: "claude-3-haiku-20240307"
    base: "claude-3-5-sonnet-20241022"      # <-- The "base" all tools use
    powerful: "claude-3-opus-20240229"

# ... rest is just execution/logging/etc config
```

**config.openai.minimal.yaml:**
```yaml
llm:
  backend: "openai"

  # Map abstract roles to actual OpenAI models
  model_roles:
    fast: "gpt-4o-mini"
    base: "gpt-4o"                          # <-- The "base" all tools use
    powerful: "o1-preview"

# ... rest is identical to anthropic config
```

## Role System

Tools reference these abstract roles:

| Role | Purpose | Example Models |
|------|---------|---------------|
| **fast** | Simple tasks, quick operations | claude-haiku, gpt-4o-mini, tinyllama |
| **base** | Most tasks, default model | claude-sonnet, gpt-4o, codellama |
| **powerful** | Complex reasoning, security | claude-opus, o1-preview, qwen2.5-coder:14b |
| **god_level** | Last resort, most capable | deepseek-coder, claude-opus |
| **embedding** | Vector embeddings for RAG | nomic-embed-text, text-embedding-3-small |

## Benefits

### ✅ Zero Tool Duplication
- Tools defined **once** in `tools/` directory
- Works with **any** backend automatically

### ✅ Easy Backend Switching
```bash
# Switch from Anthropic to OpenAI
python chat_cli.py --config config.openai.minimal.yaml

# Switch from OpenAI to local Ollama
python chat_cli.py --config config.local.minimal.yaml
```

### ✅ Clean Separation
- **Backend metadata** → `backends.yaml`
- **Tool definitions** → `tools/`
- **User config** → `config.*.yaml` (just picks backend + maps roles)

### ✅ Easy Tool Addition
Just drop a new .yaml file in `tools/llm/`:

**tools/llm/my_new_tool.yaml:**
```yaml
name: "My New Tool"
type: "llm"

llm:
  role: "base"  # Automatically uses right model for chosen backend!

  prompt_template: |
    Do something: {input}
```

## Example: Tool Using Different Models

**The `general` tool:**

```yaml
# tools/llm/general.yaml
llm:
  role: "base"  # References the base model
```

**When used with different backends:**

| Backend | Config | Actual Model Used |
|---------|--------|------------------|
| Anthropic | `config.anthropic.minimal.yaml` | claude-3-5-sonnet-20241022 |
| OpenAI | `config.openai.minimal.yaml` | gpt-4o |
| Ollama | `config.local.minimal.yaml` | codellama |

**Same tool, different model, zero code changes!**

## Migration Path

### Old Way (Duplicated)
```yaml
# config.anthropic.yaml
tools:
  general:
    llm:
      backend: "anthropic"
      model: "claude-3-5-sonnet-20241022"

# config.openai.yaml
tools:
  general:
    llm:
      backend: "openai"
      model: "gpt-4o"
```

### New Way (DRY)
```yaml
# tools/llm/general.yaml (ONCE!)
llm:
  role: "base"

# config.anthropic.minimal.yaml
llm:
  backend: "anthropic"
  model_roles:
    base: "claude-3-5-sonnet-20241022"

# config.openai.minimal.yaml
llm:
  backend: "openai"
  model_roles:
    base: "gpt-4o"
```

## Directory Structure

```
code_evolver/
├── backends.yaml                  # Backend & model metadata
│
├── tools/                         # Tool definitions
│   ├── llm/                       # LLM-based tools
│   │   ├── general.yaml
│   │   ├── fast_code_generator.yaml
│   │   ├── content_generator.yaml
│   │   ├── code_reviewer.yaml
│   │   ├── security_auditor.yaml
│   │   ├── quick_feedback.yaml
│   │   ├── summarizer.yaml
│   │   └── ... (more LLM tools)
│   │
│   ├── executable/                # CLI/script tools
│   │   ├── save_to_disk.yaml
│   │   ├── load_from_disk.yaml
│   │   ├── pip_install.yaml
│   │   ├── pylint_checker.yaml
│   │   └── ... (more executable tools)
│   │
│   └── custom/                    # Custom Python tools
│       └── http_server.yaml
│
├── config.anthropic.minimal.yaml  # Anthropic: role mapping only
├── config.openai.minimal.yaml     # OpenAI: role mapping only
├── config.azure.minimal.yaml      # Azure: role mapping only
├── config.local.minimal.yaml      # Ollama: role mapping only
└── config.hybrid.minimal.yaml     # Hybrid: Cloud LLM + Local embeddings
```

## Usage

### Use Anthropic
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
python chat_cli.py --config config.anthropic.minimal.yaml
```

### Use OpenAI
```bash
export OPENAI_API_KEY='sk-...'
python chat_cli.py --config config.openai.minimal.yaml
```

### Use Local Ollama (Free)
```bash
ollama serve
python chat_cli.py --config config.local.minimal.yaml
```

### Hybrid (Cloud + Local Embeddings)
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
python chat_cli.py --config config.hybrid.minimal.yaml
# LLM tasks use Anthropic, embeddings use local Ollama
```

## Adding a New Tool

1. Create tool file: `tools/llm/my_tool.yaml`
2. Reference a role: `role: "base"` (or "fast", "powerful")
3. Done! Works with all backends automatically

## Adding a New Backend

1. Add to `backends.yaml`:
```yaml
backends:
  my_new_backend:
    type: "my_backend"
    models:
      my-fast-model:
        context_window: 32000
        cost_per_1m_input: 1.00
```

2. Create `config.my_backend.minimal.yaml`:
```yaml
llm:
  backend: "my_new_backend"
  model_roles:
    fast: "my-fast-model"
    base: "my-base-model"
    powerful: "my-powerful-model"
```

3. All existing tools work automatically!

## Summary

**Before:**
- Tools duplicated in every config
- 1000+ lines per config file
- Hard to maintain
- Easy to get out of sync

**After:**
- Tools defined once
- ~100 lines per config file
- Easy to maintain
- Impossible to get out of sync
- Backend-agnostic tools
- Clean separation of concerns
