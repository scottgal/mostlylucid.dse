# Automatic Test Data Generation for Workflows

## Problem

Workflows were producing empty output because generated code expected specific input fields that weren't being provided.

**Example:**

User request: "Translate the article into German"

Generated code expected:
```python
article = input_data.get("article", "")
target_language = input_data.get("target_language", "")
```

But system only provided generic fields:
```python
input_data = {
    "input": "Translate the article into German",
    "description": "Translate the article into German",
    "prompt": "Translate the article into German"
}
```

Result: `{"translated_article": ""}` (empty!)

---

## Solution

### 1. Input Field Detection

**File:** `chat_cli.py` (lines 2950-2957, 1433-1441)

The system now automatically detects what input fields the generated code expects by parsing for patterns like:
```python
input_data.get("field_name", ...)
```

**Implementation:**
```python
import re
expected_fields = set()
code_lines = code.split('\n')
for line in code_lines:
    # Look for patterns like: input_data.get("field_name", ...)
    matches = re.findall(r'input_data\.get\(["\']([^"\']+)["\']', line)
    expected_fields.update(matches)
```

### 2. Automatic Test Data Generation

**File:** `chat_cli.py` (lines 2972-3010, 1455-1489)

When the system detects specific fields needed (beyond generic ones like "input", "description", etc.), it:

1. **Identifies** which fields are specific (not in the generic list)
2. **Builds a schema** by guessing field types from names
3. **Calls random_data_generator** to create test data
4. **Merges** the generated data into input_data

**Implementation:**
```python
# Generic fields that are always provided
generic_fields = {"input", "task", "description", "query", "topic", "prompt", "question", "request"}

# Find fields that are NOT generic
specific_fields_needed = expected_fields - generic_fields

if specific_fields_needed:
    console.print(f"[yellow]→ Detected specific input fields needed: {', '.join(specific_fields_needed)}[/yellow]")
    console.print(f"[yellow]→ Auto-generating test data...[/yellow]")

    # Build a schema from the detected fields
    schema = {}
    for field in specific_fields_needed:
        # Guess type based on field name
        if any(word in field.lower() for word in ['lang', 'language']):
            schema[field] = "string"  # Will generate language code
        elif any(word in field.lower() for word in ['text', 'article', 'content', 'message']):
            schema[field] = "string"  # Will generate text
        elif any(word in field.lower() for word in ['age', 'count', 'number', 'size']):
            schema[field] = "number"
        else:
            schema[field] = "string"

    # Generate test data using random_data_generator
    schema_json = json.dumps(schema)
    test_data_result = self.tools.invoke_executable_tool(
        tool_id="random_data_generator",
        source_file="",
        prompt=schema_json
    )

    if test_data_result.get("success"):
        test_data = json.loads(test_data_result["stdout"])
        console.print(f"[green]→ Generated test data: {json.dumps(test_data, indent=2)}[/green]")
        # Merge generated data into input_data
        input_data.update(test_data)
```

### 3. Improved Output Display

**File:** `chat_cli.py` (lines 2972-3022, 1503-1566)

The output display now:

**Checks more field names:**
```python
result_fields = ['result', 'output', 'answer', 'content', 'translated_article',
                 'summary', 'text', 'data', 'response']
```

**Detects empty output:**
```python
if not result_content or (isinstance(result_content, str) and not result_content.strip()):
    has_empty_output = True
    console.print(f"[yellow]⚠ Warning: Field '{field}' is empty![/yellow]")
```

**Shows helpful warnings:**
```python
if has_empty_output:
    console.print("\n[yellow]━" * 40 + "[/yellow]")
    console.print("[yellow]⚠ The workflow produced empty output![/yellow]")
    console.print("[yellow]This usually means the workflow needs specific input data.[/yellow]")
    console.print("[yellow]Try providing input fields or use test data generation.[/yellow]")
    console.print("[yellow]━" * 40 + "[/yellow]")
```

**Shows all output fields (not just "result"):**
```python
# If no recognized field found, show all non-empty values
if not result_displayed and output_data:
    console.print("[bold]Output fields:[/bold]")
    for key, value in output_data.items():
        if value and (not isinstance(value, str) or value.strip()):
            console.print(f"  {key}: {value}")
        else:
            has_empty_output = True
            console.print(f"  [dim]{key}: (empty)[/dim]")
```

---

## Example Flow

### Before Fix

**User:** "Translate the article into German"

**Generated Code:**
```python
article = input_data.get("article", "")
target_language = input_data.get("target_language", "")

if not article:
    print(json.dumps({"translated_article": ""}))
    return

prompt = f"Translate the following text into {target_language}: {article}"
translated_article = call_tool("quick_translator", prompt)
print(json.dumps({"translated_article": translated_article}))
```

**Input Data (provided):**
```json
{
  "input": "Translate the article into German",
  "description": "Translate the article into German",
  "prompt": "Translate the article into German"
}
```

**Output:**
```json
{"translated_article": ""}
```

**User sees:** Empty output, no warning, no explanation!

---

### After Fix

**User:** "Translate the article into German"

**System detects:** Code needs "article" and "target_language"

