# Anthropic SDK Migration Summary

## Problem Solved

**Previous Issue:**
- Custom `requests`-based Anthropic client implementation
- 401 authentication errors with message "invalid x-api-key"
- All requests routed to single backend, causing 404 errors when trying to use Ollama models through Anthropic API

**Solution:**
1. ✅ Migrated to **official Anthropic Python SDK** for better reliability
2. ✅ Created **RoutingClient** that auto-detects which backend to use per model
3. ✅ Updated chat_cli.py to use routing instead of single backend

---

## Changes Made

### 1. Migrated to Official Anthropic SDK

**File:** `src/anthropic_client.py`

**Before:**
```python
import requests

response = requests.post(
    messages_url,
    headers=self._get_headers(),
    json=payload,
    timeout=timeout
)
```

**After:**
```python
from anthropic import Anthropic, AuthenticationError, APIError

self.client = Anthropic(api_key=self.api_key)

message = self.client.messages.create(
    model=model,
    messages=messages,
    max_tokens=max_tokens,
    temperature=temperature
)
```

**Benefits:**
- ✓ Better error handling with specific exception types
- ✓ Maintained and tested by Anthropic
- ✓ Automatic retries and edge case handling
- ✓ Type safety

---

### 2. Created Routing Client

**File:** `src/llm_client_factory.py` (added `RoutingClient` class)

**How It Works:**
1. Initializes clients for all enabled backends (Ollama, Anthropic, etc.)
2. When `generate()` is called, checks model metadata to determine backend
3. Routes request to appropriate client automatically

**Example:**
```python
from src.llm_client_factory import LLMClientFactory

# Initialize routing client
client = LLMClientFactory.create_routing_client(config)

# This routes to Anthropic
result = client.generate(
    model="claude-3-haiku-20240307",
    model_key="claude_haiku",  # Metadata says backend="anthropic"
    prompt="Hello"
)

# This routes to Ollama
result = client.generate(
    model="tinyllama",
    model_key="tinyllama",  # Metadata says backend="ollama"
    prompt="Hello"
)
```

**Backend Detection Logic:**
```python
def _get_backend_for_model(self, model: str, model_key: Optional[str] = None):
    # 1. Check model_key metadata for backend field
    if model_key:
        metadata = self.config_manager.get_model_metadata(model_key)
        return metadata.get("backend")

    # 2. Search model registry by name
    for key, config in models.items():
        if config.get("name") == model:
            return config.get("backend", "ollama")

    # 3. Fallback: guess from model name
    if model.startswith("claude"):
        return "anthropic"
    elif model.startswith("gpt"):
        return "openai"
    else:
        return "ollama"
```

---

### 3. Updated Chat CLI

**File:** `chat_cli.py`

**Before:**
```python
backend = self.config.get_primary_llm_backend()
self.client = LLMClientFactory.create_from_config(self.config, backend)
console.print(f"Using {backend} backend for LLM")
```

**After:**
```python
self.client = LLMClientFactory.create_routing_client(self.config)
console.print("Using multi-backend routing (auto-detects backend per model)")
```

---

### 4. Updated Requirements

**File:** `requirements.txt`

Added:
```
anthropic>=0.69.0
```

---

### 5. Updated Documentation

**File:** `SETUP_ANTHROPIC.md`

Added section explaining how routing works:
```
## How Routing Works

The system uses a **Routing Client** that automatically detects which backend to use for each model:

1. When a model is requested, the routing client checks the model's `backend` field in the config
2. Anthropic models (claude-*) → Route to Anthropic API
3. Ollama models (tinyllama, nomic-embed-text) → Route to local Ollama
4. This happens automatically - no manual switching needed!
```

---

## Testing

**File:** `test_anthropic_sdk.py`

Tests both:
1. Anthropic model routing (should use Anthropic API)
2. Ollama model routing (should use local Ollama)

**Run test:**
```powershell
python code_evolver/test_anthropic_sdk.py
```

**Expected output:**
```
[OK] API key found
[OK] Config loaded successfully
[OK] Routing client initialized
  Available backends: ['ollama', 'anthropic']
[OK] Anthropic generation successful!
Response: Hello from Anthropic!
[OK] Ollama generation successful!
Response: Hello from Ollama!
[SUCCESS] ALL TESTS PASSED - Routing client is working correctly!
```

