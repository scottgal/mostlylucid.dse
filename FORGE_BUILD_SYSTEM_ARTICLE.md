# The Forge Build System - Complete Architecture Guide

## Executive Summary

**Forge** is a sophisticated, production-grade tool management and execution system within the mostlylucid DiSE (Directed Synthetic Evolution) codebase. It provides a RAG-backed, consensus-driven architecture for generating, validating, optimizing, and serving tools through a distributed network.

The system is designed to be:
- **Self-improving**: Learns from execution metrics to improve tool selection
- **Consensus-hardened**: Tools validated by multiple LLM models
- **Integration-optimized**: Tests tools in real workflows to characterize performance
- **Provenance-tracked**: Full lineage and audit logs for all tools
- **Mesh-ready**: Architecture supports distributed forge networks

---

## Part 1: Architecture Overview

### 1.1 Core System Layers

The Forge system operates on three main architectural layers:

```
┌─────────────────────────────────────────────────────┐
│ PRESENTATION LAYER - CLI Interface                 │
│ └─ ForgeCLI (forge/cli.py)                          │
│    - /forge_register, /forge_validate, /forge_query │
│    - /forge_execute, /forge_optimize, /forge_list   │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│ ORCHESTRATION LAYER - Director & Management        │
│ ├─ ForgeDirector (forge/core/director.py) - High-level orchestration
│ ├─ ValidationCouncil (forge/core/validator.py) - Multi-stage validation
│ ├─ ConsensusEngine (forge/core/consensus.py) - Metric aggregation
│ └─ IntegrationOptimizer (forge/core/optimizer.py) - Workflow optimization
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│ EXECUTION & STORAGE LAYER                           │
│ ├─ ForgeRegistry (forge/core/registry.py) - Tool manifests + RAG backend
│ ├─ ForgeRuntime (forge/core/runtime.py) - MCP server execution
│ ├─ RAGMemory (src/rag_memory.py) - Semantic search & storage
│ └─ ToolsManager (src/tools_manager.py) - Tool definitions
└─────────────────────────────────────────────────────┘
```

### 1.2 Component Responsibilities

| Component | File | Lines | Responsibility |
|-----------|------|-------|-----------------|
| **ForgeCLI** | forge/cli.py | 420 | User-facing command interface |
| **ForgeDirector** | forge/core/director.py | 401 | Intent → Tool execution orchestration |
| **ForgeRegistry** | forge/core/registry.py | 364 | Tool manifest storage & semantic search |
| **ForgeRuntime** | forge/core/runtime.py | 281 | MCP server management & sandboxed execution |
| **ValidationCouncil** | forge/core/validator.py | 409 | Multi-stage validation pipeline |
| **ConsensusEngine** | forge/core/consensus.py | 338 | Metric aggregation & weight calculation |
| **IntegrationOptimizer** | forge/core/optimizer.py | 333 | Workflow performance characterization |

---

## Part 2: Entry Points & Execution Flow

### 2.1 Main Entry Points

The Forge system can be invoked through multiple entry points:

#### **Chat CLI** (`chat_cli.py` - 515KB)
```python
# Interactive conversation-based interface
$ python chat_cli.py
> /forge_register my_tool mcp
> /forge_validate my_tool
> /forge_query translate_text --latency 500 --risk 0.2
> /forge_execute my_tool --input '{"text": "Hello"}'
```

#### **Orchestrator** (`orchestrator.py`)
```python
# Programmatic workflow management
orchestrator = Orchestrator()
orchestrator.check_setup()
orchestrator.generate_node("node_id", "Title", "prompt")
orchestrator.run_node("node_id", {"input": "data"})
```

#### **Build System** (`build.py`, `build_executable.py`)
```bash
# Create standalone executables
python build_executable.py --platform windows
python build_executable.py --all  # All platforms
```

### 2.2 Complete Execution Flow

