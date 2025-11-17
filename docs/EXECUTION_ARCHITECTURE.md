# Code Evolver - Execution Architecture Summary

## Overview
The Code Evolver system has a **synchronous, sequential execution model** with **limited parallelism** in specific areas. It's designed as an interactive CLI system that generates, executes, and optimizes code through an overseer-driven workflow decomposition approach.

---

## 1. EXECUTION MODEL

### Main Loop (chat_cli.py)
- **Location**: `/home/user/mostlylucid.dse/code_evolver/chat_cli.py` (7546 lines)
- **Entry Point**: `main()` function at line 7546
- **Run Method**: `ChatCLI.run()` at line 7329

```
Main Loop (Synchronous):
├─ while True:
│  ├─ User input (line 7345-7360)
│  ├─ Command parsing
│  └─ Handler execution (sequential)
│     ├─ handle_generate() - most common
│     ├─ handle_workflow()
│     ├─ handle_run()
│     └─ Other commands
└─ Save history on exit
```

**Characteristics**:
- **Blocking input/output**: Uses `console.input()` or `prompt_toolkit`
- **Sequential command execution**: One command at a time
- **Interactive**: Waits for user input between operations
- **Signal handling**: Ctrl-C interrupts current task

---

## 2. WORKFLOW EXECUTION

### Workflow Specification (workflow_spec.py)
The system defines workflows using a declarative specification with:

**File**: `/home/user/mostlylucid.dse/code_evolver/src/workflow_spec.py` (514 lines)

**Structure**:
```python
WorkflowSpec:
  ├─ workflow_id: str
  ├─ description: str
  ├─ version: str
  ├─ inputs: List[WorkflowInput]
  ├─ outputs: List[WorkflowOutput]
  ├─ steps: List[WorkflowStep]
  └─ tools: Dict[tool_id, ToolDefinition]

WorkflowStep:
  ├─ step_id: str
  ├─ step_type: StepType (llm_call, python_tool, sub_workflow, existing_tool)
  ├─ tool_name: str
  ├─ prompt_template: str
  ├─ input_mapping: Dict
  ├─ output_name: str
  ├─ timeout: int (seconds)
  ├─ retry_on_failure: bool
  ├─ max_retries: int
  ├─ parallel_group: Optional[int]
  └─ depends_on: List[str]
```

### Workflow Builder (workflow_builder.py)
**File**: `/home/user/mostlylucid.dse/code_evolver/src/workflow_builder.py` (263 lines)

**Purpose**: Converts overseer output into WorkflowSpec objects

**Methods**:
- `build_from_text()` - Parse overseer output
- `build_from_json()` - Build from JSON specification
- `create_simple_workflow()` - Create single-step workflow
- `_parse_step()` - Parse individual workflow steps

### Workflow Execution (chat_cli.py - handle_workflow)
**Location**: chat_cli.py, lines ~800-950

**Flow**:
```
handle_workflow(description):
1. Workflow Decomposition (Overseer)
   └─ Call overseer LLM to plan steps
   └─ Parse response into WorkflowSpec
   └─ Validate step count

2. Execute Steps (Sequential + Limited Parallel)
   ├─ Organize steps into execution groups (respecting dependencies)
   ├─ For each group:
   │  ├─ If group has 1 step: Execute directly
   │  └─ If group has N steps: Execute in ThreadPoolExecutor
   │     └─ concurrent.futures.ThreadPoolExecutor (default: max_workers based on CPU count)
   └─ Collect results from all steps

3. Aggregate Results
   └─ Combine step outputs into workflow result
```

**Parallel Execution Details** (lines 843-910):
```python
import concurrent.futures
import threading

if len(parallel_group) == 1:
    execute_step(step)  # Direct execution
else:
    with concurrent.futures.ThreadPoolExecutor(max_workers=...) as executor:
        futures = [executor.submit(execute_step, step) for step in parallel_group]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
```

**Limitations**:
- Parallel execution is only for steps in the SAME group
- Steps with dependencies are never parallelized
- No async/await patterns in workflow execution
- Thread-based (not process-based) due to GIL limitations in Python

---

## 3. NODE EXECUTION

### NodeRunner (node_runner.py)
**File**: `/home/user/mostlylucid.dse/code_evolver/src/node_runner.py` (242 lines)

**Purpose**: Execute generated Python code in a subprocess

**Execution Model**:
```
run_node(node_id, input_payload, timeout_ms):
  ├─ Validate code exists
  ├─ Serialize input to JSON
  ├─ subprocess.Popen() - Execute Python process
  │  └─ Stdin: JSON input
  │  └─ Stdout/Stderr: Captured
  │  └─ Timeout: timeout_ms milliseconds
  ├─ Monitor memory usage with psutil
  ├─ Collect metrics:
  │  ├─ latency_ms
  │  ├─ cpu_time_ms
  │  ├─ memory_mb_peak
  │  ├─ exit_code
  │  └─ success: bool
  └─ Return (stdout, stderr, metrics)
```

**Timeout Handling**:
- Default: 600,000ms (10 minutes) - previously was 60s
- On timeout: `process.kill()`
- Error code: -1

