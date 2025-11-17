# Debug Store: Fast Request/Response Recording System

A high-performance hybrid data store for recording, analyzing, and optimizing debug data from AI workflows, tools, and code execution.

## 🎯 Overview

The Debug Store system provides:

- **Ultra-fast writes** via LMDB (Lightning Memory-Mapped Database)
- **Powerful analytics** via DuckDB (embedded analytical database)
- **Automatic sync** between write and analytics layers
- **Code variant tracking** for comparing different implementations
- **Performance telemetry** (OpenTelemetry-compatible)
- **LLM-optimized output** for feeding analysis to code models
- **Zero service dependencies** - just install and use

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
│  (Workflows, Tools, Functions, Steps)                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Debug Integration Layer                     │
│  • Decorators (@debug_track)                                │
│  • Context Managers (DebugContext, WorkflowDebugContext)   │
│  • WorkflowTracker Integration                             │
└─────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    ▼               ▼
        ┌───────────────┐   ┌──────────────┐
        │  LMDB Layer   │   │ DuckDB Layer │
        │  (Fast Write) │──▶│  (Analytics) │
        └───────────────┘   └──────────────┘
             │ Write              │ Query
             │ <10μs              │ <1ms
             ▼                    ▼
        [.lmdb file]        [.duckdb file]
```

### Components

1. **DebugStore** (`debug_store.py`)
   - Hybrid LMDB + DuckDB storage
   - Background sync thread
   - Performance metrics tracking
   - Hierarchical context support

2. **DebugAnalyzer** (`debug_analyzer.py`)
   - Code variant comparison
   - Performance analysis
   - Error pattern detection
   - LLM-optimized output generation
   - Token budget management

3. **DebugIntegration** (`debug_integration.py`)
   - WorkflowTracker integration
   - Decorator-based tracking
   - Context managers
   - Automatic code snapshot capture

## 🚀 Quick Start

### Installation

```bash
cd code_evolver
pip install -r requirements_debug_store.txt
```

### Basic Usage

```python
from debug_store import DebugStore

# Create a debug store for your session
with DebugStore(session_id="my_workflow_run") as store:
    # Record an operation
    store.write_record(
        context_type="tool",
        context_id="data_processor",
        context_name="Data Processor",
        request_data={"input": "hello"},
        response_data={"output": "HELLO"},
        duration_ms=45.2,
        memory_mb=5.3,
        status="success"
    )

    # Sync to analytics layer
    store.sync_to_duckdb()

    # Query performance
    summary = store.get_performance_summary()
    print(summary)
```

### Using Decorators

```python
from debug_integration import init_debug_integration, debug_track

# Initialize once
init_debug_integration("my_session")

# Track any function automatically
@debug_track(context_type="tool")
def process_data(input_data):
    # Your code here
    return processed_data

# Calls are automatically tracked!
result = process_data({"key": "value"})
```

### Workflow Integration

```python
from debug_integration import DebugIntegration
from workflow_tracker import WorkflowTracker, WorkflowStep

integration = DebugIntegration(session_id="pipeline_run")

# Create workflow
tracker = WorkflowTracker("data_pipeline", "Process data")

# Track entire workflow
with integration.track_workflow(tracker):
    step = WorkflowStep("step_1", "fetch", "Fetch data")

    with integration.track_step(step):
        step.start()
        # Do work...
        step.complete("Success")

integration.close()
```

## 📊 Analysis & LLM Export

### Generate Analysis Report

```python
from debug_analyzer import DebugAnalyzer

analyzer = DebugAnalyzer(store)

# Analyze a specific context
package = analyzer.analyze_context(
    context_type="tool",
    context_id="my_tool",
    include_variants=True,
    max_samples=10
)

# Export for LLM consumption (markdown format)
markdown = package.to_markdown(max_tokens=50000)

# Or save to file
analyzer.export_to_file(
    package,
    "analysis.md",
    format="markdown",
    max_tokens=50000
)
```

### Example Output Structure

The analysis package includes:

```markdown
# Debug Analysis: Tool Name

