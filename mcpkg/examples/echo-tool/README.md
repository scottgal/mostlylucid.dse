# Echo Tool Example

This is a minimal example MCPKG package that demonstrates the format and structure.

## Contents

- `manifest.json` - Tool specification
- `tests/echo.test.json` - Test case
- `examples/basic_usage.md` - Usage documentation

## Building the Package

```bash
cd examples/echo-tool
mcpkg create . --output echo.mcpkg
```

## Installing the Package

```bash
mcpkg install echo.mcpkg
```

## Testing the Tool

```bash
mcpkg test demo.echo
```

## Exporting for LLM Runtime

```bash
mcpkg export --output tools.json
```
