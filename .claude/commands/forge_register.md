# Register Tool in Forge

Register a new tool manifest in the forge registry with comprehensive metadata tracking.

## Usage
```
/forge_register <tool_name> <type>
```

## Parameters
- `tool_name`: Name of the tool to register
- `type`: Tool type (mcp, llm, executable, etc.)

## What This Command Does

1. **Collect Tool Information**:
   - Interactive prompts for tool details
   - Capability definitions
   - Interface schemas
   - Test specifications

2. **Create Manifest**:
   - Generate forge-compliant YAML manifest
   - Set initial trust level (experimental)
   - Add lineage tracking
   - Configure optimization settings

3. **Register in Systems**:
   - Store in forge registry
   - Add to RAG memory for semantic search
   - Create initial consensus score

4. **Initialize Validation**:
   - Create placeholder test files
   - Set up validation pipeline
   - Configure security policies

## Example
```bash
/forge_register my_translator mcp
```

This will:
1. Prompt for tool description and capabilities
2. Ask for MCP server configuration
3. Create manifest at `code_evolver/forge/data/manifests/my_translator_v1.0.0.yaml`
4. Register in forge registry and RAG memory
5. Set trust level to "experimental"
6. Initialize with validation_score = 0.0

## Generated Manifest Structure
```yaml
tool_id: "my_translator"
version: "1.0.0"
name: "My Translator"
type: "mcp"
description: "Translation tool using MCP"
origin:
  author: "system"
  source_model: "user"
  created_at: "2025-11-18T..."
lineage:
  ancestor_tool_id: null
  mutation_reason: "initial_registration"
  commits: []
trust:
  level: "experimental"
  validation_score: 0.0
  risk_score: 1.0
tags: ["forge", "translation", "mcp"]
```

## Notes
- Newly registered tools start with "experimental" trust level
- Run validation to upgrade trust level to "third_party" or "core"
- Tools can be evolved using `/forge_mutate` command
- Use `/forge_validate` to run validation pipeline
