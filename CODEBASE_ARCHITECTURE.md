# Code Evolver - Complete Codebase Architecture Analysis

## Executive Summary

**mostlylucid-dse** (Directed Synthetic Evolution) is a sophisticated, self-improving AI workflow system that generates, executes, evaluates, and optimizes Python code using multiple LLM models. The system is designed to learn from every execution, auto-evolve based on performance, and create specialist tools.

### Key Architecture Principles
- **Executable Ground Truth**: Store tested, executable code rather than metadata
- **Self-Learning**: Builds semantic library from successful patterns
- **Auto-Evolution**: Automatically improves when quality drops
- **Multi-tier Optimization**: Balance cost, speed, quality based on context
- **RAG-Powered**: Semantic search finds similar artifacts

---

## Part 1: Code Generation Architecture

### 1.1 Main Entry Points

#### Primary CLI: `chat_cli.py` (377KB)
- **Purpose**: Interactive conversation-based code evolution
- **Key Functions**:
  - Task understanding via LLM classification
  - Workflow planning with overseer model
  - Code generation with appropriate tools
  - Automatic testing and validation
  - Performance optimization (4 levels!)
  - Conversation memory with auto-summarization

#### Orchestrator: `orchestrator.py`
- Lower-level workflow management
- Manages registry, node runners, evaluators
- Entry point for programmatic use

#### Workflow System: `src/workflow_spec.py`
- Declarative workflow specifications
- Supports: LLM_CALL, PYTHON_TOOL, SUB_WORKFLOW, EXISTING_TOOL steps
- Stored in RAG for reuse and evolution

### 1.2 Code Generation Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ 1. Task Understanding                                   │
│    └─ LLM classifies task into categories               │
│       (optimization, generation, testing, etc.)         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Overseer Planning                                    │
│    └─ Parallel execution strategy                       │
│       Consults RAG for similar patterns                 │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Tool Selection                                       │
│    └─ RAG-based tool discovery                          │
│       Semantic search for relevant tools                │
│       Specification-based selection                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Code Generation                                      │
│    ├─ Generate Python code                              │
│    ├─ Generate tests (BDD, pytest)                      │
│    ├─ Generate documentation                            │
│    └─ Generate workflows                                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Execution & Testing                                  │
│    ├─ Run generated code                                │
│    ├─ Run unit/integration tests                        │
│    ├─ BDD specification tests                           │
│    └─ Performance benchmarking                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Multi-Level Optimization                             │
│    ├─ LOCAL: qwen2.5-coder (free, 10-20% improvement)   │
│    ├─ CLOUD: GPT-4/Claude (expensive, 20-40%)           │
│    ├─ DEEP: Claude Sonnet (5-50% improvement)           │
│    └─ BATCH: Overnight optimization runs                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 7. Learning & Evolution                                 │
│    ├─ Store in RAG (semantic embeddings)                │
│    ├─ Track performance metrics                         │
│    ├─ Auto-detect performance drift                     │
│    └─ Trigger evolution if needed                       │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Key Generation-Related Files

| File | Purpose | Key Classes |
|------|---------|------------|
| `src/auto_evolver.py` | Automatic evolution engine | `AutoEvolver` |
| `src/tool_split_detector.py` | Detects tool version splits | `ToolSplitDetector`, `ToolSpecification` |
| `src/workflow_spec.py` | Workflow specifications | `WorkflowSpec`, `WorkflowStep`, `StepType` |
| `src/tools_manager.py` | Tool registry & management | `Tool`, `ToolType`, `ToolsManager` |
| `src/hierarchical_evolver.py` | Hierarchical evolution | `HierarchicalEvolver` |
| `src/fine_tuning_evolver.py` | Fine-tuning specialist models | `FineTuningEvolver` |
| `tools/llm/code_optimizer.yaml` | Main optimization tool definition | Multi-level optimization |

---

## Part 2: Tool Structure and Format

### 2.1 Tool Definition Format

Tools are defined in YAML with structured metadata. Example from `tools/llm/code_optimizer.yaml`:

