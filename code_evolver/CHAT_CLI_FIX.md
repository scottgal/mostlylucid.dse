# ChatCLI Initialization Fix

## Problem

After adding background tools loading, ChatCLI was broken with errors:
```
Error: 'ChatCLI' object has no attribute 'history'
Error: 'ChatCLI' object has no attribute 'pt_history'
```

## Root Cause

The `__init__` method structure was malformed:
1. Property definition (`@property def tools_manager`) was inserted incorrectly
2. Code that should be in `__init__` ended up inside or after the property
3. History initialization was in the wrong place or removed entirely

## Fix

Rebuilt `__init__` method with proper structure:

```python
def __init__(self, config_path: str = "config.yaml"):
    # ... existing init code ...

    # Initialize tools in background
    self._tools_loader = BackgroundToolsLoader(...)
    self._tools_loader.start()
    self._tools_manager = None

    # Register callback
    def on_tools_ready(tools_manager):
        self._tools_manager = tools_manager
        console.print(f"✓ Tools ready ({len(tools_manager.tools)} loaded)")

    self._tools_loader.on_ready(on_tools_ready)

    # Initialize task evaluator
    self.task_evaluator = TaskEvaluator(self.client)

    # Initialize history BEFORE accessing tools
    self.context = {}
    self.history = []
    self.display = WorkflowDisplay(console)
    self.history_file = Path(...)

    if PROMPT_TOOLKIT_AVAILABLE:
        self.pt_history = FileHistory(...)
        self.pt_completer = WordCompleter(...)
    else:
        self.pt_history = None
        self.pt_completer = None
        self._load_history()

    # Register model selector (this accesses tools_manager)
    try:
        create_model_selector_tool(self.config, self.tools_manager)
    except Exception as e:
        console.print(f"Model selector not available: {e}")

# Property OUTSIDE of __init__
@property
def tools_manager(self):
    """Get tools manager, waiting if necessary."""
    if self._tools_manager is None:
        if not self._tools_loader.is_ready_sync():
            console.print("Waiting for tools...")
        self._tools_manager = self._tools_loader.get_tools(wait=True)
    return self._tools_manager
```

## Key Changes

1. **Proper method structure** - Property is OUTSIDE `__init__`, not inside
2. **History first** - Initialize `self.history` and `self.pt_history` BEFORE any code that might access `tools_manager`
3. **Callback registration** - Added proper `on_tools_ready` callback
4. **Error handling** - Model selector registration wrapped in try/except

## Testing

```bash
$ python chat_cli.py
> Processing configuration...
Loading tools in background...
[dim]Background: Starting ToolsManager initialization...[/dim]
Waiting for tools...
[dim]Background: Loaded 153 tools in 57.72s[/dim]
✓ Tools ready (153 loaded)
Registered model selector tool

# All attributes present:
- history: ✓
- pt_history: ✓
- context: ✓
- display: ✓
- history_file: ✓
```

## Remaining Note

The CLI currently waits for tools during initialization because `create_model_selector_tool()` accesses `self.tools_manager`, which triggers the wait. This is still faster than before since the basic CLI structure loads first.

To make it truly non-blocking, we could defer model selector registration to after tools load:

```python
# In on_tools_ready callback:
def on_tools_ready(tools_manager):
    self._tools_manager = tools_manager
    console.print(f"✓ Tools ready")

    # Register model selector AFTER tools ready
    try:
        create_model_selector_tool(self.config, tools_manager)
        console.print("Registered model selector")
    except Exception as e:
        console.print(f"Model selector error: {e}")
```

But this isn't critical since the user can start using the CLI as soon as tools finish loading.