## Summary
Total Executions: 150
Success Rate: 94.7% (142/150)
Average Duration: 123.45ms
P95 Duration: 234.56ms

## Code Variants
### Variant 1: Original Implementation
- Executions: 100
- Success Rate: 100%
- Avg Duration: 150.23ms

**Code:**
```python
def process(data):
    return data.upper()
```

### Variant 2: Optimized Implementation
- Executions: 50
- Success Rate: 90%
- Avg Duration: 80.12ms

**Code:**
```python
def process(data):
    return data.upper() if data else ""
```

## Performance Comparison
{detailed metrics}

## Error Analysis
{error patterns and recommendations}

## Recommendations
- ✅ Variant 2 is 46% faster than Variant 1
- ⚠️ Moderate error rate (10%) - add null checks
```

## 🔍 Key Features

### 1. Fast Writes (LMDB)

- **Sub-millisecond writes** (~10-100μs)
- **Zero-copy reads** via memory mapping
- **ACID transactions** without write-ahead log
- **Crash-proof** design
- **10GB+ capacity** per session

### 2. Powerful Analytics (DuckDB)

- **SQL queries** for complex analysis
- **Columnar storage** for fast aggregations
- **Vectorized execution** engine
- **Embedded** - no server needed
- **Pandas integration** for data science workflows

### 3. Code Variant Tracking

Track multiple implementations of the same function:

```python
# Variant 1
store.write_record(
    ...,
    code_snapshot=code_v1,
    variant_id="variant_1"
)

# Variant 2
store.write_record(
    ...,
    code_snapshot=code_v2,
    variant_id="variant_2"
)

# Compare performance
analyzer.analyze_context(..., include_variants=True)
```

### 4. Performance Telemetry

OpenTelemetry-compatible metrics:

- Duration (ms)
- Memory usage (MB)
- CPU utilization (%)
- Custom metadata
- Hierarchical tracing (parent/child contexts)

### 5. LLM Optimization

- **Token counting** via tiktoken
- **Smart truncation** to fit context windows
- **Structured output** (markdown/JSON)
- **Representative sampling** (fast/slow/error/median)
- **Code + metrics + recommendations** in one package

## 📁 File Organization

Each debug session creates:

```
debug_data/
├── session_id.lmdb/          # LMDB database directory
│   ├── data.mdb              # Main data file
│   └── lock.mdb              # Lock file
└── session_id.duckdb         # DuckDB database file
```

**Recommended patterns:**

```python
# One file per workflow run
session_id = f"workflow_{workflow_id}_{timestamp}"

# One file per tool execution
session_id = f"tool_{tool_name}_{timestamp}"

# One file per debug session
session_id = f"debug_{code_hash}_{timestamp}"
```

## 🎯 Use Cases

### 1. Auto-Debug Recording

Record all request/response data during debug mode:

```python
if DEBUG_MODE:
    integration = DebugIntegration(f"debug_{workflow_id}")

    @integration.track_function()
    def problematic_function():
        # Code being debugged
        pass
```

### 2. Performance Optimization

Find slow operations:

```python
analyzer = DebugAnalyzer(store)
candidates = analyzer.get_optimization_candidates(
    min_executions=10,
    min_duration_ms=500
)

for candidate in candidates:
    print(f"{candidate['context_name']}: {candidate['avg_duration_ms']}ms")
```

### 3. Code Evolution Tracking

Compare before/after changes:

```python
# Before optimization
store.write_record(..., variant_id="before", code_snapshot=old_code)

# After optimization
store.write_record(..., variant_id="after", code_snapshot=new_code)

# Compare
package = analyzer.analyze_context(..., include_variants=True)
# Shows performance difference between variants
```

### 4. Error Pattern Analysis

Identify common failures:

```python
package = analyzer.analyze_context(context_type="tool", context_id="flaky_api")

for error_type, count in package.error_analysis['common_errors']:
    print(f"{error_type}: {count} occurrences")
