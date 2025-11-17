# Parallel Execution System

Code Evolver now supports parallel execution at multiple levels: workflow steps and tool calls within generated code.

## Overview

The system intelligently identifies opportunities for parallel execution while respecting dependencies to avoid race conditions.

## Multi-Level Parallelism

### Level 1: Workflow Step Parallelism

**When the overseer decomposes a task**, it analyzes dependencies and identifies which steps can run concurrently.

#### Example 1: Parallel Translations

**Task**: "write a joke and translate to french and spanish"

**Decomposition**:
```json
{
  "steps": [
    {
      "step_id": "step1",
      "description": "Write a joke",
      "tool": "content_generator",
      "parallel_group": null,
      "depends_on": []
    },
    {
      "step_id": "step2",
      "description": "Translate to French",
      "tool": "nmt_translator",
      "parallel_group": 1,
      "depends_on": ["step1"]
    },
    {
      "step_id": "step3",
      "description": "Translate to Spanish",
      "tool": "nmt_translator",
      "parallel_group": 1,
      "depends_on": ["step1"]
    }
  ]
}
```

**Execution**:
- Step 1 runs first (generates the joke)
- Steps 2 and 3 run **in parallel** after step 1 completes
- Both translations process simultaneously, cutting execution time in half

#### Example 2: Fully Parallel Tasks

**Task**: "write 3 different jokes about cats, dogs, and birds"

**Decomposition**:
```json
{
  "steps": [
    {
      "step_id": "step1",
      "description": "Write joke about cats",
      "parallel_group": 1,
      "depends_on": []
    },
    {
      "step_id": "step2",
      "description": "Write joke about dogs",
      "parallel_group": 1,
      "depends_on": []
    },
    {
      "step_id": "step3",
      "description": "Write joke about birds",
      "parallel_group": 1,
      "depends_on": []
    }
  ]
}
```

**Execution**:
- All 3 steps run **in parallel** (no dependencies)
- Reduces total time from 3× to ~1× (limited by slowest step)

### Level 2: Code-Level Parallelism

**Generated code** can use `call_tools_parallel()` to run multiple tools concurrently within a single node.

#### Example: Multi-Language Translation Node

```python
from node_runtime import call_tools_parallel

def main():
    input_data = json.load(sys.stdin)
    content = input_data.get("content", "")

    # Translate to multiple languages in parallel
    results = call_tools_parallel([
        ("nmt_translator", f"Translate to french: {content}", {"target_lang": "fr"}),
        ("nmt_translator", f"Translate to spanish: {content}", {"target_lang": "es"}),
        ("nmt_translator", f"Translate to german: {content}", {"target_lang": "de"})
    ])

    french, spanish, german = results

    return {
        "french": french,
        "spanish": spanish,
        "german": german
    }
```

## Dependency Analysis

The overseer uses these rules to determine dependencies:

### Rule 1: Data Dependencies
If step B uses output from step A → `depends_on: ["stepA"]`

### Rule 2: Independence
If steps B and C don't depend on each other → same `parallel_group`

### Rule 3: Race Condition Avoidance
Steps that modify shared state cannot be parallel

## Implementation Details

### WorkflowStep Fields

```python
@dataclass
class WorkflowStep:
    step_id: str
    description: str
    tool_name: str

    # Parallel execution metadata
    parallel_group: Optional[int] = None      # Steps with same group run in parallel
    depends_on: List[str] = []                # Step IDs this step depends on
```

### Execution Algorithm

1. **Organize steps** by dependencies using `_organize_parallel_execution()`
2. **Group ready steps** whose dependencies are satisfied
3. **Execute parallel groups** using `ThreadPoolExecutor`
4. **Wait for completion** before moving to next group

### Code Location

- **Workflow decomposition prompt**: chat_cli.py:421-450
- **Parallel execution logic**: chat_cli.py:533-615
- **Dependency organizer**: chat_cli.py:635-704
- **Runtime parallel function**: node_runtime.py:159-213

## Performance Benefits

### Sequential Execution
```
Step 1: Write joke (5s)
Step 2: Translate to french (3s)
Step 3: Translate to spanish (3s)
Total: 11 seconds
```

### Parallel Execution
```
Step 1: Write joke (5s)
Steps 2+3 in parallel: max(3s, 3s) = 3s
Total: 8 seconds (27% faster)
```

For N independent translations: **N× speedup**

## Usage Examples

### Example 1: Content Generation Pipeline

**Task**: "write a technical article, a summary, and social media posts"

**Workflow**:
1. Write article (sequential)
2. Generate summary, Twitter post, LinkedIn post **in parallel** (all depend on article)

### Example 2: Multi-Format Export

**Task**: "convert document to PDF, DOCX, and HTML"

**Workflow**:
All 3 conversions run **in parallel** (independent operations)

### Example 3: A/B Testing

**Task**: "generate 5 different headlines for A/B testing"

**Workflow**:
All 5 generations run **in parallel** (no dependencies)

## Best Practices

### DO:
- Use parallel execution for **independent operations**
- Specify `depends_on` for **data dependencies**
- Group steps with same `parallel_group` when they don't interfere
- Use `call_tools_parallel()` for multiple tool calls in generated code

### DON'T:
- Run steps in parallel if they modify shared state
- Create circular dependencies
- Forget to specify dependencies when output is used
- Use parallel execution for steps that must be sequential

## Debugging

### Check Workflow Plan

The system displays the workflow plan before execution:

```
Workflow Plan (3 steps):
  1. Write a joke
  2. Translate to French
     Node task: Translate to French
  3. Translate to Spanish
     Node task: Translate to Spanish
```

### Parallel Execution Indicator

When steps run in parallel, you'll see:

```
Executing 2 steps in parallel:
  - Translate to French
  - Translate to Spanish
```

## Configuration

Parallel execution is enabled by default when `workflow_mode.enabled: true` in config.yaml.

```yaml
chat:
  workflow_mode:
    enabled: true
    detect_keywords: ["and", "then", "translate", "convert"]
```

## Future Enhancements

- [ ] Async/await support for I/O-bound operations
- [ ] Resource-aware scheduling (limit concurrent LLM calls)
- [ ] Automatic retry with exponential backoff for failed parallel tasks
- [ ] Performance metrics tracking (speedup ratio, concurrency level)
- [ ] GPU-aware parallelism for local LLMs

---

**Status**: Implemented and tested
**Date**: 2025-01-15
**Version**: 1.0.0
