# Code Evolver - Complete Codebase Exploration Report

## 1. PROJECT OVERVIEW

### What is Code Evolver?
A self-optimizing, self-evolving multi-LLM workflow system that:
- Generates Python code using multiple LLM models
- Automatically tests and validates generated code
- Optimizes workflows through iterative improvement
- Learns from successful solutions via RAG memory
- Distributes workflows across different platforms (Cloud, Edge, Embedded)

### Key Innovation: Digital Synthetic Evolution (DSE)
The system stores **executable ground truth** (tested code) rather than metadata, learning from real execution metrics.

---

## 2. PROJECT STRUCTURE

```
mostlylucid.dse/
├── code_evolver/                 # Main application
│   ├── src/                      # Core source code (91 Python modules)
│   │   ├── chat_cli.py          # Interactive CLI interface
│   │   ├── tools_manager.py      # Tool registry and management
│   │   ├── workflow_spec.py      # Workflow specification format
│   │   ├── workflow_builder.py   # Convert overseer output to workflows
│   │   ├── workflow_distributor.py # Export workflows for different platforms
│   │   ├── auto_evolver.py       # Automatic code improvement engine
│   │   ├── http_server_tool.py   # Flask-based HTTP server for workflows
│   │   ├── config_manager.py     # Configuration management
│   │   ├── registry.py           # File-based registry for nodes
│   │   └── [80+ other modules]   # RAG, LLM clients, tools, optimization, etc.
│   │
│   ├── tools/                    # Tool definitions
│   │   ├── executable/           # Python-based tools (100+ tools)
│   │   ├── llm/                  # LLM-based prompts for specialized tasks
│   │   ├── custom/               # Custom implementations
│   │   └── openapi/              # OpenAPI tool definitions
│   │
│   ├── examples/                 # Example workflows and demonstrations
│   ├── tests/                    # Test suite
│   ├── workflows/                # Saved workflow definitions
│   ├── rag_memory/               # RAG database for semantic search
│   └── config*.yaml              # Configuration files (Ollama, Anthropic, Azure, OpenAI)
│
├── registry/                     # File-based registry for nodes
├── test_content/                 # Test data
└── docs/                         # Documentation

KEY FILES FOR FLASK INTEGRATION:
- code_evolver/src/http_server_tool.py  ← Flask-based HTTP server (ALREADY EXISTS!)
- code_evolver/chat_cli.py               ← CLI entry point with main loop
- code_evolver/src/tools_manager.py      ← Tool registry system
- code_evolver/src/workflow_spec.py      ← Workflow data structures

---

## 3. CORE COMPONENTS & MAIN MODULES

### 3.1 Tools Manager (src/tools_manager.py)
**Purpose**: Central registry for all reusable tools/components

**Key Classes**:
- `Tool`: Represents a reusable tool with metadata
- `ToolsManager`: Manages tool registration, discovery, and execution
- `ToolType` (Enum): Function, LLM, Workflow, Community, Database, etc.

**Main Methods**:
- `register_tool()` - Add tool to registry
- `get_tool()` - Retrieve tool by name
- `search_tools()` - Semantic search via RAG
- `get_tool_by_name()` - Direct lookup
- `list_tools()` - List all available tools

**Example Tools in Registry** (100+ available):
```
Executable Tools:
- http_rest_client.py           # JSON REST API calls
- bandit_security.yaml           # Security scanning
- behave_test_generator.py       # BDD test generation
- black_formatter.yaml           # Code formatting
- buffer.py                      # Text buffering
- circular_import_fixer.py       # Python import fixing

LLM Tools (Prompts):
- content_generator.yaml         # General content generation
- code_optimizer.yaml            # Code optimization
- code_reviewer.yaml             # Code review
- doc_generator.yaml             # Documentation generation
- llm_fake_data_generator.yaml  # Test data generation
```

### 3.2 Workflow System

#### Workflow Specification (src/workflow_spec.py)
Defines declarative workflow format (JSON-serializable):

```python
@dataclass
class WorkflowSpec:
    workflow_id: str
    name: str
    version: str
    description: str
    inputs: List[WorkflowInput]
    outputs: List[WorkflowOutput]
    steps: List[WorkflowStep]
    
