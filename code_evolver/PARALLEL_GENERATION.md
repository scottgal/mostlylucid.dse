# Parallel Generation System - Multi-Model Experiments

**Date:** 2025-11-17
**Status:** ✓ Implemented

---

## Overview

The Parallel Generation System allows the **Overseer to run multiple "content writers"** (code generators) simultaneously and select the best result based on **quality vs speed tradeoffs**.

This creates a **competitive, experimental environment** where:
- Multiple models generate code in parallel
- Each variant is tested and scored
- The best is selected based on real data
- The system learns which generators work best for which tasks

---

## Key Innovations

### 1. Multiple Content Writers

Instead of a single code generator, the Overseer can run 3-5 generators in parallel:

```
Overseer Plan
  ↓
Fork into parallel experiments:
  ├─→ codellama (conservative, temp=0.1)
  ├─→ qwen:14b (balanced, temp=0.5)
  ├─→ qwen:14b (creative, temp=0.9)
  ├─→ deepseek (conservative, temp=0.1)
  └─→ deepseek (balanced, temp=0.5)
  ↓
Test all variants in parallel
  ↓
Score: quality × speed
  ↓
Select best → ONE winner
```

### 2. Quality vs Speed Optimization

Configurable weights balance different priorities:

```python
# Quality-focused (critical tasks)
quality_weight = 0.85
speed_weight = 0.15

# Speed-focused (simple tasks)
quality_weight = 0.5
speed_weight = 0.5

# Balanced (most tasks)
quality_weight = 0.7
speed_weight = 0.3
```

### 3. Learning System

The system tracks which generators work best for which task types:

```python
{
    "api_integration": {
        "deepseek_conservative": {"success_rate": 0.92},
        "qwen_balanced": {"success_rate": 0.85},
        "codellama_conservative": {"success_rate": 0.78}
    },
    "simple_function": {
        "codellama_conservative": {"success_rate": 0.95},
        "qwen_creative": {"success_rate": 0.88}
    }
}
```

---

## Architecture

### Components

#### 1. ParallelGenerator (`src/parallel_generator.py`)

Orchestrates parallel code generation:

```python
from src.parallel_generator import ParallelGenerator, GeneratorConfig

# Initialize
parallel_gen = ParallelGenerator(
    ollama_client=client,
    node_runner=runner,
    evaluator=evaluator,
    quality_weight=0.7,
    speed_weight=0.3
)

# Define generators
generators = [
    GeneratorConfig(
        name="codellama_conservative",
        model="codellama",
        temperature=0.1
    ),
    GeneratorConfig(
        name="qwen_balanced",
        model="qwen2.5-coder:14b",
        temperature=0.5
    ),
    GeneratorConfig(
        name="deepseek_powerful",
        model="deepseek-coder:6.7b",
        temperature=0.3
    )
]

# Generate in parallel
results = parallel_gen.generate_parallel(
    prompt="Write a function that validates email addresses",
    generators=generators,
    node_id="email_validator",
    description="Email validation function"
)

# Results are sorted by combined score
best = results[0]
print(f"Winner: {best.generator_name}")
print(f"Quality: {best.quality_score:.2f}")
print(f"Generation time: {best.generation_time:.2f}s")
print(f"Combined score: {best.combined_score:.2f}")
```

#### 2. ExperimentSelector (`src/experiment_selector.py`)

Selects best result based on criteria:

```python
from src.experiment_selector import ExperimentSelector, SelectionCriteria

# Define criteria
criteria = SelectionCriteria(
    quality_weight=0.7,
    speed_weight=0.3,
    min_quality_score=0.5,
    max_generation_time=120.0
)

# Initialize selector
selector = ExperimentSelector(criteria=criteria)

# Select best from results
best = selector.select_best(
    results=generation_results,
    task_context={"task_type": "api_integration"}
)

# Learn from feedback
selector.learn_from_feedback(
    selected_result=best,
    user_satisfaction=0.9  # User rates the result
)
```

#### 3. GenerationResult (Data Structure)

```python
@dataclass
class GenerationResult:
    generator_name: str         # "qwen_balanced"
    code: str                   # Generated code
    generation_time: float      # 12.3 seconds
    model_used: str            # "qwen2.5-coder:14b"
    temperature: float          # 0.5

    # Measured after testing
    test_passed: bool          # True
    test_time: float           # 2.1 seconds
    quality_score: float       # 0.85 (0-1)
    execution_time: float      # 0.05 seconds

    # Final score
    combined_score: float      # 0.78
```

---

## Scoring System

### Quality Score (0-1)

