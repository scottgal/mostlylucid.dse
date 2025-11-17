# Multi-Backend LLM Implementation Notes

Hey CLI brother! 👋

This document explains the multi-backend LLM implementation I just completed. Read this first before making changes to the backend system.

## 🎯 What Was Built

I added support for **5 LLM backends** (was just Ollama before):
- Ollama (local/self-hosted) - **existing**
- OpenAI (GPT-4, GPT-3.5, etc.) - **new**
- Anthropic (Claude 3.5, Opus, Haiku) - **new**
- Azure OpenAI (enterprise) - **new**
- LM Studio (local with OpenAI-compatible API) - **new**

Plus a **Model Selector Tool** that lets users say things like:
- "Using my OpenAPI settings use gpt-4 for this operation"
- "Use Anthropic Claude for this analysis"

## 📁 File Structure

### Core Implementation

```
code_evolver/src/
├── llm_client_base.py          # Abstract base class (interface)
├── ollama_client.py             # Existing Ollama implementation
├── openai_client.py             # NEW: OpenAI/ChatGPT support
├── anthropic_client.py          # NEW: Claude support
├── azure_client.py              # NEW: Azure OpenAI support
├── lmstudio_client.py           # NEW: LM Studio support
├── llm_client_factory.py        # NEW: Factory pattern + fallbacks
└── model_selector_tool.py       # NEW: Intelligent model selection
```

### Configuration & Docs

```
.
├── config.example.yaml           # Shows ALL backend configs
├── config.anthropic-simple.yaml  # Minimal "all Anthropic" setup
└── docs/
    └── BACKEND_CONFIGURATION.md  # Complete user guide
```

### Tests

```
code_evolver/tests/
└── test_multi_backend.py         # Comprehensive test suite
```

## 🏗️ Architecture Overview

### The Strategy Pattern

I used the **Strategy Pattern** with a **Factory** to make backends swappable:

```
┌─────────────────────┐
│  LLMClientBase      │  ← Abstract interface
│  (ABC)              │
└──────────┬──────────┘
           │
           ├── OllamaClient
           ├── OpenAIClient
           ├── AnthropicClient
           ├── AzureOpenAIClient
           └── LMStudioClient
```

All clients implement the same interface:
- `generate(model, prompt, system, ...)` - Main text generation
- `generate_code(prompt, constraints)` - Code generation
- `evaluate(code_summary, metrics)` - Evaluation
- `triage(metrics, targets)` - Quick pass/fail
- `check_connection()` - Health check
- `list_models()` - List available models

### The Factory Pattern

`LLMClientFactory` creates the right client based on config:

```python
# Simple usage
client = LLMClientFactory.create_client("openai", api_key="sk-...")

# From config
client = LLMClientFactory.create_from_config(config_manager, "anthropic")

# Multi-backend with fallback
client = MultiBackendClient(
    config_manager,
    primary_backend="anthropic",
    fallback_backends=["openai", "ollama"]
)
```

## 🔧 How It Works

### 1. Configuration Format

The new config structure in `config.yaml`:

```yaml
llm:
  # Which backend to use
  backend: "anthropic"

  # Optional fallbacks (tries in order if primary fails)
  fallback_backends: ["openai", "ollama"]

  # MAGIC: Global defaults apply to ALL tools!
  global_defaults:
    default_backend: "anthropic"  # Makes all tools use Anthropic
    temperature: 0.7
    max_tokens: 4096

  # Backend-specific configs
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      generator: "claude-3-5-sonnet-20241022"
      evaluator: "claude-3-5-sonnet-20241022"

  openai:
    api_key: "${OPENAI_API_KEY}"
    # ...
```

**Key insight**: Set `global_defaults.default_backend` once, and **all tools automatically use that backend** without per-tool configuration. Super clean!

### 2. Integration Points

Updated `chat_cli.py` to use factory pattern:

```python
# Before (hardcoded Ollama):
self.client = OllamaClient(self.config.ollama_url, config_manager=self.config)

# After (uses factory with fallback):
try:
    backend = self.config.config.get("llm", {}).get("backend", "ollama")
    self.client = LLMClientFactory.create_from_config(self.config, backend)
except Exception as e:
    # Graceful fallback to Ollama
    self.client = OllamaClient(self.config.ollama_url, config_manager=self.config)
```

**Backward compatible**: Old configs without `llm.backend` still work with Ollama.

### 3. Model Selector Tool

Registered automatically in `chat_cli.py`:

```python
from src.model_selector_tool import create_model_selector_tool

if self.config.config.get("model_selector", {}).get("enabled", True):
    create_model_selector_tool(self.config, self.tools_manager)
```

Users can then say:
- "use gpt-4" → backend=openai, model=gpt-4
- "use claude" → backend=anthropic
- "use my openapi settings" → backend=openai

