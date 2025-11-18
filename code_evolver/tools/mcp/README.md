# MCP Tools Directory

This directory contains YAML configuration files for Model Context Protocol (MCP) tools. MCP is a standardized protocol for connecting AI systems to external data sources and tools.

## What is MCP?

The Model Context Protocol (MCP) is a protocol that enables:
- **Standardized tool integration** - Connect to any MCP-compatible server
- **Automatic tool discovery** - Tools are discovered from servers automatically
- **Type-safe interfaces** - JSON schemas define inputs/outputs
- **Multiple backends** - npm packages, Python servers, custom endpoints

## Quick Start

### 1. Using Existing MCP Tools

The following MCP tools are included by default:

| Tool | Description | Status | Auto-Start |
|------|-------------|--------|------------|
| **GitHub MCP** | GitHub API integration | Enabled | Yes |
| **Memory MCP** | Knowledge graph memory | Enabled | Yes |
| **Fetch MCP** | Web content fetching | Enabled | Yes |
| **Time MCP** | Time/timezone utilities | Enabled | Yes |
| **Filesystem MCP** | File operations | Disabled | No |

### 2. Creating a New MCP Tool

Copy the template and customize:

```bash
cd code_evolver/tools/mcp
cp _template.yaml my_new_tool_mcp.yaml
```

Edit the file and fill in:
- `name`: Display name for your tool
- `mcp.server_name`: Unique identifier
- `mcp.command` and `mcp.args`: How to start the server
- `capabilities`: List of tools the server provides
- `tags`: Discovery tags
- `examples`: Usage examples

### 3. Pointing at Custom Endpoints

For HTTP-based MCP servers or custom endpoints:

```yaml
mcp:
  server_name: "custom_api"
  command: "python"
  args:
    - "-m"
    - "your.custom.mcp_server"
    - "--endpoint"
    - "https://your-api.com/mcp"
  env:
    API_URL: "https://your-api.com"
    API_KEY: "${YOUR_API_KEY}"
```

For local development:

```yaml
mcp:
  server_name: "local_dev"
  command: "node"
  args:
    - "/path/to/your/mcp-server/index.js"
  env:
    DEBUG: "true"
```

## MCP Tool Configuration Reference

### Basic Structure

```yaml
name: "Tool Name MCP"
type: "mcp"  # Must be "mcp"
description: "What this tool does"

cost_tier: "free"     # free, low, medium, high
speed_tier: "fast"    # instant, fast, medium, slow
quality_tier: "excellent"  # good, excellent, premium

mcp:
  server_name: "unique_id"
  command: "npx"  # or python, node, etc.
  args:
    - "-y"
    - "@modelcontextprotocol/server-name"
  env:  # Optional environment variables
    API_KEY: "${YOUR_API_KEY}"
  enabled: true  # Enable/disable this server
  auto_start: true  # Auto-start on tool manager init

capabilities:
  - name: "tool_function_1"
    description: "What it does"

tags:
  - mcp
  - mcp-tool
  - your-domain-tags
```

### Environment Variables

Set environment variables for MCP servers:

```bash
# In your shell
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export OPENAI_API_KEY="sk-xxxxxxxxxxxx"

# Or in .env file
echo "GITHUB_TOKEN=ghp_xxxxxxxxxxxx" >> .env
```

Reference them in your YAML:

```yaml
mcp:
  env:
    GITHUB_TOKEN: "${GITHUB_TOKEN}"
```

## Finding MCP Servers

### Official MCP Servers (npm)

```bash
# Filesystem operations
npx -y @modelcontextprotocol/server-filesystem

# GitHub integration
npx -y @modelcontextprotocol/server-github

# Web fetching
npx -y @modelcontextprotocol/server-fetch

# Memory/knowledge graph
npx -y @modelcontextprotocol/server-memory

# Time utilities
npx -y @modelcontextprotocol/server-time
```

### Community Servers

