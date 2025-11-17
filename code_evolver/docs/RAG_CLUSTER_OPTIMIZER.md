# RAG Cluster Optimizer

## Overview

The RAG Cluster Optimizer is an **iterative self-optimization loop** that evolves code artifacts toward higher fitness over time. Instead of just picking one "best" version, the system moves outward from the core function, testing alternates, folding in their performance data, and converging toward fitter canonical artifacts.

## 🧠 Core Concept: The Living Library

Think of it as a **guild master refining a ritual**: start with the core chant, then test variations from apprentices. Each cycle, the master keeps the strongest elements, discards the weak, and the ritual evolves. Over time, the guild's library becomes a living lineage of ever-stronger spells.

### Key Principles

1. **Lineage Preservation**: Never delete variants, always archive with parent links
2. **Pattern Learning**: System gets smarter over time by learning from successes
3. **Multi-Strategy**: Different strategies for different optimization needs
4. **Fitness-Driven**: Objective metrics guide all decisions
5. **Iterative Refinement**: Small steps toward better implementations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   OptimizerConfigManager                    │
│         Loads policies from YAML configuration              │
└───────────┬─────────────────────────────────────────────────┘
            │
            ├── NodeTypeOptimizer (FUNCTION)
            ├── NodeTypeOptimizer (WORKFLOW)
            ├── NodeTypeOptimizer (PROMPT)
            ├── NodeTypeOptimizer (SUB_WORKFLOW)
            ├── NodeTypeOptimizer (PLAN)
            └── NodeTypeOptimizer (PATTERN)
                    │
                    ├── RAGClusterOptimizer
                    │   ├── Generate candidates
                    │   ├── Validate candidates
                    │   ├── Compare fitness
                    │   ├── Promote if better
                    │   └── Learn patterns
                    │
                    └── TrimmingPolicy
                        └── Distance from fittest algorithm
