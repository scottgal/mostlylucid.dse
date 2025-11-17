# MCP (Model Context Protocol) Integration

## Overview

mostlylucid DiSE now supports the Model Context Protocol (MCP), an open-source standard for connecting AI systems to external tools, data sources, and services. This integration allows you to seamlessly use any MCP-compatible server as tools within the mostlylucid DiSE system.

## What is MCP?

The Model Context Protocol (MCP) is an open standard introduced by Anthropic that standardizes how AI systems integrate with external tools and data sources. MCP servers expose three core primitives:

- **Tools**: Functions that the AI can invoke (similar to function calling)
- **Resources**: Data sources like files and database records
- **Prompts**: Pre-defined templates for LLM interactions

## Architecture

The MCP integration in mostlylucid DiSE consists of three main components:

### 1. MCPClientManager (`src/mcp_client_manager.py`)

Manages connections to multiple MCP servers:
- Handles server lifecycle (connect/disconnect)
- Maintains active connections
- Provides access to server capabilities
- Supports both async and sync operations

### 2. MCPToolAdapter (`src/mcp_tool_adapter.py`)

Converts MCP tools to system Tool objects:
- Discovers tools from connected MCP servers
- Wraps MCP tool calls in system-compatible functions
- Handles resource access as tools
- Provides caching for performance

### 3. ToolsManager Integration

The existing ToolsManager automatically loads MCP tools during initialization:
- Reads MCP server configurations
- Connects to enabled servers
- Registers discovered tools
- Makes them available system-wide

## Installation

### Prerequisites

1. **Python MCP SDK**: Already installed with the MCP integration
   ```bash
   pip install mcp
   ```

2. **Node.js**: Required for most official MCP servers
   ```bash
   # Check if Node.js is installed
   node --version

   # If not installed, download from https://nodejs.org/
   ```

### Optional: Install MCP Servers Globally

While servers can run via `npx`, you can install them globally for faster startup:

```bash
npm install -g @modelcontextprotocol/server-fetch
npm install -g @modelcontextprotocol/server-memory
npm install -g @modelcontextprotocol/server-time
npm install -g @modelcontextprotocol/server-filesystem
```

## Configuration

### Basic Configuration

Add an `mcp_servers` section to your configuration file:

```yaml
mcp_servers:
  - name: fetch
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-fetch"
    description: "Fetch and convert web content"
    tags:
      - web
      - http
    enabled: true
```

### Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the server |
| `command` | string | Yes | Command to start the server (e.g., `npx`, `python`, `node`) |
| `args` | list | Yes | Arguments passed to the command |
| `env` | dict | No | Environment variables for the server |
| `description` | string | No | Human-readable description |
| `tags` | list | No | Tags for tool discovery and categorization |
| `enabled` | boolean | No | Whether to load this server (default: true) |

### Example Configuration File

See `config.mcp.yaml` for a complete example with multiple servers configured.

## Available Public MCP Servers

### Official Servers (Anthropic)

1. **Fetch Server** - Web content fetching and conversion
   ```yaml
   - name: fetch
     command: npx
     args: ["-y", "@modelcontextprotocol/server-fetch"]
     enabled: true
   ```

2. **Memory Server** - Persistent knowledge graph
   ```yaml
   - name: memory
     command: npx
     args: ["-y", "@modelcontextprotocol/server-memory"]
     enabled: true
   ```

3. **Time Server** - Time and timezone utilities
   ```yaml
   - name: time
     command: npx
     args: ["-y", "@modelcontextprotocol/server-time"]
     enabled: true
   ```

4. **Filesystem Server** - Secure file operations
   ```yaml
   - name: filesystem
     command: npx
     args:
       - "-y"
       - "@modelcontextprotocol/server-filesystem"
       - "/path/to/allowed/directory"
     enabled: false  # Security: Enable only when needed
   ```

### Community Servers

1. **Git Server** - Git repository operations
   ```yaml
   - name: git
     command: npx
     args: ["-y", "@cyanheads/git-mcp-server"]
     enabled: false
   ```

2. **GitHub Server** - GitHub API access
   ```yaml
   - name: github
     command: npx
     args: ["-y", "@modelcontextprotocol/server-github"]
     env:
       GITHUB_TOKEN: "${GITHUB_TOKEN}"
     enabled: false
   ```

For more servers, visit:
- Official repository: https://github.com/modelcontextprotocol/servers
- Community list: https://github.com/TensorBlock/awesome-mcp-servers

## Usage

### Automatic Loading

When you initialize ToolsManager with a config that includes MCP servers, they're automatically loaded:

```python
from src.config_manager import ConfigManager
from src.tools_manager import ToolsManager

config = ConfigManager("config.mcp.yaml")
tools_manager = ToolsManager(config_manager=config)

# MCP tools are now available in tools_manager.tools
```

### Manual Usage

You can also use the MCP components directly:

```python
from src.mcp_client_manager import get_mcp_client_manager, MCPServerConfig
from src.mcp_tool_adapter import get_mcp_tool_adapter

# Configure a server
config = MCPServerConfig(
    name="fetch",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-fetch"]
)

# Connect
manager = get_mcp_client_manager()
manager.add_server(config)
manager.connect_all_sync()

# Load tools
adapter = get_mcp_tool_adapter()
tools = adapter.load_all_tools_sync()

# Use tools
for tool in tools:
    print(f"Tool: {tool.name}")
    print(f"Description: {tool.description}")
```

### Finding MCP Tools

MCP tools are tagged with `'mcp'` and the server name:

```python
# Find all MCP tools
mcp_tools = tools_manager.find_by_tags(["mcp"])

# Find tools from specific server
fetch_tools = tools_manager.find_by_tags(["mcp", "fetch"])

# Search semantically (if RAG is enabled)
web_tools = tools_manager.search("fetch web content", use_rag=True)
```

### Invoking MCP Tools

MCP tools work like any other tool in the system:

```python
# Get tool by ID
tool = tools_manager.get_tool("mcp_fetch_fetch_url")

# Invoke it
result = tool.implementation(url="https://example.com")
```

## Testing

Run the test script to verify your MCP setup:

```bash
python test_mcp_integration.py --config config.mcp.yaml
```

The test script will:
1. Load your MCP configuration
2. Connect to enabled servers
3. Discover and list available tools
4. Test integration with ToolsManager
5. Clean up connections

## Security Considerations

### Filesystem Access

The filesystem server can access your local files. Always:
- Specify exact allowed directories
- Use the most restrictive path possible
- Keep it disabled unless actively needed
- Never expose sensitive directories

```yaml
# ✓ Good - specific, limited path
args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp/mcp_workspace"]

# ✗ Bad - overly broad access
args: ["-y", "@modelcontextprotocol/server-filesystem", "/"]
```

### Network Access

The fetch server can access any URL:
- Be cautious when fetching untrusted URLs
- Consider network policies and firewall rules
- Monitor for unexpected network activity

### API Keys and Secrets

For servers requiring authentication:
- Use environment variables, not hardcoded values
- Use `.env` files (never commit them to git)
- Rotate keys regularly

```yaml
# ✓ Good - uses environment variable
env:
  GITHUB_TOKEN: "${GITHUB_TOKEN}"

# ✗ Bad - hardcoded secret
env:
  GITHUB_TOKEN: "ghp_1234567890abcdef"
```

## Troubleshooting

### Server Won't Start

**Problem**: MCP server fails to connect

**Solutions**:
1. Check Node.js is installed: `node --version`
2. Try installing server globally: `npm install -g @modelcontextprotocol/server-fetch`
3. Check server logs for error messages
4. Verify command and args are correct

### No Tools Loaded

**Problem**: MCP servers connect but no tools appear

**Solutions**:
1. Check server is enabled: `enabled: true`
2. Verify server is actually connected
3. Check logs for connection errors
4. Try restarting the application

### Tool Invocation Fails

**Problem**: Tool exists but fails when called

**Solutions**:
1. Check required parameters are provided
2. Verify server is still connected
3. Check server-specific requirements (e.g., API keys)
4. Review server logs for errors

### Permission Denied

**Problem**: Filesystem server can't access files

**Solutions**:
1. Verify the allowed path in configuration
2. Check file/directory permissions
3. Ensure path exists before starting server
4. Try absolute path instead of relative

## Advanced Topics

### Custom MCP Servers

You can create your own MCP servers using the official SDKs:
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- TypeScript SDK: https://github.com/modelcontextprotocol/typescript-sdk

Once created, add them to your configuration:

```yaml
- name: my-custom-server
  command: python
  args: ["path/to/my_server.py"]
  description: "My custom MCP server"
  enabled: true
```

### Environment Variables

Pass environment variables to servers:

```yaml
- name: api-server
  command: npx
  args: ["-y", "@company/api-server"]
  env:
    API_KEY: "${API_KEY}"
    API_URL: "https://api.example.com"
  enabled: true
```

### Multiple Instances

Run multiple instances of the same server with different configs:

```yaml
- name: filesystem-workspace
  command: npx
  args: ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
  enabled: true

- name: filesystem-home
  command: npx
  args: ["-y", "@modelcontextprotocol/server-filesystem", "~"]
  enabled: false
```

## Performance Tips

1. **Global Installation**: Install frequently-used servers globally to avoid download delays
2. **Selective Loading**: Only enable servers you're actively using
3. **Connection Pooling**: The manager reuses connections efficiently
4. **Caching**: Tools are cached after first discovery

## Future Enhancements

Planned improvements:
- [ ] Automatic server discovery
- [ ] Health monitoring and auto-reconnect
- [ ] Server metrics and performance tracking
- [ ] MCP resource browsing UI
- [ ] Prompt template integration
- [ ] Server marketplace integration

## Resources

- **MCP Specification**: https://modelcontextprotocol.io/
- **Official Servers**: https://github.com/modelcontextprotocol/servers
- **Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Awesome MCP Servers**: https://github.com/TensorBlock/awesome-mcp-servers

## Support

For issues with:
- **MCP Integration**: File an issue in this repository
- **Official Servers**: https://github.com/modelcontextprotocol/servers/issues
- **MCP Protocol**: https://github.com/modelcontextprotocol/specification/issues
