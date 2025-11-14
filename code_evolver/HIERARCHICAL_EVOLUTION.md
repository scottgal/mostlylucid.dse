# Hierarchical Evolution System

## Overview

The Hierarchical Evolution System is an advanced LLM-powered code evolution framework that implements:

1. **Separate Execution and Evolution Phases** - Clean separation between initial execution and iterative improvement
2. **RAG Integration at Every Level** - Retrieves similar solutions from memory at workflow, nodeplan, and function levels
3. **Self-Optimizing Architecture** - Automatically improves code through token optimization and quality feedback
4. **Hierarchical Learning** - Parent nodes learn from child performance and evolve the plan itself
5. **Multi-Level Granularity** - Operates at three levels: Workflow → Nodeplan → Function

## Architecture

### Core Components

#### 1. OverseerLlm (`overseer_llm.py`)
**Purpose**: Strategic planning and solution improvement

- Creates execution plans based on task descriptions
- Searches RAG for similar past plans
- Generates improvement strategies based on evaluation feedback
- **NOT** responsible for code generation - focuses on high-level strategy

**Key Features**:
- Plan creation with expected quality/speed targets
- Historical performance tracking
- Iterative plan improvement based on feedback

#### 2. EvaluatorLlm (`evaluator_llm.py`)
**Purpose**: Fitness determination and quality assessment

- Evaluates execution results across multiple dimensions
- Provides detailed fitness scores (correctness, quality, speed)
- Generates actionable recommendations
- Compares multiple solutions to find the best

**Evaluation Dimensions**:
- **Correctness**: Does it produce correct output?
- **Quality**: Is implementation robust and well-designed?
- **Speed**: How does performance compare to targets?

#### 3. HierarchicalEvolver (`hierarchical_evolver.py`)
**Purpose**: Orchestrates the complete evolution pipeline

**Workflow**:
```
1. PLAN      → Overseer creates execution plan
2. EXECUTE   → Run based on plan, collect metrics
3. EVALUATE  → Evaluator determines fitness
4. EVOLVE    → Feedback loop: improve and repeat
5. LEARN     → Contribute learnings to shared context
```

**Key Features**:
- Node-level quality/speed tracking
- Parent-child hierarchy management
- Shared plan context for learning
- Multi-iteration evolution

#### 4. RAGIntegratedTools (`rag_integrated_tools.py`)
**Purpose**: RAG-based tool discovery and optimization

**Self-Optimization Loop**:
```
1. Search RAG → Find closest solution at current level
2. Retrieve Tools → Get relevant functions/plans from RAG
3. Pass to Overseer → Overseer evaluates for current task
4. Execute/Modify → Code LLM manipulates if needed
5. Optimize Tokens → Reduce token count while preserving functionality
6. Save to RAG → Store for future use with quality score
```

**Levels of Operation**:
- **Workflow**: High-level complete workflows
- **Nodeplan**: Actual scripts/plans for execution
- **Function**: Individual reusable functions

#### 5. SharedPlanContext (`hierarchical_evolver.py`)
**Purpose**: Evolving shared knowledge base

- Stores learnings from all node executions
- Tracks strategy preferences (e.g., "for task X, use approach Y")
- Enables parent nodes to learn from children
- Provides context-aware recommendations

## The Three Levels

### Level 1: Workflow
- **Scope**: Complete end-to-end workflows
- **Example**: "Write a book" (planning → writing → editing → publishing)
- **RAG Artifact Type**: `WORKFLOW`
- **Characteristics**: High-level orchestration, coordinates multiple nodeplans

### Level 2: Nodeplan
- **Scope**: Specific execution scripts/plans
- **Example**: "Write Chapter 3" plan with specific steps
- **RAG Artifact Type**: `PLAN`
- **Characteristics**: Actual executable strategy, can be directly run

### Level 3: Function
- **Scope**: Individual reusable functions
- **Example**: `quicksort()`, `validate_email()`, `parse_json()`
- **RAG Artifact Type**: `FUNCTION`
- **Characteristics**: Granular, reusable, tagged with metadata

## Complete Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     HIERARCHICAL EVOLUTION                       │
└─────────────────────────────────────────────────────────────────┘

LEVEL 1: WORKFLOW
┌────────────────────────────────────────────────────────────┐
│ User Request: "Write a science fiction book"               │
└────────────────────────────────────────────────────────────┘
                          │
                          ├─[1]─> Search RAG for similar workflows
                          │       └─> Found: "Fantasy novel workflow" (0.75 similarity)
                          │
                          ├─[2]─> Overseer creates Workflow Plan
                          │       └─> Steps: Outline → Chapters → Edit → Publish
                          │
                          ▼