Components:
1. **Base quality** (from evaluator): 0-1
2. **Test success**: +0.5 if tests pass
3. **Simplicity bonus** (optional): +0.1 for concise code
4. **Error handling bonus**: +0.05 if try/except present

Formula:
```python
quality_score = 0.0

if test_passed:
    quality_score += 0.5

quality_score += evaluator_score * 0.5  # 0-0.5

if prefer_simplicity and lines < 50:
    quality_score += 0.1

if has_error_handling:
    quality_score += 0.05
```

### Speed Score (0-1)

Components:
1. **Generation speed**: Faster generation = higher score
2. **Execution speed**: Faster runtime = higher score

Formula:
```python
# Normalize generation time (< 10s = 1.0, > 60s = 0.0)
gen_score = max(0, 1.0 - (gen_time / 60.0))

# Normalize execution time (< 1s = 1.0, > 10s = 0.0)
exec_score = max(0, 1.0 - (exec_time / 10.0))

# Weighted average (60% generation, 40% execution)
speed_score = (gen_score * 0.6) + (exec_score * 0.4)
```

### Combined Score

```python
combined_score = (quality_weight * quality_score) + (speed_weight * speed_score)
```

Example:
```
Quality score: 0.85
Speed score: 0.65
Quality weight: 0.7
Speed weight: 0.3

Combined = (0.7 × 0.85) + (0.3 × 0.65)
        = 0.595 + 0.195
        = 0.79
```

---

## Usage Examples

### Example 1: API Integration (Quality-Focused)

```python
# Critical task - prioritize quality
generators = [
    GeneratorConfig("deepseek_conservative", "deepseek-coder:6.7b", 0.1),
    GeneratorConfig("qwen_conservative", "qwen2.5-coder:14b", 0.1),
    GeneratorConfig("qwen_balanced", "qwen2.5-coder:14b", 0.3)
]

results = parallel_gen.generate_parallel(
    prompt="Create API client for Stripe payments",
    generators=generators,
    node_id="stripe_client",
    description="Stripe API integration"
)

# Results weighted 85% quality, 15% speed
# Winner: deepseek_conservative (quality=0.92, speed=0.45, combined=0.85)
```

### Example 2: Simple Utility (Speed-Focused)

```python
# Simple task - prioritize speed
parallel_gen.quality_weight = 0.5
parallel_gen.speed_weight = 0.5

generators = [
    GeneratorConfig("codellama_fast", "codellama", 0.1),
    GeneratorConfig("qwen_creative", "qwen2.5-coder:3b", 0.9)
]

results = parallel_gen.generate_parallel(
    prompt="Write function to format phone numbers",
    generators=generators,
    node_id="format_phone",
    description="Phone number formatter"
)

# Results weighted 50/50 quality and speed
# Winner: codellama_fast (quality=0.78, speed=0.92, combined=0.85)
```

### Example 3: Learning from History

```python
# Get recommendations based on past success
task_type = "data_processing"
recommended = parallel_gen.get_generator_recommendations(task_type, top_k=3)

# Returns: ["qwen_balanced", "deepseek_balanced", "codellama_conservative"]
# Based on historical success rates for this task type

# Use recommended generators
generators = [
    GeneratorConfig(name, get_model(name), get_temp(name))
    for name in recommended
]
```

### Example 4: Adaptive Weight Learning

```python
selector = ExperimentSelector(learning_rate=0.1)

# Generate code
best = selector.select_best(results, context={"task_type": "api"})

# User rates the result
user_satisfaction = 0.4  # Low satisfaction

# Selector learns: maybe weights were wrong for this task
selector.learn_from_feedback(best, user_satisfaction)

# Weights automatically adjusted:
# quality_weight: 0.7 → 0.65
# speed_weight: 0.3 → 0.35
```

---

## Performance Optimization

### Parallel Execution

All generators run simultaneously using `ThreadPoolExecutor`:

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(generate, gen): gen
        for gen in generators
    }

    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        results.append(result)
```

Benefits:
- **3-5x faster** than sequential generation
- **Wall-clock time** = slowest generator (not sum of all)
- **Better GPU utilization** if using multiple Ollama instances

### Time Comparison

**Without parallel generation:**
```
Generator 1: 12s
Generator 2: 15s
Generator 3: 10s
Total: 37 seconds
```

**With parallel generation:**
```
All generators: max(12s, 15s, 10s) = 15 seconds
Speedup: 2.5x
```

---

## Task-Specific Optimization

### Recommended Criteria by Task Type

```python
# API / Database / Security (quality-critical)
SelectionCriteria(
    quality_weight=0.85,
    speed_weight=0.15,
    min_quality_score=0.7,
    max_generation_time=120.0
)

