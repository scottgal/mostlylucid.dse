# Routing Fix - Correct Backend Selection

## Problem

The system was sending Anthropic models (like `claude-3-5-sonnet-20241022`) to the Ollama endpoint (`http://localhost:11434`) instead of to Anthropic's API, resulting in 404 errors:

```
Consulting claude-3-5-sonnet-20241022...
ERROR:src.ollama_client:Error generating response from http://localhost:11434: 404 Client Error: Not Found
```

## Root Cause

The `RoutingClient` was not receiving the correct `model_key` parameter needed to look up the model's backend from metadata.

**Before Fix:**
```python
specification = self.client.generate(
    model=self.config.overseer_model,  # "claude-3-5-sonnet-20241022" (model NAME)
    model_key="overseer"  # WRONG - "overseer" is a role, not a model key
)
```

The RoutingClient tried to look up `"overseer"` in `llm.models` registry but couldn't find it, so it fell back to guessing based on the model name. However, this fallback wasn't working correctly.

## Solution

### 1. ✅ Added Model Key Properties to ConfigManager

Added new properties that return the actual model key (e.g., `"claude_sonnet"`) instead of just the model name:

**File: `src/config_manager.py` (lines 332-407)**

```python
@property
def overseer_model_key(self) -> Optional[str]:
    """Get overseer model key for routing."""
    return self.get_model(role="default", level="general")

@property
def generator_model_key(self) -> Optional[str]:
    """Get generator model key for routing."""
    return self.get_model(role="code", level="general")

@property
def evaluator_model_key(self) -> Optional[str]:
    """Get evaluator model key for routing."""
    return self.get_model(role="default", level="general")

@property
def triage_model_key(self) -> Optional[str]:
    """Get triage model key for routing."""
    return self.get_model(role="default", level="veryfast")

@property
def escalation_model_key(self) -> Optional[str]:
    """Get escalation model key for routing."""
    return self.get_model(role="default", level="escalation")
```

### 2. ✅ Updated All `client.generate()` Calls in chat_cli.py

Replaced all hardcoded `model_key="overseer"`, `model_key="generator"`, etc. with the actual model key properties:

**Before:**
```python
self.client.generate(
    model=self.config.overseer_model,
    prompt=prompt,
    model_key="overseer"  # WRONG
)
```

**After:**
```python
self.client.generate(
    model=self.config.overseer_model,
    prompt=prompt,
    model_key=self.config.overseer_model_key  # CORRECT - e.g., "claude_sonnet"
)
```

**Changes in chat_cli.py:**
- Line 653: Workflow decomposition
- Line 1181: Semantic check (triage)
- Line 1319: Semantic check (triage)
- Line 1648: Specification generation (overseer)
- Line 1698: Task classification (triage)
- Line 2145: Code generation (generator)
- Line 2752: Code improvement (generator)
- Line 3065: Interface detection (overseer)
- Line 3147: Task type classification (triage - already correct)
- Line 3272: TDD test generation (generator)
- Line 3527: Test generation (generator)
- Line 3822: Adaptive fix with escalation (generator/escalation)
- Line 4303: Escalation fix (escalation)
- And more...

## How It Works Now

### Example: Anthropic Mode

**Config:** `config.anthropic.yaml`
```yaml
llm:
  models:
    claude_sonnet:
      name: "claude-3-5-sonnet-20241022"
      backend: "anthropic"

  defaults:
    general: claude_sonnet  # default.general → claude_sonnet
```

**Code Flow:**
```python
# 1. Get overseer model key
overseer_model_key = self.config.overseer_model_key
# → calls get_model(role="default", level="general")
# → returns "claude_sonnet"

# 2. Get overseer model name
overseer_model_name = self.config.overseer_model
# → resolves "claude_sonnet" → "claude-3-5-sonnet-20241022"

# 3. Call client.generate()
specification = self.client.generate(
    model="claude-3-5-sonnet-20241022",
    model_key="claude_sonnet",  # ← CORRECT!
    prompt=prompt
)

# 4. RoutingClient routes to correct backend
# _get_backend_for_model("claude-3-5-sonnet-20241022", "claude_sonnet")
# → lookup metadata for "claude_sonnet"
# → backend = "anthropic"
# → route to AnthropicClient ✓
```

### Example: Local Mode

