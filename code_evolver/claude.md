# mostlylucid DiSE - Claude Code CLI Documentation

**AI-Powered Code Evolution System with Multi-Backend LLM Support**

> **Note:** This system now uses a **role-based and tier-based configuration** for flexible model management. See [NEW_CONFIG_ARCHITECTURE.md](NEW_CONFIG_ARCHITECTURE.md) and [MODEL_TIERS.md](MODEL_TIERS.md) for details.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Pull Ollama models
ollama pull llama3
ollama pull codellama
ollama pull tiny

# Verify setup
python orchestrator.py check

# Start interactive chat
python chat_cli.py
```

---

## Core Workflow

### The Overseer Pattern

Every code generation starts with the **Overseer LLM** planning the approach:

```
User Request
    ↓
[Overseer LLM] ← Analyzes request, plans strategy
    ↓
[Generator LLM] ← Receives strategy, writes code
    ↓
[Test Runner] ← Executes code, collects metrics
    ↓
[Evaluator LLM] ← Reviews results, scores quality
    ↓
[RAG Memory] ← Stores successful solutions
    ↓
[Auto-Evolution] ← Monitors and improves over time
```

### Node Communication Flow

**Each node follows this pattern:**

1. **Receive Instructions**: Node gets task description
2. **Consult Overseer**: Sends instructions to overseer for strategy
3. **Execute Task**: Uses overseer's plan to complete work
4. **Update Shared State**: Stores code & plans in RAG memory
5. **Pass to Next Node**: Sends results downstream

**Example Flow:**

```python
# Step 1: User request arrives
request = "Write a function that validates email addresses"

# Step 2: Overseer plans approach (uses "base" role)
overseer_response = client.generate(
    role="base",  # Maps to model based on config
    prompt=f"Plan how to solve: {request}"
)

# Step 3: Store plan in RAG
rag.store_artifact(
    artifact_id=f"plan_{node_id}",
    artifact_type=ArtifactType.PLAN,
    name=f"Plan for {request}",
    content=overseer_response,
    tags=["plan", "overseer"]
)

# Step 4: Generator uses plan (uses "base" role or specific tier)
code = client.generate(
    role="base",  # Or use tier: "coding.tier_2"
    prompt=f"Based on this strategy:\n{overseer_response}\n\nWrite code for: {request}"
)

# Step 5: Store code in RAG
rag.store_artifact(
    artifact_id=f"func_{node_id}",
    artifact_type=ArtifactType.FUNCTION,
    name="Email Validator",
    content=code,
    tags=["function", "validation", "email"]
)

# Step 6: Next node receives code + plan
```

---

## Architecture

### Components

1. **Ollama Client** (`src/ollama_client.py`)
   - Communicates with local Ollama servers
   - Supports multi-endpoint routing
   - Handles code generation, evaluation, triage

2. **RAG Memory** (`src/rag_memory.py`)
   - Stores plans, functions, workflows, sub-workflows
   - Semantic search using embeddings
   - Tag-based retrieval
   - Quality tracking

3. **Registry** (`src/registry.py`)
   - File-based storage for nodes
   - Metrics collection
   - Evaluation results
   - Lineage tracking

4. **Node Runner** (`src/node_runner.py`)
   - Sandboxed code execution
   - Resource limits (CPU, memory, time)
   - Metrics collection

5. **Evaluator** (`src/evaluator.py`)
   - Multi-model evaluation (tiny, llama3)
   - Performance scoring
   - Quality assessment

6. **Auto-Evolver** (`src/auto_evolver.py`)
   - Performance monitoring
   - Automatic code improvement
   - A/B testing

7. **Tools Manager** (`src/tools_manager.py`)
   - Reusable components
   - Specialized LLMs
   - Workflow patterns

8. **Config Manager** (`src/config_manager.py`)
   - YAML-based configuration
   - Per-model endpoint routing
   - Settings management

---

## Configuration System

### Role-Based Configuration

The new system uses **abstract roles** that map to actual models:

```yaml
llm:
  backend: "ollama"

  # Map roles to models
  model_roles:
    fast: "qwen2.5-coder:3b"      # Fast, simple tasks
    base: "codellama:7b"           # Most tasks (default)
    powerful: "qwen2.5-coder:14b"  # Complex reasoning
    god_level: "deepseek-coder-v2:16b"  # Last resort
    embedding: "nomic-embed-text"  # Vector embeddings

  backends:
    ollama:
      base_url: "http://localhost:11434"
      enabled: true