@dataclass
class WorkflowStep:
    step_id: str
    step_type: StepType  # LLM_CALL, PYTHON_TOOL, SUB_WORKFLOW, EXISTING_TOOL
    tool_name: Optional[str]
    input_mapping: Dict[str, Any]
    output_mapping: Dict[str, Any]
```

**StepTypes**:
1. **LLM_CALL** - Call LLM tool (content_generator, translator, etc.)
2. **PYTHON_TOOL** - Execute Python function (generated or existing)
3. **SUB_WORKFLOW** - Execute nested workflow
4. **EXISTING_TOOL** - Use registered tool from registry

#### Workflow Builder (src/workflow_builder.py)
Converts overseer LLM output → WorkflowSpec

**Process**:
1. Extracts JSON from overseer's text output
2. Parses step definitions and tool selections
3. Maps inputs/outputs between steps
4. Creates executable WorkflowSpec object
5. Stores in RAG for reuse

#### Workflow Distributor (src/workflow_distributor.py)
Exports workflows for different platforms:

**Platforms**:
- **CLOUD**: Full workflow + cloud LLM APIs (GPT-4, Claude)
- **EDGE**: Lightweight workflow + local Ollama
- **EMBEDDED**: Pure Python code, no LLMs (air-gapped IoT)
- **WASM**: WebAssembly builds (future)

### 3.3 LLM Client System

**Supported Backends**:
- Ollama (local, free)
- Anthropic (Claude)
- OpenAI (GPT-3.5, GPT-4)
- Azure OpenAI
- LMStudio (local)

**Client Classes**:
- `llm_client_factory.py`: Factory pattern for creating clients
- `anthropic_client.py`: Anthropic SDK integration
- `openai_client.py`: OpenAI integration
- `ollama_client.py`: Ollama integration
- `azure_client.py`: Azure OpenAI integration

**Usage**:
```python
from src.llm_client_factory import LLMClientFactory

client = LLMClientFactory.create(
    config_manager,
    backend='anthropic'
)
response = client.generate(model='claude-3-sonnet', prompt='...')
```

### 3.4 RAG Memory System

**Hybrid RAG Architecture**:
- **Vector DB** (Qdrant): Semantic search of artifacts
- **SQLite**: Metadata and structured queries
- **File Storage**: Actual code/workflow files

**Main Classes**:
- `qdrant_rag_memory.py`: Qdrant vector database integration
- `rag_memory.py`: Core RAG interface
- `pattern_clusterer.py`: Groups similar solutions

**Artifact Types**:
```python
class ArtifactType(Enum):
    FUNCTION = "function"              # Reusable Python function
    WORKFLOW = "workflow"              # Complete workflow
    TEST = "test"                      # Test code
    TOOL = "tool"                      # Custom tool
    PROMPT = "prompt"                  # Reusable prompt
    DATASET = "dataset"                # Training/test data
```

### 3.5 Configuration System (src/config_manager.py)

**Supports**:
- YAML-based configuration
- Multiple backend configurations
- Model tier management
- Execution policies
- Testing parameters
- Auto-evolution settings

**Config Files**:
- `config.yaml` - Main config
- `config.anthropic.yaml` - Anthropic-specific
- `config.openai.yaml` - OpenAI-specific
- `config.local.yaml` - Local Ollama setup
- `model_tiers.yaml` - Model capability tiers

---

## 4. WORKFLOW EXECUTION FLOW

### End-to-End Process

```
User Input (Chat)
    ↓
[1] Task Evaluation (task_evaluator.py)
    - Classify task type
    - Determine complexity
    ↓
[2] Tool Selection (RAG semantic search)
    - Search for specialized tools
    - If found: Use cached solution
    - If not: Proceed to generation
    ↓
[3] Overseer Planning (overseer_llm.py)
    - Strategic planning
    - Determine approach
    - Select execution model
    ↓
[4] Workflow Generation (workflow_builder.py)
    - Parse overseer output
    - Define workflow steps
    - Map inputs/outputs
    ↓