The tool scores models based on:
- Task requirements (code, analysis, speed, etc.)
- Backend/model preferences
- Constraints (cost, speed, context window)
- Model capabilities

## 🧪 Testing

Run the comprehensive test suite:

```bash
cd code_evolver
pytest tests/test_multi_backend.py -v
```

Tests cover:
- ✅ All 5 backend clients
- ✅ Factory pattern
- ✅ Multi-backend fallback
- ✅ Model selector tool
- ✅ Configuration parsing
- ✅ Natural language parsing

## 🚀 How to Use

### For Users

**Simplest setup (Anthropic everything):**

```yaml
llm:
  backend: "anthropic"
  global_defaults:
    default_backend: "anthropic"
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
```

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python chat_cli.py
```

Done! All tools now use Claude.

**Mix backends (cost optimization):**

```yaml
llm:
  backend: "ollama"  # Cheap default
  global_defaults:
    default_backend: "ollama"

  ollama:
    models:
      triage: "tinyllama"  # Super fast/cheap

tools:
  expensive_analysis:
    backend: "anthropic"  # Override for this tool
    llm:
      model: "claude-3-opus-20240229"
```

### For Developers

**Adding a new backend:**

1. Create `src/my_backend_client.py`:

```python
from .llm_client_base import LLMClientBase

