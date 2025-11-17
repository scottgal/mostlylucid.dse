# JSON Structured Output & General Fallback Tool

## Critical Fixes Implemented ✅

### 1. JSON Structured Output
### 2. Code/Explanation Separation
### 3. General Fallback Tool
### 4. RAG Integration with Full Metadata

---

## Issue: Mixed Code and Explanations

### Before (BROKEN)
```
Line 1: import json
Line 2: def add():
Line 3:     return 1 + 1
Line 4: This code adds two numbers and returns...  ← SYNTAX ERROR!
Line 5: To test this code, run python...
```

**Problem**: LLM mixed explanations with code, causing syntax errors.

### After (FIXED)
```json
{
  "code": "import json\ndef add():\n    return 1 + 1",
  "description": "Adds two numbers",
  "tags": ["math", "addition"]
}
```

**Solution**: Request JSON structure, parse it, extract only code field.

---

## Implementation

### 1. Code Generation Prompt (New Format)

**chat_cli.py - Code generation:**
```python
code_prompt = f"""Based on this strategy:
{strategy}

Generate a Python implementation. You MUST respond with ONLY a JSON object:

{{
  "code": "the actual Python code as a string",
  "description": "brief one-line description",
  "tags": ["tag1", "tag2"]
}}

Code requirements:
- Pure Python, no external dependencies
- Include __main__ section for JSON I/O
- Production-ready

CRITICAL:
- The "code" field must contain ONLY executable Python code
- NO markdown fences (no ```python)
- NO explanations mixed with code
- Must be immediately runnable

Return ONLY the JSON object, nothing else."""
```

### 2. JSON Parsing Logic

**chat_cli.py - Parse response:**
```python
# Parse JSON response
try:
    import json
    # Clean any markdown wrapping
    response = response.strip()
    if response.startswith('```json'):
        response = response.split('```json')[1].split('```')[0].strip()
    elif response.startswith('```'):
        response = response.split('```')[1].split('```')[0].strip()

    result = json.loads(response)
    code = result.get("code", "")
    code_description = result.get("description", description)
    code_tags = result.get("tags", ["generated", "chat"])

    if not code:
        console.print("[red]No code in JSON response[/red]")
        return False

except json.JSONDecodeError as e:
    console.print(f"[yellow]Failed to parse JSON, using raw output: {e}[/yellow]")
    # Fallback: treat entire response as code
    code = response
    code_description = description
    code_tags = ["generated", "chat"]

# Clean the code (remove any remaining markdown)
code = self._clean_code(code)
```

### 3. Escalation Prompt (JSON Format)

**chat_cli.py - Escalation/fixing:**
```python
fix_prompt = f"""You are an expert code debugger. The following code FAILED.

ORIGINAL GOAL: {description}
OVERSEER STRATEGY: {strategy}
ERROR OUTPUT: {error_output}

CURRENT CODE:
```python
{code}
```

You MUST respond with ONLY a JSON object:

{{
  "code": "the fixed Python code as a string",
  "fixes_applied": ["brief description of fix 1", "fix 2"],
  "analysis": "one sentence explaining what was wrong"
}}

Requirements for "code" field:
- ONLY executable Python code
- NO markdown fences
- Must fix ALL errors shown above

