# How to Run SignalR Training

## Quick Start

### 1. Install Dependencies
```bash
pip install signalr-client aiohttp
```

### 2. Run Training Script
```bash
cd code_evolver
python start_signalr_training.py
```

That's it! The script will:
- Connect to `http://localhost:5000/taskhub` (default)
- Listen for tasks
- Generate workflows automatically
- Save each workflow as a new node
- Train your system in real-time

## Usage Examples

### Basic - Connect and Train Forever
```bash
python start_signalr_training.py
```
Press Ctrl+C to stop.

### Custom Hub URL
```bash
python start_signalr_training.py --hub-url http://prod:8080/llmhub
```

### Train for 5 Minutes
```bash
python start_signalr_training.py --duration 300
```

### Custom Hub Context
```bash
python start_signalr_training.py --hub-name LLMTasks
```

### Save Tasks to File
```bash
python start_signalr_training.py --output received_tasks.json
```

### All Options Together
```bash
python start_signalr_training.py \
  --hub-url http://prod:8080/llmhub \
  --hub-name LLMTasks \
  --duration 300 \
  --output tasks.json
```

### Just Receive Tasks (Don't Generate Workflows)
```bash
python start_signalr_training.py --no-auto-generate --output tasks.json
```

## What You'll See

```
======================================================================
  SignalR Training Launcher for Code Evolver
======================================================================

Hub URL:          http://localhost:5000/taskhub
Hub Name:         TaskHub
Duration:         Forever (Ctrl+C to stop)
Auto-Generate:    Yes
Save Tasks:       No

======================================================================

Connecting to SignalR hub...

✓ Workflow generator started (processing one task at a time)

✓ Connected! Listening for tasks...
  (Press Ctrl+C to stop)

[New Task] ID: task-1
           Type: summarize
           Queue Size: 1

[Task 1] Processing: task-1
         Type: summarize
         Queue: 0 waiting

  → Step 1: Generating workflow code...
  → Step 2: Saving node 'summarize_blog_post'...
  ✓ Completed: Workflow saved as 'nodes/summarize_blog_post/main.py'

[New Task] ID: task-2
           Type: generate
           Queue Size: 1

[Task 2] Processing: task-2
         Type: generate
         Queue: 0 waiting

  → Step 1: Generating workflow code...
  → Step 2: Saving node 'generate_email_content'...
  ✓ Completed: Workflow saved as 'nodes/generate_email_content/main.py'

...continues until Ctrl+C...

^C
Shutdown requested...
Disconnecting...
Waiting for current task to finish...

======================================================================
  Training Session Complete
======================================================================
  Total Tasks Received: 15
  Workflows Generated: 15
======================================================================
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--hub-url` | SignalR hub URL | `http://localhost:5000/taskhub` |
| `--hub-name` | Hub method/context name | `TaskHub` |
| `--duration` | Listen duration in seconds | Forever (until Ctrl+C) |
| `--output` | Save tasks to JSON file | None |
| `--no-auto-generate` | Don't generate workflows | Auto-generate enabled |

## Common Scenarios

### Scenario 1: Local Development
```bash
# Start your SignalR hub locally
# Then connect and train
python start_signalr_training.py
```

### Scenario 2: Production Monitoring (5 min sample)
```bash
python start_signalr_training.py \
  --hub-url https://prod-server/llmhub \
  --duration 300 \
  --output prod_tasks.json
```

### Scenario 3: Just Collect Tasks (No Training)
```bash
python start_signalr_training.py \
  --no-auto-generate \
  --output all_tasks.json
```

## Workflow Generation

**What Happens for Each Task:**

1. Task received from SignalR
2. Added to queue
3. Current task finishes (if any)
4. LLM analyzes task type
5. LLM generates Python code
6. Code saved as `nodes/{node_id}/main.py`
7. Node registered in system
8. Next task starts

**Processing Speed:**
- Each workflow: 1-3 minutes
- Sequential: One at a time
- No parallel processing

## Generated Workflows

**Example Task:**
```json
{
  "id": "task-1",
  "taskName": "LLM Summarization for Blog Post",
  "llmTaskType": "summarize"
}
```

**Generated File:**
`nodes/summarize_blog_post/main.py`

**You can now use it:**
```bash
echo '{"content": "Long article text..."}' | \
  python nodes/summarize_blog_post/main.py
```

## Troubleshooting

### "SignalR client library not installed"
```bash
pip install signalr-client aiohttp
```

### "Failed to import required modules"
Make sure you're in the `code_evolver` directory:
```bash
cd code_evolver
python start_signalr_training.py
```

### Connection Fails
- Check hub URL is correct
- Verify hub is running: `curl http://localhost:5000/taskhub`
- Check firewall settings

### No Tasks Received
- Verify hub is sending messages
- Check hub method name matches (`--hub-name`)
- Review hub-side logs

### Workflow Generation Fails
- Check LLM backend is running
- Verify tools are loaded: `python -c "from src.tools_manager import ToolsManager; tm = ToolsManager()"`
- Check stderr for detailed errors

## Stopping Training

**Graceful Shutdown:**
1. Press Ctrl+C
2. Current task finishes
3. Connection closes
4. Tasks saved (if `--output` specified)
5. Summary displayed

**Force Quit:**
- Ctrl+C twice (may lose current task)

## Checking Generated Workflows

```bash
# List all generated nodes
ls -la nodes/

# View a generated workflow
cat nodes/summarize_blog_post/main.py

# Test a workflow
echo '{"content": "test"}' | python nodes/summarize_blog_post/main.py
```

## Advanced: Integration with Other Scripts

```python
import subprocess

# Run training for 60 seconds
process = subprocess.run(
    ["python", "start_signalr_training.py", "--duration", "60"],
    cwd="code_evolver"
)

# Check generated workflows
from pathlib import Path
workflows = list(Path("code_evolver/nodes").iterdir())
print(f"Generated {len(workflows)} workflows")
```

## Requirements

**Python Packages:**
- `signalr-client` or `signalrcore`
- `aiohttp`

**System Components:**
- Code Evolver system
- Node runtime
- Tools manager
- Registry

**External:**
- Running SignalR hub
- LLM backend (for workflow generation)

## Tips

1. **Start Small**: Test with `--duration 60` first
2. **Monitor Progress**: Watch the console output
3. **Check Nodes**: Verify workflows are being created in `nodes/`
4. **Save Tasks**: Use `--output` to keep a record
5. **Graceful Stop**: Always Ctrl+C (don't kill process)

## What Gets Created

After running training, you'll have:

```
code_evolver/
  nodes/
    summarize_blog_post/
      main.py                    # ← New workflow
    generate_email_content/
      main.py                    # ← New workflow
    translate_product_description/
      main.py                    # ← New workflow
    ...

  received_tasks.json            # ← If --output specified
```

Each workflow is:
- ✅ Complete Python code
- ✅ Uses appropriate tools
- ✅ Reads JSON from stdin
- ✅ Outputs JSON to stdout
- ✅ Ready to execute

## Next Steps

1. **Start Training:**
   ```bash
   python start_signalr_training.py
   ```

2. **Let It Run:** Let it collect and process tasks

3. **Check Results:**
   ```bash
   ls nodes/
   ```

4. **Test a Workflow:**
   ```bash
   echo '{"content": "test"}' | python nodes/summarize_blog_post/main.py
   ```

5. **Repeat:** The more tasks you process, the better trained your system becomes!

## Help

```bash
python start_signalr_training.py --help
```

For detailed documentation, see:
- `SIGNALR_QUICKSTART.md`
- `SIGNALR_TRAINING_INTEGRATION.md`