---

## 4. BUILDER PATTERN

### WorkflowBuilder
**File**: `/home/user/mostlylucid.dse/code_evolver/src/workflow_builder.py`

**Pattern**:
```python
class WorkflowBuilder:
    def build_from_text(description, overseer_output) -> WorkflowSpec
    def build_from_json(json_str) -> WorkflowSpec
    def create_simple_workflow(description) -> WorkflowSpec
```

**No explicit "Builder" pattern** in the traditional sense (no step-by-step construction with fluent API). Instead, it's a **direct mapping** from external data to WorkflowSpec objects.

---

## 5. ASYNC/THREADING PATTERNS

### Threading (LIMITED)

**Found in**:
1. **BackgroundToolsLoader** (background_tools_loader.py)
   - Uses `threading.Thread` (daemon thread)
   - Loads ToolsManager in background
   - Non-blocking CLI startup
   - Lock-based synchronization: `threading.Lock()`

2. **Workflow Parallel Execution** (chat_cli.py)
   - Uses `concurrent.futures.ThreadPoolExecutor`
   - Limited to steps in same dependency group
   - No true async/await

3. **Progress Display** (background_tools_loader.py)
   - Spinner thread for UI feedback

### Asyncio (MINIMAL)

**Found in**:
1. **MCP Client Manager** (mcp_client_manager.py)
   - Uses `asyncio` for Model Context Protocol connections
   - Async methods: `connect()`, `disconnect()`, `call_tool()`
   - NOT integrated with main CLI loop
   - Separate from main execution

**Files**:
- `/home/user/mostlylucid.dse/code_evolver/src/mcp_client_manager.py` - MCP server connections
- `/home/user/mostlylucid.dse/code_evolver/src/mcp_tool_adapter.py` - Tool adaptation layer

---

## 6. TASK QUEUE / SCHEDULER

### NO TRADITIONAL TASK QUEUE FOUND

**What exists**:
1. **Message Queue Reference** (tools_manager.py, line 90)
   ```python
   MESSAGE_QUEUE = "message_queue"   # Kafka/RabbitMQ for streaming
   ```
   - **Status**: Defined but NOT implemented
   - **Intended for**: Future streaming/distributed execution

2. **Offline Batch Optimizer** (offline_optimizer.py)
   - `batch_optimize_overnight()` - Identifies optimization candidates
   - `schedule_nightly_optimization()` - Scheduling method (NOT fully implemented)
   - Cost-based prioritization, but no actual scheduler

3. **WorkflowTracker** (workflow_tracker.py)
   - Tracks step execution
   - NOT a scheduler - just a tracker
   - Records timing and status, not task scheduling

### Workflow Distribution (workflow_distributor.py)
**File**: `/home/user/mostlylucid.dse/code_evolver/src/workflow_distributor.py` (495 lines)

**Purpose**: Export workflows for different platforms

**Export Targets**:
```
├─ Cloud (GPT-4, Claude APIs)
├─ Edge (Local Ollama)
├─ Embedded (No LLMs, pure Python)
└─ WASM (Future)
```

**Execution Method**:
- Generated `run_workflow.py` runner scripts
- Platform-specific requirements
- No centralized scheduler - each runner is independent

---

## 7. CLI ENTRY POINT AND MAIN LOOP

### Entry Point
**File**: `/home/user/mostlylucid.dse/code_evolver/chat_cli.py`

```python
def main():
    parser = argparse.ArgumentParser(description="Code Evolver - Interactive CLI")
    parser.add_argument("--config", type=str, default="config.yaml")
    args = parser.parse_args()
    
    chat = ChatCLI(config_path=args.config)
    chat.run()

if __name__ == "__main__":
    main()
```

### Main Loop (chat_cli.py:7329)
```python
def run(self):
    """Run the interactive CLI."""
    self.print_welcome()
    
    if not self.client.check_connection():
        console.print("[red]Warning: Cannot connect to Ollama...[/red]")
    
    prompt_text = self.config.get("chat.prompt", "CodeEvolver> ")
    
    while True:
        try:
            # Get user input (blocking)
            if PROMPT_TOOLKIT_AVAILABLE and sys.stdin.isatty():
                user_input = pt_prompt(...)  # prompt_toolkit
            else:
                user_input = console.input(...)  # Rich console
            
            if not user_input:
                continue
            
            # Handle exit
            if user_input.lower() in ['exit', 'quit', 'q']:
                console.print("[cyan]Goodbye![/cyan]")
                break
            
            self.history.append(user_input)
            
            # Parse and execute commands
            if not user_input.startswith('/'):
                self.handle_generate(user_input)  # Default: generate and run
            else:
                cmd = user_input[1:].strip()
                # Route to appropriate handler
                if cmd.lower() == 'help':
                    self.print_help()
                elif cmd.lower() == 'tools':
                    self.handle_tools()
                elif cmd.startswith('workflow '):
                    self.handle_workflow(...)
                elif cmd.startswith('generate '):
                    self.handle_generate(...)
                # ... etc
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted! Cancelling task...[/yellow]")
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    self._save_history()
```