```

### 5. LLM-Assisted Optimization

Export analysis for higher-level code models:

```python
# Generate comprehensive analysis
package = analyzer.analyze_context(...)

# Export optimized for LLM consumption
markdown = package.to_markdown(max_tokens=100000)

# Feed to code model for optimization suggestions
llm_response = code_model.generate(
    prompt=f"Analyze this debug data and suggest optimizations:\n\n{markdown}"
)
```

## ⚙️ Configuration

### Store Options

```python
DebugStore(
    session_id="my_session",
    base_path="debug_data",           # Storage directory
    auto_sync_interval=30,             # Sync every 30 seconds
    enable_auto_sync=True              # Background sync thread
)
```

### Integration Options

```python
DebugIntegration(
    session_id="my_session",
    base_path="debug_data",
    auto_sync_interval=30,
    enable_code_snapshots=True         # Capture source code
)
```

### Analysis Options

```python
analyzer.analyze_context(
    context_type="tool",
    context_id="my_tool",
    include_variants=True,             # Include code variant analysis
    max_samples=10,                    # Representative samples
    error_sample_limit=5               # Errors per variant
)
```

## 📈 Performance Characteristics

### Write Performance (LMDB)

- **Throughput**: 100K+ writes/sec
- **Latency**: 10-100μs per write
- **Concurrency**: Multiple threads supported
- **Overhead**: ~1KB per record (with msgpack compression)

### Query Performance (DuckDB)

- **Simple queries**: <1ms
- **Aggregations**: 1-10ms for 100K records
- **Full table scan**: 10-50ms for 1M records
- **Index lookups**: <1ms

### Sync Performance

- **Batch size**: 1000 records (configurable)
- **Sync time**: ~10ms per 1000 records
- **Background sync**: Minimal impact on writes

## 🧪 Testing

Run the test suite:

```bash
cd code_evolver
pytest tests/test_debug_store.py -v
pytest tests/test_debug_analyzer.py -v
```

Run examples:

```bash
python examples/debug_store_example.py
```

## 🔧 Advanced Usage

### Custom Queries

```python
# Complex analytics query
results = store.query_analytics("""
    SELECT
        context_name,
        AVG(duration_ms) as avg_duration,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95,
        COUNT(*) as executions,
        SUM(CASE WHEN status='error' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as error_rate
    FROM records
    WHERE context_type = 'tool'
    GROUP BY context_name
    HAVING executions > 10
    ORDER BY avg_duration DESC
""").fetchdf()
```

### Cross-Session Analysis

```python
# Compare multiple sessions
stores = [
    DebugStore("session_1", enable_auto_sync=False),
    DebugStore("session_2", enable_auto_sync=False),
    DebugStore("session_3", enable_auto_sync=False)
]

analyzer = DebugAnalyzer(stores[0])
comparison = analyzer.compare_sessions(
    stores,
    context_type="workflow",
    context_id="my_workflow"
)
```

### Memory Management

```python
# Manual sync control
store = DebugStore("my_session", enable_auto_sync=False)

# Write many records...
for i in range(10000):
    store.write_record(...)

    # Sync periodically to free LMDB memory
    if i % 1000 == 0:
        store.sync_to_duckdb()

store.close()
```

## 🤝 Integration Points

### Existing Code Evolver Components

The debug store integrates with:

1. **WorkflowTracker** - Automatic workflow recording
2. **Auto Evolver** - Track evolution metrics
3. **Node Runner** - Record execution data
4. **RAG Memory** - Store debug artifacts
5. **Pressure Manager** - Conditional recording based on system load

Example integration:

```python
# In orchestrator.py or similar
from debug_integration import DebugIntegration

integration = DebugIntegration(session_id=f"run_{run_id}")

# Wrap workflow execution
with integration.track_workflow(workflow_tracker):
    # Existing workflow code
    result = execute_workflow(...)

# Analyze after execution
if result.has_errors:
    package = integration.analyze("workflow", workflow_id)
    send_to_auto_evolver(package)
