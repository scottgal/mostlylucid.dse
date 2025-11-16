# Setting Up Anthropic Claude Backend

## Prerequisites

1. Get an Anthropic API key from [https://console.anthropic.com/](https://console.anthropic.com/)
2. **Optionally** ensure Ollama is running locally for embeddings: `ollama serve`
   - Required ONLY if you want to use RAG memory (embeddings)
   - NOT required for basic text generation
3. The system uses the **official Anthropic Python SDK** for better reliability and error handling

## Setup Instructions

### PowerShell (Windows)

```powershell
# Set the API key environment variable (WITHOUT the ANTHROPIC_API_KEY= prefix!)
$env:ANTHROPIC_API_KEY="sk-ant-api03-..."

# Verify it's set
echo $env:ANTHROPIC_API_KEY

# Run with Anthropic config
python chat_cli.py --config config.anthropic.yaml
```

**IMPORTANT:** Do NOT include `ANTHROPIC_API_KEY=` in the value! Just the key itself!

✅ **Correct:**
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-api03-GmO7sOLpRF0Tc3ytu..."
```

❌ **Wrong:**
```powershell
$env:ANTHROPIC_API_KEY="ANTHROPIC_API_KEY=sk-ant-api03..."  # Don't do this!
```

### Bash/ZSH (Linux/Mac)

```bash
# Set the API key
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# Verify
echo $ANTHROPIC_API_KEY

# Run with Anthropic config
python chat_cli.py --config config.anthropic.yaml
```

### Permanent Setup

#### Windows (PowerShell)

```powershell
# Add to your PowerShell profile
notepad $PROFILE

# Add this line:
$env:ANTHROPIC_API_KEY="sk-ant-api03-..."
```

#### Linux/Mac (Bash)

```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-..."' >> ~/.bashrc
source ~/.bashrc
```

## Verification

After setting the environment variable, verify the setup:

```powershell
# Check that the API key is set
echo $env:ANTHROPIC_API_KEY

# Should show your key starting with sk-ant-api03-

# Start the CLI
python chat_cli.py --config config.anthropic.yaml
```

You should see:
```
> Processing configuration...
Using anthropic backend for LLM
OK Using Qdrant for RAG memory
> Loading 42 tool(s) from YAML files...
```

If you see "Using ollama backend for LLM", the API key isn't set correctly!

## Troubleshooting

### Issue: "Using ollama backend for LLM" instead of "Using anthropic backend"

**Cause:** API key not set or set incorrectly

**Fix:**
```powershell
# PowerShell - make sure NO extra text!
$env:ANTHROPIC_API_KEY="sk-ant-api03-YOUR-KEY-HERE"

# Verify
echo $env:ANTHROPIC_API_KEY
```

### Issue: "404 Client Error: Not Found for url: https://api.anthropic.com/api/embeddings"

**Cause:** Ollama not running locally for embeddings

**Fix:**
```powershell
# Start Ollama (separate terminal)
ollama serve

# Pull embedding model if needed
ollama pull nomic-embed-text
```

**Note:** Embeddings ALWAYS use local Ollama, even when using Anthropic for LLM. This is by design because Anthropic doesn't provide an embeddings API.

### Issue: Environment variable not persisting between sessions

**Fix:** Add to your shell profile (see "Permanent Setup" above)

## Cost Estimates

When using config.anthropic.yaml:

- **god** (claude-opus): ~$15 per million input tokens, ~$75 per million output
- **general/escalation** (claude-sonnet): ~$3 per million input tokens, ~$15 per million output
- **fast** (claude-haiku): ~$0.25 per million input tokens, ~$1.25 per million output
- **veryfast** (tinyllama): FREE (local Ollama)

Typical workflow: 10-50k tokens = **$0.03-$0.75 per generation**

## What Gets Used Where

| Component | Model | Backend | Why |
|-----------|-------|---------|-----|
| Main LLM (god) | Claude Opus | Anthropic | Most powerful tasks |
| Main LLM (general) | Claude Sonnet | Anthropic | Normal tasks |
| Fast LLM | Claude Haiku | Anthropic | Quick tasks |
| Very Fast (triage) | Claude Haiku | Anthropic | Fast validation/classification |
| Embeddings | nomic-embed-text | Ollama (local) | RAG memory (optional) |

**Key Point:** Ollama is now **optional** - only needed if you want to use RAG memory (embeddings). All LLM operations can run with just Anthropic!

## How Routing Works

The system uses a **Routing Client** that automatically detects which backend to use for each model:

1. When a model is requested, the routing client checks the model's `backend` field in the config
2. Anthropic models (claude-*) → Route to Anthropic API
3. Ollama models (tinyllama, nomic-embed-text) → Route to local Ollama
4. This happens automatically - no manual switching needed!

Example:
```
User request: "write a poem"
  ↓
Triage (tinyllama) → Routes to Ollama ✓
  ↓
Generation (claude-sonnet) → Routes to Anthropic ✓
  ↓
Evaluation (tinyllama) → Routes to Ollama ✓
```

## Switching Between Backends

```powershell
# Use local Ollama (free)
python chat_cli.py --config config.yaml

# Use Anthropic Claude (paid, better quality)
python chat_cli.py --config config.anthropic.yaml
```

Both configs use the same unified structure - just different model assignments!