```
User Input (Intent)
        ↓
    ForgeCLI
        ├─ /forge_register → ForgeRegistry.register_tool_manifest()
        ├─ /forge_validate → ValidationCouncil.validate_tool()
        ├─ /forge_query   → ForgeRegistry.query_tools()
        ├─ /forge_execute → ForgeDirector.submit_intent()
        └─ /forge_optimize → IntegrationOptimizer.optimize_workflow()
        ↓
    ForgeDirector (Orchestration)
        ├─ Analyze intent (request decomposition)
        ├─ Query registry via RAG (semantic search)
        ├─ Generate tools if gaps exist (with LLM)
        ├─ Coordinate validation pipeline
        ├─ Execute via ForgeRuntime
        └─ Collect metrics → Update registry
        ↓
    ForgeRegistry (Storage & Discovery)
        ├─ Store tool manifest (YAML)
        ├─ Index in RAG memory
        ├─ Update consensus scores
        └─ Track lineage
        ↓
    ForgeRuntime (Execution)
        ├─ Start MCP server (if needed)
        ├─ Execute tool with sandbox
        ├─ Capture provenance (call_id, hashes, timestamps)
        └─ Collect metrics (latency, success rate, cost)
        ↓
    ConsensusEngine (Scoring)
        ├─ Aggregate execution metrics
        ├─ Apply temporal decay
        ├─ Calculate weighted consensus score
        └─ Update trust levels
        ↓
    IntegrationOptimizer (Optimization)
        ├─ Test tool variants in workflows
        ├─ Characterize performance
        ├─ Trigger specialization if thresholds met
        └─ Recommend best variants
```

---

## Part 3: Forge Registry & Tool Manifests

### 3.1 Tool Manifest Format

Tools in Forge are defined using comprehensive YAML manifests:

```yaml
tool_id: "nmt_translator"
version: "2.1.0"
name: "Neural Machine Translation Tool"
type: "mcp"
description: "High-performance neural machine translation supporting 50+ languages"

origin:
  author: "system"
  source_model: "claude-3.5-sonnet"
  created_at: "2025-10-15T12:30:00Z"

lineage:
  ancestor_tool_id: "nmt_translator_v1"
  mutation_reason: "improved latency under load"
  commits:
    - id: "c9a2f8b"
      message: "Optimize batch processing"
      timestamp: "2025-10-15T12:30:00Z"

mcp:
  server_name: "nmt_server"
  command: "npx"
  args: ["-y", "@modelcontextprotocol/server-nmt"]
  env:
    DEBUG: "false"
    MAX_BATCH_SIZE: "32"

capabilities:
  - name: "translate"
    description: "Translate text between languages"
    parameters:
      text: {type: "string", required: true}
      target_lang: {type: "string", required: true}

trust:
  level: "core"
  validation_score: 0.98
  risk_score: 0.05

metrics:
  latest:
    correctness: 0.98
    latency_ms_p95: 180
    cost_per_call: 0.0003
    failure_rate: 0.005

tags: ["mcp", "translation", "nmt", "multilingual"]
```

### 3.2 Registry Operations

The ForgeRegistry provides semantic search and storage:

```python
# Register a new tool
manifest = ToolManifest(
    tool_id="my_tool",
    version="1.0.0",
    name="My Tool",
    type="mcp",
    description="Does something useful"
)
registry.register_tool_manifest(manifest)

# Query tools by capability
results = registry.query_tools(
    capability="translate_text",
    constraints={
        'latency_ms_p95': 500,
        'risk_score': 0.2
    }
)

# Get best tool
best_tool = results['best_tool']
alternatives = results['alternatives']
```

### 3.3 Trust Levels

Tools are classified into three trust levels:

| Level | Validation Score | Characteristics | Usage |
|-------|-----------------|-----------------|-------|
| **core** | ≥ 0.95 | Fully validated, low risk | Production workloads |
| **third_party** | ≥ 0.80 | Contributed tools, moderate testing | Experimental features |
| **experimental** | < 0.80 | Newly generated, needs validation | Testing only |

---

## Part 4: Workflow System

### 4.1 Workflow Specifications