```yaml
name: "Code Optimizer"
type: "llm"
version: "1.0.0"
description: "Comprehensive code optimization with hierarchical levels"

llm:
  model_key: "escalation"
  system_prompt: |
    [Detailed prompt for the LLM role]
  temperature: 0.4

tags: ["optimization", "performance", "refactoring"]

constraints:
  max_memory_mb: 2048
  max_execution_time_ms: 600000
  max_cost_per_optimization: 5.0

metadata:
  speed_tier: "slow"
  cost_tier: "variable"
  reliability: "high"
  
  optimization_levels:
    - name: "local"
      model_key: "escalation"
      cost_usd: 0.0
      expected_improvement: 0.10
      
    - name: "cloud"
      model_key: "cloud_optimizer"
      cost_usd: 0.50
      expected_improvement: 0.30

workflow:
  steps:
    - id: "1_profile_baseline"
      action: "profile_code"
      tool: "performance_profiler"
```

### 2.2 Tool Types (from `src/tools_manager.py`)

```python
class ToolType(Enum):
    # Execution
    FUNCTION = "function"
    LLM = "llm"
    WORKFLOW = "workflow"
    COMMUNITY = "community"
    PROMPT_TEMPLATE = "prompt_template"
    DATA_PROCESSOR = "data_processor"
    VALIDATOR = "validator"
    OPENAPI = "openapi"
    EXECUTABLE = "executable"
    CUSTOM = "custom"
    
    # Storage & Data
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    VECTOR_STORE = "vector_store"
    API_CONNECTOR = "api_connector"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    
    # Optimization
    FINE_TUNED_LLM = "fine_tuned_llm"
    TRAINING_PIPELINE = "training_pipeline"
    OPTIMIZER = "optimizer"
```

### 2.3 Tool Directory Structure

```
tools/
├── custom/              - Custom workflow tools (git, github, http_server, ask_user)
├── debug/               - Debugging & validation (bugcatcher, validators, static analysis)
├── executable/          - General-purpose executables
├── fixer/               - Bug fixing & error correction
├── llm/                 - LLM-based tools
├── openapi/             - API-related tools
├── optimization/        - Code optimization tools
├── perf/                - Performance testing & profiling tools
├── index.json           - Tool registry with metadata
└── TOOL_ORGANIZATION.md - Comprehensive tool documentation
```

### 2.4 Tool Metadata in Registry

Each tool is indexed in `tools/index.json` with comprehensive metadata:

```json
{
  "tool_id": "code_optimizer",
  "name": "Code Optimizer",
  "version": "1.0.0",
  "metadata": {
    "performance": {
      "execution_time_ms": 7.8,
      "memory_usage_kb": 1280,
      "regression_evaluation": {
        "score": 85,
        "recommendation": "ACCEPT"
      }
    },
    "static_analysis": {
      "complexity": {"average_complexity": 3.2, "grade": "B"},
      "security": {"total_issues": 0},
      "correctness": {"syntax_valid": true},
      "code_quality": {"documentation_ratio": 0.75}
    },
    "source": "<source code>",
    "preconditions": [
      "Code must be syntactically valid Python",
      "Input must be non-empty"
    ],
    "postconditions": [
      "Returns optimized code",
      "Performance improvement >= 10%"
    ],
    "behavioral_contracts": [
      "Must handle empty input gracefully",
      "Must preserve function semantics"
    ]
  }
}
```

---

## Part 3: Testing Infrastructure

### 3.1 Test Organization

```
tests/
├── conftest.py              - Pytest fixtures (BugCatcher, FixTemplateStore, etc.)
├── integration/             - Integration tests
├── test_*.py (50+ files)    - Unit tests for each module
│
├── Core Infrastructure Tests:
│   ├── test_config_manager.py
│   ├── test_config_unified.py
│   ├── test_integration.py
│   ├── test_monitoring_integration.py
│   ├── test_multi_backend.py
│   └── test_backend_checker.py
│
├── Tool Management Tests:
│   ├── test_hierarchical_evolution.py
│   ├── test_workflow_chain.py
│   ├── test_specification_reuse.py
│   ├── test_tool_characterization.py
│   ├── test_tool_interceptors.py
│   └── test_fix_template_store.py (26,573 lines!)
│
├── Performance Tests:
│   ├── test_profiling.py
│   ├── test_performance_auditor.py
│   ├── test_perfanalyzer.py
│   ├── test_optimized_perf_tracker.py
│   └── test_monitoring_integration.py
│
├── RAG & Learning Tests:
│   ├── test_rag_memory.py
│   ├── test_rag_cluster_optimizer.py
│   └── test_rag_retry.py
│
└── Tool-Specific Tests:
    ├── test_http_content_fetcher.py
    ├── test_http_rest_client.py
    ├── test_cron_querier.py
    ├── test_debug_store.py
    ├── test_bugcatcher.py
    ├── test_buganalyzer.py
    └── test_fake_data_generator.py
```

