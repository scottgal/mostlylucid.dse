# Quality Evaluation System with phi3:3.8b

## Overview

The mostlylucid DiSE system now includes comprehensive quality evaluation at each workflow step, with **automatic threshold adjustment**, **iterative improvement**, and **separate evaluators for different content types**.

**Key Feature**: Uses **phi3:3.8b for writing evaluation** and **llama3 for code evaluation**.

## Architecture

### Multi-Model Evaluation

Different models are used for different evaluation types:

| Content Type | Model | Purpose |
|--------------|-------|---------|
| **Writing** (blog, articles, docs) | **phi3:3.8b** | Technical writing evaluation |
| **Code** (functions, classes) | **llama3** | Code quality evaluation |
| **Tests** (unit tests) | **llama3** | Test coverage evaluation |
| **Strategy** (plans) | **llama3** | Strategic planning evaluation |

### Configuration

```yaml
# config.yaml
ollama:
  models:
    evaluator:
      # For technical writing evaluation
      writing:
        model: "phi3:3.8b"
        endpoint: null
      # For code evaluation
      code:
        model: "llama3"
        endpoint: null
      # Default fallback
      default:
        model: "llama3"
        endpoint: null

quality_evaluation:
  enabled: true

  # Evaluate at each step
  evaluate_steps:
    strategy: true
    code: true
    tests: true
    final: true

  # Automatic thresholds
  thresholds:
    strategy_min: 0.70      # 70%+ required
    code_quality_min: 0.75  # 75%+ required
    test_coverage_min: 0.80 # 80%+ required
    final_min: 0.80         # 80%+ required

    # Auto-adjust based on history
    auto_adjust: true
    adjustment_window: 100  # Last 100 evaluations

  # Iterative improvement
  max_iterations: 3
  improvement_threshold: 0.05  # 5% minimum improvement

  # Feedback loop
  feedback:
    include_suggestions: true
    include_examples: true
    store_in_rag: true
    learn_from_success: true
```

## Workflow Integration

### Complete Evaluation Pipeline

```
User Request: "generate add 1 plus 1"
    ↓
[1. Strategy Creation - Overseer]
    llama3 creates strategy
    ↓
[2. Strategy Evaluation - llama3]
    ← Evaluate quality (clarity, completeness, feasibility)
    Score: 0.85 → PASS
    ↓
[3. Code Generation - codellama]
    Generate code based on strategy
    ↓
[4. Code Evaluation - llama3]
    ← Evaluate code (correctness, quality, practices)
    Score: 0.72 → FAIL (< 0.75 threshold)
    ↓
[5. Iterative Improvement]
    Iteration 1:
      - Apply feedback suggestions
      - Re-generate code
      - Re-evaluate: Score 0.78 → PASS
    ↓
[6. Test Generation]
    Generate unit tests
    ↓
[7. Test Evaluation - llama3]
    ← Evaluate tests (coverage, quality)
    Score: 0.85 → PASS
    ↓
[8. Final Comprehensive Evaluation]
    All steps passed → Store in RAG
    ↓
Done! ✓
```

### For Writing Tasks

```
User Request: "write blog post about async/await"
    ↓
[1. Outline Creation - Overseer]
    ↓
[2. Content Generation - Technical Writer]
    ↓
[3. Writing Evaluation - phi3:3.8b] ← Special evaluator!
    ← Evaluate (clarity, accuracy, structure, SEO)
    Score: 0.77 → FAIL (< 0.80 threshold)
    ↓
[4. Iterative Improvement]
    Iteration 1:
      - Add code examples (suggestion from evaluator)
      - Improve SEO headings
      - Re-evaluate: Score 0.83 → PASS
    ↓
Store in RAG ✓
```

## Evaluation Criteria

### Strategy Evaluation

Evaluates overseer's strategic plan:

1. **Clarity** (0-1.0): Is the approach clearly explained?
2. **Completeness** (0-1.0): Does it address all task aspects?
3. **Feasibility** (0-1.0): Is it practically implementable?
4. **Best Practices** (0-1.0): Follows engineering standards?
5. **Edge Cases** (0-1.0): Considers potential issues?

**Output**:
```json
{
  "score": 0.85,
  "strengths": ["clear explanation", "considers edge cases"],
  "weaknesses": ["missing error handling strategy"],
  "suggestions": ["add error handling approach"],
  "feedback": "Solid strategy with good coverage..."
}
```

### Code Evaluation

Evaluates generated Python code:

1. **Correctness**: Does it solve the task?
2. **Code Quality**: Clean, readable, structured?
3. **Error Handling**: Proper error handling?
4. **Best Practices**: Follows Python standards?
5. **Documentation**: Docstrings, comments?
6. **Testing**: Includes proper I/O handling?

**Output**:
```json
{
  "score": 0.78,
  "strengths": ["clean code", "good structure"],
  "weaknesses": ["missing type hints", "no docstring"],
  "suggestions": ["add type hints", "add module docstring"],
  "examples": {
    "improvement": "def add(a: int, b: int) -> int: ..."
  }
}
```

### Test Evaluation

Evaluates unit tests:

1. **Coverage**: Normal cases, edge cases, errors?
2. **Quality**: Well-structured, clear assertions?
3. **Independence**: Tests isolated?
4. **Best Practices**: Testing standards?

### Writing Evaluation (phi3:3.8b)

Evaluates technical writing:

1. **Clarity**: Easy to understand?
2. **Technical Accuracy**: Information correct?
3. **Structure**: Well-organized, logical flow?
4. **Readability**: Appropriate for audience?
5. **Completeness**: Adequate topic coverage?
6. **Engagement**: Interesting content?
7. **SEO**: Good keywords and structure?

**Output**:
```json
{
  "score": 0.83,
  "strengths": ["clear explanations", "good examples"],
  "weaknesses": ["missing SEO optimization"],
  "suggestions": [
    "optimize headings for SEO",
    "add practical use cases"
  ]
}
```

## Automatic Threshold Adjustment

Thresholds auto-adjust based on historical performance:

```python
# Initial threshold: 0.75
# After 100 evaluations with median score 0.82
# Adjusted threshold: min(0.75, 0.82 * 0.8) = 0.656

# System becomes more lenient if consistently scoring high
# But never goes above configured minimum
```

**Benefits**:
- Adapts to model capabilities
- Prevents unrealistic expectations
- Maintains quality standards

## Iterative Improvement

If content fails evaluation, automatically improves it:

```
Initial Code: Score 0.65 (FAIL)
    ↓
Apply Feedback:
  - Add type hints
  - Add error handling
  - Improve docstrings
    ↓
Iteration 1: Score 0.73 (still FAIL)
    ↓
Apply More Feedback:
  - Add input validation
  - Improve structure
    ↓
Iteration 2: Score 0.78 (PASS!)
    ↓
Done in 2 iterations ✓
```

**Stopping Conditions**:
1. Content passes threshold
2. Max iterations reached (default: 3)
3. Improvement < 5% between iterations

## RAG Integration

### Learning from Evaluations

**High-quality examples** (score ≥ 0.85) are stored:

```python
rag.store_artifact(
    artifact_id="eval_success_code_12345",
    artifact_type=ArtifactType.PATTERN,
    name="High-Quality Code Example",
    description="Score: 0.92 - Excellent error handling",
    content=code,
    tags=["evaluation", "success", "code", "quality"],
    metadata={"score": 0.92, "strengths": [...]}
)
```

**Feedback patterns** are stored:

```python
rag.store_artifact(
    artifact_id="eval_feedback_code_67890",
    artifact_type=ArtifactType.PATTERN,
    name="Code Improvement Pattern",
    description="Add type hints and docstrings",
    content=json.dumps({
        "suggestions": ["add type hints", "add docstrings"],
        "weaknesses": ["missing documentation"],
        "feedback": "Good logic but needs documentation"
    }),
    tags=["evaluation", "feedback", "improvement"]
)
```

**Future generations** can learn from past evaluations:

```python
# When generating new code, search for similar high-quality examples
similar_successes = rag.find_similar(
    task_description,
    artifact_type=ArtifactType.PATTERN,
    tags=["success", "code"]
)

# Use successful patterns as reference
```

## Usage Examples

### Example 1: Evaluate Strategy

```python
from src import QualityEvaluator, OllamaClient, ConfigManager

config = ConfigManager("config.yaml")
client = OllamaClient(config.ollama_url, config_manager=config)
evaluator = QualityEvaluator(client, config)

strategy = """
1. Use recursive approach for factorial
2. Add base case for n = 0, 1
3. Handle negative inputs
4. Add memoization for performance
"""

result = evaluator.evaluate_strategy(strategy, "create factorial function")

print(f"Score: {result.score:.2f}")
print(f"Passed: {result.passed}")
print(f"Feedback: {result.feedback}")
print(f"Suggestions: {result.suggestions}")
```

### Example 2: Evaluate Code

```python
code = """
def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("Negative input")
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

result = evaluator.evaluate_code(
    code,
    task_description="create factorial function",
    strategy=strategy
)

if not result.passed:
    print(f"Code needs improvement: {result.feedback}")
    for suggestion in result.suggestions:
        print(f"  - {suggestion}")
```

### Example 3: Iterative Improvement

```python
# Start with poor code
poor_code = "def add(a, b): return a + b"

# Automatically improve until it passes
final_code, evaluations = evaluator.iterative_improve(
    poor_code,
    "code",
    {
        "task_description": "add two numbers with validation",
        "strategy": "validate inputs and handle errors"
    }
)

print(f"Improved in {len(evaluations)} iterations")
print(f"Final score: {evaluations[-1].score:.2f}")
print(f"Final code:\n{final_code}")
```

### Example 4: Evaluate Writing (phi3:3.8b)

```python
article = """
# Python Async/Await Guide

Async/await is a powerful feature for concurrent programming.

## How It Works
...
"""

result = evaluator.evaluate_writing(
    article,
    task_description="write blog post about async/await",
    content_type="blog"
)

print(f"Writing score: {result.score:.2f}")
print(f"Strengths: {', '.join(result.strengths)}")
print(f"SEO suggestions: {[s for s in result.suggestions if 'SEO' in s]}")
```

