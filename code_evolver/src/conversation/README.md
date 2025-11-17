# Conversation Tool

A comprehensive conversation management system with multi-chat context memory, auto-summarization, and semantic search capabilities.

## Features

### 1. Multi-Chat Context Memory
- Remembers all messages in a conversation
- Retrieves conversation history on demand
- Supports multiple concurrent conversations

### 2. Auto-Summarization
- Uses gemma3:1b for fast, efficient summarization
- Context-aware: triggers when approaching model's context window
- Incremental summarization: keeps recent messages full, summarizes older ones
- Optimizes for response speed while maintaining accuracy

### 3. Volatile Qdrant Storage
- Each conversation gets its own Qdrant collection
- Semantic search within conversations
- Collections are deleted when conversation ends
- Conversation metadata persists for future retrieval

### 4. Context Optimization
- Dynamically adjusts context based on model's window size
- Balances summary, related context, and recent messages
- Token estimation ensures staying within limits
- Optimizes for fast responses

### 5. Related Context Retrieval
- Finds similar past conversations using embeddings
- Includes relevant snippets in current conversation
- Size-optimized for context window

### 6. Intent Detection
- Comprehensive pattern matching (70+ patterns)
- Distinguishes "let's chat" from "write a conversation between X and Y"
- Minimal LLM usage for speed
- Extracts conversation topic automatically

### 7. Performance Tracking
- Tracks response time per message
- Records conversation metadata
- Monitors context window utilization

## Architecture

```
conversation/
├── __init__.py
├── conversation_storage.py    # Qdrant volatile storage management
├── context_manager.py          # Context window optimization
├── summarizer.py               # Auto-summarization with gemma3:1b
├── intent_detector.py          # Conversation intent detection
├── embedder.py                 # Embedding & retrieval of related conversations
└── conversation_tool.py        # Main coordinator
```

## Usage

### CLI Slash Commands

#### Start a conversation:
```bash
/conversation start software architecture
```

#### End a conversation:
```bash
/conversation end
# or
/conversation end software architecture
```

### Python API

```python
from code_evolver.src.conversation import ConversationTool

# Initialize
tool = ConversationTool.create_from_config_file(
    "code_evolver/config.yaml",
    conversation_model="gemma3:1b"
)

# Start conversation
result = tool.start_conversation(topic="Python best practices")
print(f"Started: {result['conversation_id']}")

# Add user message
tool.add_user_message("What are type hints?")

# Prepare context for response (optimized for model)
context = tool.prepare_context_for_response(
    user_message="What are type hints?",
    response_model="llama3"
)

# Use context.messages, context.summary, context.related_context for response

# Add assistant response with performance tracking
tool.add_assistant_message(
    content="Type hints are...",
    performance_data={"response_time": 1.2, "tokens": 150}
)

# End conversation (saves metadata for future retrieval)
result = tool.end_conversation(save_metadata=True)
print(f"Summary: {result['summary']}")
print(f"Key points: {result['key_points']}")
```

### Tool Wrapper (JSON API)

```bash
# Start conversation
echo '{"action": "start", "topic": "AI ethics"}' | \
  python code_evolver/tools/executable/conversation_manager.py

# Detect intent
echo '{"action": "detect_intent", "user_input": "let'\''s chat about ML"}' | \
  python code_evolver/tools/executable/conversation_manager.py

# Prepare context
echo '{"action": "prepare_context", "user_message": "Tell me more", "response_model": "llama3"}' | \
  python code_evolver/tools/executable/conversation_manager.py

# End conversation
echo '{"action": "end", "save_metadata": true}' | \
  python code_evolver/tools/executable/conversation_manager.py
```

## Configuration

The conversation tool uses the main `config.yaml` configuration:

```yaml
llm:
  models:
    gemma3_1b:
      name: "gemma3:1b"
      backend: "ollama"
      context_window: 8192
      speed: "very-fast"

  defaults:
    veryfast: gemma3_1b

rag_memory:
  qdrant_url: "http://localhost:6333"
  use_qdrant: true

  embedding:
    default: nomic_embed
```

## Intent Detection Patterns

The tool recognizes 70+ conversation patterns including:

**Conversation starters:**
- "let's chat/talk/discuss"
- "up for a conversation"
- "can we talk about..."
- "wanna discuss..."
- "ready to chat"
- And many more...

**Generation requests (NOT conversations):**
- "write a conversation between X and Y"
- "create a dialogue for..."
- "script a scene where..."
- "example conversation about..."
- And many more...

## Context Optimization

The context manager automatically optimizes content to fit the model's window:

1. **Always includes** (if available):
   - Conversation summary
   - Related context from past conversations

2. **Includes as many recent messages as fit**

3. **Triggers summarization** when conversation reaches 70% of context window

4. **Smart truncation** if individual messages are too large

## Performance

- **Intent detection**: < 0.1s (pattern matching), ~0.5s (LLM fallback)
- **Summarization**: ~1-2s with gemma3:1b
- **Context preparation**: ~0.3-0.5s
- **Context optimization**: Real-time, < 0.1s

## Requirements

- Python 3.8+
- Qdrant server running at `http://localhost:6333`
- Ollama with:
  - `gemma3:1b` (conversation management)
  - `nomic-embed-text` (embeddings)
- Dependencies:
  - `qdrant-client`
  - `requests`
  - `pyyaml`

## Examples

### Example 1: Natural Language Intent Detection

