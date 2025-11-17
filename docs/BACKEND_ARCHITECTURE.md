# Code Evolver Backend Architecture Analysis

## Executive Summary
The codebase currently uses **Ollama** as its exclusive LLM backend provider. To add support for OpenAPI, Anthropic, Azure AI, and LM Studio, you'll need to implement a backend abstraction layer that maintains compatibility with existing code while supporting multiple providers.

---

## 1. CURRENT BACKEND IMPLEMENTATION ARCHITECTURE

### 1.1 Current Design Pattern
The system is tightly coupled to **Ollama** through the `OllamaClient` class:
- **File**: `/home/user/mostlylucid.dse/code_evolver/src/ollama_client.py` (419 lines)
- **Pattern**: Direct HTTP requests to Ollama API using `requests` library
- **Models supported**: Any Ollama-compatible model (codellama, llama3, mistral, etc.)

### 1.2 OllamaClient Architecture

```python
class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", config_manager=None)
    
    # Core methods:
    def check_connection(endpoint: Optional[str]) -> bool
    def list_models(endpoint: Optional[str]) -> list
    def generate(model: str, prompt: str, system: Optional[str], 
                 temperature: float, stream: bool, endpoint: Optional[str],
                 model_key: Optional[str], speed_tier: Optional[str]) -> str
    def generate_code(prompt: str, constraints: Optional[str]) -> str
    def evaluate(code_summary: str, metrics: Dict) -> str
    def triage(metrics: Dict, targets: Dict) -> str
```

### 1.3 Key Features Currently Implemented
1. **Round-robin load balancing** - Multiple endpoints per model for distributed inference
2. **Dynamic timeout calculation** - Based on model size and speed tier
3. **Context window management** - Prompts truncated to fit model limits
4. **Per-model endpoint routing** - Different endpoints for different model roles
5. **Temperature control** - Configurable sampling temperature

---

## 2. CONFIGURATION STRUCTURE

### 2.1 Configuration File Location
**File**: `/home/user/mostlylucid.dse/code_evolver/config.yaml` (900+ lines)

### 2.2 Backend Configuration Format (Currently Ollama-only)

```yaml
ollama:
  # Default base URL for all models
  base_url: "http://localhost:11434"

  # Model assignments with per-model endpoints
  models:
    overseer:
      model: "llama3"
      endpoint: null  # Uses base_url if null
    
    generator:
      model: "codellama"
      endpoint: null  # Uses base_url

    evaluator:
      writing:
        model: "phi3:3.8b"
        endpoint: null
      code:
        model: "llama3"
        endpoint: null
      default:
        model: "llama3"
        endpoint: null
    
    # ... more models ...

  # Context window sizes for prompt truncation
  context_windows:
    llama3: 8192
    codellama: 16384
    qwen2.5-coder:14b: 32768
    # ... more models ...
```

### 2.3 Tool Configuration (Also Ollama-based)

```yaml
tools:
  fast_code_generator:
    name: "Fast Code Generator"
    type: "llm"
    llm:
      model: "gemma3:4b"
      endpoint: null
      system_prompt: "..."
      prompt_template: "..."
```

### 2.4 ConfigManager Class
**File**: `/home/user/mostlylucid.dse/code_evolver/src/config_manager.py` (494 lines)

Key methods for backend configuration:
- `get(key_path: str)` - Dot notation access (e.g., "ollama.models.overseer")
- `get_model_endpoint(model_key: str)` - Returns endpoint for specific model role
- `get_model_endpoints(model_key: str)` - Returns list of endpoints (for round-robin)
- `get_context_window(model_name: str)` - Returns context window size

---

## 3. WHERE API CALLS TO LLMs ARE MADE

### 3.1 Primary Call Sites