```

**Tools reference roles, not models:**

```yaml
# tools/llm/general.yaml
name: "General Code Generator"
type: "llm"
llm:
  role: "base"  # Uses codellama:7b with above config

# tools/llm/security_auditor.yaml
name: "Security Auditor"
type: "llm"
llm:
  role: "powerful"  # Uses qwen2.5-coder:14b
```

### Tier-Based Configuration

For more granular control, use **model tiers**:

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

**Benefits:**
- **Backend-agnostic:** Tools work with any backend
- **Easy switching:** Change all models by updating role mapping
- **No duplication:** Tools defined once
- **Automatic escalation:** Tiers escalate to more powerful models
- **Context management:** Higher tiers get bigger context windows

---

## RAG Memory System

### Shared State Pattern

All nodes update a **common RAG memory** with their contributions:

```python
# Overseer stores its plan
rag.store_artifact(
    artifact_id=f"plan_{task_id}",
    artifact_type=ArtifactType.PLAN,
    name="Processing Strategy",
    description="How to approach the task",
    content=overseer_output,
    tags=["plan", "strategy"],
    metadata={"task_id": task_id, "model": "overseer"}
)

# Generator stores its code
rag.store_artifact(
    artifact_id=f"func_{task_id}",
    artifact_type=ArtifactType.FUNCTION,
    name="Generated Function",
    description="Implementation based on plan",
    content=generated_code,
    tags=["function", "generated"],
    metadata={"task_id": task_id, "model": "generator", "based_on": f"plan_{task_id}"}
)

# Evaluator stores its assessment
rag.store_artifact(
    artifact_id=f"eval_{task_id}",
    artifact_type=ArtifactType.PATTERN,
    name="Evaluation Report",
    description="Quality assessment",
    content=json.dumps(evaluation),
    tags=["evaluation", "metrics"],
    metadata={"task_id": task_id, "score": 0.85}
)
```

### Retrieving from Shared State

Later tasks can find relevant past work:

```python
# Find similar plans
similar_plans = rag.find_similar(
    "How to process large files?",
    artifact_type=ArtifactType.PLAN,
    top_k=3
)

# Reuse successful patterns
if similar_plans:
    best_plan = similar_plans[0][0]  # (artifact, similarity)
    print(f"Reusing plan: {best_plan.name} (quality: {best_plan.quality_score})")
    rag.increment_usage(best_plan.artifact_id)
```

---

## Command Reference

### Orchestrator CLI

```bash
# Check system status
python orchestrator.py check

# Generate code
python orchestrator.py generate my_func "Function Name" "Description"

# Run generated code
python orchestrator.py run my_func --input '{"data":"test"}'

# Evaluate performance
python orchestrator.py evaluate my_func

# Full workflow (generate + run + evaluate)
python orchestrator.py full my_func "Function" "Description" --input '{"data":"test"}'

# List all nodes
python orchestrator.py list
```

### Interactive Chat

```bash
python chat_cli.py
```

**Chat Commands:**
- `generate <description>` - Create new code
- `run <node_id> [input]` - Execute code
- `list` - Show all nodes
- `status` - System status
- `auto on/off` - Toggle auto-evolution
- `help` - Show commands
- `exit` - Quit

---

## Testing

### Run All Tests

```bash
# Run test suite
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_rag_memory.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Manual Testing

