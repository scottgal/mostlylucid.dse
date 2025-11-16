# Static Analysis Integration with Registry & RAG

## Overview

**Static analysis results** are now stored in:
1. **Registry** - For node-specific tracking and metrics
2. **RAG Memory** - For retrieval by optimizers and code generators

This enables:
- ✅ Quality tracking over time
- ✅ Pattern recognition (what works well)
- ✅ Optimizer feedback loops
- ✅ Similar code retrieval based on quality
- ✅ Automatic improvement suggestions

---

## Data Flow

```
┌──────────────────────────────────────────────────┐
│ 1. GENERATE CODE                                  │
│    chat_cli.py generates code using LLM          │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│ 2. RUN STATIC ANALYSIS                            │
│    StaticAnalysisTracker.analyze_file()          │
│    - Python Syntax Check                          │
│    - Main Function Check                          │
│    - JSON Output Check                            │
│    - Stdin Usage Check                            │
│    - Import Order Check (auto-fix)               │
│    - Node Runtime Import (auto-fix)              │
│    - call_tool() Usage Check                      │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│ 3. GENERATE QUALITY REPORT                        │
│    StaticAnalysisReport:                          │
│    - Overall Score: 0.87/1.00 (B+)               │
│    - Syntax Score: 1.0                            │
│    - Structure Score: 1.0                         │
│    - Import Score: 0.5 (auto-fixed!)             │
│    - Usage Score: 1.0                             │
│    - Validators Passed: 6/7                       │
│    - Auto-Fixes: 1                                │
└──────────────────────────────────────────────────┘
                    ↓
        ┌───────────┴────────────┐
        ↓                        ↓
┌──────────────────┐    ┌────────────────────┐
│ 4a. SAVE TO      │    │ 4b. SAVE TO RAG    │
│     REGISTRY     │    │     MEMORY         │
│                  │    │                    │
│ registry/        │    │ Artifact:          │
│   my_node/       │    │   Type: PATTERN    │
│   static_        │    │   Quality: 0.87    │
│   analysis.json  │    │   Tags:            │
│                  │    │   - static-analysis│
│ {                │    │   - code-quality   │
│   "overall_      │    │   - score-87       │
│    score": 0.87, │    │                    │
│   "passed": 6,   │    │ Searchable by:     │
│   "results": [   │    │   - Quality score  │
│     ...          │    │   - Tags           │
│   ]              │    │   - Similarity     │
│ }                │    │                    │
└──────────────────┘    └────────────────────┘
                                ↓
                    ┌───────────────────────┐
                    │ 5. OPTIMIZER QUERIES  │
                    │    RAG MEMORY         │
                    │                       │
                    │ "Find high-quality    │
                    │  code for task X"     │
                    │                       │
                    │ Returns:              │
                    │ - Code with score>0.8 │
                    │ - Similar patterns    │
                    │ - What worked before  │
                    └───────────────────────┘
```

---

## Integration with chat_cli.py

### Add Static Analysis After Code Generation

```python
# chat_cli.py

from src.static_analysis_tracker import StaticAnalysisTracker

class ChatCLI:
    def __init__(self, ...):
        # ... existing init ...
        self.static_tracker = StaticAnalysisTracker(
            tools_dir="code_evolver/tools/executable"
        )

    def generate_node_code(self, node_id: str, description: str, ...):
        """Generate code with static analysis tracking."""

        # ... existing code generation ...

        # Save generated code
        code_file = self.runner.save_code(node_id, code)

        # ═══════════════════════════════════════════════════
        # NEW: Run static analysis BEFORE testing
        # ═══════════════════════════════════════════════════
        console.print("\n[cyan]Running static analysis...[/cyan]")

        analysis_report = self.static_tracker.analyze_file(
            code_file=code_file,
            node_id=node_id,
            auto_fix=True  # Apply auto-fixes
        )

        # Display quality summary
        console.print(f"\n[bold]{analysis_report.get_quality_summary()}[/bold]")

        # Save to registry
        self.static_tracker.save_to_registry(
            analysis_report,
            registry_path="code_evolver/registry"
        )

        # Save to RAG
        self.static_tracker.save_to_rag(
            analysis_report,
            rag_memory=self.rag
        )

        # Check if we should escalate based on quality
        if analysis_report.overall_score < 0.5:
            console.print(
                f"[yellow]Low quality score ({analysis_report.overall_score:.2f}), "
                f"escalating to LLM for fixes...[/yellow]"
            )
            return self._escalate_for_quality_fixes(
                node_id,
                analysis_report
            )

        # ═══════════════════════════════════════════════════
        # Continue with existing workflow (tests, etc.)
        # ═══════════════════════════════════════════════════

        # ... run tests ...
        # ... evaluate ...
        # ... etc ...
```

