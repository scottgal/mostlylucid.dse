# Background Process Execution Design

**Date:** 2025-11-17
**Status:** 🚧 IN DESIGN

## Overview

Allow long-running tasks (tool building, workflow execution) to run in the background while keeping the chat interactive. Use sentinel AI to intelligently decide when to interrupt background processes.

## Requirements

1. **Background Execution**: Start long-running processes in background threads
2. **Interactive Chat**: Return to prompt immediately, accept new commands
3. **Live Status Updates**: Show progress updates without blocking input
4. **Sentinel Decision Making**: Use gemma3:1b to decide when to interrupt
5. **Process Management**: Track, monitor, and control background processes

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Chat CLI                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Input Thread │  │ Status Thread│  │ Sentinel AI  │      │
│  │              │  │              │  │  (gemma3:1b) │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
│                ┌──────────▼───────────┐                    │
│                │ Background Process   │                    │
│                │      Manager         │                    │
│                └──────────┬───────────┘                    │
│                           │                                │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│    ┌────▼────┐      ┌─────▼─────┐     ┌────▼────┐         │
│    │ Tool    │      │ Workflow  │     │ Custom  │         │
│    │ Builder │      │ Executor  │     │ Task    │         │
│    └─────────┘      └───────────┘     └─────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Background Process Manager

**File:** `src/background_process_manager.py`

```python
class BackgroundProcessManager:
    def __init__(self, sentinel: SentinelLLM):
        self.processes: Dict[str, BackgroundProcess] = {}
        self.sentinel = sentinel
        self.lock = threading.Lock()

    def start_process(self, process_id: str, task_fn, args) -> str:
        """Start a background process"""

    def get_status(self, process_id: str) -> Dict[str, Any]:
        """Get process status"""

    def should_interrupt(self, process_id: str, user_input: str) -> bool:
        """Use sentinel AI to decide if we should interrupt"""

    def wait_for_completion(self, process_id: str, timeout: Optional[float] = None):
        """Wait for process to complete"""

    def cancel_process(self, process_id: str):
        """Cancel a running process"""
```

### Background Process

**File:** `src/background_process.py`

```python
class BackgroundProcess:
    def __init__(self, process_id: str, task_fn, args):
        self.process_id = process_id
        self.task_fn = task_fn
        self.args = args
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.progress = 0.0
        self.result = None
        self.error = None
        self.thread = None
        self.start_time = None
        self.end_time = None
        self.status_updates: List[str] = []

    def start(self):
        """Start the background process in a thread"""

    def update_status(self, message: str, progress: float):
        """Update status message and progress"""

    def cancel(self):
        """Cancel the process"""
```

### Sentinel Interrupt Decision

**File:** `src/sentinel_llm.py` (extend existing)

```python
def should_interrupt_background_process(
    self,
    process_info: Dict[str, Any],
    user_input: str
) -> Dict[str, Any]:
    """
    Decide if user input requires interrupting a background process.

    Args:
        process_info: Info about running process
        user_input: New user input

    Returns:
        {
            "should_interrupt": bool,
            "reason": str,
            "urgency": str  # "low", "medium", "high"
        }
    """

    prompt = f"""Background process is running:
Type: {process_info['type']}
Status: {process_info['status']}
Progress: {process_info['progress']}%
Latest update: {process_info['latest_status']}

User says: "{user_input}"

Should we interrupt the background process to handle this request?

Consider:
1. Is the user asking about the background process? (DON'T interrupt, answer from status)
2. Is the user starting a NEW unrelated task? (DON'T interrupt, queue or warn)
3. Is the user requesting cancellation? (INTERRUPT, cancel the process)
4. Is the user correcting/modifying the current task? (INTERRUPT, need to restart)

Format:
DECISION: <CONTINUE|INTERRUPT>
URGENCY: <LOW|MEDIUM|HIGH>
REASON: <brief explanation>
"""

    response = self.client.generate(
        model=self.sentinel_model,  # gemma3:1b
        prompt=prompt,
        temperature=0.1,
        max_tokens=100
    ).strip()

    # Parse response...
```

## Integration with Chat CLI

### Modified Chat Loop

```python
async def chat_loop(self):
    """Main chat loop with background process support"""

    while True:
        # Check for background process status updates
        self._print_background_status_updates()

        # Get user input (non-blocking)
        user_input = await self._get_input_async()

        # Check if we have running background processes
        if self.bg_manager.has_running_processes():
            # Ask sentinel: should we interrupt?
            processes = self.bg_manager.get_running_processes()

            for proc_id, proc_info in processes.items():
                decision = self.sentinel.should_interrupt_background_process(
                    proc_info,
                    user_input
                )

                if decision['should_interrupt']:
                    console.print(f"[yellow]Interrupting background process: {proc_id}[/yellow]")
                    console.print(f"[dim]Reason: {decision['reason']}[/dim]")
                    self.bg_manager.cancel_process(proc_id)

        # Process command
        if user_input.startswith("generate"):
            # Start tool building in background
            process_id = f"build_{int(time.time())}"

            self.bg_manager.start_process(
                process_id,
                task_fn=self._build_tool_background,
                args=(user_input,)
            )

            console.print(f"[cyan]Started background process: {process_id}[/cyan]")
            console.print(f"[dim]You can continue using the CLI while it runs[/dim]")

        elif user_input == "status":
            # Show all background processes
            self._show_background_status()

        elif user_input == "wait":
            # Wait for all background processes
            self._wait_for_all_processes()
```