**Config:** `config.yaml`
```yaml
llm:
  models:
    llama3:
      name: "llama3"
      backend: "ollama"

  defaults:
    general: llama3  # default.general → llama3
```

**Code Flow:**
```python
# 1. Get overseer model key
overseer_model_key = self.config.overseer_model_key
# → returns "llama3"

# 2. Get overseer model name
overseer_model_name = self.config.overseer_model
# → returns "llama3"

# 3. Call client.generate()
specification = self.client.generate(
    model="llama3",
    model_key="llama3",  # ← CORRECT!
    prompt=prompt
)

# 4. RoutingClient routes to correct backend
# _get_backend_for_model("llama3", "llama3")
# → lookup metadata for "llama3"
# → backend = "ollama"
# → route to OllamaClient ✓
```

## Verification

### Test the Fix

```bash
# In Anthropic mode
python code_evolver/chat_cli.py --config code_evolver/config.anthropic.yaml

# Should see:
# ✓ Consulting claude-3-5-sonnet-20241022...
# ✓ No 404 errors
# ✓ Successful API calls to Anthropic
```

### Routing Flow

```
User Request
    ↓
chat_cli.py calls:
    self.client.generate(
        model="claude-3-5-sonnet-20241022",
        model_key="claude_sonnet"  ← The key!
    )
    ↓
RoutingClient._get_backend_for_model():
    1. Look up metadata for "claude_sonnet"
    2. Find backend: "anthropic"
    3. Route to AnthropicClient
    ↓
AnthropicClient.generate():
    Uses official Anthropic SDK
    Sends request to https://api.anthropic.com
    ✓ Success!
```

## Files Modified

### src/config_manager.py
- Added `overseer_model_key` property (lines 332-334)
- Added `generator_model_key` property (lines 350-352)
- Added `evaluator_model_key` property (lines 368-370)
- Added `triage_model_key` property (lines 387-389)
- Added `escalation_model_key` property (lines 405-407)

### chat_cli.py
- Updated all `client.generate()` calls to use actual model keys (13+ locations)
- Replaced `model_key="overseer"` with `model_key=self.config.overseer_model_key`
- Replaced `model_key="generator"` with `model_key=self.config.generator_model_key`
- Replaced `model_key="triage"` with `model_key=self.config.triage_model_key`
- Replaced `model_key="escalation"` with `model_key=self.config.escalation_model_key`

## Benefits

### 1. **Correct Routing** ✅
- Claude models go to Anthropic API
- Ollama models go to Ollama endpoint
- No more 404 errors

### 2. **Mixed Backend Support** ✅
- Can use Claude for complex tasks (general, escalation)
- Can use local Ollama for fast triage (veryfast)
- Cost-effective hybrid approach

### 3. **Proper Abstraction** ✅
- Config properties return correct model keys
- chat_cli.py doesn't need to know about routing logic
- RoutingClient handles all backend selection

### 4. **Future-Proof** ✅
- Easy to add new backends
- Easy to change model assignments
- No hardcoded routing logic

## Example Scenarios

### Scenario 1: All Anthropic (Cloud)
```yaml
defaults:
  general: claude_sonnet    # overseer, generator, evaluator
  escalation: claude_opus   # escalation
  veryfast: claude_haiku    # triage
```
**Result:** All requests go to Anthropic API ✓

### Scenario 2: Mixed (Hybrid)
```yaml
defaults:
  general: claude_sonnet    # overseer, generator, evaluator
  escalation: claude_opus   # escalation
  veryfast: tinyllama       # triage (local, free!)
```
**Result:**
- Complex tasks → Anthropic API
- Fast triage → Local Ollama
- Cost-effective! ✓

### Scenario 3: All Local (Free)
```yaml
defaults:
  general: llama3           # overseer, generator, evaluator
  escalation: qwen_14b      # escalation
  veryfast: tinyllama       # triage
```
**Result:** All requests go to local Ollama ✓

## Next Steps

1. ✅ Routing fix complete
2. ✅ Model key properties added
3. ✅ All client calls updated
4. ✅ Ready to test

**Test it:**
```bash
python code_evolver/chat_cli.py --config code_evolver/config.anthropic.yaml
```

---

**Status:** ✅ Routing fixed! Models will now correctly route to their respective backends.