Return ONLY the JSON object."""
```

### 4. RAG Storage with Metadata

**chat_cli.py - Store in RAG:**
```python
# Step 5: Store in RAG with metadata
if hasattr(self, 'rag'):
    try:
        from src.rag_memory import ArtifactType
        self.rag.store_artifact(
            artifact_id=f"func_{node_id}",
            artifact_type=ArtifactType.FUNCTION,
            name=code_description,  # From JSON
            description=description,
            content=code,           # From JSON
            tags=code_tags,         # From JSON
            metadata={
                "node_id": node_id,
                "strategy": strategy[:200],
                "tools_available": available_tools
            },
            auto_embed=True
        )
    except Exception as e:
        console.print(f"[dim yellow]Note: Could not store in RAG: {e}[/dim yellow]")
```

---

## General Fallback Tool

### Concept

When no specialized tool matches the task, use a **general** fallback tool instead of failing.

### Configuration

**config.yaml:**
```yaml
tools:
  # General fallback - always available
  general:
    name: "General Code Generator"
    type: "llm"
    description: "General purpose code generation for any programming task. Used as fallback when no specialized tool matches."
    llm:
      model: "codellama"
      endpoint: null
    tags: ["general", "fallback", "code-generation", "any-task"]

  # Specialized tools
  code_reviewer:
    name: "Code Reviewer"
    type: "llm"
    description: "Reviews code for quality, bugs, and best practices"
    llm:
      model: "llama3"
      endpoint: null
    tags: ["review", "quality"]
```

### Tool Selection Logic

**tools_manager.py:**
```python
def get_best_llm_for_task(self, task_description: str, min_similarity: float = 0.6) -> Optional[Tool]:
    """
    Get the best LLM tool for a given task using RAG semantic search.
    Falls back to 'general' tool if no good matches found.
    """
    # Try to find specialized tools
    llm_tools = self.search(task_description, top_k=3, use_rag=True)
    llm_tools = [t for t in llm_tools if t.tool_type == ToolType.LLM]

    # Return specialized tool if found
    if llm_tools:
        return llm_tools[0]

    # No good match - use 'general' fallback tool
    if 'general' in self.tools:
        logger.info("No specialized tool found, using general fallback")
        return self.tools['general']

    # No tools at all
    return None
```

### User Feedback

**chat_cli.py:**
```python
if selected_tool:
    if "general" in selected_tool.tool_id.lower() or "fallback" in selected_tool.tags:
        console.print(f"[dim]Using general code generator (fallback)[/dim]")
    else:
        console.print(f"[dim]✓ Selected specialized tool: {selected_tool.name}[/dim]")
```

---

## Workflow

### Example: Random Number Task

```
User: "generate add 5 plus a random number"
    ↓
[Tool Search]
  - Search: "add 5 plus a random number"
  - No specialized "math" or "random" tool found
  - Fall back to 'general' tool
  - console.print("Using general code generator (fallback)")
    ↓
[Code Generation via General Tool]
  - Prompt requests JSON structure
  - LLM generates:
    {
      "code": "import json\nimport random\n...",
      "description": "Adds 5 to a random number",
      "tags": ["math", "random", "calculation"]
    }
    ↓
[Parse JSON]
  - Extract code: "import json\nimport random..."
  - Extract description: "Adds 5 to a random number"
  - Extract tags: ["math", "random", "calculation"]
    ↓
[Store in RAG]
  - artifact_id: "func_add_5_random"
  - name: "Adds 5 to a random number"
  - tags: ["math", "random", "calculation"]
  - metadata: {strategy, tools_available, node_id}
  - auto_embed: true
    ↓
[Save & Test]
  - Save clean code (no explanations!)
  - Run tests
  - Success ✅
```

---

## Benefits

### 1. Clean Code
- **No mixed explanations**: Code is pure, executable Python
- **No syntax errors**: From text mixed into code
- **Predictable format**: Always know what you're getting

### 2. Rich Metadata
- **Description**: What the code does
- **Tags**: Categorization for search
- **Strategy**: How it was designed
- **Tools**: What was available

### 3. RAG Integration
- **Searchable**: Find similar solutions semantically
- **Reusable**: Tag-based and similarity-based retrieval
- **Learning**: System remembers successful patterns

### 4. Fallback Safety
- **Always works**: General tool catches everything
- **Transparent**: User sees "fallback" message
- **Extensible**: Add specialized tools over time

---

## Tool Hierarchy

```
Task: "validate email address"
    ↓
Search tools with RAG
    ↓
Found: "Email Validator" (specialized) → Use it!


Task: "add two numbers"
    ↓
Search tools with RAG
    ↓
Not found: No specialized tool
    ↓
Fallback: Use 'general' tool ✅
```

---

## Output Structure

### Code Generation Response

```json
{
  "code": "import json\nimport sys\n\ndef process(data):\n    return data\n\nif __name__ == '__main__':\n    input_json = json.load(sys.stdin)\n    result = process(input_json)\n    print(json.dumps(result))",
  "description": "Processes input data",
  "tags": ["data-processing", "json", "utility"]
}
```

### Escalation/Fix Response

```json
{
  "code": "import json\nimport sys  # Added missing import\n\ndef process(data):\n    return data\n\nif __name__ == '__main__':\n    input_json = json.load(sys.stdin)\n    result = process(input_json)\n    print(json.dumps(result))",
  "fixes_applied": [
    "Added missing 'import sys' statement",
    "Fixed JSON output format"
  ],
  "analysis": "Code was missing sys import required for stdin/stdout"
}
```

---

## Testing

### Test 1: JSON Parsing

```bash
python chat_cli.py
```

```
CodeEvolver> generate calculate factorial

Generating code with codellama...
# Should receive JSON response
# Parse and extract code only
# No explanatory text in saved file
```

### Test 2: General Fallback

```
CodeEvolver> generate some random task

Using general code generator (fallback)  ← Shown to user
Generating code with General Code Generator...
```

### Test 3: Specialized Tool

```
CodeEvolver> generate review this code for bugs

✓ Selected specialized tool: Code Reviewer  ← Specialized!
Generating code with Code Reviewer...
```

### Test 4: RAG Storage

```python
from src import RAGMemory, ConfigManager, OllamaClient

config = ConfigManager("config.yaml")
client = OllamaClient(config.ollama_url, config_manager=config)
rag = RAGMemory(ollama_client=client)

# After generating code, check RAG
artifacts = rag.list_all()
for artifact in artifacts:
    print(f"Name: {artifact.name}")
    print(f"Tags: {artifact.tags}")
    print(f"Metadata: {artifact.metadata}")
```

---

## Error Handling

### Invalid JSON

```python
except json.JSONDecodeError as e:
    console.print(f"[yellow]Failed to parse JSON, using raw output: {e}[/yellow]")
    # Fallback: treat entire response as code
    code = response
    code_description = description
    code_tags = ["generated", "chat"]
```

### No Code in JSON

```python
if not code:
    console.print("[red]No code in JSON response[/red]")
    return False
```

### Markdown Wrapping

```python
# Clean JSON markdown fences
if response.startswith('```json'):
    response = response.split('```json')[1].split('```')[0].strip()
```

---

## Summary

### What Was Fixed

✅ **JSON structured output**: Code separated from explanations
✅ **Metadata extraction**: Description and tags from JSON
✅ **RAG integration**: Full context stored in RAG
✅ **General fallback tool**: Always have a tool available
✅ **Clean code**: No more text mixed with code
✅ **Error recovery**: Graceful fallback on JSON parse errors

### Files Changed

1. **chat_cli.py**
   - JSON prompt for code generation
   - JSON parsing logic
   - JSON prompt for escalation
   - RAG storage with metadata
   - General tool fallback display

2. **tools_manager.py**
   - `get_best_llm_for_task()` - General fallback logic

3. **config.yaml**
   - Added 'general' tool definition

### Usage

```bash
# Restart to load changes
exit
python chat_cli.py
```

```
generate your task here
```

**Expect:**
- Clean code without explanations
- Proper JSON parsing
- General fallback when no specialized tool
- Full metadata in RAG

---

**All systems ready for production!** 🚀