### 3.2 Test Infrastructure Components

#### Fixtures (`conftest.py`)
```python
@pytest.fixture
def bugcatcher_instance():
    """Create a BugCatcher instance for testing."""
    
@pytest.fixture
def fix_template_store(temp_dir):
    """Create a FixTemplateStore instance for testing."""

@pytest.fixture
def sample_exception_data():
    """Sample exception data for testing."""

@pytest.fixture
def sample_performance_data():
    """Sample performance data for testing."""

@pytest.fixture
def mock_loki_exception_response():
    """Mock Loki API response for exception queries."""
```

#### Test Types Supported

1. **Unit Tests**: Test individual functions/classes
   - Example: `test_config_manager.py`
   - Uses pytest fixtures for setup/teardown

2. **Integration Tests**: Test component interactions
   - Example: `test_integration.py`
   - Full workflow testing with progress display

3. **Performance Tests**: Test performance metrics
   - Benchmark tools with timeit_optimizer
   - Track memory usage, execution time
   - Detect regressions

4. **Regression Tests**: Prevent performance degradation
   - Uses `performance_regression_evaluator.py`
   - LLM-based assessment of trade-offs

5. **BDD Tests**: Behavior-Driven Development
   - Uses `behave_test_generator.py`
   - Creates Gherkin-style specifications
   - Translates to pytest assertions

6. **Property-Based Tests**: Pynguin integration
   - Automatic test generation with mutation analysis
   - Assertion-based mutation testing

### 3.3 Testing Key Classes

| Module | Key Test Classes |
|--------|------------------|
| `src/bugcatcher.py` | Exception tracking, severity classification |
| `src/rag_memory.py` | Semantic search, artifact storage, quality ranking |
| `src/tool_split_detector.py` | Tool split detection with test/spec comparison |
| `src/fix_template_store.py` | Fix pattern storage and RAG search |
| `src/optimized_perf_tracker.py` | Performance tracking with minimal overhead |

### 3.4 Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config_manager.py

# Run with coverage
pytest --cov=src tests/

# Run integration tests only
pytest tests/integration/

# Run with verbose output
pytest -v
```

---

## Part 4: Overall Architecture (9 Layers)

### Layer 1: Core Storage - RAG Memory
- **ChromaDB**: Vector embeddings for semantic search
- **SQLite**: Metadata structured queries
- **Artifact Types**: FUNCTION, WORKFLOW, TOOL, TEST, CODE_FIX, DEBUG_DATA, PERF_DATA
- **Quality Tracking**: Test results, execution metrics
- **Reuse Tracking**: Usage count, last_used timestamps

### Layer 2: Learning & Evolution
- **AutoEvolutionEngine**: Monitors performance drift
- **ToolSplitDetector**: Detects version divergence
- **HierarchicalLearning**: Parent learns from child results
- **FineTuningEvolver**: Creates specialist models

### Layer 3: Multi-Tier Optimization
- **LOCAL**: qwen2.5-coder (free, 10-20% improvement)
- **CLOUD**: GPT-4/Claude (expensive, 20-40%)
- **DEEP**: Claude Sonnet (comprehensive, 50%+)
- **BATCH**: Overnight optimization runs

### Layer 4: Workflow Engine
- **Workflow Spec**: Declarative specifications
- **Workflow Builder**: Constructs workflows
- **Workflow Distributor**: Parallel execution
- **Workflow Tracker**: Execution history

### Layer 5: Tool Management
- **ToolsManager**: Registry and retrieval
- **VersionedToolManager**: Version tracking
- **ToolDiscovery**: Semantic search
- **ToolInterceptors**: Auto-wrap tool calls

### Layer 6: Code Generation
- **Test Generation**: BDD specs, pytest, Pynguin
- **Code Generation**: Python, workflows
- **Documentation**: Auto-generated docs
- **Specification Validation**: Contract verification

### Layer 7: Execution & Evaluation
- **NodeRunner**: Execute generated code
- **Evaluator**: Quality assessment
- **BugCatcher**: Exception tracking
- **Performance Tracking**: Metrics collection

### Layer 8: Conversation & Context
- **ConversationManager**: Multi-chat history
- **SummarizationSystem**: Auto-summarization
- **InteractionMemory**: Context preservation
- **DebugStore**: Debugging information

### Layer 9: CLI & Interface
- **chat_cli.py**: Interactive conversation
- **orchestrator.py**: Programmatic API
- **Slack/HTTP Integration**: External interfaces

---

## Part 5: Where Code Contracts Would Best Fit

### 5.1 Current Contract Support

The system already has **foundational contract support** in `tool_split_detector.py`:

```python
@dataclass
class ToolSpecification:
    """Represents a tool's specification."""
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    preconditions: List[str]          # Pre-conditions
    postconditions: List[str]         # Post-conditions
    error_cases: List[str]            # Error handling
    performance_requirements: Dict[str, Any]
    behavioral_contracts: List[str]   # Behavioral contracts
