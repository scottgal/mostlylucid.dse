# CLI Visualization Panels

Beautiful, real-time ASCII art visualizations for Code Evolver's CLI interface.

## Features

✨ **Workflow Flowcharts** - ASCII art flowcharts showing workflow execution in real-time
🔧 **Tool Assembly** - Animated visualization of tools being built component-by-component
🎯 **Modular Design** - Easy to extend with new panel types
📦 **Drop-in Replacement** - Backward compatible with existing WorkflowDisplay
⚡ **Live Updates** - Real-time refresh using Rich's Live display
🎨 **Beautiful ASCII Art** - Professional-looking box drawing characters

## Quick Start

### Basic Demo

```bash
cd code_evolver
python demo_panels.py
```

This will run three comprehensive demos showing:
1. Workflow flowchart visualization
2. Tool assembly animation
3. Enhanced workflow display (integration example)

### Integration into chat_cli.py

There are two ways to integrate the panels into your CLI:

#### Option 1: Drop-in Replacement (Recommended)

Replace the existing `WorkflowDisplay` with `EnhancedWorkflowDisplay`:

```python
# In chat_cli.py, change this line:
from src.enhanced_workflow_display import EnhancedWorkflowDisplay

# In ChatCLI.__init__:
self.display = EnhancedWorkflowDisplay(console, enable_panels=False)

# Later, when you want to enable visualizations:
self.display.enable_live_panels()
```

All existing code will work as-is! The enhanced display is 100% backward compatible.

#### Option 2: Selective Usage

Use panels only for specific operations:

```python
from src.cli_panels import (
    create_workflow_panel,
    create_tool_assembly_panel,
    WorkflowStep,
    ToolComponent,
    StepStatus
)
from rich.live import Live

# Create workflow panel
workflow_panel = create_workflow_panel("My Workflow")

# Add steps
workflow_panel.add_step(WorkflowStep(
    id="step1",
    name="Parse Input",
    tool_name="parser",
    description="Extract structured data"
))

# Use Live display for real-time updates
with Live(workflow_panel.render(), refresh_per_second=4) as live:
    # Execute workflow
    workflow_panel.update_step("step1", StepStatus.ACTIVE)
    live.update(workflow_panel.render())

    # ... do work ...

    workflow_panel.update_step("step1", StepStatus.COMPLETED)
    live.update(workflow_panel.render())
```

## Architecture

### Module Structure

```
code_evolver/
├── src/
│   ├── cli_panels.py                 # Core panel classes
│   └── enhanced_workflow_display.py  # Enhanced WorkflowDisplay
└── demo_panels.py                    # Demonstration script
```

### Core Classes

#### `WorkflowFlowchartPanel`

Displays workflow steps as ASCII art flowchart.

```python
from src.cli_panels import WorkflowFlowchartPanel, WorkflowStep, StepStatus

panel = WorkflowFlowchartPanel("Code Generation")

# Add steps
panel.add_step(WorkflowStep(
    id="analyze",
    name="Analyze Requirements",
    tool_name="analyzer",
    description="Extract features and constraints"
))

# Update step status
panel.update_step("analyze", StepStatus.ACTIVE)
panel.update_step("analyze", StepStatus.COMPLETED)

# Render panel
rich_panel = panel.render()
```

**Output Example:**
```
╔════════════════════════════════════════════════════════════════╗
║ ✓ Step 1: Analyze Requirements                                ║
║    Tool: analyzer                                              ║
║    Extract features and constraints                            ║
║    Duration: 1.23s                                             ║
╚════════════════════════════════════════════════════════════════╝
     ║
     ▼
╔════════════════════════════════════════════════════════════════╗
║ ⚙ Step 2: Generate Code                                       ║
║    Tool: code_generator                                        ║
╚════════════════════════════════════════════════════════════════╝
```

#### `ToolAssemblyPanel`

Shows tool components being built with progress tracking.

```python
from src.cli_panels import ToolAssemblyPanel, ToolComponent, StepStatus

panel = ToolAssemblyPanel("DataValidator")

# Add components
panel.add_component(ToolComponent(
    name="validate_email",
    type="function",
    lines_of_code=15
))

# Update component status
panel.update_component("validate_email", StepStatus.ACTIVE)
panel.update_component("validate_email", StepStatus.COMPLETED)

# Set progress message
panel.set_progress("Building validation logic...")

# Render panel
rich_panel = panel.render()
```

**Output Example:**
```
┌─ Tool Assembly ────────────────────────────────────────────┐
│                                                            │
│ 🔧 Building: DataValidator                                │
│                                                            │
│ ⚡ Building validation logic...                           │
│                                                            │
│ Components:                                                │
│                                                            │
│  ✅ FUNCTION      validate_email  (15 lines)             │
│  🔄 CLASS         EmailValidator  (45 lines)             │
│  ⬜ FUNCTION      main  (8 lines)                        │
│                                                            │
│ Progress: 1/3 components  |  Total Lines: 68              │
└────────────────────────────────────────────────────────────┘
```

