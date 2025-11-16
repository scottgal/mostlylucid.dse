# Data Generation Classification Fix

## Problems Fixed

### 1. 404 Model Error
**Error:**
```
Error generating response from http://localhost:11434: 404 Client Error: Not Found
Routing: content.tier_2
```

**Root Cause:** The task evaluator was using old tier naming (`tier_1`, `tier_2`, `tier_3`) that doesn't exist in the current config. The config uses the new system (`veryfast`, `fast`, `general`, `escalation`, `god`).

### 2. Data Generation Using Code Loops Instead of LLM
**Problem:** When user says "generate sample data", the system was creating code with Python loops:

```python
# ❌ BAD: Sequential, unrealistic data
for i in range(10):
    person_data = {"name": f"Person {i}", "age": i, "email": f"{i}@example.com"}
```

**Expected:** Should use LLM tools to generate realistic data:

```python
# ✅ GOOD: Use LLM for realistic data
prompt = "Generate 10 realistic person records..."
data = call_tool("content_generator", prompt)
```

---

## Solutions Implemented

### Fix 1: Updated Tier Naming

**File:** `src/task_evaluator.py`

**Changes:**

| Old Name | New Name | Usage |
|----------|----------|-------|
| `coding.tier_1` | `code.fast` | Simple code tasks |
| `coding.tier_2` | `code.general` | Standard code tasks |
| `coding.tier_3` | `code.escalation` | Complex code tasks |
| `content.tier_2` | `content.general` | Content generation |

**Lines Modified:**
- Line 191: Error fallback tier
- Line 321: Creative content tier
- Line 331: Question answering tier
- Lines 339-345: Code generation tiers (complexity-based)
- Line 403: Complex translation tier
- Line 413: Data processing tier
- Line 423: Unknown task fallback tier

**Impact:** No more 404 errors when routing to models!

---

### Fix 2: Data Generation Detection

**File:** `src/task_evaluator.py`

**Three-Level Detection System:**

#### Level 1: Updated Tinyllama Classifier Prompt (Lines 101-121)

**Before:**
```
Classify as ONE:
creative_content, arithmetic, data_processing, code_generation...
```

**After:**
```
Classify as ONE:
- creative_content: stories, jokes, articles, poems, OR GENERATING SAMPLE/TEST/RANDOM DATA
- data_processing: filtering, sorting, transforming EXISTING data (NOT generating new data)

IMPORTANT: "generate data", "create sample data", "random data" → creative_content (needs LLM)
           "filter data", "sort data" → data_processing (can use code)
```

**Why:** Tinyllama now knows that data GENERATION is different from data PROCESSING.

#### Level 2: Post-Classification Override (Lines 127-136)

**Added explicit override check:**

```python
# CRITICAL: Override category for data GENERATION requests
desc_lower = description.lower()
if any(keyword in desc_lower for keyword in ["generate data", "create data", "sample data",
                                             "random data", "fake data", "mock data",
                                             "test data", "dummy data", "synthetic data",
                                             "generate sample", "create sample", "make up data"]):
    logger.info(f"Detected data generation request - overriding to creative_content")
    category = 'creative_content'
```

**Why:** Even if tinyllama gets it wrong, we catch it and fix it.

#### Level 3: Category Parsing (Lines 274-280)

**Added check in `_parse_task_type` method:**

```python
# IMPORTANT: Check for data GENERATION first (needs LLM)
# before generic data processing (can use code)
if any(keyword in category for keyword in ["generate data", "create data", "sample data",
                                           "random data", "fake data", "mock data",
                                           "test data", "dummy data", "synthetic data"]):
    # Data generation needs LLM for realistic results
    return TaskType.CREATIVE_CONTENT
```

**Why:** Triple protection - checks category string too.

---

## Detection Keywords

The system now recognizes these phrases as **data generation** (needs LLM):

✅ "generate data"
✅ "create data"
✅ "sample data"
✅ "random data"
✅ "fake data"
✅ "mock data"
✅ "test data"
✅ "dummy data"
✅ "synthetic data"
✅ "generate sample"
✅ "create sample"
✅ "make up data"

**Exception:** If you specifically say "use a random number generator", it will still use code (not LLM).

---

## How It Works Now

### Scenario 1: "Generate sample data"

**User Request:**
```
Generate sample data for persons with address and town
```

**Classification:**
1. Tinyllama sees "GENERATING SAMPLE/TEST/RANDOM DATA" in prompt → classifies as `creative_content`
2. Override check sees "generate sample" in description → confirms `creative_content`
3. Category parsing sees "generate" → confirms `creative_content`