[5] Code Generation
    - Generator LLM (codellama/qwen) creates code
    - Returns JSON structure with:
      * code: actual Python code
      * description: human-readable explanation
      * tags: semantic tags
    ↓
[6] Parsing & Validation (interface_validator.py)
    - Extract JSON from LLM response
    - Validate Python syntax
    - Clean code (remove markdown, etc.)
    ↓
[7] Test Generation (test_tool_generator.py)
    - Generate unit tests
    - BDD-style specs (via behave)
    ↓
[8] Execution & Validation
    - Run code with test harness
    - Check: syntax, runtime, test results
    - Measure: performance, resource usage
    ↓
[9] Quality Evaluation
    If PASS:
      - Save to registry (file-based)
      - Store in RAG (with embeddings)
      - Tag with metadata
    If FAIL:
      - Escalate to higher-tier LLM
      - Up to 3 escalation attempts
      - Log error for learning
    ↓
[10] Auto-Evolution (auto_evolver.py)
    - Monitor execution metrics
    - Detect performance drift
    - Trigger optimization if needed
    - Attempt multi-tier fixes
```

### Escalation Strategy
When code fails tests:

```
Tier 1: Fast/Free (Ollama qwen2.5-coder:3b)
  ↓ if failed
Tier 2: Better (Ollama codellama:7b)
  ↓ if failed
Tier 3: Best (Ollama deepseek-coder:6.7b or cloud Claude)
  ↓ if still failed
Give up & report to user
```

---

## 5. EXISTING WEB INTERFACE

### HTTP Server Tool (src/http_server_tool.py)
**IMPORTANT: Flask-based HTTP server ALREADY EXISTS!**

**Features**:
```python
class HTTPServerTool:
    def __init__(host="0.0.0.0", port=8080, enable_cors=True)
    def add_route(path, methods, handler, response_type, description)
    def add_workflow_route(path, methods, workflow_id, workflow_executor)
    def start(blocking=False)  # Non-blocking background server
    def stop()
    def list_routes()
    def get_server_info()
```

**Supported Response Types**:
- `json`: Returns JSON response
- `html`: Returns HTML response

**Example Usage**:
```python
from src.http_server_tool import HTTPServerTool

server = HTTPServerTool(host="127.0.0.1", port=8080)

# Add JSON API endpoint
server.add_route(
    path="/api/generate",
    methods=["POST"],
    handler=lambda req: {"result": "generated"},
    response_type="json"
)

# Add HTML endpoint
server.add_route(
    path="/",
    methods=["GET"],
    handler=lambda req: "<h1>Welcome</h1>",
    response_type="html"
)

server.start(blocking=False)  # Non-blocking!
```

**WorkflowHTTPAdapter**:
Bridges workflow system with HTTP server:
```python
adapter = WorkflowHTTPAdapter(workflow_manager, tools_manager)
server = adapter.create_server("main_api", port=8080)
adapter.register_workflow_endpoint(
    "main_api",
    "my_workflow",
    "/api/process"
)
adapter.start_server("main_api")
```

**Existing Demo**:
See: `examples/http_server_demo.py` - Full working example!

---

## 6. CLI INTERFACE (chat_cli.py)

### Main Components

**Chat Loop**:
- Interactive REPL with command history
- Prompt toolkit support for cross-platform compatibility
- Rich console output with panels, tables, syntax highlighting

**Key Commands**:
- Regular chat: Type your request
- `/help`: Show available commands
- `/save`: Save workflow
- `/load`: Load workflow
- `/export`: Export to JSON
- `/history`: Show chat history

**Session Management**:
- Maintains conversation context
- Stores history in `.code_evolver_history`
- Auto-summarization for long conversations
- State preservation across sessions

**Key Classes**:
- `SafeConsole`: Unicode-safe output (Windows compatible)
- `LogPanel`: Display last N log messages
- `ChatSession`: Manages conversation state

### Main Loop Flow
```python
while True:
    user_input = get_user_input()
    
    if is_command(user_input):
        handle_command(user_input)
    else:
        # Process as task
        task_evaluator.classify(user_input)
        tools = rag_memory.search(user_input)
        overseer_plan = overseer_llm.plan(user_input)
        workflow = workflow_builder.build(overseer_plan)
        result = execute_workflow(workflow)
        display_result(result)
