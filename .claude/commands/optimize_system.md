# Optimize System Command

You are a system optimization specialist. Your task is to run a full optimization workflow on the RAG tool system.

## Task

Execute a complete system-wide optimization that includes:

1. **Cluster Analysis & Prime Tool Identification**
   - Identify all tool clusters in the system
   - For each cluster, find the "prime" tool (highest version/fittest)
   - Ensure the prime tool maintains all tool manager references

2. **Similarity-Based Weight Optimization**
   - For each tool, find similar tools within its clusters
   - If similarity exceeds the configurable threshold, adjust the optimization weight
   - Handle tools that belong to multiple clusters appropriately
   - Track cluster-specific optimization weights per tool

3. **Low-Score Tool Culling**
   - Identify tools with consistently low optimization scores across all their nodes
   - Cull (archive/remove) these low-performing tools
   - Ensure safe removal that doesn't break references

4. **Distance-Based Variant Pruning**
   - For each prime tool, find all related variants
   - Calculate semantic/performance distance from the prime
   - Drop variants that are too distant or redundant
   - Use a decay function based on distance from prime

## Configuration

Use these configurable parameters (can be overridden via config file):

```python
similarity_threshold = 0.85  # Threshold for considering tools similar
min_optimization_score = 0.50  # Minimum score to avoid culling
max_distance_from_prime = 0.30  # Maximum allowed distance from prime tool
weight_reduction_factor = 0.7  # Factor to reduce weight for similar tools
```

## Execution Steps

1. Load the current tool registry and RAG memory
2. Run the system optimizer with the workflow:
   - Identify clusters and prime tools
   - Calculate similarities and adjust weights
   - Cull low-scoring tools
   - Prune distant variants
3. Generate a detailed optimization report showing:
   - Number of clusters analyzed
   - Prime tools identified
   - Tools with adjusted weights
   - Tools culled
   - Variants pruned
   - Estimated performance improvement

## Implementation

Use the `SystemOptimizer` class from `code_evolver/src/system_optimizer.py`:

### Option 1: Use Configuration File (Recommended)

```python
from pathlib import Path
from code_evolver.src.system_optimizer import SystemOptimizer, load_config_from_file

# Load configuration from file
config_path = Path("code_evolver/config/optimization_config.yaml")
config = load_config_from_file(config_path)

# Create optimizer
optimizer = SystemOptimizer(config=config)

# Run full optimization
result = optimizer.run_full_optimization()

# Display results
print(result.summary())
```

### Option 2: Use Programmatic Configuration

```python
from code_evolver.src.system_optimizer import SystemOptimizer, OptimizationConfig

# Create optimizer with inline configuration
config = OptimizationConfig(
    similarity_threshold=0.85,
    min_optimization_score=0.50,
    max_distance_from_prime=0.30,
    weight_reduction_factor=0.7,
    dry_run=False,  # Set to True for testing
    verbose=True,
    report_path=Path("optimization_reports/optimization_report.json")
)

optimizer = SystemOptimizer(config=config)

# Run full optimization
result = optimizer.run_full_optimization()

# Display results
print(result.summary())
```

### Option 3: Use Default Configuration

```python
from code_evolver.src.system_optimizer import SystemOptimizer

# Use all defaults
optimizer = SystemOptimizer()

# Run full optimization
result = optimizer.run_full_optimization()

# Display results
print(result.summary())
```

## Safety

- Always backup the current state before optimization
- Validate that tool references remain intact
- Archive rather than delete to allow rollback
- Log all optimization decisions for audit trail
- **Use dry_run=True first** to preview changes before applying them

## Testing Before Running

Before running the optimization on production data, test with dry run mode:

```python
# Test with dry run first
config = OptimizationConfig(dry_run=True, verbose=True)
optimizer = SystemOptimizer(config=config)
result = optimizer.run_full_optimization()

# Review the results
print(result.summary())

# If satisfied, run for real
config.dry_run = False
result = optimizer.run_full_optimization()
```

## Expected Output

Provide a summary report including:
- Optimization metrics
- Actions taken
- Performance predictions
- Recommendations for next steps
- List of clusters analyzed
- Weight adjustments made
- Tools culled
- Variants pruned
