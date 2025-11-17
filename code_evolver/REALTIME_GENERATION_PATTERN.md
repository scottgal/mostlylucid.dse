# Real-Time Generation Pattern - Fast LLM → Better LLM

**Use Case**: Generate content in real-time (streaming), optimize later

---

## The Pattern

### Phase 1 (Interactive): Real-Time with Fast LLM

**Goal**: User sees content appearing IMMEDIATELY

**Approach**:
```
User request
  ↓
VERY fast LLM (tinyllama 1b, ~100ms/token)
  ↓
Stream output to user in real-time
  ↓
Optional: "Shaping" stage with another fast LLM
  ↓
User has content NOW (even if not perfect)
```

**Example**: Blog post generation
- User: "Write a blog post about Python async"
- Tinyllama 1b: Streams 500 words in 5 seconds
- User reads while it generates
- "Good enough" quality for initial draft

### Phase 2 (Optimize): Better Quality Later

**Goal**: Improve content quality with powerful LLM

**Approach**:
```
Load Phase 1 content
  ↓
Powerful LLM (deepseek 16b, claude-opus)
  ↓
Optional: Multi-stage refinement
  ↓
Store improved version
  ↓
Next user gets better version from Phase 1
```

---

## Example: Blog Post Generator

### Phase 1 - Real-Time Generation (5 seconds)

```python
from src.mantras import MantraLibrary

# User request
user_prompt = "Write a blog post about Python async programming"

# Phase 1 mantra: VERY fast
mantra = MantraLibrary.get("lightning_fast")

# Use fastest model
model = "tinyllama"  # 1.1B parameters, ~100ms per token
temperature = 0.7    # Slightly creative

# Stream generation
print("Generating blog post...")
print("-" * 60)

async def generate_realtime():
    """Generate content in real-time, streaming to user."""

    # Fast LLM generates
    async for chunk in stream_generate(
        model=model,
        prompt=user_prompt,
        temperature=temperature,
        max_tokens=500
    ):
        print(chunk, end='', flush=True)  # User sees immediately

    print("\n" + "-" * 60)
    print("✓ Initial draft complete (5 seconds)")

# Result: User has 500-word blog post in 5 seconds
# Quality: 0.65 (good enough for draft)
```

**Output (streaming in real-time)**:
```
Generating blog post...
------------------------------------------------------------
# Python Async Programming: A Beginner's Guide

Python's async features let you write concurrent code that's
more efficient than traditional threading. The async/await
syntax makes it easy to...

[continues streaming...]

✓ Initial draft complete (5 seconds)
```

### Optional: Shaping Stage (2 seconds)

```python
# Use another fast LLM to "shape" the content
shaping_prompt = f"""Improve this draft:
- Fix grammar
- Add transitions
- Keep it concise

DRAFT:
{draft_content}

IMPROVED VERSION:"""

shaped_content = fast_generate(
    model="qwen2.5-coder:3b",  # Slightly bigger, still fast
    prompt=shaping_prompt,
    temperature=0.3,
    max_tokens=500
)

print("✓ Shaped version ready (7 seconds total)")
# Quality: 0.70 (minor improvements)
```

### Phase 2 - Optimization (background, 45 seconds)

```python
# Later (6 PM background job)
optimize_prompt = f"""You are an expert technical writer.
Rewrite this blog post with:
- More depth and detail
- Code examples
- Best practices
- Professional tone

ORIGINAL POST:
{phase1_content}

IMPROVED POST:"""

# Use powerful model
improved_content = generate(
    model="deepseek-coder:16b",  # 16B parameters, high quality
    prompt=optimize_prompt,
    temperature=0.3,
    max_tokens=1500
)

# Quality: 0.92 (professional-grade)
```

**Output (background)**:
```
# Mastering Python Async Programming: A Comprehensive Guide

## Introduction

Python's asynchronous programming model, introduced in Python 3.4
with asyncio and enhanced with async/await syntax in Python 3.5,
revolutionizes how we handle concurrent operations...

## Understanding the Event Loop

The event loop is the core of Python's async infrastructure. Here's
how it works:

```python
import asyncio

async def fetch_data():
    await asyncio.sleep(1)
    return "data"

# The event loop manages execution
asyncio.run(fetch_data())
```

[Much more detailed, with examples, explanations...]

✓ Optimized version ready
```

---

## Multi-Stage Refinement Pattern

For maximum quality, use **multiple stages**:

### Stage 1: Fast Generation (5s)
```
Model: tinyllama (1b)
Temperature: 0.7
Output: Initial draft (quality: 0.60)
```