| Location | File | Method | Purpose |
|----------|------|--------|---------|
| **OllamaClient.generate()** | ollama_client.py:207 | POST to `/api/generate` | Core text generation |
| **OllamaClient.generate_code()** | ollama_client.py:307 | Uses generate() | Code generation wrapper |
| **OllamaClient.evaluate()** | ollama_client.py:337 | Uses generate() | Code evaluation |
| **OllamaClient.triage()** | ollama_client.py:390 | Uses generate() | Quick pass/fail decisions |
| **OverseerLlm.plan_strategy()** | overseer_llm.py | Uses client.generate() | Strategic planning |
| **EvaluatorLlm.evaluate()** | evaluator_llm.py | Uses client.generate() | Fitness evaluation |
| **ToolsManager.invoke_llm_tool()** | tools_manager.py:444 | Uses ollama_client.generate() | Tool invocation |

### 3.2 Execution Flow Diagram

```
User Request
    ↓
chat_cli.py (or orchestrator.py)
    ↓
HierarchicalEvolver / ToolsManager
    ↓
OverseerLlm / EvaluatorLlm / ToolsManager
    ↓
OllamaClient.generate() ← BOTTLENECK: Only Ollama supported here
    ↓
HTTP POST to Ollama API (/api/generate)
    ↓
LLM Response
```

---

## 4. EXISTING ABSTRACTION LAYERS

### 4.1 Tool Type System
**File**: `/home/user/mostlylucid.dse/code_evolver/src/tools_manager.py` (Lines 18-29)

```python
class ToolType(Enum):
    FUNCTION = "function"
    LLM = "llm"                    # <-- For LLM-based tools
    WORKFLOW = "workflow"
    OPENAPI = "openapi"            # <-- Already has abstraction!
    EXECUTABLE = "executable"
    CUSTOM = "custom"
    # ... more types ...
```

### 4.2 Existing OpenAPI Tool Abstraction
**File**: `/home/user/mostlylucid.dse/code_evolver/src/openapi_tool.py` (11KB)

This shows the pattern for plugin backends:
```python
class OpenAPITool:
    def __init__(self, tool_id: str, name: str, spec_path: Optional[str] = None,
                 spec_url: Optional[str] = None, spec_dict: Optional[Dict] = None,
                 base_url_override: Optional[str] = None,
                 auth_config: Optional[Dict] = None)
    
    def invoke(self, operation_id: str, parameters: Optional[Dict],
               body: Optional[Dict]) -> Dict[str, Any]
```

### 4.3 Tool Invocation Pattern
**File**: `/home/user/mostlylucid.dse/code_evolver/src/tools_manager.py:444-549`

```python
def invoke_llm_tool(self, tool_id: str, prompt: str, system_prompt=None,
                    temperature=0.7, **template_vars) -> str:
    # 1. Get tool metadata from config
    tool = self.get_tool(tool_id)
    llm_config = tool.implementation or tool.metadata
    model = llm_config.get("llm_model") or llm_config.get("model")
    endpoint = llm_config.get("llm_endpoint")
    
    # 2. Get model and endpoint info
    # 3. Format prompt with template
    
    # 4. CURRENT: Call only OllamaClient
    response = self.ollama_client.generate(
        model=model, prompt=prompt, system=system_prompt,
        temperature=temperature, endpoint=endpoint
    )
    
    # 5. Store in RAG memory for learning
    self.rag_memory.store_artifact(...)
    
    return response
```

---

## 5. MAIN ENTRY POINTS AND WORKFLOW EXECUTION

### 5.1 Primary Entry Points

| Entry Point | File | Class | Purpose |
|-------------|------|-------|---------|
| **orchestrator.py** | orchestrator.py:21 | `Orchestrator` | Main CLI orchestrator |
| **chat_cli.py** | chat_cli.py | Chat interface | Interactive chat mode |
| **HierarchicalEvolver** | hierarchical_evolver.py:220 | Creates OllamaClient internally | Main evolution system |