### Async Input Handler

```python
async def _get_input_async(self) -> str:
    """Get user input without blocking status updates"""

    # Use asyncio to read input while allowing status updates
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self.session.prompt, "CodeEvolver> ")
```

### Status Update Printer

```python
def _print_background_status_updates(self):
    """Print new status updates from background processes"""

    for proc_id, process in self.bg_manager.get_running_processes().items():
        new_updates = process.get_new_status_updates()

        for update in new_updates:
            console.print(f"[dim cyan][{proc_id}] {update}[/dim cyan]")
```

## Long-Running Tasks to Background

### Tool Building

```python
def _build_tool_background(self, description: str):
    """Build tool in background with status updates"""

    process = self.bg_manager.get_current_process()

    try:
        process.update_status("Consulting overseer...", 10)
        strategy = self._consult_overseer(description)

        process.update_status("Generating code...", 30)
        code = self._generate_code(strategy)

        process.update_status("Running tests...", 60)
        test_result = self._run_tests(code)

        process.update_status("Running static analysis...", 80)
        analysis = self._run_static_analysis(code)

        process.update_status("Saving tool...", 90)
        node_id = self._save_tool(code)

        process.update_status("Complete!", 100)
        process.complete(result={"node_id": node_id, "success": True})

    except Exception as e:
        process.fail(error=str(e))
```

### Workflow Execution

```python
def _execute_workflow_background(self, workflow_spec: Dict):
    """Execute multi-step workflow in background"""

    process = self.bg_manager.get_current_process()

    total_steps = len(workflow_spec['steps'])

    for i, step in enumerate(workflow_spec['steps']):
        progress = int((i / total_steps) * 100)
        process.update_status(f"Step {i+1}/{total_steps}: {step['name']}", progress)

        # Execute step...
        result = self._execute_step(step)

        if not result['success']:
            process.fail(error=f"Step {i+1} failed: {result['error']}")
            return

    process.update_status("Workflow complete!", 100)
    process.complete(result={"success": True})
```

## User Commands

### New Commands

- `/status` - Show all background processes
- `/wait [process_id]` - Wait for process to complete
- `/cancel [process_id]` - Cancel a background process
- `/bg on|off` - Enable/disable background execution

### Example Session

```
CodeEvolver> generate email validator
Started background process: build_1634567890
You can continue using the CLI while it runs

CodeEvolver> [build_1634567890] Consulting overseer...

CodeEvolver> list
Available tools:
- string_validator
- json_parser
...

[build_1634567890] Generating code...

CodeEvolver> [build_1634567890] Running tests...

CodeEvolver> status
Background Processes:
- build_1634567890: Running (60%) - Running tests...

[build_1634567890] All tests passed
[build_1634567890] Complete!

CodeEvolver>
```

## Configuration

**File:** `config.yaml`

```yaml
background_execution:
  enabled: true
  max_concurrent_processes: 3
  status_update_interval: 2  # seconds

  # What tasks should run in background
  background_tasks:
    - tool_building
    - workflow_execution
    - batch_testing
    - optimization

  # Sentinel AI settings
  sentinel:
    model: "gemma3:1b"
    interrupt_decision_timeout: 5  # seconds

  # Status display
  status_display:
    show_progress_bar: true
    show_timestamps: false
    max_updates_shown: 5
```

## Implementation Phases

### Phase 1: Core Infrastructure ✅
- [x] Create BackgroundProcessManager
- [x] Create BackgroundProcess class
- [x] Thread-based execution

### Phase 2: Sentinel Integration 🚧
- [ ] Extend SentinelLLM with interrupt decision
- [ ] Test interrupt scenarios
- [ ] Tune decision prompts

### Phase 3: Chat Integration 🚧
- [ ] Async input handling
- [ ] Status update printing
- [ ] Process lifecycle management

### Phase 4: Long-Running Tasks 🚧
- [ ] Background tool building
- [ ] Background workflow execution
- [ ] Background testing/optimization

### Phase 5: User Commands 🚧
- [ ] /status command
- [ ] /wait command
- [ ] /cancel command

## Benefits

✅ **Responsive UI**: Chat remains interactive during long tasks
✅ **Parallel Work**: Can query info while tool builds
✅ **Smart Interrupts**: Sentinel decides when to stop
✅ **Progress Visibility**: See what's happening in real-time
✅ **Flexibility**: Continue working or wait for completion

## Status

🚧 **IN DESIGN** - Architecture defined, ready for implementation