Workflows are defined declaratively in JSON/YAML:

```json
{
  "workflow_id": "translation_pipeline",
  "version": "1.0.0",
  "description": "Multi-step translation and localization workflow",
  
  "inputs": {
    "text": {"type": "string", "required": true},
    "target_lang": {"type": "string", "required": true}
  },
  
  "outputs": {
    "translated_text": {
      "type": "string",
      "source_reference": "steps.translate.result"
    }
  },
  
  "steps": [
    {
      "step_id": "translate",
      "type": "llm_call",
      "tool": "nmt_translator",
      "input_mapping": {
        "text": "inputs.text",
        "target_lang": "inputs.target_lang"
      },
      "output_name": "result"
    },
    {
      "step_id": "post_process",
      "type": "python_tool",
      "tool": "text_cleaner",
      "input_mapping": {
        "text": "steps.translate.result"
      }
    }
  ]
}
```

### 4.2 Workflow Builder

The WorkflowBuilder converts overseer output into executable workflows:

```python
builder = WorkflowBuilder(tools_manager)

# Build from overseer output
workflow = builder.build_from_text(
    description="Translate text to Spanish",
    overseer_output=overseer_response,
    task_id="translation_task"
)

# Or create simple single-step workflow
workflow = builder.create_simple_workflow(
    description="Translate text",
    tool_name="nmt_translator"
)

# Execute workflow
result = workflow.execute({"text": "Hello", "target_lang": "es"})
```

### 4.3 Step Types

Workflows support multiple step types:

| Step Type | Usage | Example |
|-----------|-------|---------|
| `LLM_CALL` | Call an LLM model | Translation, content generation |
| `PYTHON_TOOL` | Execute Python code | Data processing, validation |
| `SUB_WORKFLOW` | Execute nested workflow | Complex multi-stage processes |
| `EXISTING_TOOL` | Use registered tool | Call any Forge-registered tool |

---

## Part 5: Validation Pipeline

### 5.1 Multi-Stage Validation

The ValidationCouncil runs tools through 6 validation stages:

```
Input Tool Manifest
        ↓
┌───────────────────────────────────────┐
│ Stage 1: BDD Acceptance Tests         │
│ Tool: behave_test_generator           │
│ Output: Test feature file + results   │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│ Stage 2: Unit Tests                   │
│ Tool: pytest                           │
│ Output: Coverage report, test results │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│ Stage 3: Load Tests                   │
│ Tool: locust_test_generator           │
│ Output: Performance characteristics   │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│ Stage 4: Static Security Scan         │
│ Tools: semgrep, bandit, llm_static    │
│ Output: Security findings             │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│ Stage 5: Fuzz Testing                 │
│ Tool: LLM-based fuzzer                │
│ Output: Edge cases, error handling    │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│ Stage 6: Multi-LLM Consensus Review   │
│ Models: Multiple LLM backends         │
│ Output: Consensus validation score    │
└───────────────────────────────────────┘
        ↓
Validation Result (score, trust_level)
```

### 5.2 Validation Result

```python
result = validator.validate_tool("my_tool", "1.0.0")

{
    'success': True,
    'validation_score': 0.92,
    'stages': [
        {
            'name': 'BDD acceptance tests',
            'success': True,
            'score': 0.95,
            'metrics': {...}
        },
        # ... more stages
    ],
    'trust_level': 'third_party'
}
```

---

## Part 6: Consensus Engine & Metrics

### 6.1 Multi-Dimensional Scoring

The ConsensusEngine aggregates metrics across five dimensions:

```
Tool Performance Score Calculation:

consensus_score = Σ(dimension_value × dimension_weight)

Dimensions:
├─ Correctness (weight: 0.30)
│  └─ Validation score, test pass rate, accuracy metrics
├─ Latency (weight: 0.25)
│  └─ p50, p95, p99 execution time
├─ Cost (weight: 0.15)
│  └─ Per-call cost, resource usage
├─ Safety (weight: 0.20)
│  └─ Security findings, risk score, vulnerability count
└─ Resilience (weight: 0.10)
   └─ Success rate, error handling, recovery time
```