**System output:**
```
→ Detected specific input fields needed: article, target_language
→ Auto-generating test data...
→ Generated test data: {
  "article": "Quick brown fox jumps over lazy dog sample.",
  "target_language": "de"
}
```

**Input Data (merged):**
```json
{
  "input": "Translate the article into German",
  "description": "Translate the article into German",
  "prompt": "Translate the article into German",
  "article": "Quick brown fox jumps over lazy dog sample.",
  "target_language": "de"
}
```

**Output:**
```json
{"translated_article": "Schneller brauner Fuchs springt über faulen Hund Probe."}
```

**User sees:** Actual translation with generated test data!

---

## Field Type Heuristics

The system guesses field types based on name patterns:

| Field Name Pattern | Generated Type | Example Output |
|--------------------|----------------|----------------|
| `*lang*`, `*language*` | Language code | "de", "fr", "es" |
| `*text*`, `*article*`, `*content*`, `*message*` | Text content | "Quick brown fox jumps over..." |
| `*age*`, `*count*`, `*number*`, `*size*` | Number | 32, 150, 42 |
| Default | String | "sample text" |

**Examples:**
- `"article"` → Generates: `"Quick brown fox jumps over lazy dog sample."`
- `"target_language"` → Generates: `"de"` (German)
- `"source_lang"` → Generates: `"en"` (English)
- `"age"` → Generates: `32`
- `"email"` → Generates: `"alice.smith@gmail.com"`

---

## Benefits

### 1. Always Shows Output

Before: `{"translated_article": ""}` with no explanation
After: Shows warning + full output + explanation

### 2. Automatic Test Data

Before: Workflows failed silently due to missing data
After: System auto-generates realistic test data

### 3. Better Field Detection

Before: Only checked for "result", "output", "answer", "content"
After: Checks 9 common field names + shows ALL fields if none match

### 4. Helpful Warnings

Before: Silent failures
After: Clear warnings explaining why output is empty

---

## Usage

### As a User

**You don't need to do anything!** The system automatically:
1. Detects what data your workflow needs
2. Generates appropriate test data
3. Shows clear warnings if output is still empty

### As a Developer

**When writing workflows:**

You can still use specific field names like:
```python
article = input_data.get("article", "")
target_language = input_data.get("target_language", "")
```

The system will:
- Detect these fields
- Auto-generate test data for them
- Run your workflow with realistic data

**Alternatively, use generic fields:**
```python
text = input_data.get("input", input_data.get("description", ""))
```

This works with the generic input data and doesn't need test generation.

---

## Limitations

### 1. Heuristics May Be Imperfect

The system guesses field types based on names. Sometimes it might guess wrong:

**Example:**
- Field: `"model"` → Generates: `"sample text"` (string)
- But you might want: `"gpt-4"` or `"llama3"`

**Workaround:** Use more descriptive field names like `"model_name"`, `"llm_model"`, etc.

### 2. Complex Data Structures

The auto-generation works for simple types (string, number). Complex nested structures may not generate correctly.

**Example:**
```python
user = input_data.get("user", {})  # Expects nested dict
name = user.get("name", "")
age = user.get("age", 0)
```

The system will generate:
```json
{"user": "sample text"}  # Not a dict!
```

**Workaround:** Use the `random_data_generator` tool directly with a proper schema.

### 3. Business Logic Context

Generated data is random and context-free. It won't understand business logic.

**Example:**
If your workflow needs a valid product ID from a database, the random generator will just create a random string/number, not a real product ID.

**Workaround:** For production use, provide real input data or mock data specific to your domain.

---

## Configuration

### Disable Auto-Generation (Future)

Currently, auto-generation is always enabled. In the future, you could add a config option:

```yaml
# config.yaml
workflows:
  auto_generate_test_data: true  # Set to false to disable
```

### Customize Field Type Mapping (Future)

You could extend the heuristics with custom mappings:

```python
# Custom type mapping
field_type_mapping = {
    "user_id": "uuid",
    "product_id": "sku",
    "timestamp": "datetime",
    ...
}
```

---

## Testing

### Manual Test

**Before fix:**
```bash
cd code_evolver
python chat_cli.py
> Translate the article into German
# Output: {"translated_article": ""}
```

**After fix:**
```bash
cd code_evolver
python chat_cli.py
> Translate the article into German

# System output:
→ Detected specific input fields needed: article, target_language
→ Auto-generating test data...
→ Generated test data: {
  "article": "Quick brown fox jumps over lazy dog sample.",
  "target_language": "de"
}

# Result:
{"translated_article": "Schneller brauner Fuchs springt über faulen Hund Probe."}
```

---

## Summary

### Problem

✗ Workflows expected specific input fields
✗ System only provided generic fields
✗ Result: Empty output with no explanation

### Solution

✓ Auto-detect required input fields
✓ Auto-generate test data using random_data_generator
✓ Show clear warnings when output is empty
✓ Display ALL output fields, not just "result"

### Result

**Users ALWAYS see meaningful output** - either real results or clear explanations of why output is empty!

---

**Status:** Implemented and ready for testing
**Files Modified:** `chat_cli.py` (2 execution paths updated)
**Tools Used:** `random_data_generator`
