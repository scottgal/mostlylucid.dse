# MCP System Implementation Analysis - mostlylucid DiSE

## Overview

The mostlylucid DiSE codebase implements comprehensive support for MCP (Model Context Protocol) servers, enabling seamless integration of external tools and services. The system is built with three core components that handle connection management, tool discovery, and tool adaptation.

---

## 1. Current MCP Implementation Architecture

### Core Components

#### 1.1 MCPClientManager (`src/mcp_client_manager.py`)
**Purpose**: Manages lifecycle and connections to MCP servers

**Key Classes**:
- **MCPServerConfig** (dataclass):
  - `name`: Unique identifier for the server
  - `command`: Command to start the server (e.g., "npx", "python")
  - `args`: Arguments passed to the command
  - `env`: Optional environment variables
  - `description`: Human-readable description
  - `tags`: Tags for discovery and categorization
  - `enabled`: Whether to load this server (default: true)

- **MCPServerConnection**:
  - Manages active connection to a single MCP server
  - Handles server lifecycle (connect/disconnect)
  - Caches tools, resources, and prompts
  - Provides async/sync interface for tool calls
  - Methods:
    - `connect()`: Establish connection using stdio_client
    - `disconnect()`: Close connection and cleanup
    - `list_tools()`: List available tools
    - `list_resources()`: List available resources
    - `list_prompts()`: List available prompts
    - `call_tool(tool_name, arguments)`: Execute a tool

- **MCPClientManager**:
  - Manages multiple MCP server connections
  - Global singleton instance via `get_mcp_client_manager()`
  - Key methods:
    - `add_server(config)`: Add server configuration
    - `connect_all_sync()`: Connect to all enabled servers
    - `disconnect_all_sync()`: Disconnect from all servers
    - `list_servers()`: List all configured servers
    - `list_connected_servers()`: List connected servers
    - `load_from_config(config_data)`: Load servers from config dict

**Connection Flow**:
```
MCPServerConfig → MCPServerConnection.connect() 
  → StdioServerParameters 
  → stdio_client 
  → ClientSession
  → initialized & cached
```

#### 1.2 MCPToolAdapter (`src/mcp_tool_adapter.py`)
**Purpose**: Converts MCP tools/resources to system Tool objects

**Key Methods**:
- `_mcp_tool_to_system_tool()`: 
  - Extracts tool metadata from MCP tool
  - Wraps MCP tool invocation in system-compatible function
  - Creates sync wrapper for async MCP calls
  - Extracts parameters from JSON schema
  - Sets tags: ['mcp', server_name] + server tags

- `_mcp_resource_to_system_tool()`:
  - Converts MCP resources to Tool objects
  - Handles resource reading
  - Creates tags: ['mcp', 'resource', server_name]

- `load_tools_from_server(server_name)`:
  - Loads all tools and resources from a specific server
  - Returns List[Tool]
  - Caches tools for performance

- `load_all_tools_sync()`:
  - Loads tools from all connected servers
  - Returns flat list of all Tool objects

**Tool Conversion Details**:
```python
MCP Tool:
{
  name: str,
  description: str,
  inputSchema: JSON Schema
}
↓
System Tool:
{
  tool_id: f"mcp_{server_name}_{tool_name}",
  name: f"{server_name}_{tool_name}",
  tool_type: ToolType.CUSTOM,
  tags: ['mcp', server_name, ...server_tags],
  implementation: sync_wrapper(async_mcp_call),
  parameters: {extracted from inputSchema},
  metadata: {mcp_server, mcp_tool_name, source: 'mcp'}
}
```

#### 1.3 ToolsManager Integration (`src/tools_manager.py`)
**Purpose**: Registry for all tools, including MCP tools

**MCP Integration Flow**:
1. ToolsManager.__init__() calls `_load_mcp_tools()` (line 370)
2. `_load_mcp_tools()` (lines 889-931):
   - Gets config from config_manager
   - Checks for 'mcp_servers' in config
   - Gets MCPClientManager singleton
   - Loads config into manager: `mcp_manager.load_from_config(config_data)`
   - Connects: `mcp_manager.connect_all_sync()`
   - Gets MCPToolAdapter singleton
   - Loads tools: `mcp_adapter.load_all_tools_sync()`
   - Registers tools in self.tools registry
   - Logs success/errors