### 6.2 Temporal Decay

Recent performance is weighted more heavily:

```python
decayed_weight = weight × exp(-decay_factor × age_days)

# Example: After 30 days
# decay_factor = 0.1
# decayed_weight = weight × exp(-0.1 × 30) = weight × 0.049
```

### 6.3 Dynamic Weight Adjustment

Weights adjust based on task constraints:

```python
constraints = {
    'latency_critical': True,  # Increase latency weight
    'cost_sensitive': True,     # Increase cost weight
    'safety_critical': True     # Increase safety weight
}

# Weights recalculated: latency 0.25 → 0.40, etc.
```

---

## Part 7: Integration Optimizer

### 7.1 Workflow Optimization Process

The IntegrationOptimizer characterizes tool variants in real workflows:

```python
optimizer.optimize_workflow(
    workflow_id='translation_pipeline',
    tasks=[
        {
            'id': 'translate',
            'role': 'translator',
            'candidates': [
                {'tool_id': 'nmt_v1', 'variant_tag': 'fast'},
                {'tool_id': 'nmt_v2', 'variant_tag': 'accurate'}
            ]
        }
    ],
    runs={
        'count': 50,
        'constraints': {'latency_ms_p95': 500}
    }
)
```

### 7.2 Specialization Triggers

Triggers automatically create specialized variants:

```
Condition: "latency_p95 < 200ms consistently"
Action: "Create 'fast' variant with optimizations"

Condition: "accuracy > 0.99 for 100+ runs"
Action: "Create 'accurate' variant, promote to core trust level"

Condition: "failure_rate > 0.05"
Action: "Trigger evolution, test alternative implementations"
```

---

## Part 8: Build System

### 8.1 PyInstaller Build Process

The build system creates standalone executables:

```
┌─ build.py (363 lines)
│  ├─ Platform detection (Windows/Linux/macOS)
│  ├─ Clean build directories
│  ├─ Configure PyInstaller args
│  ├─ Include data files (config, docs, prompts)
│  └─ Execute build
│
└─ build_executable.py (533 lines)
   ├─ ToolDependencyAnalyzer
   │  ├─ Load all tool definitions
   │  ├─ Analyze dependencies
   │  ├─ Tree-shake unused tools
   │  └─ Calculate minimal set needed
   │
   ├─ Tool inlining
   │  ├─ Embed all tools in single file
   │  ├─ Add ID comments for identification
   │  └─ Reduce final executable size
   │
   ├─ Config generation
   │  ├─ Minimal settings file
   │  ├─ Comprehensive documentation
   │  └─ Platform-specific adjustments
   │
   └─ Output
      ├─ dist/code_evolver.exe (Windows)
      ├─ dist/code_evolver (Linux/Mac)
      ├─ dist/config.yaml (minimal)
      └─ dist/README.md (instructions)
```

### 8.2 Build Script Usage

```bash
# Build for current platform
python build_executable.py

# Build for specific platform
python build_executable.py --platform windows

# Build for all platforms
python build_executable.py --all

# Analyze what would be included (dry run)
python build_executable.py --analyze
```

---

## Part 9: Configuration Management

### 9.1 Configuration Hierarchy

```yaml
llm:
  # Model registry - define models once
  models:
    claude_sonnet:
      name: "claude-3-5-sonnet-20241022"
      backend: "anthropic"
      context_window: 200000
      cost: "medium"
    
    qwen_14b:
      name: "qwen2.5-coder:14b"
      backend: "ollama"
      context_window: 32768
      cost: "high"
  
  # Cascading defaults
  defaults:
    god: deepseek_16b
    escalation: qwen_14b
    general: gemma3_4b
    fast: qwen25_3b
    veryfast: gemma3_1b
  
  # Role-specific overrides
  roles:
    code:
      general: codellama_7b
      fast: qwen_3b
    
    content:
      god: mistral_nemo
```