```python
detector = ConversationIntentDetector()

# Conversation request
result = detector.detect_intent("let's have a chat about Python")
# → {intent: "start_conversation", confidence: 0.9, topic: "Python"}

# Generation request
result = detector.detect_intent("write a conversation between Alice and Bob")
# → {intent: "generate_dialogue", confidence: 0.95, topic: None}

# Regular task
result = detector.detect_intent("what is a list comprehension?")
# → {intent: "task", confidence: 0.5, topic: None}
```

### Example 2: Context Window Optimization

```python
manager = ContextMemoryManager(model_name="gemma3:1b")

# Check if summarization needed
messages = [...]  # 50 messages
if manager.should_summarize(messages):
    to_summarize, to_keep = manager.get_messages_for_summary(messages, keep_recent=3)
    # Summarize old messages, keep 3 recent ones

# Optimize for model
optimized = manager.optimize_context(
    messages=messages,
    summary="Previous discussion about...",
    related_context=["Related snippet 1", "Related snippet 2"]
)
# → Returns messages that fit in context window
```

### Example 3: Complete Conversation Flow

```python
# Start
tool = ConversationTool()
tool.start_conversation("Python debugging")

# User message
tool.add_user_message("How do I use pdb?")

# Prepare context (includes summary + related conversations)
context = tool.prepare_context_for_response(
    user_message="How do I use pdb?",
    response_model="llama3"
)

# Generate response using context
response = generate_llm_response(context)

# Save response
tool.add_assistant_message(
    content=response,
    performance_data={"response_time": 1.5}
)

# End and save
result = tool.end_conversation()
# → Saves summary and key points for future retrieval
```

## Future Enhancements

- [ ] Multi-turn conversation branching
- [ ] Conversation export (JSON, Markdown)
- [ ] Custom summarization prompts
- [ ] Conversation merging
- [ ] Advanced filtering (by date, topic, etc.)
- [ ] Conversation analytics dashboard

## License

Part of the Code Evolver DSE system.

## Smart Conversations (Living MCP)

The conversation tool now features **smart orchestration** - a "living MCP" that dynamically calls tools and generates workflows during conversations.

### Smart Features

#### 1. **Automatic Task Detection**
- Analyzes user messages to detect task requests
- Distinguishes between conversation and actionable tasks
- Classifies task type and complexity

#### 2. **Dynamic Tool Selection**
- Uses gemma3:1b to select appropriate tools
- Considers available tools and task requirements
- Recommends execution order for multiple tools

#### 3. **Workflow Generation**
- Creates optimal workflows for complex tasks
- Identifies dependencies between steps
- Finds opportunities for parallel execution

#### 4. **Parallel Task Execution**
- **Runs tools in background** (non-blocking)
- Conversation continues while tasks execute
- Returns task IDs for status tracking

#### 5. **CPU/GPU Load Monitoring**
- Checks system resources before starting tasks
- Queues tasks when system is busy
- Automatically starts when resources available
- Configurable thresholds (default: 80% CPU, 85% memory)

### Usage

```python
from code_evolver.src.conversation import ConversationTool

# Initialize with smart orchestration
tool = ConversationTool.create_from_config_file(
    "code_evolver/config.yaml",
    conversation_model="gemma3:1b"
)

# Start conversation
tool.start_conversation("Python development")

# User says: "Can you analyze this codebase for bugs?"
# Smart orchestrator:
# 1. Detects task (code analysis)
# 2. Selects tools (code analyzer, linter)
# 3. Generates workflow
# 4. Checks system load
# 5. Starts execution in background
# 6. Returns immediately

result = tool.orchestrator.orchestrate_with_parallel_execution(
    user_message="Can you analyze this codebase for bugs?",
    conversation_context="Previous conversation context..."
)

# Immediate response
print(result["immediate_response"])
# → "I understand you want to analyze codebase for bugs. I'm working on that in the background. Feel free to continue our conversation while I work on it!"

# Check task status later
task_id = result.get("task_id")
if task_id:
    status = tool.orchestrator.get_task_status(task_id)
    print(f"Status: {status['status']}")  # queued, running, completed, or failed
    
    if status['status'] == 'completed':
        print(f"Result: {status['result']}")
```

### System Load Awareness

```python
# Check current system load
load = tool.orchestrator.check_system_load()
print(f"CPU: {load['cpu_percent']}%")
print(f"Memory: {load['memory_percent']}%")
print(f"Too busy: {load['is_busy']}")

# Task will wait if system busy
task_id = tool.orchestrator.execute_task_in_background(
    task_id=None,
    task_description="Generate documentation",
    workflow=workflow_spec,
    wait_if_busy=True  # Waits up to 5 minutes for resources
)
```

### Task Management

```python
# List active tasks
active_tasks = tool.orchestrator.list_active_tasks()
for task in active_tasks:
    print(f"{task['task_id']}: {task['description']} - {task['status']}")

# Get specific task status
status = tool.orchestrator.get_task_status(task_id)
if status:
    print(f"Started: {status['started_at']}")
    print(f"Duration: {status.get('completed_at', time.time()) - status['started_at']}s")
```

### Example: Smart Conversation Flow

```
User: "Let's discuss Python best practices"
Assistant: [Starts conversation]

User: "Can you refactor my code to follow PEP 8?"
Smart Orchestrator:
  → Detects task: code_generation
  → Selects tools: [code_analyzer, pep8_formatter]
  → Generates 3-step workflow
  → Checks system: CPU 45%, Memory 60% ✓
  → Starts background task: task_abc123
  → Returns immediately
