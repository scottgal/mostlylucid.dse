# Code Evolver : En Experiment in Directed Synthetic Evolution

> NOTE: This is an experiment accompanying my blog series on [Directed Synthetic Evolution](https://www.mostlylucid.net/blog/category/Emergent%20Intelligence).
A rather simple idea which just uses code generating llms to generate Python scripts and multi-agent, multistep plans to accomplish aribrary wokrflows.

It's a vibe coded project to experiment with the idea I had in the thought experiment around self optimizing multi-llm workflows.

It's not a production ready system and it's slow (but it gets faster, that's the kind of odd thing!

Right now it can do the generate part but it needs:
1. Ann offline 'big bad model' optimization step to enable the self optimization to use accumulated real data to improve the Python node script's performance on tasks.
2. Inter-layer communication (through the shared context) allowing dynamic quality assesment anf 'hints between layers to optimize overall workflow.
3. Lots more tools. As more are added it is able to more accurately asses things like performance, security, and code quality.
4. The ability (and templates to reduce boilerplate though thos may emerge as par tof optimization) allowing storage node tools to build additonal capabilities. 
5. It is NOT secure / good code or antyhing else again **I AM NOT A PYTHON DEVELOPER**

It would as well be called: 

# Self Assembling, Self Optimising Workflows with a multillm, multistep, multimodel approach.

Not as catchy though. But that's basically the elevator pitch it;s an ENTIRELY vibe coded experiment into how that might work.


**AI-Powered Code Evolution System with RAG Memory and Intelligent Tool Selection**

A Python-based system for evolving code through AI-assisted generation, execution, and evaluation using local Ollama models. Features semantic tool selection, RAG memory, hierarchical evolution, and multi-endpoint LLM routing.

---

##  What's New in Latest Version

### RAG-Powered Semantic Tool Selection
- **Intelligent Tool Discovery**: Uses RAG (Retrieval-Augmented Generation) to find the best tools for your task
- **Semantic Search**: Embedding-based search finds relevant tools based on meaning, not just keywords
- **Auto-Tool Selection**: System automatically picks the best specialized LLM for each task
- **Tool Memory**: All tools indexed in RAG for fast retrieval

### Multi-Endpoint LLM Routing
- **Distributed Inference**: Run different models on different machines
- **Per-Model Endpoints**: Route overseer to powerful CPU, generator to GPU machine
- **Load Distribution**: Balance workload across multiple Ollama servers
- **Flexible Configuration**: Easy YAML-based endpoint configuration

### Enhanced Features
- **Windows Support**: Full compatibility with Windows (readline-free implementation)
- **Hierarchical Evolution**: Break complex tasks into manageable sub-workflows
- **Qdrant Integration**: Optional vector database for scalable RAG (millions of artifacts)
- **Progress Display**: Real-time visual progress with rich terminal UI
- **Solution Memory**: Stores and reuses successful patterns

---

## Overview

Code Evolver is a comprehensive system for AI-driven code generation and evolution that uses:

- **Ollama LLMs** (codellama, llama3, tiny) for code generation and evaluation
- **RAG Memory** for semantic search and pattern reuse
- **Intelligent Tool Selection** to automatically choose the best LLM for each task
- **Sandboxed Execution** with comprehensive metrics collection
- **Auto-Evolution** that monitors and improves code performance over time
- **Multi-Model Workflow** with overseer planning, specialized generation, and evaluation

---

## Key Features

### 🧠 AI-Powered Intelligence
- **Overseer Pattern**: Every task starts with strategic planning by overseer LLM
- **RAG Memory System**: Stores plans, functions, workflows as embeddings for semantic retrieval
- **Tool Selection**: Automatically finds and uses specialized LLMs for specific tasks
- **Pattern Recognition**: Learns from past solutions and reuses successful patterns
- **Semantic Search**: Find similar solutions using embedding similarity

### 🛠️ Development Tools
- **Interactive CLI**: Chat-based interface for natural interaction
- **Code Generation**: Natural language to working Python code
- **Automatic Testing**: Generates and runs unit tests automatically
- **Error Escalation**: Auto-fixes failing code using higher-level LLMs
- **Code Cleaning**: Removes markdown artifacts from LLM output

### 📊 Performance & Quality
- **Sandboxed Execution**: Safe code execution with timeout and memory limits
- **Comprehensive Metrics**: Latency, memory, CPU usage, exit codes
- **Multi-Model Evaluation**: Fast triage (tiny) + comprehensive evaluation (llama3)
- **Auto-Evolution**: Monitors performance and triggers improvements
- **A/B Testing**: Compares versions and keeps the best

### 🔧 Tools & Workflows
- **Tools Registry**: Reusable components (LLMs, functions, workflows)
- **Specialized LLMs**: Code reviewers, security auditors, performance optimizers
- **Workflow Composition**: Build complex workflows from simple components
- **Hierarchical Evolution**: Break tasks into manageable sub-problems
- **Community Patterns**: Share and reuse successful approaches

### 🌐 Scalability
- **Multi-Endpoint Routing**: Distribute work across multiple Ollama servers
- **Qdrant Support**: Optional vector database for millions of embeddings
- **Distributed Computing**: Put heavy models on powerful hardware
- **Cross-Platform**: Windows, Linux, macOS support
- **Executable Builds**: Standalone binaries for easy distribution

---

## Prerequisites

### 1. Install Python

Python 3.11 or higher is required.

### 2. Install Ollama

Download and install Ollama from [https://ollama.com](https://ollama.com)

**Windows:**
- Download the Windows installer
- Run the installer
- Ollama will start automatically in the system tray

**Linux/macOS:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 3. Pull Required Models

```bash
# Essential models
ollama pull codellama    # Code generation
ollama pull llama3       # Strategy, evaluation, reviewing
ollama pull tinyllama    # Fast triage

# Optional: For embeddings (RAG)
ollama pull nomic-embed-text
```

Verify models are available:
```bash
ollama list
```

### 4. Optional: Install Qdrant (For Scalable RAG)

If you want to use Qdrant for vector storage (recommended for production):

**Using Docker:**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

**Or install standalone**: See [Qdrant docs](https://qdrant.tech/documentation/quick-start/)

---

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies:**

```bash
cd code_evolver
pip install -r requirements.txt
```

3. **Verify setup:**

```bash
python orchestrator.py check
```

You should see:
```
✓ Connected to Ollama server
Available models: codellama, llama3, tinyllama
✓ RAG memory initialized
✓ Tools registry loaded (4 tools)
✓ Setup OK
```

---

## Quick Start (5 Minutes)

### 1. Start Interactive Chat

```bash
python chat_cli.py
```

### 2. Generate Your First Code

```
CodeEvolver> generate Write a function that validates email addresses using regex
```

The system will:
1. 🔍 Search for relevant tools (e.g., validation specialists)
2. 🧠 Consult overseer LLM for strategy
3. 🤖 Select best LLM tool (or use codellama)
4. ✨ Generate working Python code
5. ✅ Create and run unit tests
6. 📊 Evaluate quality and performance

### 3. Run the Generated Code

```
CodeEvolver> run validate_email_addresses {"email": "test@example.com"}
```

### 4. View All Generated Nodes

```
CodeEvolver> list
```

---

## Usage

### Interactive CLI Commands

Launch the chat interface:
```bash
python chat_cli.py
```

**Available Commands:**
- `generate <description>` - Create new code with AI assistance
- `run <node_id> [input_json]` - Execute a node
- `list` - Show all nodes in registry
- `status` - System status and available models
- `auto on/off` - Toggle auto-evolution
- `help` - Show all commands
- `exit` or `quit` - Exit

**Example Session:**
```
CodeEvolver> generate Calculate Fibonacci sequence up to n

Searching for relevant tools...
✓ Found 1 relevant tools
Consulting overseer LLM (llama3) for approach...
✓ Strategy received
Using standard generator: codellama
Generating code with codellama...
✓ Node 'calculate_fibonacci_sequence_up_to' created successfully!

CodeEvolver> run calculate_fibonacci_sequence_up_to {"n": 10}

Running calculate_fibonacci_sequence_up_to...
✓ Execution successful
┌─────────────────────────────────────────┐
│ Output                                   │
├─────────────────────────────────────────┤
│ {"sequence": [0,1,1,2,3,5,8,13,21,34]}  │
└─────────────────────────────────────────┘

CodeEvolver> list
```

### Command-Line Interface

#### Check Setup
```bash
python orchestrator.py check
```

#### Generate a Node
```bash
python orchestrator.py generate compress_text "Text Compressor" \
  "Write a Python function that compresses text using run-length encoding"
```

#### Run a Node
```bash
python orchestrator.py run compress_text --input '{"text":"AAAABBB"}'
```

#### Full Workflow (Generate + Run + Evaluate)
```bash
python orchestrator.py full my_function "My Function" \
  "Write a function for..." \
  --input '{"data":"test"}'
```

#### List All Nodes
```bash
python orchestrator.py list
```

### Python API

```python
from src import (
    OllamaClient, Registry, NodeRunner, Evaluator,
    RAGMemory, ToolsManager, ConfigManager
)
from src.rag_memory import ArtifactType

# Initialize with full configuration
config = ConfigManager("config.yaml")
client = OllamaClient(config.ollama_url, config_manager=config)

# RAG memory for semantic search
rag = RAGMemory(
    memory_path=config.rag_memory_path,
    ollama_client=client
)

# Tools with RAG integration
tools = ToolsManager(
    config_manager=config,
    ollama_client=client,
    rag_memory=rag
)

# Registry and runner
registry = Registry(config.registry_path)
runner = NodeRunner(config.nodes_path)
evaluator = Evaluator(client)

# 1. Consult overseer for strategy
strategy = client.generate(
    model=config.overseer_model,
    prompt="How to compress text efficiently?",
    model_key="overseer"
)

# 2. Store strategy in RAG
rag.store_artifact(
    artifact_id="plan_compress",
    artifact_type=ArtifactType.PLAN,
    name="Text Compression Strategy",
    content=strategy,
    tags=["compression", "plan"],
    auto_embed=True
)

# 3. Generate code based on strategy
code = client.generate(
    model=config.generator_model,
    prompt=f"Based on: {strategy}\n\nWrite compression code",
    model_key="generator"
)

# 4. Store code in RAG
rag.store_artifact(
    artifact_id="func_compress",
    artifact_type=ArtifactType.FUNCTION,
    name="RLE Compressor",
    content=code,
    tags=["compression", "function"],
    auto_embed=True
)

# 5. Save and run
runner.save_code("compressor", code)
stdout, stderr, metrics = runner.run_node(
    "compressor",
    {"text": "AAABBB"}
)

# 6. Evaluate
result = evaluator.evaluate_full(stdout, stderr, metrics)
print(f"Score: {result['final_score']}")

# 7. Find similar solutions later
similar = rag.find_similar(
    "How to compress strings?",
    artifact_type=ArtifactType.FUNCTION,
    top_k=3
)
```

---

## Configuration

### Basic Configuration (config.yaml)

```yaml
# Ollama server settings
ollama:
  base_url: "http://localhost:11434"

  # Model assignments with optional per-model endpoints
  models:
    # Overseer - Plans strategy (llama3, mistral, mixtral)
    overseer:
      model: "llama3"
      endpoint: null  # Uses base_url

    # Generator - Writes code (codellama, deepseek-coder)
    generator:
      model: "codellama"
      endpoint: null

    # Evaluator - Assesses quality (llama3, mistral)
    evaluator:
      model: "llama3"
      endpoint: null

    # Triage - Quick pass/fail (tinyllama, llama3)
    triage:
      model: "tinyllama"
      endpoint: null

    # Escalation - Fixes issues (llama3, mixtral)
    escalation:
      model: "llama3"
      endpoint: null

  # Embedding model for RAG
  embedding:
    model: "nomic-embed-text"
    endpoint: null
    vector_size: 768

# Execution settings
execution:
  default_timeout_ms: 5000
  max_memory_mb: 256
  max_retries: 3

# Auto-evolution
auto_evolution:
  enabled: true
  performance_threshold: 0.15
  min_runs_before_evolution: 3

# RAG Memory
rag_memory:
  path: "./rag_memory"
  use_qdrant: false  # Set true for Qdrant
  qdrant_url: "http://localhost:6333"

# Testing
testing:
  enabled: true
  generate_unit_tests: true
  auto_escalate_on_failure: true

# Chat interface
chat:
  show_thinking: false  # Show overseer reasoning
  show_metrics: true
```

### Multi-Endpoint Configuration

Run different models on different machines:

```yaml
ollama:
  base_url: "http://localhost:11434"

  models:
    # Heavy planning on powerful CPU machine
    overseer:
      model: "llama3"
      endpoint: "http://powerful-cpu:11434"

    # Code generation on GPU machine
    generator:
      model: "codellama"
      endpoint: "http://gpu-server:11434"

    # Fast evaluation locally
    evaluator:
      model: "llama3"
      endpoint: null  # Uses base_url

    # Quick triage on fast machine
    triage:
      model: "tinyllama"
      endpoint: "http://fast-machine:11434"
```

### Tools Configuration

Define specialized LLMs for specific tasks:

```yaml
tools:
  # Code reviewer
  code_reviewer:
    name: "Code Reviewer"
    type: "llm"
    description: "Reviews code for quality, bugs, and best practices"
    llm:
      model: "llama3"
      endpoint: null
    tags: ["review", "quality"]

  # Performance optimizer
  performance_optimizer:
    name: "Performance Optimizer"
    type: "llm"
    description: "Suggests performance optimizations"
    llm:
      model: "codellama"
      endpoint: null
    tags: ["performance", "optimization"]

  # Security auditor
  security_auditor:
    name: "Security Auditor"
    type: "llm"
    description: "Audits code for security vulnerabilities"
    llm:
      model: "llama3"
      endpoint: null
    tags: ["security", "audit"]
```

---

## How It Works: The Overseer Pattern

Every code generation follows this intelligent workflow:

```
User Request: "Generate code to..."
       ↓
[1. RAG Tool Search] → Find relevant specialized LLMs
       ↓
[2. Overseer Planning] → Strategize approach with available tools
       ↓
[3. Tool Selection] → Pick best LLM (specialized or standard)
       ↓
[4. Code Generation] → Generate using selected tool
       ↓
[5. Store in RAG] → Index code for future reuse
       ↓
[6. Execute & Test] → Run with metrics collection
       ↓
[7. Evaluate] → Multi-model quality assessment
       ↓
[8. Auto-Evolve] → Monitor and improve over time
```

### Example Flow

**Request:** "Write a function that validates email addresses"

1. **RAG Search**: Finds "validation specialist" and "regex expert" tools
2. **Overseer**: Plans regex-based approach, recommends validation specialist
3. **Tool Selection**: Picks specialized validation LLM
4. **Generation**: Creates production-ready code with tests
5. **RAG Storage**: Indexes as reusable "validation pattern"
6. **Execution**: Runs unit tests automatically
7. **Evaluation**: Scores correctness, performance, code quality
8. **Future Reuse**: Similar requests find this solution via semantic search

---

## RAG Memory System

### What is RAG Memory?

RAG (Retrieval-Augmented Generation) allows the system to:
- **Remember** successful solutions and strategies
- **Search** semantically (by meaning, not keywords)
- **Reuse** proven patterns for similar problems
- **Learn** from past experiences

### Artifact Types

```python
from src.rag_memory import ArtifactType

# Store different types of knowledge
ArtifactType.PLAN       # Strategies and approaches
ArtifactType.FUNCTION   # Reusable functions
ArtifactType.WORKFLOW   # Complete workflows
ArtifactType.SUB_WORKFLOW  # Sub-task workflows
ArtifactType.PATTERN    # Design patterns and tools
```

### Using RAG Memory

```python
# Store a successful solution
rag.store_artifact(
    artifact_id="email_validator",
    artifact_type=ArtifactType.FUNCTION,
    name="Email Validator",
    description="Validates email addresses using regex",
    content=code,
    tags=["validation", "email", "regex"],
    auto_embed=True  # Create embedding for semantic search
)

# Find similar solutions later
results = rag.find_similar(
    query="validate user email input",
    artifact_type=ArtifactType.FUNCTION,
    top_k=5
)

for artifact, similarity in results:
    print(f"{artifact.name}: {similarity:.2f}")
```

### Qdrant Integration (Optional)

For production use with millions of artifacts:

```yaml
rag_memory:
  use_qdrant: true
  qdrant_url: "http://localhost:6333"
  collection_name: "code_evolver_artifacts"
```

Benefits:
- **Scalable**: Handle millions of embeddings
- **Fast**: Optimized vector search
- **Persistent**: Durable storage
- **Production-Ready**: Battle-tested in real applications

---

## Tools System

### What are Tools?

Tools are reusable components that can be:
- **LLM Specialists**: Models fine-tuned for specific tasks
- **Functions**: Python code snippets
- **Workflows**: Multi-step processes
- **Patterns**: Proven approaches

### Automatic Tool Selection

The system uses RAG to find the best tool for your task:

```
Task: "Optimize database query performance"
  ↓ RAG Semantic Search
  ↓
Found: Performance Optimizer (codellama)
  ↓
Uses specialized LLM instead of generic generator
```

### Creating Custom Tools

Add to `config.yaml`:

```yaml
tools:
  my_specialist:
    name: "My Specialist"
    type: "llm"
    description: "Specializes in X, Y, Z tasks"
    llm:
      model: "codellama"
      endpoint: "http://specialist-server:11434"
    tags: ["specialist", "custom"]
```

The tool is automatically indexed in RAG and becomes available for semantic search.

---

## Auto-Evolution

### How It Works

Auto-evolution continuously improves code:

1. **Monitor**: Track performance metrics for each node run
2. **Detect**: Identify degradation or optimization opportunities
3. **Mutate**: Generate improved version using feedback
4. **Test**: A/B test old vs. new version
5. **Select**: Keep the better performer
6. **Update**: Save lineage and version history

### Enable Auto-Evolution

**Via CLI:**
```bash
python orchestrator.py config --auto-evolution on
```

**Via Config:**
```yaml
auto_evolution:
  enabled: true
  performance_threshold: 0.15  # Trigger at 15% change
  min_runs_before_evolution: 3
  check_interval_minutes: 60
```

**Via Chat:**
```
CodeEvolver> auto on
✓ Auto-evolution enabled
```

### Evolution Example

```
Node: text_compressor_v1
Runs: 50
Average Score: 0.75

↓ Performance degrades to 0.65

Auto-Evolution Triggered:
- Analyze metrics
- Generate improved version
- Create text_compressor_v1_1_0

A/B Test:
- v1.0.0: Score 0.65
- v1.1.0: Score 0.82

✓ Promoted v1.1.0 as primary
```

---

## Building Executables

Create standalone executables for distribution:

### Build for Current Platform
```bash
python build.py
```

### Build for Specific Platform
```bash
python build.py --platform windows
python build.py --platform linux
python build.py --platform macos
```

### Build for All Platforms
```bash
python build.py --all
```

**Outputs:**
- Windows: `dist/code_evolver.exe`
- Linux: `dist/code_evolver`
- macOS: `dist/code_evolver.app`

---

## Examples

### Example 1: Email Validator

```bash
python chat_cli.py
```

```
CodeEvolver> generate Write a function to validate email addresses using regex

Searching for relevant tools...
✓ Found validation specialist
Consulting overseer...
✓ Using specialized tool: Validation Expert
Generating code...
✓ Tests passed
✓ Node 'validate_email_addresses' created!

CodeEvolver> run validate_email_addresses {"email": "test@example.com"}

✓ Execution successful
Output: {"valid": true, "email": "test@example.com"}
```

### Example 2: Using RAG to Find Similar Solutions

```python
from src import RAGMemory, OllamaClient
from src.rag_memory import ArtifactType

client = OllamaClient()
rag = RAGMemory(ollama_client=client)

# Find similar validation functions
results = rag.find_similar(
    "check if email is valid",
    artifact_type=ArtifactType.FUNCTION,
    top_k=3
)

for artifact, similarity in results:
    print(f"\n{artifact.name} (similarity: {similarity:.2f})")
    print(f"Description: {artifact.description}")
    print(f"Tags: {', '.join(artifact.tags)}")
    print(f"Quality Score: {artifact.quality_score:.2f}")
    print(f"Times Used: {artifact.usage_count}")
```

### Example 3: Multi-Step Workflow with Tools

```python
from src import OllamaClient, ToolsManager, ConfigManager
from src.rag_memory import RAGMemory

config = ConfigManager()
client = OllamaClient(config.ollama_url, config_manager=config)
rag = RAGMemory(ollama_client=client)
tools = ToolsManager(config_manager=config, ollama_client=client, rag_memory=rag)

# 1. Find best tool for code review
review_tool = tools.get_best_llm_for_task("review code quality and security")

# 2. Use the tool
code = """
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    return db.execute(query)
"""

review = tools.invoke_llm_tool(
    tool_id=review_tool.tool_id,
    prompt=f"Review this code:\n{code}",
    temperature=0.3
)

print(review)
# Output: "⚠️ SQL Injection vulnerability! Use parameterized queries..."
```

---

## Directory Structure

```
code_evolver/
├── orchestrator.py          # Main CLI entry point
├── chat_cli.py             # Interactive chat interface
├── demo_progress.py        # Progress display demo
├── build.py                # Build script for executables
├── config.yaml             # Configuration file
├── requirements.txt        # Python dependencies
│
├── src/                    # Core modules
│   ├── __init__.py
│   ├── ollama_client.py    # Ollama API client with multi-endpoint support
│   ├── registry.py         # File-based node registry
│   ├── node_runner.py      # Sandboxed code execution
│   ├── evaluator.py        # Multi-model evaluation
│   ├── config_manager.py   # Configuration management
│   ├── auto_evolver.py     # Auto-evolution engine
│   ├── rag_memory.py       # RAG memory with embeddings
│   ├── qdrant_rag_memory.py # Qdrant-based scalable RAG
│   ├── tools_manager.py    # Tools registry with RAG integration
│   ├── hierarchical_evolver.py  # Hierarchical task decomposition
│   ├── progress_display.py # Rich terminal UI for progress
│   └── solution_memory.py  # Solution storage and retrieval
│
├── nodes/                  # Generated code
│   └── [node_id]/
│       ├── main.py
│       └── test_main.py
│
├── registry/               # Node metadata and metrics
│   ├── index.json
│   └── [node_id]/
│       ├── node.json
│       ├── metrics.json
│       └── evaluation.json
│
├── rag_memory/            # RAG artifacts and embeddings
│   ├── artifacts.json
│   └── embeddings.npy
│
├── tools/                 # Tools registry
│   └── index.json
│
└── shared_context/        # Shared state for workflows
    └── shared_context.json
```

---

## Advanced Features

### Hierarchical Evolution

Break complex tasks into manageable sub-workflows:

```python
from src import HierarchicalEvolver

evolver = HierarchicalEvolver(
    config=config,
    client=client,
    rag_memory=rag
)

result = evolver.evolve_hierarchical(
    root_goal="Build a complete REST API",
    max_depth=3,
    max_breadth=4
)

# Automatically creates sub-workflows:
# - Design API schema
# - Implement authentication
# - Create endpoints
# - Add error handling
# - Write tests
```

### Progress Display

Real-time visual progress for long-running tasks:

```python
from src.progress_display import ProgressDisplay

with ProgressDisplay() as progress:
    task = progress.add_task("Generating code", total=100)

    # Your code here
    progress.update(task, advance=10)
```

### Solution Memory

Specialized storage for successful solutions:

```python
from src import SolutionMemory

memory = SolutionMemory(rag_memory=rag)

# Store solution
memory.store_solution(
    problem="sort list of dictionaries",
    solution=code,
    quality_score=0.95,
    tags=["sorting", "data-structures"]
)

# Find similar solutions
solutions = memory.find_solutions("sort dictionary array")
```

---

## Troubleshooting

### Cannot Connect to Ollama

1. **Check if running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Start Ollama:**
   - Windows: Check system tray or run `ollama serve`
   - Linux/macOS: `ollama serve`

### Model Not Found

```bash
ollama pull codellama
ollama pull llama3
ollama pull tinyllama
ollama pull nomic-embed-text
```

### Windows: ModuleNotFoundError: readline

This is expected on Windows - the system handles it automatically. The CLI works without readline (just no command history persistence).

### RAG Memory Slow with Many Artifacts

Enable Qdrant for better performance:

```yaml
rag_memory:
  use_qdrant: true
  qdrant_url: "http://localhost:6333"
```

### Code Generation Produces Markdown

The system automatically cleans markdown artifacts (` ```python ` fences). If it persists, check `_clean_code()` in `chat_cli.py`.

### Poor Tool Selection

1. **Check tool definitions** in `config.yaml`
2. **Verify RAG indexing**: Look for "Indexed X tools in RAG memory"
3. **Review tool descriptions**: Make them specific and detailed
4. **Check embeddings**: Ensure `nomic-embed-text` model is available

---

## Performance Optimization

### Use Triage Model First
```python
# Fast pass/fail check before full evaluation
triage_result = client.triage(metrics, targets)
if "pass" in triage_result:
    full_result = evaluator.evaluate_full(...)
```

### Cache in RAG
```python
# Reuse successful solutions
similar = rag.find_similar(task_description)
if similar and similar[0][1] > 0.9:  # High similarity
    return similar[0][0].content  # Reuse solution
```

### Multi-Endpoint Distribution
```yaml
# Heavy models on powerful hardware
overseer:
  endpoint: "http://powerful-server:11434"
generator:
  endpoint: "http://gpu-machine:11434"
```

### Batch Processing
```python
# Run multiple tests before evaluation
for test_case in test_cases:
    results.append(runner.run_node(node_id, test_case))

# Evaluate once with all results
evaluation = evaluator.evaluate_batch(results)
```

---

## Security Considerations

⚠️ **Warning**: This system executes AI-generated code.

### Built-in Protections
- ✅ **Timeout limits**: Prevents infinite loops
- ✅ **Memory limits**: Prevents excessive memory usage
- ✅ **Sandboxed execution**: Isolated subprocess
- ✅ **Code review**: Optional review before execution

### Best Practices
1. **Review generated code** before running in production
2. **Run in isolated environment** (VM, container, sandbox)
3. **Don't run with elevated privileges**
4. **Monitor system resources**
5. **Use code review tools** before deployment
6. **Enable security auditor** in tools config
7. **Keep backups** of important data

### Recommended Setup

```yaml
# Enable security tools
tools:
  security_auditor:
    name: "Security Auditor"
    type: "llm"
    description: "Audits code for security vulnerabilities"
    llm:
      model: "llama3"
    tags: ["security", "audit"]

# Stricter execution limits
execution:
  default_timeout_ms: 3000
  max_memory_mb: 128
  sandbox:
    allow_network: false
    allow_file_write: false
```

---

## Roadmap

### ✅ Completed (Current Version)
- Interactive CLI chat interface
- RAG memory with semantic search
- Tools system with automatic selection
- Multi-endpoint LLM routing
- Hierarchical evolution
- Qdrant integration
- Windows support
- Progress display
- Auto-evolution
- Configuration management
- Executable builds

### 🚧 In Progress (v1.0)
- [ ] Web UI dashboard with real-time monitoring
- [ ] Multi-language support (JavaScript, Go, Rust)
- [ ] Advanced sandboxing (Docker, cgroups)
- [ ] Fine-tuned specialist models
- [ ] Git integration for version control
- [ ] Distributed registry with consensus
- [ ] Cloud deployment (AWS, Azure, GCP)
- [ ] Plugin system for extensibility

### 🔮 Future (v2.0+)
- [ ] Visual workflow builder
- [ ] Collaborative coding (multi-user)
- [ ] Custom model training pipeline
- [ ] Integration with popular IDEs
- [ ] Mobile app for monitoring
- [ ] Marketplace for tools and workflows
- [ ] Enterprise features (SSO, audit logs)

---

## Contributing

We welcome contributions! Here's how:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Test thoroughly**
   ```bash
   python -m pytest tests/ -v
   ```
5. **Submit a pull request**

### Areas for Contribution
- 🧪 **Testing**: Add unit tests, integration tests
- 📚 **Documentation**: Improve guides, add examples
- 🛠️ **Tools**: Create specialized LLM tools
- 🐛 **Bug Fixes**: Fix issues, improve stability
- ✨ **Features**: Implement roadmap items
- 🌍 **Localization**: Translate documentation

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

- **Ollama**: Local LLM inference ([ollama.com](https://ollama.com))
- **Qdrant**: Vector database ([qdrant.tech](https://qdrant.tech))
- **Rich**: Beautiful terminal formatting ([rich.readthedocs.io](https://rich.readthedocs.io))
- Inspired by genetic algorithms and evolutionary computation research
- Built with contributions from the AI and open-source communities

---

## Documentation

- **README.md** (this file) - Complete guide
- **QUICKSTART.md** - 5-minute getting started guide
- **IMPLEMENTATION_SUMMARY.md** - Technical architecture overview
- **CLAUDE.md** - Claude Code CLI documentation
- **config.yaml** - Configuration reference with comments

---

## Support

### Getting Help
- 📖 Read the documentation (this README + others)
- 💬 Open an issue on GitHub
- 🔍 Check existing issues and discussions
- 📧 Contact the maintainers

### Common Questions

**Q: Can I use different Ollama models?**
A: Yes! Edit `config.yaml` and change model names. Any Ollama-compatible model works.

**Q: Does it work offline?**
A: Yes! All LLMs run locally via Ollama. No internet required (after downloading models).

**Q: Can I use OpenAI or other APIs?**
A: Currently designed for Ollama. Adding API support is on the roadmap.

**Q: How much RAM do I need?**
A: Depends on models. Minimum 8GB for tinyllama, 16GB+ recommended for llama3/codellama.

**Q: Is the generated code safe?**
A: Review all generated code before production use. Use sandboxing and security tools.

**Q: Can I run this in production?**
A: Yes, with proper security measures. Enable Qdrant, use strict sandboxing, review code.

---

**Happy Code Evolving! 🧬🤖**

Built with ❤️ using AI and open-source tools.
