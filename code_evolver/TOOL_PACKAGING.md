# Tool Packaging Format

## Overview

Tools are packaged as **YAML + optional ZIP** files for easy distribution and auto-loading.

## Structure

```
tools/
├── llm/                      # LLM-based tools (YAML only)
│   ├── code/
│   │   ├── general.yaml
│   │   ├── code_reviewer.yaml
│   │   └── security_auditor.yaml
│   ├── content/
│   │   └── content_generator.yaml
│   ├── analysis/
│   │   └── summarizer.yaml
│   └── fast/
│       ├── fast_code_generator.yaml
│       └── quick_feedback.yaml
│
├── executable/               # Executable tools (YAML + optional ZIP)
│   ├── save_to_disk.yaml
│   └── save_to_disk.zip     # Contains Python code
│
└── custom/                   # Custom Python tools (YAML + ZIP)
    ├── http_server.yaml
    └── http_server.zip      # Contains implementation code
```

## YAML Format

### LLM Tools (no code needed)

```yaml
name: "General Code Generator"
type: "llm"
description: "General purpose code generation"

# Performance characteristics
cost_tier: "medium"
speed_tier: "fast"
quality_tier: "excellent"
max_output_length: "very-long"

# LLM configuration
llm:
  role: "base"  # References backend's model mapping (fast/base/powerful)

  system_prompt: |
    You are an expert software engineer.
    Priority: {priority}

  prompt_template: |
    Generate code for: {task}

# Tags for discovery
tags:
  - general
  - code-generation
```

### Executable Tools (with ZIP)

```yaml
name: "Save to Disk"
type: "executable"
description: "Saves content to a file"

# Reference to implementation
implementation:
  type: "python_zip"
  entry_point: "main.py"
  function: "save_file"

# Parameters schema
parameters:
  filepath:
    type: "string"
    required: true
  content:
    type: "string"
    required: true

tags:
  - file-operations
  - storage
```

**Corresponding ZIP** (`save_to_disk.zip`):
```
save_to_disk.zip
├── main.py          # Entry point
├── utils.py         # Helper functions
└── requirements.txt # Dependencies
```

### Custom Tools (with ZIP)

```yaml
name: "HTTP Content Fetcher"
type: "custom"
description: "Fetches content from HTTP endpoints"

implementation:
  type: "python_zip"
  entry_point: "fetcher.py"
  class: "HTTPContentFetcher"

parameters:
  url:
    type: "string"
    required: true
  method:
    type: "string"
    default: "GET"

tags:
  - http
  - api
  - fetching
```

## ZIP Package Format

For tools with Python code, create a ZIP file with:

```
tool_name.zip
├── main.py or entry_point.py    # Entry point
├── requirements.txt              # Python dependencies
├── README.md                     # Documentation
└── src/                         # Additional modules
    ├── __init__.py
    └── helpers.py
```

### Entry Point Interface

```python
# For executable tools
def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the tool with given parameters.

    Args:
        parameters: Tool parameters from YAML schema

    Returns:
        Dictionary with 'result' or 'error'
    """
    pass

# For custom tools (class-based)
class MyTool:
    def __init__(self, config: Dict[str, Any]):
        """Initialize with config from YAML"""
        pass

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute with parameters"""
        pass
```

## Backend-Agnostic Design

Tools reference **abstract roles** instead of specific models:

- `role: "fast"` → Maps to fast model (claude-haiku, gpt-4o-mini, tinyllama)
- `role: "base"` → Maps to base model (claude-sonnet, gpt-4o, codellama)
- `role: "powerful"` → Maps to powerful model (claude-opus, o1-preview, deepseek)

This allows tools to work with **any LLM backend** without modification.

## Loading Tools

Tools are auto-loaded from the `tools/` directory:

```python
from src.tools_manager import ToolsManager

tools = ToolsManager(tools_path="./tools")
tools.load_all_tools()  # Loads all YAML + ZIP packages

# Use a tool
result = tools.invoke_tool("general", {"task": "write hello world"})
```

## Creating a New Tool

### 1. LLM Tool (Simple)

Create `tools/llm/category/my_tool.yaml`:

```yaml
name: "My Tool"
type: "llm"
description: "Does something useful"

llm:
  role: "base"
  system_prompt: "You are..."
  prompt_template: "Do this: {task}"

tags:
  - my-category
```

Done! Works with all backends automatically.

### 2. Custom Tool (With Code)

Create `tools/custom/my_tool.yaml`:

```yaml
name: "My Tool"
type: "custom"
description: "Custom Python tool"

implementation:
  type: "python_zip"
  entry_point: "tool.py"
  class: "MyTool"

tags:
  - custom
```

Create `tools/custom/my_tool.zip`:

```python
# tool.py
class MyTool:
    def execute(self, parameters):
        return {"result": "success"}
```

Done!

## Benefits

✅ **No duplication** - Tools defined once, work everywhere
✅ **Backend-agnostic** - Switch LLM providers without changing tools
✅ **Easy distribution** - YAML + ZIP = portable package
✅ **Auto-loading** - Drop in `tools/` directory and go
✅ **Organized** - Grouped by type and purpose
✅ **Extensible** - Add new tools without touching core code
