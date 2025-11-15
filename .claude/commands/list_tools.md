# List Tools Command

Display all registered tools in the ToolsManager registry with filtering and search options.

## Task

List all tools registered in the system with:
1. Tool ID, name, and type
2. Description and tags
3. Usage statistics
4. Optional filtering by type or tags
5. Optional semantic search

## Usage

- `/list_tools` - List all tools
- `/list_tools type:llm` - List only LLM tools
- `/list_tools tag:validation` - List tools with 'validation' tag
- `/list_tools search:email` - Semantic search for tools related to 'email'

## Steps

1. **Load Tools Registry**
   - Initialize ToolsManager
   - Load all registered tools from `tools/index.json`

2. **Apply Filters** (if provided)
   - Filter by type: llm, function, workflow, community, openapi, etc.
   - Filter by tags: Show only tools matching specified tags
   - Search: Use RAG-based semantic search

3. **Display Tools**
   - Show in organized table format
   - Group by type
   - Include usage statistics

4. **Show Summary**
   - Total tools count
   - Breakdown by type
   - Most used tools

## Output Format

```
=== Registered Tools ===

📊 Total: XX tools

By Type:
  LLM Tools: XX
  Functions: XX
  Workflows: XX
  OpenAPI: XX
  Community: XX
  Other: XX

────────────────────────────────

🤖 LLM TOOLS

[tool_id] tool_name
  Type: llm
  Description: Tool description here
  Tags: [tag1, tag2, tag3]
  Usage: XX calls
  Model: model_name

[Repeat for each LLM tool]

────────────────────────────────

⚙️ FUNCTION TOOLS

[tool_id] tool_name
  Type: function
  Description: Function description
  Tags: [tag1, tag2]
  Usage: XX calls
  Parameters: param1, param2, ...

[Repeat for each function]

────────────────────────────────

🔄 WORKFLOW TOOLS

[tool_id] tool_name
  Type: workflow
  Description: Workflow description
  Tags: [tag1, tag2]
  Usage: XX calls
  Steps: XX

[Repeat for each workflow]

────────────────────────────────

📈 Statistics

Most Used Tools:
1. tool_name_1 (XXX calls)
2. tool_name_2 (XX calls)
3. tool_name_3 (XX calls)

Average usage: XX calls/tool
Total tool calls: XXXX
```

## Implementation

Run this Python code:

```python
import sys
from pathlib import Path
from collections import defaultdict

# Add code_evolver to path
sys.path.insert(0, str(Path.cwd() / "code_evolver" / "src"))

from tools_manager import ToolsManager, ToolType

# Parse arguments from command (simple parsing)
import re
args_str = """{{ARGS}}"""  # Will be replaced with actual args

filter_type = None
filter_tags = []
search_query = None

if "type:" in args_str:
    match = re.search(r'type:(\w+)', args_str)
    if match:
        filter_type = match.group(1)

if "tag:" in args_str:
    match = re.search(r'tag:(\w+)', args_str)
    if match:
        filter_tags = [match.group(1)]

if "search:" in args_str:
    match = re.search(r'search:(\S+)', args_str)
    if match:
        search_query = match.group(1)

# Initialize manager
manager = ToolsManager()

# Get tools
if search_query:
    tools = manager.search(search_query, top_k=20, use_rag=True)
elif filter_type:
    tools = manager.find_by_type(filter_type)
elif filter_tags:
    tools = manager.find_by_tags(filter_tags)
else:
    tools = manager.get_all_tools()

# Group by type
by_type = defaultdict(list)
for tool in tools:
    by_type[tool.tool_type].append(tool)

# Print header
print("=== Registered Tools ===\n")
print(f"📊 Total: {len(tools)} tools\n")

# Type breakdown
print("By Type:")
for tool_type in ToolType:
    count = len(by_type[tool_type.value])
    if count > 0:
        type_name = tool_type.value.replace('_', ' ').title()
        print(f"  {type_name}: {count}")
print()

# Type icons
type_icons = {
    "llm": "🤖",
    "function": "⚙️",
    "workflow": "🔄",
    "community": "👥",
    "openapi": "🌐",
    "executable": "💻",
    "database": "🗄️",
    "vector_store": "🔍",
    "fine_tuned_llm": "🎯",
    "optimizer": "⚡"
}

# Display each type
for tool_type, type_tools in sorted(by_type.items()):
    if not type_tools:
        continue

    icon = type_icons.get(tool_type, "📦")
    type_name = tool_type.replace('_', ' ').upper()

    print("─" * 60)
    print(f"\n{icon} {type_name} TOOLS\n")

    for tool in sorted(type_tools, key=lambda t: t.name):
        print(f"[{tool.tool_id}] {tool.name}")
        print(f"  Type: {tool.tool_type}")
        print(f"  Description: {tool.description}")
        if tool.tags:
            print(f"  Tags: {tool.tags}")
        if hasattr(tool, 'usage_count'):
            print(f"  Usage: {tool.usage_count} calls")

        # Type-specific details
        if tool.tool_type == "llm" and hasattr(tool, 'implementation'):
            impl = tool.implementation
            if isinstance(impl, dict) and 'model_name' in impl:
                print(f"  Model: {impl['model_name']}")

        elif tool.tool_type == "function" and tool.parameters:
            params = [p.get('name', p) if isinstance(p, dict) else p
                      for p in tool.parameters]
            print(f"  Parameters: {', '.join(params)}")

        elif tool.tool_type == "workflow" and hasattr(tool, 'implementation'):
            impl = tool.implementation
            if isinstance(impl, dict) and 'steps' in impl:
                print(f"  Steps: {len(impl['steps'])}")

        print()

# Statistics
print("─" * 60)
print("\n📈 Statistics\n")

# Get statistics
stats = manager.get_statistics()

# Most used tools
tools_with_usage = [(t, getattr(t, 'usage_count', 0)) for t in tools]
most_used = sorted(tools_with_usage, key=lambda x: x[1], reverse=True)[:5]

if any(usage > 0 for _, usage in most_used):
    print("Most Used Tools:")
    for i, (tool, usage) in enumerate(most_used, 1):
        if usage > 0:
            print(f"{i}. {tool.name} ({usage} calls)")
    print()

total_usage = sum(getattr(t, 'usage_count', 0) for t in tools)
if total_usage > 0:
    avg_usage = total_usage / len(tools) if tools else 0
    print(f"Average usage: {avg_usage:.1f} calls/tool")
    print(f"Total tool calls: {total_usage}")
else:
    print("No usage statistics available yet.")
```