**Tool Registration**:
- MCP tools stored with prefix: `mcp_` in tool_id
- Can be found by tag: `find_by_tags(['mcp'])`
- Can find by server: `find_by_tags(['mcp', server_name])`
- Discoverable via RAG if enabled

---

## 2. Tool Configuration System

### 2.1 YAML Tool Definitions

Tools are defined in YAML files organized by type:

**Directory Structure** (`code_evolver/tools/`):
```
tools/
├── executable/      - 140+ executable tools (shell commands, Python scripts)
├── llm/            - 50+ LLM-based tools
├── custom/         - 4 custom tools (git, github, ask_user, http_server)
├── openapi/        - OpenAPI/REST API tools
├── fixer/          - Bug fixing tools
├── perf/           - Performance testing tools
├── optimization/   - Code optimization tools
└── debug/          - Debug/validation tools
```

**Total**: 174 YAML tool files

### 2.2 YAML Tool Structure

#### Example 1: Executable Tool (smart_faker.yaml)
```yaml
name: "Smart Faker"
type: "executable"
description: "Intelligent fake data generator..."

executable:
  command: "python"
  args: ["{tool_dir}/smart_faker.py"]
  stdin_mode: true
  timeout: 60

input_schema:
  prompt:
    type: string
    description: "Plain English description..."
    required: true
  count:
    type: integer
    default: 1

output_schema:
  type: object
  properties:
    success:
      type: boolean
    data:
      description: "Generated data..."

tags: ["testing", "data-generation", "faker", "llm"]
cost_tier: "low"
speed_tier: "fast"
quality_tier: "excellent"
priority: 80

examples:
  - description: "Generate user data"
    input:
      prompt: "I need user data..."
    output:
      success: true
```

#### Example 2: LLM Tool (code_optimizer.yaml)
```yaml
name: "Code Optimizer"
type: "llm"
version: "1.0.0"
description: "Comprehensive code optimization..."

llm:
  model_key: "escalation"
  endpoint: null
  system_prompt: |
    You are an expert code optimizer...
  temperature: 0.4

tags: ["optimization", "performance", "refactoring"]
constraints:
  max_memory_mb: 2048
  max_execution_time_ms: 600000

metadata:
  speed_tier: "slow"
  cost_tier: "variable"

workflow:
  steps:
    - id: "1_profile_baseline"
      action: "profile_code"
      tool: "performance_profiler"
      output: "baseline_profile"
    # ... more steps
```

#### Example 3: Custom Tool (git.yaml)
```yaml
name: "Git"
type: "custom"
description: "Powerful yet safe Git integration..."

custom:
  module: "src.git_tool"
  class: "GitTool"
  config:
    safe_mode: true
    require_confirmation_for_destructive: true

input_schema:
  action:
    type: string
    enum: ["status", "log", "diff", "clone", "push", "pull"]
    required: true
  # ... more parameters

tags: ["git", "version-control", "vcs"]
```

### 2.3 MCP Configuration (config.mcp.yaml)

```yaml
mcp_servers:
  - name: fetch
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-fetch"
    description: "Fetch and convert web content"
    tags: [web, http, scraping]
    enabled: true

  - name: memory
    command: npx
    args: ["-y", "@modelcontextprotocol/server-memory"]
    description: "Knowledge graph-based memory"
    tags: [memory, knowledge-graph]
    enabled: true

  - name: filesystem
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp/mcp_workspace"]
    enabled: false  # Disabled for security

  # Custom server example:
  - name: my-custom
    command: python
    args: ["path/to/my_server.py"]
    env:
      API_KEY: "${API_KEY}"
    enabled: true
```

---

## 3. Tool Loading Pipeline

### 3.1 Complete Tool Loading Sequence

