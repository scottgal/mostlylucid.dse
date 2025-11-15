# Remove Tool Command

Remove a tool from the ToolsManager registry.

## Task

Safely remove a tool from the system:
1. Verify the tool exists
2. Show tool details for confirmation
3. Check for dependencies (workflows using this tool)
4. Remove from registry
5. Clean up associated files if needed

## Usage

`/remove_tool <tool_id>`

Example: `/remove_tool email_validator`

## Steps

1. **Verify Tool Exists**
   - Load tool from registry
   - Display tool information
   - Show usage statistics

2. **Check Dependencies**
   - Scan workflows that use this tool
   - Warn if tool is currently in use
   - List dependent workflows

3. **Confirm Removal**
   - Request confirmation (if interactive)
   - Show what will be deleted

4. **Remove Tool**
   - Delete from ToolsManager
   - Update registry file
   - Clean up tool-specific files

5. **Report Results**
   - Confirm deletion
   - Show updated tool count
   - Suggest related cleanup actions

## Output Format

```
=== Remove Tool ===

Tool Found: [tool_id] tool_name

Details:
  Type: tool_type
  Description: Tool description
  Tags: [tag1, tag2]
  Usage: XX calls
  Created: date

Checking Dependencies...
⚠️ Warning: This tool is used by X workflows:
  - workflow_name_1
  - workflow_name_2

Removing tool from registry...

✅ Tool '[tool_id]' successfully removed

Updated Statistics:
  Tools remaining: XX
  Total calls saved: XXX

Recommendations:
- Review workflows that used this tool
- Consider using /optimize_tools to find replacement suggestions
- Update any documentation referencing this tool
```

## Implementation

Run this Python code:

```python
import sys
from pathlib import Path

# Add code_evolver to path
sys.path.insert(0, str(Path.cwd() / "code_evolver" / "src"))

from tools_manager import ToolsManager
import json

# Get tool_id from arguments
args_str = """{{ARGS}}""".strip()

if not args_str:
    print("❌ Error: Please provide a tool_id")
    print("Usage: /remove_tool <tool_id>")
    print("Example: /remove_tool email_validator")
    sys.exit(1)

tool_id = args_str.split()[0]

# Initialize manager
manager = ToolsManager()

# Check if tool exists
tool = manager.get_tool(tool_id)

if not tool:
    print(f"❌ Error: Tool '{tool_id}' not found")
    print("\nAvailable tools:")
    all_tools = manager.get_all_tools()
    for t in sorted(all_tools, key=lambda x: x.tool_id)[:10]:
        print(f"  - {t.tool_id}")
    if len(all_tools) > 10:
        print(f"  ... and {len(all_tools) - 10} more")
    print("\nUse /list_tools to see all tools")
    sys.exit(1)

# Display tool info
print("=== Remove Tool ===\n")
print(f"Tool Found: [{tool.tool_id}] {tool.name}\n")
print("Details:")
print(f"  Type: {tool.tool_type}")
print(f"  Description: {tool.description}")
if tool.tags:
    print(f"  Tags: {tool.tags}")
if hasattr(tool, 'usage_count'):
    print(f"  Usage: {tool.usage_count} calls")
print()

# Check dependencies (scan workflows)
print("Checking dependencies...")

dependent_workflows = []
workflows_dir = Path("registry")
if workflows_dir.exists():
    for workflow_file in workflows_dir.glob("*.json"):
        try:
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)

            # Check if tool is referenced in workflow steps
            if 'steps' in workflow_data:
                for step in workflow_data['steps']:
                    if step.get('tool') == tool_id:
                        dependent_workflows.append(workflow_data.get('workflow_id', workflow_file.stem))
                        break
        except Exception:
            pass

if dependent_workflows:
    print(f"⚠️  Warning: This tool is used by {len(dependent_workflows)} workflow(s):")
    for wf in dependent_workflows[:5]:
        print(f"  - {wf}")
    if len(dependent_workflows) > 5:
        print(f"  ... and {len(dependent_workflows) - 5} more")
    print()
else:
    print("✓ No workflow dependencies found")
    print()

# Remove tool
print("Removing tool from registry...")

try:
    manager.delete_tool(tool_id)
    print(f"\n✅ Tool '{tool_id}' successfully removed\n")

    # Updated statistics
    remaining_tools = manager.get_all_tools()
    stats = manager.get_statistics()

    print("Updated Statistics:")
    print(f"  Tools remaining: {len(remaining_tools)}")

    print("\nRecommendations:")
    if dependent_workflows:
        print("- ⚠️  Review and update workflows that used this tool")
    print("- Consider using /optimize_tools to find replacement suggestions")
    print("- Update any documentation referencing this tool")
    if tool.tool_type in ["workflow", "community"]:
        print(f"- Check {workflows_dir} for any orphaned workflow files")

except Exception as e:
    print(f"\n❌ Error removing tool: {str(e)}")
    print("\nThe tool may have already been removed or the registry file is locked.")
    sys.exit(1)
```