### 9.2 Configuration Sources

| Config File | Purpose |
|------------|---------|
| `config.yaml` | Main unified configuration |
| `config.anthropic.yaml` | Anthropic API setup |
| `config.local.yaml` | Local Ollama setup |
| `config.azure.yaml` | Azure OpenAI setup |
| `config.mcp.yaml` | MCP server configuration |
| `config.tiered.yaml` | Multi-tier model setup |

---

## Part 10: RAG Integration

### 10.1 Tool Storage in RAG

Tool manifests are stored in RAG for semantic search:

```python
# When registering a tool
artifact_id = f"{tool.tool_id}_v{tool.version}"
rag_memory.store_artifact(
    artifact_id=artifact_id,
    artifact_type=ArtifactType.TOOL,
    name=tool.name,
    description=tool.description,
    content=json.dumps(tool.to_dict()),
    tags=tool.tags + ['forge', f"trust:{tool.trust['level']}"],
    metadata={
        'tool_id': tool.tool_id,
        'version': tool.version,
        'type': tool.type,
        'trust_level': tool.trust.get('level'),
        'validation_score': tool.trust.get('validation_score'),
        'lineage': tool.lineage
    }
)
```

### 10.2 Semantic Tool Discovery

```python
# Query tools with semantic search
results = registry.query_tools(
    capability="translate",
    constraints={'latency_ms_p95': 500}
)

# RAG returns:
# - Semantic matches (embeddings of description/capabilities)
# - Filtered by constraints
# - Ranked by consensus score
# - With lineage information
```

---

## Part 11: Tools Manager

### 11.1 Tool Types

The system supports many tool types:

```python
class ToolType(Enum):
    # Core tools
    FUNCTION = "function"
    LLM = "llm"
    WORKFLOW = "workflow"
    COMMUNITY = "community"
    
    # Data and storage
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    VECTOR_STORE = "vector_store"
    API_CONNECTOR = "api_connector"
    
    # Optimization
    FINE_TUNED_LLM = "fine_tuned_llm"
    TRAINING_PIPELINE = "training_pipeline"
    OPTIMIZER = "optimizer"
    
    # Execution
    EXECUTABLE = "executable"
    OPENAPI = "openapi"
    MCP = "mcp"
```

### 11.2 Tool Definition

Tools are defined in YAML with rich metadata:

```yaml
name: "Environment File Generator"
type: "executable"
description: "Generates .env files with complete configuration"

cost_tier: "free"
speed_tier: "very-fast"
quality_tier: "excellent"

executable:
  command: "python"
  args: ["{tool_dir}/env_file_generator.py"]

input_schema:
  config_json: "str - JSON configuration"

output_schema:
  success: "bool"
  env_file: "str"

tags:
  - environment
  - configuration
  - docker
```

---

## Part 12: Runtime Execution

### 12.1 Node Runtime

The NodeRuntime provides the execution environment for generated code:

```python
runtime = NodeRuntime.get_instance()

# Call any tool
result = runtime.call_tool(
    "technical_writer",
    "Write a blog post about Python decorators",
    temperature=0.7,
    system_prompt="You are an expert Python educator"
)

# Tool usage is tracked by default
# Can be disabled via: disable_tracking=True
```

### 12.2 Execution Tracking

Usage tracking is enabled by default and can be disabled at three levels:

```python
# Tool-level (in YAML)
track_usage: false

# Workflow-level (environment variable)
export DISABLE_USAGE_TRACKING=true

# Call-level (parameter)
runtime.call_tool("tool_name", "prompt", disable_tracking=True)
```

---

## Part 13: Data Structures

### 13.1 Key Data Classes

