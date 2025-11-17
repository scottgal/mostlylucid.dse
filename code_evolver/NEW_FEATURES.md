# Code Evolver - New Features Guide

## Recent Major Features

This document describes the two major new features added to Code Evolver:
1. **Smart Conversation Mode** - Multi-chat context memory with semantic search
2. **RAG Cluster Optimizer** - Iterative self-optimization of code artifacts

---

## 1. Smart Conversation Mode

### Overview

The Smart Conversation Mode provides an intelligent, context-aware conversational experience with:
- Multi-chat context memory (remembers previous conversations)
- Auto-summarization based on context window size
- Volatile Qdrant storage for semantic search
- Related context retrieval from past conversations
- Performance tracking (response time, tokens, etc.)
- Intent detection (distinguishes conversation from dialogue generation)
- Smart orchestration with dynamic tool calling and workflow generation

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  ConversationTool (Main)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌──────────────────┐                  │
│  │ Storage        │  │ Context Manager  │                  │
│  │ (Qdrant)       │  │ (Memory)         │                  │
│  └────────────────┘  └──────────────────┘                  │
│  ┌────────────────┐  ┌──────────────────┐                  │
│  │ Summarizer     │  │ Intent Detector  │                  │
│  │ (Auto)         │  │ (Smart)          │                  │
│  └────────────────┘  └──────────────────┘                  │
│  ┌────────────────┐  ┌──────────────────┐                  │
│  │ Embedder       │  │ Smart            │                  │
│  │ (Semantic)     │  │ Orchestrator     │                  │
│  └────────────────┘  └──────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### Installation

#### Requirements

```bash
# Install base requirements
pip install -r requirements.txt

# Start Qdrant (required for conversation mode)
docker run -p 6333:6333 qdrant/qdrant
# OR download from: https://qdrant.tech/documentation/quick-start/
```

#### Configuration

Edit `config.yaml`:

```yaml
conversation:
  qdrant_url: "http://localhost:6333"
  embedding_model: "nomic-embed-text"
  embedding_endpoint: "http://localhost:11434"
  ollama_endpoint: "http://localhost:11434"
  conversation_model: "gemma3:1b"  # Fast model for management tasks
  vector_size: 768
```

### Usage

#### Command Line

Start a conversation using the `/conversation_start` command:

```bash
python chat_cli.py
```

Then inside the CLI:

```
CodeEvolver> /conversation_start python_best_practices

# Chat about Python
CodeEvolver> What are the best practices for error handling?

# Continue conversation with full context
CodeEvolver> Can you show me an example?

# End when done
CodeEvolver> /conversation_end
```

#### Programmatic Usage

```python
from src.conversation import ConversationTool

# Initialize
conv = ConversationTool(
    config={
        "qdrant_url": "http://localhost:6333",
        "embedding_model": "nomic-embed-text"
    },
    conversation_model="gemma3:1b"
)

# Start conversation
result = conv.start_conversation(topic="Python best practices")
conversation_id = result["conversation_id"]

# Add messages
conv.add_user_message("What are the best practices for error handling?")

# Prepare context for response (with auto-summarization)
context = conv.prepare_context(
    user_message="What are the best practices for error handling?",
    response_model="llama3"  # Model that will generate response
)

# Use context to generate response...
# Then add response to conversation
conv.add_assistant_message(
    "Here are the best practices...",
    performance_data={
        "response_time": 2.5,
        "tokens": 150
    }
)

# End conversation (saves metadata for future retrieval)
summary = conv.end_conversation(save_metadata=True)
print(summary["key_points"])
```

#### Tool Integration

The conversation manager is also available as an executable tool:

```python
from node_runtime import call_tool

# Start conversation
result = call_tool(
    "conversation_manager",
    action="start",
    topic="Machine Learning"
)

# Detect intent
intent = call_tool(
    "conversation_manager",
    action="detect_intent",
    user_input="let's chat about AI"
)
# Returns: {"intent": "start_conversation", "confidence": 0.9, "topic": "AI"}

# Prepare context
context = call_tool(
    "conversation_manager",
    action="prepare_context",
    user_message="What is gradient descent?",
    response_model="llama3"
)
```

