# MCP Server Integration for Code Evolver

## 🚀 Quick Start

Code Evolver now supports MCP (Model Context Protocol) servers! Use any MCP-compatible tool as a native system tool.

### Installation

```bash
# Install MCP Python SDK (already done)
pip install mcp

# Install Node.js for official MCP servers
# Download from https://nodejs.org/
```

### Basic Usage

1. **Configure MCP servers** in your config file:

```yaml
mcp_servers:
  - name: fetch
    command: npx
    args: ["-y", "@modelcontextprotocol/server-fetch"]
    enabled: true
```

2. **Use the configuration**:

```bash
python chat_cli.py --config config.mcp.yaml
```

That's it! MCP tools are now available in your tool registry.

### Test the Integration

```bash
python test_mcp_integration.py --config config.mcp.yaml
```

## 📦 What's Included

### New Components

1. **MCPClientManager** (`src/mcp_client_manager.py`)
   - Manages connections to MCP servers
   - Handles server lifecycle
   - Provides async and sync interfaces

2. **MCPToolAdapter** (`src/mcp_tool_adapter.py`)
   - Converts MCP tools to system Tool objects
   - Wraps MCP tool invocations
   - Provides tool caching

3. **ToolsManager Integration**
   - Automatic MCP tool loading
   - Seamless tool discovery
   - Configuration-driven setup

### Configuration Files

- **config.mcp.yaml** - Example configuration with popular MCP servers
- **test_mcp_integration.py** - Test script to verify setup
- **docs/MCP_INTEGRATION.md** - Complete documentation

## 🌟 Available Public MCP Servers

### Official Servers (Anthropic)

| Server | Description | NPM Package |
|--------|-------------|-------------|
| **Fetch** | Web content fetching and conversion | `@modelcontextprotocol/server-fetch` |
| **Memory** | Persistent knowledge graph | `@modelcontextprotocol/server-memory` |
| **Time** | Time and timezone utilities | `@modelcontextprotocol/server-time` |
| **Filesystem** | Secure file operations | `@modelcontextprotocol/server-filesystem` |

### Community Servers

| Server | Description | NPM Package |
|--------|-------------|-------------|
| **Git** | Git repository operations | `@cyanheads/git-mcp-server` |
| **GitHub** | GitHub API access | `@modelcontextprotocol/server-github` |

**Find more**: https://github.com/TensorBlock/awesome-mcp-servers (7260+ servers!)

## 📖 Documentation

See `docs/MCP_INTEGRATION.md` for:
- Detailed architecture overview
- Configuration reference
- Security best practices
- Troubleshooting guide
- Advanced usage patterns

## 🎯 Examples

### Example 1: Web Content Fetching

```yaml
mcp_servers:
  - name: fetch
    command: npx
    args: ["-y", "@modelcontextprotocol/server-fetch"]
    description: "Fetch and convert web content"
    tags: [web, http, scraping]
    enabled: true
```

```python
# Tools are auto-loaded and available
fetch_tool = tools_manager.get_tool("mcp_fetch_fetch_url")
content = fetch_tool.implementation(url="https://example.com")
```

### Example 2: Knowledge Graph Memory

```yaml
mcp_servers:
  - name: memory
    command: npx
    args: ["-y", "@modelcontextprotocol/server-memory"]
    description: "Persistent knowledge graph"
    tags: [memory, knowledge-graph]
    enabled: true
```

### Example 3: Filesystem Access (Secure)

```yaml
mcp_servers:
  - name: filesystem
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/tmp/mcp_workspace"  # Limited to specific directory
    enabled: false  # Enable only when needed
```

## 🔒 Security

**Important security notes:**

1. **Filesystem Server**: Only grant access to specific, limited directories
2. **Network Access**: Fetch server can access any URL - use with caution
3. **API Keys**: Always use environment variables, never hardcode secrets
4. **Enable Selectively**: Only enable servers you're actively using

## 🛠️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Code Evolver                       │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         ToolsManager                         │  │
│  │  (Unified tool registry)                     │  │
│  └──────────────┬───────────────────────────────┘  │
│                 │                                   │
│  ┌──────────────▼───────────────────────────────┐  │
│  │      MCPToolAdapter                          │  │
│  │  (Converts MCP tools → System tools)         │  │
│  └──────────────┬───────────────────────────────┘  │
│                 │                                   │
│  ┌──────────────▼───────────────────────────────┐  │
│  │      MCPClientManager                        │  │
│  │  (Manages server connections)                │  │
│  └──────────────┬───────────────────────────────┘  │
└─────────────────┼───────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
    ┌────▼────┐      ┌────▼────┐
    │  Fetch  │      │ Memory  │  ... (More MCP Servers)
    │  Server │      │ Server  │
    └─────────┘      └─────────┘
```

## 🚧 Troubleshooting

### Server won't start
```bash
# Check Node.js is installed
node --version

# Try installing server globally
npm install -g @modelcontextprotocol/server-fetch
```

### No tools loaded
1. Check `enabled: true` in config
2. Verify Node.js is installed
3. Check logs for connection errors

### Tool fails when invoked
1. Verify required parameters
2. Check server is still connected
3. Review server-specific requirements (API keys, etc.)

## 📚 Learn More

- **MCP Protocol**: https://modelcontextprotocol.io/
- **Official Servers**: https://github.com/modelcontextprotocol/servers
- **Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Awesome MCP Servers**: https://github.com/TensorBlock/awesome-mcp-servers

## 🎉 Benefits

✅ **Composable**: Mix and match tools from different MCP servers
✅ **Standardized**: Use any MCP-compatible server
✅ **Automatic**: Tools load automatically from configuration
✅ **Seamless**: MCP tools work like any other system tool
✅ **Extensible**: Easy to add new servers or create custom ones

---

**Ready to use MCP servers?** Check out `config.mcp.yaml` and run `python test_mcp_integration.py`!