```
ToolsManager.__init__()
├── _load_tools()                    # Load from tools/index.json
├── _load_tools_from_config()        # Load from config.yaml (LLM models)
├── _load_tools_from_yaml_files()    # Load from YAML files (174 files)
│   ├── Scan tools/**/*.yaml
│   ├── Parse each YAML
│   ├── Calculate hash for versioning
│   ├── Handle version bumping
│   └── Register in self.tools
├── _load_tools_from_rag()           # Load from RAG memory
├── _index_tools_in_rag()            # Index for semantic search
└── _load_mcp_tools()                # Load from MCP servers
    ├── mcp_manager.load_from_config()
    ├── mcp_manager.connect_all_sync()
    ├── mcp_adapter.load_all_tools_sync()
    └── Register tools in self.tools
```

### 3.2 Tool Loading Sources Priority

1. **Index** (index.json) - cached tools
2. **Config** - LLM model definitions
3. **YAML Files** - 174 tool definitions
4. **RAG Memory** - learned tools
5. **MCP Servers** - dynamic external tools

---

## 4. Configuration Files

### 4.1 Available Config Files
```
config.anthropic.yaml           - Anthropic Claude setup
config.local.yaml               - Local Ollama setup
config.lmstudio.minimal.yaml    - LM Studio setup
config.mcp.yaml                 - MCP servers configuration
config.openai.yaml              - OpenAI API setup
config.azure.yaml               - Azure OpenAI setup
config.unified.yaml             - Multi-backend config
config.yaml                     - Default configuration
```

### 4.2 Config Structure

**MCP Configuration Section**:
```yaml
mcp_servers:
  - name: string           # Unique identifier
    command: string        # Executable (npx, python, etc.)
    args: [strings]        # Arguments to command
    env: dict             # Optional environment variables
    description: string    # Human-readable description
    tags: [strings]        # Tags for discovery
    enabled: bool         # Whether to connect
```

**Tool Resolution**:
```yaml
llm:
  models:
    model_name:
      name: string
      backend: string     # ollama, anthropic, openai, azure
      context_window: int
      cost: string       # low, medium, high
      speed: string      # fast, medium, slow
      quality: string    # good, excellent, poor
      timeout: int

  roles:
    overseer:
      model: model_name
    generator:
      model: model_name
    # ... more roles
```

---

## 5. How Tools Are Currently Defined and Loaded

### 5.1 Tool Definition Methods

#### A. YAML-Based Tools
**Files**: `tools/**/*.yaml` (174 total)

**Loading**: 
1. Globbing: `tools_path.glob("**/*.yaml")`
2. Parsing: `yaml.safe_load(file)`
3. Hash calculation: detect changes
4. Version management: semantic versioning
5. Registration: Tool() object creation

**Versioning**:
```python
# Hash of tool definition
new_hash = calculate_tool_hash(tool_def)

# If hash changed, bump version
if old_hash != new_hash:
    version = bump_version(old_version, change_type)
    # Major, minor, or patch
```

#### B. Python-Implemented Tools
**Files**: `tools/executable/**/*.py`, `src/git_tool.py`, etc.

**Loading**:
```yaml
custom:
  module: "src.module_name"
  class: "ClassName"
  config:
    key: value
```

Loaded via importlib at runtime.

#### C. LLM-Based Tools
**Files**: `tools/llm/**/*.yaml` (50+ tools)

**Structure**:
```yaml
name: "Tool Name"
type: "llm"
llm:
  model_key: "overseer"  # Role reference
  system_prompt: "..."
  temperature: 0.7
tags: ["tag1", "tag2"]
```

**Invocation** via `invoke_llm_tool()` in ToolsManager

#### D. OpenAPI Tools
**File**: `tools/openapi/nmt_translator.yaml`

**Structure**:
```yaml
type: "openapi"
openapi:
  spec_path: "path/to/spec.yaml"
  base_url_override: "url"
  auth_config:
    type: "bearer"
    token: "${API_TOKEN}"
```

Handled via OpenAPITool class

#### E. MCP Tools
**Configuration**: `config.mcp.yaml`

**Definition**:
```yaml
mcp_servers:
  - name: fetch
    command: npx
    args: ["-y", "@modelcontextprotocol/server-fetch"]
```

