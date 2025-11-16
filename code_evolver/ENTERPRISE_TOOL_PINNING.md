## Enterprise Tool Pinning System

## Overview

Enterprise-grade tool version management for reproducible, auditable workflows:
- **Pin tools** to specific versions
- **Inline tools** into workflow scripts
- **Protect versions** from trimming
- **Force updates** for critical bug fixes
- **Full audit trail** via RAG tracking

## Problem Solved

### Before: Unreliable Dependencies

```python
# Production workflow
from node_runtime import call_tool

# Uses whatever version of buffer is current
result = call_tool("buffer", json.dumps({...}))

# Risk: Tool evolves, production breaks
# Risk: Tool trimmed, workflow fails
# Risk: Can't reproduce exact production state
```

**Issues:**
- Tools evolve over time
- Old versions get trimmed
- Can't guarantee reproducibility
- Difficult to audit what ran in production
- No rollback capability

### After: Pinned and Reproducible

```python
# Production workflow with pinned dependencies
# ==================== INLINED TOOL: buffer@1.5.0 ====================
# TOOL_ID: buffer
# VERSION: 1.5.0
# RAG_ARTIFACT_ID: buffer_v1_5_0
# INLINED_AT: 2025-01-15T10:30:00Z
# PINNED: true
# ==================== CODE START ====================

[buffer v1.5.0 code embedded here]

# ==================== CODE END ====================

# Workflow is now:
# ✅ Fully self-contained
# ✅ Version-tracked
# ✅ Protected from trimming
# ✅ Auditable
# ✅ Reproducible
```

## Components

### 1. Pin Tool Version (`pin_tool_version.py`)

**Purpose:** Lock tools to specific versions and protect from trimming

**Operations:**
- `pin` - Pin tool to version
- `unpin` - Remove pin
- `list` - List all pins

**Storage:** `.tool_pins.json`

### 2. Inline Tool (`inline_tool.py`)

**Purpose:** Embed tool code into workflow scripts with version tracking

**Operations:**
- `inline` - Embed tool code
- `extract` - Remove embedded code
- `update` - Update to new version
- `list` - List inlined tools

**Markers:** Special comments linking to RAG

## Quick Start

### Pin a Tool

```bash
echo '{
  "operation": "pin",
  "tool_id": "buffer",
  "version": "1.5.0",
  "workflow_id": "production_pipeline",
  "reason": "Production validated version"
}' | python tools/executable/pin_tool_version.py
```

### Inline a Tool

```bash
echo '{
  "operation": "inline",
  "workflow_file": "workflows/production.py",
  "tool_id": "buffer",
  "version": "1.5.0",
  "pin_version": true
}' | python tools/executable/inline_tool.py
```

### List Pinned Versions

```bash
echo '{
  "operation": "list"
}' | python tools/executable/pin_tool_version.py
```

### List Inlined Tools

```bash
echo '{
  "operation": "list",
  "workflow_file": "workflows/production.py"
}' | python tools/executable/inline_tool.py
```

## Workflows

### Workflow 1: Production Deployment

**Goal:** Deploy workflow with guaranteed reproducibility

```python
from node_runtime import call_tool
import json

# Step 1: Test workflow with current versions
test_result = run_workflow("staging_pipeline.py")

if test_result['success']:
    # Step 2: Pin all dependencies to current versions
    dependencies = ["buffer", "nmt_translator", "evaluator"]

    for tool_id in dependencies:
        pin_result = call_tool("pin_tool_version", json.dumps({
            "tool_id": tool_id,
            "version": "current",
            "workflow_id": "production_v2",
            "reason": "Production release 2.0 - validated on staging"
        }))

        print(f"Pinned {tool_id} to version {pin_result['version']}")

    # Step 3: Create production workflow file
    import shutil
    shutil.copy("staging_pipeline.py", "production_v2.py")

    # Step 4: Inline all dependencies
    for tool_id in dependencies:
        inline_result = call_tool("inline_tool", json.dumps({
            "operation": "inline",
            "workflow_file": "production_v2.py",
            "tool_id": tool_id,
            "version": "current",
            "position": "top",
            "pin_version": True
        }))

        print(f"Inlined {tool_id}: marker {inline_result['inline_marker_id']}")

    # Step 5: Deploy
    # production_v2.py is now fully self-contained
    # Contains all dependencies inlined
    # All versions tracked and pinned
    # Can be deployed anywhere without external dependencies

    print("✅ Production workflow ready for deployment")
```