```python
@dataclass
class ToolManifest:
    """Complete tool specification"""
    tool_id: str
    version: str
    name: str
    type: str
    description: str
    origin: Dict[str, Any]
    lineage: Dict[str, Any]
    mcp: Optional[Dict[str, Any]]
    capabilities: List[Dict[str, Any]]
    trust: Dict[str, Any]
    metrics: Dict[str, Any]
    tags: List[str]

@dataclass
class ConsensusScore:
    """Consensus scoring record"""
    tool_id: str
    version: str
    scores: Dict[str, float]
    weight: float
    evaluators: List[Dict[str, Any]]
    timestamp: str

@dataclass
class IntentRequest:
    """Tool orchestration request"""
    intent: str
    context_docs: Optional[List[str]]
    constraints: Optional[Dict[str, Any]]
    preferences: Optional[Dict[str, str]]

@dataclass
class VariantCharacterization:
    """Tool variant performance metrics"""
    tool_id: str
    version: str
    variant_tag: str
    metrics: Dict[str, float]
    run_count: int
    success_rate: float
```

---

## Part 14: Directory Structure

```
code_evolver/
├── forge/                          # Forge system
│   ├── __init__.py
│   ├── cli.py (420 lines)          # User CLI interface
│   ├── README.md                   # Comprehensive documentation
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── registry.py (364)       # Tool manifest storage & RAG
│   │   ├── director.py (401)       # Intent orchestration
│   │   ├── runtime.py (281)        # MCP execution & sandboxing
│   │   ├── validator.py (409)      # Multi-stage validation
│   │   ├── consensus.py (338)      # Metric aggregation
│   │   └── optimizer.py (333)      # Workflow optimization
│   │
│   ├── data/
│   │   ├── manifests/              # Tool manifest YAML files
│   │   │   └── example_translator.yaml
│   │   ├── workflows/              # Example workflows
│   │   │   └── example_translation_workflow.yaml
│   │   └── logs/                   # Provenance logs
│   │
│   └── tests/
│       ├── test_registry.py
│       └── test_consensus.py
│
├── src/                            # Core system modules
│   ├── workflow_spec.py            # Workflow definitions
│   ├── workflow_builder.py         # Workflow construction
│   ├── rag_memory.py               # RAG storage & search
│   ├── tools_manager.py            # Tool registry
│   ├── config_manager.py           # Configuration
│   ├── recursive_optimizer.py      # Optimization pipeline
│   ├── llm_client_factory.py       # LLM client creation
│   └── ... (140+ other modules)
│
├── build.py (363)                  # Platform build script
├── build_executable.py (533)       # Tree-shaking executable builder
├── node_runtime.py                 # Generated code execution
├── orchestrator.py                 # Workflow management
├── chat_cli.py (515KB)             # Interactive interface
│
├── workflows/                      # Example workflows
│   ├── simple_summarizer.json
│   ├── data_analysis_workflow.json
│   ├── docker_packaging_workflow.json
│   └── test_parallel_workflow.json
│
├── tools/                          # Tool definitions
│   ├── executable/                 # Executable tools
│   │   ├── env_file_generator.yaml
│   │   ├── docker_compose_generator.yaml
│   │   └── ... (50+ tools)
│   ├── llm/                        # LLM-based tools
│   │   └── ... (20+ tools)
│   ├── debug/                      # Debug tools
│   │   └── ... (10+ tools)
│   └── perf/                       # Performance tools
│       └── ... (5+ tools)
│
└── config*.yaml                    # Configuration files
    ├── config.yaml                 # Main config
    ├── config.anthropic.yaml
    ├── config.local.yaml
    └── ... (12+ variants)
```

---

## Part 15: Key Algorithms & Processes

### 15.1 Tool Discovery Algorithm

```
Query Tool Registry:

1. Parse Query
   └─ Extract capability + constraints

2. Semantic Search
   └─ Query RAG with embedding
   └─ Find similar tool descriptions
   └─ Return candidates with similarity scores

3. Constraint Filtering
   └─ Filter by latency threshold
   └─ Filter by risk score
   └─ Filter by trust level
   └─ Filter by cost range

4. Ranking
   └─ Apply consensus weights
   └─ Apply temporal decay
   └─ Sort by final score
   
5. Return
   └─ Best tool (top candidate)
   └─ Alternatives (2-5 runners-up)
   └─ Metadata & metrics
```