```

## Iterative Optimization Process

### Phase 1: Core Function Anchor

1. Identify current "best" implementation (canonical artifact)
2. Treat it as the root of the optimization tree
3. Establish baseline fitness metrics

### Phase 2: Alternate Exploration

1. Pull all close variants (≥0.96 similarity cluster)
2. Extract semantic deltas:
   - Algorithm tweaks
   - Error handling improvements
   - Refactoring patterns
   - Performance optimizations
3. Analyze performance data + usage stats for each alternate

### Phase 3: Iteration Loop (Repeat up to MAX_ITERATIONS)

#### Step 1: Generate Candidate

- Combine alternates + performance insights
- Apply learned patterns
- Use strategy: BEST_OF_BREED, INCREMENTAL, RADICAL, or HYBRID
- Create new candidate variant

#### Step 2: Validate Candidate

- Run functional tests
- Execute performance benchmarks
- Perform mutation tests
- Measure fitness score

#### Step 3: Compare Fitness

- Compare candidate fitness vs canonical fitness
- Compare against cluster median
- Calculate improvement delta

#### Step 4: Promote If Fitter

If fitness improvement > threshold:
- Archive old canonical (preserve lineage)
- Promote candidate to new canonical
- Archive weak variants (fitness < candidate - 0.1)
- Update parent-child relationships

Else:
- Keep current canonical
- Stop iteration if no improvement

#### Step 5: Expand Outward

- If promoted: explore next layer of alternates
- If not promoted: stop iterations
- Re-run loop with updated cluster

### Phase 4: Self-Optimization & Learning

1. Learn patterns from successful promotions
2. Store learned patterns in cluster metadata
3. Use patterns to prioritize future deltas
4. Track optimization history

## Node Types

The RAG system supports six artifact node types, each with customizable optimization policies:

### 1. **FUNCTION** - Code functions and methods

**Default Strategy**: `best_of_breed`
**Priority**: 8 (high)
**Optimization Frequency**: daily

**Fitness Weights**:
- Latency: 30%
- Memory: 20%
- CPU: 15%
- Success Rate: 25%
- Coverage: 10%

**Use Case**: Optimizing individual functions for performance and correctness.

### 2. **WORKFLOW** - Complete workflows

**Default Strategy**: `incremental`
**Priority**: 9 (highest)
**Optimization Frequency**: weekly

**Fitness Weights**:
- Latency: 20%
- Memory: 10%
- CPU: 10%
- Success Rate: 40% (prioritize reliability)
- Coverage: 20%

**Use Case**: Critical workflows requiring stability and high success rates.

### 3. **PROMPT** - LLM prompts and templates

**Default Strategy**: `hybrid`
**Priority**: 7
**Optimization Frequency**: daily

**Fitness Weights**:
- Latency: 15%
- Memory: 5%
- CPU: 5%
- Success Rate: 50% (prioritize quality)
- Coverage: 25%

**Use Case**: Optimizing prompts for better LLM outputs.

### 4. **SUB_WORKFLOW** - Workflow components

**Default Strategy**: `best_of_breed`
**Priority**: 6
**Optimization Frequency**: daily

**Use Case**: Reusable workflow building blocks.

### 5. **PLAN** - Execution plans

**Default Strategy**: `best_of_breed`
**Priority**: 5
**Optimization Frequency**: daily

**Use Case**: Planning and orchestration artifacts.

### 6. **PATTERN** - Code patterns and templates

**Default Strategy**: `radical`
**Priority**: 6
**Optimization Frequency**: daily

**Use Case**: Exploring radical improvements to common patterns.

## Optimization Strategies

### 1. BEST_OF_BREED

**Description**: Combine best features from multiple alternates
**Expected Improvement**: 15%
**Use Case**: When you have diverse high-quality variants

**Example**:
```python
# Takes:
# - Best latency from variant A
# - Best memory from variant B
# - Best error handling from variant C
# Creates new candidate with all best features
```

### 2. INCREMENTAL

**Description**: Small, safe changes from canonical
**Expected Improvement**: 5%
**Use Case**: When canonical is already good, need gradual refinement

**Example**:
```python
# Canonical: Good performance, slight memory leak
# Incremental: Fix memory leak only
# Low risk, targeted improvement
```

### 3. RADICAL

**Description**: Experimental, high-risk high-reward changes
**Expected Improvement**: 25%
**Use Case**: When canonical needs major overhaul

**Example**:
```python
# Canonical: O(n²) algorithm
# Radical: Complete rewrite with O(n log n) algorithm
# High risk, high reward
```

### 4. HYBRID

**Description**: Alternate between strategies across iterations
**Expected Improvement**: 12%
**Use Case**: When you want balanced exploration

**Example**:
```python
# Iteration 1: BEST_OF_BREED
# Iteration 2: INCREMENTAL
# Iteration 3: RADICAL
# Adapts to context
```

## Trimming Algorithm: Distance from Fittest

The trimming algorithm prunes variants based on their "distance from fittest" combined with usage patterns.

### Decision Rules

#### Rule 1: Poor Performance + Far Distance = PRUNE

```
IF fitness < min_fitness_absolute (0.50)
   AND distance_from_fittest > max_distance (0.30)
THEN PRUNE
```

**Example**:
- Variant fitness: 0.40
- Fittest fitness: 0.85
- Distance: 0.45
- **Decision**: PRUNE ("Poor fitness and far from fittest")

#### Rule 2: Low Similarity = PRUNE (unless high performance)

```
IF similarity < min_similarity_to_fittest (0.70)
   AND fitness < preserve_high_perf_threshold (0.85)
THEN PRUNE
```

**Example**:
- Variant similarity: 0.65
- Variant fitness: 0.75
- **Decision**: PRUNE ("Low similarity to fittest")

**Exception**:
- Variant similarity: 0.65
- Variant fitness: 0.87
- **Decision**: KEEP ("Low similarity but high fitness - worth evaluating")

#### Rule 3: Never Used + Past Grace Period = PRUNE (unless high performance)

```
IF usage_count == 0
   AND days_since_creation > never_used_grace_period_days (30)
   AND fitness < preserve_high_perf_threshold (0.85)
THEN PRUNE
```

**Example**:
- Variant usage: 0
- Days old: 40
- Fitness: 0.70
- **Decision**: PRUNE ("Never used after 40 days")

**Exception**:
- Variant usage: 0
- Days old: 40
- Fitness: 0.90
- **Decision**: KEEP ("Never used but high fitness - worth evaluating")

#### Rule 4: High Coverage = KEEP

```
IF test_coverage >= 0.90
THEN KEEP
```

**Rationale**: Well-tested code should be preserved.

#### Rule 5: Lineage Endpoint = KEEP

```
IF len(children_ids) == 0
   AND preserve_lineage_endpoints == true