### Features Detail

#### 1. Multi-Chat Context Memory
- Remembers all messages in current conversation
- Links related past conversations using semantic search
- Automatically retrieves relevant context from conversation history

#### 2. Auto-Summarization
- Monitors context window size based on target model
- Automatically summarizes older messages when approaching limit
- Preserves key information while reducing token count
- Configurable summarization strategies

#### 3. Semantic Search
- Stores conversation metadata in Qdrant
- Finds related conversations using vector similarity
- Enriches context with relevant past discussions
- Volatile per-conversation collections (auto-deleted on end)

#### 4. Intent Detection
- Distinguishes between "start conversation" and "generate dialogue"
- Uses both pattern matching and LLM-based detection
- Helps route requests appropriately

#### 5. Smart Orchestration
- Dynamic tool calling during conversations
- Workflow generation on-the-fly
- Parallel execution of independent tasks
- Automatic error recovery

### Performance

- **Startup**: < 1s (with background loading)
- **Context Preparation**: 0.5-2s depending on history size
- **Semantic Search**: < 100ms (Qdrant)
- **Summarization**: 1-3s (using gemma3:1b)

### Troubleshooting

**Issue**: `Connection refused` to Qdrant

**Solution**:
```bash
# Start Qdrant server
docker run -p 6333:6333 qdrant/qdrant
```

**Issue**: Slow summarization

**Solution**:
- Use faster model (gemma3:1b or tinyllama)
- Increase summarization threshold
- Disable auto-summarization for short conversations

---

## 2. RAG Cluster Optimizer

### Overview

The RAG Cluster Optimizer is an **iterative self-optimization loop** that continuously improves code artifacts stored in RAG memory. Instead of just picking one "best" version, it:

- Tests alternates and learns from their performance
- Converges toward fitter canonical implementations
- Archives weak variants but preserves lineage
- Learns patterns over time (e.g., "error handling improvements reduce latency")

### How It Works

```
┌──────────────────────────────────────────────────────────┐
│              Iterative Optimization Loop                  │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  1. Start with canonical artifact (current "best")       │
│     ↓                                                     │
│  2. Pull all close variants (≥0.96 similarity)           │
│     ↓                                                     │
│  3. Extract semantic deltas (algorithm, error handling)  │
│     ↓                                                     │
│  4. Generate candidate by combining insights             │
│     ↓                                                     │
│  5. Validate (tests, benchmarks, mutation tests)         │
│     ↓                                                     │
│  6. Compare fitness score vs. cluster median             │
│     ↓                                                     │
│  7. If fitter → promote to canonical, archive weak ones  │
│     ↓                                                     │
│  8. Repeat with next layer of alternates                 │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Example Flow

**Scenario**: Optimizing a cron parser function

1. **Core function**: `cron_parser v1.0` (canonical)
2. **Alternates found**:
   - `v1.1` - Better error handling
   - `v1.2` - Faster regex
   - `v1.3` - Memory-optimized
3. **Iteration**:
   - Generate `v2.0` combining regex speed + error handling
   - Validate → coverage +5%, latency -12%
   - Promote `v2.0` as new canonical
   - Archive `v1.x` variants with lineage pointers
4. **Next iteration**: Explore `v2.0`'s cluster for further refinements

### Installation

#### Requirements

```bash
# Already included in requirements.txt
pip install numpy>=1.24.0 PyYAML>=6.0.1
```

#### Configuration

Create `config/rag_cluster_optimizer.yaml`:

```yaml
# Node-type-specific optimizer configurations
optimizers:
  function:
    enabled: true
    similarity_threshold: 0.96
    max_iterations: 10
    fitness_improvement_threshold: 0.05
    strategy: "best_of_breed"  # or: incremental, radical, hybrid

    # Fitness weights
    fitness_weights:
      latency: 0.30
      memory: 0.20
      success_rate: 0.30
      test_coverage: 0.20

    # Trimming policy
    trimming:
      min_similarity_to_fittest: 0.70
      preserve_high_perf_threshold: 0.85
      min_usage_count: 1
      never_used_grace_period_days: 30
      min_fitness_absolute: 0.50

    # Scheduling
    optimization_frequency: "daily"
    priority: 8

  workflow:
    enabled: true
    similarity_threshold: 0.95
    strategy: "incremental"
    optimization_frequency: "weekly"
    priority: 5

  prompt:
    enabled: false  # Disable optimization for prompts