### 15.2 Validation Scoring Algorithm

```
Calculate Validation Score:

1. Run all 6 validation stages
   └─ Each stage produces score (0.0-1.0)

2. Aggregate stage scores
   stage_weight = depends on stage
   aggregate_score = Σ(stage_score × stage_weight)

3. Apply modifiers
   └─ If any stage failed: reduce score
   └─ If security critical: increase weight of security findings
   
4. Determine trust level
   ├─ score ≥ 0.95 → core
   ├─ score ≥ 0.80 → third_party
   └─ score < 0.80 → experimental

5. Return
   └─ Overall score
   └─ Per-stage results
   └─ Recommended trust level
```

### 15.3 Consensus Weight Calculation

```
Calculate Consensus Score:

1. Extract metrics
   ├─ Execution metrics (latency, cost, success rate)
   ├─ Validation metrics (validation_score, risk_score)
   ├─ Security metrics (findings count, severity)
   └─ User feedback (ratings, success feedback)

2. Normalize metrics to 0.0-1.0 scale
   └─ Correctness: validation_score
   └─ Latency: 1.0 / (1.0 + latency_ms/1000)
   └─ Cost: 1.0 / (1.0 + cost_per_call)
   └─ Safety: 1.0 - (findings / max_findings)
   └─ Resilience: success_rate

3. Apply weights
   weighted = Σ(metric × weight)
   └─ Weights sum to 1.0
   └─ Can adjust per-task

4. Apply temporal decay
   decayed = weighted × exp(-decay_factor × age_days)

5. Evaluate constraints
   └─ If violates hard constraints: score = 0.0
   └─ If meets preferred constraints: boost score

6. Return
   └─ Final consensus weight (0.0-1.0)
   └─ Component scores
   └─ Evaluators used
```

---

## Part 16: Security & Provenance

### 16.1 Execution Provenance

Every tool execution is logged with complete context:

```python
{
    'call_id': 'unique_identifier',
    'tool_id': 'nmt_translator',
    'version': '2.1.0',
    'timestamp': '2025-11-20T13:45:00Z',
    'input_hash': 'sha256_hash_of_input',
    'output_hash': 'sha256_hash_of_output',
    'execution_time_ms': 150,
    'metrics': {
        'latency_ms': 150,
        'tokens_used': 250,
        'cost': 0.0005,
        'success': True
    },
    'sandbox_config': {
        'network': 'restricted',
        'filesystem': 'readonly',
        'environment': 'whitelisted'
    }
}
```

### 16.2 Lineage Tracking

Tool evolution is tracked in lineage graphs:

```yaml
lineage:
  ancestor_tool_id: "nmt_translator_v1"
  mutation_reason: "improved latency under load"
  commits:
    - id: "c9a2f8b"
      message: "Optimize batch processing for parallel requests"
      timestamp: "2025-10-15T12:30:00Z"
      author: "system"
    - id: "d4e3c1a"
      message: "Add caching layer for common phrases"
      timestamp: "2025-10-16T09:15:00Z"
      author: "auto_optimizer"
```

### 16.3 Sandboxing

Tool execution is sandboxed with configurable policies:

```python
sandbox_config = {
    'network': 'restricted',  # No external network
    'filesystem': 'readonly',  # Read-only access
    'environment': 'whitelisted',  # Only specified env vars
    'resource_limits': {
        'memory_mb': 512,
        'cpu_time_seconds': 30,
        'max_output_bytes': 1000000
    }
}
```

---

## Part 17: Future Vision - Forge Mesh

### 17.1 Distributed Forge Network

The architecture is designed for multi-forge networks:

```
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  Forge A     │◄──────►│  Forge B     │◄──────►│  Forge C     │
│  (Edge)      │        │  (Cloud)     │        │  (Local)     │
└──────────────┘        └──────────────┘        └──────────────┘
       ▲                      ▲                        ▲
       │                      │                        │
       └──────────────────────┴────────────────────────┘
              Shared RAG Memory Layer
         (Semantic search across all forges)
```