THEN KEEP
```

**Rationale**: Preserve historical record (leaf nodes in lineage tree).

#### Rule 6: Good Fitness + Usage = KEEP

```
IF fitness >= min_fitness_absolute (0.50)
   AND usage_count >= min_usage_count (1)
THEN KEEP
```

**Rationale**: Active variants with decent performance are valuable.

### Trimming Examples

#### Example 1: High-Performance Unused Variant ✅ KEEP

```yaml
Variant:
  usage_count: 0
  fitness: 0.90
  days_old: 40
  similarity_to_fittest: 0.75

Decision: KEEP
Reason: "Never used but high fitness (0.90) - worth evaluating"
```

**Why**: High performance indicates potential value, even without usage history.

#### Example 2: Poor Performance + Far Distance ❌ PRUNE

```yaml
Variant:
  fitness: 0.40
  fittest_fitness: 0.85
  distance: 0.45
  usage_count: 2

Decision: PRUNE
Reason: "Poor fitness (0.40) and far from fittest (0.45)"
```

**Why**: Low fitness + large distance = no value, regardless of usage.

#### Example 3: Different Approach, High Performance ✅ KEEP

```yaml
Variant:
  similarity_to_fittest: 0.65
  fitness: 0.87
  usage_count: 5

Decision: KEEP
Reason: "Low similarity but high fitness (0.87)"
```

**Why**: Alternative approaches that perform well should be explored.

#### Example 4: Well-Tested Variant ✅ KEEP

```yaml
Variant:
  test_coverage: 0.92
  fitness: 0.70
  similarity_to_fittest: 0.68

Decision: KEEP
Reason: "High test coverage (0.92)"
```

**Why**: High test coverage indicates quality and should be preserved.

## Configuration

### YAML Configuration Structure

```yaml
node_type_optimizers:
  function:
    enabled: true
    similarity_threshold: 0.96
    max_iterations: 10
    fitness_improvement_threshold: 0.05
    strategy: best_of_breed
    optimization_frequency: daily
    priority: 8

    fitness_weights:
      latency: 0.30
      memory: 0.20
      cpu: 0.15
      success_rate: 0.25
      coverage: 0.10

    trimming_policy:
      min_similarity_to_fittest: 0.70
      preserve_high_perf_threshold: 0.85
      min_usage_count: 1
      never_used_grace_period_days: 30
      min_fitness_absolute: 0.50
      max_distance_from_fittest: 0.30
      always_keep_canonical: true
      keep_high_coverage_variants: true
      preserve_lineage_endpoints: true
```

### Loading Configuration

```python
from src.rag_cluster_optimizer import OptimizerConfigManager, NodeType

# Load from file
config_manager = OptimizerConfigManager(
    config_path="config/rag_cluster_optimizer.yaml"
)

# Get optimizer for specific node type
function_optimizer = config_manager.get_optimizer(NodeType.FUNCTION)

# Optimize a cluster
iterations = function_optimizer.optimize_cluster(cluster)

# Export updated config
config_manager.export_config("config/rag_cluster_optimizer.updated.yaml")
```

### Customizing Per Node Type

You can override any setting for specific node types:

```yaml
node_type_optimizers:
  workflow:
    # More conservative for critical workflows
    similarity_threshold: 0.94
    max_iterations: 15
    fitness_improvement_threshold: 0.08  # Require larger improvement
    strategy: incremental  # Safer strategy

    trimming_policy:
      never_used_grace_period_days: 45  # Longer grace period
      min_fitness_absolute: 0.60  # Higher minimum
```

## Usage Examples

### Example 1: Basic Cluster Optimization

```python
from src.rag_cluster_optimizer import (
    RAGClusterOptimizer,
    OptimizationCluster,
    ArtifactVariant,
    PerformanceMetrics,
    OptimizationStrategy,
    VariantStatus
)

# Create canonical variant
canonical = ArtifactVariant(
    variant_id="cron_parser_v1",
    artifact_id="cron_parser",
    version="1.0",
    content="def parse_cron(expr): ...",
    status=VariantStatus.CANONICAL,
    performance=PerformanceMetrics(
        latency_ms=50.0,
        memory_mb=10.0,
        success_rate=0.92,
        test_coverage=0.75
    )
)

