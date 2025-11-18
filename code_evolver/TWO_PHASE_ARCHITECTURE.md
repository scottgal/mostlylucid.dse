# Two-Phase Architecture - Core + Optimize

**The Complete Flow: User Request → Result → Continuous Improvement**

---

## Overview

mostlylucid DiSE uses a **two-phase architecture** that balances immediate results with long-term optimization:

**Phase 1 (CORE)**: Get result NOW
**Phase 2 (OPTIMIZE)**: Make it better LATER

---

## The Complete Flow

```
User Request
    ↓
Phase 1 Core → Result + Metrics
    ↓
Artifact stored with:
    - Tool usage
    - Latency
    - Coverage
    - Fitness score
    ↓
Phase 2 Core (triggered by time, hardware change, or manual command)
    ↓
Optimizer re-runs with new constraints
    → Stops when no further gain
    → Can resume later
```

---

## Phase 1: CORE (Interactive)

**Goal**: Get user their result IMMEDIATELY

**Priority**: Speed > Quality (but still good enough)

**Flow**:
```
1. User makes request
2. Sentinel LLM detects intent (<500ms)
3. Select best-known generator for task type
4. Generate code (single shot, 5-15s)
5. Test code
6. If error: Check auto-fix library (2s)
7. Return result to user
8. Store artifact with metrics
```

**Metrics Stored**:
```json
{
  "node_id": "email_validator_v1",
  "task_type": "validation",
  "generator_used": "codellama_conservative",
  "generation_time": 8.3,
  "test_passed": true,
  "quality_score": 0.75,
  "latency": 0.05,
  "coverage": 0.82,
  "fitness_score": 0.78,
  "tool_usage": ["email_validator", "regex_helper"],
  "phase": "core",
  "timestamp": "2025-11-17T12:00:00Z"
}
```

**User Experience**:
- Wait time: 5-15 seconds
- Gets working solution
- Can use immediately
- Doesn't care HOW it was made

---

## Phase 2: OPTIMIZE (Background)

**Goal**: Improve quality for future users

**Priority**: Quality > Speed (no user waiting)

**Triggers**:
1. **Time-based**: Every N hours (configurable)
2. **Hardware change**: New GPU, more resources available
3. **Manual command**: `/optimize <node_id>` or `/optimize all`
4. **Fitness threshold**: Artifact score < 0.8
5. **Usage threshold**: Node used >10 times

**Flow**:
```
1. Trigger detected (time/hardware/manual)
2. Load artifact + metrics from Phase 1
3. Analyze current fitness score
4. Run parallel experiments:
   - 5 different generators
   - Different temperatures
   - Different approaches
5. Test all variants
6. Score: quality × speed × coverage
7. Select best (must be better than current)
8. If improvement found:
   - Update artifact
   - Evolve tool definitions
   - Update "best generator" registry
9. Store new metrics
10. Stop when no further gain
```

**Optimization Stages**:

**Stage 1: Parallel Experiments** (5-10 minutes)
```python
variants = [
    GeneratorConfig("deepseek_conservative", "deepseek-coder:6.7b", 0.1),
    GeneratorConfig("qwen_balanced", "qwen2.5-coder:14b", 0.5),
    GeneratorConfig("qwen_creative", "qwen2.5-coder:14b", 0.9),
    GeneratorConfig("codellama_fast", "codellama", 0.3),
    GeneratorConfig("deepseek_powerful", "deepseek-coder:16b", 0.3)
]

results = parallel_gen.generate_parallel(
    prompt=original_prompt,
    generators=variants,
    node_id=node_id
)

best = select_best(results, current_score)
```

**Stage 2: Tool Evolution** (if improvement > 10%)
```python
if best.fitness_score > current_score * 1.1:
    # Create specialized tool
    evolve_tool_definition(
        task_type=task_type,
        winning_generator=best.generator_name,
        success_metrics=best
    )
```

**Stage 3: Incremental Improvements**
```python
# Try small variations
for temp in [best_temp - 0.1, best_temp, best_temp + 0.1]:
    variant = generate(model=best_model, temp=temp)
    if variant.score > best.score:
        best = variant
    else:
        break  # Stop when no further gain
```

**Stopping Conditions**:
- No improvement in last 3 attempts
- Fitness score > 0.95 (diminishing returns)
- Time limit reached (configurable)
- Resource budget exhausted

**Can Resume Later**:
```python
# Store optimization state
optimization_state = {
    "node_id": node_id,
    "current_best_score": 0.87,
    "attempts": 12,
    "last_improvement": "2025-11-17T12:30:00Z",
    "next_strategies": ["try_higher_temp", "try_different_model"],
    "paused_at": "Stage 2: Tool Evolution"
}

# Resume later (e.g., when better hardware available)
resume_optimization(optimization_state)
```

