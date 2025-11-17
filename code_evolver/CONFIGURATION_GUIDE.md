# Configuration Guide

Complete guide to configuring the mostlylucid DiSE system for different LLM backends, execution environments, and optimization strategies.

> **⚠️ IMPORTANT: New Configuration System**
>
> The system now uses a **role-based and tier-based configuration architecture** for improved flexibility and maintainability.
>
> - **See [NEW_CONFIG_ARCHITECTURE.md](NEW_CONFIG_ARCHITECTURE.md)** for the complete new architecture
> - **See [MODEL_TIERS.md](MODEL_TIERS.md)** for tier-based configuration details
>
> **Key changes:**
> - Tools now reference **abstract roles** (fast, base, powerful) instead of hardcoded models
> - Role mappings defined once in config, not duplicated in every tool
> - Easy backend switching without changing tool definitions
> - **This guide has been updated to reflect the new system**

## Table of Contents

1. [New Configuration Architecture](#new-configuration-architecture) ⭐ **NEW**
2. [Configuration Files](#configuration-files)
3. [LLM Backend Configuration](#llm-backend-configuration)
4. [Execution Settings](#execution-settings)
5. [Testing & Code Quality](#testing--code-quality)
6. [Auto-Evolution & Optimization](#auto-evolution--optimization)
7. [Logging & Debugging](#logging--debugging)
8. [Advanced Configurations](#advanced-configurations)

---

## New Configuration Architecture

### Role-Based Configuration

The new system uses **abstract roles** that map to actual models:

```yaml
llm:
  backend: "ollama"

  # Map abstract roles to actual models
  model_roles:
    fast: "qwen2.5-coder:3b"          # Fast, simple tasks
    base: "codellama:7b"               # Most tasks (default)
    powerful: "qwen2.5-coder:14b"      # Complex reasoning
    god_level: "deepseek-coder-v2:16b" # Last resort
    embedding: "nomic-embed-text"      # Vector embeddings

  backends:
    ollama:
      base_url: "http://localhost:11434"
      enabled: true
```

**Tools reference roles:**

```yaml
# tools/llm/general.yaml
name: "General Code Generator"
type: "llm"
llm:
  role: "base"  # Uses codellama:7b with above config
```

### Tier-Based Configuration

For automatic escalation and context management:

```yaml
model_tiers:
  coding:
    tier_1:  # Fast coding
      model: "qwen2.5-coder:3b"
      context_window: 32768
      timeout: 60
      escalates_to: "tier_2"

    tier_2:  # General coding (DEFAULT)
      model: "codellama:7b"
      context_window: 16384
      timeout: 120
      escalates_to: "tier_3"

    tier_3:  # Complex coding
      model: "qwen2.5-coder:14b"
      context_window: 32768
      timeout: 600
      escalates_to: null
```

### Benefits of New System

✅ **Zero Tool Duplication** - Tools defined once, work with any backend
✅ **Easy Backend Switching** - Change role mappings, tools adapt automatically
✅ **Clean Separation** - Backend metadata, tool definitions, and user config are separate
✅ **Automatic Escalation** - Tiers escalate to more powerful models when needed
✅ **Context Management** - Higher tiers get bigger context windows

### Minimal Configuration Examples

**Anthropic (Claude):**
```yaml
# config.anthropic.minimal.yaml
llm:
  backend: "anthropic"
  model_roles:
    fast: "claude-3-haiku-20240307"
    base: "claude-3-5-sonnet-20241022"
    powerful: "claude-3-opus-20240229"
```

**OpenAI:**
```yaml
# config.openai.minimal.yaml
llm:
  backend: "openai"
  model_roles:
    fast: "gpt-4o-mini"
    base: "gpt-4o"
    powerful: "o1-preview"
```

**Local Ollama:**
```yaml
# config.local.minimal.yaml
llm:
  backend: "ollama"
  model_roles:
    fast: "qwen2.5-coder:3b"
    base: "codellama:7b"
    powerful: "deepseek-coder-v2:16b"
```

---

## Configuration Files

### File Structure

Configuration files use YAML format and are located in the `code_evolver/` directory:

```
code_evolver/
├── config.yaml                    # Main default configuration
├── config.local.yaml              # Local development (gitignored)
├── config.openai.yaml             # OpenAI provider
├── config.anthropic.yaml          # Anthropic Claude provider
├── config.anthropic.simple.yaml   # Simplified Anthropic config
├── config.azure.yaml              # Azure OpenAI provider
├── config.lmstudio.yaml           # LM Studio local models
├── config.hybrid.yaml             # Multi-backend with fallback
└── config.unified.yaml            # Unified backend configuration
```

### Configuration Priority

1. **Lowest**: Default `config.yaml`
2. **Medium**: Provider-specific (e.g., `config.openai.yaml`)
3. **Highest**: Local overrides (e.g., `config.local.yaml`) - automatically loaded and gitignored

### Loading Configuration

The system automatically loads configuration in this order:

```python
from src.config_manager import ConfigManager

# Automatically loads config.yaml + config.local.yaml (if exists)
config = ConfigManager()

# Access settings
backend = config.get("llm.backend")  # "ollama", "openai", "anthropic", etc.
```

---

## LLM Backend Configuration

> **Note:** The examples below show the **old configuration format** for reference.
>
> **The new recommended format** uses **role-based configuration** (see [New Configuration Architecture](#new-configuration-architecture) above).
>
> The old format still works for backward compatibility, but the new format is simpler and more flexible.

### 1. Ollama (Local Models) - NEW FORMAT ⭐

**Advantages**: Free, 100% private, no API keys needed
**Setup**: [ollama.ai](https://ollama.ai)

**Recommended (New Role-Based):**

```yaml
# config.local.minimal.yaml
llm:
  backend: "ollama"

  # Map abstract roles to actual models
  model_roles:
    fast: "qwen2.5-coder:3b"          # Fast tasks
    base: "codellama:7b"               # Default
    powerful: "qwen2.5-coder:14b"      # Complex tasks
    god_level: "deepseek-coder-v2:16b" # Last resort
    embedding: "nomic-embed-text"      # Embeddings

  backends:
    ollama:
      base_url: "http://localhost:11434"
      enabled: true
```

<details>
<summary><strong>Old Format (still supported, but deprecated)</strong></summary>

```yaml
# config.yaml - OLD FORMAT
llm:
  backend: "ollama"

  ollama:
    base_url: "http://localhost:11434"

    models:
      # Task classification (fast, small model)
      triage:
        model: "tinyllama"
        temperature: 0.1
        timeout: 10

      # Main code generation
      generator:
        model: "codellama"
        temperature: 0.3
        timeout: 60

      # Overseer/planner
      overseer:
        model: "llama3"
        temperature: 0.2
        timeout: 45

      # Evaluator
      evaluator:
        model: "llama3"
        temperature: 0.1
        timeout: 30

      # Escalation (most powerful)
      escalation:
        model: "deepseek-coder-v2:16b"
        temperature: 0.7
        timeout: 120
```

</details>

**Installation**:
```bash
ollama pull tinyllama
ollama pull codellama
ollama pull llama3
ollama pull deepseek-coder-v2:16b

# Start server
ollama serve
```

---

### 2. OpenAI (GPT Models) - NEW FORMAT ⭐

**Advantages**: High quality, fast inference, frontier models
**Cost**: Pay-per-use

**Recommended (New Role-Based):**

```yaml
# config.openai.minimal.yaml
llm:
  backend: "openai"

  # Map abstract roles to actual models
  model_roles:
    fast: "gpt-4o-mini"     # Fast, cheap tasks
    base: "gpt-4o"          # Default
    powerful: "o1-preview"  # Complex reasoning
    god_level: "o1"         # Most powerful

  backends:
    openai:
      api_key: "${OPENAI_API_KEY}"
      base_url: "https://api.openai.com/v1"
      enabled: true
```

<details>
<summary><strong>Old Format (still supported, but deprecated)</strong></summary>

```yaml
# config.openai.yaml - OLD FORMAT
llm:
  backend: "openai"

  openai:
    api_key: "${OPENAI_API_KEY}"  # Set via environment variable
    base_url: "https://api.openai.com/v1"
    organization: "your-org-id"  # Optional

    models:
      triage:
        model: "gpt-3.5-turbo"
        temperature: 0.1
        timeout: 10

      generator:
        model: "gpt-3.5-turbo"
        temperature: 0.3
        timeout: 30

      overseer:
        model: "gpt-4-turbo"
        temperature: 0.2
        timeout: 45

      evaluator:
        model: "gpt-3.5-turbo"
        temperature: 0.1
        timeout: 20

      escalation:
        model: "gpt-4"
        temperature: 0.7
        timeout: 60
```

</details>

**Setup**:
```bash
export OPENAI_API_KEY="sk-..."
python chat_cli.py
```

---

### 3. Anthropic (Claude) - NEW FORMAT ⭐

**Advantages**: Strong reasoning, long context, excellent code understanding
**Cost**: Pay-per-use

**Recommended (New Role-Based):**

```yaml
# config.anthropic.minimal.yaml
llm:
  backend: "anthropic"

  # Map abstract roles to actual models
  model_roles:
    fast: "claude-3-haiku-20240307"       # Fast, cheap tasks
    base: "claude-3-5-sonnet-20241022"    # Default (best balance)
    powerful: "claude-3-opus-20240229"    # Complex reasoning
    god_level: "claude-3-opus-20240229"   # Most powerful

  backends:
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}"
      enabled: true
```

<details>
<summary><strong>Old Format (still supported, but deprecated)</strong></summary>

```yaml
# config.anthropic.yaml - OLD FORMAT
llm:
  backend: "anthropic"

  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    base_url: "https://api.anthropic.com"

    models:
      triage:
        model: "claude-3-haiku-20240307"
        temperature: 0.1
        timeout: 10

      generator:
        model: "claude-3-sonnet-20240229"
        temperature: 0.3
        timeout: 45

      overseer:
        model: "claude-3-sonnet-20240229"
        temperature: 0.2
        timeout: 60

      evaluator:
        model: "claude-3-haiku-20240307"
        temperature: 0.1
        timeout: 30

      escalation:
        model: "claude-3-opus-20240229"
        temperature: 0.7
        timeout: 120
```

**Setup**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python chat_cli.py
```

---

### 4. Azure OpenAI (Enterprise)

**Advantages**: Enterprise compliance, custom deployments, Azure integration
**Cost**: Depends on Azure plan

```yaml
# config.azure.yaml
llm:
  backend: "azure"

  azure:
    api_key: "${AZURE_OPENAI_API_KEY}"
    endpoint: "${AZURE_OPENAI_ENDPOINT}"
    api_version: "2024-02-15-preview"

    models:
      triage:
        deployment: "gpt-35-turbo-small"
        temperature: 0.1

      generator:
        deployment: "gpt-35-turbo"
        temperature: 0.3

      overseer:
        deployment: "gpt-4-turbo"
        temperature: 0.2

      escalation:
        deployment: "gpt-4"
        temperature: 0.7
```

---

### 5. LM Studio (Local GGUF Models)

**Advantages**: Free, any GGUF model, full privacy
**Setup**: Download LM Studio from [lmstudio.ai](https://lmstudio.ai)

```yaml
# config.lmstudio.yaml
llm:
  backend: "lmstudio"

  lmstudio:
    base_url: "http://localhost:1234/v1"

    models:
      generator:
        model: "your-fine-tuned-model"
        temperature: 0.3
        timeout: 60
```

---

### 6. Multi-Backend with Fallback

**Use Case**: Hybrid setup with automatic fallback

```yaml
# config.hybrid.yaml
llm:
  backend: "ollama"  # Primary
  fallback_backends: ["openai", "anthropic"]  # Fallback order

  # Configure all backends
  ollama:
    base_url: "http://localhost:11434"
    models:
      generator:
        model: "codellama"

  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      generator:
        model: "gpt-3.5-turbo"

  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      generator:
        model: "claude-3-sonnet-20240229"
```

**Behavior**:
1. Try primary backend (ollama)
2. If fails → fallback to OpenAI
3. If fails → fallback to Anthropic
4. If all fail → error

---

## Execution Settings

### Timeouts & Performance

```yaml
execution:
  # Default timeout for code execution (seconds)
  default_timeout: 30

  # Timeout for LLM model calls
  llm_timeout: 120

  # Memory monitoring
  memory:
    # Monitor peak memory usage
    monitor_peak: true
    # Warn if exceeds threshold (MB)
    warning_threshold: 512
    # Kill if exceeds threshold (0 = disabled)
    kill_threshold: 1024

  # Retry configuration
  retries:
    max_attempts: 3
    backoff_factor: 2  # exponential backoff
    initial_delay: 1   # seconds
```

### Sandbox & Security

```yaml
execution:
  sandbox:
    # Enable code execution sandbox (false for full access)
    enabled: false

    # Environment variables allowed
    allowed_env_vars:
      - "PATH"
      - "HOME"
      - "USER"
      - "OPENAI_API_KEY"
      - "ANTHROPIC_API_KEY"
```

---

## Testing & Code Quality

### Unit Test Generation

```yaml
testing:
  # Auto-generate unit tests
  generate_unit_tests: true

  # Test framework
  framework: "pytest"

  # Require passing tests before code acceptance
  require_passing_tests: true

  # Test generation template
  test_template: "bdd"  # "bdd", "unittest", "pytest"

  # Coverage requirements
  coverage:
    # Minimum code coverage %
    minimum_coverage: 70
    # Types to measure
    measure: ["line", "branch"]
```

### Static Analysis Configuration

```yaml
static_analysis:
  # Enable static analysis checks
  enabled: true

  # Validators to run (in order of priority)
  validators:
    - name: "syntax"
      enabled: true
      priority: 200

    - name: "undefined_names"
      enabled: true
      priority: 120
      tool: "flake8"

    - name: "import_order"
      enabled: true
      priority: 110
      tool: "isort"
      auto_fix: true

    - name: "type_checking"
      enabled: true
      priority: 100
      tool: "mypy"
      args: ["--strict"]

    - name: "security"
      enabled: true
      priority: 80
      tool: "bandit"

    - name: "complexity"
      enabled: true
      priority: 70
      tool: "radon"
      max_complexity: 10

  # Timeout per validator (seconds)
  validator_timeout: 30

  # Fail on any validation error
  fail_on_error: true
```

### Code Quality Tools

```yaml
code_quality:
  # Style checking
  flake8:
    enabled: true
    max_line_length: 100
    ignore: ["E203", "W503"]  # Ignored error codes

  # Type checking
  mypy:
    enabled: true
    strict: true

  # Code formatting
  black:
    enabled: true
    line_length: 100

  # Import sorting
  isort:
    enabled: true
    profile: "black"
    auto_fix: true

  # Security scanning
  bandit:
    enabled: true
    severity_level: "medium"

  # Complexity analysis
  radon:
    enabled: true
    max_cyclomatic_complexity: 10
    max_maintainability_index: 50
```

---

## Auto-Evolution & Optimization

### Optimization Loop

```yaml
auto_evolution:
  # Enable automatic code optimization
  enabled: true

  # Number of optimization iterations
  iterations: 3

  # Targets to optimize for
  targets:
    - "performance"  # Speed optimization
    - "memory"       # Memory efficiency
    - "quality"      # Code quality improvements

  # Performance improvement threshold
  improvement_threshold: 0.05  # 5% improvement required

  # Complexity management
  complexity:
    max_cyclomatic: 10
    max_maintainability: 50
```

### Pattern Clustering

```yaml
pattern_recognition:
  # Enable pattern clustering for RAG optimization
  enabled: true

  # Minimum cluster size
  min_cluster_size: 3

  # Similarity threshold (0-1)
  similarity_threshold: 0.75

  # Run clustering every N executions
  run_every: 10

  # Auto-generate tools from patterns
  auto_generate_tools: true
```

---

## Logging & Debugging

### Logging Configuration

```yaml
logging:
  # Log level: DEBUG, INFO, WARNING, ERROR
  level: "INFO"

  # Log to file
  file: "code_evolver.log"

  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

  # Max log file size (MB)
  max_size: 100

  # Number of backup log files to keep
  backup_count: 5

  # Console output
  console:
    enabled: true
    level: "INFO"  # Can be different from file
```

### Debug Mode

```yaml
debug:
  # Enable debug logging
  enabled: false

  # Log LLM prompts and responses
  log_llm_calls: false

  # Log code generation details
  log_generation: false

  # Log test execution
  log_tests: true

  # Keep temporary files
  keep_temp_files: false

  # Verbose output
  verbose: false
```

---

## Advanced Configurations

### RAG Memory Configuration

```yaml
rag:
  # Enable RAG memory system
  enabled: true

  # Vector database backend
  backend: "qdrant"  # "qdrant", "faiss", "inmemory"

  # Qdrant configuration
  qdrant:
    host: "localhost"
    port: 6333

    # Collection settings
    collection_name: "code_evolver"
    vector_size: 384
    distance_metric: "cosine"

  # Embedding model
  embedding:
    model: "sentence-transformers/all-MiniLM-L6-v2"
    dimension: 384

  # Storage settings
  storage:
    # Maximum artifacts to store
    max_artifacts: 10000
    # TTL for artifacts (days)
    retention_days: 90
```

### HTTP Server Configuration

```yaml
http_server:
  # Enable HTTP server tool
  enabled: true

  # Server settings
  host: "0.0.0.0"
  port: 8080

  # Request handling
  max_request_size: "10mb"
  request_timeout: 30

  # CORS settings
  cors:
    enabled: true
    allowed_origins: ["*"]
    allowed_methods: ["GET", "POST", "PUT", "DELETE"]

  # Logging
  log_requests: true
```

### Tool Configuration

```yaml
tools:
  # Tool registry
  registry_path: "./tools"

  # Cache tool definitions
  cache_definitions: true

  # Tool timeout (seconds)
  default_timeout: 30

  # Custom tools directory
  custom_tools_dir: "./custom_tools"

  # Tool metadata
  metadata:
    # Add cost/speed/quality tiers
    include_performance_metrics: true
```

---

## Configuration Examples

### Minimal Local Setup

```yaml
# config.local.yaml
llm:
  backend: "ollama"

  ollama:
    base_url: "http://localhost:11434"

    models:
      generator:
        model: "codellama"

testing:
  generate_unit_tests: true

auto_evolution:
  enabled: true
  iterations: 2
```

### Production OpenAI Setup

```yaml
# config.production.yaml
llm:
  backend: "openai"

  openai:
    api_key: "${OPENAI_API_KEY}"

    models:
      generator:
        model: "gpt-4"
        temperature: 0.3

execution:
  default_timeout: 60
  memory:
    kill_threshold: 2048

testing:
  generate_unit_tests: true
  require_passing_tests: true
  coverage:
    minimum_coverage: 80

static_analysis:
  enabled: true
  fail_on_error: true

logging:
  level: "WARNING"
```

### Hybrid Development Setup

```yaml
# config.hybrid.yaml
llm:
  backend: "ollama"
  fallback_backends: ["openai"]

  ollama:
    base_url: "http://localhost:11434"
    models:
      generator:
        model: "codellama"

  openai:
    api_key: "${OPENAI_API_KEY}"
    models:
      generator:
        model: "gpt-4"

auto_evolution:
  enabled: true
  iterations: 3

debug:
  enabled: true
  log_generation: true
```

---

## Environment Variables

### Backend API Keys

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Azure OpenAI
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://..."

# LM Studio (local, no key needed)
```

### Other Settings

```bash
# Enable debug mode
export DEBUG=1

# Log level
export LOG_LEVEL=DEBUG

# Custom config file
export CONFIG_FILE=config.production.yaml

# RAG database URL
export QDRANT_URL=http://localhost:6333
```

---

## Loading Custom Configuration

### Programmatically

```python
from src.config_manager import ConfigManager

# Load specific config file
config = ConfigManager(config_file="config.production.yaml")

# Access settings
llm_backend = config.get("llm.backend")
timeout = config.get("execution.default_timeout")

# Override settings
config.set("llm.backend", "openai")

# Get all settings
all_settings = config.get_all()
```

### Command Line

```bash
# Use specific config
CONFIG_FILE=config.openai.yaml python chat_cli.py

# Override settings
export OPENAI_API_KEY="sk-..."
python chat_cli.py
```

---

## Validation & Defaults

The configuration system validates all settings against a schema and provides sensible defaults:

- **Missing values**: Use built-in defaults
- **Type mismatches**: Raise validation error
- **Invalid choices**: Suggest valid options
- **Missing required settings**: Clear error messages

```python
# Validation happens automatically
config = ConfigManager()  # Validates on load

# Check if valid
if config.is_valid():
    print("Configuration OK")
else:
    print("Validation errors:", config.get_errors())
```

---

## See Also

- [TOOL_INVOCATION_GUIDE.md](TOOL_INVOCATION_GUIDE.md) - Using `call_tool()` and tool chains
- [STATIC_ANALYSIS_TOOLS.md](STATIC_ANALYSIS_TOOLS.md) - Static analysis validators
- [README.md](../README.md) - Overview and features