### 5.2 HierarchicalEvolver Initialization (Lines 220-222)
```python
class HierarchicalEvolver:
    def __init__(self, rag_memory=None, config_manager=None,
                 overseer=None, evaluator=None):
        # Creates OllamaClient directly (hardcoded!)
        self.client = OllamaClient()
        
        # Uses it to create LLM agents
        self.overseer = overseer or OverseerLlm(self.client, rag_memory)
        self.evaluator = evaluator or EvaluatorLlm(self.client)
```

### 5.3 ToolsManager Initialization
```python
class ToolsManager:
    def __init__(self, tools_path: str = "./tools",
                 config_manager: Optional[Any] = None,
                 ollama_client: Optional[Any] = None,  # <-- Accepts client
                 rag_memory: Optional[Any] = None):
        
        self.ollama_client = ollama_client  # Stored for invoke_llm_tool()
        # ...
```

---

## 6. ARCHITECTURE PROBLEMS AND REQUIRED CHANGES

### 6.1 Current Limitations

| Issue | Impact | Severity |
|-------|--------|----------|
| **Tight coupling to Ollama** | Can't use other providers without major refactoring | CRITICAL |
| **OllamaClient hardcoded in multiple places** | 4+ locations instantiate OllamaClient directly | CRITICAL |
| **No provider abstraction** | No base class or interface for LLM backends | CRITICAL |
| **Config tied to Ollama structure** | Adding new backends requires config changes | HIGH |
| **Tool system assumes Ollama** | invoke_llm_tool() only works with OllamaClient | HIGH |
| **No authentication pattern** | Ollama uses local URLs, doesn't handle API keys | MEDIUM |

### 6.2 Places That Need Modification

```
Files requiring changes for multi-backend support:
├── src/ollama_client.py              # Split into base + Ollama impl
├── src/config_manager.py              # Support multiple backend configs
├── src/tools_manager.py               # Support multiple client types
├── src/hierarchical_evolver.py        # Accept client factory/type
├── src/overseer_llm.py                # Accept any client type
├── src/evaluator_llm.py               # Accept any client type
├── src/rag_memory.py                  # If using embeddings from different backends
├── src/__init__.py                    # Export new clients
├── config.yaml                        # Define new backend configurations
└── orchestrator.py / chat_cli.py      # Initialize correct client based on config
```

---

## 7. RECOMMENDED BACKEND ABSTRACTION DESIGN

### 7.1 Base Client Interface (NEW)

Create file: `/home/user/mostlylucid.dse/code_evolver/src/llm_client.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class LLMClient(ABC):
    """Base class for all LLM provider clients."""
    
    @abstractmethod
    def check_connection(self, endpoint: Optional[str] = None) -> bool:
        """Check if backend is accessible."""
        pass
    
    @abstractmethod
    def list_models(self, endpoint: Optional[str] = None) -> list:
        """List available models."""
        pass
    
    @abstractmethod
    def generate(self, model: str, prompt: str, system: Optional[str],
                 temperature: float, stream: bool,
                 endpoint: Optional[str], model_key: Optional[str],
                 speed_tier: Optional[str]) -> str:
        """Generate text from model."""
        pass
    
    @abstractmethod
    def get_context_window(self, model: str) -> int:
        """Get context window size for model."""
        pass
    
    @abstractmethod
    def calculate_timeout(self, model: str, model_key: Optional[str],
                         speed_tier: Optional[str]) -> int:
        """Calculate timeout for model."""
        pass
```

### 7.2 Refactored OllamaClient

```python
class OllamaClient(LLMClient):
    """Ollama-specific implementation (keep existing code)."""
    def __init__(self, base_url: str = "http://localhost:11434",
                 config_manager: Optional['ConfigManager'] = None):
        # Keep all existing implementation
        # ...
```

### 7.3 New Backend Clients (Examples)