---

## Trigger Examples

### Time-Based Trigger
```python
# Every 24 hours
scheduler.schedule(
    task="optimize_all",
    interval_hours=24,
    condition=lambda: not user_active()
)
```

### Hardware Change Trigger
```python
# Detect GPU upgrade
if detect_hardware_change():
    console.print("[cyan]Detected new GPU - running optimization pass[/cyan]")
    optimize_all_artifacts(
        priority_min="medium",
        fitness_threshold=0.8
    )
```

### Manual Trigger
```bash
# User commands
/optimize email_validator              # Optimize specific node
/optimize all --priority=high          # Optimize high-priority nodes
/optimize --fitness-below=0.8          # Optimize low-scoring nodes
```

### Fitness Threshold Trigger
```python
# After each Phase 1 generation
if artifact.fitness_score < 0.8:
    queue_for_optimization(
        node_id=artifact.node_id,
        reason="low_fitness",
        priority="high"
    )
```

---

## Metrics Evolution

### Phase 1 Metrics (Initial)
```json
{
  "fitness_score": 0.75,
  "quality_score": 0.70,
  "latency": 0.08,
  "coverage": 0.82,
  "generation_time": 8.3,
  "generator": "codellama_conservative"
}
```

### Phase 2 Metrics (After Optimization)
```json
{
  "fitness_score": 0.92,
  "quality_score": 0.95,
  "latency": 0.03,
  "coverage": 0.94,
  "generation_time": 12.1,
  "generator": "deepseek_powerful",
  "optimization_iterations": 5,
  "improvement_percentage": 22.7,
  "optimized_at": "2025-11-17T18:00:00Z"
}
```

---

## Example: Complete Lifecycle

### User Request (10:00 AM)
```
User: "Quickly write a function to validate email addresses"
```

### Phase 1 Core (10:00:08 AM - 8 seconds later)
```python
# Sentinel detects "quickly" → INTERACTIVE mode
mode = sentinel.detect_intent(request)  # mode = "interactive"

# Use best known generator (from past success)
generator = execution_mode.select_generator_for_interactive("validation")
# Returns: "codellama_conservative"

# Generate code (single shot)
code = client.generate(
    model="codellama",
    prompt="Write email validation function",
    temperature=0.3
)

# Test
result = runner.run_node("email_validator", code)
# Tests pass ✓

# Store artifact with metrics
rag.store_artifact(
    artifact_id="email_validator_v1",
    content=code,
    metadata={
        "fitness_score": 0.75,
        "quality_score": 0.70,
        "latency": 0.08,
        "coverage": 0.82,
        "tool_usage": ["regex"],
        "generator": "codellama_conservative"
    }
)

# Return to user
console.print("[green]✓ Email validator created![/green]")
console.print(f"[dim]Quality: 0.75, Time: 8.3s[/dim]")
```

**User gets result: 8 seconds total**

---

### Phase 2 Optimize (6:00 PM - triggered by scheduler)

```python
# Scheduler detects low fitness score (0.75 < 0.8)
optimizer.run_optimization("email_validator_v1")

# Load original artifact
artifact = rag.get_artifact("email_validator_v1")
original_prompt = artifact.metadata["original_prompt"]
current_score = artifact.metadata["fitness_score"]  # 0.75

# Run parallel experiments
console.print("[cyan]Running optimization experiments...[/cyan]")

variants = parallel_gen.generate_parallel(
    prompt=original_prompt,
    generators=[
        GeneratorConfig("deepseek_conservative", "deepseek-coder:6.7b", 0.1),
        GeneratorConfig("qwen_balanced", "qwen2.5-coder:14b", 0.5),
        GeneratorConfig("qwen_creative", "qwen2.5-coder:14b", 0.9),
        GeneratorConfig("deepseek_powerful", "deepseek-coder:16b", 0.3),
        GeneratorConfig("codellama_optimized", "codellama", 0.5)
    ],
    node_id="email_validator_v1"
)

# Results:
# 1. deepseek_conservative: 0.89
# 2. qwen_balanced: 0.85
# 3. qwen_creative: 0.72
# 4. deepseek_powerful: 0.92 ← BEST
# 5. codellama_optimized: 0.78

best = variants[3]  # deepseek_powerful

# Improvement found: 0.92 vs 0.75 (22.7% better)
if best.fitness_score > current_score:
    console.print(f"[green]✓ Improvement: {current_score:.2f} → {best.fitness_score:.2f}[/green]")

    # Update artifact
    rag.update_artifact(
        artifact_id="email_validator_v1",
        content=best.code,
        metadata={
            "fitness_score": 0.92,
            "quality_score": 0.95,
            "optimized_at": datetime.now().isoformat(),
            "optimization_iterations": 5,
            "improvement_percentage": 22.7
        }
    )

    # Evolve tool: Create "validation expert"
    evolve_tool_definition(
        task_type="validation",
        winning_generator="deepseek_powerful",
        success_metrics=best
    )

    # Update best generator registry
    execution_mode.update_best_generator("validation", "deepseek_powerful")

# Try incremental improvements
for temp in [0.2, 0.3, 0.4]:
    variant = generate(model="deepseek-coder:16b", temp=temp)
    if variant.fitness_score > best.fitness_score:
        best = variant
        console.print(f"[cyan]Small improvement: {variant.fitness_score:.2f}[/cyan]")
    else:
        console.print("[dim]No further gain - stopping[/dim]")
        break

# Store final state
console.print(f"[green]✓ Optimization complete[/green]")
console.print(f"[dim]Final score: {best.fitness_score:.2f}[/dim]")
```