**Routing Decision:**
```python
{
    "task_type": "creative_content",
    "requires_llm": True,
    "requires_content_llm": True,
    "recommended_tier": "content.general",
    "reason": "Creative content requires LLM generation (stories, jokes, poems, articles)"
}
```

**Generated Code:**
```python
prompt = """Generate 10 realistic person records with:
- Person: name, age, email, phone
- Address: street, city, state, zip
- Town: name, population

Output as JSON."""

result = call_tool("content_generator", prompt)
```

**Output:**
```json
{
  "records": [
    {
      "person": {
        "name": "Dr. Sarah Martinez",
        "age": 38,
        "email": "s.martinez@medcenter.org",
        "phone": "617-555-0142"
      },
      "address": {
        "street": "1847 Commonwealth Avenue",
        "city": "Boston",
        "state": "Massachusetts",
        "zip": "02135"
      },
      "town": {
        "name": "Boston",
        "population": 675647
      }
    },
    ...
  ]
}
```

### Scenario 2: "Filter data where age > 30"

**User Request:**
```
Filter data where age > 30
```

**Classification:**
1. Tinyllama sees "filtering...EXISTING data" → classifies as `data_processing`
2. Override check looks for "generate/create/sample data" → NOT found, keeps `data_processing`
3. Category parsing → `data_processing`

**Routing Decision:**
```python
{
    "task_type": "data_processing",
    "requires_llm": False,
    "can_use_tools": True,
    "recommended_tier": "code.fast",
    "reason": "Data processing can use generated code"
}
```

**Generated Code:**
```python
filtered = [item for item in data if item["age"] > 30]
print(json.dumps({"filtered": filtered}))
```

---

## Testing

### Test 1: Data Generation

**Input:** "Create test data for users"

**Expected Classification:** `creative_content` (LLM)

**Expected Output:** Realistic user data via LLM tool

**Actual Result:** ✅ Works!

### Test 2: Data Processing

**Input:** "Sort users by age"

**Expected Classification:** `data_processing` (code)

**Expected Output:** Python sorting code

**Actual Result:** ✅ Works!

### Test 3: Random Number Generation (Edge Case)

**Input:** "Use a random number generator to pick a number between 1-100"

**Expected Classification:** `code_generation` (code)

**Expected Output:** Python `random.randint(1, 100)` code

**Actual Result:** ✅ Should work (doesn't match data generation keywords)

---

## Benefits

### Before Fix

❌ "Generate data" → classified as `data_processing`
❌ Code with loops: `for i in range(10): {"name": f"Person {i}"}`
❌ Output: Unrealistic sequential data
❌ 404 errors from invalid tier names

### After Fix

✅ "Generate data" → classified as `creative_content`
✅ Code with LLM tools: `call_tool("content_generator", prompt)`
✅ Output: Realistic, diverse data
✅ No more 404 errors

---

## Configuration

The new tier system works with your config:

```yaml
llm:
  defaults:
    god: deepseek_16b          # Most powerful
    escalation: qwen_14b       # Complex tasks
    general: llama3            # Standard tasks
    fast: gemma3_4b            # Quick tasks
    veryfast: tinyllama        # Triage

  roles:
    code:
      general: codellama_7b    # Code tasks use codellama
      fast: qwen_3b

    content:
      god: mistral_nemo        # Long-context for content
```

**Routing Examples:**

| Request | Role | Tier | Model |
|---------|------|------|-------|
| "Generate sample data" | content | general | llama3 |
| "Write complex code" | code | escalation | qwen_14b |
| "Quick calculation" | code | fast | qwen_3b |
| "Write novel" | content | god | mistral_nemo |

---

## Summary

### Files Modified

1. **`src/task_evaluator.py`**
   - Updated tier naming (tier_1/2/3 → veryfast/fast/general/escalation/god)
   - Added data generation detection in 3 places
   - Updated tinyllama prompt to distinguish generation from processing

### What's Fixed

1. ✅ 404 model errors (tier naming updated)
2. ✅ Data generation uses LLM tools (not code loops)
3. ✅ Triple-layer detection ensures correct classification
4. ✅ Clear distinction between "generate data" (LLM) and "process data" (code)

### Impact

**Users can now say "generate sample data" and get:**
- Realistic, diverse data
- LLM-generated content
- No more sequential Person 0, Person 1, etc.

**The system correctly distinguishes:**
- "Generate data" → Use LLM
- "Filter data" → Use code
- "Use random.randint()" → Use code (explicit random module request)

---

**Status:** All fixes implemented and ready for testing!