```

### 5.2 Integration Points for Contracts

#### A. Tool Generation Phase
**File**: `chat_cli.py`, `src/auto_evolver.py`

**Enhancement**: When generating new tools:
1. **Generate Contract Specifications**
   - Parse requirements for contracts
   - Extract preconditions, postconditions
   - Define behavioral contracts
   - Specify performance requirements

2. **Contract-Driven Test Generation**
   - Generate tests from contracts
   - Use contracts to guide property testing
   - Validate contract compliance

#### B. Tool Registry & Metadata
**File**: `tools/index.json`, `src/tools_manager.py`

**Enhancement**: Extend Tool metadata:
```json
{
  "contracts": {
    "preconditions": [
      "Input must be valid JSON",
      "file_path must point to existing file"
    ],
    "postconditions": [
      "Returns non-null result",
      "Result satisfies input_schema"
    ],
    "invariants": [
      "Tool state remains consistent",
      "No side effects outside scope"
    ],
    "performance_slas": [
      "execution_time_ms < 1000",
      "memory_usage_kb < 500"
    ]
  }
}
```

#### C. Test Suite Validation
**File**: `src/tool_split_detector.py`

**Enhancement**: Contract-based split detection:
1. **Contract Divergence Analysis**
   - Compare preconditions across versions
   - Detect breaking contract changes
   - Flag incompatible versions

2. **Contract-Driven Migration**
   - Automatic adapter generation for contract changes
   - Migration guides from old contracts to new

#### D. Execution & Validation
**File**: `src/tool_interceptors.py`, `src/node_runner.py`

**Enhancement**: Runtime contract verification:
1. **Precondition Checking**
   - Validate inputs before execution
   - Clear error messages for violations
   - Fallback handling

2. **Postcondition Verification**
   - Validate outputs after execution
   - Detect contract violations
   - Track violations for evolution

3. **Invariant Monitoring**
   - Track system invariants
   - Detect violations that trigger evolution
   - Performance SLA monitoring

#### E. RAG-Based Contract Learning
**File**: `src/rag_memory.py`

**Enhancement**: Contract-based artifact search:
1. **Contract Similarity Search**
   - Find tools with similar contracts
   - Discover contract patterns
   - Reuse working contracts

2. **Contract Evolution Tracking**
   - Store contract history
   - Track successful contract patterns
   - Learn from contract violations

#### F. Optimization Integration
**File**: `tools/llm/code_optimizer.yaml`, `src/system_optimizer.py`

**Enhancement**: Contract-aware optimization:
1. **Contract-Preserving Optimization**
   - Only accept optimizations that maintain contracts
   - Flag contract-breaking changes
   - Enforce contract compliance

2. **Contract Relaxation**
   - Suggest contract relaxation for better performance
   - Get user approval for changes
   - Document trade-offs

### 5.3 Recommended Implementation Plan

#### Phase 1: Contract Definition System (Immediate)
**Files to Create/Modify**:
- `src/contract_parser.py` - Parse contracts from docstrings, YAML
- `src/contract_specification.py` - Contract dataclasses and utilities
- `src/contract_validator.py` - Runtime contract validation
- `tools/fixer/contract_validator.yaml` - Tool for checking contracts

**Key Features**:
- Extract contracts from function docstrings
- Parse contract metadata from YAML
- Define contract types (precondition, postcondition, invariant, SLA)

#### Phase 2: Contract-Driven Code Generation (Week 2)
**Files to Enhance**:
- `chat_cli.py` - Extract contract requirements from prompts
- `src/prompt_generator_tool.py` - Generate contract specifications
- `src/test_tool_generator.py` - Generate tests from contracts

**Key Features**:
- Contract-driven test generation
- Property-based testing from contracts
- Contract compliance in generated code

#### Phase 3: Contract Validation & Monitoring (Week 2-3)
**Files to Create/Modify**:
- `src/tool_interceptors.py` - Add ContractValidationInterceptor
- `src/contract_monitor.py` - Track contract violations
- `tools/debug/contract_validator.yaml` - Contract checking tool

**Key Features**:
- Runtime precondition checking
- Postcondition verification
- SLA monitoring
- Violation reporting

#### Phase 4: Contract-Based Evolution (Week 3-4)
**Files to Enhance**:
- `src/tool_split_detector.py` - Contract-based split detection
- `src/auto_evolver.py` - Contract-aware evolution
- `src/rag_memory.py` - Contract-based search

**Key Features**:
- Detect contract-breaking changes
- Contract-preserving optimization
- Adaptive contract negotiation

### 5.4 Benefits of Contract Integration

| Benefit | Implementation |
|---------|-----------------|
| **Automatic Test Generation** | Generate tests from contracts |
| **Better Tool Discovery** | Find tools by contract similarity |
| **Version Management** | Detect breaking contract changes |
| **Performance Guarantees** | Track SLA compliance |
| **Self-Healing Code** | Auto-fix contract violations |
| **Safer Evolution** | Only optimize while preserving contracts |
| **Better Documentation** | Contracts as executable specs |
| **Bug Prevention** | Catch violations early |

### 5.5 Example Contract Implementation

```python
# In tool YAML
contracts:
  preconditions:
    - "input_data must be non-empty"
    - "batch_size must be > 0"
    - "output_path must be writable directory"
    
  postconditions:
    - "output file exists and is valid JSON"
    - "output_records > 0"
    
  invariants:
    - "No data loss during processing"
    - "Idempotent: running twice gives same result"
    
  performance_slas:
    - "execution_time_ms < 5000"
    - "memory_usage_kb < 512000"