**Result:**
- Single self-contained Python file
- All dependencies embedded
- All versions tracked in comments
- All versions protected from trimming
- Complete audit trail in RAG

### Workflow 2: Critical Bug Fix (Force Update)

**Goal:** Update all workflows using a buggy tool version

```python
# Critical bug found in buffer v1.5.0
# Fixed in buffer v1.5.1

# Step 1: Find all workflows using buffer v1.5.0
workflows = [
    "workflows/production_v1.py",
    "workflows/production_v2.py",
    "workflows/staging.py"
]

updated_workflows = []

for workflow_file in workflows:
    # List inlined tools
    list_result = call_tool("inline_tool", json.dumps({
        "operation": "list",
        "workflow_file": workflow_file
    }))

    # Find buffer instances
    for tool in list_result['inlined_tools']:
        if tool['tool_id'] == 'buffer' and tool['version'] == '1.5.0':
            # Force update to v1.5.1
            update_result = call_tool("inline_tool", json.dumps({
                "operation": "update",
                "workflow_file": workflow_file,
                "inline_marker_id": tool['inline_marker_id'],
                "version": "1.5.1"
            }))

            updated_workflows.append({
                'workflow': workflow_file,
                'old_version': '1.5.0',
                'new_version': '1.5.1',
                'marker': update_result['inline_marker_id']
            })

            print(f"Updated {workflow_file}: buffer v1.5.0 -> v1.5.1")

# Step 2: Document the update
print(f"\n✅ Updated {len(updated_workflows)} workflow(s)")
print("\nAudit Trail:")
for update in updated_workflows:
    print(f"  - {update['workflow']}: {update['old_version']} -> {update['new_version']}")
```

**Result:**
- All workflows updated to patched version
- Old version extracted
- New version inlined
- Complete audit trail maintained
- Can roll back if needed

### Workflow 3: Rollback to Previous Version

**Goal:** Revert to stable version if new version has issues

```python
# buffer v1.5.1 has unexpected behavior in production
# Rollback to v1.5.0

workflow_file = "workflows/production_v2.py"

# Step 1: List inlined tools to find the marker
list_result = call_tool("inline_tool", json.dumps({
    "operation": "list",
    "workflow_file": workflow_file
}))

buffer_marker = None
for tool in list_result['inlined_tools']:
    if tool['tool_id'] == 'buffer':
        buffer_marker = tool['inline_marker_id']
        current_version = tool['version']
        break

if buffer_marker:
    # Step 2: Extract current (problematic) version
    extract_result = call_tool("inline_tool", json.dumps({
        "operation": "extract",
        "workflow_file": workflow_file,
        "inline_marker_id": buffer_marker
    }))

    print(f"Extracted buffer v{current_version}")

    # Step 3: Inline previous stable version
    inline_result = call_tool("inline_tool", json.dumps({
        "operation": "inline",
        "workflow_file": workflow_file,
        "tool_id": "buffer",
        "version": "1.5.0",  # Previous stable version
        "position": "top",
        "pin_version": True
    }))

    print(f"✅ Rolled back to buffer v1.5.0")
    print(f"   New marker: {inline_result['inline_marker_id']}")
```

**Result:**
- Reverted to stable version
- Problematic version removed
- Stable version re-inlined
- Audit trail preserved

### Workflow 4: Multi-Environment Management

**Goal:** Different versions for dev/staging/production