### 17.2 Mesh Features (Future)

**Phase 2**: Cross-forge Communication
- [ ] Forge discovery protocol
- [ ] Tool query federation
- [ ] Consensus score propagation
- [ ] Lineage graph synchronization

**Phase 3**: Mesh Optimization
- [ ] Multi-forge tool routing
- [ ] Load balancing
- [ ] Geographic distribution
- [ ] Fault tolerance

**Phase 4**: Autonomous Evolution
- [ ] Automatic specialization replication
- [ ] Self-healing mechanisms
- [ ] Adaptive mesh topology
- [ ] Economic optimization

---

## Part 18: Integration Points

### 18.1 Integration with Existing Systems

The Forge system integrates with:

```
┌─────────────────────────────┐
│ Chat CLI (chat_cli.py)      │
│ └─ User conversation        │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ Forge System                │
│ ├─ Registry (RAG-backed)    │
│ ├─ Director (orchestration) │
│ ├─ Validator (multi-stage)  │
│ ├─ Consensus (scoring)      │
│ └─ Optimizer (variant test) │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ RAG Memory (rag_memory.py)  │
│ └─ Semantic search/storage  │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ LLM Clients                 │
│ ├─ Anthropic API            │
│ ├─ Ollama local             │
│ ├─ Azure OpenAI             │
│ └─ LM Studio                │
└─────────────────────────────┘
```

### 18.2 Tool Integration

Tools can be:
- **MCP servers** (via ForgeRuntime)
- **Python executables** (via NodeRuntime)
- **OpenAPI endpoints** (via OpenAPITool)
- **Workflows** (via WorkflowBuilder)
- **LLM calls** (via LLMClientFactory)

---

## Part 19: Performance Characteristics

### 19.1 Scalability

| Operation | Complexity | Latency |
|-----------|-----------|---------|
| Tool registration | O(1) | <100ms |
| Registry query | O(log n) semantic search | 50-200ms |
| Tool execution | O(1) + network | 100ms - 30s |
| Validation pipeline | O(n stages) | 5-60 min |
| Consensus scoring | O(m metrics) | <50ms |

### 19.2 Memory Usage

- **Registry cache**: ~10MB per 1000 tools
- **RAG memory**: ~100MB-1GB depending on storage
- **Runtime instances**: ~50MB per MCP server
- **Validation artifacts**: ~500MB during validation

---

## Part 20: Summary & Key Takeaways

### 20.1 Core Strengths

1. **Semantic Tool Discovery**: RAG-powered search finds the right tool
2. **Multi-LLM Hardening**: Consensus validation across models
3. **Integration Testing**: Real workflow execution validates tools
4. **Complete Provenance**: Every execution tracked with full context
5. **Automatic Optimization**: Tools improve through execution
6. **Production-Ready**: Sandboxing, security, monitoring

### 20.2 Unique Features

- **Consensus Scoring**: Multi-dimensional metrics with temporal decay
- **Trust Levels**: Automatic classification (core/third_party/experimental)
- **Lineage Tracking**: Full evolution history for all tools
- **Dynamic Optimization**: Weights adjust per-task constraints
- **Tree-Shaking Build**: Minimal standalone executables
- **Mesh Architecture**: Designed for distributed networks

### 20.3 Implementation Status

- ✅ Core forge components
- ✅ RAG integration
- ✅ Validation pipeline
- ✅ Consensus engine
- ✅ Integration optimizer
- ⏳ Cross-forge communication (future)
- ⏳ Distributed mesh (future)

---

## Conclusion

The Forge build system represents a sophisticated approach to tool management that combines:
- **Semantic search** (RAG integration)
- **Multi-model consensus** (validation)
- **Performance optimization** (integration testing)
- **Complete auditability** (provenance tracking)
- **Automatic evolution** (continuous improvement)

This architecture provides a foundation for self-improving, distributed AI tool systems that can scale from a single forge to a global mesh of collaborating forges.