---

## How to Use

### Setup (unchanged)
```powershell
# Set API key
$env:ANTHROPIC_API_KEY="sk-ant-api03-YOUR-KEY-HERE"

# Verify
echo $env:ANTHROPIC_API_KEY

# Start Ollama (required for embeddings)
ollama serve
```

### Run (unchanged)
```powershell
python code_evolver/chat_cli.py --config code_evolver/config.anthropic.yaml
```

### What Changed
- Previously: Single backend client, all requests went to one backend
- Now: Routing client that automatically uses the correct backend per model
- Result: Anthropic models → Anthropic API, Ollama models → local Ollama

---

## Benefits

### 1. Better Reliability
- Official SDK is more robust than custom implementation
- Proper error handling with specific exception types
- Maintained by Anthropic

### 2. Automatic Routing
- No manual backend switching required
- Models automatically routed to correct backend
- Supports multiple backends in single config

### 3. Cost Optimization
- Expensive models (claude-opus, claude-sonnet) → Anthropic (paid)
- Cheap models (tinyllama) → Ollama (free)
- Embeddings → Ollama (free)

### 4. Flexibility
- Easy to add new backends (OpenAI, Azure, etc.)
- Mix-and-match models from different providers
- Override routing with explicit backend specification

---

## Architecture

```
User Request
    ↓
[RoutingClient]
    ↓
Check model_key metadata → backend="anthropic" or "ollama"
    ↓
    ├─→ [AnthropicClient] → Official Anthropic SDK → api.anthropic.com
    │       ↓
    │   claude-opus, claude-sonnet, claude-haiku
    │
    └─→ [OllamaClient] → Local Ollama → localhost:11434
            ↓
        tinyllama, nomic-embed-text
```

---

## Migration Checklist

- [x] Install official Anthropic SDK (`anthropic>=0.69.0`)
- [x] Migrate AnthropicClient to use SDK
- [x] Create RoutingClient class
- [x] Update chat_cli.py to use routing
- [x] Update requirements.txt
- [x] Update documentation (SETUP_ANTHROPIC.md)
- [x] Create test script (test_anthropic_sdk.py)
- [ ] Test with real API key (user needs to verify)
- [ ] Run full workflow test (user needs to verify)

---

## Troubleshooting

### Still getting 401 errors?

1. **Check API key is set:**
   ```powershell
   echo $env:ANTHROPIC_API_KEY
   ```

2. **Verify it's the KEY ONLY (no prefix):**
   ```powershell
   # ✅ Correct
   $env:ANTHROPIC_API_KEY="sk-ant-api03-..."

   # ❌ Wrong
   $env:ANTHROPIC_API_KEY="ANTHROPIC_API_KEY=sk-ant-api03-..."
   ```

3. **Run test script:**
   ```powershell
   python code_evolver/test_anthropic_sdk.py
   ```

### Getting 404 errors for Ollama models?

1. **Check Ollama is running:**
   ```powershell
   ollama list
   ```

2. **Start Ollama if needed:**
   ```powershell
   ollama serve
   ```

3. **Pull required models:**
   ```powershell
   ollama pull tinyllama
   ollama pull nomic-embed-text
   ```

### Routing to wrong backend?

1. **Check model metadata:**
   ```python
   from src.config_manager import ConfigManager
   config = ConfigManager("config.anthropic.yaml")
   metadata = config.get_model_metadata("claude_haiku")
   print(metadata.get("backend"))  # Should print "anthropic"
   ```

2. **Check enabled backends:**
   ```python
   backends = config.get("llm.backends", {})
   for name, cfg in backends.items():
       print(f"{name}: enabled={cfg.get('enabled')}")
   ```

---

## Next Steps

1. **Test the changes:**
   ```powershell
   python code_evolver/test_anthropic_sdk.py
   ```

2. **Run the chat CLI:**
   ```powershell
   python code_evolver/chat_cli.py --config code_evolver/config.anthropic.yaml
   ```

3. **Try a simple request:**
   ```
   DiSE> write a haiku about coding
   ```

4. **Verify routing is working:**
   - Check logs for "Routing model 'X' to Y backend"
   - Anthropic models should go to Anthropic
   - Ollama models should go to Ollama

---

**Status:** ✅ Migration complete, ready for testing!