```python
environments = {
    'dev': {
        'workflow': 'workflows/dev_pipeline.py',
        'buffer_version': 'current',  # Use latest
        'reason': 'Development - testing new features'
    },
    'staging': {
        'workflow': 'workflows/staging_pipeline.py',
        'buffer_version': '1.6.0',  # Testing next version
        'reason': 'Staging - validation for production'
    },
    'production': {
        'workflow': 'workflows/production_pipeline.py',
        'buffer_version': '1.5.0',  # Stable version
        'reason': 'Production - proven stable'
    }
}

for env_name, env_config in environments.items():
    # Pin version for this environment
    pin_result = call_tool("pin_tool_version", json.dumps({
        "tool_id": "buffer",
        "version": env_config['buffer_version'],
        "workflow_id": f"{env_name}_pipeline",
        "reason": env_config['reason']
    }))

    # Inline into workflow
    inline_result = call_tool("inline_tool", json.dumps({
        "operation": "inline",
        "workflow_file": env_config['workflow'],
        "tool_id": "buffer",
        "version": env_config['buffer_version'],
        "pin_version": True
    }))

    print(f"✅ {env_name}: buffer v{pin_result['version']}")

# Result:
# - Dev: Uses latest features
# - Staging: Testing v1.6.0 before production
# - Production: Stable v1.5.0
# - All versions tracked and protected
```

## Integration with Version Management

### Pins Protect from Trimming

```python
# When trim_tool_versions runs, it checks for pins

def trim_tool_versions(tool_id, keep_recent=3):
    versions = get_all_versions(tool_id)

    # Load pins
    pins = load_pins()
    pinned_versions = {
        pin['version']
        for pin in pins.values()
        if pin['tool_id'] == tool_id
    }

    for version in versions:
        # Check if pinned
        if version['version'] in pinned_versions:
            print(f"PROTECTED: {tool_id} v{version['version']} (pinned)")
            continue  # Don't trim

        # Check if inlined (via RAG tags)
        if 'inlined' in version['tags']:
            print(f"PROTECTED: {tool_id} v{version['version']} (inlined)")
            continue  # Don't trim

        # Not protected, can trim
        if should_trim(version, keep_recent):
            archive_version(version)
```

**Protection Layers:**
1. **Pin file** (`.tool_pins.json`) - Explicit pins
2. **RAG tags** (`pinned`, `inlined`) - Metadata tracking
3. **Inline comments** - Version references in workflows

### Complete Protection Flow

```
User pins buffer v1.5.0
    ↓
[pin_tool_version]
    ↓
1. Store in .tool_pins.json
2. Tag in RAG with 'pinned:buffer@1.5.0'
    ↓
User inlines buffer v1.5.0
    ↓
[inline_tool]
    ↓
1. Embed code in workflow
2. Add RAG tag 'inlined:{marker_id}'
3. Add comments with version info
    ↓
[trim_tool_versions] runs
    ↓
1. Check .tool_pins.json → v1.5.0 pinned ✅
2. Check RAG tags → 'pinned' tag ✅
3. Check RAG tags → 'inlined' tag ✅
    ↓
Result: buffer v1.5.0 PROTECTED ✅
```

## Pin File Format

`.tool_pins.json`:

```json
{
  "buffer@1.5.0": {
    "tool_id": "buffer",
    "version": "1.5.0",
    "workflow_id": null,
    "pinned_at": "2025-01-15T10:30:00Z",
    "reason": "Production validated",
    "pinned_by": "user"
  },
  "production_v2:nmt_translator@2.5.0": {
    "tool_id": "nmt_translator",
    "version": "2.5.0",
    "workflow_id": "production_v2",
    "pinned_at": "2025-01-15T11:00:00Z",
    "reason": "Production release 2.0",
    "pinned_by": "user"
  },
  "staging:buffer@1.6.0": {
    "tool_id": "buffer",
    "version": "1.6.0",
    "workflow_id": "staging",
    "pinned_at": "2025-01-15T12:00:00Z",
    "reason": "Testing for next production release",
    "pinned_by": "user"
  }
}
```

