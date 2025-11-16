# Translation Tools Guide

## Overview

The code_evolver system has **three types of translation tools** with different purposes and usage patterns:

1. **NMT API Tool** (`nmt_translator`) - Direct API access with structured parameters
2. **NMT Executable Wrapper** (`nmt_translate`) - Natural language prompt wrapper
3. **LLM Translation Tools** - AI-powered translation with context awareness

---

## 1. NMT API Tool (nmt_translator)

**Type:** OpenAPI
**Name:** `nmt_translator`
**Purpose:** Direct access to the Neural Machine Translation API at `localhost:8000`

### How It Works

This is a **direct API tool** - it doesn't take a "prompt". Instead, it requires structured parameters:

**Required Parameters:**
- `text` (string) - The text to translate
- `target_lang` (string) - ISO 639-1 target language code (e.g., "de", "fr", "es")

**Optional Parameters:**
- `source_lang` (string) - ISO 639-1 source language code (default: "en")
- `beam_size` (integer) - Beam search size for quality (default: 5)
- `perform_sentence_splitting` (boolean) - Split sentences before translation (default: true)

### API Specification

**Endpoint:**
```
GET http://localhost:8000/translate
```

**Query Parameters:**
```
?text=hello&target_lang=de&source_lang=en&beam_size=5&perform_sentence_splitting=true
```

**Response:**
```json
{
  "translations": ["Guten Tag."],
  "pivot_path": "de->en->de",
  "error": null
}
```

### Usage (Direct API Call)

**NOT from workflows** - OpenAPI tools need specific invoke methods:

```python
from src.tools_manager import ToolsManager

tools = ToolsManager()

# Call the API directly with structured parameters
result = tools.invoke_openapi_tool(
    tool_id="nmt_translator",
    operation_id="translate",  # Operation from OpenAPI spec
    parameters={
        "text": "Hello, world!",
        "source_lang": "en",
        "target_lang": "de",
        "beam_size": 5,
        "perform_sentence_splitting": True
    }
)

if result["success"]:
    translations = result["data"]["translations"]
    print(translations[0])  # "Hallo, Welt!"
```

### When to Use

- ✅ When you need direct API access with full control
- ✅ When integrating with external systems
- ✅ When you have structured translation parameters
- ❌ NOT for simple workflow calls with prompts

---

## 2. NMT Executable Wrapper (nmt_translate)

**Type:** Executable
**Name:** `nmt_translate`
**Purpose:** Natural language wrapper for the NMT API - parses prompts and calls the API

### How It Works

This tool **accepts natural language prompts** and automatically:
1. Parses the prompt to extract text, source/target languages
2. Normalizes language names to ISO codes ("German" → "de")
3. Calls the NMT API with proper parameters
4. Returns the translated text

### Supported Prompt Formats

**Format 1:** `"Translate to <language>: <text>"`
```
Translate to German: Hello
→ Calls API with: text="Hello", source_lang="en", target_lang="de"
```

**Format 2:** `"Translate from <source> to <target>: <text>"`
```
Translate from English to French: Hello, world!
→ Calls API with: text="Hello, world!", source_lang="en", target_lang="fr"
```

**Format 3:** `"Translate '<text>' to <language>"`
```
Translate 'Goodbye' to Spanish
→ Calls API with: text="Goodbye", source_lang="en", target_lang="es"
```

### Usage from Workflows

**✅ Recommended for most workflows:**

```python
from node_runtime import call_tool

# Simple, natural language prompt
result = call_tool("nmt_translate", "Translate to German: Hello")
# Returns: "Hallo"

# With source language specified
result = call_tool("nmt_translate", "Translate from English to French: Good morning")
# Returns: "Bonjour"

# Using variables
text = "How are you?"
target = "Spanish"
result = call_tool("nmt_translate", f"Translate to {target}: {text}")
# Returns: "¿Cómo estás?"
```

### When to Use

- ✅ **BEST for workflow calls** - simple, natural language
- ✅ When you have a prompt-style interface
- ✅ When you want automatic language name normalization
- ✅ When you don't need to control beam_size or other advanced parameters

---

## 3. LLM Translation Tools

**Type:** LLM
**Names:** `quick_translator`, `translation_quality_checker`, `code_translation_validator`
**Purpose:** AI-powered translation with context awareness, quality checking, and validation

### How They Work

These tools use **large language models** to:
- Translate with context awareness
- Preserve tone and meaning
- Check translation quality
- Validate code translations
- Handle nuanced language

### quick_translator

**Purpose:** Fast, context-aware translation using AI

```python
from node_runtime import call_tool

# Natural language instruction
result = call_tool(
    "quick_translator",
    "Translate this technical article to German, preserving technical terms: ..."
)
```

**Differences from NMT:**
- ✅ Understands context ("technical article", "casual tone", etc.)
- ✅ Can preserve specific terms or formatting
- ✅ Handles complex instructions
- ❌ Slower than NMT API
- ❌ May be less accurate for simple literal translation

### translation_quality_checker

**Purpose:** Validates translation quality, detects errors

```python
result = call_tool(
    "translation_quality_checker",
    original="Hello, world!",
    translated="Hallo, Welt!",
    source_lang="English",
    target_lang="German"
)
# Returns: Quality assessment, detected issues, score
```

**Use Case:**
- Validate NMT output
- Detect repeated characters or garbled text
- Check for accurate meaning preservation

