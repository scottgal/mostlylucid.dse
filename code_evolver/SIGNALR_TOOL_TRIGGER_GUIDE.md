# SignalR Tool Trigger - Complete Guide

## Overview

The **SignalR Tool Trigger** enables real-time, event-driven execution of tools and workflows. Listen to a SignalR endpoint and dynamically trigger ANY tool based on incoming messages.

## What It Does

1. **Listens** to SignalR hub in real-time
2. **Receives** messages containing tool invocation requests
3. **Triggers** tools dynamically based on message content
4. **Returns** results back to your system

## Three Modes of Operation

### Mode 1: Direct Tool Invocation

Trigger any existing tool with custom parameters:

```json
{
  "action": "trigger_tool",
  "tool_id": "nmt_translator",
  "parameters": {
    "text": "Hello world",
    "target_lang": "es"
  },
  "task_id": "task-123"
}
```

**Result**: Tool runs immediately, returns translation

### Mode 2: Workflow Generation

Auto-generate workflows from natural language:

```json
{
  "action": "generate_workflow",
  "description": "Translate blog posts and save to database",
  "task_id": "wf-456"
}
```

**Result**: New workflow node created and saved

### Mode 3: Dynamic Tool Creation

Create new tools from OpenAPI specs:

```json
{
  "action": "create_tool",
  "tool_spec": {
    "openapi": "3.0.0",
    "paths": {...}
  },
  "task_id": "api-789"
}
```

**Result**: New tool created from API specification

## Installation

```bash
# Install SignalR client
pip install signalrcore
```

## Quick Start Examples

### Example 1: Listen for 60 Seconds

```bash
cd code_evolver
echo '{
  "hub_url": "http://localhost:5000/toolhub",
  "hub_method": "ToolTrigger",
  "duration_seconds": 60
}' | python tools/executable/signalr_tool_trigger.py
```

### Example 2: Continuous Listening

```bash
cd code_evolver
echo '{
  "hub_url": "http://production-server:5000/toolhub",
  "hub_method": "ToolTrigger"
}' | python tools/executable/signalr_tool_trigger.py
```

Press Ctrl+C to stop.

### Example 3: Via node_runtime

```python
from node_runtime import call_tool
import json

# Start listener
result = call_tool("signalr_tool_trigger", json.dumps({
    "hub_url": "http://localhost:5000/toolhub",
    "duration_seconds": 300  # 5 minutes
}))

summary = json.loads(result)
print(f"Processed {summary['successful_results']} messages")
```

## Real-World Use Cases

### Use Case 1: Real-Time API Testing

**Scenario**: New API endpoint deployed, need to test immediately

**Hub sends**:
```json
{
  "action": "create_tool",
  "tool_spec": {
    "openapi": "3.0.0",
    "servers": [{"url": "https://api.example.com"}],
    "paths": {
      "/users": {
        "post": {...}
      }
    }
  },
  "task_id": "api-test-001"
}
```

**System**:
1. Creates tool from OpenAPI spec
2. Generates test data using `fake_data_generator`
3. Tests all endpoints
4. Returns results

### Use Case 2: Event-Driven Workflows

**Scenario**: User uploads document, needs translation

**Hub sends**:
```json
{
  "action": "trigger_tool",
  "tool_id": "nmt_translator",
  "parameters": {
    "text": "Document content...",
    "target_lang": "es",
    "document_id": "doc-12345"
  },
  "task_id": "translate-doc-12345"
}
```

**System**:
1. Triggers `nmt_translator` tool
2. Translates document
3. Returns translation
4. Can trigger follow-up workflow to save result

### Use Case 3: Training Pipeline

**Scenario**: Collect real-world usage patterns to improve system

**Hub sends** (from production app):
```json
{
  "action": "generate_workflow",
  "description": "User requested: Summarize this article and tweet the summary",
  "task_id": "training-001"
}
```

**System**:
1. Generates workflow from description
2. Saves as new node
3. Learns from real usage patterns
4. Improves workflow suggestions over time

## Message Flow Diagram