---

## Registry Storage Format

### File: `registry/<node_id>/static_analysis.json`

```json
{
  "node_id": "write_a_poem_1763277877",
  "file_path": "nodes/write_a_poem_1763277877/main.py",
  "timestamp": 1699123456.789,
  "metrics": {
    "total_validators": 7,
    "passed_validators": 6,
    "failed_validators": 1,
    "auto_fixes_applied": 1,
    "syntax_score": 1.0,
    "structure_score": 1.0,
    "import_score": 0.5,
    "usage_score": 1.0,
    "overall_score": 0.87,
    "total_analysis_time_ms": 850.5
  },
  "results": [
    {
      "validator_name": "Python Syntax",
      "passed": true,
      "exit_code": 0,
      "output": "OK: Valid Python syntax",
      "execution_time_ms": 45.2,
      "auto_fixed": false,
      "fix_applied": ""
    },
    {
      "validator_name": "Node Runtime Import",
      "passed": true,
      "exit_code": 0,
      "output": "FIXED: Moved node_runtime import from line 2 to after line 6",
      "execution_time_ms": 98.7,
      "auto_fixed": true,
      "fix_applied": "Moved node_runtime import from line 2 to after line 6"
    },
    {
      "validator_name": "Undefined Names",
      "passed": false,
      "exit_code": 1,
      "output": "main.py:15:5: F821 undefined name 'json'",
      "execution_time_ms": 285.3,
      "auto_fixed": false,
      "fix_applied": ""
    }
  ]
}
```

---

## RAG Memory Storage

### Artifact Type: PATTERN

```python
# Stored in RAG
{
  'artifact_id': 'write_a_poem_1763277877_static_analysis',
  'artifact_type': ArtifactType.PATTERN,
  'name': 'Static Analysis: write_a_poem_1763277877',
  'description': 'Code quality: 0.87 (6/7 checks passed)',
  'content': '<full JSON report>',
  'tags': [
    'static-analysis',
    'code-quality',
    'score-87',  # Score bucket (0-100)
    'fixes-1'    # Number of auto-fixes applied
  ],
  'metadata': {
    'overall_score': 0.87,
    'syntax_score': 1.0,
    'structure_score': 1.0,
    'import_score': 0.5,
    'usage_score': 1.0,
    'validators_passed': 6,
    'validators_total': 7,
    'auto_fixes_applied': 1,
    'analysis_time_ms': 850.5
  },
  'quality_score': 0.87  # Used for RAG ranking
}
```

---

## Optimizer Usage

### 1. Find High-Quality Code Examples

```python
# In auto_evolver.py or optimizer

def get_high_quality_examples(task_description: str, min_score: float = 0.8):
    """Find similar high-quality code for a task."""

    # Search RAG for similar tasks with high quality
    results = rag.find_similar(
        query=task_description,
        artifact_type=ArtifactType.PATTERN,
        top_k=5,
        filters={'tags': ['static-analysis']}
    )

    # Filter by quality score
    high_quality = [
        (artifact, similarity)
        for artifact, similarity in results
        if artifact.metadata.get('overall_score', 0) >= min_score
    ]

    return high_quality
```

