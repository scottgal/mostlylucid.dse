# Background Workflow System

**Parallel Workflow Execution with Automatic Naming**

## Overview

The background workflow system allows users to kick off multiple code generation workflows in parallel, with each workflow automatically named using a 1B LLM for easy tracking.

## Features

### 1. **Automatic Workflow Naming** (1B LLM)
Each workflow is automatically named based on its description using the fast triage model (veryfast tier - typically 1B parameters).

**Example:**
```
User: "write a function to validate email addresses"
→ Workflow named: "email-validation-function"

User: "create a REST API client for GitHub"
→ Workflow named: "github-rest-api-client"
```

### 2. **Background Execution**
Workflows run in separate threads, allowing the prompt to return immediately for new tasks.

**Workflow:**
```
User Input → Start Workflow → Generate Name → Return to Prompt
                    ↓
            [Background Thread]
                    ↓
            Complete Generation
                    ↓
            Show Result
```

### 3. **Progress Tracking**
All workflows show their status with name tags:

```
→ [email-validation] Starting workflow...
→ [github-client] Starting workflow...

[email-validation] Generating code...
[github-client] Consulting overseer...

✓ [email-validation] Completed in 45.3s
✓ [github-client] Completed in 62.1s
```

## Architecture

### Classes

#### `WorkflowStatus` (Enum)
Status states for workflows:
- `QUEUED` - Waiting to start
- `NAMING` - Generating workflow name
- `RUNNING` - Executing code generation
- `COMPLETED` - Successfully finished
- `FAILED` - Error occurred

#### `BackgroundWorkflow` (Dataclass)
Represents a single background workflow:

```python
@dataclass
class BackgroundWorkflow:
    workflow_id: str              # Unique ID
    description: str              # Task description
    name: Optional[str]           # Generated name
    status: WorkflowStatus        # Current status
    progress: str                 # Progress message
    result: Optional[Any]         # Result when complete
    error: Optional[str]          # Error if failed
    thread: Optional[Thread]      # Execution thread
    start_time: float             # When started
    end_time: Optional[float]     # When completed
```

#### `BackgroundWorkflowManager`
Manages all background workflows:

**Methods:**
- `generate_workflow_name(description)` - Use 1B LLM to generate name
- `start_workflow(description)` - Start new background workflow
- `get_active_workflows()` - List running workflows
- `get_workflow(workflow_id)` - Get specific workflow
- `list_workflows()` - Display workflow table

### Integration Points

#### Modified `handle_generate()`

**Before:**
```python
def handle_generate(description: str) -> bool:
    # Runs synchronously
    return self._process_generate(description)
```

**After:**
```python
def handle_generate(description: str, background: bool = False) -> bool:
    if background:
        # Start in background, return immediately
        workflow_id = self.workflow_manager.start_workflow(description)
        console.print(f"[dim cyan]Started workflow {workflow_id}[/dim cyan]")
        return True
    else:
        # Run in foreground (original behavior)
        return self._process_generate(description)
```

#### New Method `_process_generate()`

Renamed from `handle_generate()` - contains all the actual generation logic.

**Signature:**
```python
def _process_generate(
    self,
    description: str,
    display_description: str = None,
    workflow_id: Optional[str] = None
) -> bool:
    # All existing code generation logic
    # workflow_id used for progress updates
```

## Usage

### Default (Foreground) Mode

```
User> write a function to validate emails
[Runs synchronously, shows all output, blocks prompt]
```

### Background Mode

```
User> /generate --background write a function to validate emails
→ [email-validator] Starting workflow...
Started workflow wf_1_1732123456
User> write a REST API client
→ [rest-api-client] Starting workflow...
Started workflow wf_2_1732123457
User> _
```

### View Workflows

```
User> /workflows
╭─────────────────────────────────────────────────────────────╮
│                     Background Workflows                     │
├───────────────┬─────────────────┬──────────┬─────────┬───────┤
│ ID            │ Name            │ Status   │ Progress│ Time  │
├───────────────┼─────────────────┼──────────┼─────────┼───────┤
│ wf_1_17321... │ email-validator │ running  │ Testing │ 23.4s │
│ wf_2_17321... │ rest-api-client │ queued   │         │ 2.1s  │
│ wf_3_17321... │ json-parser     │ completed│         │ 45.2s │
│ wf_4_17321... │ image-resizer   │ failed   │ Error   │ 12.1s │
╰───────────────┴─────────────────┴──────────┴─────────┴───────╯
```

## Commands

### `/generate --background <description>`
Start a workflow in background mode.

### `/workflows` or `/wf`
List all workflows and their status.

### `/workflow <id>` or `/wf <id>`
Show details of a specific workflow.

## Implementation Status

✅ **Completed:**
- `WorkflowStatus` enum
- `BackgroundWorkflow` dataclass
- `BackgroundWorkflowManager` class
- Workflow naming with 1B LLM
- Thread-safe workflow tracking
- Workflow listing

⚠️ **Pending:**
- Rename `handle_generate` → `_process_generate`
- Create new `handle_generate` with background support
- Add `/workflows` command parsing
- Add `/workflow <id>` command
- Progress updates from background threads
- Workflow result storage

## Example Session

```
User> /generate --background create email validator
→ [naming] Generating workflow name...
→ [email-validator] Starting workflow...
Started workflow wf_1_1732123456

User> /generate --background build REST client
→ [naming] Generating workflow name...
→ [rest-client] Starting workflow...
Started workflow wf_2_1732123457

User> /workflows
╭──────────────────────────────────────────────╮
│         Background Workflows                 │
├─────────┬─────────────────┬─────────┬────────┤
│ ID      │ Name            │ Status  │ Time   │
├─────────┼─────────────────┼─────────┼────────┤
│ wf_1... │ email-validator │ running │ 12.3s  │
│ wf_2... │ rest-client     │ naming  │ 1.2s   │
╰─────────┴─────────────────┴─────────┴────────╯

[Background output:]
→ [email-validator] Consulting overseer...
→ [rest-client] Starting workflow...

User> create a simple calculator
[Runs in foreground - default behavior]

[Background output:]
→ [email-validator] Generating tests...
✓ [rest-client] Completed in 34.5s

User> /wf wf_1_1732123456
Workflow: email-validator (wf_1_1732123456)
Status: running
Progress: Running tests...
Started: 45s ago
```

## Benefits

### 1. **Parallel Development**
Work on multiple tasks simultaneously without waiting for long-running generations.

### 2. **Efficient Resource Usage**
CPU-intensive tasks run in background while user continues planning.

### 3. **Clear Tracking**
Auto-generated names make it easy to identify workflows.

### 4. **Non-Blocking**
Prompt remains responsive for new requests.

### 5. **Visibility**
See all active workflows at a glance with `/workflows`.

## Technical Notes

- Workflows run as daemon threads (exit when main program exits)
- Thread-safe with lock for workflow dictionary
- Names generated using `veryfast` tier (1B model) for speed
- Progress messages printed to console in real-time
- Original foreground mode preserved as default

---

**Status**: Core infrastructure complete, integration pending.