**Key Features:**
- Workflow-specific pins: `workflow_id:tool_id@version`
- Global pins: `tool_id@version`
- Reason tracking for audit trail
- Timestamp for history
- User tracking for accountability

## Inline Comment Format

```python
# ==================== INLINED TOOL: buffer@1.5.0 ====================
# INLINE_MARKER: a3f5c2d1
# TOOL_ID: buffer
# VERSION: 1.5.0
# RAG_ARTIFACT_ID: buffer_v1_5_0
# INLINED_AT: 2025-01-15T10:30:00Z
# PINNED: true
#
# This tool has been inlined for enterprise reproducibility.
# The code below is tied to buffer v1.5.0 in the RAG memory.
# This version is protected from trimming.
#
# To extract this tool back out:
#   python tools/executable/inline_tool.py extract workflow.py a3f5c2d1
#
# To update to a newer version:
#   python tools/executable/inline_tool.py update workflow.py a3f5c2d1 --version 1.6.0
# ==================== CODE START ====================

[Full tool code here]

# ==================== CODE END: buffer@1.5.0 ====================
```

**Parseable Fields:**
- `INLINE_MARKER` - Unique identifier for extraction/updates
- `TOOL_ID` - Tool identifier
- `VERSION` - Exact version inlined
- `RAG_ARTIFACT_ID` - Link to RAG memory
- `INLINED_AT` - Timestamp for audit
- `PINNED` - Protection status

## Use Cases

### Case 1: Regulatory Compliance

**Requirement:** Must prove exact code ran in production

```python
# Inline all dependencies
inline_all_dependencies("production.py")

# Result: Single file with all code
# - Complete audit trail
# - Exact versions documented
# - Can reproduce production environment
# - Meets compliance requirements
```

### Case 2: Air-Gapped Deployment

**Requirement:** No network access in production

```python
# Development environment (with network):
# 1. Pin dependencies
# 2. Inline dependencies
# 3. Generate single self-contained file

# Production environment (air-gapped):
# 1. Transfer single workflow file
# 2. Run without external dependencies
# 3. No tool resolution needed
```

### Case 3: Long-Term Archival

**Requirement:** Archive projects for 10+ years

```python
# Pin and inline everything
# Store in version control
# Even if RAG memory is lost, workflow still has:
# - Complete code
# - Version information
# - Full functionality
```

### Case 4: A/B Testing

**Requirement:** Test new tool version alongside old

```python
# Production: Uses buffer v1.5.0 (inlined)
# Canary: Uses buffer v1.6.0 (inlined)
# Compare results
# Roll out or rollback based on metrics
```

## Best Practices

### 1. Always Test Before Pinning

```python
# Test in staging first
test_result = run_workflow("staging.py")

if test_result['success'] and test_result['quality'] > 0.95:
    # Pin and promote to production
    pin_and_inline("buffer", "1.6.0", "production.py")
else:
    print("Don't pin - quality threshold not met")
```

### 2. Document Why Versions Are Pinned

```python
# Bad: No context
call_tool("pin_tool_version", {"tool_id": "buffer", "version": "1.5.0"})

# Good: Clear reasoning
call_tool("pin_tool_version", {
    "tool_id": "buffer",
    "version": "1.5.0",
    "workflow_id": "production",
    "reason": "Tested with 10M records, 99.9% success rate, validated by QA"
})
```

### 3. Use Workflow-Specific Pins

```python
# Bad: Global pin affects all workflows
call_tool("pin_tool_version", {
    "tool_id": "buffer",
    "version": "1.5.0"
})

# Good: Workflow-specific (dev can use latest)
call_tool("pin_tool_version", {
    "tool_id": "buffer",
    "version": "1.5.0",
    "workflow_id": "production"
})
```

### 4. Maintain Pin Registry

