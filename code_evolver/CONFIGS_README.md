# Configuration Files Guide

mostlylucid DiSE supports multiple AI backends through swappable configuration files. All configs share the same tools definitions and structure - you just swap the provider.

## Available Configurations

### 1. **config.local.yaml** (Default - Ollama)
- **Provider**: Local Ollama models
- **Cost**: FREE (runs on your hardware)
- **Speed**: Fast (no network latency)
- **Setup**: Install Ollama, pull models
- **Best for**: Development, experimentation, privacy-sensitive work

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull required models
ollama pull llama3
ollama pull codellama
ollama pull tinyllama
ollama pull nomic-embed-text

# Run mostlylucid DiSE (uses config.yaml by default)
python chat_cli.py
```

### 2. **config.anthropic.yaml** (Claude)
- **Provider**: Anthropic Claude models
- **Cost**: ~$0.15-$0.75 per workflow (pay-as-you-go)
- **Speed**: Very fast (API-based)
- **Setup**: Get API key from https://console.anthropic.com/
- **Best for**: Production, high-quality output, long context windows

```bash
# Set API key
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# Run with Anthropic config
python chat_cli.py --config config.anthropic.yaml
```

**Base Model**: `claude-3-5-sonnet-20241022` (200K context)
- All tools use this by default
- Fast tasks use: `claude-3-haiku-20240307`
- Security/complex tasks use: `claude-3-opus-20240229`

### 3. **config.openai.yaml** (GPT)
- **Provider**: OpenAI GPT models
- **Cost**: ~$0.01-$0.50 per workflow (pay-as-you-go)
- **Speed**: Very fast (API-based)
- **Setup**: Get API key from https://platform.openai.com/api-keys
- **Best for**: General purpose, good balance of cost/quality

```bash
# Set API key
export OPENAI_API_KEY='sk-...'

# Run with OpenAI config
python chat_cli.py --config config.openai.yaml
```

**Base Model**: `gpt-4o` (128K context)
- All tools use this by default
- Fast tasks use: `gpt-4o-mini`
- Reasoning tasks use: `o1-preview`

### 4. **config.azure.yaml** (Azure OpenAI)
- **Provider**: Azure OpenAI Service
- **Cost**: Same as OpenAI (pay-as-you-go)
- **Speed**: Very fast (API-based)
- **Setup**: Create Azure OpenAI resource, deploy models
- **Best for**: Enterprise, compliance requirements, Azure ecosystem

```bash
# Set credentials
export AZURE_OPENAI_API_KEY='your-key'
export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com'

# Update deployment names in config.azure.yaml to match your deployments

# Run with Azure config
python chat_cli.py --config config.azure.yaml
```

**Base Deployment**: `gpt-4o` (you name this in Azure)
- Must create deployments in Azure OpenAI Studio first
- Update config file with your deployment names

## Configuration Structure

All config files follow this pattern:

```yaml
# Backend selection
llm:
  backend: "anthropic"  # or "openai", "azure", "ollama"

  anthropic:  # Backend-specific settings
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      fast: "claude-3-haiku-20240307"
      base: "claude-3-5-sonnet-20241022"  # THE BASE MODEL
      powerful: "claude-3-opus-20240229"

# Shared tools definitions
tools:
  general:  # General code generator
    name: "General Code Generator"
    type: "llm"
    llm:
      backend: "anthropic"  # References backend above
      model: "claude-3-5-sonnet-20241022"  # Uses base model

  fast_code_generator:  # Fast code generator
    llm:
      backend: "anthropic"
      model: "claude-3-haiku-20240307"  # Uses fast model

  security_auditor:  # Security auditor
    llm:
      backend: "anthropic"
      model: "claude-3-opus-20240229"  # Uses powerful model
```

## Swapping Providers

**Easy Method**: Use the `--config` flag:
```bash
python chat_cli.py --config config.openai.yaml
```

**Default Method**: Copy your preferred config to `config.yaml`:
```bash
cp config.anthropic.yaml config.yaml
python chat_cli.py
```

## Base Model Pattern

Each config defines a **base model** that most tools use:

| Config | Base Model | Used By |
|--------|-----------|---------|
| **local** | codellama | 90% of tools |
| **anthropic** | claude-3-5-sonnet-20241022 | 90% of tools |
| **openai** | gpt-4o | 90% of tools |
| **azure** | gpt-4o (deployment) | 90% of tools |

**Fast model**: Simple tasks (spell check, quick feedback)
**Base model**: Most tasks (code generation, content, review)
**Powerful model**: Complex tasks (security audit, deep reasoning)

## Tools Configuration

All tools are backend-agnostic. They just reference the backend:

```yaml
tools:
  code_reviewer:
    name: "Code Reviewer"
    type: "llm"
    llm:
      backend: "anthropic"  # Change this line to swap provider
      model: "claude-3-5-sonnet-20241022"  # And this line
