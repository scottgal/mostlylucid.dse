# Evolutionary Pressure Configuration

## Overview

The **evolutionary pressure** configuration option controls how the optimizer evolves the codebase over time. It determines whether the system tends towards smaller, more specific functions or larger, more encompassing ones.

This setting affects:
- **Clustering behavior**: How similar variants are grouped together
- **Node optimization**: Whether to create specialized or generalized functions
- **Variant pruning**: How aggressively to trim distant variants

## Configuration Options

The `evolutionary_pressure` setting can be configured for each optimization pressure level in `config.yaml`:

```yaml
optimization_pressure:
  high:
    evolutionary_pressure: "granular"  # Tend towards small, specific functions

  medium:
    evolutionary_pressure: "balanced"  # Middle ground

  low:
    evolutionary_pressure: "generic"   # Tend towards large, encompassing functions
```

### Pressure Values

#### `granular` - Small, Specific Functions

Best for:
- Highly specialized, single-purpose functions
- Strict type safety and validation
- Maximum code reusability through composition
- Microservices-style architecture

Behavior:
- **Tighter similarity thresholds** (0.98): Requires variants to be very similar to cluster together
- **Smaller distance tolerance** (0.15): Prunes variants that deviate significantly from the fittest
- **Higher minimum cluster size** (3): Avoids creating tiny, fragmented clusters
- **No function merging**: Keeps similar functions separate
- **High specialization bias** (0.8): Optimizes for specific use cases

Example:
```python
# Granular pressure creates focused, single-purpose functions
def validate_email(email: str) -> bool:
    """Validates only email format."""
    ...

def validate_domain(domain: str) -> bool:
    """Validates only domain names."""
    ...

def validate_url(url: str) -> bool:
    """Validates only URLs."""
    ...
```

---

#### `generic` - Large, Encompassing Functions

Best for:
- General-purpose utility functions
- Reducing code duplication
- Simplifying architecture
- Monolithic or framework-style code

Behavior:
- **Looser similarity thresholds** (0.85): Allows more diverse variants to cluster together
- **Larger distance tolerance** (0.50): Keeps more diverse variants in the cluster
- **Lower minimum cluster size** (1): Allows smaller, more flexible clusters
- **Function merging enabled**: Consolidates related functionality
- **Low specialization bias** (0.2): Optimizes for general use cases

Example:
```python
# Generic pressure creates multi-purpose, encompassing functions
def validate_input(input_value: str, input_type: str = "any") -> bool:
    """Validates multiple input types: email, domain, URL, etc."""
    if input_type == "email":
        ...
    elif input_type == "domain":
        ...
    elif input_type == "url":
        ...
    else:
        ...
```

---

#### `balanced` - Middle Ground (Default)

Best for:
- General application development
- Balanced architecture
- Not sure which approach to take

Behavior:
- **Standard similarity thresholds** (0.96): Default clustering behavior
- **Standard distance tolerance** (0.30): Default pruning behavior
- **Standard minimum cluster size** (2): Default cluster management
- **No special merging**: Standard function management
- **Balanced specialization** (0.5): Equal weight to both approaches

---

## How It Works

### 1. Configuration Loading

When the system starts, the `PressureManager` reads the `evolutionary_pressure` setting from the active pressure level:

```python
from src.pressure_manager import PressureManager, PressureLevel

pressure_manager = PressureManager(config_manager)
current_pressure = pressure_manager.get_current_pressure()

# Get evolutionary adjustments
adjustments = pressure_manager.get_evolutionary_adjustments(
    pressure=current_pressure,
    base_similarity=0.96,
    base_max_distance=0.30
)
```

### 2. Applying to Optimizers

The adjustments are applied to the optimizer configuration:

```python
from src.system_optimizer import OptimizationConfig

# Create optimizer config
config = OptimizationConfig()

# Apply evolutionary pressure adjustments
config.apply_evolutionary_adjustments(adjustments)

# Now the optimizer uses adjusted thresholds
optimizer = SystemOptimizer(config=config)
```

### 3. Clustering and Optimization

During optimization, the adjusted parameters control:

- **Variant clustering**: Similar functions are grouped based on the similarity threshold
- **Variant pruning**: Distant variants are removed based on the max distance threshold
- **Node merging**: Similar function nodes may be merged if `merge_similar_functions` is True

## Example Use Cases

### Use Case 1: Rapid Prototyping (Generic Pressure)

During early development, you want flexible, general-purpose functions:

```yaml
optimization_pressure:
  medium:
    evolutionary_pressure: "generic"  # Allow flexible, multi-purpose functions
```

### Use Case 2: Production Hardening (Granular Pressure)

For production code, you want focused, well-tested functions:

```yaml
optimization_pressure:
  low:
    evolutionary_pressure: "granular"  # Enforce specialized, single-purpose functions
```

### Use Case 3: Time-Based Strategy

