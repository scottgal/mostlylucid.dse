# Advanced Features Guide

This document details the advanced AI-powered features that make mostlylucid DiSE intelligent and efficient.

## Table of Contents
1. [Specification-Based Code Generation](#specification-based-code-generation)
2. [Semantic Task Classification](#semantic-task-classification)
3. [Fitness-Based Tool Selection](#fitness-based-tool-selection)
4. [RAG Memory System](#rag-memory-system)
5. [Template Modification](#template-modification)
6. [Context-Aware Truncation](#context-aware-truncation)
7. [Safety Limits](#safety-limits)

---

## Specification-Based Code Generation

### The Two-Stage Architecture

mostlylucid DiSE uses a **separation of concerns** approach:

#### Stage 1: Specification Creation (Overseer Model)
The **Overseer (llama3)** - a large, capable reasoning model - creates a comprehensive specification:

```
User Request: "calculate fibonacci sequence"

Overseer Output:
┌─────────────────────────────────────────────────┐
│ DETAILED SPECIFICATION                          │
├─────────────────────────────────────────────────┤
│ 1. Problem Definition                           │
│    - Generate Fibonacci sequence                │
│    - Input: length (int)                        │
│    - Output: list of Fibonacci numbers          │
│    - Algorithm: Iterative DP approach           │
│                                                  │
│ 2. Requirements & Constraints                   │
│    - Performance: O(n) time, O(n) space         │
│    - Safety: Limit to max 100 numbers           │
│    - Error handling: Validate input >= 0        │
│                                                  │
│ 3. Implementation Plan                          │
│    - Function: fibonacci_sequence(n: int)       │
│    - Use memoization for efficiency             │
│    - Return list of first n numbers             │
│                                                  │
│ 4. Input/Output Interface                       │
│    - Read: input_data["n"] or input_data["len"] │
│    - Write: {"result": [0, 1, 1, 2, 3, 5, ...]} │
│                                                  │
│ 5. Test Cases                                   │
│    - fib(0) → []                                │
│    - fib(5) → [0, 1, 1, 2, 3]                   │
│    - fib(10) → [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]│
│                                                  │
│ 6. Tool Recommendation                          │
│    - Direct implementation (no LLM tools needed)│
└─────────────────────────────────────────────────┘
```

#### Stage 2: Code Implementation (Generator Model)
The **Code Generator (codellama)** - a specialized code model - implements the specification **exactly**:

```python
import json
import sys

def fibonacci_sequence(n: int) -> list[int]:
    if n <= 0:
        return []

    sequence = []
    a, b = 0, 1
    for _ in range(n):
        sequence.append(a)
        a, b = b, a + b

    return sequence

def main():
    input_data = json.load(sys.stdin)
    n = min(int(input_data.get("n", 20)), 100)  # Cap at 100 max

    if n < 0:
        print(json.dumps({"error": "n must be non-negative"}))
        return

    result = fibonacci_sequence(n)
    print(json.dumps({"result": result}))

if __name__ == "__main__":
    main()
```

### Benefits

✅ **Consistent Interfaces**: All code follows the same JSON input/output format
✅ **No Hallucinations**: Generator follows spec exactly, no missing requirements
✅ **Better Quality**: Planning and implementation separated
✅ **Context Efficiency**: Specification is truncated if too long for generator's context window

### Context-Aware Specification Truncation

```python
# Automatically respects code generator's context window
max_spec_chars = context_window(generator_model) * 2  # ~2 chars/token conservative

if len(specification) > max_spec_chars:
    specification = specification[:max_spec_chars] + "\n\n[... specification truncated ...]"
```

---

## Semantic Task Classification

### The Problem: Text Similarity ≠ Task Equivalence

Traditional similarity search fails in these cases:

❌ **False Positives** (high similarity, different tasks):
- "fibonacci sequence" vs "fibonacci backwards" → 77% similar, but **DIFFERENT** outputs

❌ **False Negatives** (low similarity, same task):
- "fibonacci sequence" vs "fibonaccie sequense and output result" → 65% similar, but **SAME** task (typo)

### The Solution: Semantic Classification

Uses **tinyllama** triage model to classify task relationships:

```python
semantic_check_prompt = """Compare these two tasks:

Task 1 (existing): calculate the fibonacci sequence
Task 2 (requested): calculate fibonacci sequence backwards

Classification:
- SAME: Identical tasks (ignore typos/wording, same core algorithm)
- RELATED: Same domain but different variation
- DIFFERENT: Completely different domains

Answer with ONLY ONE WORD: SAME, RELATED, or DIFFERENT
"""

# Model response: "RELATED"
```

### Classification Rules

| Relationship | Example | Action |
|-------------|---------|--------|
| **SAME** | "fibonacci" vs "fibonaccie and output" | Reuse as-is |
| **SAME** | "add 10 and 20" vs "sum 10 and 20" | Reuse as-is |
| **RELATED** | "fibonacci" vs "fibonacci backwards" | Use as template, modify |
| **RELATED** | "write story" vs "write technical article" | Use as template, modify |
| **DIFFERENT** | "fibonacci" vs "prime numbers" | Generate from scratch |
| **DIFFERENT** | "fibonacci" vs "write story" | Generate from scratch |

### Benefits

✅ **Ignores Typos**: "fibonaccie" recognized as same as "fibonacci"
✅ **Ignores Wording**: "calculate" vs "compute" vs "find" all recognized as same
✅ **Detects Variations**: "forward" vs "backward" detected as related
✅ **Prevents Wrong Reuse**: Won't reuse "story writer" for "article writer"

---

## Fitness-Based Tool Selection

### The Problem: Semantic Similarity Alone is Insufficient

A tool might be semantically similar but:
- Too slow for the task
- Too expensive
- Poor quality
- High failure rate
- Requires too much effort to adapt

### The Solution: Multi-Dimensional Fitness

```python
def calculate_fitness(tool, similarity):
    """
    Calculate overall fitness score for a tool.
    Higher score = better choice for this task.
    """
    fitness = similarity * 100  # Base score (0-100)

    # Speed bonus (faster = better)
    if speed_tier == 'very-fast': fitness += 20
    elif speed_tier == 'fast': fitness += 10
    elif speed_tier == 'slow': fitness -= 10
    elif speed_tier == 'very-slow': fitness -= 20

    # Cost bonus (cheaper = better)
    if cost_tier == 'free': fitness += 15
    elif cost_tier == 'low': fitness += 10
    elif cost_tier == 'high': fitness -= 10
    elif cost_tier == 'very-high': fitness -= 15

    # Quality bonus
    if quality_tier == 'excellent': fitness += 15
    elif quality_tier == 'very-good': fitness += 10
    elif quality_tier == 'poor': fitness -= 15

    # Success rate bonus (from past runs)
    quality_score = metadata.get('quality_score', 0)
    if quality_score > 0:
        fitness += quality_score * 10  # 0-10 bonus

    # Performance metrics
    latency_ms = metadata.get('latency_ms', 0)
    if latency_ms < 100: fitness += 15  # Very fast
    elif latency_ms < 500: fitness += 10  # Fast
    elif latency_ms > 5000: fitness -= 10  # Slow

    # Effort bonus: Reusing existing workflow
    if tool.tool_type == ToolType.WORKFLOW:
        if similarity >= 0.90: fitness += 30  # Exact match
        elif similarity >= 0.70: fitness += 15  # Template

    return fitness
```

### Fitness Dimensions Stored in RAG

All fitness dimensions are indexed in Qdrant for fast filtering:

```python
# Stored in Qdrant payload for every tool/workflow
payload = {
    "artifact_id": "fibonacci_generator",
    "name": "Fibonacci Sequence Generator",

    # Fitness dimensions (indexed for fast search)
    "speed_tier": "very-fast",
    "cost_tier": "free",
    "quality_tier": "excellent",
    "latency_ms": 23.5,
    "memory_mb_peak": 1.94,
    "success_count": 42,
    "total_runs": 45,
    "success_rate": 0.93,  # 93% success

    # Tool metadata
    "is_tool": True,
    "tool_id": "fibonacci_generator",
    "max_output_length": "medium"
}
```

### Example: Choosing Between Similar Tools

```
Task: "write a technical article"

Candidates found:
┌──────────────────────────────────────────────────────────────┐
│ Tool                  │ Sim  │ Speed │ Cost │ Quality │ Fit  │
├──────────────────────────────────────────────────────────────┤
│ Long-Form Writer      │ 85%  │ slow  │ high │ excell. │ 95   │
│ Technical Writer      │ 88%  │ fast  │ low  │ v.good  │ 113  │ ← WINNER
│ Blog Post Generator   │ 78%  │ fast  │ free │ good    │ 103  │
└──────────────────────────────────────────────────────────────┘

Selected: Technical Writer (highest fitness despite lower similarity!)
```

### Task-Type Filtering

Prevents completely wrong tool selection:

```python
# Detect task type
code_keywords = ['code', 'function', 'fibonacci', 'calculate', 'add']
writing_keywords = ['write', 'story', 'article', 'novel', 'essay']

is_code_task = any(keyword in task.lower() for keyword in code_keywords)
is_writing_task = any(keyword in task.lower() for keyword in writing_keywords)

# Filter tools by task type
if is_code_task:
    # EXCLUDE all writing tools
    excluded = ['long_form_writer', 'content writer', 'creative', 'story']
    tools = [t for t in tools if not any(excl in t.name.lower() for excl in excluded)]

elif is_writing_task:
    # EXCLUDE all code tools
    excluded = ['code', 'coder', 'generator', 'compiler']
    tools = [t for t in tools if not any(excl in t.name.lower() for excl in excluded)]
```

### Benefits

✅ **Never Wrong Tool for Wrong Job**: Code tasks get code tools, writing tasks get writing tools
✅ **Optimal Performance**: Considers speed, cost, quality, not just similarity
✅ **Historical Learning**: Better tools with higher success rates are preferred
✅ **Effort Minimization**: Reuses existing code when fitness is high enough

---

## RAG Memory System

### Qdrant Vector Database

mostlylucid DiSE uses **Qdrant** for semantic search with fitness indexing:

```python
# Store artifact with fitness dimensions
rag.store_artifact(
    artifact_id="fibonacci_gen",
    artifact_type=ArtifactType.WORKFLOW,
    name="Fibonacci Sequence Generator",
    content=code,
    tags=["fibonacci", "math", "sequence"],
    metadata={
        # Fitness dimensions
        "speed_tier": "very-fast",
        "cost_tier": "free",
        "quality_tier": "excellent",
        "latency_ms": 23,
        "memory_mb_peak": 1.94,
        "success_count": 42,
        "total_runs": 45,

        # Tool metadata
        "is_tool": True,
        "tool_id": "fibonacci_gen",
        "node_id": "calculate_fibonacci"
    }
)
```

### Semantic Search with Fitness Filtering

```python
# Search for similar solutions
results = rag.find_similar(
    "calculate fibonacci backwards",
    artifact_type=ArtifactType.WORKFLOW,
    top_k=5
)

# Results include fitness dimensions for scoring
for artifact, similarity in results:
    fitness = calculate_fitness(artifact, similarity)
    print(f"{artifact.name}: {similarity:.0%} similarity, {fitness:.0f} fitness")
```

### Fallback to NumPy Memory

If Qdrant is unavailable, automatically falls back to NumPy-based memory:

```python
def create_rag_memory(ollama_client, config_manager):
    """Factory function for dynamic RAG backend selection."""
    if config_manager.use_qdrant:
        try:
            return QdrantRAGMemory(ollama_client, config_manager)
        except Exception:
            logger.warning("Qdrant unavailable, falling back to NumPy memory")
            return RAGMemory(ollama_client)
    else:
        return RAGMemory(ollama_client)
```

---

## Template Modification

### Intelligent Code Reuse for Related Tasks

When tasks are **RELATED**, the system:
1. Loads existing code as template
2. Asks overseer to create **modification plan**
3. Generator modifies template instead of regenerating

### Example: Fibonacci Backwards

```
User: "calculate fibonacci sequence backwards"

┌─ Step 1: RAG Search ─────────────────────────────┐
│ Found: "fibonacci forward" (77% similar)         │
└──────────────────────────────────────────────────┘

┌─ Step 2: Semantic Classification ────────────────┐
│ Relationship: RELATED                            │
│ (same algorithm, different variation)            │
└──────────────────────────────────────────────────┘

┌─ Step 3: Load Template ──────────────────────────┐
│ Template Code:                                   │
│   def fibonacci_sequence(n):                     │
│       ...                                        │
│       return sequence  # [0, 1, 1, 2, 3, 5, ...] │
└──────────────────────────────────────────────────┘

┌─ Step 4: Overseer Creates Modification Plan ────┐
│ MODIFICATION SPECIFICATION:                      │
│                                                  │
│ 1. Keep: Core fibonacci algorithm               │
│ 2. Keep: Input validation and safety limits     │
│ 3. Add:  Reverse the sequence before returning  │
│    - Add: return sequence[::-1]                 │
│ 4. Update: Function name to fibonacci_backwards │
│ 5. Update: Docstring to mention reversed order  │
└──────────────────────────────────────────────────┘

┌─ Step 5: Generator Applies Modifications ───────┐
│ Modified Code:                                   │
│   def fibonacci_backwards(n):                    │
│       ...                                        │
│       return sequence[::-1]  # Reversed!         │
└──────────────────────────────────────────────────┘

RESULT: [89, 55, 34, 21, 13, 8, 5, 3, 2, 1, 1, 0]
```

### Benefits

✅ **Less Work**: Modify existing code instead of regenerating from scratch
✅ **Faster**: Skip full code generation process
✅ **More Reliable**: Tested code used as foundation
✅ **Preserves Quality**: Keeps working parts, only changes what's needed

---

## Context-Aware Truncation

### The Problem: Specification Exceeds Context Window

The overseer (llama3) might create a very detailed specification that exceeds the code generator's (codellama) context window.

### The Solution: Intelligent Truncation

```python
# Get code generator's context window from config
context_window = config.get_context_window(generator_model)  # e.g., 4096 tokens

# Conservative estimate: ~2 chars per token
# Leave room for prompt template and response
max_spec_chars = context_window * 2

if len(specification) > max_spec_chars:
    console.print(f"[yellow]Note: Specification ({len(specification)} chars) exceeds context window[/yellow]")
    console.print(f"[yellow]Truncating to {max_spec_chars} chars[/yellow]")

    # Keep the most important info at the beginning
    specification = specification[:max_spec_chars] + "\n\n[... specification truncated due to context limits ...]"
```

### Why This Works

Most important information is at the **beginning** of the specification:
1. Problem definition
2. Requirements & constraints
3. Implementation plan
4. Input/output interface
5. Test cases (might be truncated)
6. Tool recommendations (might be truncated)

Even if truncated, the code generator has enough information to implement correctly.

---

## Safety Limits

### Demo-Safe Code Generation

All generated code includes **sensible limits** to prevent infinite loops or resource exhaustion:

```python
# Overseer specification includes safety limits
"""
IMPORTANT - DEMO SAFETY:
For potentially infinite or resource-intensive tasks, include SENSIBLE LIMITS:
- Fibonacci sequence: Calculate first 10-20 numbers only (not infinite)
- Prime numbers: Find first 100 primes (not all primes)
- Iterations: Limit to 1000 iterations max
- File sizes: Limit to 10MB max
- List lengths: Limit to 10,000 items max
- Timeouts: Add timeout logic for long-running operations
"""

# Generated code includes limits
def main():
    input_data = json.load(sys.stdin)
    # SAFE: Limit to first 20 Fibonacci numbers
    n = min(int(input_data.get("n", 20)), 100)  # Cap at 100 max

    if n < 0:
        print(json.dumps({"error": "n must be non-negative"}))
        return

    result = calculate_fibonacci(n)
    print(json.dumps({"result": result}))
```

### Default Limits

| Operation | Default | Maximum |
|-----------|---------|---------|
| Fibonacci sequence | 20 numbers | 100 |
| Prime numbers | 100 primes | 1000 |
| Loop iterations | - | 1000 |
| File size | - | 10 MB |
| List length | - | 10,000 |
| Execution timeout | 2 seconds | 10 minutes |

### Benefits

✅ **No Infinite Loops**: All potentially infinite operations have caps
✅ **Resource Protection**: Memory and CPU usage bounded
✅ **Demo-Friendly**: Can run examples safely without hangs
✅ **Production-Ready**: Limits can be adjusted in production

---

---

## File I/O Tools

### Save to Disk (Output Only)

For **safety**, saves are restricted to the `./output/` directory only:

```yaml
save_to_disk:
  description: "Saves content to ./output/ directory (for safety)"
  input_schema:
    filename: "Name of file (will be saved in ./output/)"
    content: "Content to write to file"
  output_schema:
    status: "'saved' if successful"
    path: "Full path where file was saved"
```

**Example Usage**:
```
User: "generate a funny story and save it to disk"

Workflow:
1. Overseer plans: Generate story, then save to file
2. Generator creates: Funny story content
3. save_to_disk tool: Saves to ./output/funny_story.txt
4. Result: Story saved safely to ./output/
```

### Load from Disk (Anywhere)

Can load files from **anywhere** on the filesystem (not restricted):

```yaml
load_from_disk:
  description: "Loads content from any file path on disk"
  input_schema:
    filepath: "Full or relative path to file"
  output_schema:
    status: "'loaded' if successful, 'not_found' if missing"
    content: "Content of the file"
    path: "Full path that was read"
```

**Example Usage (Self-Optimization)**:
```
User: "load your own source code and optimize it"

Workflow:
1. load_from_disk: Reads ./src/ollama_client.py
2. Overseer analyzes: Identifies optimization opportunities
3. Generator refactors: Creates improved version
4. save_to_disk: Saves to ./output/ollama_client_v2.py
```

### Multi-File Workflows

File I/O enables complex multi-file generation:

```
User: "generate a microservice architecture"

Workflow:
1. Overseer creates: Full architecture specification
2. Generator creates: api_gateway.py
3. save_to_disk: Saves to ./output/api_gateway.py
4. Generator creates: user_service.py
5. save_to_disk: Saves to ./output/user_service.py
6. Generator creates: docker-compose.yml
7. save_to_disk: Saves to ./output/docker-compose.yml
8. Result: Complete microservice setup in ./output/
```

### Benefits

✅ **Safety**: Writes restricted to ./output/ directory only
✅ **Flexibility**: Reads from anywhere (enables self-optimization)
✅ **Multi-File Support**: Can generate entire project structures
✅ **Persistence**: Generated content saved for later use
✅ **Self-Improvement**: System can read and improve its own code

---

## Summary

mostlylucid DiSE's advanced features work together to create an intelligent, efficient, and safe code generation system:

1. **Specification-Based Generation**: Separation of planning (overseer) and implementation (generator)
2. **Semantic Classification**: SAME/RELATED/DIFFERENT for intelligent reuse
3. **Fitness-Based Selection**: Multi-dimensional scoring always picks the right tool
4. **RAG Memory**: Qdrant vector database with fitness indexing
5. **Template Modification**: Reuse and modify instead of regenerating
6. **Context-Aware Truncation**: Respects model context windows
7. **Safety Limits**: Demo-safe code with sensible resource bounds
8. **File I/O Tools**: Save to disk (output only) and load from disk (anywhere) for persistence and self-optimization

The result: **A system that learns, reuses, continuously improves, and can even optimize itself.**