LEVEL 2: NODEPLAN (for each chapter)
┌────────────────────────────────────────────────────────────┐
│ Nodeplan: "Write Chapter 1: The Discovery"                 │
└────────────────────────────────────────────────────────────┘
                          │
                          ├─[1]─> Search RAG for similar nodeplans
                          │       └─> Found: "Chapter intro with character" (0.82)
                          │
                          ├─[2]─> Get tools from RAG
                          │       ├─> Function: create_character_description()
                          │       ├─> Function: write_dialogue()
                          │       └─> Function: build_scene()
                          │
                          ├─[3]─> Overseer evaluates tools for task
                          │       └─> Selected: create_character_description, write_dialogue
                          │
                          ├─[4]─> EXECUTE nodeplan
                          │       └─> Generate chapter content using selected tools
                          │
                          ├─[5]─> EVALUATE with EvaluatorLlm
                          │       ├─> Quality: 0.82
                          │       ├─> Correctness: 0.90
                          │       └─> Speed: 0.75
                          │
                          ├─[6]─> IF quality < target: EVOLVE
                          │       ├─> Overseer creates improved plan
                          │       ├─> Re-execute with improvements
                          │       └─> Compare results, keep best
                          │
                          ├─[7]─> Token Optimization
                          │       ├─> Code LLM reduces token count
                          │       └─> 4500 tokens → 3200 tokens (-29%)
                          │
                          ├─[8]─> Save to RAG
                          │       └─> Stored for future "chapter writing" tasks
                          │
                          ▼

LEVEL 3: FUNCTION (individual operations)
┌────────────────────────────────────────────────────────────┐
│ Function: create_character_description(name, traits)       │
└────────────────────────────────────────────────────────────┘
                          │
                          ├─[1]─> Search RAG for similar functions
                          │       └─> Found: describe_person() (0.88)
                          │
                          ├─[2]─> Reuse or adapt from RAG
                          │       └─> Adapted version with modifications
                          │
                          ├─[3]─> Execute and measure
                          │       ├─> Quality: 0.91
                          │       └─> Speed: 45ms
                          │
                          ├─[4]─> Save to RAG with metadata
                          │       ├─> Tags: ["description", "character", "fiction"]
                          │       ├─> Use cases: ["character intro", "description"]
                          │       └─> Quality score: 0.91
                          │
                          ▼

HIERARCHICAL LEARNING
┌────────────────────────────────────────────────────────────┐
│ Parent Node: "Write Chapter 1"                              │
│ Children: [character_desc_A, character_desc_B]             │
│                                                              │
│ Learning:                                                    │
│  - child_A achieved quality 0.91 in 45ms                   │
│  - child_B achieved quality 0.75 in 30ms                   │
│                                                              │
│ Decision: Prefer child_A for future similar contexts       │
│ (higher quality more important than speed for character descriptions)  │
│                                                              │
│ Contribution to Shared Context:                            │
│  "For character descriptions in fiction, use detailed      │
│   approach (child_A strategy) - achieves 0.91 quality"    │
└────────────────────────────────────────────────────────────┘
```

## Function Metadata and Tagging

Functions are self-documenting with metadata tags:

```python
def quicksort(arr: list) -> list:
    """
    Sort array using quicksort algorithm.

    #tags: sort, divide-conquer, efficient
    #use-case: Sorting large arrays efficiently
    #use-case: When O(n log n) performance needed
    #complexity: O(n log n) average, O(n²) worst
    """
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
```

**Metadata Extracted**:
- **Function name**: `quicksort`
- **Description**: From docstring
- **Tags**: `["sort", "divide-conquer", "efficient"]`
- **Use cases**: Specific scenarios where function applies
- **Complexity**: Time/space complexity
- **Parameters**: Type and description
- **Returns**: Return type

This metadata is:
1. Stored in RAG alongside the function
2. Used for semantic search
3. Passed to Overseer for tool selection
4. Updated with quality scores from executions

## Token Optimization

The system automatically optimizes code to reduce token usage while preserving functionality:

**Before Optimization** (120 tokens):
```python
def calculate_average_of_numbers_in_list(input_list_of_numbers: list) -> float:
    """Calculate the average (mean) value of all numbers in a given list."""
    if len(input_list_of_numbers) == 0:
        return 0.0
    total_sum_of_all_numbers = 0.0
    for individual_number in input_list_of_numbers:
        total_sum_of_all_numbers = total_sum_of_all_numbers + individual_number
    average_value = total_sum_of_all_numbers / len(input_list_of_numbers)
    return average_value