```markdown
## Pin Registry

### Production
- buffer@1.5.0 (pinned: 2025-01-15)
  - Reason: Production validated, 1M+ records processed
  - Workflows: production_v1.py, production_v2.py
  - Inline markers: a3f5c2d1, b7e4d9f2

- nmt_translator@2.5.0 (pinned: 2025-01-15)
  - Reason: Production release 2.0
  - Workflows: production_v2.py
  - Inline markers: c8a2e5b3
```

### 5. Regular Pin Audits

```python
# Monthly audit
pins = call_tool("pin_tool_version", {"operation": "list"})

for pin in pins['pins']:
    age_days = (datetime.now() - parse(pin['pinned_at'])).days

    if age_days > 90:
        print(f"⚠️ Old pin: {pin['tool_id']}@{pin['version']}")
        print(f"   Pinned {age_days} days ago")
        print(f"   Reason: {pin['reason']}")
        print(f"   Review: Consider updating or documenting why still pinned")
```

## Advantages Over External Dependencies

| Aspect | External Tools | Pinned Tools | Inlined Tools |
|--------|---------------|--------------|---------------|
| **Reproducibility** | Depends on availability | Guaranteed (if files exist) | 100% Guaranteed |
| **Offline Execution** | No | No | Yes |
| **Version Control** | Separate tracking | Pin file | Embedded in workflow |
| **Deployment** | Multiple files | Multiple files | Single file |
| **Audit Trail** | External refs | Pin file + RAG | Complete code + comments |
| **Rollback** | Complex | Medium | Simple |
| **Force Updates** | Difficult | Medium | Easy |
| **Air-Gap Friendly** | No | Partial | Yes |
| **Compliance** | Difficult to prove | Can audit pins | Complete proof |

## Troubleshooting

### Pin Not Protecting from Trimming

**Issue:** Version trimmed even though pinned

**Debug:**
```python
# Check pin file
with open('.tool_pins.json') as f:
    pins = json.load(f)
    print(json.dumps(pins, indent=2))

# Check RAG tags
artifact = rag.get_artifact('buffer_v1_5_0')
print(f"Tags: {artifact.tags}")

# Should include: 'pinned', 'pinned:buffer@1.5.0'
```

### Inline Marker Not Found

**Issue:** Can't extract or update inlined tool

**Debug:**
```python
# List all inlined tools
result = call_tool("inline_tool", {
    "operation": "list",
    "workflow_file": "production.py"
})

print(json.dumps(result, indent=2))

# Verify marker exists and matches
```

### Version Mismatch

**Issue:** Pinned version doesn't exist

**Debug:**
```bash
# Check available versions
ls tools/executable/buffer/buffer_v*.py

# Check RAG artifacts
python -c "
from src.rag_memory import RAGMemory
rag = RAGMemory()
buffer_artifacts = rag.find_by_tags(['buffer'])
for art in buffer_artifacts:
    print(f\"{art.artifact_id}: {art.metadata.get('version', 'unknown')}\")
"
```

## Summary

**Status:** ✅ COMPLETE

**Tools Created:**
1. `pin_tool_version.py` + `.yaml` - Pin/unpin/list operations
2. `inline_tool.py` + `.yaml` - Inline/extract/update/list operations

**Features:**
- ✅ Pin tools to specific versions
- ✅ Workflow-specific pins
- ✅ Inline tools into workflow scripts
- ✅ Version tracking in comments
- ✅ RAG protection (pinned + inlined tags)
- ✅ Force updates via extract/update
- ✅ Complete audit trail
- ✅ Self-contained deployments
- ✅ Rollback capability

**Benefits:**
- **Enterprise reproducibility** - Exact versions documented
- **Offline execution** - No external dependencies
- **Compliance** - Complete audit trail
- **Force updates** - Critical bug fixes
- **Rollback** - Revert to stable versions
- **Multi-environment** - Different versions per environment

**Integration:**
- Works with version management system
- Integrates with trim_tool_versions
- RAG-based protection
- Full audit trail

**Next Steps:**
- Test with real workflows
- Add CLI commands to chat_cli.py
- Create automated deployment scripts
- Add monitoring and alerting
