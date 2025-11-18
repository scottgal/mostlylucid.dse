# Universal Comparison Tool

A comprehensive comparison framework for Code Evolver that supports performance testing, content comparison, and quality analysis with hooks into the telemetry system.

## Features

- **Performance Comparison**: Compare execution speed of two endpoints/functions
- **Content Comparison**: Text similarity, diff analysis, semantic matching
- **Quality Comparison**: Custom quality metrics evaluation
- **Multiple Strategies**: Sequential, interleaved, parallel, warmup, sustained load testing
- **Telemetry Integration**: Hooks into OpenTelemetry for tracking
- **Relative Scoring**: 0-infinity scale (0=failed, 100=identical, >100=faster)

## Quick Start

### Performance Comparison

```python
from src.comparer_tool import compare_performance

# Compare two functions
result = compare_performance(
    func_a=my_implementation,
    func_b=reference_implementation,
    params_a={"data": test_data},
    params_b={"data": test_data},
    iterations=10,
    strategy="interleaved"
)

print(result.summary)
print(f"Score: {result.score}")  # >100 means A is faster
print(f"Winner: {result.winner}")
```

### Text Comparison

```python
from src.comparer_tool import compare_text

# Compare two text strings
result = compare_text(
    text_a="Original text",
    text_b="Modified text",
    method="similarity"  # or "diff" or "semantic"
)

print(result.summary)
print(f"Similarity: {result.score}%")
```

### Quality Comparison

```python
from src.comparer_tool import compare_quality

# Define quality metrics
def code_quality(code: str) -> float:
    """Score code quality (0-100)"""
    # Count docstrings, type hints, etc.
    score = 0
    if '"""' in code:
        score += 25
    if '->' in code:
        score += 25
    if 'def ' in code:
        score += 25
    if 'return' in code:
        score += 25
    return score

# Compare two implementations
result = compare_quality(
    item_a=implementation_a,
    item_b=implementation_b,
    metrics=[code_quality, complexity_score, maintainability_score]
)

print(result.summary)
```

## Comparison Strategies

### Performance Testing Strategies

1. **Sequential**: Run all A iterations, then all B iterations
   - Best for: Avoiding interference between tests
   - Use when: Functions modify global state

2. **Interleaved**: Alternate between A and B (A, B, A, B...)
   - Best for: Fair comparison accounting for warmup
   - Use when: Most general-purpose performance testing (default)

3. **Parallel**: Run A and B simultaneously
   - Best for: Testing under concurrent load
   - Use when: Testing APIs, databases, network services

4. **Warmup**: Run several iterations before measuring
   - Best for: JIT-compiled code, caches
   - Use when: Initial runs are significantly slower

5. **Sustained**: Long-duration load testing
   - Best for: Memory leaks, resource exhaustion
   - Use when: Testing long-running processes

### Content Comparison Methods

1. **Similarity**: Overall text similarity score using SequenceMatcher
2. **Diff**: Line-by-line diff analysis
3. **Semantic**: Embedding-based semantic similarity (requires RAG)

## Scoring Scale

### Performance Score

The performance score uses a 0-infinity scale:

- **0**: Endpoint A completely failed (dead stop)
- **50**: Endpoint B is 2x faster than A
- **100**: Endpoints are identical in speed
- **200**: Endpoint A is 2x faster than B
- **300**: Endpoint A is 3x faster than B

Formula: `score = 100 * (mean_b / mean_a)`

### Content/Quality Score

Text and quality comparisons use a 0-100 scale:

- **0-40**: Very different
- **40-60**: Somewhat different
- **60-80**: Moderately similar
- **80-95**: Very similar
- **95-100**: Nearly identical
- **100**: Identical

## Advanced Usage

### With Telemetry Integration

```python
from src.comparer_tool import PerformanceComparer
from src.telemetry_tracker import get_tracker

# Get telemetry tracker
tracker = get_tracker()

# Create comparer with telemetry
comparer = PerformanceComparer(telemetry_tracker=tracker)

# Comparisons will now be tracked in OpenTelemetry
result = await comparer.compare_endpoints(
    endpoint_a=func_a,
    endpoint_b=func_b,
    params_a={},
    params_b={},
    iterations=10
)
```

### Async Functions