### Stage 2: Fast Shaping (2s)
```
Model: qwen:3b
Temperature: 0.3
Task: Fix grammar, add structure
Output: Shaped draft (quality: 0.70)
```

### Stage 3: Powerful Enhancement (30s, background)
```
Model: deepseek:16b
Temperature: 0.2
Task: Add depth, examples, polish
Output: Professional version (quality: 0.90)
```

### Stage 4: Expert Review (optional, 45s, background)
```
Model: claude-opus or gpt-4
Temperature: 0.1
Task: Expert-level refinement
Output: Publication-ready (quality: 0.95)
```

---

## Mantra Application

### Phase 1 Mantra: "Lightning Fast"

```python
{
    "speed_priority": 0.95,
    "quality_floor": 0.40,
    "model": "tinyllama",
    "temperature": 0.7,
    "max_time": 10,
    "stream": True,  # CRITICAL for real-time
    "max_tokens": 500
}
```

### Shaping Mantra: "Quick & Accurate"

```python
{
    "speed_priority": 0.70,
    "quality_floor": 0.60,
    "model": "qwen:3b",
    "temperature": 0.3,
    "max_time": 5,
    "stream": False,
    "max_tokens": 500
}
```

### Phase 2 Mantra: "Deliberately Thorough"

```python
{
    "speed_priority": 0.20,
    "quality_floor": 0.85,
    "model": "deepseek-coder:16b",
    "temperature": 0.2,
    "max_time": 60,
    "stream": False,
    "max_tokens": 2000
}
```

---

## Code Implementation

```python
class RealtimeGenerator:
    """
    Real-time content generation with fast LLM, optimization later.
    """

    def __init__(self, ollama_client, rag_memory):
        self.client = ollama_client
        self.rag = rag_memory

    async def generate_realtime(
        self,
        prompt: str,
        user_id: str,
        with_shaping: bool = True
    ) -> str:
        """
        Phase 1: Generate content in real-time with fast LLM.

        Args:
            prompt: User's request
            user_id: User identifier
            with_shaping: Apply fast shaping stage

        Returns:
            Generated content (streamed to user)
        """

        # Use lightning fast mantra
        from src.mantras import MantraLibrary
        mantra = MantraLibrary.get("lightning_fast")

        print(f"\n[Generating with {mantra.name}...]")
        print("-" * 60)

        # Stage 1: Fast generation with streaming
        content = ""
        async for chunk in self.client.stream_generate(
            model="tinyllama",
            prompt=prompt,
            temperature=mantra.temperature,
            max_tokens=500
        ):
            print(chunk, end='', flush=True)
            content += chunk

        print("\n" + "-" * 60)

        # Stage 2: Optional fast shaping
        if with_shaping:
            print("[Shaping content...]")

            shaped = self.client.generate(
                model="qwen2.5-coder:3b",
                prompt=f"Improve this (fix grammar, add structure):\n\n{content}",
                temperature=0.3,
                max_tokens=500
            )

            content = shaped
            print("✓ Shaped")

        # Store for later optimization
        self._store_for_optimization(prompt, content, user_id)

        return content

    def _store_for_optimization(
        self,
        prompt: str,
        content: str,
        user_id: str
    ):
        """Store content for Phase 2 optimization."""

        from src.rag_memory import ArtifactType
        import json

        artifact_id = f"realtime_{user_id}_{hash(prompt)}"

        self.rag.store_artifact(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.PATTERN,
            name="Real-time Generated Content",
            description=prompt[:100],
            content=json.dumps({
                "prompt": prompt,
                "content": content,
                "phase": "1_realtime",
                "quality_estimate": 0.65,
                "user_id": user_id,
                "generated_at": datetime.now().isoformat()
            }),
            tags=["realtime", "needs_optimization", user_id],
            auto_embed=True
        )

    def optimize_background(
        self,
        artifact_id: str,
        stages: int = 1
    ) -> str:
        """
        Phase 2: Optimize content with powerful LLM.

        Args:
            artifact_id: Artifact to optimize
            stages: Number of refinement stages (1-3)

        Returns:
            Optimized content
        """

        # Load artifact
        artifact = self.rag.get_artifact(artifact_id)
        data = json.loads(artifact.content)

        original_prompt = data["prompt"]
        phase1_content = data["content"]

        print(f"\n[Optimizing {artifact_id}...]")

        # Stage 1: Powerful enhancement
        enhanced = self.client.generate(
            model="deepseek-coder:16b",
            prompt=f"""Rewrite this with more depth and quality:

ORIGINAL REQUEST: {original_prompt}

DRAFT CONTENT:
{phase1_content}

IMPROVED VERSION (with examples, details, polish):""",
            temperature=0.2,
            max_tokens=2000
        )

        current_content = enhanced
        quality = 0.85

        # Stage 2: Additional refinement (optional)
        if stages >= 2:
            refined = self.client.generate(
                model="qwen2.5-coder:14b",
                prompt=f"Further refine this:\n\n{current_content}",
                temperature=0.15,
                max_tokens=2000
            )
            current_content = refined
            quality = 0.90

        # Stage 3: Expert polish (optional)
        if stages >= 3:
            polished = self.client.generate(
                model="deepseek-coder:16b",
                prompt=f"Expert-level polish:\n\n{current_content}",
                temperature=0.1,
                max_tokens=2500
            )
            current_content = polished
            quality = 0.95

        # Update artifact
        data["content"] = current_content
        data["phase"] = f"2_optimized_{stages}_stages"
        data["quality_estimate"] = quality
        data["optimized_at"] = datetime.now().isoformat()

        self.rag.update_artifact(
            artifact_id=artifact_id,
            content=json.dumps(data)
        )

        print(f"✓ Optimized (quality: {quality:.2f})")

        return current_content


# Example usage
async def example():
    generator = RealtimeGenerator(ollama_client, rag_memory)

    # User makes request
    prompt = "Write a blog post about Python async programming"

    # Phase 1: Real-time (user sees immediately)
    content = await generator.generate_realtime(
        prompt=prompt,
        user_id="user123",
        with_shaping=True
    )
    # Returns in 7 seconds, user has content

    # Phase 2: Background optimization (triggered later)
    # Runs at 6 PM or when system idle
    optimized = generator.optimize_background(
        artifact_id="realtime_user123_...",
        stages=2
    )
    # Takes 60 seconds, quality: 0.90

    # Next user gets optimized version from Phase 1!
```

