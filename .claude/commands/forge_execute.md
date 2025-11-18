# Execute Forge Tool

Execute a tool via the forge runtime with sandboxing and provenance tracking.

## Usage
```
/forge_execute <tool_id> [version] --input <json>
```

## Parameters
- `tool_id`: Tool identifier
- `version`: Tool version (optional, uses latest)
- `--input`: JSON input data

## Options
- `--sandbox <config>`: Sandbox configuration (network, filesystem)
- `--no-sandbox`: Disable sandboxing (not recommended)
- `--log-provenance`: Save detailed provenance logs

## What This Command Does

1. **Prepare Execution**:
   - Load tool manifest from registry
   - Start MCP server if needed
   - Configure sandbox environment

2. **Execute Tool**:
   - Call tool with provided input
   - Track execution metrics
   - Capture output and errors

3. **Collect Provenance**:
   - Generate unique call_id
   - Record input/output hashes
   - Log timestamps and metrics
   - Store provenance record

4. **Update Metrics**:
   - Record execution in consensus engine
   - Update tool metrics
   - Recalculate consensus weight

## Examples

### Basic Execution
```bash
/forge_execute my_translator --input '{"text": "Hello", "target_lang": "es"}'
```

Output:
```
Executing: my_translator v2.0.0
call_id: a3f5c9d2e1b4...

✓ Execution successful
Result: {
  "translated_text": "Hola"
}

Provenance:
  started_at: 2025-11-18T14:23:45Z
  finished_at: 2025-11-18T14:23:46Z
  latency_ms: 850

Metrics:
  latency_ms: 850
  success: true
  cost: $0.0005

Provenance log: code_evolver/forge/data/logs/a3f5c9d2e1b4.json
```

### With Sandbox Config
```bash
/forge_execute risky_tool --input '{"command": "process"}' --sandbox '{"network": "none", "fs": "readonly"}'
```

Output:
```
Executing: risky_tool v1.0.0 (SANDBOXED)
Sandbox: network=none, filesystem=readonly

✓ Execution successful
Result: {...}

Security: Tool executed in restricted sandbox
```

### Using Intent (Auto-Discovery)
```bash
/forge_execute --intent "translate this text to French: Hello world"
```

Output:
```
Analyzing intent...
Discovered tool: nmt_translator v2.1.0

Executing with auto-extracted parameters:
  text: "Hello world"
  target_lang: "fr"

✓ Execution successful
Result: {
  "translated_text": "Bonjour le monde"
}
```

## Provenance Tracking

Each execution creates a provenance record:

```json
{
  "call_id": "a3f5c9d2e1b4...",
  "tool_id": "my_translator",
  "version": "2.0.0",
  "started_at": "2025-11-18T14:23:45Z",
  "finished_at": "2025-11-18T14:23:46Z",
  "input_hash": "e4d909c290d0...",
  "result_hash": "7b52009b64fd...",
  "sandbox_config": {
    "network": "restricted",
    "fs": "readonly"
  },
  "metrics": {
    "latency_ms": 850,
    "success": true
  }
}
```

## Notes
- All executions are logged for auditability
- Sandboxing is enabled by default for safety
- Metrics automatically update consensus weights
- Failed executions also recorded for analysis
