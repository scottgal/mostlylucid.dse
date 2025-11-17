# Pattern Recognizer - Code Fix Learning System

## Overview

The Pattern Recognizer is a RAG-based (Retrieval-Augmented Generation) learning system that stores and retrieves code fix patterns. It enables the system to learn from past errors and apply proven fixes to similar problems in the future.

## Components

### 1. Store Code Fix Pattern (`store_code_fix_pattern`)

Stores code errors and their fixes as reusable patterns in a RAG data store.

**Purpose:**
- Learn from mistakes by storing error-fix pairs
- Build a knowledge base of proven solutions
- Enable semantic search for similar errors
- Track usage statistics for ranking by effectiveness

**Key Features:**
- Stores patterns with full context (error, broken code, fixed code, debug info)
- Automatically creates semantic embeddings for similarity search
- Supports scoped visibility (tool, tool+subtools, hierarchy, global)
- Tags patterns by error type, language, tool, and framework
- Tracks quality scores and usage statistics

### 2. Find Code Fix Pattern (`find_code_fix_pattern`)

Searches the RAG data store for similar code errors and returns proven fixes.

**Purpose:**
- Find similar errors using semantic search
- Return multiple solutions ranked by proven effectiveness
- Filter patterns by scope for context-aware results
- Provide confidence scores and metadata

**Key Features:**
- Semantic similarity search using RAG embeddings
- Combined ranking: usage count (10x) + similarity (1x) + quality (0.1x)
- Scope-based filtering for targeted searches
- Returns top-k most relevant fixes with confidence scores

## Data Store Scopes

The pattern recognizer supports four levels of data store scope that control pattern visibility and accessibility:

### 1. **tool** - Tool-specific Learning
```yaml
scope: "tool"
tool_id: "my_code_generator"
```
- Patterns are only accessible by the specific tool that stored them
- Enables isolated learning for specialized tools
- Prevents cross-contamination between different tool contexts
- Use when: Tool has unique error patterns not relevant to others

**Example:**
```python
# Store a pattern only for this tool
store_code_fix_pattern(
    error_message="Custom DSL syntax error",
    broken_code="...",
    fixed_code="...",
    scope="tool",
    tool_id="dsl_compiler"
)

# Only dsl_compiler can find this pattern
find_code_fix_pattern(
    error_message="Custom DSL syntax error",
    scope="tool",
    tool_id="dsl_compiler"
)
```

### 2. **tool_subttools** - Hierarchical Learning
```yaml
scope: "tool_subttools"
tool_id: "web_scraper"
```
- Patterns accessible by the tool and all its sub-tools
- Enables parent-child knowledge sharing
- Sub-tools inherit fixes from parent but not vice versa
- Use when: Tool family shares common error patterns

**Example:**
```python
# Parent tool stores a pattern
store_code_fix_pattern(
    error_message="HTTP timeout",
    broken_code="requests.get(url)",
    fixed_code="requests.get(url, timeout=30)",
    scope="tool_subttools",
    tool_id="web_scraper"
)

# Sub-tools can access parent patterns
find_code_fix_pattern(
    error_message="HTTP timeout",
    scope="tool_subttools",
    tool_id="web_scraper.html_parser"  # Child can access
)
```

### 3. **hierarchy** - Contextual Learning
```yaml
scope: "hierarchy"
tool_id: "code_optimizer"
```
- Patterns accessible by all tools in the current hierarchy
- Enables broader knowledge sharing within related tool groups
- Maintains contextual relevance while allowing collaboration
- Use when: Multiple related tools face similar challenges

**Example:**
```python
# Store pattern accessible across the hierarchy
store_code_fix_pattern(
    error_message="Memory leak in loop",
    broken_code="...",
    fixed_code="...",
    scope="hierarchy",
    tool_id="code_optimizer.performance.memory"
)

# Any tool in the hierarchy can access
find_code_fix_pattern(
    error_message="Memory leak in loop",
    scope="hierarchy",
    tool_id="code_optimizer.performance.cpu"
)
```

### 4. **global** - Universal Learning (Default)
```yaml
scope: "global"
```
- Patterns accessible by all tools across the entire system
- Maximum knowledge sharing and reuse
- Best for common error patterns (syntax errors, import errors, etc.)
- Use when: Error patterns are universally applicable

**Example:**
```python
# Store pattern globally (default)
store_code_fix_pattern(
    error_message="SyntaxError: invalid syntax",
    broken_code="print('Hello'",
    fixed_code="print('Hello')",
    scope="global"  # Accessible by all tools
)

# Any tool can find this pattern
find_code_fix_pattern(
    error_message="SyntaxError: invalid syntax",
    scope="global"
)
```