**Loading**:
1. Parse config → MCPServerConfig
2. Connect → MCPServerConnection
3. List tools → MCP tools API
4. Adapt → MCPToolAdapter
5. Register → ToolsManager

---

## 6. Tool Registry and Discovery

### 6.1 In-Memory Registry
```python
ToolsManager.tools: Dict[str, Tool]
```

Tool object structure:
```python
class Tool:
    tool_id: str              # Unique ID
    name: str                 # Display name
    tool_type: ToolType       # ENUM: function, llm, workflow, custom, etc.
    description: str
    tags: List[str]           # For categorization and search
    implementation: Any       # Function, code, or config
    parameters: Dict[str, Any]
    metadata: Dict[str, Any]
    constraints: Dict[str, Any]
    version: str              # Semantic versioning
    definition_hash: str      # Change detection
```

### 6.2 Tool Discovery Methods

**By ID**:
```python
tool = tools_manager.get_tool("tool_id")
```

**By Tags**:
```python
tools = tools_manager.find_by_tags(["mcp", "fetch"])
```

**By Type**:
```python
tools = [t for t in tools_manager.tools.values() 
         if t.tool_type == ToolType.EXECUTABLE]
```

**Semantic Search** (if RAG enabled):
```python
tools = tools_manager.search("fetch web content", use_rag=True)
```

### 6.3 Tool Index Storage

**File**: `tools/index.json` (515KB, ~174 tools)

**Structure**:
```json
{
  "tool_id": {
    "tool_id": "tool_id",
    "name": "Tool Name",
    "tool_type": "executable",
    "description": "...",
    "tags": ["tag1", "tag2"],
    "parameters": {},
    "metadata": {
      "from_yaml": true,
      "yaml_file": "executable/tool.yaml",
      "version": "1.0.0",
      "definition_hash": "sha256..."
    }
  }
}
```

---

## 7. Integration Points

### 7.1 With ConfigManager
```python
config_manager = ConfigManager("config.mcp.yaml")
tools_manager = ToolsManager(config_manager=config_manager)
# MCP servers from config automatically loaded
```

### 7.2 With RAG Memory
```python
tools_manager = ToolsManager(
    config_manager=config_manager,
    rag_memory=rag_memory
)
# Tools indexed for semantic search
```

### 7.3 With OllamaClient
```python
tools_manager = ToolsManager(
    ollama_client=ollama_client
)
# LLM tools can be invoked
```

---

## 8. MCP Server Communication Flow

### 8.1 Connection Sequence

```
1. Config → MCPServerConfig
2. MCPServerConnection.__init__(config)
3. connection.connect()
   a. StdioServerParameters(command, args, env)
   b. stdio_client(params)
   c. ClientSession(read_stream, write_stream)
   d. session.initialize()
4. is_connected = True
```

### 8.2 Tool Discovery Sequence

```
1. server.list_tools()
   → await session.list_tools()
   → MCP protocol call
   → result.tools array

2. server.list_resources()
   → await session.list_resources()
   → result.resources array

3. MCPToolAdapter._mcp_tool_to_system_tool()
   → Extract: name, description, inputSchema
   → Create sync wrapper
   → Create System Tool object
```

### 8.3 Tool Invocation Sequence

```
1. user calls: tool.implementation(param1=value1, ...)
2. sync_wrapper(param1=value1, ...)
3. asyncio_loop.run_until_complete(mcp_tool_implementation(...))
4. server.call_tool(tool_name, arguments={...})
5. await session.call_tool(tool_name, arguments)
6. return result.content[0].text
```

---

## 9. Template and Configuration Systems

### 9.1 Prompt Templates

**System Prompts** (in LLM tools):
```yaml
llm:
  system_prompt: |
    You are an expert code optimizer...
    
    PHASE 1: ANALYSIS
    1. Profile current code
    2. Identify bottlenecks
    
    OUTPUT FORMAT:
    ```markdown
    ## Optimization Report
    ...
    ```
```

