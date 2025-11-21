# MCPKG - AI-Native Package Manager for MCP Tools

MCPKG is a package format and tooling for distributing, installing, and managing MCP (Model Context Protocol) tools. It provides a standardised way to package tools with their specifications, tests, and metadata for use by LLMs and AI agents.

## Features

- ✨ **AI-Native Design** - Package format designed for LLM consumption
- 📦 **ZIP-based Format** - Simple `.mcpkg` files containing everything needed
- ✅ **Built-in Validation** - JSON Schema validation for manifests and inputs
- 🧪 **Integrated Testing** - Test cases with JSONPath assertions
- 🔐 **Security First** - Support for authentication and provenance tracking
- 🚀 **Beautiful CLI** - Powered by Spectre.Console
- 📊 **Tools Export** - Generate `tools.json` for LLM runtimes
- 🌐 **URL Installation** - Install packages directly from URLs

## Installation

### Prerequisites

- .NET 8.0 SDK or later

### Building from Source

```bash
cd mcpkg
dotnet build
dotnet publish McPkg.Cli -c Release -o publish
```

Add the `publish` directory to your PATH to use the `mcpkg` command globally.

## Quick Start

### 1. Create a Package

Create a folder with your tool specification:

```
my-tool/
├─ manifest.json          # Required
├─ tests/
│  └─ test1.test.json
├─ examples/
│  └─ usage.md
└─ README.md
```

Create the package:

```bash
mcpkg create my-tool --output my-tool.mcpkg
```

### 2. Install a Package

```bash
# From local file
mcpkg install my-tool.mcpkg

# From URL
mcpkg install https://example.com/packages/my-tool.mcpkg
```

### 3. List Installed Tools

```bash
mcpkg list
```

### 4. Run Tests

```bash
mcpkg test my.tool.id
```

### 5. Export for LLM Runtime

```bash
mcpkg export --output tools.json --run-tests
```

## Package Format

### Manifest Structure

Every `.mcpkg` file must contain a `manifest.json`:

```json
{
  "toolId": "publisher.domain.capability.name",
  "name": "Human Readable Name",
  "version": "1.0.0",
  "description": "What this tool does",
  "capabilities": ["tag1", "tag2"],
  "endpoint": {
    "type": "http",
    "method": "POST",
    "url": "https://api.example.com/endpoint",
    "timeoutMs": 10000
  },
  "input_schema": { /* JSON Schema */ },
  "output_schema": { /* JSON Schema */ },
  "auth": {
    "type": "bearer",
    "scopes": ["read", "write"],
    "configHints": {
      "env": ["API_KEY"],
      "docsUrl": "https://docs.example.com/auth"
    }
  },
  "tests": ["tests/test1.test.json"],
  "examples": ["examples/usage.md"],
  "meta": {
    "publisher": {
      "id": "acme",
      "name": "ACME Corp",
      "website": "https://acme.com"
    },
    "license": "MIT",
    "tags": ["production", "verified"]
  }
}
```

### Test Case Format

Tests use JSONPath assertions:

```json
{
  "name": "test_success_case",
  "description": "Tests successful operation",
  "input": {
    "param1": "value1"
  },
  "expected": {
    "status": "success"
  },
  "assertions": [
    {
      "path": "$.status",
      "equals": "success"
    },
    {
      "path": "$.result",
      "exists": true
    }
  ],
  "timeoutMs": 5000
}
```

### Supported Assertion Types

- `equals` - Value must equal expected
- `notEquals` - Value must not equal expected
- `exists` - Path must exist in response
- `notExists` - Path must not exist in response

## CLI Commands

### create

Create a new `.mcpkg` package:

```bash
mcpkg create <source-folder> [options]

Options:
  -o, --output <path>    Output file path
  --no-validate          Skip validation
```

### install

Install a package:

```bash
mcpkg install <package> [options]

Options:
  --root <path>          Installation root (default: .mcp/tools)
  --no-validate          Skip validation
```

### list

List installed packages:

```bash
mcpkg list [options]

Options:
  --root <path>          Installation root (default: .mcp/tools)
```

### test

Run tests for a tool:

```bash
mcpkg test <toolId> [options]

Options:
  --root <path>          Installation root (default: .mcp/tools)
```

### export

Export installed tools to `tools.json`:

```bash
mcpkg export [options]

Options:
  --output <path>        Output file path (default: tools.json)
  --root <path>          Installation root (default: .mcp/tools)
  --run-tests            Run tests and include summaries
```

### validate

Validate a manifest file:

```bash
mcpkg validate <manifest.json>
```

### uninstall

Uninstall a package:

```bash
mcpkg uninstall <toolId> [options]

Options:
  --root <path>          Installation root (default: .mcp/tools)
```

## Integration with DiSE

MCPKG is designed to integrate seamlessly with DiSE (Dynamic Intelligence Selection Engine):

- **Generated Nodes**: Each installed tool becomes a DiSE node with standardised structure
- **Tool Ranking**: DiSE can score tools based on test pass rate and performance metrics
- **RAG Context**: Examples and tests provide context for tool selection decisions
- **Regression Detection**: Continuous testing detects when tool behaviour changes

## Architecture

```
McPkg.Core/
├─ Models/              # Data models with JSON source generation
├─ Validation/          # Manifest and test validation
├─ PackageManager/      # Package creation, installation, export
└─ Testing/             # Test runner with JSONPath assertions

McPkg.Cli/
└─ Program.cs           # Spectre.Console CLI with System.CommandLine
```

## Example Package

See [`examples/echo-tool/`](examples/echo-tool/) for a complete working example.

## Spec

See [SPEC.md](SPEC.md) for the complete MCPKG v0.1 specification.

## Development

### Prerequisites

- .NET 8.0 SDK
- Your favourite code editor

### Building

```bash
dotnet build
```

### Running Tests

```bash
dotnet test
```

### Code Structure

- Uses `System.Text.Json` with source generation for performance
- No dependencies on Newtonsoft.Json
- Uses `JsonSchema.Net` for JSON Schema validation
- Uses `JsonPath.Net` for test assertions
- Uses `Spectre.Console` for beautiful CLI output

## License

MIT License - see LICENSE file for details

## Contributing

This is part of the mostlylucid.dse project. Contributions welcome!

## Roadmap

- [ ] Registry server for package discovery
- [ ] Package signing and verification
- [ ] Support for gRPC and local endpoints
- [ ] Dependency management between tools
- [ ] Performance metrics collection
- [ ] Integration with popular LLM frameworks
- [ ] Web UI for package management

## Links

- [Main Project](https://github.com/scottgal/mostlylucid.dse)
- [Blog](https://mostlylucid.net)
- [MCPKG Spec](SPEC.md)
