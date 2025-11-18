# MCP System - Quick Reference Guide

## File Locations

### Core MCP Implementation
```
/home/user/mostlylucid.dse/code_evolver/src/mcp_client_manager.py       (314 lines)
/home/user/mostlylucid.dse/code_evolver/src/mcp_tool_adapter.py          (288 lines)
/home/user/mostlylucid.dse/code_evolver/src/tools_manager.py             (1200+ lines)
```

### Configuration Files
```
/home/user/mostlylucid.dse/code_evolver/config.mcp.yaml                  (194 lines)
/home/user/mostlylucid.dse/code_evolver/config.anthropic.yaml
/home/user/mostlylucid.dse/code_evolver/config.local.yaml
/home/user/mostlylucid.dse/code_evolver/config.yaml
```

### Tool Definitions
```
/home/user/mostlylucid.dse/code_evolver/tools/executable/                (~140 .yaml files)
/home/user/mostlylucid.dse/code_evolver/tools/llm/                       (~50 .yaml files)
/home/user/mostlylucid.dse/code_evolver/tools/custom/                    (4 .yaml files)
/home/user/mostlylucid.dse/code_evolver/tools/index.json                 (Tool registry cache)
```

### Documentation
```
/home/user/mostlylucid.dse/code_evolver/MCP_README.md
/home/user/mostlylucid.dse/code_evolver/docs/MCP_INTEGRATION.md
/home/user/mostlylucid.dse/code_evolver/docs/MCP_SYSTEM_ANALYSIS.md       (Detailed analysis)
```

### Testing
```
/home/user/mostlylucid.dse/code_evolver/test_mcp_integration.py
```

---

## Quick Start

### 1. Connect to MCP Servers
```python
from src.config_manager import ConfigManager
from src.tools_manager import ToolsManager

# Load configuration with MCP servers
config = ConfigManager("config.mcp.yaml")
tools_manager = ToolsManager(config_manager=config)

# MCP tools are now available
```

### 2. Find MCP Tools
```python
# Find all MCP tools
mcp_tools = tools_manager.find_by_tags(["mcp"])

# Find tools from specific server
fetch_tools = tools_manager.find_by_tags(["mcp", "fetch"])

# Get tool by ID
tool = tools_manager.get_tool("mcp_fetch_fetch_url")
```

### 3. Call an MCP Tool
```python
# Execute tool
result = tool.implementation(url="https://example.com")
print(result)
```

### 4. Add New MCP Server
Edit `config.mcp.yaml`:
```yaml
mcp_servers:
  - name: my-server
    command: npx
    args: ["-y", "@my-org/server-package"]
    description: "My custom MCP server"
    tags: [custom, special]
    enabled: true
```

---

## Architecture Layers

### Layer 1: MCPClientManager
- Manages server connections
- Connection lifecycle
- Communication protocol

### Layer 2: MCPToolAdapter
- Converts MCP tools to system format
- Wraps async calls
- Extracts parameters

### Layer 3: ToolsManager
- Central registry
- Discovery and search
- RAG integration
- Version management

---

## Tool Type Reference

| Type | File Pattern | Example |
|------|---|---|
| executable | `tools/executable/*.yaml` | smart_faker.yaml |
| llm | `tools/llm/*.yaml` | code_optimizer.yaml |
| custom | `tools/custom/*.yaml` + Python class | git.yaml |
| openapi | `tools/openapi/*.yaml` | nmt_translator.yaml |
| mcp | `config.mcp.yaml` | fetch, memory, time |

---

## YAML Tool Template

### Executable Tool
```yaml
name: "Tool Name"
type: "executable"
description: "What it does"
executable:
  command: "python"
  args: ["{tool_dir}/script.py"]
  timeout: 60
tags: ["category"]
```

### LLM Tool
```yaml
name: "Tool Name"
type: "llm"
llm:
  model_key: "role"
  system_prompt: "..."
  temperature: 0.7
tags: ["category"]
```

### Custom Tool
```yaml
name: "Tool Name"
type: "custom"
custom:
  module: "src.module"
  class: "ClassName"
tags: ["category"]
```

### MCP Server
```yaml
mcp_servers:
  - name: server_name
    command: "npx"
    args: ["-y", "@org/package"]
    tags: [category]
    enabled: true
```

---

## Key Concepts

### Tool ID Naming
- Regular tools: `tool_name`
- MCP tools: `mcp_{server_name}_{tool_name}`
- Resources: `mcp_{server_name}_resource_{name}`

### Tool Discovery Methods
- **By ID**: `tools_manager.get_tool(tool_id)`
- **By Tags**: `tools_manager.find_by_tags(["tag1", "tag2"])`
- **By Type**: Filter `tools_manager.tools.values()`
- **Semantic**: `tools_manager.search("query", use_rag=True)`

### Tool Loading Pipeline
1. Index (cached tools)
2. Config (LLM models)
3. YAML Files (174 tools)
4. RAG Memory (learned tools)
5. MCP Servers (dynamic tools)

---

## Common Tasks

### List All Tools
```python
for tool_id, tool in tools_manager.tools.items():
    print(f"{tool.name}: {tool.description}")
```

### Find Tools by Server
```python
fetch_tools = [t for t in tools_manager.tools.values() 
               if 'fetch' in t.tags]
```

### Check Tool Parameters
```python
tool = tools_manager.get_tool("tool_id")
print(tool.parameters)
```

### Test MCP Integration
```bash
python test_mcp_integration.py --config config.mcp.yaml
```

---

## Official MCP Servers

| Server | Package | Status |
|--------|---------|--------|
| Fetch | `@modelcontextprotocol/server-fetch` | ✓ Official |
| Memory | `@modelcontextprotocol/server-memory` | ✓ Official |
| Time | `@modelcontextprotocol/server-time` | ✓ Official |
| Filesystem | `@modelcontextprotocol/server-filesystem` | ✓ Official |
| GitHub | `@modelcontextprotocol/server-github` | ✓ Community |
| Git | `@cyanheads/git-mcp-server` | ✓ Community |

Find more: https://github.com/TensorBlock/awesome-mcp-servers

---

## Code Examples

### Connect to All MCP Servers
```python
from src.mcp_client_manager import get_mcp_client_manager

manager = get_mcp_client_manager()
manager.load_from_config(config_data)
manager.connect_all_sync()
print(f"Connected: {manager.list_connected_servers()}")
```

### Load Tools from Specific Server
```python
from src.mcp_tool_adapter import get_mcp_tool_adapter

adapter = get_mcp_tool_adapter()
tools = adapter.load_tools_from_server_sync("fetch")
print(f"Loaded {len(tools)} tools from fetch server")
```

### Use Tool in Code
```python
tool = tools_manager.get_tool("mcp_fetch_fetch_url")
result = tool.implementation(url="https://example.com")
print(result)
```

---

## Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Tool Metadata
```python
tool = tools_manager.get_tool("tool_id")
print(f"Tags: {tool.tags}")
print(f"Type: {tool.tool_type}")
print(f"Metadata: {tool.metadata}")
```

### Verify MCP Connection
```python
manager = get_mcp_client_manager()
print(f"Servers: {manager.list_servers()}")
print(f"Connected: {manager.list_connected_servers()}")
```

---

## Resources

- **MCP Spec**: https://modelcontextprotocol.io/
- **Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Official Servers**: https://github.com/modelcontextprotocol/servers
- **Awesome MCP**: https://github.com/TensorBlock/awesome-mcp-servers