# Create cluster with alternates
cluster = OptimizationCluster(
    cluster_id="cron_parser_cluster",
    canonical_variant=canonical,
    alternates=[alt1, alt2, alt3]  # Your alternates
)

# Run optimization
optimizer = RAGClusterOptimizer(
    strategy=OptimizationStrategy.BEST_OF_BREED
)
iterations = optimizer.optimize_cluster(cluster)

# Get report
report = optimizer.get_optimization_report(cluster, iterations)
print(report)
```

### Example 2: Node-Type-Specific Optimization

```python
from src.rag_cluster_optimizer import (
    OptimizerConfigManager,
    NodeType
)

# Load configuration
config_manager = OptimizerConfigManager(
    config_path="config/rag_cluster_optimizer.yaml"
)

# Optimize different node types with their specific policies
function_optimizer = config_manager.get_optimizer(NodeType.FUNCTION)
workflow_optimizer = config_manager.get_optimizer(NodeType.WORKFLOW)
prompt_optimizer = config_manager.get_optimizer(NodeType.PROMPT)

# Each uses its own strategy, weights, and trimming policy
function_iterations = function_optimizer.optimize_cluster(function_cluster)
workflow_iterations = workflow_optimizer.optimize_cluster(workflow_cluster)
prompt_iterations = prompt_optimizer.optimize_cluster(prompt_cluster)
```

### Example 3: Custom Validation

```python
def my_validator(candidate: ArtifactVariant) -> ValidationResult:
    """Custom validation logic."""
    # Run your own tests
    test_results = run_my_tests(candidate)

    # Measure performance
    perf = measure_performance(candidate)

    return ValidationResult(
        passed=test_results.all_passed,
        fitness_score=perf.fitness_score(),
        performance=perf,
        test_results=test_results
    )

# Use custom validator
iterations = optimizer.optimize_cluster(cluster, validator_fn=my_validator)
```

### Example 4: Trimming Clusters

```python
from src.rag_cluster_optimizer import TrimmingPolicy, NodeType

# Create custom trimming policy
aggressive_trimming = TrimmingPolicy(
    node_type=NodeType.FUNCTION,
    min_similarity_to_fittest=0.80,  # More aggressive
    never_used_grace_period_days=14,  # Shorter grace period
    min_fitness_absolute=0.65  # Higher minimum
)

# Apply trimming
trim_report = optimizer.trim_cluster(cluster, aggressive_trimming)

print(f"Pruned {trim_report['pruned_count']} variants")
print(f"Kept {trim_report['kept_count']} variants")
```

## Fitness Scoring

Fitness score is a composite metric (0.0-1.0) calculated from:

```python
fitness = (
    weights['latency'] * latency_score +
    weights['memory'] * memory_score +
    weights['cpu'] * cpu_score +
    weights['success_rate'] * success_rate +
    weights['coverage'] * test_coverage
)
```

Where each component is normalized:
- **latency_score**: `1.0 - (latency_ms / 1000.0)` (lower is better)
- **memory_score**: `1.0 - (memory_mb / 100.0)` (lower is better)
- **cpu_score**: `1.0 - (cpu_percent / 100.0)` (lower is better)
- **success_rate**: `0.0-1.0` (higher is better)
- **test_coverage**: `0.0-1.0` (higher is better)

## Pattern Learning

The system learns patterns from successful promotions:

```python
# After promotion
learned_patterns = {
    'error_handling': [
        {
            'improvement': 0.12,
            'description': 'Added try/except',
            'cluster_id': 'cluster_1'
        }
    ],
    'algorithm': [
        {
            'improvement': 0.25,
            'description': 'Changed to binary search',
            'cluster_id': 'cluster_2'
        }
    ]
}

# Future deltas with these patterns get boosted priority
```

## Integration

### With RAG Memory

```python
# Load clusters from RAG memory
from src.rag_memory import RAGMemory

rag = RAGMemory()
clusters = rag.get_clusters_by_type(NodeType.FUNCTION)

