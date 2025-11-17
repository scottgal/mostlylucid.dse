# Tool Feedback Loop System

**Self-Optimizing Tool Selection Through Learning**

## Overview

The feedback loop system enables mostlylucid DiSE to learn from successes and failures, improving tool selection over time. This creates a self-optimizing system where the RAG-based tool search gets smarter with each task.

## How It Works

### 1. Tool Selection (RAG-Based)
When you request a task:
```
-> Searching for relevant tools
  Found 3 tools: conversation_manager, Connect SignalR, Optimize Cluster
```

The system:
- Uses semantic search to find relevant tools
- Calculates fitness scores based on multiple factors
- **NEW**: Checks historical feedback for similar tasks
- Adjusts scores based on past successes/failures

### 2. Feedback Recording
After task completion, the system automatically records:

**Positive Feedback** (quality_score >= 0.7):
- Task completed successfully
- Tool worked well for this type of prompt
- Stored with embeddings for semantic matching

**Negative Feedback** (task failed):
- Task did not complete
- Tool was not appropriate
- Prevents future misuse for similar tasks

### 3. Feedback Integration
During tool search, the fitness calculation now includes:

```python
# FEEDBACK SCORE: Learn from past successes and failures
feedback_score = self.get_tool_feedback_score(tool.tool_id, query)
fitness += feedback_score  # Add/subtract based on past feedback
```

**Scoring:**
- Positive feedback: +10 to +50 points
- Negative feedback: -10 to -50 points
- Weighted by semantic similarity to current task
- More relevant feedback = higher weight

## Architecture

### Storage
Feedback is stored in RAG as embeddings:
```yaml
Artifact:
  artifact_id: feedback_positive_tool_id_abc123
  type: PATTERN
  tags: [tool_feedback, positive, tool_id]
  metadata:
    tool_id: "conversation_manager"
    prompt: "Start a new conversation about X"
    feedback_type: "positive"
    quality_score: 0.85
    timestamp: "2025-11-17T..."
  auto_embed: true  # Enables semantic search
```

### Semantic Matching
The system uses **semantic similarity** between:
- Current task prompt
- Historical feedback prompts

This means feedback from "write a story about dragons" will influence selection for "write a tale about fantasy creatures" (semantically similar) but NOT "build a calculator" (semantically different).

## Methods

### `record_tool_feedback()`
**Location**: `src/tools_manager.py`

Records positive or negative feedback:
```python
tools_manager.record_tool_feedback(
    tool_id="conversation_manager",
    prompt="Start a new conversation",
    feedback_type="positive",  # or "negative"
    reason="Task completed with quality 0.85",
    metadata={"quality_score": 0.85}
)
```

### `get_tool_feedback_score()`
**Location**: `src/tools_manager.py`

Calculates feedback adjustment for fitness scoring:
```python
feedback_score = tools_manager.get_tool_feedback_score(
    tool_id="conversation_manager",
    query="Begin a new chat session"
)
# Returns -50 to +50 points adjustment
```

### `_record_tool_feedback_on_completion()`
**Location**: `chat_cli.py`

Automatically called after task completion:
```python
self._record_tool_feedback_on_completion(
    description="Write a function to parse JSON",
    quality_score=0.85,
    success=True
)
```

## Feedback Criteria

### Positive Feedback Recorded When:
- `success = True`
- `quality_score >= 0.7` → Strong positive signal
- `quality_score >= 0.5` → Acceptable positive signal

### Negative Feedback Recorded When:
- `success = False` (task failed)
- Any quality score (doesn't matter if it didn't work)

### No Feedback Recorded When:
- `success = True` but `quality_score < 0.5` (too ambiguous)

## Self-Optimization Flow

```
Task Request
    ↓
RAG Tool Search
    ↓
Calculate Fitness (includes feedback)
    ↓
Select Best Tool
    ↓
Execute Task
    ↓
Evaluate Quality
    ↓
Record Feedback ← Stored in RAG with embeddings
    ↓
[LOOP] Next Task Benefits from Previous Feedback
```

## Example Learning Scenario

**Day 1**: User asks "Write a REST API client"
- System selects "general" tool (no feedback yet)
- Task succeeds with quality 0.9
- **Positive feedback recorded**

**Day 2**: User asks "Create an HTTP endpoint wrapper"
- System searches for relevant tools
- Finds "general" tool with positive feedback for "REST API" task
- Semantic similarity: 0.8 (very similar)
- **Fitness boosted by +36 points** (positive + high relevance)
- "general" tool selected with higher confidence

**Day 3**: User asks "Build a calculator"
- System searches for relevant tools
- Finds "general" tool with positive feedback for "REST API" task
- Semantic similarity: 0.1 (not similar)
- **Fitness boost: only +2 points** (positive but not relevant)
- Other tools may rank higher

## Benefits

1. **Self-Improving**: Gets smarter with each task
2. **Context-Aware**: Feedback weighted by semantic similarity
3. **Automatic**: No manual intervention required
4. **Transparent**: Feedback stored in RAG for inspection
5. **Fail-Safe**: Errors in feedback system don't break tasks

## Monitoring Feedback

### View Feedback in RAG:
```python
feedback = rag.find_by_tags(["tool_feedback", "positive"], limit=10)
for artifact in feedback:
    print(f"Tool: {artifact.metadata['tool_id']}")
    print(f"Prompt: {artifact.metadata['prompt']}")
    print(f"Score: {artifact.metadata.get('quality_score')}")
```

### Check Tool's Feedback Score:
```python
score = tools_manager.get_tool_feedback_score(
    tool_id="conversation_manager",
    query="Start a conversation"
)
print(f"Feedback adjustment: {score:+.1f} points")
```

## Technical Notes

- Feedback uses simple Jaccard similarity for prompt matching
- Could be enhanced with actual embedding similarity
- Feedback capped at +/- 50 points to prevent overwhelming other factors
- Only the top-ranked tool receives feedback (most responsible)
- Feedback is non-blocking (failures logged but don't break tasks)

## Future Enhancements

- [ ] Use actual embedding similarity instead of Jaccard
- [ ] Allow multiple tools to receive feedback
- [ ] Add feedback decay (older feedback = less weight)
- [ ] Expose feedback in CLI (`/tool feedback <tool_id>`)
- [ ] Add manual feedback mechanism (`/feedback <tool_id> positive|negative`)
- [ ] Visualize feedback trends over time

---

**Result**: The system now learns from every task, continuously improving tool selection accuracy.