**Usage:**
```python
# When generating new code
task = "write a joke"

# Find what worked well before
examples = get_high_quality_examples(task, min_score=0.9)

if examples:
    best_example, similarity = examples[0]
    print(f"Found high-quality example (score: {best_example.quality_score})")
    print(f"Similarity: {similarity:.2f}")

    # Use as reference for new generation
    prompt = f"""
    Generate code for: {task}

    Reference this high-quality example (quality score: {best_example.quality_score}):
    {best_example.content}

    Follow the same patterns and structure.
    """
```

---

### 2. Identify Common Failure Patterns

```python
def analyze_common_failures(rag_memory):
    """Find which validators commonly fail."""

    # Get all static analysis artifacts
    all_analyses = rag.find_by_tags(['static-analysis'], limit=100)

    # Count failures by validator
    failure_counts = {}

    for artifact, _ in all_analyses:
        report = json.loads(artifact.content)

        for result in report['results']:
            if not result['passed']:
                validator = result['validator_name']
                failure_counts[validator] = failure_counts.get(validator, 0) + 1

    # Sort by most common failures
    sorted_failures = sorted(
        failure_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return sorted_failures
```

**Output:**
```
Common Validator Failures (last 100 generations):
  1. Undefined Names:           45/100 (45%)  ← Most common!
  2. Node Runtime Import:        28/100 (28%)  (auto-fixed)
  3. JSON Output:                12/100 (12%)
  4. call_tool() Usage:           8/100 (8%)
  5. Main Function:               5/100 (5%)
```

**Optimizer Action:**
```python
# Based on analysis, add better prompts for common failures

if 'Undefined Names' failures > 40%:
    # Add to code generation prompt:
    code_prompt += """
    CRITICAL: Ensure ALL imports are included:
    - import json (if using json.dumps or json.load)
    - import sys (if using sys.stdin, sys.stdout)
    - from pathlib import Path (if using Path)
    - from node_runtime import call_tool (if using call_tool)
    """
```

---

### 3. Track Quality Over Time

```python
def track_quality_trend(rag_memory, last_n: int = 50):
    """Track code quality trend over time."""

    # Get recent analyses sorted by timestamp
    analyses = rag.find_by_tags(['static-analysis'], limit=last_n)

    # Sort by timestamp
    sorted_analyses = sorted(
        analyses,
        key=lambda x: json.loads(x[0].content)['timestamp']
    )

    # Extract scores
    scores = [
        json.loads(artifact.content)['metrics']['overall_score']
        for artifact, _ in sorted_analyses
    ]

    # Calculate trend
    avg_score = sum(scores) / len(scores)
    recent_avg = sum(scores[-10:]) / 10  # Last 10

    print(f"Average quality (last {last_n}): {avg_score:.2f}")
    print(f"Recent quality (last 10): {recent_avg:.2f}")

    if recent_avg > avg_score:
        print("✓ Quality improving!")
    else:
        print("✗ Quality declining - review prompts")

    return scores
```

**Visualization:**
```
Quality Trend (Last 50 Generations):
  Overall Average: 0.75
  Recent Average:  0.82  ✓ Improving!

  Score Distribution:
  0.9-1.0:  ████████████████████████  24 (48%)
  0.8-0.9:  ████████████              12 (24%)
  0.7-0.8:  ██████                     6 (12%)
  0.6-0.7:  ████                       4 (8%)
  0.0-0.6:  ████                       4 (8%)
```

---

### 4. Auto-Fix Impact Analysis

```python
def analyze_autofix_impact(rag_memory):
    """Measure impact of auto-fixes on quality."""

    analyses = rag.find_by_tags(['static-analysis'], limit=100)

    with_fixes = []
    without_fixes = []

    for artifact, _ in analyses:
        report = json.loads(artifact.content)
        score = report['metrics']['overall_score']
        fixes = report['metrics']['auto_fixes_applied']

        if fixes > 0:
            with_fixes.append(score)
        else:
            without_fixes.append(score)

    avg_with = sum(with_fixes) / len(with_fixes)
    avg_without = sum(without_fixes) / len(without_fixes)

    print(f"Average score WITH auto-fixes:    {avg_with:.2f}")
    print(f"Average score WITHOUT auto-fixes: {avg_without:.2f}")
    print(f"Impact: {(avg_with - avg_without):.2f} improvement")
```

