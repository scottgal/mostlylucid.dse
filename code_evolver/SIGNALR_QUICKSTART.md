# SignalR Integration - Quick Start Guide

## ✅ Complete! Ready to Use

You now have a full SignalR integration system that lets you train your Code Evolver system from streaming task data.

## Installation

```bash
# Required Python packages
pip install signalr-client aiohttp

# Or fallback if signalr-client doesn't work
pip install signalrcore
```

## The Easy Way - Natural Language

**Just say what you want in plain English:**

```bash
cd code_evolver

# Example 1: Simple connection with auto-workflow generation
echo "connect to http://localhost:5000/taskhub and create workflows" | \
  python tools/executable/connect_signalr.py

# Example 2: Full specification
echo "connect to this signalr api at http://prod:8080/llmhub with hub context LLMTasks and each time a workflow finishes processing feed the json contents into creating a new workflow" | \
  python tools/executable/connect_signalr.py

# Example 3: Timed collection
echo "listen to http://localhost:5000/hub for 60 seconds and save tasks to tasks.json" | \
  python tools/executable/connect_signalr.py
```

**That's it!** The system will:
1. Parse your natural language request
2. Connect to the SignalR hub
3. Receive streaming tasks
4. Process them sequentially (one at a time)
5. Generate Python workflows automatically
6. Save each workflow as a new node
7. Train itself with real-world examples

## What Gets Created

When a task arrives from SignalR:

**Task Received:**
```json
{
  "id": "task-1",
  "taskName": "LLM Summarization for Blog Post",
  "llmTaskType": "summarize",
  "priority": "medium"
}
```

**Workflow Generated:**
`nodes/summarize_blog_post/main.py`

**Result:**
Complete, executable Python workflow ready to use!

## Sequential Processing

Tasks are processed **one at a time:**

```
Task 1 arrives → [Queue: Task 1]
  ↓ Generate workflow (1-3 min)
  ↓ Save node
  ↓ Complete ✓

Task 2 arrives → [Queue: Task 2]
  ↓ Generate workflow (1-3 min)
  ↓ Save node
  ↓ Complete ✓

Task 3 arrives → [Queue: Task 3]
  ...and so on
```

## Real-Time Event Log

Watch what's happening (stderr):

```bash
python tools/executable/connect_signalr.py < request.txt 2>&1 | grep '"event"'
```

You'll see:
```json
{"event": "connected", "hub_url": "...", "status": "listening"}
{"event": "task_queued", "task_id": "task-1", "queue_size": 1}
{"event": "processing_task", "task_id": "task-1"}
{"event": "workflow_generated", "workflow_name": "Blog Post Summarization"}
{"event": "workflow_saved", "node_id": "summarize_blog_post"}
{"event": "task_completed", "task_id": "task-1"}
```

## Supported Task Types

### 1. Summarize Tasks
```json
{"llmTaskType": "summarize"}
```
→ Uses `summarizer` tool

### 2. Generate Tasks
```json
{"llmTaskType": "generate"}
```
→ Uses `content_generator` tool

### 3. Translate Tasks
```json
{
  "llmTaskType": "translate",
  "translationLanguages": [
    {"from": "de", "to": "en"}
  ]
}
```
→ Uses `nmt_translator` tool

## Advanced Usage

### Custom Configuration (JSON)

If you prefer JSON over natural language:

```bash
echo '{
  "hub_url": "http://localhost:5000/taskhub",
  "hub_name": "TaskHub",
  "duration_seconds": 300,
  "auto_generate_workflows": true,
  "output_file": "tasks.json"
}' | python tools/executable/signalr_hub_connector.py
```

### From Python

```python
import json
import subprocess

# Natural language
request = "connect to http://localhost:5000/hub and create workflows"

result = subprocess.run(
    ["python", "tools/executable/connect_signalr.py"],
    input=request,
    capture_output=True,
    text=True,
    cwd="code_evolver"
)

summary = json.loads(result.stdout)
print(f"Processed {summary['tasks_received']} tasks")
```

## Tools Created

1. **`connect_signalr`** - Simple natural language wrapper (recommended)
2. **`signalr_hub_connector`** - Low-level SignalR connector
3. **`signalr_connection_parser`** - Natural language parser (LLM)
4. **`task_to_workflow_router`** - Task → workflow generator (LLM)
5. **`workflow_documenter`** - Auto-documentation tool (bonus!)

## File Structure

```
code_evolver/
  tools/
    executable/
      connect_signalr.py          # ← Use this (natural language)
      connect_signalr.yaml
      signalr_hub_connector.py    # ← Or this (JSON config)
      signalr_hub_connector.yaml
    llm/
      signalr_connection_parser.yaml
      task_to_workflow_router.yaml

  nodes/
    summarize_blog_post/          # ← Generated workflows appear here
      main.py
    generate_email_with_translations/
      main.py
    translate_product_description/
      main.py
```

## Troubleshooting

**"SignalR package not installed"**
```bash
pip install signalr-client aiohttp
```

**Connection fails:**
- Check hub URL is correct
- Verify hub is running: `curl http://localhost:5000/taskhub`
- Check firewall/network settings

**No workflows generated:**
- Ensure you mentioned "create workflows" or "process" in natural language
- Or set `"auto_generate_workflows": true` in JSON
- Check stderr logs for errors

**Slow processing:**
- Normal! Each workflow takes 1-3 minutes to generate
- Tasks processed sequentially (one at a time)
- Check queue size in event log

## Next Steps

1. **Install dependencies:**
   ```bash
   pip install signalr-client aiohttp
   ```

2. **Test with local hub:**
   ```bash
   echo "connect to http://localhost:5000/hub and create workflows" | \
     python tools/executable/connect_signalr.py
   ```

3. **Check generated workflows:**
   ```bash
   ls -la nodes/
   ```

4. **Execute a generated workflow:**
   ```bash
   echo '{"content": "test"}' | python nodes/summarize_blog_post/main.py
   ```

## Documentation

- **Full Details:** `SIGNALR_TRAINING_INTEGRATION.md`
- **System Overview:** `README.md`

## Features

✅ Natural language interface
✅ Sequential task processing (one at a time)
✅ Automatic workflow generation
✅ Node creation and registration
✅ Real-time event logging
✅ Graceful shutdown (finishes current task)
✅ Auto-reconnection (exponential backoff)
✅ Dual library support (signalr-client or signalrcore)
✅ Support for summarize/generate/translate tasks
✅ Multi-language translation support

## Summary

**Before:**
- Manual workflow creation
- No real-time training
- Static training examples

**Now:**
- Say: "connect to http://localhost:5000/hub and create workflows"
- System automatically trains itself from streaming data
- Real-world examples → better training

**It's that easy!**