```

**After Optimization** (35 tokens, -71%):
```python
def calc_avg(nums: list) -> float:
    """Calculate average of numbers."""
    return sum(nums) / len(nums) if nums else 0.0
```

**Process**:
1. Code LLM analyzes function
2. Identifies redundancy, verbose naming
3. Reduces tokens while preserving:
   - Functionality
   - Correctness
   - Readability
4. Validates optimization didn't break behavior
5. Saves optimized version to RAG

## Shared Plan Context Evolution

The `SharedPlanContext` stores and evolves based on execution history:

```python
# Example: Context learns from executions

# Execution 1: Task "sort numbers", used quicksort → quality 0.95, speed 80ms
# Execution 2: Task "sort numbers", used bubblesort → quality 0.70, speed 200ms

# Learning Stored:
{
  "context_signature": "sort_numbers",
  "lesson": "Quicksort achieves better quality and speed for number sorting",
  "recommendation": "Use quicksort for similar tasks",
  "quality_achieved": 0.95,
  "speed_achieved": 80,
  "confidence": 0.9,
  "usage_count": 0,
  "success_rate": 1.0
}

# Future Execution: Task "sort large array"
# → Retrieves learning
# → Overseer sees "quicksort recommended"
# → Uses quicksort strategy
# → Success! Update learning usage_count and success_rate
```

## Practical Example: Book Writing Workflow

See `examples/book_writing_workflow.py` for a complete implementation.

**Demonstrates**:
- Multiple specialized LLMs (Planner, Plotter, Writer, Editor, Researcher)
- Hierarchical workflow: Book → Outline → Chapters → Paragraphs
- SQLite storage for persistent state
- RAG integration at each level
- Quality evaluation and iterative improvement

**Running the Example**:
```bash
cd code_evolver
python examples/book_writing_workflow.py
```

**Output**:
- Creates book project with outline
- Writes chapters using hierarchical evolution
- Evaluates quality of each chapter
- Learns from execution patterns
- Stores everything in RAG for future use

## Testing

Run comprehensive tests:

```bash
cd code_evolver
python tests/test_hierarchical_evolution.py
```

**Test Coverage**:
- OverseerLlm plan creation and improvement
- EvaluatorLlm fitness assessment
- SharedPlanContext learning storage/retrieval
- RAGIntegratedTools function registration and search
- HierarchicalEvolver complete workflow
- Node metrics tracking
- Parent-child learning

## Configuration

No additional configuration needed beyond existing `config.yaml`:

```yaml
ollama:
  base_url: "http://localhost:11434"
  models:
    generator: "codellama"
    evaluator: "llama3"
    overseer: "llama3"
    triage: "tiny"

execution:
  default_timeout_ms: 30000
  max_memory_mb: 512

# Hierarchical evolution settings
hierarchical_evolution:
  enabled: true
  max_evolution_iterations: 3
  quality_improvement_threshold: 0.1  # Must improve by 10% to keep
  enable_token_optimization: true
  min_similarity_threshold: 0.6  # For RAG retrieval
```

## Benefits

1. **Quality Retention**: Ensures solutions don't degrade through evolution
2. **Speed Optimization**: Actively works to reduce execution time
3. **Token Efficiency**: Reduces costs by optimizing token usage
4. **Learning**: System gets better over time as RAG fills with solutions
5. **Transparency**: Clear separation of plan/execute/evaluate phases
6. **Reusability**: Functions become tools for future tasks
7. **Scalability**: Works from simple functions to complex workflows

## Future Enhancements

- **Multi-model ensembles**: Use different models at different levels
- **A/B testing framework**: Automated comparison of approaches
- **Cost tracking**: Monitor token usage and costs per level
- **Visualization**: Graphical view of evolution tree
- **Distributed execution**: Run nodeplans in parallel
- **Fine-tuning**: Train specialist models from successful executions

## Summary

The Hierarchical Evolution System transforms LLM-based code generation from one-shot attempts into an iterative, self-improving process. By:

1. Separating planning from execution
2. Using RAG to learn from history
3. Evaluating fitness explicitly
4. Evolving through feedback loops
5. Operating at multiple levels of granularity

The system achieves both high quality and efficiency while continuously improving its performance on similar tasks.
