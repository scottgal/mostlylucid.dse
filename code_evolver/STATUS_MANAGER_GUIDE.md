# Live Status Manager - Real-Time Activity Display

## Overview

The Status Manager provides a **live, self-updating status line** that shows what the system is doing in real-time. This prevents the CLI from appearing frozen during long operations.

## What You'll See

When the system is working, you'll see a live status line like:

```
⚡ anthropic/claude-3-sonnet-20241022 → generate
```

```
⚡ Tool: Write a poem (model: llama3)
```

```
⚡ ollama/nomic-embed-text → embedding
```

The status line:
- ✅ Updates in real-time
- ✅ Overwrites itself (doesn't spam your terminal)
- ✅ Shows which backend/model is being used
- ✅ Clears automatically when operations complete
- ✅ Displays errors if they occur

## Status Types

### 1. LLM Generation Calls
Shows when the system is generating text:

```
⚡ anthropic/claude-3-haiku-20240307 → generate
```

Format: `backend/model → operation`

### 2. Tool Calls
Shows when a tool is being executed:

```
⚡ Tool: Code Generator (model: codellama)
```

Format: `Tool: name (model: model_name)`

### 3. Embedding Calls
Shows when creating embeddings for RAG:

```
⚡ ollama/nomic-embed-text → embedding
```

Format: `backend/model → embedding`

### 4. HTTP Calls
Shows direct HTTP requests (if needed):

```
⚡ POST anthropic → https://api.anthropic.com/v1/messages
```

Format: `METHOD backend → URL`

## How It Works

### Architecture

```
User Request
    ↓
[StatusManager] ← Initialized in ChatCLI
    ↓
├─→ [AnthropicClient] → Shows "anthropic/model → generate"
├─→ [OllamaClient] → Shows "ollama/model → generate"
└─→ [ToolsManager] → Shows "Tool: name (model: X)"
```

### Technical Details

**Thread-Safe:** Uses locks to prevent race conditions

**Non-Blocking:** Updates don't block execution

**Auto-Clearing:** Clears after success or error

**Rich Integration:** Uses Rich console for styled output

## Implementation Details

### Status Manager (src/status_manager.py)

```python
from src.status_manager import get_status_manager

# Get singleton instance
status_mgr = get_status_manager()

# Show LLM call
status_mgr.llm_call("claude-3-haiku", "anthropic", "generate")

# Show tool call
status_mgr.tool_call("Code Generator", "codellama")

# Show embedding call
status_mgr.embedding_call("nomic-embed-text", "ollama")

# Clear status
status_mgr.clear()
```

### Integration Points

**1. Anthropic Client (src/anthropic_client.py:183-186)**
```python
# Before API call
if STATUS_MANAGER_AVAILABLE:
    status_mgr = get_status_manager()
    status_mgr.llm_call(model, "anthropic", "generate")

# After API call (success or error)
if STATUS_MANAGER_AVAILABLE:
    get_status_manager().clear()
```

**2. Ollama Client (src/ollama_client.py:306-309)**
```python
# Before API call
if STATUS_MANAGER_AVAILABLE:
    status_mgr = get_status_manager()
    status_mgr.llm_call(model, "ollama", "generate")

# After API call
if STATUS_MANAGER_AVAILABLE:
    get_status_manager().clear()
```

**3. Tools Manager (src/tools_manager.py:947-950)**
```python
# Before tool execution
if STATUS_MANAGER_AVAILABLE:
    status_mgr = get_status_manager()
    status_mgr.tool_call(tool.name, model)

# After tool execution
if STATUS_MANAGER_AVAILABLE:
    get_status_manager().clear()
```

**4. Chat CLI (chat_cli.py:216-218)**
```python
# Initialize status manager at startup
from src.status_manager import get_status_manager
self.status_manager = get_status_manager(console)
```

## Status Colors

| Status Type | Color | Example |
|-------------|-------|---------|
| LLM Call | Blue | `⚡ anthropic/claude-sonnet → generate` |
| Tool Call | Magenta | `⚡ Tool: Code Generator` |
| Embedding | Green | `⚡ ollama/nomic-embed → embedding` |
| HTTP Call | Cyan | `⚡ POST → https://api.anthropic.com` |
| Processing | Yellow | `⚡ Processing request...` |

## Example Session

```
CodeEvolver> write a poem

⚡ ollama/tinyllama → generate        # Triage/classification
⚡ ollama/nomic-embed-text → embedding # RAG search
⚡ Tool: Write a poem (model: llama3)  # Tool selection
⚡ anthropic/claude-3-sonnet → generate # Actual generation

[Poem appears here]
```

Each status line overwrites the previous one, so you only see the current operation.

## Benefits

### 1. **Visibility**
- See exactly what the system is doing
- Know which model/backend is being used
- Understand the workflow steps

### 2. **No More "Is It Frozen?"**
- Status updates show the system is working
- Long operations display progress
- Clear indication when waiting for API responses

### 3. **Debugging**
- Easily see which backend a model is routed to
- Track the sequence of operations
- Identify slow operations

### 4. **Cost Awareness**
- See when paid APIs (Anthropic) are being used
- See when free local models (Ollama) are being used
- Make informed decisions about model usage

## Troubleshooting

### Status not showing?

1. **Check status manager is available:**
   ```python
   from src.status_manager import STATUS_MANAGER_AVAILABLE
   print(STATUS_MANAGER_AVAILABLE)  # Should be True
   ```

2. **Check it's initialized:**
   ```python
   from src.status_manager import get_status_manager
   status = get_status_manager()
   print(status._enabled)  # Should be True
   ```

3. **Check console is attached:**
   - Status manager needs a Rich console instance
   - Should be initialized in ChatCLI.__init__()

### Status stuck/not clearing?

- Manually clear it:
  ```python
  from src.status_manager import clear_status
  clear_status()
  ```

- Check for exceptions in client code
- Status should auto-clear after operations

### Want to disable it temporarily?

```python
from src.status_manager import get_status_manager
get_status_manager().set_enabled(False)
```

## Future Enhancements

Possible future additions:

- [ ] Progress bars for long operations
- [ ] Estimated time remaining
- [ ] Token usage display
- [ ] Cost estimates in real-time
- [ ] Multi-line status for parallel operations
- [ ] History of recent operations

## API Reference

### StatusManager Methods

```python
class StatusManager:
    def update(message: str, style: str = "cyan")
        """Update status line with custom message"""

    def clear()
        """Clear the status line"""

    def http_call(method: str, url: str, backend: str = None)
        """Show HTTP request status"""

    def tool_call(tool_name: str, model: str = None)
        """Show tool execution status"""

    def llm_call(model: str, backend: str, operation: str = "generate")
        """Show LLM generation status"""

    def embedding_call(model: str, backend: str)
        """Show embedding generation status"""

    def processing(message: str)
        """Show generic processing status"""

    def set_enabled(enabled: bool)
        """Enable or disable status updates"""
```

### Convenience Functions

```python
from src.status_manager import set_status, clear_status

set_status("Custom message", style="yellow")
clear_status()
```

## Summary

The Status Manager provides real-time visibility into what the system is doing, preventing the "frozen" feeling during long operations. It automatically shows:

- Which backend is being used (Anthropic vs Ollama)
- Which model is processing the request
- Which tools are being invoked
- When operations complete

All with a clean, self-updating status line that doesn't clutter your terminal!

---

**Status:** ✅ Fully implemented and integrated across all clients and tools
