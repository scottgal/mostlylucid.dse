# Tool Evolution & Optimization Flow

## Overview

This document describes the **strengthened** tool evolution and replace flow, implementing a **namespace-based semantic cluster** system where calling `call_tool(toolname)` automatically selects the **BEST/FITTEST** version available (original or evolved).

## Core Concept: Semantic Namespaces

A tool name (e.g., `translate_text`, `code_generator`) represents a **semantic namespace** or **capability cluster**, not a specific implementation. When you call a tool by name, the system uses:

1. **Promotion Files** (`.tool_promotions.json`) to track evolved versions
2. **RAG Semantic Search** to find similar tools in the semantic cluster
3. **Quality Scores** and **Failure History** to rank candidates by fitness
4. **Automatic Selection** of the best/fittest tool

This ensures **continuous optimization** where better versions automatically replace older ones.

---

## Architecture

### 1. Tool Evolution Process

When a tool fails, the system:

```
Tool Fails
    ↓
evolve_tool()
    ↓
Generate New Version (e.g., v1.1)
    ↓
Create Versioned File (tool_v1_1.py)
    ↓
Update .tool_promotions.json
    ↓
Store Evolution in RAG
    ↓
Record in Cumulative Changelog
```

**File**: `code_evolver/tools/executable/evolve_tool.py`

**Key Features**:
- Creates versioned files: `tool_id_v1_1.py`, `tool_id_v1_2.py`, etc.
- Stores promotion metadata in `.tool_promotions.json`
- Includes evolution reason, mutation hint, and timestamp
- Stores evolution patterns in RAG for learning

---

### 2. Tool Selection Flow (Strengthened)

When `call_tool(toolname)` is called:

```
call_tool("translator")
    ↓
tools_manager.get_tool("translator")
    ↓
Check .tool_promotions.json
    ↓
Evolved Version Found?
    ├─ YES → Load Evolved Tool (v1.1)
    └─ NO → Load Original Tool (v1.0)
    ↓
invoke_executable_tool()
    ↓
Check for evolved_file in implementation
    ↓
Execute Evolved File or Original
```

**File**: `code_evolver/src/tools_manager.py:1774-1920`

**Key Methods**:

#### `get_tool(tool_id, use_evolved=True)`
- **Default behavior**: Automatically checks for evolved versions
- **Transparent upgrade**: Returns evolved tool if available, otherwise original
- **Namespace-based**: The tool_id represents the semantic namespace

#### `_get_evolved_tool(tool_id)`
- Reads `.tool_promotions.json`
- Loads evolved tool metadata
- Creates Tool object with evolved version info
- Maintains same tool_id (namespace) but updated version

#### Example:
```python
# Call a tool by namespace
tool = tools_manager.get_tool("code_generator")

# If code_generator evolved to v1.2, this returns the v1.2 version
# If not evolved, returns original v1.0
# Completely transparent to the caller!
```

---

### 3. RAG-Based Best Tool Selection

For advanced scenarios, use **RAG semantic search** to find the best tool in a namespace:

```
get_best_tool_in_namespace("translator", scenario="translate Python code comments")
    ↓
Collect Candidates:
    - Evolved version (if exists) → score = 1.0
    - Original version → score = 0.9
    - RAG semantic matches → score = similarity × quality × 0.8
    ↓
Rank by Fitness:
    - Multiply by quality_score
    - Demote based on failure history
    ↓
Return Best Tool
```

**File**: `code_evolver/src/tools_manager.py:1774-1875`

**Key Method**: `get_best_tool_in_namespace(tool_id, scenario, use_rag=True)`

**Features**:
1. **Multi-candidate search**:
   - Evolved versions (highest priority)
   - Original tool (baseline)
   - RAG semantic matches (semantic cluster)

2. **Fitness Scoring**:
   ```python
   final_score = base_score × quality_score × failure_demotion
   ```
   - base_score: 1.0 (evolved) → 0.9 (original) → 0.8×similarity (RAG match)
   - quality_score: Dynamic score updated by `mark_tool_failure`
   - failure_demotion: 0.7× per high-similarity failure (>0.7)

3. **Failure-Aware Ranking**:
   - Queries RAG for similar past failures
   - Demotes tools with high failure similarity
   - Prevents repeated mistakes

**Example**:
```python
# Find best tool for specific scenario
best_tool = tools_manager.get_best_tool_in_namespace(
    tool_id="translator",
    scenario="translate technical documentation from English to Spanish with code preservation"
)

# Returns the fittest tool considering:
# - Is there an evolved version? (highest priority)
# - Are there similar tools with better track records? (RAG search)
# - Has this tool failed on similar scenarios? (failure history)
```

---

### 4. Evolved Tool Execution

When an evolved tool is executed:

```
invoke_executable_tool(tool_id="my_tool", ...)
    ↓
Check tool.implementation["evolved_file"]
    ↓
Evolved File Found?
    ├─ YES → Replace args with evolved file path
    └─ NO → Use original tool path
    ↓
Execute Command with Correct File
```

