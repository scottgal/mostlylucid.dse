# LLM-Based Data Generation Guide

## Problem

The current workflow for generating sample data just uses Python loops with sequential numbers:

```python
# ❌ BAD: Sequential, unrealistic data
for i in range(10):
    person_data = {
        "name": f"Person {i}",
        "age": i,
        "email": f"{i}@example.com"
    }
```

**Output:**
```json
{
  "name": "Person 0",
  "age": 0,
  "email": "0@example.com"
}
```

This is not realistic! We want the system to use LLM tools to generate truly realistic data.

---

## Solution: Use LLM Tools for Data Generation

### Approach 1: Use Content Generator Tool

**Generate realistic data with an LLM:**

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool


def main():
    input_data = json.load(sys.stdin)

    # Get the description
    description = input_data.get("input", input_data.get("description", ""))

    # Use LLM to generate realistic sample data
    prompt = """Generate 10 realistic person records with the following structure:
- Person details (name, age, email, phone)
- Address (street, city, state, zip)
- Town (name, population)

Make the data realistic and varied. Output as JSON with a "records" array."""

    # Call LLM tool to generate data
    result = call_tool("content_generator", prompt)

    # Try to parse as JSON, or wrap it if it's plain text
    try:
        data = json.loads(result)
        print(json.dumps(data))
    except:
        # LLM returned text, try to extract JSON or wrap it
        print(json.dumps({"generated_content": result}))


if __name__ == "__main__":
    main()
```

**Output (realistic!):**
```json
{
  "records": [
    {
      "person": {
        "name": "Sarah Johnson",
        "age": 34,
        "email": "sarah.j@techcorp.com",
        "phone": "555-0123"
      },
      "address": {
        "street": "421 Maple Avenue",
        "city": "Portland",
        "state": "Oregon",
        "zip": "97204"
      },
      "town": {
        "name": "Portland",
        "population": 652503
      }
    },
    ...
  ]
}
```

### Approach 2: Use Random Data Generator + LLM Enhancement

**Combine random generation with LLM polish:**

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool


def main():
    input_data = json.load(sys.stdin)

    records = []

    # Generate 10 records
    for i in range(10):
        # Use random_data_generator for base data
        schema = {
            "name": "string",
            "age": "number",
            "email": "string",
            "street": "string",
            "city": "string",
            "state": "string"
        }

        random_data = call_tool("random_data_generator", json.dumps(schema))
        person_data = json.loads(random_data)

        # Enhance with LLM to make it more realistic/detailed
        enhancement_prompt = f"""Given this person data: {json.dumps(person_data)}

Add realistic details:
- A plausible occupation based on their age
- A brief bio (2-3 sentences)
- Hobbies (2-3 items)

Return as JSON with fields: occupation, bio, hobbies"""

        enhancements = call_tool("content_generator", enhancement_prompt)

        try:
            enhanced = json.loads(enhancements)
            person_data.update(enhanced)
        except:
            # If LLM didn't return valid JSON, add as text
            person_data["bio"] = enhancements

        records.append(person_data)

    print(json.dumps({"records": records}))


if __name__ == "__main__":
    main()
```

### Approach 3: Fully LLM-Generated (Best for Realism)

**Let the LLM do ALL the work:**

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool


def main():
    input_data = json.load(sys.stdin)

    description = input_data.get("input", input_data.get("description", ""))

    # Build a detailed prompt for the LLM
    prompt = f"""Generate sample data for: {description}

Requirements:
- Create 10 realistic, diverse records
- Each record should include:
  * Person details: name, age, email, phone
  * Address: street number and name, city, state, ZIP code
  * Town: name, population
- Make names ethnically diverse
- Vary ages between 18-75
- Use real US cities and states
- Make population realistic for town size
- Ensure all data is plausible and internally consistent

Output ONLY valid JSON with this structure:
{{
  "records": [
    {{
      "person": {{"name": "...", "age": ..., "email": "...", "phone": "..."}},
      "address": {{"street": "...", "city": "...", "state": "...", "zip": "..."}},
      "town": {{"name": "...", "population": ...}}
    }},
    ...
  ]
}}"""

    # Use content generator with JSON output
    result = call_tool("content_generator", prompt)

    # Clean up any markdown code blocks
    if "```json" in result:
        result = result.split("```json")[1].split("```")[0].strip()
    elif "```" in result:
        result = result.split("```")[1].split("```")[0].strip()

    # Parse and validate
    try:
        data = json.loads(result)
        # Ensure it has the right structure
        if "records" in data and isinstance(data["records"], list):
            print(json.dumps(data, indent=2))
        else:
            print(json.dumps({"error": "Invalid structure", "raw": result}))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Failed to parse JSON: {e}", "raw": result}))