#### `EnhancedWorkflowDisplay`

Drop-in replacement for WorkflowDisplay with panel support.

```python
from src.enhanced_workflow_display import EnhancedWorkflowDisplay
from rich.console import Console

console = Console()
display = EnhancedWorkflowDisplay(console, enable_panels=True)

# Use existing WorkflowDisplay API (backward compatible)
display.start_workflow("Generate API Client")
display.start_stage("Planning", "Analyzing OpenAPI spec")
display.complete_stage("Planning", "Found 15 endpoints")

# New panel features
display.show_workflow_flowchart("API Generation")
display.show_tool_assembly("APIClient")

# Add workflow steps
display.add_workflow_step("step1", "Parse Spec", "openapi_parser")
display.update_workflow_step("step1", StepStatus.ACTIVE)
display.update_workflow_step("step1", StepStatus.COMPLETED)

# Add tool components
display.add_tool_component("parse_endpoint", "function", 20)
display.update_tool_component("parse_endpoint", StepStatus.COMPLETED)

# Cleanup when done
display.cleanup()
```

#### `LivePanelDisplay`

Manages live updating display for multiple panels.

```python
from src.cli_panels import LivePanelDisplay, create_workflow_panel

console = Console()
live_display = LivePanelDisplay(console, refresh_per_second=4)

# Add panels
workflow_panel = create_workflow_panel("My Workflow")
live_display.add_panel("workflow", workflow_panel)

# Start live updates
live_display.start()

# Make changes (display auto-updates)
workflow_panel.add_step(WorkflowStep(...))

# Stop when done
live_display.stop()

# Or use as context manager
with LivePanelDisplay(console) as live:
    live.add_panel("workflow", workflow_panel)
    # ... do work ...
```

### Status Types

```python
class StepStatus(Enum):
    PENDING = "pending"      # Not started (○ dim)
    ACTIVE = "active"        # Currently executing (⚙ yellow)
    COMPLETED = "completed"  # Successfully done (✓ green)
    FAILED = "failed"        # Error occurred (✗ red)
    SKIPPED = "skipped"      # Skipped (⊝ dim)
```

## Usage Examples

### Example 1: Simple Workflow Visualization

```python
from src.cli_panels import create_workflow_panel, WorkflowStep, StepStatus
from rich.console import Console
from rich.live import Live
import time

console = Console()
panel = create_workflow_panel("Data Processing")

# Add steps
steps = ["Load Data", "Transform", "Validate", "Export"]
for i, name in enumerate(steps):
    panel.add_step(WorkflowStep(
        id=f"step{i}",
        name=name,
        status=StepStatus.PENDING
    ))

# Execute with live updates
with Live(panel.render(), console=console, refresh_per_second=4) as live:
    for i in range(len(steps)):
        panel.update_step(f"step{i}", StepStatus.ACTIVE)
        live.update(panel.render())
        time.sleep(1)

        panel.update_step(f"step{i}", StepStatus.COMPLETED)
        live.update(panel.render())
```

### Example 2: Tool Assembly with Progress

```python
from src.cli_panels import create_tool_assembly_panel, ToolComponent, StepStatus
from rich.live import Live
import time

panel = create_tool_assembly_panel("UserService")

# Define components
components = [
    ("imports", "import", 5),
    ("UserModel", "class", 30),
    ("create_user", "function", 15),
    ("update_user", "function", 12),
]

for name, type_, lines in components:
    panel.add_component(ToolComponent(name, type_, lines))

# Build with live updates
with Live(panel.render(), refresh_per_second=4) as live:
    for name, _, _ in components:
        panel.set_progress(f"Building {name}...")
        panel.update_component(name, StepStatus.ACTIVE)
        live.update(panel.render())
        time.sleep(1)

        panel.update_component(name, StepStatus.COMPLETED)
        live.update(panel.render())

    panel.set_progress("Build complete!")
    live.update(panel.render())
    time.sleep(1)
```

### Example 3: Complete Integration