```python
# src/anthropic_client.py
class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, config_manager: Optional['ConfigManager']):
        self.api_key = api_key
        # Uses Claude API instead of local endpoints
        
# src/azure_ai_client.py
class AzureAIClient(LLMClient):
    def __init__(self, endpoint: str, api_key: str,
                 config_manager: Optional['ConfigManager']):
        self.endpoint = endpoint
        self.api_key = api_key
        # Uses Azure OpenAI endpoint
        
# src/lm_studio_client.py
class LMStudioClient(LLMClient):
    def __init__(self, base_url: str = "http://localhost:1234",
                 config_manager: Optional['ConfigManager']):
        self.base_url = base_url
        # LM Studio has OpenAI-compatible API
```

### 7.4 Factory Pattern for Client Creation

Create: `/home/user/mostlylucid.dse/code_evolver/src/client_factory.py`

```python
class LLMClientFactory:
    @staticmethod
    def create_client(config_manager: 'ConfigManager',
                      backend_name: str = None) -> LLMClient:
        """Create appropriate client based on config."""
        
        backend = backend_name or config_manager.get("backend.type", "ollama")
        
        if backend == "ollama":
            return OllamaClient(config_manager=config_manager)
        elif backend == "anthropic":
            api_key = config_manager.get("anthropic.api_key")
            return AnthropicClient(api_key, config_manager)
        elif backend == "azure":
            endpoint = config_manager.get("azure.endpoint")
            api_key = config_manager.get("azure.api_key")
            return AzureAIClient(endpoint, api_key, config_manager)
        elif backend == "lm_studio":
            base_url = config_manager.get("lm_studio.base_url", "http://localhost:1234")
            return LMStudioClient(base_url, config_manager)
        else:
            raise ValueError(f"Unknown backend: {backend}")
```

---

## 8. CONFIGURATION PATTERNS FOR NEW BACKENDS

### 8.1 Multi-Backend Configuration Format

```yaml
# Choose active backend
backend:
  type: "anthropic"  # "ollama" | "anthropic" | "azure" | "lm_studio"

# Ollama (existing)
ollama:
  base_url: "http://localhost:11434"
  models:
    # ... existing config ...

# Anthropic Claude API (new)
anthropic:
  api_key: "${ANTHROPIC_API_KEY}"  # Environment variable
  models:
    overseer:
      model: "claude-3-5-sonnet-20241022"
    generator:
      model: "claude-3-5-sonnet-20241022"
    evaluator:
      writing:
        model: "claude-3-5-sonnet-20241022"
      code:
        model: "claude-3-5-sonnet-20241022"
  # Model-specific settings
  context_windows:
    claude-3-5-sonnet-20241022: 200000

# Azure OpenAI (new)
azure:
  endpoint: "${AZURE_ENDPOINT}"
  api_key: "${AZURE_API_KEY}"
  api_version: "2024-02-15-preview"
  models:
    overseer:
      model: "gpt-4-turbo"
      deployment_name: "gpt4-deployment"
    # ... more models ...

# LM Studio (new - OpenAI-compatible)
lm_studio:
  base_url: "http://localhost:1234"
  models:
    generator:
      model: "local-model"
    # ... more models ...
```

### 8.2 Environment Variable Pattern
```bash
# Support backend-specific environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export AZURE_ENDPOINT="https://example.openai.azure.com/"
export AZURE_API_KEY="..."
```

---

## 9. PLACES REQUIRING IMPLEMENTATION CHANGES

### 9.1 Critical Files for Backend Support

#### 1. **Create Base Interface** (NEW)
- File: `src/llm_client.py`
- Purpose: Define `LLMClient` abstract base class
- Effort: 2-3 hours

#### 2. **Refactor OllamaClient**
- File: `src/ollama_client.py`
- Change: Make it inherit from `LLMClient`
- Keep: All existing implementation
- Effort: 1-2 hours

#### 3. **Implement New Clients**
- Files: `src/anthropic_client.py`, `src/azure_client.py`, `src/lm_studio_client.py`
- Purpose: Provider-specific implementations
- Each file: ~200-300 lines
- Effort: 3-4 hours each (12-16 hours total)