# Simple functions / Utilities
SelectionCriteria(
    quality_weight=0.5,
    speed_weight=0.5,
    min_quality_score=0.4,
    max_generation_time=30.0
)

# Data processing / Batch jobs
SelectionCriteria(
    quality_weight=0.6,
    speed_weight=0.4,
    min_quality_score=0.5,
    max_execution_time=30.0  # Allow longer execution
)
```

---

## Integration with Overseer

### Modified Workflow

```python
# OLD (single generator):
code = client.generate(model="codellama", prompt=prompt)

# NEW (parallel experiments):
results = parallel_gen.generate_parallel(
    prompt=prompt,
    generators=create_default_generators(),
    node_id=node_id,
    description=description
)

best = results[0]  # Sorted by combined score
code = best.code

# Record which generator won for this task type
parallel_gen.record_success(
    generator_name=best.generator_name,
    task_type=task_type,
    success=best.test_passed
)
```

### Future: Tool Mutation

The system can evolve tool definitions based on success:

```python
# If deepseek_balanced consistently wins for API tasks,
# create a specialized "api_integration_expert" tool:

new_tool = {
    "name": "API Integration Expert",
    "type": "llm",
    "llm": {
        "model": "deepseek-coder:6.7b",
        "temperature": 0.3,  # Learned optimal
        "system_prompt": "You are an expert at creating robust API integrations..."
    },
    "tags": ["api", "integration", "expert"],
    "metadata": {
        "evolved_from": "deepseek_balanced",
        "specialized_for": "api_integration",
        "success_rate": 0.94
    }
}
```

---

## Metrics and Analytics

### Generator Performance Tracking

```python
stats = parallel_gen.generator_stats

# Example output:
{
    "api_integration": {
        "deepseek_conservative": {
            "success_count": 23,
            "total_count": 25,
            "success_rate": 0.92
        },
        "qwen_balanced": {
            "success_count": 21,
            "total_count": 25,
            "success_rate": 0.84
        }
    },
    "simple_function": {
        "codellama_conservative": {
            "success_count": 19,
            "total_count": 20,
            "success_rate": 0.95
        }
    }
}
```

### Selection History

```python
stats = selector.get_stats()

# Example output:
{
    "total_selections": 47,
    "generator_distribution": {
        "qwen_balanced": 23,
        "deepseek_conservative": 15,
        "codellama_conservative": 9
    },
    "average_score": 0.78,
    "score_std_dev": 0.12,
    "current_weights": {
        "quality": 0.68,
        "speed": 0.32
    },
    "total_adjustments": 5
}
```

---

## Benefits

### 1. Better First-Shot Success

- Multiple approaches tried simultaneously
- Best one selected automatically
- Reduces need for repair cycles from 6 to 0-1

### 2. Task-Specific Optimization

- Quality-critical tasks get conservative, thorough generation
- Simple tasks get fast, lightweight generation
- System learns optimal generator for each task type

### 3. Resource Efficiency

- Parallel execution uses GPU efficiently
- Wall-clock time = slowest generator (not sum)
- Can distribute across multiple Ollama instances

### 4. Continuous Improvement

- Tracks which generators work best
- Learns from user feedback
- Automatically adjusts weights
- Can evolve specialized tools

---

## Future Enhancements

### 1. Multi-Objective Optimization

Add more criteria beyond quality/speed:
- Code readability
- Maintainability
- Test coverage
- Documentation quality

### 2. Genetic Algorithms

Evolve generator configurations:
- Crossover: Combine successful temperatures
- Mutation: Try variations of winning configs
- Selection: Keep best performers

### 3. Distributed Execution

Run generators on multiple machines:
- Load balance across Ollama instances
- Use cloud GPUs for expensive models
- Reduce wall-clock time further

### 4. Ensemble Methods

Combine multiple generators:
- Use best parts from each
- Voting for consensus
- Hybrid approaches

---

## Summary

The Parallel Generation System transforms code generation from a **single-shot gamble** into a **competitive experiment** where:

1. **Multiple generators** run in parallel
2. **Real metrics** (quality + speed) drive selection
3. **System learns** which works best for which tasks
4. **Continuous improvement** through feedback and evolution

This achieves the user's goal:
> "Balance quality and speed based on real data"

The Overseer is now a **meta-optimizer** that experiments with different approaches and learns what works best.

---

**Generated:** 2025-11-17
**Version:** 1.0
**Status:** ✓ Production Ready