```

---

## 7. TOOL REGISTRY & DISCOVERY

### Tool Storage Format

**YAML Definition** (each tool has a .yaml file):
```yaml
name: my_tool
type: executable  # or 'llm', 'workflow', etc.
description: Tool description
tags: [tag1, tag2]
inputs:
  param1:
    type: string
    description: Parameter description
    required: true
outputs:
  result:
    type: string
    description: Output description
implementation:
  path: my_tool.py
  class: MyToolClass
  method: execute
  
# For LLM-based tools:
# prompt_template: "Optimize: {code}"
# model: gpt-3.5-turbo
```

### Tool Discovery Process

1. **Scanning**:
   - Scan `tools/executable/` for Python tools
   - Scan `tools/llm/` for prompt-based tools
   - Index in `tools/index.json`

2. **Registration**:
   - Tools automatically loaded into ToolsManager
   - Background loader (BackgroundToolsLoader) in separate thread
   - Deduplication system (ToolDeduplicationSystem)

3. **Semantic Search** (RAG):
   - Convert tool description → embeddings
   - Store in Qdrant vector DB
   - Search by semantic similarity
   - Rank by relevance and usage metrics

### Tool Categories

**Executable Tools** (100+ available):
- Data: generators, parsers, validators
- Code: formatters, linters, analyzers, optimizers
- Testing: test generators, test runners
- Integration: API clients, HTTP tools
- System: file ops, config generators, env checkers

**LLM Tools** (specialized prompts):
- content_generator: General content creation
- code_optimizer: Code performance optimization
- code_reviewer: Code quality review
- doc_generator: Documentation generation
- prompt_generator: Dynamic prompt generation
- llm_fake_data_generator: Test data generation

---

## 8. AUTO-EVOLUTION SYSTEM (src/auto_evolver.py)

### Performance Monitoring
Tracks:
- Execution time
- Quality score (test pass %, coverage %)
- Error rate
- Cache hit rates
- Resource usage

### Drift Detection
Triggers evolution when:
- Quality drops below threshold (default 0.15)
- Execution time increases significantly
- Error rate rises
- Cache effectiveness decreases

### Evolution Strategies
1. **Local Optimization** (Ollama, free/fast)
   - Quick fixes, code cleanup
   - Good enough for most cases

2. **Cloud Optimization** (Claude/GPT-4, expensive)
   - High-value artifacts
   - Batch processing overnight
   - Deep analysis

3. **Tool Switching**
   - Cache → NMT (Neural Machine Translation)
   - SQLite → Cloud if performance needed
   - Local → Specialized fine-tuned model

4. **Platform Adaptation**
   - Inline LLMs for Pi/Edge
   - Heavy models for Cloud
   - Pure Python for Embedded

### Real-World Example
```
Translation system:
Initial: 99.9% cache hits → Use SQLite (fast, free)
Drift detected: Cache hits drop to 85% → Switch to NMT
Recovery: Quality improves, cache back to 95% → Switch back to SQLite
Result: Learned optimal strategy for this workload
```

---

## 9. KEY INTEGRATION POINTS FOR FLASK UI

### For Building Flask UI, You Need:

1. **Configuration Access**:
   ```python
   from src.config_manager import ConfigManager
   config = ConfigManager(config_path='config.yaml')
   ```

2. **Tool Registry Access**:
   ```python
   from src.tools_manager import ToolsManager
   tools_manager = ToolsManager(config)
   tools = tools_manager.list_tools()
   ```

3. **Workflow Execution**:
   ```python
   from src.workflow_spec import WorkflowSpec
   from src.workflow_builder import WorkflowBuilder
   
   builder = WorkflowBuilder(tools_manager)
   workflow = builder.build_from_text(description, overseer_output)
   result = execute_workflow(workflow)  # Via workflow distributor
   ```

4. **Task Evaluation**:
   ```python
   from src.task_evaluator import TaskEvaluator
   evaluator = TaskEvaluator()
   task_type = evaluator.classify(user_input)
   ```

5. **RAG Search**:
   ```python
   from src.qdrant_rag_memory import QdrantRAGMemory
   rag = QdrantRAGMemory(config)
   similar_tools = rag.search("task description", k=5)
   ```

6. **LLM Integration**:
   ```python
   from src.llm_client_factory import LLMClientFactory
   client = LLMClientFactory.create(config, backend='anthropic')
   response = client.generate('claude-3-sonnet', prompt)
   ```

7. **HTTP Server (Flask)**:
   ```python
   from src.http_server_tool import HTTPServerTool
   server = HTTPServerTool(port=8080)
   server.add_route("/api/generate", ["POST"], handler)
   server.start(blocking=False)
   ```

---

## 10. SUGGESTED FLASK UI ARCHITECTURE

### Design Recommendations

1. **Separation of Concerns**:
   ```
   Flask App
   ├── API Routes (views)
   │   ├── /api/tasks         - Task submission & status
   │   ├── /api/workflows     - Workflow management
   │   ├── /api/tools         - Tool discovery
   │   ├── /api/chat          - Chat interface
   │   └── /api/config        - Configuration
   │
   ├── Service Layer
   │   ├── WorkflowService    - Workflow execution
   │   ├── ToolService        - Tool management
   │   ├── TaskService        - Task evaluation
   │   └── ChatService        - Chat session management
   │
   └── Integration Layer
       ├── Config (ConfigManager)
       ├── Tools (ToolsManager)
       ├── RAG (QdrantRAGMemory)
       ├── LLM Clients
       └── Workflow System
   ```

2. **Async Execution**:
   - Use Celery or APScheduler for background tasks
   - Store workflow results in database
   - Webhook callbacks for completion

3. **Stateful Sessions**:
   - Maintain conversation context per user
   - Store conversation history in database
   - Support multiple concurrent sessions

4. **Real-time Updates**:
   - WebSockets for live task progress
   - Server-Sent Events (SSE) for updates
   - Or use existing HTTP polling

---

## 11. FILES READY FOR INTEGRATION

### Direct Integration Files
- `/code_evolver/src/http_server_tool.py` - Already Flask-based!
- `/code_evolver/src/tools_manager.py` - Tool registry (107KB)
- `/code_evolver/src/workflow_spec.py` - Workflow data structures
- `/code_evolver/src/workflow_builder.py` - Build workflows from specs
- `/code_evolver/src/config_manager.py` - Configuration system
- `/code_evolver/src/task_evaluator.py` - Task classification
- `/code_evolver/examples/http_server_demo.py` - Working example!

### LLM Client Integration
- `/code_evolver/src/llm_client_factory.py` - Client creation
- `/code_evolver/src/anthropic_client.py` - Anthropic integration
- `/code_evolver/src/openai_client.py` - OpenAI integration
- `/code_evolver/src/ollama_client.py` - Local Ollama

### RAG & Memory
- `/code_evolver/src/qdrant_rag_memory.py` - Vector search
- `/code_evolver/src/rag_memory.py` - Core RAG interface
- `/code_evolver/src/interaction_logger.py` - Chat logging

### Testing & Validation
- `/code_evolver/test_http_tools_e2e.py` - E2E test examples
- `/code_evolver/test_http_server.py` - HTTP server tests

---

## SUMMARY

**The Code Evolver is a sophisticated, production-ready system for:**
- Multi-LLM code generation and optimization
- Workflow specification and execution
- Tool discovery and semantic search
- Automatic quality evaluation and escalation
- Platform-specific distribution

**For Flask UI Integration:**
1. HTTPServerTool already provides Flask foundation
2. ToolsManager and WorkflowSpec provide data structures
3. ConfigManager handles all configuration
4. LLM clients support multiple backends
5. RAG memory enables semantic search
6. Examples demonstrate working patterns

**Your Flask UI can wrap these components to provide:**
- Web-based workflow editor and executor
- Tool discovery and management interface
- Real-time chat/conversation interface
- Workflow monitoring and logging
- Configuration management UI