### Initialization (ChatCLI.__init__)

```
ChatCLI initialization:
├─ ConfigManager - Load config.yaml
├─ StatusManager - Live status updates
├─ LLMClientFactory - Create routing client (Ollama, OpenAI, Anthropic)
├─ Registry - Node metadata
├─ NodeRunner - Code execution
├─ Evaluator - Result evaluation
├─ RAG Memory - Qdrant or NumPy-based
└─ BackgroundToolsLoader
   └─ Load ToolsManager in background thread (non-blocking)
```

---

## 8. KEY OBSERVATIONS

### What Exists
1. ✅ **Declarative Workflow Specification** (WorkflowSpec)
2. ✅ **Workflow Builder** (converts overseer output to specs)
3. ✅ **Limited Parallel Execution** (ThreadPoolExecutor for independent steps)
4. ✅ **Subprocess-based Node Execution** (sandboxed)
5. ✅ **Multi-platform Distribution** (Cloud, Edge, Embedded, WASM)
6. ✅ **Background Loading** (Threading for tools)
7. ✅ **MCP Support** (Asyncio-based, separate from main loop)
8. ✅ **Metrics Collection** (Latency, CPU, Memory)
9. ✅ **Interactive CLI** (Prompt-toolkit or Rich console)

### What's Missing
1. ❌ **True Async/Await** - Main loop is blocking/synchronous
2. ❌ **Task Queue** - No Celery, RQ, or similar
3. ❌ **Distributed Execution** - No multi-machine coordination
4. ❌ **Message Queue Integration** - Defined but not implemented
5. ❌ **Scheduler** - No Airflow, Prefect, or cron-based scheduling
6. ❌ **Process Pool** - Uses ThreadPoolExecutor (GIL-bound)
7. ❌ **Streaming/Real-time** - No event-driven architecture

---

## 9. ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────┐
│ chat_cli.py (Main Loop)                                 │
│ ├─ while True:                                          │
│ │  ├─ User Input (blocking)                            │
│ │  └─ Command Routing                                  │
│ │     ├─ handle_generate()                             │
│ │     ├─ handle_workflow()                             │
│ │     └─ handle_run()                                  │
└─────────────────────────────────────────────────────────┘
         │
         ├─────────────────┬──────────────────┐
         │                 │                  │
         ▼                 ▼                  ▼
    ┌──────────┐   ┌──────────────┐   ┌──────────────┐
    │ Overseer │   │ Workflow     │   │ Tools        │
    │ LLM      │   │ Builder      │   │ Manager      │
    └──────────┘   └──────────────┘   └──────────────┘
         │                 │                  │
         └─────────┬───────┴──────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ WorkflowSpec        │
         │ (Declarative)       │
         │ ├─ steps[]          │
         │ ├─ inputs[]         │
         │ └─ outputs[]        │
         └─────────────────────┘
                   │
                   ▼
         ┌─────────────────────────┐
         │ Workflow Executor       │
         │ (chat_cli.py ~line 830) │
         │ ├─ Organize by group    │
         │ └─ ThreadPoolExecutor   │
         └─────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
    ┌─────────┐         ┌──────────┐
    │ Step 1  │         │ Step N   │
    │ LLM/Tool│         │ LLM/Tool │
    └─────────┘         └──────────┘
         │                   │
         └─────────┬─────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ NodeRunner          │
         │ subprocess.Popen()  │
         └─────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼                    ▼
    ┌──────────┐         ┌──────────┐
    │ Metrics  │         │ Output   │
    │ Collection       │ Evaluation
    └──────────┘         └──────────┘
```

---

## 10. FILE LOCATIONS SUMMARY

### Core Execution Files
| File | Purpose | Lines |
|------|---------|-------|
| `chat_cli.py` | Main CLI loop and command routing | 7565 |
| `node_runner.py` | Subprocess-based node execution | 242 |
| `workflow_spec.py` | Workflow specification data structures | 514 |
| `workflow_builder.py` | Converts overseer output to specs | 263 |
| `workflow_tracker.py` | Tracks workflow step execution | ~150 |
| `workflow_distributor.py` | Multi-platform workflow export | 495 |

### Supporting Execution Files
| File | Purpose |
|------|---------|
| `background_tools_loader.py` | Background thread for tool loading |
| `mcp_client_manager.py` | Async MCP server connections |
| `offline_optimizer.py` | Batch optimization scheduler (stub) |
| `tools_manager.py` | Tool registry and invocation (2434 lines) |
| `config_manager.py` | Configuration management |

---

## 11. EXECUTION PATTERNS USED

1. **Sequential Main Loop** - Synchronous CLI with blocking input
2. **Subprocess Isolation** - Each node runs in separate process
3. **Thread Pool for Parallelism** - Limited to dependency-free steps
4. **Overseer-Driven Decomposition** - LLM breaks tasks into steps
5. **Declarative Workflow Specs** - JSON-serializable workflow definitions
6. **Background Loading** - Threading to avoid blocking startup
7. **Signal-Driven Cancellation** - KeyboardInterrupt and EOFError handling