if __name__ == "__main__":
    main()
```

---

## Fixing the 404 Model Error

The error you're seeing:
```
Error generating response from http://localhost:11434: 404 Client Error: Not Found
```

This means the system is trying to use a model that doesn't exist. To fix:

### Option 1: Check Model Tier Configuration

Look at your config and see what model "content.tier_2" is mapped to:

```bash
cd code_evolver
grep -A 10 "tier_2" config*.yaml
```

Make sure that model exists in your Ollama:
```bash
ollama list | grep <model_name>
```

### Option 2: Use a Known Working Model

Instead of relying on tier routing, specify the model directly:

```python
# Instead of letting the system route to tier_2
result = call_tool("content_generator", prompt)

# You can also use call_llm directly with a specific model
result = call_llm("llama3", prompt)
```

### Option 3: Update Config to Use Available Models

Edit your config to map tiers to models you actually have:

```yaml
llm:
  tiers:
    content:
      tier_1: "qwen2.5-coder:3b"      # Fast
      tier_2: "codellama:7b"           # Medium
      tier_3: "deepseek-coder-v2:16b"  # Powerful
```

---

## Code Generation Prompt Enhancement

To make the system generate better code that uses LLM tools, we should update the code generation prompt.

**Add to the overseer prompt:**

```markdown
## Data Generation Best Practices

When generating sample/test data:

1. **Use LLM tools for realistic data:**
   ```python
   # ✅ GOOD: Use LLM to generate realistic data
   prompt = "Generate 10 realistic person records with names, ages, emails..."
   data = call_tool("content_generator", prompt)
   ```

2. **NOT sequential loops:**
   ```python
   # ❌ BAD: Sequential, unrealistic data
   for i in range(10):
       data = {"name": f"Person {i}", "age": i}
   ```

3. **For structured data, request JSON:**
   ```python
   prompt = "Generate data as JSON with structure: {fields...}"
   result = call_tool("content_generator", prompt)
   data = json.loads(result)
   ```

4. **Use random_data_generator for quick, varied data:**
   ```python
   schema = {"name": "string", "age": "number", "email": "string"}
   data = call_tool("random_data_generator", json.dumps(schema))
   ```
```

---

## Testing

### Test 1: Generate Realistic Person Data

**Request:** "Generate sample data with person details, address, and town"

**Expected code:**
```python
prompt = "Generate 10 realistic person records with..."
result = call_tool("content_generator", prompt)
```

**Expected output:**
```json
{
  "records": [
    {
      "person": {
        "name": "Maria Rodriguez",
        "age": 42,
        "email": "maria.r@consulting.com",
        "phone": "555-8421"
      },
      ...
    }
  ]
}
```

### Test 2: Generate Product Catalog Data

**Request:** "Create sample product catalog data"

**Expected code:**
```python
prompt = "Generate 20 realistic product catalog entries with..."
products = call_tool("content_generator", prompt)
```

---

## Summary

### Current Workflow (BAD)
❌ Uses Python loops with sequential numbers
❌ Generates unrealistic data (Person 0, age 0, etc.)
❌ No variation or diversity
❌ Looks fake and template-like

### LLM-Based Workflow (GOOD)
✅ Uses LLM tools to generate realistic data
✅ Varied, diverse, plausible names and details
✅ Internally consistent (city matches state, etc.)
✅ Looks like real data

### How to Make the System Use LLM Tools

1. **Update code generation prompts** to prefer LLM tools for data generation
2. **Fix model routing** so it doesn't try to use non-existent models
3. **Test workflows** to ensure they generate realistic data
4. **Use examples** that show LLM-based generation instead of loops

---

**Next Steps:**
1. Fix the 404 model error by checking your tier configuration
2. Regenerate the sample data workflow to use LLM tools
3. Update code generation prompts to encourage LLM-based data generation
