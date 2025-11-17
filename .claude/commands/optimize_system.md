# Optimize System Command

You are a system optimization specialist. Your task is to run a full optimization workflow on the RAG tool system with neighbor-based testing and version-aware clustering.

## Task

Execute a complete system-wide optimization that includes:

1. **Cluster Analysis & Prime Tool Identification**
   - Identify all tool clusters in the system (including version-based clusters)
   - For each cluster, find the "prime" tool (highest version/fittest)
   - Rank clusters by performance scores to prioritize optimization
   - Ensure the prime tool maintains all tool manager references

2. **Neighbor-Based Testing & Mutation** ✨ NEW
   - For each tool, find its 10 closest neighbors with matching interfaces
   - Test tool against each neighbor (near or higher performance)
   - If neighbor performs better, mutate current tool with neighbor's improvements
   - Repeat iteratively until no improvement from top 10 neighbors
   - If new variant outperforms prime, promote it to prime status

3. **Similarity-Based Weight Optimization**
   - For each tool, find similar tools within its clusters
   - If similarity exceeds the configurable threshold, adjust the optimization weight
   - Handle tools that belong to multiple clusters appropriately
   - Track cluster-specific optimization weights per tool

4. **Low-Score Tool Culling**
   - Identify tools with consistently low optimization scores across all their nodes
   - Cull (archive/remove) these low-performing tools
   - Ensure safe removal that doesn't break references

5. **Distance-Based Variant Pruning**
   - For each prime tool, find all related variants
   - Calculate semantic/performance distance from the prime
   - Drop variants that are too distant or redundant
   - Use a decay function based on distance from prime

6. **Version-Aware Cluster Formation** ✨ NEW
   - Automatically form clusters around tool versions
   - Track all tool calls with name + version for cluster identification
   - Enable better versions to naturally become current through testing
   - Maintain ability to specialize while promoting best versions

7. **Tool Split Detection (Specialization)** ✨ NEW & IMPORTANT
   - Uses LLM (4B model) to detect when variants have diverged enough to be different tools
   - Analyzes drift between spec, interface, tests, and implementation (0-100 score)
   - LLM suggests unique new tool name if split is warranted
   - Creates deprecation pointers for backward compatibility
   - **This is the OPPOSITE of clustering** - it specializes rather than generalizes
   - Prevents false unification of fundamentally different tools

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

### Basic Optimization (Original)

Use the `SystemOptimizer` class from `code_evolver/src/system_optimizer.py`:

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

### Advanced Optimization with Neighbor Testing ✨ NEW & RECOMMENDED

Use the `NeighborOptimizer` class from `code_evolver/src/neighbor_optimizer.py`:

```python
from pathlib import Path
from code_evolver.src.neighbor_optimizer import NeighborOptimizer
from code_evolver.src.system_optimizer import load_config_from_file
from code_evolver.src.versioned_tool_manager import VersionedToolManager

# Initialize version-aware tool manager
tool_manager = VersionedToolManager()

# Load configuration
config_path = Path("code_evolver/config/optimization_config.yaml")
config = load_config_from_file(config_path)

# Create neighbor optimizer with test function
optimizer = NeighborOptimizer(
    config=config,
    tools_manager=tool_manager
    # test_function will use default if not specified
)

# Run full optimization with neighbor testing
result = optimizer.run_full_optimization_with_neighbors()

# Display results
print(result.summary())

# Access neighbor optimization details
for opt in result.neighbor_optimizations:
    print(f"Cluster: {opt['cluster_id']}")
    print(f"  Improved: {opt['improvement']*100:.1f}%")
    for log_entry in opt['log']:
        print(f"    {log_entry}")
```

### Version-Aware Tool Calling ✨ NEW

Use the `call_tool` function for automatic version tracking:

```python
from code_evolver.src.versioned_tool_caller import call_tool, analyze_version_clusters

# Call a tool with version specification
result = call_tool(
    "parse_cron",
    args={"expression": "0 0 * * *"},
    version="best"  # or "latest", "1.2.3", "1.2", etc.
)

# Analyze version clusters from call history
analysis = analyze_version_clusters()

print("Cluster Analysis:")
for tool_name, cluster_info in analysis['clusters'].items():
    print(f"  {tool_name}:")
    print(f"    Dominant version: {cluster_info['dominant_version']}")
    print(f"    Usage: {cluster_info['dominant_usage_percent']:.1f}%")
    print(f"    Best version: {cluster_info['best_version']}")

# View recommendations
for recommendation in analysis['recommendations']:
    print(f"  💡 {recommendation}")
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
- Neighbor optimization results (iterations, mutations, improvements)
- Version cluster formation statistics

## Version-Aware Code Generation

When generating code that calls tools, ALWAYS specify the tool name and version:

### ❌ OLD WAY (Don't do this):
```python
# This doesn't track versions
result = some_function()
```

### ✅ NEW WAY (Do this):
```python
from code_evolver.src.versioned_tool_caller import call_tool

# Explicitly track tool name and version
result = call_tool(
    "some_function",
    args={"param": "value"},
    version="best"  # or specific version like "1.2.3"
)
```

This enables:
1. **Cluster identification** - See which versions are used together
2. **Performance tracking** - Monitor which versions perform best
3. **Safe optimization** - Don't break during optimization cycles
4. **Automatic promotion** - Better versions naturally become current

## Benefits of Version-Aware Optimization

1. **Cluster Formation**: New clusters automatically form around popular versions
2. **Natural Evolution**: Better versions organically become the default through testing
3. **Specialization**: Maintain ability to use specific versions when needed
4. **Safe Refactoring**: Old versions remain available during transitions
5. **Performance History**: Track performance improvements across versions
6. **Automatic Discovery**: Identify optimization opportunities from usage patterns