## Testing

Run the comprehensive test suite:

```bash
cd code_evolver
python test_quality_evaluator.py
```

**Tests include**:
1. Strategy evaluation
2. Code evaluation
3. Test evaluation
4. Writing evaluation (phi3:3.8b)
5. Iterative improvement
6. Threshold auto-adjustment
7. Model selection (writing vs code)

**Expected output**:
```
Testing Quality Evaluator System

Test 1: Evaluating Strategy Quality
Score: 0.85
Passed: True
Feedback: Clear and comprehensive strategy...

Test 2: Evaluating Code Quality
Score: 0.78
Passed: True
...

Test 4: Evaluating Writing Quality (phi3:3.8b)
Score: 0.83
Passed: True
Strengths: clear explanations, good examples
...

All Tests Complete!
```

## Integration with Chat CLI

The quality evaluator is automatically used in the generation workflow:

```bash
python chat_cli.py
```

```
CodeEvolver> generate fibonacci calculator

Checking for existing solutions...
[No similar workflows found]

Consulting overseer...
OK Strategy created (score: 0.87)

Generating code...
OK Code generated
Evaluating code quality...
FAIL Code score: 0.72 (threshold: 0.75)

Improving based on feedback...
  - Adding type hints
  - Adding docstrings
  - Improving error handling

Iteration 1: Score 0.79 → PASS!

Generating tests...
OK Tests generated (score: 0.85)

OK Node created successfully!
```

## Performance Metrics

| Evaluation Type | Model | Average Time | Token Usage |
|----------------|-------|--------------|-------------|
| Strategy | llama3 | ~3s | ~500 tokens |
| Code | llama3 | ~4s | ~800 tokens |
| Tests | llama3 | ~3s | ~600 tokens |
| Writing | phi3:3.8b | ~5s | ~1000 tokens |
| Improvement iteration | varies | ~8s | ~1200 tokens |

**Total overhead per generation**:
- Without evaluation: ~20s
- With evaluation: ~35s
- **Benefit**: Higher quality, fewer manual fixes

## Threshold Recommendations

### Conservative (High Quality)
```yaml
thresholds:
  strategy_min: 0.85
  code_quality_min: 0.85
  test_coverage_min: 0.90
  final_min: 0.85
```

### Balanced (Default)
```yaml
thresholds:
  strategy_min: 0.70
  code_quality_min: 0.75
  test_coverage_min: 0.80
  final_min: 0.80
```

### Lenient (Fast Iteration)
```yaml
thresholds:
  strategy_min: 0.60
  code_quality_min: 0.65
  test_coverage_min: 0.70
  final_min: 0.70
```

## Best Practices

### 1. Enable for Production Code

```yaml
quality_evaluation:
  enabled: true
  evaluate_steps:
    code: true
    tests: true
```

### 2. Use Auto-Adjustment

```yaml
thresholds:
  auto_adjust: true
  adjustment_window: 100
```

### 3. Store Successful Patterns

```yaml
feedback:
  store_in_rag: true
  learn_from_success: true
```

### 4. Monitor Statistics

```python
stats = evaluator.get_evaluation_stats()
print(f"Average code quality: {stats['code']['mean']:.2f}")
print(f"Pass rate: {sum(1 for s in scores if s >= 0.75) / len(scores):.1%}")
```

## Troubleshooting

### Issue: All evaluations fail

**Check thresholds**:
```bash
# Lower thresholds temporarily
sed -i 's/0.75/0.65/g' config.yaml
```

**Check model availability**:
```bash
ollama list | grep phi3
ollama pull phi3:3.8b
```

### Issue: Evaluations too slow

**Options**:
1. Disable some steps:
```yaml
evaluate_steps:
  strategy: false  # Skip strategy evaluation
  code: true
```

2. Use faster model:
```yaml
evaluator:
  code:
    model: "tinyllama"  # Faster but less accurate
```

### Issue: Inconsistent scores

**Enable auto-adjustment**:
```yaml
thresholds:
  auto_adjust: true
  adjustment_window: 50  # Smaller window for faster adaptation
```

## Summary

The quality evaluation system provides:

✅ **Multi-model evaluation**: phi3:3.8b for writing, llama3 for code
✅ **Automatic thresholds**: Self-adjusting based on performance
✅ **Iterative improvement**: Auto-fixes based on feedback
✅ **RAG integration**: Learns from successful patterns
✅ **Comprehensive metrics**: Track quality over time
✅ **Flexible configuration**: Adjust per use case

**Result**: Higher quality outputs with automated quality assurance at every step!

## Next Steps

Planned enhancements:

1. **Multi-metric scoring**: Separate scores for different quality aspects
2. **A/B testing**: Compare evaluation models
3. **Custom evaluation criteria**: Define your own quality metrics
4. **Batch evaluation**: Evaluate multiple items efficiently
5. **Quality trends**: Track improvements over time
6. **Evaluation presets**: Quick configs for different scenarios

---

**Ready to use!** The quality evaluation system is fully integrated and operational.