**File**: `code_evolver/src/tools_manager.py:1382-1391`

**Logic**:
1. Check if `tool.implementation` contains `evolved_file`
2. If yes, update `args_template` to use evolved file
3. Add `{evolved_file}` as a substitution variable
4. Execute with the evolved implementation

**Example**:
```python
# Original tool: python {tool_dir}/translator.py
# Evolved tool: python tools/executable/translator_v1_1.py

# The system automatically uses the evolved file
# Completely transparent!
```

---

## Data Structures

### .tool_promotions.json

```json
{
  "code_generator": {
    "evolved_version": "1.1.0",
    "evolved_file": "tools/executable/code_generator_v1_1.py",
    "original_version": "1.0.0",
    "reason": "Evolved to fix: timeout on large files",
    "mutation": "add streaming output for large code generation",
    "promoted_at": "2024-01-15T10:30:45Z"
  },
  "translator": {
    "evolved_version": "1.2.0",
    "evolved_file": "tools/executable/translator_v1_2.py",
    "original_version": "1.1.0",
    "reason": "Evolved to fix: incorrect handling of code blocks",
    "mutation": "preserve code formatting in translations",
    "promoted_at": "2024-01-16T14:22:10Z"
  }
}
```

**Location**: Workflow root directory (`.tool_promotions.json`)

**Purpose**:
- Maps tool namespace to evolved versions
- Tracks evolution metadata
- Enables automatic version selection

---

## Usage Examples

### Example 1: Transparent Evolution (Default)

```python
from node_runtime import call_tool

# Call tool by namespace - automatically uses best version
result = call_tool(
    "code_generator",
    "Generate a Python function for prime number checking"
)

# If code_generator evolved to v1.1, uses v1.1
# If not evolved, uses v1.0
# Caller doesn't need to know!
```

### Example 2: Explicit RAG-Based Selection

```python
from src.tools_manager import ToolsManager
from src.config_manager import ConfigManager

config = ConfigManager()
tools = ToolsManager(config)

# Get best tool in namespace for specific scenario
best_tool = tools.get_best_tool_in_namespace(
    tool_id="translator",
    scenario="translate API documentation with code examples",
    use_rag=True
)

# Returns fittest tool based on:
# - Evolved versions
# - RAG semantic matches
# - Quality scores
# - Failure history
```

### Example 3: Disable Evolution (Testing)

```python
# Get original version without evolution
original_tool = tools.get_tool(
    tool_id="code_generator",
    use_evolved=False  # Skip promotion checking
)

# Useful for:
# - Testing evolved vs original
# - Debugging
# - Baseline comparisons
```

---

## Quality Score & Failure Tracking

### Failure Recording

**File**: `code_evolver/tools/executable/mark_tool_failure.py`

When a tool fails:

```python
call_tool("mark_tool_failure", json.dumps({
    "tool_id": "translator",
    "scenario": "translate with code preservation",
    "error_message": "IndexError: list index out of range",
    "severity": "high"  # low | medium | high
}))
```

**Effects**:
1. **Quality Score Demotion**:
   - `low`: -0.01
   - `medium`: -0.05
   - `high`: -0.10
   - Additional -0.05 if >5 failures
   - Additional -0.10 if >10 failures

2. **Failure Pattern Storage**:
   - Stores in RAG with tags: `["tool_failure", tool_id, "severity_high"]`
   - Enables semantic matching for similar failures
   - Used by `resilient_tool_call` and `get_best_tool_in_namespace`

3. **Tag Refinement**:
   - Adds negative tags: `["not-for-translation", "not-for-code-blocks"]`
   - Narrows tool's applicable use cases

### Quality Score Evolution

```
Initial Quality Score: 1.0
    ↓
Failure 1 (high): 1.0 - 0.10 = 0.90
    ↓
Failure 2 (medium): 0.90 - 0.05 = 0.85
    ↓
Failure 3 (high): 0.85 - 0.10 = 0.75
    ↓
... (6th failure) ...
    ↓
Additional Demotion: -0.05 (>5 failures)
    ↓
Final Score: 0.65
```

**Impact on Selection**:
- Tool with quality_score=0.65 ranked lower than quality_score=1.0
- Evolved tools inherit original quality_score
- Forces evolution when quality drops too low

---

## Resilient Tool Call Integration

**File**: `code_evolver/tools/executable/resilient_tool_call.py`

The resilient call system automatically handles failures:

```
resilient_tool_call(scenario="translate code comments")
    ↓
find_tools_for_scenario(scenario)
    ↓
RAG Search → Rank by Quality × Similarity
    ↓
Try Best Candidate
    ↓
Success? → Return Result
    ↓
Failure? → Mark Failure → Try Next Candidate
    ↓
All Failed? → Call evolve_tool() → Retry
```

**Key Features**:
1. **Automatic Fallback**: Tries multiple tools until one succeeds
2. **Failure-Based Demotion**: Ranks tools lower if they have similar past failures
3. **Evolution Trigger**: Evolves tools if all candidates fail
4. **Learning Loop**: Each failure improves future selections