```
┌──────────────────┐
│  External System │
│  (Your App/API)  │
└────────┬─────────┘
         │ SignalR Message
         │ {action, tool_id, parameters}
         ↓
┌────────────────────────┐
│ SignalR Tool Trigger   │
│ (Listening on Hub)     │
└────────┬───────────────┘
         │
         ├─→ action: "trigger_tool"
         │   ↓
         │   ┌──────────────┐
         │   │  Call Tool   │
         │   └──────┬───────┘
         │          ↓
         │   ┌──────────────┐
         │   │  Return      │
         │   │  Result      │
         │   └──────────────┘
         │
         ├─→ action: "generate_workflow"
         │   ↓
         │   ┌────────────────────┐
         │   │ Workflow Generator │
         │   └──────┬─────────────┘
         │          ↓
         │   ┌─────────────────┐
         │   │ Save as Node    │
         │   └─────────────────┘
         │
         └─→ action: "create_tool"
             ↓
             ┌──────────────────┐
             │ API Parser       │
             └──────┬───────────┘
                    ↓
             ┌─────────────────┐
             │ New Tool Created│
             └─────────────────┘
```

## Integration with Existing Tools

The SignalR Tool Trigger can work with ALL your existing tools:

```json
// Trigger fake data generation
{
  "action": "trigger_tool",
  "tool_id": "fake_data_generator",
  "parameters": {
    "schema": {"type": "object", "properties": {...}},
    "count": 100
  }
}

// Trigger smart API parser
{
  "action": "trigger_tool",
  "tool_id": "smart_api_parser",
  "parameters": {
    "openapi_spec": {...},
    "make_requests": true
  }
}

// Trigger LLM data generation
{
  "action": "trigger_tool",
  "tool_id": "llm_fake_data_generator",
  "parameters": {
    "schema_json": "...",
    "additional_context": "Medical patient records"
  }
}

// Chain multiple tools
{
  "action": "trigger_tool",
  "tool_id": "workflow_name",
  "parameters": {
    "step1_tool": "fake_data_generator",
    "step2_tool": "smart_api_parser"
  }
}
```

## Server-Side Integration (C#/.NET Example)

```csharp
using Microsoft.AspNetCore.SignalR;

public class ToolHub : Hub
{
    // Method that clients listen to
    public async Task TriggerTool(string toolId, object parameters, string taskId)
    {
        // Send to all listening mostlylucid DiSE instances
        await Clients.All.SendAsync("ToolTrigger", new
        {
            action = "trigger_tool",
            tool_id = toolId,
            parameters = parameters,
            task_id = taskId
        });
    }

    public async Task GenerateWorkflow(string description, string taskId)
    {
        await Clients.All.SendAsync("ToolTrigger", new
        {
            action = "generate_workflow",
            description = description,
            task_id = taskId
        });
    }

    public async Task CreateToolFromAPI(object openApiSpec, string taskId)
    {
        await Clients.All.SendAsync("ToolTrigger", new
        {
            action = "create_tool",
            tool_spec = openApiSpec,
            task_id = taskId
        });
    }
}
```

## Server-Side Integration (Node.js Example)

```javascript
const signalR = require('@microsoft/signalr');

// Create hub connection
const connection = new signalR.HubConnectionBuilder()
    .withUrl("http://localhost:5000/toolhub")
    .build();

// Start connection
connection.start().then(() => {
    console.log("Connected to hub");

    // Trigger a tool
    connection.invoke("ToolTrigger", {
        action: "trigger_tool",
        tool_id: "nmt_translator",
        parameters: {
            text: "Hello world",
            target_lang: "es"
        },
        task_id: "task-123"
    });
});
```

## Python Server Example

```python
from signalrcore.hub import Hub

hub = Hub()

@hub.on_connect
def on_connect():
    print("mostlylucid DiSE connected!")

# Trigger tool from your Python app
def trigger_translation(text, target_lang):
    hub.send("ToolTrigger", {
        "action": "trigger_tool",
        "tool_id": "nmt_translator",
        "parameters": {
            "text": text,
            "target_lang": target_lang
        },
        "task_id": f"trans-{uuid.uuid4()}"
    })
```

