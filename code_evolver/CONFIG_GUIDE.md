# Configuration Guide

## Overview

Code Evolver supports multiple configuration files for different backends and use cases. This guide explains which config files to use and when.

## Quick Start

**For most users**: Use the default `config.yaml` which is configured for Ollama (local LLMs).

**For specific backends**: Use one of the backend-specific configs:
- `config.anthropic.yaml` - For Claude models via Anthropic API
- `config.openai.yaml` - For GPT models via OpenAI API
- `config.azure.yaml` - For Azure OpenAI
- `config.local.yaml` - For local/offline models (Ollama, LM Studio)

**For tiered model systems**: Use `config.tiered.yaml` for advanced tier-based model selection.

## Configuration Files

### Primary Configuration Files

#### `config.yaml` (Default)
- **When to use**: Default configuration for Ollama-based local LLMs
- **Backend**: Ollama
- **Features**: Full-featured config with all settings
- **Models**: Configurable Ollama models (llama3, codellama, etc.)

#### `config.tiered.yaml` (Recommended for Production)
- **When to use**: When you want automatic model escalation and tier-based selection
- **Backend**: Any (Ollama, Anthropic, OpenAI, Azure)
- **Features**: Hierarchical model tiers with automatic escalation
- **Benefits**:
  - Tools reference tiers (e.g., `coding.tier_2`) not specific models
  - Automatic escalation from simple→general→complex→god-level
  - Clean separation of concerns
  - Easy to swap models without changing tool definitions
- **Documentation**: See `MODEL_TIERS.md` for full details

### Backend-Specific Configurations

#### `config.anthropic.yaml`
- **Backend**: Anthropic Claude API
- **Models**: claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
- **Use case**: Production deployments using Claude models
- **Requires**: `ANTHROPIC_API_KEY` environment variable

#### `config.anthropic.minimal.yaml`
- **Same as above** but with minimal settings (faster to load)

#### `config.openai.yaml`
- **Backend**: OpenAI API
- **Models**: gpt-4o, gpt-4o-mini, o1-preview
- **Use case**: Production deployments using GPT models
- **Requires**: `OPENAI_API_KEY` environment variable

#### `config.openai.minimal.yaml`
- **Same as above** but with minimal settings

#### `config.azure.yaml`
- **Backend**: Azure OpenAI
- **Use case**: Enterprise deployments using Azure
- **Requires**: `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` environment variables

#### `config.azure.minimal.yaml`
- **Same as above** but with minimal settings

#### `config.local.yaml`
- **Backend**: Ollama or LM Studio
- **Use case**: Local development without API costs
- **Models**: Local models only (llama3, codellama, etc.)

#### `config.local.minimal.yaml`
- **Same as above** but with minimal settings

#### `config.lmstudio.minimal.yaml`
- **Backend**: LM Studio
- **Use case**: Using LM Studio for local inference with a GUI
- **Endpoint**: `http://localhost:1234/v1`

#### `config.hybrid.yaml`
- **Backend**: Mixed (multiple backends)
- **Use case**: Using different backends for different purposes
  - Example: Fast local models for triage, cloud models for complex tasks

### Supporting Files

#### `backends.yaml`
- Defines available backend configurations
- Not used directly - referenced by main config files

## Tool Definitions

### Tools Directory Structure

```
tools/
├── llm/              # LLM-based tools
│   ├── code_reviewer.yaml
│   ├── content_generator.yaml
│   ├── fast_code_generator.yaml
│   ├── general.yaml
│   ├── quick_feedback.yaml
│   ├── security_auditor.yaml
│   └── summarizer.yaml
├── executable/       # Executable/command-line tools
│   └── save_to_disk.yaml
└── custom/           # Custom tool definitions
    └── (your custom tools here)
```

### Tool Definition Format

All tools in the `tools/` directory use tier-based references:

```yaml
name: "Code Reviewer"
type: "llm"
description: "Reviews code for quality and issues"

# Performance characteristics
cost_tier: "medium"
speed_tier: "fast"
quality_tier: "excellent"
max_output_length: "long"

# LLM configuration
llm:
  tier: "quality.tier_2"  # Tiered system (preferred)
  role: "base"            # Legacy role system (fallback)

  system_prompt: |
    You are an expert code reviewer...

  prompt_template: |
    Review this code: {code}
```

### Tier vs Role References

**Tier-based (Preferred)**:
- `tier: "coding.tier_1"` - Fast, simple coding tasks
- `tier: "coding.tier_2"` - General coding (default)
- `tier: "coding.tier_3"` - Complex/advanced coding
- `tier: "content.tier_2"` - Quality content generation
- `tier: "quality.tier_2"` - Quality review/assessment
- `tier: "validation.tier_1"` - Fast validation

**Role-based (Fallback)**:
- `role: "fast"` - Fast model (tinyllama, gpt-4o-mini, claude-haiku)
- `role: "base"` - Base model (llama3, gpt-4o, claude-sonnet)
- `role: "powerful"` - Most capable model (qwen2.5-coder:14b, o1-preview, claude-opus)

Tools can specify both for maximum compatibility.

## How to Use a Specific Config

### Command Line

```bash
# Use default config.yaml
python chat_cli.py

# Use a specific config
python chat_cli.py --config config.tiered.yaml
python chat_cli.py --config config.anthropic.yaml
python chat_cli.py --config config.openai.yaml
```

### In Code

```python
from src.config_manager import ConfigManager

# Load default config
config = ConfigManager()

# Load specific config
config = ConfigManager("config.tiered.yaml")
config = ConfigManager("config.anthropic.yaml")
```

## Choosing the Right Configuration

### For Development
- Use `config.yaml` or `config.local.yaml`
- Free, runs locally, no API costs
- Requires Ollama to be running

### For Production
- Use `config.tiered.yaml` with your preferred backend
- Automatic model escalation
- Clean tier-based tool references

### For Specific Backends
- **Claude users**: `config.anthropic.yaml` or `.minimal.yaml`
- **GPT users**: `config.openai.yaml` or `.minimal.yaml`
- **Azure users**: `config.azure.yaml` or `.minimal.yaml`
- **Local users**: `config.local.yaml` or `config.lmstudio.minimal.yaml`

### For Cost Optimization
- Use `config.tiered.yaml` to ensure cheaper models are tried first
- Automatic escalation only when needed
- Fine-grained control over which tier each task uses

## Environment Variables

Different configs require different environment variables:

```bash
# For Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# For OpenAI
export OPENAI_API_KEY="sk-..."

# For Azure
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"

# For Ollama (usually not needed, uses localhost)
export OLLAMA_BASE_URL="http://localhost:11434"
```

## Configuration Validation

Test your configuration:

```bash
# Check backend availability
python demo_backend_checker.py

# Test configuration loading
python -c "from src.config_manager import ConfigManager; c = ConfigManager('config.tiered.yaml'); print('Config loaded successfully')"
```

## Troubleshooting

### "Config file not found"
- Ensure you're in the `code_evolver/` directory
- Use full path: `python chat_cli.py --config /path/to/config.yaml`

### "Backend not available"
- Check environment variables are set
- For Ollama: ensure `ollama serve` is running
- For APIs: verify API keys are valid

### "Tool tier not found"
- Ensure `config.tiered.yaml` defines the tier your tool references
- Check `MODEL_TIERS.md` for valid tier names

## See Also

- `MODEL_TIERS.md` - Complete guide to the tiered model system
- `CLAUDE.md` - Complete system documentation
- `README.md` - Project overview and quick start