class MyBackendClient(LLMClientBase):
    def __init__(self, api_key=None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.backend_type = "mybackend"

    def check_connection(self, endpoint=None):
        # Implement health check
        pass

    def list_models(self, endpoint=None):
        # Return list of model IDs
        pass

    def generate(self, model, prompt, **kwargs):
        # Main generation logic
        pass

    # Implement other abstract methods...
```

2. Register in `llm_client_factory.py`:

```python
from .my_backend_client import MyBackendClient

class LLMClientFactory:
    BACKENDS = {
        "ollama": OllamaClient,
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "azure": AzureOpenAIClient,
        "lmstudio": LMStudioClient,
        "mybackend": MyBackendClient,  # ADD THIS
    }
```

3. Add config support in `create_from_config()`:

```python
elif backend_lower == "mybackend":
    return MyBackendClient(
        api_key=backend_config.get("api_key"),
        config_manager=config_manager
    )
```

4. Add tests in `tests/test_multi_backend.py`

5. Document in `docs/BACKEND_CONFIGURATION.md`

**That's it!** The factory handles the rest.

## 🎨 Design Decisions

### Why Abstract Base Class?

- **Type safety**: Ensures all backends implement required methods
- **Documentation**: Interface is self-documenting
- **IDE support**: Auto-completion works perfectly

### Why Factory Pattern?

- **Loose coupling**: Code doesn't know which backend it's using
- **Easy testing**: Mock the factory, not each backend
- **Runtime flexibility**: Switch backends without restarting

### Why Global Defaults?

**Problem**: With 100 tools, configuring backend for each is tedious.

**Solution**: Set once, applies to all:

```yaml
global_defaults:
  default_backend: "anthropic"  # All tools use this!
```

Override per-tool when needed:

```yaml
tools:
  special_tool:
    backend: "openai"  # Just this one
```

### Why Model Selector Tool?

**Problem**: Users don't know which model to use for which task.

**Solution**: Let them say "use gpt-4" or "best model for code" and the system figures it out.

Natural language beats config files for user experience.

## 🔒 Security Notes

**API Keys**: Always use environment variables:

```yaml
openai:
  api_key: "${OPENAI_API_KEY}"  # Good ✅

# NOT this:
# api_key: "sk-actual-key"  # Bad ❌ (committed to git!)
```

**Example configs**: All example configs use env vars or placeholder keys.

## 🐛 Debugging

**Check which backend is being used:**

```python
print(f"Backend: {client.backend_type}")
```

**Enable debug logging:**

```bash
export CODE_EVOLVER_DEBUG=1
python chat_cli.py
```

Shows full LLM conversations.

**Test specific backend:**

```python
from src.llm_client_factory import LLMClientFactory

client = LLMClientFactory.create_client("openai", api_key="test")
result = client.generate(model="gpt-4", prompt="Hello")
print(result)
```

## 📊 Performance Considerations

**Timeouts**: Each backend has dynamic timeouts based on model speed:

```python
TIER_TIMEOUTS = {
    "very-fast": 30,    # tinyllama, haiku
    "fast": 60,          # gpt-3.5-turbo
    "medium": 120,       # llama3, gpt-4
    "slow": 240,         # opus, large models
    "very-slow": 480     # huge models
}
```

Override in config if needed.

**Rate Limits**: Some APIs (OpenAI, Anthropic) have rate limits. The multi-backend fallback helps:

```yaml
llm:
  backend: "openai"
  fallback_backends: ["anthropic", "ollama"]  # Falls back on rate limit
```

**Context Windows**: Each backend tracks context limits:

- Ollama: 2k-128k (model-dependent)
- OpenAI: 8k-128k
- Anthropic: 200k (all Claude 3 models)
- Azure: Same as OpenAI
- LM Studio: Varies by loaded model

Prompts are auto-truncated if too long.

## 🔮 Future Enhancements

Ideas for next iteration:

1. **Streaming support**: Currently `stream=False` everywhere. Add streaming for real-time UX.

2. **Cost tracking**: Track API usage per backend:
   ```python
   client.get_usage_stats()  # tokens, cost, requests
   ```

3. **Caching**: Cache responses to reduce API calls:
   ```python
   client.generate(prompt, use_cache=True)
   ```

4. **Retry logic**: Automatic retry with exponential backoff.

5. **Load balancing**: Round-robin across multiple API keys.

6. **Embeddings**: Add embedding support to base class:
   ```python
   client.embed(texts)  # For RAG
   ```

7. **Fine-tuned models**: Support OpenAI fine-tuned models.

8. **Local models**: Add Transformers backend for Hugging Face models.

## 🚨 Common Pitfalls

### Pitfall 1: Forgetting API Keys

**Error**: "No API key provided"

**Fix**: Set environment variable:
```bash
export OPENAI_API_KEY="sk-..."
```

### Pitfall 2: Azure Deployments vs Models

Azure uses "deployments" not model names!

**Wrong**:
```yaml
azure:
  model: "gpt-4"  # ❌ Won't work
```

**Right**:
```yaml
azure:
  deployments:
    my_deployment:
      deployment: "my-gpt-4-deployment"  # ✅
      model: "gpt-4"  # Underlying model
```

### Pitfall 3: Context Length Exceeded

**Error**: "This model's maximum context length is..."

**Fix**: Use model with larger context or enable truncation:
```python
prompt = client.truncate_prompt(prompt, model)
```

### Pitfall 4: Missing Fallback

If primary backend is down and no fallback configured:

```yaml
llm:
  backend: "anthropic"
  # No fallback_backends!  # ❌ System stops if Anthropic is down
```

**Fix**: Always configure fallback:
```yaml
llm:
  backend: "anthropic"
  fallback_backends: ["openai", "ollama"]  # ✅
```

## 📝 Code Comments Philosophy

I followed these commenting rules:

1. **Why, not what**: Code shows *what*, comments explain *why*
2. **Docstrings for public APIs**: All public methods have full docstrings
3. **Type hints everywhere**: Prefer `model: str` over `# model is a string`
4. **No obvious comments**: Never `x = 5  # Set x to 5`

## 🤝 Working with This Code

**Before making changes:**

1. Read `docs/BACKEND_CONFIGURATION.md` (user-facing docs)
2. Read this file (implementation notes)
3. Look at `config.example.yaml` (see how it's used)
4. Run tests: `pytest tests/test_multi_backend.py`

**When adding features:**

1. Update the abstract base class (`llm_client_base.py`) if needed
2. Implement in all backends (or make it optional)
3. Add to factory (`llm_client_factory.py`)
4. Update tests
5. Update docs

**When fixing bugs:**

1. Add a test that reproduces the bug
2. Fix the bug
3. Verify test passes
4. Update relevant docs

## 📞 Questions?

If something is unclear, check:

1. `docs/BACKEND_CONFIGURATION.md` - User guide
2. `config.example.yaml` - Example usage
3. `tests/test_multi_backend.py` - Test examples
4. Source code docstrings

Or ask the team! This is complex stuff.

## 🎓 Learning Resources

If you're new to these patterns:

- **Strategy Pattern**: https://refactoring.guru/design-patterns/strategy
- **Factory Pattern**: https://refactoring.guru/design-patterns/factory-method
- **ABC in Python**: https://docs.python.org/3/library/abc.html

## ✅ Checklist for New Backends

When adding a new backend, ensure:

- [ ] Inherits from `LLMClientBase`
- [ ] Implements all abstract methods
- [ ] Has `backend_type` attribute
- [ ] Registered in `LLMClientFactory.BACKENDS`
- [ ] Added to `create_from_config()`
- [ ] Has unit tests in `test_multi_backend.py`
- [ ] Documented in `BACKEND_CONFIGURATION.md`
- [ ] Has example config in `config.example.yaml`
- [ ] Handles API keys from env vars
- [ ] Implements proper error handling
- [ ] Calculates timeouts correctly
- [ ] Tracks context windows

## 🎉 Final Notes

This was a big refactor, but it maintains **100% backward compatibility**. Old configs still work. The system gracefully falls back to Ollama if the new stuff isn't configured.

The beauty of this design: Users can start simple (all Ollama) and gradually adopt cloud providers as needed. Or go full Anthropic from day one. Or mix and match. **It's flexible**.

Happy coding! 🚀

---

*Written with ❤️ by Claude, for future Claude (and human developers)*