```

## 📝 Schema Reference

### Records Table (DuckDB)

```sql
CREATE TABLE records (
    id VARCHAR PRIMARY KEY,           -- Unique record ID
    timestamp TIMESTAMP,              -- When recorded
    context_type VARCHAR,             -- 'tool', 'workflow', 'step', 'node'
    context_id VARCHAR,               -- Specific identifier
    context_name VARCHAR,             -- Human-readable name
    parent_context VARCHAR,           -- Parent ID (for hierarchy)
    request_data JSON,                -- Input data
    response_data JSON,               -- Output data
    metadata JSON,                    -- Additional metadata
    duration_ms DOUBLE,               -- Execution time
    memory_mb DOUBLE,                 -- Memory usage
    cpu_percent DOUBLE,               -- CPU usage
    status VARCHAR,                   -- 'success', 'error', 'timeout'
    error TEXT,                       -- Error message if failed
    code_snapshot TEXT,               -- Source code
    code_hash VARCHAR,                -- Code hash for dedup
    variant_id VARCHAR                -- Code variant identifier
);
```

## 🛠️ Troubleshooting

### Large Database Files

If database files grow too large:

```python
# Archive old sessions
import shutil
shutil.move("debug_data/old_session.lmdb", "archive/")
shutil.move("debug_data/old_session.duckdb", "archive/")

# Or query and export just what you need
analyzer.export_to_file(package, "summary.md")
# Then delete full database
```

### Sync Issues

If background sync is causing issues:

```python
# Disable auto-sync
store = DebugStore("session", enable_auto_sync=False)

# Manual sync when needed
store.sync_to_duckdb()
```

### Memory Usage

LMDB is memory-mapped but won't necessarily use all RAM:

```python
# Check actual usage
stats = store.get_stats()
print(f"LMDB size: {stats['lmdb_size_mb']} MB")
print(f"DuckDB size: {stats['duckdb_size_mb']} MB")
```

## 📚 API Reference

See source code documentation in:
- `src/debug_store.py` - Core storage
- `src/debug_analyzer.py` - Analysis tools
- `src/debug_integration.py` - Integration helpers

## 🎓 Best Practices

1. **Use meaningful session IDs** - Include workflow/tool name and timestamp
2. **Enable auto-sync** for long-running processes
3. **Disable auto-sync** for batch operations, sync manually
4. **Capture code snapshots** for variant comparison
5. **Use hierarchical contexts** (parent_context) for workflows
6. **Export to markdown** for LLM consumption
7. **Archive old sessions** to manage disk space
8. **Use representative sampling** to reduce token usage

## 📄 License

Part of the Code Evolver project.

## 🤔 FAQ

**Q: How does this compare to logging?**
A: Debug store captures structured request/response data with performance metrics, enabling analytics. Logging is text-based and harder to analyze programmatically.

**Q: Can I use this in production?**
A: Yes, but consider using conditional recording based on sampling rate or error conditions to minimize overhead.

**Q: How much overhead does tracking add?**
A: LMDB writes are ~10-100μs. Total overhead typically <1% for operations >10ms.

**Q: Can I query across multiple sessions?**
A: Yes, use `compare_sessions()` or open multiple DuckDB files and union the results.

**Q: What's the max database size?**
A: LMDB supports up to 10GB by default (configurable). DuckDB handles terabytes.

**Q: How do I share analysis with others?**
A: Export to markdown or JSON and share the file. Or share the .duckdb file directly (it's portable).

## 🚦 Next Steps

1. **Install dependencies**: `pip install -r requirements_debug_store.txt`
2. **Run examples**: `python examples/debug_store_example.py`
3. **Run tests**: `pytest tests/test_debug_store.py -v`
4. **Integrate with your code**: Add decorators or context managers
5. **Analyze your data**: Use DebugAnalyzer to generate reports
6. **Feed to LLM**: Export markdown and use for optimization

---

**Happy Debugging! 🐛🔍**