# Auto-generated test
@contract.precondition("input_data must be non-empty")
@contract.postcondition("output file exists and is valid JSON")
@contract.sla("execution_time_ms < 5000")
def test_contract_compliance():
    result = call_tool(empty_input)
    # Should raise PreconditionViolation
    assert isinstance(result, PreconditionViolation)
```

---

## Key Files Summary Table

| Category | File | Lines | Purpose |
|----------|------|-------|---------|
| **Core** | `chat_cli.py` | 377KB | Main CLI entry point |
| | `orchestrator.py` | ~200 | Programmatic orchestration |
| **Generation** | `src/auto_evolver.py` | ~300 | Automatic evolution |
| | `src/workflow_spec.py` | ~300 | Workflow definitions |
| **Tool Management** | `src/tools_manager.py` | ~600 | Tool registry |
| | `src/tool_split_detector.py` | ~663 | Contract-aware split detection |
| **Contracts** | `src/tool_split_detector.py` | ~663 | ToolSpecification with contracts |
| **Testing** | `tests/conftest.py` | ~200 | Test fixtures |
| | `tests/test_*.py` | 50+ files | 400+ total test files |
| **Tools** | `tools/*/` | 200+ YAML files | Executable tool specs |
| **RAG** | `src/rag_memory.py` | ~500 | Semantic storage |
| **Performance** | `tools/perf/*.py` | ~2000 | Performance testing tools |

---

## Conclusion

The mostlylucid-dse system is architecturally sophisticated with:

1. **Clear code generation pipeline** from task understanding → generation → testing → optimization
2. **Well-structured tool system** using YAML specs with metadata
3. **Comprehensive testing infrastructure** supporting unit, integration, performance, and property-based tests
4. **9-layer architecture** from storage to CLI
5. **Existing contract foundations** in ToolSpecification that can be extended

**Contracts would fit naturally** into:
- Tool registry (metadata)
- Test generation (contract-driven)
- Tool discovery (contract-based search)
- Evolution (contract-aware optimization)
- Validation (runtime checking)
- Version management (contract-based split detection)

The system is positioned to support comprehensive code contracts as a major evolution.