### code_translation_validator

**Purpose:** Validates translations of code comments/strings

```python
result = call_tool(
    "code_translation_validator",
    original_code="...",
    translated_code="...",
    source_lang="English",
    target_lang="French"
)
# Returns: Validation report, issues found
```

### When to Use LLM Translation

- ✅ When you need context awareness
- ✅ For creative or nuanced content
- ✅ When tone preservation matters
- ✅ For quality validation
- ❌ When speed is critical (use NMT instead)
- ❌ For simple, literal translation (use NMT instead)

---

## Comparison Table

| Feature | NMT API | NMT Wrapper | LLM Translation |
|---------|---------|-------------|-----------------|
| **Speed** | Very Fast | Very Fast | Slow |
| **Accuracy** | Good | Good | Excellent |
| **Context Awareness** | None | None | High |
| **Accepts Prompts** | ❌ No | ✅ Yes | ✅ Yes |
| **Structured Params** | ✅ Yes | ❌ No | ❌ No |
| **Workflow-Friendly** | ❌ No | ✅ Yes | ✅ Yes |
| **Language Normalization** | ❌ No | ✅ Yes | ✅ Yes |
| **Requires NMT Service** | ✅ Yes | ✅ Yes | ❌ No |
| **Cost** | Free | Free | Model-dependent |

---

## Decision Tree

### "Which translation tool should I use?"

```
Is speed critical?
└─ YES → Is the text simple/literal?
   ├─ YES → Use NMT Wrapper (nmt_translate)
   └─ NO → Use LLM (quick_translator)

└─ NO → Do you need context/tone preservation?
   ├─ YES → Use LLM (quick_translator)
   └─ NO → Use NMT Wrapper (nmt_translate)
```

### Common Scenarios

**Scenario 1: Workflow needs to translate user input**
```python
# ✅ Use NMT Wrapper
user_text = input_data.get("text")
target_lang = input_data.get("target_language")
result = call_tool("nmt_translate", f"Translate to {target_lang}: {user_text}")
```

**Scenario 2: Need to validate translation quality**
```python
# First translate with NMT
translation = call_tool("nmt_translate", f"Translate to German: {text}")

# Then validate with LLM
quality_report = call_tool(
    "translation_quality_checker",
    f"Check this translation: Original (EN): {text} | Translation (DE): {translation}"
)
```

**Scenario 3: Translating technical documentation with context**
```python
# ✅ Use LLM for context awareness
result = call_tool(
    "quick_translator",
    "Translate this API documentation to French, "
    "keeping code examples in English: ..."
)
```

**Scenario 4: Batch translation with full control**
```python
# ✅ Use NMT API directly
from src.tools_manager import ToolsManager

tools = ToolsManager()
for text in batch_texts:
    result = tools.invoke_openapi_tool(
        "nmt_translator",
        "translate",
        parameters={
            "text": text,
            "target_lang": "de",
            "beam_size": 10  # Higher quality
        }
    )
```

---

## Best Practices

### For Workflow Developers

1. **Default to NMT Wrapper for Simple Translation**
   ```python
   # ✅ Good - fast and simple
   result = call_tool("nmt_translate", f"Translate to {lang}: {text}")
   ```

2. **Use LLM When Context Matters**
   ```python
   # ✅ Good for nuanced content
   result = call_tool("quick_translator", f"Translate to {lang}, preserving formal tone: {text}")
   ```

3. **Chain NMT + Validation for Production**
   ```python
   # Step 1: Fast translation with NMT
   translation = call_tool("nmt_translate", f"Translate to German: {text}")

   # Step 2: Quality check with LLM
   quality = call_tool("translation_quality_checker", f"Validate: {text} → {translation}")

   # Step 3: Use translation if quality is good
   ```

4. **Don't Use OpenAPI Tools Directly from Workflows**
   ```python
   # ❌ Don't do this - call_tool() doesn't support structured params
   result = call_tool("nmt_translator", text="Hello", target_lang="de")

   # ✅ Do this instead - use the wrapper
   result = call_tool("nmt_translate", "Translate to German: Hello")
   ```

### For Tool Developers

1. **Create Executable Wrappers for APIs**
   - Wrap OpenAPI tools in executable scripts
   - Parse natural language prompts
   - Convert to structured API calls
   - Return clean text output

2. **Document Parameter Requirements**
   - Clearly state if tool needs structured params
   - Provide prompt format examples
   - Show expected input/output formats

---

## Summary

### Key Takeaways

1. **NMT API (`nmt_translator`)**: Direct API access, needs structured parameters, not workflow-friendly
2. **NMT Wrapper (`nmt_translate`)**: Natural language wrapper, perfect for workflows, fast and simple
3. **LLM Translation**: Context-aware, slower, best for nuanced content

### Recommended Usage

- **Workflows**: Use `nmt_translate` (executable wrapper)
- **API Integration**: Use `nmt_translator` (OpenAPI tool)
- **Context-Aware**: Use `quick_translator` (LLM tool)
- **Quality Check**: Use `translation_quality_checker` (LLM tool)

### Remember

> **NMT tools don't take "prompts" - they need specific parameters like text, source_lang, target_lang.**
> **Use the executable wrapper (`nmt_translate`) for prompt-based workflow calls.**
> **Use LLM tools when context and nuance matter more than speed.**

---

**Status:** All translation tools working correctly with their intended interfaces.