## Configuration

### Global Configuration (`config.yaml`)

```yaml
pattern_recognizer:
  enabled: true
  rag_backend: "qdrant"
  default_scope: "global"

  # Search parameters
  default_top_k: 3
  min_similarity_threshold: 0.5

  # Ranking weights
  usage_weight: 10
  similarity_weight: 1
  quality_weight: 0.1

  # Storage parameters
  initial_quality_score: 0.95
  auto_tag_tool_id: true
  max_patterns_per_tool: 1000

  # Data store configuration
  data_store:
    type: "rag"
    backend: "qdrant"
    collection: "code_fix_patterns"
    auto_embed: true
    embedding_model: "nomic_embed"
```

### Per-Tool Overrides

You can override default settings for specific tools:

```yaml
pattern_recognizer:
  tool_overrides:
    # Code generator: isolated learning
    my_code_generator:
      default_scope: "tool"
      max_patterns_per_tool: 500
      usage_weight: 20  # Prioritize proven fixes

    # Web scraper: hierarchical learning
    web_scraper:
      default_scope: "tool_subttools"
      min_similarity_threshold: 0.7

    # Universal fixer: global learning
    universal_fixer:
      default_scope: "global"
      max_patterns_per_tool: 5000
```

## Usage Examples

### Basic Usage - Store and Retrieve

```python
import json
import subprocess

# 1. Store a fix pattern
store_input = {
    "error_message": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
    "broken_code": "result = 5 + '10'",
    "fixed_code": "result = 5 + int('10')",
    "fix_description": "Convert string to int before adding to integer",
    "error_type": "type",
    "language": "python",
    "scope": "global"
}

result = subprocess.run(
    ["python", "tools/executable/store_code_fix_pattern.py"],
    input=json.dumps(store_input),
    capture_output=True,
    text=True
)
print(result.stdout)  # Pattern ID returned

# 2. Find similar patterns
find_input = {
    "error_message": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
    "broken_code": "total = count + '42'",
    "language": "python",
    "top_k": 3,
    "scope": "global"
}

result = subprocess.run(
    ["python", "tools/executable/find_code_fix_pattern.py"],
    input=json.dumps(find_input),
    capture_output=True,
    text=True
)

fixes = json.loads(result.stdout)
if fixes['found']:
    best_fix = fixes['best_match']
    print(f"Best fix (used {best_fix['usage_count']} times):")
    print(f"  Broken: {best_fix['broken_code']}")
    print(f"  Fixed: {best_fix['fixed_code']}")
    print(f"  Description: {best_fix['fix_description']}")
```

### Scoped Learning Example

```python
# Tool-specific learning
store_input = {
    "error_message": "Custom DSL parse error",
    "broken_code": "DEFINE RULE {{ invalid }}",
    "fixed_code": "DEFINE RULE { valid }",
    "fix_description": "DSL braces must be single, not double",
    "error_type": "syntax",
    "language": "dsl",
    "scope": "tool",
    "tool_id": "dsl_compiler",
    "context": {
        "tool_id": "dsl_compiler",
        "version": "2.0"
    }
}

# Store the pattern
subprocess.run(
    ["python", "tools/executable/store_code_fix_pattern.py"],
    input=json.dumps(store_input),
    capture_output=True,
    text=True
)

# Later: find tool-specific patterns
find_input = {
    "error_message": "Custom DSL parse error",
    "language": "dsl",
    "scope": "tool",
    "tool_id": "dsl_compiler"
}

result = subprocess.run(
    ["python", "tools/executable/find_code_fix_pattern.py"],
    input=json.dumps(find_input),
    capture_output=True,
    text=True
)

fixes = json.loads(result.stdout)
# Only patterns from dsl_compiler will be returned
```

### Integration with Error Handling

```python
def execute_with_pattern_learning(code, tool_id="my_tool"):
    """Execute code and learn from errors."""
    try:
        result = exec(code)
        return result
    except Exception as e:
        error_msg = str(e)

        # 1. Search for similar fixes
        find_input = {
            "error_message": error_msg,
            "broken_code": code,
            "error_type": "runtime",
            "scope": "global",
            "tool_id": tool_id
        }

        fixes = find_code_fix_pattern(find_input)

        if fixes['found'] and fixes['pattern_count'] > 0:
            # 2. Try applying the most proven fix
            best_fix = fixes['best_match']

            try:
                # Apply transformation (simplified)
                fixed_code = code.replace(
                    best_fix['broken_code'],
                    best_fix['fixed_code']
                )

                result = exec(fixed_code)

                # 3. Success! Increment usage count
                # (RAG system tracks this automatically)

                return result

            except Exception:
                # This fix didn't work, try next one
                if fixes['pattern_count'] > 1:
                    # Try second-best fix...
                    pass

        # 4. No pattern found or fixes didn't work
        # Use LLM to generate a fix
        fixed_code = llm_fix_code(code, error_msg)

        # 5. Store this new fix for future use
        store_input = {
            "error_message": error_msg,
            "broken_code": code,
            "fixed_code": fixed_code,
            "fix_description": "LLM-generated fix",
            "error_type": "runtime",
            "scope": "global",
            "tool_id": tool_id
        }

        store_code_fix_pattern(store_input)

        return exec(fixed_code)
```