- **npm**: https://www.npmjs.com/search?q=mcp-server
- **GitHub**: https://github.com/topics/mcp-server
- **MCP Registry**: https://github.com/modelcontextprotocol/servers

### Building Custom Servers

- **Python**: Use `mcp` package
- **Node.js**: Use `@modelcontextprotocol/sdk`
- **Other languages**: Implement MCP protocol (stdio-based)

## How It Works

1. **Tool Loading**: When DiSE starts, it scans this directory for `*.yaml` files
2. **Registration**: Each enabled MCP tool registers its server configuration
3. **Connection**: MCP servers are started and connected via stdio
4. **Tool Discovery**: Tools are discovered from connected servers
5. **Invocation**: Tools can be called like any other DiSE tool

## Workflow Integration

MCP tools integrate seamlessly with DiSE workflows:

```python
from node_runtime import call_mcp_tool
import json

# Call an MCP tool
result = call_mcp_tool("github", "create_issue", json.dumps({
    "owner": "user",
    "repo": "project",
    "title": "Bug found",
    "body": "Description here"
}))

data = json.loads(result)
```

## Tags and Discovery

Use tags to make your MCP tools discoverable:

- `mcp-tool` - Always include this tag
- Domain tags: `github`, `api`, `web`, `data`, etc.
- Capability tags: `search`, `fetch`, `storage`, etc.

## Best Practices

1. **Security**: Never commit API keys - use environment variables
2. **Naming**: Use descriptive `server_name` values (lowercase, underscores)
3. **Documentation**: Provide clear examples in the YAML
4. **Testing**: Test your MCP server standalone before integrating
5. **Versioning**: Use the `version` field to track changes
6. **Dependencies**: Document required npm packages or Python modules

## Troubleshooting

### Server Won't Start

- Check that `command` is correct (`npx`, `node`, `python`, etc.)
- Verify npm package is available: `npm search <package-name>`
- Check environment variables are set
- Look at logs in DiSE output

### Tools Not Appearing

- Verify `enabled: true` in the YAML
- Check that the server started successfully
- Ensure `type: "mcp"` is set correctly
- Rebuild the tools index: `python -m code_evolver.src.tools_manager --rebuild-index`

### Authentication Errors

- Verify environment variables are set: `echo $GITHUB_TOKEN`
- Check `.env` file exists and is loaded
- Ensure token format is correct (e.g., `ghp_` prefix for GitHub)

## Examples

### Example 1: GitHub Integration

```yaml
name: "GitHub MCP"
type: "mcp"
mcp:
  server_name: "github"
  command: "npx"
  args: ["-y", "@modelcontextprotocol/server-github"]
  env:
    GITHUB_TOKEN: "${GITHUB_TOKEN}"
```

### Example 2: Custom HTTP Endpoint

```yaml
name: "Custom API MCP"
type: "mcp"
mcp:
  server_name: "custom_api"
  command: "python"
  args:
    - "-m"
    - "my_mcp_adapter"
    - "--url"
    - "https://api.example.com"
  env:
    API_KEY: "${CUSTOM_API_KEY}"
```

### Example 3: Local Development Server

```yaml
name: "Local Dev MCP"
type: "mcp"
mcp:
  server_name: "local_dev"
  command: "node"
  args: ["./my-mcp-server/index.js"]
  env:
    DEBUG: "true"
    PORT: "3000"
  enabled: false  # Disabled by default
```

## Additional Resources

- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **MCP SDK**: https://github.com/modelcontextprotocol/typescript-sdk
- **Python MCP**: https://github.com/modelcontextprotocol/python-sdk
- **Example Servers**: https://github.com/modelcontextprotocol/servers

## Contributing

To add a new MCP tool to this repository:

1. Create a YAML file in this directory
2. Follow the template structure
3. Document all capabilities and provide examples
4. Test thoroughly
5. Submit a pull request

## License

MCP tools configurations are part of the mostlylucid DiSE project and follow the same license.