```

### Usage

#### Command Line Interface

```bash
# Basic usage - optimize a specific cluster
python src/cli/optimize_cluster.py --target=cron_parser_cluster

# Optimize all functions
python src/cli/optimize_cluster.py --target=all --node_type=function

# Use specific strategy
python src/cli/optimize_cluster.py \
  --target=my_workflow \
  --strategy=incremental \
  --max_iterations=20

# Output as JSON
python src/cli/optimize_cluster.py \
  --target=my_cluster \
  --output_format=json > report.json

# Verbose mode
python src/cli/optimize_cluster.py \
  --target=my_cluster \
  --verbose
```

#### Programmatic Usage

```python
from src.rag_cluster_optimizer import (
    RAGClusterOptimizer,
    OptimizerConfigManager,
    NodeType,
    OptimizationStrategy
)

# Load configuration
config_manager = OptimizerConfigManager(
    config_path="config/rag_cluster_optimizer.yaml"
)

# Get optimizer for function nodes
optimizer_wrapper = config_manager.get_optimizer(NodeType.FUNCTION)

# Load cluster from RAG
# (In real usage, load from Qdrant/RAG memory)
cluster = load_cluster_from_rag("cron_parser_cluster")

# Run optimization
iterations = optimizer_wrapper.optimize_cluster(cluster)

# Get report
report = optimizer_wrapper.optimizer.get_optimization_report(
    cluster,
    iterations
)

# Print summary
print(f"Total iterations: {report['summary']['total_iterations']}")
print(f"Total promotions: {report['summary']['total_promotions']}")
print(f"Improvement: +{report['summary']['improvement_percentage']}%")
```

### Optimization Strategies

#### 1. Best of Breed
- **Goal**: Find the absolute best variant
- **Method**: Test all alternates, promote highest fitness
- **Use case**: Critical production code
- **Speed**: Slower (exhaustive)

#### 2. Incremental
- **Goal**: Steady, safe improvements
- **Method**: Small steps, validate each change
- **Use case**: Stable systems, gradual evolution
- **Speed**: Medium

#### 3. Radical
- **Goal**: Breakthrough improvements
- **Method**: Large architectural changes
- **Use case**: Experimental features, major refactors
- **Speed**: Fast (aggressive pruning)

#### 4. Hybrid
- **Goal**: Balance of all approaches
- **Method**: Adaptive strategy based on context
- **Use case**: General purpose
- **Speed**: Variable

### Trimming Policies

The optimizer automatically prunes weak variants based on:

1. **Fitness distance** - Too far from fittest variant
2. **Similarity** - Too dissimilar to canonical
3. **Usage** - Unused variants past grace period
4. **Performance** - Below absolute fitness threshold

**Special rules**:
- Always keep canonical variant
- Preserve high-coverage variants (>90%)
- Keep lineage endpoints (leaf nodes)
- Protect high-performance variants even if unused

### Performance Metrics

The optimizer tracks:

- **Latency** (ms) - Execution time
- **Memory** (MB) - Memory usage
- **Success rate** (0.0-1.0) - Functional correctness
- **Test coverage** (0.0-1.0) - Code coverage
- **Usage count** - How often variant is used
- **Fitness score** - Weighted combination of above

### Output Formats

#### Markdown (default)

```markdown
# RAG Cluster Optimization Report

## Cluster: cron_parser_cluster
**Status**: completed

### Summary
- **Total Iterations**: 10
- **Total Promotions**: 3
- **Total Archived**: 5
- **Initial Fitness**: 0.75
- **Final Fitness**: 0.92
- **Total Improvement**: +0.17 (22.7%)

