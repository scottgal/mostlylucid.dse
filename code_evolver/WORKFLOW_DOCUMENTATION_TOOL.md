# Workflow Documentation Tool

## Summary

Created a comprehensive workflow documentation system that automatically generates "How to Use" documentation for workflows.

## Files Created

### 1. `tools/llm/workflow_documenter.yaml`
**Type:** LLM Tool
**Purpose:** LLM-powered documentation generator that analyzes workflow code and generates comprehensive markdown documentation

**Key Features:**
- Uses medium-tier model (general) for balanced quality and speed
- Temperature 0.3 for consistent, factual documentation
- Max 6000 tokens to fit in context window
- Generates concise, practical documentation (max ~3000 words)

**Template Sections:**
- Overview and purpose
- Required inputs (table format)
- Expected outputs (table format with sample JSON)
- How to Use (Quick Start, API, Python examples)
- Code examples (basic and advanced)
- Process flow (Mermaid diagram)
- Limitations and constraints
- Error handling
- Technical details
- FAQ

### 2. `tools/executable/document_workflow.py`
**Type:** Executable Python Script
**Purpose:** Wrapper that calls the LLM tool and writes documentation to README.txt

**Features:**
- Reads workflow code from specified path
- Auto-detects input fields via regex (`input_data.get("field")`)
- Auto-detects tool calls via regex (`call_tool("tool_name")`)
- Estimates workflow speed based on tool usage
- Calls `workflow_documenter` LLM tool
- Writes output to `README.txt` in workflow directory

**Input:**
```json
{
  "workflow_path": "/path/to/workflow/main.py",
  "workflow_name": "Optional workflow name",
  "description": "Optional description"
}
```

**Output:**
```json
{
  "success": true,
  "workflow_name": "Workflow Name",
  "documentation_path": "/path/to/workflow/README.txt",
  "documentation_length": 3542,
  "preview": "## Overview\n..."
}
```

### 3. `tools/executable/document_workflow.yaml`
**Type:** Tool Definition
**Purpose:** Defines the executable tool interface and metadata

## System Fixes

### 1. Unicode Encoding Fix in tools_manager.py
**Problem:** JSON index couldn't save tools with Unicode characters (arrows, checkmarks, etc.)

**Fix:** Added `ensure_ascii=False` to json.dump() in `_save_index()` method:
```python
json.dump(index, f, indent=2, ensure_ascii=False)
```

### 2. Index Save After YAML Load
**Problem:** Tools loaded from YAML files were not being saved to index.json

**Fix:** Added `self._save_index()` call after loading tools from YAML files:
```python
logger.info(f"✓ Loaded {len(yaml_files)} tool(s) from YAML files")
self._save_index()  # NEW: Save index after loading
```

## Usage Examples

### Example 1: Document a Single Workflow
```bash
cd code_evolver
echo '{"workflow_path": "nodes/my_workflow/main.py"}' | python tools/executable/document_workflow.py
```

### Example 2: Document with Custom Name and Description
```bash
echo '{
  "workflow_path": "nodes/email_validator/main.py",
  "workflow_name": "Advanced Email Validator",
  "description": "Enterprise-grade email validation with domain checking"
}' | python tools/executable/document_workflow.py
```

### Example 3: Batch Document All Workflows
```python
import json
import subprocess
from pathlib import Path

workflows_dir = Path("nodes")
for workflow_path in workflows_dir.glob("*/main.py"):
    input_data = {"workflow_path": str(workflow_path)}
    result = subprocess.run(
        ["python", "tools/executable/document_workflow.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        cwd="code_evolver"
    )
    print(f"Documented: {workflow_path.parent.name}")
```

## Integration with System

The tools are now registered in the tools index (`tools/index.json`) and can be invoked by:

1. **Chat CLI**: Users can request "document the workflow X" and the system will call this tool
2. **Overseer**: Can suggest documentation generation as part of workflow creation
3. **Auto-generation**: Can be triggered automatically after workflow creation
4. **API**: Can be called via the tools API endpoint

## Output Format

Documentation is saved as `README.txt` in the workflow directory:

```
nodes/
  my_workflow/
    main.py           # Workflow code
    README.txt        # Generated documentation ✓
```

## Documentation Structure

Generated README.txt includes:

1. **Overview** - 1-2 sentence summary
2. **What It Does** - 2-3 paragraphs explaining purpose and value
3. **Required Inputs** - Table with field specifications
4. **Expected Outputs** - Table with output specifications and sample JSON
5. **How to Use** - Quick start, API example, Python example
6. **Examples** - Basic and advanced usage scenarios
7. **Process Flow** - Mermaid diagram (5-7 nodes max)
8. **Limitations** - Key constraints and limitations
9. **Error Handling** - Common errors and solutions
10. **Technical Details** - Language, dependencies, tools used
11. **FAQ** - 2-3 common questions

## Performance

- **Speed**: 1-3 minutes per workflow (due to LLM call)
- **Token Usage**: ~6000 tokens max (controlled by max_tokens parameter)
- **Output Length**: ~3000 words max (controlled by prompt)
- **Context Window**: Fits within model limits (controlled by max_tokens)

## Benefits

1. **Automatic Documentation**: No manual writing needed
2. **Consistent Format**: All workflows documented the same way
3. **User-Friendly**: Written for non-technical users
4. **API-Ready**: Documentation includes API usage examples
5. **Front-End Ready**: Documentation can be used to generate UI
6. **Comprehensive**: Covers all aspects (inputs, outputs, examples, errors)
7. **Practical**: Focuses on usage rather than theory

## Future Enhancements

Potential improvements:

1. **Versioning**: Track documentation versions alongside workflow versions
2. **Diff Generation**: Show what changed between versions
3. **Multi-Language**: Generate docs in multiple languages
4. **Interactive Examples**: Generate runnable code snippets
5. **Screenshot Integration**: Include workflow output screenshots
6. **Performance Metrics**: Add actual benchmark data
7. **Dependency Graph**: Show workflow dependencies visually

## Testing

Verified with:
- ✅ Tools loaded successfully (121 total)
- ✅ Tools registered in index.json
- ✅ Unicode encoding works correctly
- ✅ Index saved after YAML load
- ✅ document_workflow tool available
- ✅ workflow_documenter LLM tool available

## Status

**✅ Complete and Ready to Use**

All files created, tools registered, and system fixes applied.