#### 4. **Create Factory Pattern**
- File: `src/client_factory.py` (NEW)
- Purpose: Create clients based on config
- Effort: 1-2 hours

#### 5. **Update ConfigManager**
- File: `src/config_manager.py`
- Changes:
  - Add `get_active_backend()` method
  - Support multiple backend configs
  - Handle environment variables
- Effort: 2-3 hours

#### 6. **Update ToolsManager**
- File: `src/tools_manager.py`
- Changes:
  - Accept generic `LLMClient` type instead of `OllamaClient`
  - Update type hints
  - Handle different authentication per backend
- Effort: 2-3 hours

#### 7. **Update HierarchicalEvolver**
- File: `src/hierarchical_evolver.py`
- Changes:
  - Use client factory instead of hardcoding OllamaClient
  - Pass client type to OverseerLlm and EvaluatorLlm
- Effort: 1-2 hours

#### 8. **Update Orchestrator and CLI**
- Files: `orchestrator.py`, `chat_cli.py`
- Changes:
  - Initialize client using factory
  - Pass client to HierarchicalEvolver
- Effort: 1-2 hours

#### 9. **Update __init__.py**
- File: `src/__init__.py`
- Changes:
  - Export new client classes and factory
  - Update imports
- Effort: 30 minutes

#### 10. **Update Configuration**
- File: `config.yaml`
- Changes:
  - Add `backend` section
  - Add per-backend configuration sections
  - Keep backward compatibility with existing Ollama config
- Effort: 1 hour

---

## 10. IMPLEMENTATION PATTERNS TO FOLLOW

### 10.1 Error Handling Pattern
```python
# Current Ollama pattern to replicate:
try:
    response = requests.post(generate_url, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    result = data.get("response", "")
except requests.exceptions.Timeout:
    logger.error(f"Request timed out for {endpoint}")
    return ""
except requests.exceptions.RequestException as e:
    logger.error(f"Error: {e}")
    return ""
```

### 10.2 Configuration Loading Pattern
```python
# In each new client's __init__:
if not config_manager:
    logger.warning("ConfigManager not provided, using defaults")
    
model_name = config_manager.get(f"{provider}.models.overseer.model")
api_key = config_manager.get(f"{provider}.api_key") or os.getenv("API_KEY")
```

### 10.3 Model Endpoint Resolution Pattern
```python
# Each client should support:
# 1. Explicit endpoint parameter
# 2. Config-based endpoint per model role
# 3. Default endpoint (base_url)

def _get_endpoint_for_model(self, model_key: str):
    endpoints = self.config_manager.get_model_endpoints(model_key)
    return endpoints[0] if endpoints else self.base_url
```

### 10.4 Timeout Calculation Pattern
```python
# Implement for each new backend:
def calculate_timeout(self, model: str, model_key=None, speed_tier=None):
    # Provider-specific timeout defaults
    PROVIDER_TIMEOUTS = {
        "claude-3-5-sonnet": 120,
        # ...
    }
    
    if model in PROVIDER_TIMEOUTS:
        return PROVIDER_TIMEOUTS[model]
    # ... fallback to tier or defaults ...
```

### 10.5 Logging Pattern
```python
# Consistent with Ollama:
logger.info(f"Generating with model '{model}' at {endpoint}...")
logger.debug(f"Request payload: {payload}")
logger.info(f"✓ Generated {len(result)} characters")
logger.error(f"✗ Error: {e}")
```

---

## 11. TESTING STRATEGY

### 11.1 Test Backend Switching
```python
# test_backend_switching.py
def test_can_switch_between_backends():
    # Load config
    config = ConfigManager("config.yaml")
    
    # Test Ollama
    config.set("backend.type", "ollama")
    client = LLMClientFactory.create_client(config)
    assert isinstance(client, OllamaClient)
    
    # Test Anthropic
    config.set("backend.type", "anthropic")
    client = LLMClientFactory.create_client(config)
    assert isinstance(client, AnthropicClient)
```

