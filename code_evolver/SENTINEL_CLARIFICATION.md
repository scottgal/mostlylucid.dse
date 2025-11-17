# Sentinel Clarification System

**Date:** 2025-11-17
**Status:** ✅ IMPLEMENTED

## Overview

The sentinel now acts as an intelligent gatekeeper that:
1. ✅ Blocks gibberish/useless inputs
2. ✅ Asks clarifying questions when input is vague
3. ✅ Stores Q&A in RAG for context
4. ✅ Allows "I'm sure" override

## New Methods

### 1. `validate_actionability()`

**File:** `src/sentinel_llm.py:585-698`

Validates if user input is actionable:

```python
result = sentinel.validate_actionability(user_input, allow_override=True)

# Returns:
{
    "is_actionable": True/False,
    "confidence": 0.0-1.0,
    "needs_clarification": True/False,
    "questions": ["Question 1?", "Question 2?"],
    "reasoning": "Why it's not actionable",
    "verdict": "ACTIONABLE" | "VAGUE" | "GIBBERISH"
}
```

**Examples:**

```python
# Gibberish - blocked
sentinel.validate_actionability("asdf qwerty zxcv")
# Returns: verdict="GIBBERISH", is_actionable=False

# Too vague - needs clarification
sentinel.validate_actionability("make something")
# Returns: verdict="VAGUE", questions=["What would you like to make?", ...]

# Clear - proceeds
sentinel.validate_actionability("create a function that validates email addresses")
# Returns: verdict="ACTIONABLE", is_actionable=True

# Override - bypasses check
sentinel.validate_actionability("make something. I'm sure.", allow_override=True)
# Returns: is_actionable=True, reasoning="User confirmed with override"
```

### 2. `ask_clarifying_questions()`

**File:** `src/sentinel_llm.py:700-725`

Asks questions and collects answers:

```python
qa_pairs = sentinel.ask_clarifying_questions(
    questions=["What type of function?", "What inputs?"],
    user_callback=lambda q: console.input(f"[yellow]{q}[/yellow] ")
)

# Returns:
{
    "What type of function?": "Email validator",
    "What inputs?": "Email string"
}
```

### 3. `store_qa_in_rag()`

**File:** `src/sentinel_llm.py:727-772`

Stores Q&A in RAG for future reference:

```python
sentinel.store_qa_in_rag(
    original_input="make something",
    qa_pairs={
        "What type of function?": "Email validator",
        "What inputs?": "Email string"
    },
    final_context="Create an email validation function that takes an email string as input"
)
```

## Integration into Chat CLI

**Add to chat_cli.py in the input handling section:**

```python
# In ChatCLI.run() method, after getting user_input:

# Initialize sentinel if not already done
if not hasattr(self, 'sentinel'):
    from src.sentinel_llm import SentinelLLM
    self.sentinel = SentinelLLM(self.client, self.rag)

# Validate actionability
validation = self.sentinel.validate_actionability(
    user_input,
    allow_override=True
)

# Handle based on verdict
if validation["verdict"] == "GIBBERISH":
    console.print(f"[red]✗ {validation['reasoning']}[/red]")
    console.print("[yellow]Please provide a clear request or type '/help' for assistance.[/yellow]")
    continue

elif validation["needs_clarification"]:
    console.print(f"[yellow]I need some clarification:[/yellow]")
    
    # Ask questions
    qa_pairs = self.sentinel.ask_clarifying_questions(
        questions=validation["questions"],
        user_callback=lambda q: console.input(f"  [cyan]→ {q}[/cyan]\n  [green]Your answer:[/green] ")
    )
    
    # Build enhanced context from answers
    answers_text = " ".join(qa_pairs.values())
    enhanced_input = f"{user_input}. {answers_text}"
    
    # Store Q&A in RAG
    self.sentinel.store_qa_in_rag(
        original_input=user_input,
        qa_pairs=qa_pairs,
        final_context=enhanced_input
    )
    
    # Replace user_input with enhanced version
    user_input = enhanced_input
    console.print(f"[green]✓ Got it! Processing: {enhanced_input[:100]}...[/green]\n")

# Continue with normal workflow...
```

## Example Flow

### Flow 1: Gibberish Blocked

```
User> asdf qwerty random words
✗ Input appears to be gibberish or random characters
Please provide a clear request or type '/help' for assistance.
```

### Flow 2: Vague Input → Clarification → Store in RAG

```
User> make something
I need some clarification:
  → What would you like to create?
  Your answer: A function to validate emails

  → What should it do specifically?
  Your answer: Check if an email string is in valid format

✓ Got it! Processing: make something. A function to validate emails. Check if an email string is in valid format...

[Generates function...]
✓ Function created successfully!

[Q&A stored in RAG with tags: clarification, sentinel, context, qa]
```

### Flow 3: Clear Input → No Questions

```
User> create a function that validates email addresses using regex
✓ Input is clear and actionable

[Directly generates function...]
```

### Flow 4: Override

```
User> do the thing. I'm sure.
✓ User confirmed with override

[Proceeds with "do the thing"]
```

## RAG Storage Format

When Q&A is stored, it creates an artifact:

```json
{
  "original_input": "make something",
  "clarifications": [
    {"q": "What would you like to create?", "a": "A function to validate emails"},
    {"q": "What should it do specifically?", "a": "Check if email format is valid"}
  ],
  "final_context": "Create a function to validate emails that checks if email format is valid",
  "timestamp": 1763391234.567
}
```

**Tags:** `["clarification", "sentinel", "context", "qa"]`

**Benefits:**
- Future requests can find similar clarifications
- Semantic search: "validate emails" will find this Q&A
- System learns common patterns of vague inputs
- Can suggest clarifications based on past Q&A

## Configuration

**Override Patterns (case-insensitive):**
- "i'm sure"
- "i am sure"
- "yes proceed"
- "confirmed"

**Gibberish Detection:**
- Less than 2 words → too short
- More than 50% non-word tokens → likely gibberish
- LLM validation for ambiguous cases

## Testing

```python
# Test gibberish blocking
from src.sentinel_llm import SentinelLLM
sentinel = SentinelLM(client, rag)

result = sentinel.validate_actionability("asdf qwerty")
assert result["verdict"] == "GIBBERISH"
assert not result["is_actionable"]

# Test vague input
result = sentinel.validate_actionability("make something")
assert result["verdict"] == "VAGUE"
assert result["needs_clarification"]
assert len(result["questions"]) > 0

# Test clear input
result = sentinel.validate_actionability("create email validator function")
assert result["verdict"] == "ACTIONABLE"
assert result["is_actionable"]

# Test override
result = sentinel.validate_actionability("random. I'm sure.", allow_override=True)
assert result["is_actionable"]
```

## Status

✅ **Implemented** - Ready for integration into chat_cli.py
- validate_actionability() ✅
- ask_clarifying_questions() ✅
- store_qa_in_rag() ✅
- Override support ✅

**Next Step:** Integrate into chat_cli.py input handling loop