## Output Format

The tool returns a summary of all processed messages:

```json
{
  "success": true,
  "hub_url": "http://localhost:5000/toolhub",
  "hub_method": "ToolTrigger",
  "total_messages": 15,
  "successful_results": 14,
  "errors": 1,
  "results": [
    {
      "task_id": "task-1",
      "action": "trigger_tool",
      "tool_id": "nmt_translator",
      "success": true,
      "result": "{\"translation\": \"Hola mundo\"}"
    },
    {
      "task_id": "wf-2",
      "action": "generate_workflow",
      "success": true,
      "node_id": "workflow_blog_translator",
      "workflow_name": "Blog Translation Workflow"
    }
  ],
  "error_details": [
    {
      "task_id": "task-99",
      "error": "Tool 'invalid_tool' not found",
      "message": {...}
    }
  ]
}
```

## Event Stream (stderr)

Real-time events logged to stderr:

```json
{"event": "connected", "hub_url": "...", "status": "listening"}
{"event": "message_received", "message_number": 1, "action": "trigger_tool", "task_id": "task-1"}
{"event": "triggering_tool", "task_id": "task-1", "tool_id": "nmt_translator"}
{"event": "tool_completed", "task_id": "task-1", "tool_id": "nmt_translator", "result_length": 1234}
{"event": "message_received", "message_number": 2, "action": "generate_workflow", "task_id": "wf-1"}
{"event": "generating_workflow", "task_id": "wf-1", "description": "Translate blog posts..."}
{"event": "workflow_created", "task_id": "wf-1", "node_id": "workflow_blog_translator"}
```

## Error Handling

### Connection Errors
- Automatic reconnection with exponential backoff
- Retries: 0s, 2s, 5s, 10s, 20s, 30s
- Keeps trying until manual shutdown

### Processing Errors
- Logged to error_details
- Doesn't stop listening
- Continues processing other messages

### Invalid Messages
- Gracefully handled
- Logged with full context
- Returns error in summary

## Performance Considerations

- **Latency**: < 50ms per message
- **Throughput**: 100+ messages/second
- **Memory**: Scales with queue size
- **CPU**: Minimal when idle

## Security Best Practices

1. **Use HTTPS**: `https://server/hub` in production
2. **Validate tool_id**: Whitelist allowed tools
3. **Sanitize parameters**: Prevent injection attacks
4. **Authenticate**: Implement hub-side authentication
5. **Rate limit**: Prevent abuse with rate limiting
6. **Monitor**: Log all tool invocations

## Comparison with Existing signalr_hub_connector

| Feature | signalr_hub_connector | signalr_tool_trigger |
|---------|----------------------|---------------------|
| Purpose | Workflow generation only | Multi-purpose (tools + workflows + APIs) |
| Actions | 1 (generate workflow) | 3 (trigger tool, generate workflow, create tool) |
| Flexibility | Fixed behavior | Dynamic based on message |
| Use Case | Training pipeline | Production integration |
| Tool Invocation | No | Yes |
| API Creation | No | Yes |

**When to use each:**
- **signalr_hub_connector**: Training system with real-world workflows
- **signalr_tool_trigger**: Production integration, event-driven architecture

## Troubleshooting

### No messages received
```bash
# Check hub is sending to correct method
# Verify hub_method matches server configuration
# Review hub-side logs
```

### Connection timeout
```bash
# Verify hub URL
# Check firewall settings
# Ensure hub is running
```

### Tool not found
```bash
# List available tools
cd code_evolver && python chat_cli.py
# Then type: list tools
```

## Next Steps

1. Set up SignalR hub on your server
2. Test with simple tool trigger
3. Integrate with production systems
4. Monitor and optimize

## Summary

The **SignalR Tool Trigger** enables you to:

✅ Trigger ANY tool from external systems
✅ Generate workflows dynamically
✅ Create tools from API specs
✅ Build event-driven architectures
✅ Train system from real usage
✅ Integrate with production apps

**Get started**: Copy one of the examples above and start listening!