**Next user request for validation will use "deepseek_powerful" from the start!**

---

### Next Day - User 2 Requests Similar Task (10:00 AM)

```
User 2: "Create an email validator"
```

```python
# Sentinel → INTERACTIVE mode
# Select best generator for "validation"
generator = execution_mode.select_generator_for_interactive("validation")
# Returns: "deepseek_powerful" (learned from yesterday's optimization!)

# Generate with optimized settings
code = client.generate(
    model="deepseek-coder:16b",
    temperature=0.3,
    prompt="Write email validation function"
)

# Tests pass ✓
# Quality score: 0.91 (better than original 0.75!)
```

**User 2 gets optimized solution from Day 1: 10 seconds, quality = 0.91**

---

## Constraints and Adaptation

### Hardware Constraints
```python
# Phase 1: Limited resources
if available_gpu_memory < 8GB:
    # Use smaller models
    generator = "codellama"  # 7B model
else:
    generator = "deepseek-coder:16b"  # 16B model

# Phase 2: More resources available
if available_gpu_memory >= 16GB:
    # Can run larger experiments
    variants = create_experiment_generators(
        include_large_models=True
    )
```

### Time Constraints
```python
# Phase 1: User waiting
max_time = 15  # seconds

# Phase 2: No user waiting
max_time = 300  # 5 minutes per experiment
```

### Re-optimization on Hardware Change
```python
# Detect GPU upgrade
if new_gpu_vram > old_gpu_vram * 1.5:
    console.print("[cyan]Detected GPU upgrade![/cyan]")
    console.print("[cyan]Re-optimizing with larger models...[/cyan]")

    # Re-run optimization with access to 16B/32B models
    for artifact in get_all_artifacts():
        reoptimize_with_new_constraints(
            artifact=artifact,
            new_constraints={"max_model_size": "32B"}
        )
```

---

## Storage and Versioning

### Artifact Evolution
```python
# Version 1 (Phase 1)
email_validator_v1:
  - fitness: 0.75
  - generator: codellama_conservative
  - created: 2025-11-17T10:00:00Z

# Version 2 (Phase 2 - first optimization)
email_validator_v2:
  - fitness: 0.92
  - generator: deepseek_powerful
  - optimized: 2025-11-17T18:00:00Z
  - parent: email_validator_v1

# Version 3 (Phase 2 - incremental improvement)
email_validator_v3:
  - fitness: 0.94
  - generator: deepseek_powerful (temp=0.4)
  - optimized: 2025-11-17T18:15:00Z
  - parent: email_validator_v2
```

---

## CLI Commands

### User Commands
```bash
# Get result NOW (Phase 1)
DiSE> write email validator

# Check optimization status
DiSE> /status email_validator
# Fitness: 0.75 (Phase 1)
# Next optimization: scheduled for 18:00

# Manually trigger optimization (Phase 2)
DiSE> /optimize email_validator
# Running experiments... (3/5 complete)
# Best so far: 0.89

# Optimize all low-scoring nodes
DiSE> /optimize all --fitness-below=0.8

# Optimize when idle
DiSE> /optimize --background --when-idle
```

---

## Summary

### Phase 1 Philosophy
- **"Good enough NOW"**
- User gets result in seconds
- Store metrics for later
- No experiments while user waits

### Phase 2 Philosophy
- **"Perfect LATER"**
- Run in background
- Parallel experiments
- Continuous improvement
- Can pause and resume

### Key Insight
The same task gets **progressively better** over time:
- Day 1: 0.75 quality (Phase 1)
- Day 1 evening: 0.92 quality (Phase 2 optimization)
- Day 2: Next user gets 0.92 quality from the start (Phase 1 uses optimized settings)

**System learns and improves, all users benefit.**

---

**Generated:** 2025-11-17
**Status:** ✓ Architecture Complete
