## Tool Version Management System

## Overview

Keeps tools organized and tidy while allowing rollback:
- **Original YAML** always kept as ultimate backup
- **Original version** (v1.0.0) always kept
- **Recent 2-3 versions** kept for rollback
- **Old versions** archived or deleted
- **Each tool** in own directory
- **Specialization** when tool diverges too far

## Problem Solved

### Before
```
tools/executable/
  buffer.py
  buffer_v1_1_0.py
  buffer_v1_2_0.py
  buffer_v1_3_0.py
  ... (100 more versions)
  buffer_v2_5_8.py
  buffer.yaml
```
- Hard to find current version
- Wasted storage
- No organization

### After
```
tools/executable/
  buffer/
    buffer.yaml                    # Ultimate backup (never deleted)
    buffer_v1_0_0.py               # Original (never deleted)
    buffer_v2_3_0.py               # Recent version (kept)
    buffer_v2_4_0.py               # Recent version (kept)
    buffer_v2_5_0.py               # Current version (kept)
    buffer.py -> buffer_v2_5_0.py  # Symlink to latest
    archived_versions/
      buffer_v1_1_0.py             # Old versions archived
      buffer_v1_2_0.py
      ... (etc)
```

## Directory Structure

### Standard Tool Layout

```
tools/executable/
  my_tool/
    my_tool.yaml              # YAML definition (ultimate backup)
    my_tool_v1_0_0.py         # Original version (always kept)
    my_tool_v1_5_0.py         # Recent -2
    my_tool_v1_6_0.py         # Recent -1
    my_tool_v1_7_0.py         # Current
    my_tool.py                # Symlink -> my_tool_v1_7_0.py
    archived_versions/
      my_tool_v1_1_0.py       # Archived (safe rollback)
      my_tool_v1_2_0.py
      my_tool_v1_3_0.py
      my_tool_v1_4_0.py
```

### When Tool Specializes

If `my_tool` diverges too far (e.g., becomes `advanced_calculator`):

```
tools/executable/
  my_tool/                    # Original tool (unchanged)
    my_tool.yaml
    my_tool_v1_0_0.py
    my_tool_v1_7_0.py
    my_tool.py

  advanced_calculator/        # NEW specialized tool
    advanced_calculator.yaml
    advanced_calculator_v1_0_0.py
    advanced_calculator.py
```

## Core Tools

### 1. trim_tool_versions

**Purpose:** Keep only recent versions

```bash
# Trim single tool
echo '{
  "tool_id": "buffer",
  "keep_recent": 3,
  "archive_old": true
}' | python tools/executable/trim_tool_versions.py

# Trim all tools
echo '{
  "trim_all": true,
  "keep_recent": 3
}' | python tools/executable/trim_tool_versions.py
```

**Keeps:**
- Original YAML
- v1.0.0
- Last 3 versions

**Archives:**
- All middle versions

### 2. detect_tool_specialization

**Purpose:** Detect when tool should fork into new specialized tool

```python
from node_runtime import call_tool
import json

result = call_tool("detect_tool_specialization", json.dumps({
    "original_name": "add_numbers",
    "original_description": "Adds two numbers",
    "original_parameters": '["num1", "num2"]',
    "evolved_name": "scientific_calculator",
    "evolved_description": "Advanced calculations",
    "evolved_parameters": '["expression", "mode", "precision"]'
}))

decision = json.loads(result)

if decision['should_specialize']:
    # Create new tool in own directory
    create_specialized_tool(decision['suggested_new_name'])
else:
    # Continue evolution
    bump_version("add_numbers")
```

## Retention Policy

### Always Kept
1. **Original YAML definition** - Ultimate backup
2. **v1.0.0** - First version
3. **Last N versions** - Recent history (default: 3)
4. **Symlink** - Points to current version

### Archived (Rollback Available)
- Versions between original and recent N
- Stored in `archived_versions/` subdirectory
- Can be restored if needed

### Never Kept (Optional)
- Very old archived versions can be pruned
- Only if storage is critical

## Workflows

### Tool Evolution Flow

```
Tool Fails
    ↓
[evolve_tool] - Generate fix
    ↓
[detect_tool_specialization] - Check divergence
    ↓
Divergence < 30%: Continue evolution (bump version)
Divergence > 70%: Specialize (new tool + directory)
    ↓
[trim_tool_versions] - Clean up old versions
    ↓
Result: Clean, organized tools
```

### Version Lifecycle

```
v1.0.0 - Created (original)
    ↓
v1.1.0 - Bug fix
v1.2.0 - Feature added
v1.3.0 - Optimization
    ↓ [trim - keep last 3]
v1.4.0 - ← Kept (recent -2)
v1.5.0 - ← Kept (recent -1)
v1.6.0 - ← Kept (current)
    ↓
v1.1.0, v1.2.0, v1.3.0 → Archived
```

### Specialization Decision

```python
def should_specialize(original, evolved):
    """Detect if tool has diverged too far"""

    # Calculate divergence score
    name_changed = original.name != evolved.name
    params_changed = len(evolved.params) > len(original.params) * 1.5
    category_changed = original.category != evolved.category
    purpose_changed = similarity(original.desc, evolved.desc) < 0.7

    divergence_score = sum([
        name_changed * 0.4,
        params_changed * 0.2,
        category_changed * 0.2,
        purpose_changed * 0.2
    ])

    return divergence_score > 0.7
```