## Ranking Algorithm

Patterns are ranked using a weighted scoring system:

```
rank_score = (usage_count × usage_weight) + (similarity × similarity_weight) + (quality_score × quality_weight)

Default weights:
- usage_weight: 10
- similarity_weight: 1
- quality_weight: 0.1
```

**Example:**

| Pattern | Usage Count | Similarity | Quality | Rank Score | Selected? |
|---------|-------------|------------|---------|------------|-----------|
| Fix A   | 50          | 0.85       | 0.95    | 500.945    | ✓ Best    |
| Fix B   | 10          | 0.95       | 0.90    | 101.04     |           |
| Fix C   | 0           | 1.00       | 0.80    | 1.08       |           |

Pattern A wins despite lower similarity because it has been proven effective 50 times.

## Best Practices

1. **Choose the Right Scope:**
   - Use `tool` for specialized, domain-specific errors
   - Use `tool_subttools` for tool families with shared patterns
   - Use `hierarchy` for related tools in a common context
   - Use `global` for universal error patterns (syntax, imports, etc.)

2. **Provide Rich Context:**
   ```python
   store_code_fix_pattern(
       error_message="...",
       broken_code="...",
       fixed_code="...",
       fix_description="Detailed explanation of the fix",
       context={
           "tool_id": "my_tool",
           "framework": "django",
           "version": "4.2",
           "environment": "production"
       },
       debug_info={
           "stack_trace": "...",
           "local_variables": {...},
           "system_info": {...}
       }
   )
   ```

3. **Tune Ranking Weights:**
   - Increase `usage_weight` to prioritize proven fixes
   - Increase `similarity_weight` for more precise matching
   - Adjust `min_similarity_threshold` to filter low-quality matches

4. **Monitor Pattern Growth:**
   - Set appropriate `max_patterns_per_tool` limits
   - Periodically review and prune low-quality patterns
   - Use quality scores to identify effective patterns

5. **Test Scoped Learning:**
   - Start with `global` scope for initial learning
   - Gradually move to narrower scopes as patterns accumulate
   - Use per-tool overrides to customize behavior

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Pattern Recognizer                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  Store Pattern   │         │  Find Pattern    │          │
│  │                  │         │                  │          │
│  │ - Error          │         │ - Semantic       │          │
│  │ - Broken Code    │         │   Search         │          │
│  │ - Fixed Code     │────────▶│ - Tag Filtering  │          │
│  │ - Context        │         │ - Scope Filter   │          │
│  │ - Scope          │         │ - Ranking        │          │
│  └────────┬─────────┘         └────────┬─────────┘          │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌─────────────────────────────────────────────┐            │
│  │           RAG Data Store (Qdrant)            │            │
│  │                                               │            │
│  │  - Embeddings (semantic similarity)          │            │
│  │  - Tags (error type, language, scope)        │            │
│  │  - Metadata (context, debug info)            │            │
│  │  - Quality Scores                            │            │
│  │  - Usage Statistics                          │            │
│  └─────────────────────────────────────────────┘            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Future Enhancements

1. **Automatic Pattern Pruning:**
   - Remove low-quality patterns that are never used
   - Merge duplicate patterns
   - Adjust quality scores based on success rate

2. **Pattern Clustering:**
   - Group similar patterns for better organization
   - Identify pattern families
   - Suggest pattern generalizations

3. **Cross-Tool Learning:**
   - Detect patterns that work across multiple tools
   - Automatically promote tool-specific patterns to hierarchy/global
   - Suggest scope adjustments based on usage patterns

4. **Visual Analytics:**
   - Dashboard showing pattern growth over time
   - Effectiveness metrics per tool
   - Most common error types
   - Pattern reuse statistics

5. **Fine-Tuning Integration:**
   - Use patterns to fine-tune specialized LLMs
   - Generate synthetic training data from patterns
   - Create domain-specific error correction models
