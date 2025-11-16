# Tool Invocation Guide

Complete guide to using the unified tool invocation system in Code Evolver, including `call_tool()`, parallel execution, and tool chaining.

## Table of Contents

1. [Overview](#overview)
2. [Basic Tool Calls](#basic-tool-calls)
3. [Parallel Tool Execution](#parallel-tool-execution)
4. [Tool Chaining](#tool-chaining)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The unified tool invocation system provides three main APIs:

| API | Purpose | Use Case |
|-----|---------|----------|
| `call_tool()` | Invoke any tool by name | Most common; works for LLM, OpenAPI, Executable tools |
| `call_tools_parallel()` | Execute multiple tools concurrently | Independent operations; multi-language translation |
| `ToolChain` | Chain tools with result passing | Sequential workflows with dependencies |
| `call_llm()` | Direct LLM calls | When you need specific model control |

---

## Basic Tool Calls

### Single Tool Invocation

```python
from node_runtime import call_tool

# Most common pattern
result = call_tool("tool_name", "input_prompt", **kwargs)
```

### Example: Content Generation

```python
from node_runtime import call_tool

# Call LLM tool
joke = call_tool("content_generator", "Tell me a funny programming joke")

# Result is the LLM's response
print(joke)  # "Why did the programmer quit his job?..."
```

### Example: API Calls

```python
from node_runtime import call_tool

# Call API tool
translation = call_tool(
    "nmt_translator",
    "Translate 'Hello, world!' to French",
    target_lang="fr"
)

print(translation)  # "Bonjour, monde!"
```

### Example: Executable Tools

```python
from node_runtime import call_tool

# Run static analysis
analysis_result = call_tool(
    "run_static_analysis",
    "Check Python code quality",
    source_file="generated_code.py"
)

print(analysis_result)  # {"passed": true, "errors": []}
```

### Tool Call Signature

```python
call_tool(
    tool_name: str,           # Name of tool to invoke
    prompt: str,              # Input prompt/description
    **kwargs                  # Tool-specific parameters
) -> str
```

**Returns**: String result from the tool

**Parameters**:
- `tool_name`: Registered name in tools manager
- `prompt`: User input or task description
- `kwargs`: Tool-specific options

---

## Parallel Tool Execution

### Basic Parallel Execution

Execute multiple independent tools concurrently to reduce total execution time.

```python
from node_runtime import call_tools_parallel

# Execute 3 translation tasks in parallel
results = call_tools_parallel([
    ("nmt_translator", "Translate 'Hello' to French", {"target_lang": "fr"}),
    ("nmt_translator", "Translate 'Hello' to Spanish", {"target_lang": "es"}),
    ("nmt_translator", "Translate 'Hello' to German", {"target_lang": "de"})
])

french, spanish, german = results
print(f"FR: {french}, ES: {spanish}, DE: {german}")
# FR: Bonjour, ES: Hola, DE: Hallo
```

### Performance Comparison

```
Sequential Execution:
  Translate to FR: 3s
  Translate to ES: 3s
  Translate to DE: 3s
  Total: 9s

Parallel Execution:
  All 3 in parallel: 3s
  Total: 3s

Speedup: 3×
```

### Complete Example: Multi-Language Content

```python
from node_runtime import call_tool, call_tools_parallel
import json

def translate_content_to_multiple_languages(content, languages):
    """
    Translate content to multiple languages in parallel
    """
    # Step 1: Generate content (sequential)
    if not content:
        content = call_tool(
            "content_generator",
            "Write a short story about a robot"
        )

    # Step 2: Translate in parallel
    translation_tasks = [
        (
            "nmt_translator",
            f"Translate to {lang}:\n{content}",
            {"target_lang": lang[:2]}  # 'French' -> 'fr'
        )
        for lang in languages
    ]

    translations = call_tools_parallel(translation_tasks)

    # Step 3: Return results
    return {
        language: translation
        for language, translation in zip(languages, translations)
    }

# Usage
result = translate_content_to_multiple_languages(
    None,  # Generate content
    ["French", "Spanish", "German", "Japanese"]
)

print(json.dumps(result, indent=2))
```

### Signature

```python
call_tools_parallel(
    tool_calls: List[Tuple[str, str, Dict]]
) -> List[Any]
```

**Parameters**:
- `tool_calls`: List of tuples `(tool_name, prompt, kwargs)`

**Returns**: List of results in same order as input

**Important**:
- Tools must be **independent** (no data dependencies)
- Order of results matches input order
- Executed in ThreadPoolExecutor
- Exceptions in one tool don't block others

---

## Tool Chaining

Chain multiple tools together where each tool's output feeds into the next tool's input.

### Basic Tool Chain

```python
from node_runtime import ToolChain

chain = ToolChain()

result = (
    chain
    .call("content_generator", "Write a technical article about Python")
    .then("spell_checker", "Check spelling:\n{result}")
    .then("style_improver", "Improve writing style:\n{result}")
    .get()
)

print(result)
```

### How Tool Chaining Works

1. **`call()`**: First tool in chain, receives input
2. **`then()`**: Next tool receives `{result}` placeholder substitution
3. **`get()`**: Execute chain and return final result

The `{result}` placeholder is automatically replaced with the previous tool's output.

### Multi-Step Workflow Example

```python
from node_runtime import ToolChain
import json

def create_and_test_algorithm():
    """
    Complex workflow:
    1. Generate algorithm
    2. Create test cases
    3. Run code quality checks
    4. Optimize performance
    """
    chain = ToolChain()

    result = (
        chain
        # Step 1: Generate algorithm
        .call(
            "code_generator",
            "Generate a fibonacci algorithm"
        )
        # Step 2: Create tests
        .then(
            "test_generator",
            "Generate pytest tests for:\n{result}"
        )
        # Step 3: Run static analysis
        .then(
            "run_static_analysis",
            "Check code quality:\n{result}",
            source_file="algorithm.py"
        )
        # Step 4: Optimize
        .then(
            "performance_optimizer",
            "Optimize this code:\n{result}"
        )
        .get()
    )

    return result

output = create_and_test_algorithm()
print(output)
```

### Chain Methods

```python
chain = ToolChain()

# Start the chain
chain.call(tool_name, prompt, **kwargs)

# Add intermediate steps
chain.then(tool_name, prompt, **kwargs)

# Get result
result = chain.get()

# Or build and execute in one call
result = ToolChain().call(...).then(...).get()
```

---

## Advanced Features

### 1. Tool Parameter Substitution

Automatically substitute parameters from previous results:

```python
from node_runtime import call_tool

# Basic substitution
result = call_tool(
    "text_processor",
    "Process: {input}",
    input="Hello, world!"  # Replaces {input}
)
```

### 2. Error Handling in Parallel Execution

```python
from node_runtime import call_tools_parallel

try:
    results = call_tools_parallel([
        ("translator", "text", {"target": "fr"}),
        ("translator", "text", {"target": "es"})
    ])
except Exception as e:
    print(f"Tool error: {e}")
    # Handle error (retry, fallback, etc.)
```

### 3. Tool Discovery & Selection

Automatically find tools by capability:

```python
from src.tools_manager import ToolsManager

tools_mgr = ToolsManager()

# Find all translation tools
translation_tools = tools_mgr.find_tools(
    query="translate",
    tags=["translation"]
)

# Find by type
llm_tools = tools_mgr.find_tools(tool_type="llm")

# Find by performance tier
fast_tools = tools_mgr.find_tools(speed_tier="very-fast")
```

### 4. Tool Metadata Access

```python
from src.tools_manager import ToolsManager

tools_mgr = ToolsManager()

# Get tool info
tool_info = tools_mgr.get_tool("nmt_translator")

print(f"Name: {tool_info.name}")
print(f"Description: {tool_info.description}")
print(f"Speed tier: {tool_info.speed_tier}")
print(f"Cost tier: {tool_info.cost_tier}")
print(f"Tags: {tool_info.tags}")
```

### 5. Conditional Tool Selection

```python
from src.tools_manager import ToolsManager
from node_runtime import call_tool

def smart_translate(text, target_lang, priority="speed"):
    """
    Intelligently select translator based on priority
    """
    tools_mgr = ToolsManager()

    if priority == "speed":
        # Use fastest translator
        tool = tools_mgr.find_tools(
            query="translate",
            speed_tier="very-fast"
        )[0]
    elif priority == "quality":
        # Use highest quality
        tool = tools_mgr.find_tools(
            query="translate",
            quality_tier="excellent"
        )[0]
    else:
        tool = tools_mgr.find_tools(query="translate")[0]

    return call_tool(
        tool.id,
        f"Translate to {target_lang}: {text}",
        target_lang=target_lang
    )

result = smart_translate("Hello", "es", priority="quality")
```

### 6. Tool Composition Patterns

#### Fan-Out-Fan-In Pattern

```python
from node_runtime import call_tool, call_tools_parallel

# Step 1: Generate content
content = call_tool(
    "content_generator",
    "Write a blog post about AI"
)

# Step 2: Process in parallel
results = call_tools_parallel([
    ("translator", f"Translate to French:\n{content}", {"lang": "fr"}),
    ("translator", f"Translate to Spanish:\n{content}", {"lang": "es"}),
    ("summarizer", f"Summarize:\n{content}"),
])

french, spanish, summary = results
print(f"French version length: {len(french)}")
print(f"Spanish version length: {len(spanish)}")
print(f"Summary: {summary}")
```

#### Pipeline Pattern

```python
from node_runtime import ToolChain

# Process data through pipeline
result = (
    ToolChain()
    .call("data_cleaner", "Clean the messy data")
    .then("data_transformer", "Transform cleaned data")
    .then("data_validator", "Validate transformed data")
    .then("report_generator", "Generate report from data")
    .get()
)
```

#### Conditional Pattern

```python
from node_runtime import call_tool
from src.tools_manager import ToolsManager

def conditional_processing(data, processing_type="auto"):
    """
    Choose processing tool based on data type
    """
    tools_mgr = ToolsManager()

    if processing_type == "auto":
        # Analyze data to determine type
        analysis = call_tool(
            "data_analyzer",
            f"What type of data is this? {data[:100]}..."
        )
        processing_type = analysis.lower()

    # Route to appropriate processor
    tool_map = {
        "json": "json_processor",
        "csv": "csv_processor",
        "xml": "xml_processor",
        "text": "text_processor"
    }

    processor = tool_map.get(processing_type, "text_processor")
    return call_tool(processor, f"Process data: {data}")
```

---

## Best Practices

### 1. Use `call_tool()` for Simplicity

❌ **Don't** directly call tool implementations:
```python
# Bad - tight coupling
from src.tools.nmt_translator import translate
result = translate("Hello", "fr")
```

✅ **Do** use the unified interface:
```python
from node_runtime import call_tool
result = call_tool("nmt_translator", "Hello", target_lang="fr")
```

**Benefits**:
- Automatic tool discovery
- Fallback support
- Performance optimization
- Better logging and tracing

### 2. Parallel Execution for Independent Tasks

❌ **Don't** run independent operations sequentially:
```python
# Bad - 9 seconds total
french = call_tool("translator", "text", {"target": "fr"})
spanish = call_tool("translator", "text", {"target": "es"})
german = call_tool("translator", "text", {"target": "de"})
```

✅ **Do** run in parallel:
```python
# Good - 3 seconds total
french, spanish, german = call_tools_parallel([
    ("translator", "text", {"target": "fr"}),
    ("translator", "text", {"target": "es"}),
    ("translator", "text", {"target": "de"})
])
```

### 3. Use Tool Chaining for Dependencies

✅ **Do** use tool chains for sequential workflows:
```python
result = (
    ToolChain()
    .call("generator", "Generate outline")
    .then("writer", "Write article from:\n{result}")
    .then("editor", "Edit for clarity:\n{result}")
    .get()
)
```

### 4. Meaningful Tool Names

Use descriptive names when calling tools:

❌ Bad:
```python
call_tool("t1", prompt)
```

✅ Good:
```python
call_tool("nmt_translator", prompt, target_lang="fr")
```

### 5. Document Expected Parameters

```python
def translate_and_summarize(text):
    """
    Translate text to 3 languages and summarize each.

    Expected tool parameters:
    - nmt_translator: target_lang (str, e.g., "fr", "es", "de")
    - text_summarizer: max_length (int, optional, default=100)
    """
    translations = call_tools_parallel([
        ("nmt_translator", text, {"target_lang": "fr"}),
        ("nmt_translator", text, {"target_lang": "es"}),
        ("nmt_translator", text, {"target_lang": "de"})
    ])

    summaries = call_tools_parallel([
        ("text_summarizer", t, {"max_length": 100})
        for t in translations
    ])

    return summaries
```

### 6. Handle Errors Gracefully

```python
from node_runtime import call_tool
from src.tools_manager import ToolsManager

def robust_translation(text, target_lang):
    """
    Translate with fallback to simpler tool if main fails
    """
    tools_mgr = ToolsManager()

    try:
        # Try primary translator
        return call_tool(
            "nmt_translator",
            f"Translate to {target_lang}: {text}",
            target_lang=target_lang
        )
    except Exception as e:
        print(f"Primary translator failed: {e}")
        # Fallback to simpler tool
        return call_tool(
            "simple_translator",
            f"Translate to {target_lang}: {text}"
        )
```

---

## Troubleshooting

### Issue: Tool Not Found

```
Error: Tool 'my_tool' not found in registry
```

**Solution**:
```python
from src.tools_manager import ToolsManager

tools_mgr = ToolsManager()

# List all available tools
all_tools = tools_mgr.list_tools()
print([t.id for t in all_tools])

# Find similar names
similar = tools_mgr.find_tools(query="translator")
```

### Issue: Parameter Mismatch

```
Error: Tool 'translator' got unexpected keyword argument 'target'
```

**Solution**:
```python
# Check tool documentation
tool_info = tools_mgr.get_tool("nmt_translator")
print(tool_info.parameters)  # Shows expected parameters

# Use correct parameter name
call_tool("nmt_translator", text, target_lang="fr")  # Correct
```

### Issue: Parallel Execution Too Slow

**Problem**: Parallel execution not faster than sequential

**Cause**: I/O-bound tasks not truly concurrent

**Solution**:
```python
# Make sure tasks are truly independent
# Use ThreadPoolExecutor for I/O-bound work
# Consider async tools for better concurrency
```

### Issue: Chain Result Not Substituted

```
# {result} appears literally in output
```

**Solution**:
```python
# Make sure to use {result} placeholder
ToolChain()
    .call("generator", prompt)
    .then("processor", "Process:\n{result}")  # Correct
    .then("processor", "Process:\n" + result)  # Wrong
```

---

## Advanced Debugging

### Enable Tool Invocation Logging

```python
import logging
from node_runtime import NodeRuntime

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Create runtime with debugging
runtime = NodeRuntime.get_instance()

# All tool calls will be logged with parameters and results
result = runtime.call_tool("my_tool", "prompt")
```

### Trace Tool Execution

```python
from node_runtime import ToolChain, call_tools_parallel

# Chains automatically log execution flow
chain_result = (
    ToolChain()
    .call("generator", prompt)  # Logged
    .then("processor", "Process:\n{result}")  # Logged
    .get()
)

# Parallel execution shows timing
results = call_tools_parallel([...])  # Shows completion times
```

---

## See Also

- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) - Tool configuration
- [STATIC_ANALYSIS_TOOLS.md](STATIC_ANALYSIS_TOOLS.md) - Available validators
- [README.md](../README.md) - System overview