```python
from src.enhanced_workflow_display import EnhancedWorkflowDisplay
from src.cli_panels import StepStatus
from rich.console import Console

console = Console()

with EnhancedWorkflowDisplay(console, enable_panels=True) as display:
    # Start workflow
    display.start_workflow("API Client Generation")
    display.show_workflow_flowchart()

    # Add and execute steps
    steps = [
        ("parse", "Parse OpenAPI Spec", "parser"),
        ("generate", "Generate Client Code", "code_gen"),
        ("test", "Generate Tests", "test_gen"),
    ]

    for step_id, name, tool in steps:
        display.add_workflow_step(step_id, name, tool)

    for step_id, name, _ in steps:
        display.start_stage(name)
        display.update_workflow_step(step_id, StepStatus.ACTIVE)
        # ... do work ...
        display.complete_stage(name)
        display.update_workflow_step(step_id, StepStatus.COMPLETED)

    # Show tool being built
    display.show_tool_assembly("APIClient")
    components = [
        ("HTTPClient", "class", 40),
        ("request", "function", 25),
        ("authenticate", "function", 15),
    ]

    for name, type_, lines in components:
        display.add_tool_component(name, type_, lines)
        display.update_tool_component(name, StepStatus.ACTIVE)
        # ... build ...
        display.update_tool_component(name, StepStatus.COMPLETED)
```

## Configuration

### Panel Refresh Rate

Control how often panels update:

```python
# Fast refresh (smooth but more CPU)
live_display = LivePanelDisplay(console, refresh_per_second=10)

# Slow refresh (less CPU)
live_display = LivePanelDisplay(console, refresh_per_second=2)

# Default is 4 refreshes/second
```

### Enabling/Disabling Panels

```python
display = EnhancedWorkflowDisplay(console, enable_panels=False)

# Enable later
display.enable_live_panels(refresh_per_second=4)

# Disable
display.disable_live_panels()
```

## Best Practices

1. **Use Context Managers**: Always use `with` statements for automatic cleanup
   ```python
   with EnhancedWorkflowDisplay(console, enable_panels=True) as display:
       # ... use display ...
   # Automatically cleaned up
   ```

2. **Update Frequently**: Call `live.update()` or `display.update()` after state changes
   ```python
   panel.update_step("step1", StepStatus.ACTIVE)
   live.update(panel.render())  # Show the change immediately
   ```

3. **Thread Safety**: All panel classes use locks for thread-safe updates
   ```python
   # Safe to update from multiple threads
   panel.update_step("step1", StepStatus.COMPLETED)
   ```

4. **Cleanup Resources**: Always cleanup when done
   ```python
   display.cleanup()  # or use context manager
   ```

5. **Backward Compatibility**: Keep existing code working
   ```python
   # Old code still works
   display.start_stage("Planning")
   display.complete_stage("Planning", "Done")

   # New features optional
   if user_wants_visualization:
       display.enable_live_panels()
   ```

## Extending the System

### Creating a Custom Panel

```python
from rich.panel import Panel
from rich.text import Text
import threading

class MyCustomPanel:
    def __init__(self, title: str):
        self.title = title
        self._data = []
        self._lock = threading.Lock()

    def add_data(self, item):
        with self._lock:
            self._data.append(item)

    def render(self) -> Panel:
        with self._lock:
            content = Text("\n".join(str(item) for item in self._data))
            return Panel(
                content,
                title=f"[bold]{self.title}[/bold]",
                border_style="cyan"
            )
```

### Adding to Live Display

```python
custom_panel = MyCustomPanel("My Data")
live_display.add_panel("custom", custom_panel)

# Update panel
custom_panel.add_data("New item")
live_display.update()  # Refresh display
```

## Troubleshooting

### Panels Not Updating

Make sure to call `update()` after changes:
```python
panel.update_step("step1", StepStatus.COMPLETED)
live.update(panel.render())  # Don't forget this!
```

### Display Flickering

Reduce refresh rate:
```python
LivePanelDisplay(console, refresh_per_second=2)  # Slower = less flicker
```

### Unicode Characters Not Showing

The system uses box drawing characters (╔═╗ etc.). Make sure your terminal supports UTF-8:
```bash
export LANG=en_US.UTF-8
```

### Performance Issues

For large workflows, limit refresh rate:
```python
# Update only when needed
with Live(panel.render(), refresh_per_second=1) as live:
    # Only major updates
    panel.update_step("step1", StepStatus.COMPLETED)
    live.update(panel.render())
```

## License

Part of Code Evolver - see main project license.

## Contributing

To add new panel types:

1. Create panel class in `src/cli_panels.py`
2. Implement `render()` method returning Rich Panel
3. Add thread-safe state management with locks
4. Create factory function for convenience
5. Add to `CompositePanelView` if needed
6. Write tests in demo script

## Future Enhancements

Planned features:
- [ ] Dependency graph visualization
- [ ] Performance metrics panel
- [ ] Error/warning timeline
- [ ] Interactive panel navigation
- [ ] Export flowcharts to SVG/PNG
- [ ] Custom themes and color schemes
- [ ] Parallel workflow visualization
- [ ] Real-time logs panel

## Credits

Built with [Rich](https://github.com/Textualize/rich) for terminal formatting.