```

**To switch all tools to OpenAI**:
1. Open config file
2. Change `llm.backend` to "openai"
3. Change model names to GPT models
4. Done!

Or just use a different config file that's already set up.

## Cost Optimization

### Free (Local)
```bash
python chat_cli.py --config config.local.yaml
```
- Uses Ollama (100% free)
- Slower on CPU, fast on GPU
- Privacy: Everything stays local

### Low Cost (OpenAI mini)
```yaml
# In config.openai.yaml, change base model:
models:
  base: "gpt-4o-mini"  # Instead of gpt-4o
```
- ~10x cheaper than GPT-4o
- Still good quality
- Avg cost: $0.01-0.05 per workflow

### Balanced (Anthropic Sonnet)
```bash
python chat_cli.py --config config.anthropic.yaml
```
- Best quality/cost ratio
- 200K context window
- Avg cost: $0.15-0.30 per workflow

### High Quality (Claude Opus / o1)
```yaml
# Set powerful model as base
models:
  base: "claude-3-opus-20240229"  # or "o1-preview"
```
- Best reasoning and quality
- Most expensive
- Avg cost: $0.50-$2.00 per workflow

## Hybrid Configurations

You can mix providers in a single config:

```yaml
llm:
  backend: "anthropic"  # Default backend

ollama:
  models:
    # Most tasks use Anthropic
    generator:
      model: "claude-3-5-sonnet-20241022"
      backend: "anthropic"

    # But embeddings use local Ollama (free)
    embedding:
      model: "nomic-embed-text"
      backend: "ollama"
      endpoint: "http://localhost:11434"
```

## Environment Variables

Set these before running:

### Anthropic
```bash
export ANTHROPIC_API_KEY='sk-ant-api03-...'
```

### OpenAI
```bash
export OPENAI_API_KEY='sk-...'
```

### Azure
```bash
export AZURE_OPENAI_API_KEY='your-key'
export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com'
```

### Local (Ollama)
```bash
# No API keys needed!
# Just make sure Ollama is running:
ollama serve
```

## Checking Backend Status

Use the `backends` command in chat_cli to check what's configured:

```bash
python chat_cli.py
DiSE> backends
```

Output:
```
Backend Status
┌────────────┬─────────────┬──────────────────────────────────┬───────┐
│ Backend    │ Status      │ Message                          │ Ready │
├────────────┼─────────────┼──────────────────────────────────┼───────┤
│ anthropic  │ OK READY    │ Anthropic configured with API    │ YES   │
│ openai     │ WARN NO KEY │ OpenAI API key not set           │ NO    │
│ azure      │ - NOT SET   │ Azure is not configured          │ NO    │
│ ollama     │ OK READY    │ Ollama at http://localhost:11434│ YES   │
└────────────┴─────────────┴──────────────────────────────────┴───────┘
```

## Quick Start Examples

### Example 1: Start with local (free)
```bash
ollama pull llama3 codellama tinyllama
python chat_cli.py
```

### Example 2: Switch to Anthropic (best quality)
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
python chat_cli.py --config config.anthropic.yaml
```

### Example 3: Try OpenAI (good balance)
```bash
export OPENAI_API_KEY='sk-...'
python chat_cli.py --config config.openai.yaml
```

### Example 4: Use Azure (enterprise)
```bash
export AZURE_OPENAI_API_KEY='...'
export AZURE_OPENAI_ENDPOINT='https://...'
# Edit config.azure.yaml with your deployment names
python chat_cli.py --config config.azure.yaml
```

## Creating Custom Configs

Want to create your own config? Copy an existing one:

```bash
cp config.anthropic.yaml config.custom.yaml
```

Then edit:
1. Change `llm.backend` to your provider
2. Update model names
3. Adjust tools to reference your models
4. Save and use: `python chat_cli.py --config config.custom.yaml`

## Tips

1. **Start local**: Use `config.local.yaml` for development
2. **Go cloud for production**: Switch to Anthropic/OpenAI for quality
3. **Check costs**: Use `backends` command to see what's configured
4. **Hybrid approach**: Use local for embeddings, cloud for LLM
5. **Test before committing**: Try a few generations before large batch jobs

## Support

- Local (Ollama): https://ollama.ai/
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/
- Azure: https://portal.azure.com/

## License

All configurations use the same license as mostlylucid DiSE (MIT).
