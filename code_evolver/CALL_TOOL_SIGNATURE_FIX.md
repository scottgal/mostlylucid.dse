# call_tool() Signature Fix

## Issue

Generated code was calling `call_tool()` incorrectly, causing **TypeError** at runtime:

```
TypeError: call_tool() takes 2 positional arguments but 3 were given
```

**Example of Broken Code:**
```python
# ❌ WRONG - Passing dict as 3rd positional argument
translated_text = call_tool(
    "nmt_translator", "translate_text", {
        "text": original_text, "src": source_language, "tgt": target_language})
```

---

## Root Cause

The code generator was **misunderstanding the call_tool() signature** and generating code that passed:
1. Tool name (correct)
2. Action string (wrong - should be part of prompt)
3. Dictionary (wrong - should be **kwargs or part of prompt)

**Actual Signature:**
```python
def call_tool(tool_name: str, prompt: str, **kwargs) -> str
```

**Parameters:**
- `tool_name`: Name of the tool to call
- `prompt`: Complete prompt/text to send to the tool
- `**kwargs`: Optional keyword arguments (NOT a dict!)

---

## Fix Applied

### 1. Fixed Broken Node ✅

**File:** `nodes/translate_text_with_nmt_and_ou/main.py`

**Before (Broken):**
```python
translated_text = call_tool(
    "nmt_translator", "translate_text", {
        "text": original_text, "src": source_language, "tgt": target_language})
```

**After (Fixed):**
```python
# Build complete prompt with all needed information
translation_prompt = f"Translate from {source_language} to {target_language}: {original_text}"

# Call tool with just tool name and prompt
translated_text = call_tool("nmt_translator", translation_prompt)
```

---

### 2. Added Clear Documentation to Code Generation Prompt ✅

**File:** `chat_cli.py` (lines 2216-2267)

Added new section: **"CRITICAL: call_tool() SIGNATURE"** with:

#### **Correct Usage Examples:**
```python
# ✅ Simple call
result = call_tool("content_generator", "Write a joke about cats")

# ✅ With f-string formatting
topic = "dogs"
result = call_tool("content_generator", f"Write a poem about {topic}")

# ✅ Translation with formatted prompt
text = "Hello"
translated = call_tool("nmt_translator", f"Translate to French: {text}")

# ✅ With keyword arguments (if tool supports them)
result = call_tool("content_generator", "Write article", temperature=0.7)
```

#### **Wrong Usage Examples (What NOT to Do):**
```python
# ❌ WRONG - Dict as positional argument
result = call_tool("tool", "action", {"text": "hello", "lang": "fr"})  # TypeError!

# ❌ WRONG - Too many positional arguments
result = call_tool("tool", "action", "param1", "param2")  # TypeError!

# ❌ WRONG - Dict instead of kwargs
result = call_tool("tool", "prompt", {"temperature": 0.7})  # TypeError!
```

#### **Key Rules:**
1. call_tool() takes **EXACTLY 2 positional arguments**: (tool_name, prompt)
2. Additional parameters **MUST be keyword arguments** (**kwargs), NOT a dict
3. Build complex prompts using **f-strings**, don't pass separate parameters
4. The prompt should be a **complete, descriptive string**

---

## Common Patterns

### ✅ **Translation:**
```python
# Build prompt with all information
source_lang = "English"
target_lang = "French"
text = "Hello, world!"

prompt = f"Translate from {source_lang} to {target_lang}: {text}"
result = call_tool("nmt_translator", prompt)
```

### ✅ **Content Generation:**
```python
# Simple, descriptive prompt
topic = "artificial intelligence"
prompt = f"Write a technical article about {topic}"
article = call_tool("content_generator", prompt)
```

### ✅ **With Template Variables (if tool supports):**
```python
# Some tools may accept kwargs for template variables
result = call_tool(
    "technical_writer",
    topic="Python decorators",
    audience="intermediate developers",
    length="1500 words"
)
```

---

## Prevention

The code generation prompt now **explicitly shows**:
- ✅ **Correct signature** with type hints
- ✅ **Multiple correct examples**
- ❌ **Wrong usage examples with explanations**
- ✅ **Key rules** emphasized

This should prevent future LLMs from generating incorrect `call_tool()` usage.

---

## Testing

After the fix, generated code should:
- ✅ Use exactly 2 positional arguments: `call_tool(tool_name, prompt)`
- ✅ Build complete prompts using f-strings
- ✅ Pass additional params as kwargs, not dicts
- ✅ Never pass action strings as separate arguments

**Verification:**
```bash
cd code_evolver
python chat_cli.py
```

Try: "Translate 'Hello' to French"

**Expected Code:**
```python
text = "Hello"
target_lang = "French"
prompt = f"Translate to {target_lang}: {text}"
result = call_tool("nmt_translator", prompt)
```

**NOT:**
```python
# ❌ This should NOT be generated anymore
result = call_tool("nmt_translator", "translate", {"text": "Hello", "lang": "French"})
```

---

## Summary

**Problem:** Code generator misunderstood call_tool() signature → TypeError
**Solution:** Fixed broken code + added clear signature documentation with examples
**Result:** Future generated code will use correct call_tool() pattern

**Key Principle:** **Complete prompts over complex parameters** - Build everything into the prompt string using f-strings, don't pass separate positional arguments or dicts.