Use auto rules to switch strategies based on time of day:

```yaml
optimization_pressure:
  auto:
    enabled: true
    rules:
      # Overnight: Allow aggressive optimization towards generic functions
      - condition: "hour >= 22 or hour <= 6"
        pressure: "low"  # Uses generic evolutionary pressure

      # Business hours: Maintain strict, granular functions
      - condition: "hour >= 9 and hour <= 17"
        pressure: "high"  # Uses granular evolutionary pressure
```

## Advanced Configuration

### Custom Adjustments

You can override specific parameters in your code:

```python
from src.pressure_manager import PressureManager

pressure_manager = PressureManager(config_manager)
adjustments = pressure_manager.get_evolutionary_adjustments(
    pressure=PressureLevel.LOW,
    base_similarity=0.90,      # Custom base similarity
    base_max_distance=0.40     # Custom base max distance
)

# For generic pressure:
# similarity_threshold = max(0.85, 0.90 - 0.11) = 0.85
# max_distance_from_fittest = min(0.50, 0.40 + 0.20) = 0.50
```

### Node-Specific Configuration

Apply different evolutionary pressures to different node types:

```python
from src.rag_cluster_optimizer import NodeTypeOptimizerConfig, NodeType

# Granular pressure for functions
function_config = NodeTypeOptimizerConfig(node_type=NodeType.FUNCTION)
function_config.apply_evolutionary_adjustments(
    pressure_manager.get_evolutionary_adjustments(
        PressureLevel.HIGH  # Granular
    )
)

# Generic pressure for workflows
workflow_config = NodeTypeOptimizerConfig(node_type=NodeType.WORKFLOW)
workflow_config.apply_evolutionary_adjustments(
    pressure_manager.get_evolutionary_adjustments(
        PressureLevel.LOW  # Generic
    )
)
```

## Monitoring and Metrics

Track the impact of evolutionary pressure:

```python
# In your optimizer logs, you'll see:
# INFO: Applied evolutionary pressure adjustments:
#       pressure=granular, similarity=0.98, max_distance=0.15

# Monitor clustering behavior:
# DEBUG: Granular evolutionary pressure: tighter clustering (sim=0.98)
```

## Best Practices

1. **Start balanced**: Use `"balanced"` until you understand your codebase's needs
2. **Measure impact**: Track function count, complexity, and reusability metrics
3. **Iterate gradually**: Switch between granular/generic and observe results
4. **Context matters**: Use granular for critical paths, generic for utilities
5. **Document decisions**: Note why you chose a particular pressure for your team

## Troubleshooting

### Too many small functions (over-fragmentation)

**Symptom**: Hundreds of tiny, single-line functions

**Solution**: Switch to `"generic"` or `"balanced"` pressure

```yaml
evolutionary_pressure: "generic"  # Consolidate functions
```

### Too many monolithic functions (under-specialization)

**Symptom**: Large, complex functions doing many things

**Solution**: Switch to `"granular"` pressure

```yaml
evolutionary_pressure: "granular"  # Break down functions
```

### Unstable clustering

**Symptom**: Variants constantly moving between clusters

**Solution**: Increase similarity threshold or use balanced pressure

```yaml
evolutionary_pressure: "balanced"  # More stable clustering
```

---

## API Reference

### PressureManager.get_evolutionary_adjustments()

```python
def get_evolutionary_adjustments(
    self,
    pressure: PressureLevel,
    base_similarity: float = 0.96,
    base_max_distance: float = 0.30
) -> Dict[str, Any]:
    """
    Get evolutionary pressure adjustments for optimizer parameters.

    Args:
        pressure: Current pressure level
        base_similarity: Base similarity threshold (default: 0.96)
        base_max_distance: Base max distance from fittest (default: 0.30)

    Returns:
        Dict with adjusted parameters:
            - evolutionary_pressure: str ("granular", "generic", or "balanced")
            - similarity_threshold: float (adjusted clustering threshold)
            - max_distance_from_fittest: float (adjusted pruning threshold)
            - min_cluster_size: int (minimum variants per cluster)
            - merge_similar_functions: bool (whether to merge similar nodes)
            - specialization_bias: float (0.0=generic, 1.0=specialized)
    """
```

### OptimizationConfig.apply_evolutionary_adjustments()

```python
def apply_evolutionary_adjustments(self, adjustments: Dict[str, Any]) -> None:
    """
    Apply evolutionary pressure adjustments from PressureManager.

    Args:
        adjustments: Dict from PressureManager.get_evolutionary_adjustments()

    Updates:
        - cluster_similarity_threshold
        - max_distance_from_prime
        - min_cluster_size
        - merge_similar_functions
        - specialization_bias
    """
```

---

## See Also

- [Optimization Pressure Configuration](./optimization_pressure.md)
- [RAG Cluster Optimizer](./rag_cluster_optimizer.md)
- [System Optimizer](./system_optimizer.md)