### Final Canonical Variant
- **Variant ID**: cron_parser_v2.3
- **Version**: 2.3
- **Fitness**: 0.92

**Performance**:
- Latency: 15.2ms
- Memory: 8.5MB
- Success Rate: 0.98
- Test Coverage: 0.95
```

#### JSON

```json
{
  "cluster_id": "cron_parser_cluster",
  "status": "completed",
  "summary": {
    "total_iterations": 10,
    "total_promotions": 3,
    "final_fitness": 0.92,
    "improvement_percentage": 22.7
  },
  "canonical_variant": {
    "variant_id": "cron_parser_v2.3",
    "version": "2.3",
    "fitness": 0.92,
    "performance": {
      "latency_ms": 15.2,
      "memory_mb": 8.5,
      "success_rate": 0.98,
      "test_coverage": 0.95
    }
  }
}
```

### Guild Analogy

Think of it like a guild master refining a ritual:
1. Start with the core chant (canonical artifact)
2. Test variations from apprentices (alternates)
3. Each cycle, keep the strongest elements
4. Discard the weak, but preserve lineage
5. Over time, the ritual evolves into its strongest form

The guild's library becomes a **living lineage of ever-stronger spells**.

### Troubleshooting

**Issue**: Optimization not improving

**Solutions**:
- Check fitness weights in config (ensure they match your goals)
- Try different strategy (radical for breakthroughs)
- Verify test coverage is adequate
- Check if cluster has enough variants

**Issue**: Too many variants getting archived

**Solutions**:
- Relax trimming policy thresholds
- Increase `never_used_grace_period_days`
- Lower `min_similarity_to_fittest`
- Set `preserve_high_perf_threshold` higher

---

## Quick Start Guide

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Start Qdrant (for conversation mode)
docker run -p 6333:6333 qdrant/qdrant

# Start Ollama (if not running)
ollama serve
```

### 2. Test Conversation Mode

```bash
python chat_cli.py
```

Inside CLI:
```
CodeEvolver> /conversation_start test_topic
CodeEvolver> tell me about Python type hints
CodeEvolver> can you show an example?
CodeEvolver> /conversation_end
```

### 3. Test Cluster Optimizer

```bash
# View help
python src/cli/optimize_cluster.py --help

# Run demo (uses example cluster)
python src/cli/optimize_cluster.py --target=demo_function --verbose
```

---

## Dependencies

All features are included in `requirements.txt`:

```txt
qdrant-client>=1.7.0  # For conversation mode
numpy>=1.24.0         # For cluster optimizer
PyYAML>=6.0.1         # For configuration
rich>=13.7.0          # For CLI output
anthropic>=0.69.0     # Optional: Claude integration
```

### Optional Dependencies

- **croniter>=2.0.0** - For scheduled optimization tasks
- **psutil>=5.9.0** - For system monitoring
- **anthropic** - For Claude model integration

---

## FAQ

### Q: Do I need Qdrant for cluster optimization?

**A**: No. The cluster optimizer works with the existing RAG memory system. Qdrant is only required for conversation mode.

### Q: Can I use conversation mode without Ollama?

**A**: No. Conversation mode requires Ollama for embeddings and summarization. You can use Anthropic Claude for the main responses, but Ollama is needed for the conversation management tasks.

### Q: How do I schedule automatic cluster optimization?

**A**: Install croniter (`pip install croniter>=2.0.0`) and configure the background scheduler in `config.yaml`. See `BACKGROUND_SCHEDULER.md` for details.

### Q: Can I customize the optimization strategies?

**A**: Yes! Edit `config/rag_cluster_optimizer.yaml` to adjust fitness weights, trimming policies, and strategies per node type.

---

## Next Steps

1. **Read full documentation**: See `CLAUDE.md` for complete system overview
2. **Explore examples**: Check `docs/examples/` for usage patterns
3. **Configure optimizers**: Edit `config/rag_cluster_optimizer.yaml` to tune performance
4. **Set up monitoring**: Enable background scheduler for automatic optimization

**Happy Evolving!** 🚀