```python
import asyncio
from src.comparer_tool import PerformanceComparer, ComparisonStrategy

async def async_function_a(data):
    await asyncio.sleep(0.01)
    return process(data)

async def async_function_b(data):
    await asyncio.sleep(0.005)
    return process_optimized(data)

comparer = PerformanceComparer()

result = await comparer.compare_endpoints(
    endpoint_a=async_function_a,
    endpoint_b=async_function_b,
    params_a={"data": test_data},
    params_b={"data": test_data},
    iterations=20,
    strategy=ComparisonStrategy.PARALLEL
)
```

### Custom Quality Metrics

```python
from src.comparer_tool import ContentComparer

def readability(text: str) -> float:
    """Score readability (0-100)"""
    words = len(text.split())
    sentences = text.count('.') + text.count('!') + text.count('?')
    avg_words = words / max(sentences, 1)
    # Ideal: 15-20 words per sentence
    if 15 <= avg_words <= 20:
        return 100
    return max(0, 100 - abs(avg_words - 17.5) * 5)

def completeness(text: str) -> float:
    """Score completeness (0-100)"""
    required = ['example', 'usage', 'parameters', 'returns']
    found = sum(1 for kw in required if kw.lower() in text.lower())
    return (found / len(required)) * 100

comparer = ContentComparer()

result = comparer.compare_quality(
    item_a=docs_a,
    item_b=docs_b,
    quality_metrics=[readability, completeness]
)
```

## Result Object

All comparison methods return a `ComparisonResult` object:

```python
@dataclass
class ComparisonResult:
    type: ComparisonType          # performance, content, quality, semantic
    item_a_name: str              # Name of first item
    item_b_name: str              # Name of second item
    score: float                  # Comparison score
    winner: Optional[str]         # Which item "won" (or None for tie)
    details: Dict[str, Any]       # Detailed metrics
    summary: str                  # Human-readable summary
    timestamp: datetime           # When comparison was performed
```

### Accessing Results

```python
# Get summary
print(result.summary)

# Get winner
if result.winner:
    print(f"Winner: {result.winner}")
else:
    print("It's a tie!")

# Get detailed metrics
print(f"Endpoint A mean: {result.details['endpoint_a']['mean_ms']}ms")
print(f"Endpoint B mean: {result.details['endpoint_b']['mean_ms']}ms")

# Export to JSON
import json
with open('results.json', 'w') as f:
    json.dump(result.to_dict(), f, indent=2)
```

## Examples

See `code_evolver/examples/compare_example.py` for comprehensive examples including:

1. Performance comparison (bubble sort vs built-in sort)
2. Text similarity comparison
3. Quality comparison with custom metrics
4. Real-world API endpoint comparison

Run examples:

```bash
cd code_evolver/examples
python compare_example.py
```

## Testing

Run the test suite:

```bash
cd code_evolver
python -m pytest ../tests/test_comparer_tool.py -v
```

Tests cover:

- All comparison strategies (sequential, interleaved, parallel)
- Error handling (endpoint failures, both failing)
- Text comparison methods (similarity, diff, semantic)
- Quality metrics
- Edge cases (empty strings, zero iterations, invalid methods)

## Integration with Code Evolver

### Use in Node Evaluation

```python
from src.comparer_tool import compare_performance
from src.node_runner import NodeRunner

runner = NodeRunner()

# Compare two node versions
result = compare_performance(
    func_a=lambda: runner.run_node("my_func_v1", test_input),
    func_b=lambda: runner.run_node("my_func_v2", test_input),
    params_a={},
    params_b={},
    iterations=10,
    strategy="interleaved"
)

if result.winner == "func_b":
    print("Version 2 is faster! Consider promoting it.")
```

### Use in Auto-Evolution

```python
from src.auto_evolver import AutoEvolver
from src.comparer_tool import PerformanceComparer

evolver = AutoEvolver(...)
comparer = PerformanceComparer()

# Compare original vs evolved version
result = await comparer.compare_endpoints(
    endpoint_a=original_implementation,
    endpoint_b=evolved_implementation,
    params_a=test_params,
    params_b=test_params,
    iterations=20
)

# Only keep evolved version if it's significantly better
if result.score > 120:  # 20% faster
    evolver.promote_version(evolved_id)
else:
    print("Evolution didn't improve performance enough")
```

