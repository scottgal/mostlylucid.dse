## Intelligent Caching System

## Overview

The system now implements intelligent caching with semantic similarity, distinguishing between:
1. **Deterministic tasks** - Cache output (e.g., "add 1 + 2" → always "3")
2. **Creative tasks** - Cache workflow/tool structure, NOT output (e.g., "write a haiku" → different haiku each time)
3. **Similar tasks** - Use as hints to overseer, generate fresh content

## Caching Rules

### Rule 1: Semantic Similarity (92% threshold)

**Purpose:** Catch typos, synonyms, and minor rewording

```python
# These are considered semantically identical (similarity >= 0.92):
"run translate"        → "execute translate"    (93% similar - synonym)
"run trasnlate"        → "run translate"        (95% similar - typo)
"add 1 + 2"            → "add 1 plus 2"         (94% similar - rewording)

# These are NOT semantically identical (similarity < 0.92):
"add 1 + 2"            → "multiply 1 × 2"       (85% similar - different intent)
"write a haiku"        → "write a poem"         (88% similar - different form)
```

### Rule 2: Creative vs Deterministic

**Deterministic Tasks** (cacheable_output = True):
- Math: "add 1 + 2" → Always "3"
- Commands: "run translate" → Always validates same way
- Data queries: "get user 123" → Same result for same user
- Code checks: "validate syntax" → Deterministic rules

**Creative Tasks** (cacheable_output = False):
- Writing: "write a haiku about coding"
- Data generation: "generate sample data"
- Random content: "create a random string"
- Creative prompts: "make up a joke"

### Rule 3: Two-Level Caching

**Level 1: Workflow/Tool Structure** (Always cached)
```
User: "write a haiku about coding"
→ Cache: Workflow structure (how to write a haiku)
→ Reuse: Tool chain, workflow steps
→ Generate: NEW haiku content each time
```

**Level 2: Output** (Only cached if deterministic)
```
# Deterministic:
User: "add 1 + 2"
→ Cache: Workflow + Output ("3")
→ Reuse: Skip execution, return "3"

# Creative:
User: "write a haiku about coding"
→ Cache: Workflow structure
→ Execute: Generate NEW haiku
→ Do NOT cache: Output content
```

## Examples

### Example 1: Deterministic Task (Full Caching)

```
First call:
  Input: "add 1 + 2"
  → Execute: Python code
  → Output: "3"
  → Log: cacheable_output=True, quality=0.95

Second call:
  Input: "add 1 plus 2"  # Minor rewording
  → Search: Similarity = 0.94 (>= 0.92 threshold)
  → Check: cacheable_output = True ✓
  → CACHE HIT: Return "3"
  → Skip: No execution needed

Result:
  ✓ Saved execution time
  ✓ Saved LLM cost (if LLM was used)
  ✓ Same correct output
```

### Example 2: Creative Task (Workflow Cached, Output Fresh)

```
First call:
  Input: "write a haiku about coding"
  → Build: Workflow for haiku generation
  → Execute: Call LLM
  → Output: "Code flows like\nAlgorithms dance free\nJoy in each line"
  → Log: cacheable_output=False, quality=0.95

Second call:
  Input: "write a haiku about coding"  # Exact same request
  → Search: Similarity = 1.0 (exact match)
  → Check: cacheable_output = False ✗
  → WORKFLOW HIT: Reuse workflow structure
  → Execute: Call LLM again
  → Output: "Variables bloom\nFunctions weave through the night\nBugs flee with dawn's light"  # NEW HAIKU

Result:
  ✓ Reused workflow structure (faster planning)
  ✗ Did NOT reuse output (fresh content each time)
  ✓ Different creative output as expected
```

### Example 3: Similar Task (Use as Hint)

```
First call:
  Input: "translate 'hello' to French"
  → Execute: Translation tool
  → Output: "bonjour"
  → Log: cacheable_output=True, quality=0.95

Second call:
  Input: "translate 'hi' to French"  # Different text
  → Search: Similarity = 0.85 (< 0.92 threshold)
  → NO CACHE HIT (not similar enough)
  → Find similar: Returns previous translation as hint
  → Pass to overseer: "Similar to previous 'hello' → 'bonjour' task"
  → Execute: New translation
  → Output: "salut"

Result:
  ✗ No cache hit (different input text)
  ✓ Used previous work as hint (faster planning)
  ✓ Generated fresh output
```

### Example 4: Typo Tolerance

```
First call:
  Input: "run translate"
  → Execute: Command validation
  → Output: "valid command"
  → Log: cacheable_output=True, quality=0.95

Second call:
  Input: "run trasnlate"  # Typo in 'translate'
  → Search: Similarity = 0.95 (>= 0.92 threshold)
  → Check: cacheable_output = True ✓
  → CACHE HIT: Return "valid command"

Result:
  ✓ Typo tolerated
  ✓ Correct validation returned
  ✓ Saved LLM call for command checking
```

## Integration Points

### Where Creative Detection Happens

**In `tools_manager.py`:**

```python
# Detect creative tasks by keywords in prompt
creative_keywords = [
    'write', 'create', 'generate', 'compose', 'make up',
    'story', 'poem', 'haiku', 'joke', 'article', 'essay',
    'creative', 'random', 'sample data', 'test data'
]

if any(keyword in prompt.lower() for keyword in creative_keywords):
    cacheable_output = False  # Don't cache creative output
```