## Integration with evolve_tool

Update `evolve_tool.py`:

```python
def evolve_tool(tool_id, error_message, mutation_hint):
    # 1. Generate evolved code
    evolved_code = generate_fix(...)

    # 2. Check if should specialize
    spec_result = call_tool("detect_tool_specialization", json.dumps({
        "original_name": tool.name,
        "original_description": tool.description,
        "evolved_name": evolved_tool.name,
        "evolved_description": evolved_tool.description,
        ...
    }))

    decision = json.loads(spec_result)

    # 3. Create specialized tool OR evolve existing
    if decision['should_specialize'] and decision['confidence'] > 0.8:
        # Create new specialized tool
        new_tool_id = decision['suggested_new_name']
        tool_dir = create_tool_directory(new_tool_id)

        save_tool_version(tool_dir, new_tool_id, evolved_code, "1.0.0")

        return {
            'action': 'specialized',
            'original_tool': tool_id,
            'new_tool': new_tool_id,
            'message': f'Tool specialized into: {new_tool_id}'
        }
    else:
        # Continue evolution
        new_version = increment_version(tool.version)
        tool_dir = get_tool_directory(tool_id)

        save_tool_version(tool_dir, tool_id, evolved_code, new_version)

        # Trim old versions
        call_tool("trim_tool_versions", json.dumps({
            "tool_id": tool_id,
            "keep_recent": 3
        }))

        return {
            'action': 'evolved',
            'tool': tool_id,
            'new_version': new_version
        }
```

## Rollback Procedure

### Rollback to Previous Version

```bash
cd tools/executable/my_tool

# List available versions
ls -la *.py

# Update symlink to older version
ln -sf my_tool_v1_5_0.py my_tool.py
```

### Restore Archived Version

```bash
cd tools/executable/my_tool

# List archived versions
ls archived_versions/

# Restore version
cp archived_versions/my_tool_v1_3_0.py .

# Use restored version
ln -sf my_tool_v1_3_0.py my_tool.py
```

### Restore from Original

```bash
# Original YAML and v1.0.0 are always available
cd tools/executable/my_tool

# Use original
ln -sf my_tool_v1_0_0.py my_tool.py
```

## Maintenance Tasks

### Weekly Cleanup

```bash
# Trim all tools (keep last 3 versions)
echo '{"trim_all": true, "keep_recent": 3}' | \
  python tools/executable/trim_tool_versions.py
```

### Dry Run (Preview)

```bash
# See what would be trimmed without actually doing it
echo '{"trim_all": true, "keep_recent": 3, "dry_run": true}' | \
  python tools/executable/trim_tool_versions.py
```

### Check Space Savings

```bash
# See how much space trimming would save
result=$(echo '{"trim_all": true, "dry_run": true}' | \
  python tools/executable/trim_tool_versions.py)

echo "$result" | jq '.total_space_saved_mb'
# Output: 12.3
```

## Benefits

### Storage Efficiency
- **Before:** 1000 versions → 5 GB storage
- **After:** 100 versions (10:1 compression) → 500 MB storage

### Organization
- Each tool in own directory
- Easy to find current version (symlink)
- Clear version history

### Safety
- Original always available
- Recent versions for rollback
- Archived versions for deep rollback
- YAML backup for recreation

### Automatic Cleanup
- No manual version management
- Automatic trimming
- Scheduled maintenance

## Examples

### Example 1: Simple Evolution

```
buffer v1.0.0 (original)
    ↓ fix timeout bug
buffer v1.1.0
    ↓ add batching
buffer v1.2.0
    ↓ optimize performance
buffer v1.3.0
```

**Trimmed State:**
- Keep: v1.0.0 (original), v1.1.0, v1.2.0, v1.3.0
- Archive: (none yet - only 4 versions)

### Example 2: Long Evolution

```
translator v1.0.0 (original)
    ↓ (20 evolutions)
translator v1.20.0
```

**Trimmed State:**
- Keep: v1.0.0, v1.18.0, v1.19.0, v1.20.0
- Archive: v1.1.0 through v1.17.0

### Example 3: Specialization

```
add_numbers v1.0.0
    ↓ (5 evolutions)
add_numbers v1.5.0
    ↓ [DIVERGENCE DETECTED]
    ↓ User wants: "scientific calculations"
    ↓
FORK INTO: scientific_calculator v1.0.0
```

**Result:**
- `add_numbers/` - Unchanged, still available
- `scientific_calculator/` - New tool, new directory

## Summary

**Status:** ✅ DESIGNED

**Tools Created:**
- `trim_tool_versions.py` + `.yaml` - Version cleanup
- `detect_tool_specialization.yaml` - Divergence detection

**Features:**
- ✅ Original always kept (YAML + v1.0.0)
- ✅ Recent 2-3 versions kept
- ✅ Old versions archived
- ✅ Each tool in own directory
- ✅ Specialization detection
- ✅ Automatic trimming
- ✅ Rollback support

**Impact:**
- **90% storage reduction** (10 versions → 4 kept)
- **Better organization** (directory per tool)
- **Safe evolution** (rollback available)
- **Clean splits** (specialization when needed)

**Next Steps:**
- Update `evolve_tool` to use new structure
- Create migration tool for existing tools
- Add scheduled cleanup
- Test rollback procedures