```python
# Test RAG memory
from src import RAGMemory, ArtifactType

rag = RAGMemory("./test_memory")

rag.store_artifact(
    artifact_id="test_1",
    artifact_type=ArtifactType.PLAN,
    name="Test Plan",
    description="Testing RAG system",
    content="Test content",
    tags=["test"],
    auto_embed=False
)

# Verify storage
artifact = rag.get_artifact("test_1")
print(artifact.name)

# Search
results = rag.find_by_tags(["test"])
print(f"Found {len(results)} results")
```

---

## Example: Complete Workflow

```python
from src import (
    ConfigManager, OllamaClient, RAGMemory,
    Registry, NodeRunner, Evaluator,
    ArtifactType
)

# Initialize
config = ConfigManager()
client = OllamaClient(config_manager=config)
rag = RAGMemory(ollama_client=client)
registry = Registry()
runner = NodeRunner()
evaluator = Evaluator(client)

# 1. User makes request
request = "Write a function that sorts a list of dictionaries by a specific key"
task_id = "sort_dicts_v1"

# 2. Consult overseer
print("Step 1: Consulting overseer for strategy...")
strategy = client.generate(
    role="base",  # Uses model mapped to "base" role
    prompt=f"How should I approach this problem: {request}"
)

# 3. Store plan in RAG
print("Step 2: Storing strategy in RAG memory...")
rag.store_artifact(
    artifact_id=f"plan_{task_id}",
    artifact_type=ArtifactType.PLAN,
    name=f"Strategy for {request}",
    description=strategy[:200],
    content=strategy,
    tags=["plan", "sorting", "dictionaries"]
)

# 4. Generate code based on strategy
print("Step 3: Generating code...")
code_prompt = f"""Based on this strategy:
{strategy}

Write Python code to: {request}

Include:
- Main function implementation
- Error handling
- Type hints
- Docstring
- Example usage in __main__"""

code = client.generate(
    role="base",  # Or use tier: "coding.tier_2" for tier-based
    prompt=code_prompt
)

# 5. Store code in RAG
print("Step 4: Storing code in RAG memory...")
rag.store_artifact(
    artifact_id=f"func_{task_id}",
    artifact_type=ArtifactType.FUNCTION,
    name="Dictionary Sorter",
    description=request,
    content=code,
    tags=["function", "sorting", "dictionaries", "utility"],
    metadata={"based_on": f"plan_{task_id}"}
)

# 6. Save code and create node
print("Step 5: Creating node...")
runner.save_code(task_id, code)
registry.create_node(
    node_id=task_id,
    title=request,
    tags=["sorting", "utility"]
)

# 7. Execute code
print("Step 6: Executing code...")
test_input = {
    "items": [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Charlie", "age": 35}
    ],
    "key": "age"
}

stdout, stderr, metrics = runner.run_node(task_id, test_input)

# 8. Save metrics
print("Step 7: Recording metrics...")
registry.save_metrics(task_id, metrics)

# 9. Evaluate
print("Step 8: Evaluating results...")
result = evaluator.evaluate_full(stdout, stderr, metrics)

# 10. Store evaluation
eval_data = {
    "score_overall": result["final_score"],
    "verdict": result["final_verdict"],
    "evaluation": result.get("evaluation")
}
registry.save_evaluation(task_id, eval_data)

# 11. Update RAG with quality score
print("Step 9: Updating quality scores...")
rag.update_quality_score(f"func_{task_id}", result["final_score"])

# 12. Update registry index
registry.update_index(
    node_id=task_id,
    version="1.0.0",
    tags=["sorting", "utility"],
    score_overall=result["final_score"]
)

print("\n✓ Workflow complete!")
print(f"Score: {result['final_score']:.2f}")
print(f"Verdict: {result['final_verdict']}")
```

---

## Auto-Evolution

The system automatically improves code based on performance:

```python
from src import AutoEvolver

evolver = AutoEvolver(
    config=config,
    client=client,
    registry=registry,
    runner=runner,
    evaluator=evaluator
)

# Record performance
evolver.record_performance(
    node_id="my_func",
    metrics=metrics,
    score=0.75
)

# Check if evolution needed
if evolver.should_evolve("my_func"):
    new_node_id = evolver.evolve_node("my_func")
    print(f"✓ Evolved to: {new_node_id}")

# Or run continuous monitoring
evolver.monitor_and_evolve(interval_minutes=60, max_iterations=10)
```

---

## Tools System

### Role-Based Tools

Tools are now defined in `tools/` directory and reference abstract roles:

```yaml
# tools/llm/code_reviewer.yaml
name: "Code Reviewer"
type: "llm"
description: "Reviews code for quality and bugs"

llm:
  role: "powerful"  # Uses powerful model for thorough review

tags: ["review", "quality"]
```

**Using tools:**

```python
from node_runtime import call_tool

# Tool automatically uses the model mapped to "powerful" role
result = call_tool(
    "code_reviewer",
    f"Review this code:\n{code}"
)
```

### Switching Backends

To switch from Ollama to Anthropic Claude:

```yaml
# Before (Ollama)
llm:
  backend: "ollama"
  model_roles:
    powerful: "qwen2.5-coder:14b"

# After (Anthropic)
llm:
  backend: "anthropic"
  model_roles:
    powerful: "claude-3-opus-20240229"
```

All tools automatically use the new backend - **no tool changes needed!**

---

## Best Practices

### 1. Always Consult Overseer First

```python
# ✅ Good: Ask overseer for strategy
strategy = client.generate(role="base", prompt="How to solve...")
code = client.generate(role="base", prompt=f"Based on: {strategy}...")

# ❌ Bad: Generate code directly without planning
code = client.generate(role="base", prompt="Write code for...")
```

### 2. Use Roles and Tiers

```python
# ✅ Good: Use roles for backend flexibility
result = client.generate(role="powerful", prompt="Complex task...")

# ✅ Good: Use tiers for automatic escalation
result = client.generate(tier="coding.tier_2", prompt="Code generation...")

# ❌ Bad: Hardcode model names (ties you to one backend)
result = client.generate(model="codellama", prompt="Code generation...")
```

### 2. Store Everything in RAG

```python
# Store plans, code, evaluations, patterns
# Future tasks can learn from past successes
```

### 3. Use Tags Effectively

```python
# ✅ Good tags
tags=["validation", "email", "regex", "utility", "production-ready"]

# ❌ Bad tags
tags=["code", "stuff"]
```

### 4. Track Quality

```python
# Update quality scores based on actual performance
if code_works_well:
    rag.update_quality_score(artifact_id, 0.9)
```

### 5. Enable Auto-Evolution

```python
# Let the system improve itself automatically
config.set("auto_evolution.enabled", True)
```

---

## Troubleshooting

### Ollama Not Connected

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Verify models
ollama list
```

### Code Generation Slow

```bash
# Use smaller models for testing
# Use distributed endpoints for production
# Enable caching in RAG
```

### Low Quality Results

```bash
# Check overseer is being consulted
# Review plans in RAG memory
# Verify test coverage
# Enable auto-escalation for failures
```

---

## Building Executables

```bash
# Build for current platform
python build.py

# Build for specific platform
python build.py --platform windows
python build.py --platform linux
python build.py --platform macos

# Build for all platforms
python build.py --all
```

---

## Further Reading

- **README.md** - Full project documentation
- **QUICKSTART.md** - 5-minute getting started guide
- **RAG_GUIDE.md** - Detailed RAG system documentation
- **TESTING.md** - Testing guide and coverage reports

---

## Contributing

We welcome contributions! Areas for improvement:

- [ ] Add more unit tests
- [ ] Improve embedding quality
- [ ] Add vector database support
- [ ] Create web UI
- [ ] Multi-language support
- [ ] Advanced workflow composition
- [ ] Performance optimizations

---

## License

MIT License - See LICENSE file

---

**Built with ❤️ using Ollama and Claude**