**In `task_evaluator.py`:**

```python
# Task type detection
if task_type == TaskType.CREATIVE_CONTENT:
    # Route to LLM for creative generation
    # Mark as cacheable_output=False
```

### Where Caching Happens

**1. Tool/Workflow Level (always cached):**
```python
# In orchestrator/workflow system:
workflow = find_cached_workflow(user_request)
if workflow and workflow.similarity >= 0.92:
    # Reuse workflow structure
    return reuse_workflow_structure(workflow)
```

**2. Output Level (only if deterministic):**
```python
# In interaction_logger:
cached = logger.get_cached_result(
    tool_id="translator",
    input_data={"text": "hello", "lang": "French"},
    similarity_threshold=0.92
)

if cached:
    # Check if output is cacheable
    if cached['metadata']['cacheable_output']:
        return cached['output_data']  # ✓ Reuse output
    else:
        # ✗ Don't reuse output, but use structure as hint
        return generate_fresh_output(hint=cached)
```

## Performance Impact

### Deterministic Tasks (Full Caching)

```
Before:
  "add 1 + 2" → 250ms execution + LLM planning
  "add 1 plus 2" → 250ms execution + LLM planning
  Total: 500ms

After (with caching):
  "add 1 + 2" → 250ms execution + LLM planning
  "add 1 plus 2" → 2ms cache hit
  Total: 252ms (50% faster)
```

### Creative Tasks (Workflow Caching Only)

```
Before:
  "write a haiku" → 50ms planning + 1500ms LLM generation
  "write a haiku" → 50ms planning + 1500ms LLM generation
  Total: 3100ms

After (with workflow caching):
  "write a haiku" → 50ms planning + 1500ms LLM generation
  "write a haiku" → 2ms cache hit + 1500ms LLM generation
  Total: 3052ms (1.5% faster, but fresh content)
```

## Configuration

```yaml
# In config.yaml:
interaction_logging:
  enabled: true

  # Semantic similarity threshold
  cache_similarity_threshold: 0.92  # 92% = safe variance for typos/synonyms

  # Quality threshold for caching
  cache_min_quality: 0.70  # Only cache good results

  # Age limit for cached results
  cache_max_age_hours: 24  # Don't use results older than 24h

  # Creative task detection
  creative_keywords: [
    "write", "create", "generate", "compose",
    "story", "poem", "haiku", "joke", "article"
  ]
```

## Monitoring

### Check Cache Hit Rate

```python
from src.interaction_logger import InteractionLogger

logger = InteractionLogger()

# Get statistics
stats = logger.get_tool_statistics("command_checker", hours=24)

print(f"Total interactions: {stats['total_interactions']}")
print(f"Cache hit rate: {stats.get('cache_hit_rate', 0):.1%}")
print(f"Avg latency (with cache): {stats['average_latency_ms']:.1f}ms")
```

### View Non-Cacheable Interactions

```python
# Find all creative tasks logged
from src.rag_memory import RAGMemory

rag = RAGMemory()
creative_tasks = rag.find_by_tags(['interaction', 'cacheable:False'])

print(f"Found {len(creative_tasks)} creative/non-cacheable interactions")
for task in creative_tasks[:10]:
    print(f"  - {task.name}: {task.description}")
```

## Best Practices

### 1. Mark Creative Tasks Explicitly

```python
# When invoking LLM for creative content:
logger.log_interaction(
    tool_id="content_generator",
    input_data=prompt,
    output_data=generated_content,
    cacheable_output=False,  # ← Explicit marking
    interaction_type='llm'
)
```

### 2. Use Appropriate Thresholds

```python
# High precision (deterministic tasks):
cached = logger.get_cached_result(
    tool_id="calculator",
    input_data="1 + 2",
    similarity_threshold=0.95  # Require very similar
)

# More tolerant (command validation):
cached = logger.get_cached_result(
    tool_id="command_validator",
    input_data=user_command,
    similarity_threshold=0.90  # Allow more variance
)
```

### 3. Use Hints for Non-Matches

```python
# If no cache hit, get similar interactions as hints
cached = logger.get_cached_result(tool_id, input_data)

if not cached:
    # Find similar past work (< 92% similarity)
    hints = logger.find_similar_interactions(
        tool_id=tool_id,
        input_data=input_data,
        similarity_threshold=0.75  # Lower threshold for hints
    )

    if hints:
        # Pass hints to overseer for planning
        overseer_prompt = f"Similar to previous: {hints[0]['description']}"
```

## Summary

**Caching Strategy:**
- ✅ Workflow/tool structure → Always cached
- ✅ Deterministic output → Cached (92% similarity)
- ❌ Creative output → Never cached
- ✅ Similar tasks → Used as hints

**Safe Variance (92% similarity):**
- ✓ Handles typos
- ✓ Handles synonyms
- ✓ Handles minor rewording
- ✗ Rejects different intents

**Performance:**
- 50-80% faster for deterministic tasks (full caching)
- 1-5% faster for creative tasks (workflow caching)
- Fresh creative content every time