### Use in Workflow Comparison

```python
from src.comparer_tool import compare_quality

# Compare two workflow outputs
result = compare_quality(
    item_a=workflow_output_a,
    item_b=workflow_output_b,
    metrics=[
        code_quality_score,
        test_coverage_score,
        documentation_score
    ]
)

print(f"Workflow A quality: {result.details['mean_quality_a']}")
print(f"Workflow B quality: {result.details['mean_quality_b']}")
```

## Configuration

The comparison tool respects the telemetry configuration in `config/telemetry.yaml`:

```yaml
telemetry:
  enabled: true
  service_name: "code-evolver"
  traces_endpoint: "http://localhost:4318/v1/traces"
```

When telemetry is enabled, all performance comparisons are automatically tracked as spans in OpenTelemetry.

## Best Practices

1. **Choose the right strategy**:
   - Use `interleaved` for most general-purpose comparisons
   - Use `parallel` for testing concurrent load
   - Use `warmup` for JIT-compiled code

2. **Run enough iterations**:
   - Minimum 10 iterations for reliable results
   - More iterations for variable workloads
   - Consider warmup iterations for cached operations

3. **Handle failures gracefully**:
   - The tool handles partial failures (some iterations fail)
   - Check `result.details['errors']` for failure count
   - Score of 0 means complete failure

4. **Use quality metrics wisely**:
   - Define clear, objective metrics
   - Metrics should return 0-100 scores
   - Combine multiple metrics for holistic view

5. **Save results**:
   - Use `result.to_dict()` to serialize results
   - Store comparisons in RAG for learning
   - Track trends over time

## Troubleshooting

### High Variance in Results

If performance scores vary significantly between runs:

- Increase iterations (20-50)
- Add warmup iterations (2-5)
- Use `sustained` strategy for long-running tests
- Check for background processes affecting system

### Memory Issues

For memory-intensive comparisons:

- Reduce iterations
- Use `sequential` strategy instead of `parallel`
- Monitor memory in `result.details['memory_mb']`

### Telemetry Not Working

If telemetry integration fails:

- Check OpenTelemetry collector is running
- Verify `telemetry.yaml` configuration
- Tool works fine without telemetry (logs warning)

## API Reference

### PerformanceComparer

```python
class PerformanceComparer:
    def __init__(self, telemetry_tracker=None):
        """Initialize with optional telemetry tracker"""

    async def compare_endpoints(
        self,
        endpoint_a: Callable,
        endpoint_b: Callable,
        params_a: Dict[str, Any],
        params_b: Dict[str, Any],
        iterations: int = 10,
        strategy: ComparisonStrategy = ComparisonStrategy.INTERLEAVED,
        warmup_iterations: int = 2
    ) -> ComparisonResult:
        """Compare performance of two endpoints"""
```

### ContentComparer

```python
class ContentComparer:
    def __init__(self, rag_memory=None):
        """Initialize with optional RAG memory for semantic comparison"""

    def compare_text(
        self,
        text_a: str,
        text_b: str,
        method: str = "similarity"
    ) -> ComparisonResult:
        """Compare two text strings"""

    def compare_quality(
        self,
        item_a: Any,
        item_b: Any,
        quality_metrics: List[Callable[[Any], float]]
    ) -> ComparisonResult:
        """Compare quality using custom metrics"""
```

### Convenience Functions

```python
def compare_performance(
    func_a: Callable,
    func_b: Callable,
    params_a: Dict,
    params_b: Dict,
    iterations: int = 10,
    strategy: str = "interleaved"
) -> ComparisonResult:
    """Quick performance comparison"""

def compare_text(
    text_a: str,
    text_b: str,
    method: str = "similarity"
) -> ComparisonResult:
    """Quick text comparison"""

def compare_quality(
    item_a: Any,
    item_b: Any,
    metrics: List[Callable]
) -> ComparisonResult:
    """Quick quality comparison"""
```

## License

MIT License - Part of Code Evolver

## Related Documentation

- [TELEMETRY_README.md](../../TELEMETRY_README.md) - OpenTelemetry integration
- [RAG_GUIDE.md](../../RAG_GUIDE.md) - RAG memory system
- [AUTO_EVOLUTION.md](../../AUTO_EVOLUTION.md) - Automatic code evolution