# Optimize all function clusters
for cluster in clusters:
    optimizer = config_manager.get_optimizer(NodeType.FUNCTION)
    iterations = optimizer.optimize_cluster(cluster)

    # Store results back in RAG
    rag.update_cluster(cluster)
```

### With Hierarchical Evolver

```python
# Integrate with hierarchical optimization
from src.hierarchical_evolver import HierarchicalEvolver

evolver = HierarchicalEvolver()

# Add cluster optimization to evolution pipeline
evolver.add_optimization_step(
    step='cluster_optimization',
    optimizer=optimizer,
    target_node_type=NodeType.FUNCTION
)
```

## Monitoring and Reporting

### Optimization Report

```json
{
  "cluster_id": "cron_parser_cluster",
  "status": "completed",
  "summary": {
    "total_iterations": 5,
    "total_promotions": 2,
    "total_archived": 3,
    "initial_fitness": 0.750,
    "final_fitness": 0.872,
    "total_improvement": 0.122,
    "improvement_percentage": 16.3
  },
  "learned_patterns": {
    "error_handling": [{"improvement": 0.08}],
    "algorithm": [{"improvement": 0.12}]
  }
}
```

### Trimming Report

```json
{
  "cluster_id": "cron_parser_cluster",
  "fittest_variant": "cron_parser_v3",
  "fittest_fitness": 0.872,
  "pruned_count": 2,
  "kept_count": 3,
  "pruned_variants": [
    {
      "variant_id": "cron_parser_v1.1",
      "reason": "Poor fitness (0.45) and far from fittest (0.42)",
      "fitness": 0.45,
      "usage_count": 0
    }
  ]
}
```

## Best Practices

### 1. Start Conservative

```yaml
# Begin with high thresholds
similarity_threshold: 0.96
fitness_improvement_threshold: 0.08
strategy: incremental
```

### 2. Monitor Learned Patterns

```python
# Review patterns periodically
patterns = optimizer.learned_patterns
for pattern_type, data in patterns.items():
    avg_improvement = np.mean([p['improvement'] for p in data])
    print(f"{pattern_type}: {avg_improvement:.1%} average improvement")
```

### 3. Customize Per Environment

```yaml
# Development: Aggressive optimization
development:
  strategy: radical
  max_iterations: 20

# Production: Conservative optimization
production:
  strategy: incremental
  max_iterations: 5
  fitness_improvement_threshold: 0.10
```

### 4. Preserve High-Value Variants

```yaml
trimming_policy:
  preserve_high_perf_threshold: 0.85  # Keep unused but high-performing
  keep_high_coverage_variants: true   # Keep well-tested
  preserve_lineage_endpoints: true    # Keep historical record
```

### 5. Regular Trimming

Schedule periodic trimming to prevent cluster bloat:

```python
# Weekly trimming job
for cluster in all_clusters:
    trim_report = optimizer.trim_cluster(cluster)
    if trim_report['pruned_count'] > 0:
        log_trimming_action(cluster.cluster_id, trim_report)
```

## Troubleshooting

### No Promotions After Many Iterations

**Cause**: Fitness improvement threshold too high
**Solution**: Lower `fitness_improvement_threshold` to 0.02-0.03

### Too Many Variants Pruned

**Cause**: Aggressive trimming policy
**Solution**: Increase `preserve_high_perf_threshold` and `never_used_grace_period_days`

### Fitness Stagnation

**Cause**: Using same strategy repeatedly
**Solution**: Switch to `hybrid` strategy or manually rotate strategies

### High Memory Usage

**Cause**: Too many variants in clusters
**Solution**: Run trimming more frequently or lower `min_similarity_to_fittest`

## Roadmap

Future enhancements planned:

- [ ] Multi-objective optimization (Pareto frontiers)
- [ ] A/B testing integration for real-world validation
- [ ] Automatic strategy selection based on cluster characteristics
- [ ] Cross-cluster pattern learning
- [ ] Distributed optimization for large clusters
- [ ] Integration with CI/CD pipelines
- [ ] Visual lineage tree explorer

## References

- **Guild Analogy**: Inspired by traditional guild apprenticeship systems
- **Genetic Algorithms**: Fitness-based selection and evolution
- **Multi-Armed Bandits**: Strategy selection and exploration/exploitation
- **Semantic Versioning**: Lineage tracking and version management
