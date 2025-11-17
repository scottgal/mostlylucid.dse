# Backend Architecture - Quick Reference

## Current State
- **Active Backend**: Ollama only (tight coupling)
- **Client Class**: `OllamaClient` (419 lines)
- **Configuration**: `config.yaml` (Ollama-specific)
- **LLM Integration Points**: 7+ locations throughout codebase

## Key Files to Understand

### 1. **Configuration** 
- `config.yaml` - Backend settings and model assignments
- `src/config_manager.py` - Configuration loading and access (494 lines)

### 2. **Backend Implementation**
- `src/ollama_client.py` - Only current backend (419 lines)
- `src/overseer_llm.py` - Uses OllamaClient (425 lines)
- `src/evaluator_llm.py` - Uses OllamaClient (367 lines)

### 3. **Tool System**
- `src/tools_manager.py` - Invokes LLM tools (500+ lines)
- Supports Ollama through `invoke_llm_tool()` method

### 4. **Orchestration**
- `src/hierarchical_evolver.py` - Main system, hardcodes OllamaClient
- `orchestrator.py` - CLI entry point
- `chat_cli.py` - Chat interface

## Critical Hardcoded Locations

These 4 locations instantiate OllamaClient directly:
1. **Line 220** in `hierarchical_evolver.py`: `self.client = OllamaClient()`
2. **Line 36** in `orchestrator.py`: `self.client = OllamaClient()`
3. **Tools manager** - passed as dependency but assumes Ollama type
4. **Various tests** - instantiate directly

## The Three-Layer Architecture

```
Layer 1: Entry Points (chat_cli.py, orchestrator.py)
    ↓
Layer 2: Orchestration (HierarchicalEvolver, ToolsManager)
    ↓
Layer 3: Backend (OllamaClient) ← SINGLE PROVIDER
    ↓
LLM Provider (Ollama HTTP API)
```

## What Needs to Happen

### Phase 1: Create Abstraction (25-31 hours)

1. **New Base Class** `src/llm_client.py`
   - Define `LLMClient` abstract base class
   - Methods: `check_connection()`, `list_models()`, `generate()`, etc.

2. **New Clients** 
   - `src/anthropic_client.py` - Claude API integration (4 hours)
   - `src/azure_client.py` - Azure OpenAI integration (4 hours)
   - `src/lm_studio_client.py` - LM Studio (OpenAI-compatible) (3 hours)

3. **Factory Pattern** `src/client_factory.py`
   - `LLMClientFactory.create_client(config_manager)` 
   - Returns appropriate client based on config

4. **Configuration Support**
   - Update `config.yaml` with `backend:` section
   - Update `ConfigManager` for multi-backend support
   - Handle environment variables

5. **High-Level Updates**
   - Replace hardcoded `OllamaClient()` with factory calls
   - Update `HierarchicalEvolver`, `orchestrator.py`, `chat_cli.py`
   - Update type hints to use `LLMClient` base class

### Phase 2: Implementation Details

```python
# BEFORE (current):
class HierarchicalEvolver:
    def __init__(self):
        self.client = OllamaClient()  # Hardcoded!

# AFTER (proposed):
class HierarchicalEvolver:
    def __init__(self, client: LLMClient):
        self.client = client

# Usage:
config = ConfigManager("config.yaml")
client = LLMClientFactory.create_client(config)
evolver = HierarchicalEvolver(client)
```

## Configuration Changes Needed

### Add to `config.yaml`

```yaml
# Choose backend
backend:
  type: "anthropic"  # or "ollama", "azure", "lm_studio"

# New backend configs (alongside existing ollama: section)
anthropic:
  api_key: "${ANTHROPIC_API_KEY}"
  models:
    overseer:
      model: "claude-3-5-sonnet-20241022"
    generator:
      model: "claude-3-5-sonnet-20241022"
    # ... more models ...

azure:
  endpoint: "${AZURE_ENDPOINT}"
  api_key: "${AZURE_API_KEY}"
  api_version: "2024-02-15-preview"
  # ... models ...

lm_studio:
  base_url: "http://localhost:1234"
  # ... models ...
```

## Implementation Effort Breakdown

| Component | Hours | Difficulty |
|-----------|-------|-----------|
| Base interface | 2-3 | Easy |
| Anthropic client | 4 | Medium |
| Azure client | 4 | Medium |
| LM Studio client | 3 | Easy |
| Factory pattern | 1-2 | Easy |
| Config updates | 2-3 | Medium |
| Tools manager | 2-3 | Medium |
| High-level refactor | 2-3 | Easy |
| Testing | 3-4 | Medium |
| **TOTAL** | **25-31** | **Medium** |

## Key Design Decisions

1. **Use Abstract Base Class** - More explicit than Protocol
2. **Factory Pattern** - Type-safe, testable client creation
3. **Backward Compatible** - Ollama as default, opt-in for new backends
4. **Environment Variables** - API keys from env, not config file
5. **Same method signatures** - All clients implement same `generate()` interface

## Testing Approach

Mock API responses - don't need real credentials to test:
```python
with patch('requests.post') as mock_post:
    mock_post.return_value.json.return_value = {"content": [{"text": "..."}]}
    client = AnthropicClient(api_key="test")
    result = client.generate(model="claude", prompt="test")
```

## Success Criteria

- Can switch backends via config (no code changes)
- All three new providers (Anthropic, Azure, LM Studio) working
- Backward compatible with existing Ollama setup
- Type-safe with proper inheritance
- Tests pass for all backends
- Documentation updated with examples

## File Locations for Reference

**Absolute paths** (use these for absolute imports):
- `/home/user/mostlylucid.dse/code_evolver/config.yaml`
- `/home/user/mostlylucid.dse/code_evolver/src/ollama_client.py`
- `/home/user/mostlylucid.dse/code_evolver/src/config_manager.py`
- `/home/user/mostlylucid.dse/code_evolver/src/tools_manager.py`
- `/home/user/mostlylucid.dse/code_evolver/src/hierarchical_evolver.py`
- `/home/user/mostlylucid.dse/code_evolver/orchestrator.py`

---

For comprehensive details, see: **BACKEND_ARCHITECTURE.md** (15 sections, 23KB)