**Example**:
```python
from node_runtime import call_tool_resilient

result = call_tool_resilient(
    scenario="generate unit tests for Python function",
    input_data={"code": python_code},
    tags=["code", "generator", "testing"],
    max_attempts=5  # Try up to 5 tools
)

# Automatically:
# - Finds best tools via RAG
# - Tries them in ranked order
# - Marks failures
# - Evolves if needed
# - Returns best result
```

---

## Benefits of Strengthened Flow

### 1. **Transparent Optimization**
- Caller uses tool by namespace: `call_tool("translator")`
- System automatically uses best version
- No code changes needed when tools evolve

### 2. **Continuous Learning**
- Every failure improves future selections
- RAG stores evolution patterns
- Quality scores adapt dynamically

### 3. **Semantic Clustering**
- Tools grouped by capability (namespace)
- RAG finds similar tools
- Enables cross-pollination of solutions

### 4. **Failure Resilience**
- Automatic fallback to alternatives
- Failure history prevents repeated mistakes
- Evolution triggered when needed

### 5. **Fitness-Based Selection**
- Multiple ranking factors:
  - Evolution status (preferred)
  - Quality score
  - Failure history
  - Semantic similarity
- Always uses fittest tool

---

## Testing the Flow

### Test 1: Evolution Detection

```bash
# Create a promotion file
cat > .tool_promotions.json << EOF
{
  "test_tool": {
    "evolved_version": "1.1.0",
    "evolved_file": "tools/executable/test_tool_v1_1.py",
    "original_version": "1.0.0",
    "reason": "Evolved to fix timeout",
    "mutation": "add caching",
    "promoted_at": "2024-01-15T10:00:00Z"
  }
}
EOF

# Test tool selection
python -c "
from src.tools_manager import ToolsManager
from src.config_manager import ConfigManager

config = ConfigManager()
tools = ToolsManager(config, None, None)

# Should return evolved version
tool = tools.get_tool('test_tool')
print(f'Version: {tool.version}')  # Should print 1.1.0
print(f'Is Evolved: {tool.metadata.get(\"is_evolved\")}')  # Should print True
"
```

### Test 2: RAG-Based Selection

```bash
python -c "
from src.tools_manager import ToolsManager
from src.config_manager import ConfigManager
from src.ollama_client import OllamaClient
from src.rag_memory import RAGMemory

config = ConfigManager()
client = OllamaClient(config_manager=config)
rag = RAGMemory(ollama_client=client)
tools = ToolsManager(config, client, rag)

# Test best tool in namespace
best_tool = tools.get_best_tool_in_namespace(
    tool_id='code_generator',
    scenario='generate Python unit tests with pytest',
    use_rag=True
)

print(f'Best Tool: {best_tool.tool_id} v{best_tool.version}')
print(f'Quality Score: {best_tool.quality_score}')
"
```

### Test 3: Evolved File Execution

```bash
# Test that evolved file is actually used
python -c "
from src.tools_manager import ToolsManager
from src.config_manager import ConfigManager

config = ConfigManager()
tools = ToolsManager(config, None, None)

# Get evolved tool
tool = tools.get_tool('test_tool')

# Check implementation
print(f'Evolved File: {tool.implementation.get(\"evolved_file\")}')

# Execute (if executable type)
if tool.tool_type.value == 'executable':
    result = tools.invoke_executable_tool(
        tool_id='test_tool',
        source_file='test.py'
    )
    print(f'Success: {result[\"success\"]}')
"
```

---

## Key Files Reference

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Tool Evolution | `tools/executable/evolve_tool.py` | 17-284 | Creates evolved versions |
| Evolved Tool Loading | `src/tools_manager.py` | 1705-1772 | Loads evolved tools from promotions |
| Best Tool Selection | `src/tools_manager.py` | 1774-1875 | RAG-based fitness ranking |
| Enhanced get_tool | `src/tools_manager.py` | 1877-1920 | Transparent version selection |
| Evolved Execution | `src/tools_manager.py` | 1382-1391 | Uses evolved file in execution |
| Resilient Calling | `tools/executable/resilient_tool_call.py` | 18-215 | Automatic fallback & retry |
| Failure Tracking | `tools/executable/mark_tool_failure.py` | 18-150 | Quality score demotion |
| RAG Memory | `src/rag_memory.py` | 344-411 | Semantic search |

---

## Summary

The **strengthened tool evolution and replace flow** implements a **semantic namespace system** where:

1. **Tool names** represent capabilities, not specific implementations
2. **Evolved versions** are automatically used when available
3. **RAG semantic search** finds the best tool in a namespace
4. **Quality scores** and **failure history** rank candidates by fitness
5. **Transparent selection** requires no code changes

This creates a **self-optimizing system** where tools continuously improve through evolution, and the best version is always used automatically.

**Call `call_tool(toolname)` → Get the BEST tool in that namespace (semantic cluster + fitness + RAG)**