### 11.2 Mock Testing Pattern
```python
# Don't require actual API credentials for testing
from unittest.mock import Mock, patch

def test_anthropic_client_generation():
    mock_response = Mock()
    mock_response.json.return_value = {
        "content": [{"text": "Generated text"}]
    }
    
    with patch('requests.post', return_value=mock_response):
        client = AnthropicClient(api_key="test-key")
        result = client.generate(model="claude", prompt="test")
        assert result == "Generated text"
```

---

## 12. MIGRATION PATH (Backward Compatibility)

### Phase 1: Add Base Interface (No Breaking Changes)
1. Create `LLMClient` base class
2. Make `OllamaClient` inherit from it
3. All existing code continues to work

### Phase 2: Add New Backends
1. Create new client implementations
2. Keep Ollama as default
3. Config supports both old and new formats

### Phase 3: Update High-Level Code
1. Update `HierarchicalEvolver` to use factory
2. Update CLI to initialize via factory
3. Gradual migration

### Phase 4: Deprecation (Optional)
1. Eventually deprecate direct `OllamaClient` use
2. Require factory pattern
3. Clean up old code

---

## 13. ESTIMATED IMPLEMENTATION EFFORT

| Task | Hours | Difficulty |
|------|-------|-----------|
| Create base LLMClient interface | 2-3 | Easy |
| Refactor OllamaClient | 1-2 | Easy |
| Implement AnthropicClient | 4 | Medium |
| Implement AzureAIClient | 4 | Medium |
| Implement LMStudioClient | 3 | Easy (OpenAI-compatible) |
| Create client factory | 1-2 | Easy |
| Update ConfigManager | 2-3 | Medium |
| Update ToolsManager | 2-3 | Medium |
| Update HierarchicalEvolver | 1-2 | Easy |
| Update orchestrator/CLI | 1-2 | Easy |
| Configuration updates | 1 | Easy |
| Testing and integration | 3-4 | Medium |
| **TOTAL** | **25-31 hours** | **Medium** |

---

## 14. KEY IMPLEMENTATION DECISIONS

### Decision 1: Abstract Base Class vs Protocol
- **Choice**: Abstract Base Class (`ABC`)
- **Reason**: More explicit, easier to document, better IDE support
- **Impact**: Requires explicit inheritance

### Decision 2: Factory vs Configuration-Based Creation
- **Choice**: Factory pattern with config
- **Reason**: Type safety, easier testing, clear initialization
- **Impact**: Slight overhead for client creation

### Decision 3: Backward Compatibility
- **Choice**: Keep Ollama as default, new configs are opt-in
- **Reason**: Existing users not affected, smooth migration
- **Impact**: Config merge logic slightly more complex

### Decision 4: API Key Handling
- **Choice**: Environment variables + config file (env vars override)
- **Reason**: Security best practice, flexibility
- **Impact**: Must update docs for env var names

---

## 15. FILES REFERENCE TABLE

| File | Size | Purpose | Changes Needed |
|------|------|---------|---|
| `config.yaml` | 900 lines | Configuration | Add new backend sections |
| `src/config_manager.py` | 494 lines | Config loading | Factory method, env vars |
| `src/ollama_client.py` | 419 lines | Ollama backend | Inherit from base class |
| `src/overseer_llm.py` | 425 lines | Strategy planning | Accept LLMClient base type |
| `src/evaluator_llm.py` | 367 lines | Fitness evaluation | Accept LLMClient base type |
| `src/tools_manager.py` | 500+ lines | Tool invocation | Support generic LLMClient |
| `src/hierarchical_evolver.py` | 600+ lines | Main orchestration | Use client factory |
| `src/openapi_tool.py` | 11 KB | OpenAPI tools | No changes (different abstraction) |
| `orchestrator.py` | 300+ lines | CLI orchestrator | Use factory |
| `chat_cli.py` | N/A | Chat interface | Use factory |
| `src/__init__.py` | 120 lines | Module exports | Export new classes |