**Prompt Templates** (for parameterization):
```python
tool.metadata.get("prompt_template")
# Format with variables:
prompt = template.format(prompt=prompt, **template_vars)
```

### 9.2 Workflow Specifications

**Embedded in YAML** (code_optimizer.yaml example):
```yaml
workflow:
  steps:
    - id: "1_profile_baseline"
      action: "profile_code"
      tool: "performance_profiler"
      output: "baseline_profile"
    
    - id: "2_analyze_bottlenecks"
      action: "analyze"
      code: |
        # Python or pseudocode
        if bottleneck > threshold:
            level = "cloud"
    
    - id: "5_update_tests"
      depends_on: ["1_profile_baseline"]
```

### 9.3 Configuration Templates

**Tool Specification Templates**:
```yaml
# Executable tool template
name: "Tool Name"
type: "executable"
executable:
  command: "program"
  args: ["{tool_dir}/script.py"]
tags: ["category"]

# LLM tool template
name: "Tool Name"
type: "llm"
llm:
  model_key: "role_name"
  system_prompt: "..."

# Custom tool template
name: "Tool Name"
type: "custom"
custom:
  module: "src.module"
  class: "ClassName"
```

---

## 10. Key Files and Their Roles

| File | Lines | Purpose |
|------|-------|---------|
| `src/mcp_client_manager.py` | 314 | MCP server lifecycle management |
| `src/mcp_tool_adapter.py` | 288 | Convert MCP tools to system Tools |
| `src/tools_manager.py` | 1200+ | Central tool registry and loading |
| `config.mcp.yaml` | 194 | MCP server configurations |
| `code_evolver/MCP_README.md` | 220 | Quick start guide |
| `code_evolver/docs/MCP_INTEGRATION.md` | 420 | Complete documentation |
| `test_mcp_integration.py` | 145 | Integration test script |
| `tools/**/*.yaml` | 174 files | Tool definitions |
| `tools/index.json` | Large | Tool registry cache |

---

## 11. Current Status & Features

### ✅ Implemented

- MCP server connection management
- Tool discovery from MCP servers
- Automatic tool adaptation to system format
- Configuration-driven setup
- YAML-based tool definitions (174 tools)
- Tool versioning and change detection
- RAG integration for semantic search
- Multiple tool types: executable, llm, custom, openapi
- Tag-based discovery
- Environment variable support in configs
- Caching of tools and resources

### 🛠️ Available Official MCP Servers

- Fetch (web content)
- Memory (knowledge graph)
- Time (timezone utilities)
- Filesystem (secure file ops)
- GitHub (community-maintained)
- Git (community-maintained)

### 🔒 Security Features

- Safe mode for destructive operations
- Filesystem path restrictions
- Credential protection in config
- Environment variable substitution
- No secrets in output

---

## 12. Testing & Validation

### Test Script
**File**: `test_mcp_integration.py`

**Tests**:
1. Load configuration
2. Initialize MCP manager
3. Connect to MCP servers
4. Load tools from servers
5. Test integration with ToolsManager
6. Cleanup and disconnect

**Usage**:
```bash
python test_mcp_integration.py --config config.mcp.yaml
```

---

## 13. Future Enhancements

From MCP_INTEGRATION.md:

- [ ] Automatic server discovery
- [ ] Health monitoring and auto-reconnect
- [ ] Server metrics and performance tracking
- [ ] MCP resource browsing UI
- [ ] Prompt template integration
- [ ] Server marketplace integration

---

## Summary

The mostlylucid DiSE codebase implements a **sophisticated MCP integration system** with:

1. **Three-tier architecture**: MCPClientManager → MCPToolAdapter → ToolsManager
2. **Flexible configuration**: YAML-based, environment variable support
3. **Multiple tool sources**: YAML files, Python classes, LLM configs, MCP servers
4. **Advanced features**: Versioning, RAG integration, tag-based discovery
5. **Production-ready**: 174+ tools, comprehensive error handling, security considerations

The system seamlessly integrates external MCP servers with existing tool infrastructure, allowing developers to compose and manage tools from multiple sources with a unified API.