---

## Benefits

### For Users

1. **Instant Feedback**: See content appearing in real-time
2. **No Waiting**: Get usable draft in 5-10 seconds
3. **Progressive Enhancement**: Quality improves over time
4. **Later Users Benefit**: Get optimized version immediately

### For the System

1. **Resource Efficiency**: Fast LLM for interactive, powerful for background
2. **Better UX**: Streaming keeps user engaged
3. **Continuous Improvement**: Every generation improves
4. **Scalable**: Fast models handle high load

---

## Use Cases

### 1. Blog Post Generation
- Phase 1: Tinyllama generates 500-word draft (5s)
- Shaping: Qwen:3b fixes grammar (2s)
- Phase 2: Deepseek adds depth, examples (45s, background)

### 2. Code Documentation
- Phase 1: Fast LLM generates docstrings (3s)
- Phase 2: Powerful LLM adds examples, edge cases (30s)

### 3. Email Responses
- Phase 1: Tinyllama generates reply (2s)
- Phase 2: Claude polishes tone, adds details (20s)

### 4. Content Summarization
- Phase 1: Fast extraction of key points (1s)
- Phase 2: Comprehensive summary with context (15s)

---

## Streaming Configuration

### For Real-Time Display

```python
async def stream_to_user(prompt: str):
    """Stream content to user in real-time."""

    async for chunk in ollama_client.stream_generate(
        model="tinyllama",
        prompt=prompt,
        temperature=0.7,
        stream=True  # ENABLE STREAMING
    ):
        # Send to user immediately
        print(chunk, end='', flush=True)
        # Or: websocket.send(chunk)
        # Or: yield chunk (SSE)
```

### Measuring Quality

```python
def estimate_quality(content: str, is_phase1: bool) -> float:
    """Estimate content quality."""

    if is_phase1:
        # Phase 1: Fast generation
        base_quality = 0.60
    else:
        # Phase 2: Optimized
        base_quality = 0.85

    # Adjust based on length, structure, etc.
    if len(content) > 1000:
        base_quality += 0.05

    if has_code_examples(content):
        base_quality += 0.05

    return min(1.0, base_quality)
```

---

## Summary

**Real-Time Generation Pattern**:

1. **Phase 1 (Interactive)**:
   - Fast LLM (tinyllama 1b)
   - Streaming output
   - Optional shaping stage
   - User has content in 5-10s

2. **Phase 2 (Optimize)**:
   - Powerful LLM (deepseek 16b)
   - Background processing
   - Multi-stage refinement
   - Quality: 0.90+

3. **Next User Benefits**:
   - Gets optimized version from Phase 1
   - High quality, no waiting

**Key Insight**: Use **model size as a resource** - small for interactive, large for batch optimization.

---

**Generated:** 2025-11-17
**Status:** ✓ Pattern Documented