**Output:**
```
Auto-Fix Impact Analysis:
  Average score WITH auto-fixes:    0.85
  Average score WITHOUT auto-fixes: 0.72
  Impact: +0.13 improvement

  Most Valuable Auto-Fixes:
  1. Import Order Fix:        +0.08 avg improvement
  2. Node Runtime Import Fix: +0.05 avg improvement
```

---

## Dashboard Integration

### Quality Metrics Dashboard

```python
def generate_quality_dashboard(rag_memory):
    """Generate quality metrics dashboard."""

    analyses = rag.find_by_tags(['static-analysis'], limit=100)

    # Calculate metrics
    total = len(analyses)
    scores = [
        json.loads(a[0].content)['metrics']['overall_score']
        for a in analyses
    ]

    avg_score = sum(scores) / total
    high_quality = sum(1 for s in scores if s >= 0.9)
    medium_quality = sum(1 for s in scores if 0.7 <= s < 0.9)
    low_quality = sum(1 for s in scores if s < 0.7)

    print(f"""
╔════════════════════════════════════════════════╗
║         CODE QUALITY DASHBOARD                 ║
╠════════════════════════════════════════════════╣
║ Total Analyses:  {total:3d}                           ║
║ Average Score:   {avg_score:.2f}                          ║
║                                                ║
║ Quality Distribution:                          ║
║   A+ (0.9-1.0):  {high_quality:3d} ({high_quality/total*100:5.1f}%)                  ║
║   B  (0.7-0.9):  {medium_quality:3d} ({medium_quality/total*100:5.1f}%)                  ║
║   C  (0.0-0.7):  {low_quality:3d} ({low_quality/total*100:5.1f}%)                  ║
╚════════════════════════════════════════════════╝
    """)
```

---

## Benefits

### 1. **Pattern Recognition** 🎯
- Find what code patterns work best
- Identify successful structures
- Reuse proven approaches

### 2. **Continuous Improvement** 📈
- Track quality over time
- Measure auto-fix impact
- Identify degradation early

### 3. **Smart Code Generation** 🧠
- Use high-quality examples
- Avoid known failure patterns
- Learn from past mistakes

### 4. **Cost Optimization** 💰
- Fewer LLM escalations
- Better first-time success rate
- Reduced iteration cycles

### 5. **Developer Insights** 📊
- Understand common issues
- Validate improvements
- Data-driven decisions

---

## Example: Complete Flow

```python
# 1. Generate code
code = generate_code_with_llm(task="write a poem")

# 2. Run static analysis
report = static_tracker.analyze_file(code_file, node_id, auto_fix=True)

# 3. Save to registry
static_tracker.save_to_registry(report, registry_path="registry")

# 4. Save to RAG
static_tracker.save_to_rag(report, rag_memory=rag)

# 5. Use in next generation
similar_tasks = rag.find_similar(
    "write a poem",
    filters={'tags': ['static-analysis', 'score-90']}  # High quality only
)

if similar_tasks:
    best_example = similar_tasks[0][0]
    print(f"Using high-quality example (score: {best_example.quality_score})")
    # Use in prompt for better generation
```

---

## Summary

✅ **Static analysis results tracked** in registry + RAG
✅ **Quality metrics** available for optimizers
✅ **Pattern recognition** enables better code generation
✅ **Trend analysis** shows improvements over time
✅ **Auto-fix impact** measurable
✅ **Data-driven optimization** possible

**Files Created:**
- `src/static_analysis_tracker.py` - Main tracking system
- Registry integration for node-specific storage
- RAG integration for retrieval and optimization

**Next Steps:**
1. Integrate into chat_cli.py workflow
2. Create quality dashboard
3. Build optimizer feedback loops
4. Track metrics over time
5. Use for prompt optimization

---

**Status:** ✅ Static analysis tracking system complete and ready for integration!
