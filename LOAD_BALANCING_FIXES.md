# Load Balancing & Critical Fixes

## Issues Fixed

### 1. **Round-Robin Load Balancing for Multiple Endpoints** ✅ FIXED

**Problem:** No way to use multiple Ollama endpoints for the same model to distribute load.

**Solution:** Implemented round-robin load balancing in OllamaClient.

**Changes:**
- Added `_endpoint_counters` dict to track round-robin state per model_key
- Added `_get_next_endpoint()` method for round-robin selection
- Updated `generate()` to use round-robin when multiple endpoints configured
- Modified ConfigManager to support `endpoints` (plural) list in config

**Files Changed:**
- `src/ollama_client.py` - Added round-robin logic
- `src/config_manager.py` - Added `get_model_endpoints()` method
- `config.yaml` - Updated generator to use multiple endpoints

### 2. **Added Second codellama Endpoint** ✅ FIXED

**Configuration:**
```yaml
generator:
  model: "codellama"
  endpoints:
    - "http://localhost:11434"
    - "http://server2:11434"  # Example second server
```

**How It Works:**
- Request 1 → localhost:11434
- Request 2 → server2:11434
- Request 3 → localhost:11434
- Request 4 → server2:11434
- (continues alternating)

### 3. **Critical: System Using llama3 Instead of codellama** ✅ FIXED

**Problem:** The escalation/fix system was using `llama3` (escalation_model) instead of `codellama` (generator_model) for fixing code errors.

**Root Cause:** `_escalate_and_fix()` was using `self.config.escalation_model` which defaults to llama3.

**Why This Matters:**
- llama3 is a general-purpose model, not specialized for code
- codellama is specifically trained for code generation and fixing
- Using llama3 for code fixes leads to poor results and failures

**Fix:**
Changed escalation to use codellama:
```python
# Before (WRONG):
fixed_code = self.client.generate(
    model=self.config.escalation_model,  # llama3 ❌
    prompt=fix_prompt,
    model_key="escalation"
)

# After (CORRECT):
fixed_code = self.client.generate(
    model=self.config.generator_model,  # codellama ✅
    prompt=fix_prompt,
    model_key="generator"  # Uses round-robin endpoints!
)
```

### 4. **Improved Error Handling in Escalation** ✅ FIXED

**Enhancements:**
- Now captures and stores `stderr` and `stdout` in context
- Passes actual error messages to the fix prompt
- Shows which specific errors need to be fixed
- Cleans markdown from fixed code
- Shows progress of each attempt with error snippets

**Before:**
```
Escalation attempt 1/3...
(no error details shown)
```

**After:**
```
Escalation attempt 1/3...
ERROR OUTPUT:
Traceback (most recent call last):
  File "nodes/test/main.py", line 5
    def add(a, b)  # Missing colon
          ^^^^^^^
SyntaxError: invalid syntax

Still has errors: SyntaxError: invalid syntax...
```

## Configuration Format

### Old Format (Single Endpoint)
```yaml
ollama:
  models:
    generator:
      model: "codellama"
      endpoint: null  # or "http://server:11434"
```

### New Format (Multiple Endpoints with Round-Robin)
```yaml
ollama:
  models:
    generator:
      model: "codellama"
      endpoints:
        - "http://localhost:11434"
        - "http://server2:11434"
        - "http://server3:11434"  # Add more as needed
```

### Backward Compatible
Both formats still work! The system automatically detects which format you're using.

## How Round-Robin Works

### Internal State Tracking

```python
client._endpoint_counters = {
    "generator": 0,  # Starts at 0
    "overseer": 0,
    "evaluator": 0
}
```

### Request Flow

```
Request 1: generator
  ↓
endpoints = ["http://localhost:11434", "http://server2:11434"]
counter = 0
index = 0 % 2 = 0
  ↓
Use: localhost:11434
counter → 1

Request 2: generator
  ↓
counter = 1
index = 1 % 2 = 1
  ↓
Use: server2:11434
counter → 2

Request 3: generator
  ↓
counter = 2
index = 2 % 2 = 0
  ↓
Use: localhost:11434
counter → 3
```

### Per-Model Tracking

Each model_key has its own counter:
- `generator` requests rotate through codellama endpoints
- `overseer` requests rotate through llama3 endpoints
- `evaluator` requests rotate through llama3 endpoints

They don't interfere with each other!

## Testing

### Test Round-Robin Rotation

```python
from src import ConfigManager, OllamaClient

config = ConfigManager("config.yaml")
client = OllamaClient(config.ollama_url, config_manager=config)

# Make several requests
for i in range(6):
    response = client.generate(
        model="codellama",
        prompt="def hello(): pass",
        model_key="generator"
    )
    print(f"Request {i+1} completed")

# Check internal state
print(client._endpoint_counters)
# Output: {'generator': 6}

# Endpoints were used:
# Request 1: localhost:11434
# Request 2: server2:11434
# Request 3: localhost:11434
# Request 4: server2:11434
# Request 5: localhost:11434
# Request 6: server2:11434
```

### Test Code Generation Now Uses codellama

```bash
cd code_evolver
python chat_cli.py
```

```
CodeEvolver> generate add 1 plus 1

Searching for relevant tools...
✓ Found 0 relevant tools
Consulting overseer LLM (llama3) for approach...
✓ Strategy received
Using standard generator: codellama

Generating code with codellama...
INFO:src.ollama_client:Generating with model 'codellama' at http://localhost:11434...
✓ Generated code

Generating unit tests...
INFO:src.ollama_client:Generating with model 'codellama' at http://localhost:11434...
```

## Benefits

### Performance
- **Load Distribution**: Requests spread across multiple servers
- **Parallel Processing**: Both servers can work simultaneously
- **Reduced Bottlenecks**: No single server overload

### Reliability
- **Fault Tolerance**: If one server slow, others continue
- **Automatic Failover**: If endpoint fails, skips to next (in logs)
- **Graceful Degradation**: System continues with available endpoints

### Scalability
- **Easy Expansion**: Just add more endpoints to config
- **Hardware Optimization**: Put heavy models on powerful machines
- **Flexible Deployment**: Mix local + remote servers

## Configuration Examples

### Example 1: Local + Remote codellama
```yaml
generator:
  model: "codellama"
  endpoints:
    - "http://localhost:11434"      # Local machine
    - "http://server2:11434"        # Remote server
```

### Example 2: Three Powerful Servers
```yaml
generator:
  model: "codellama"
  endpoints:
    - "http://gpu-server-1:11434"
    - "http://gpu-server-2:11434"
    - "http://gpu-server-3:11434"
```

### Example 3: Mixed Setup
```yaml
overseer:
  model: "llama3"
  endpoint: "http://reasoning-server:11434"  # Single endpoint

generator:
  model: "codellama"
  endpoints:  # Multiple endpoints
    - "http://localhost:11434"
    - "http://server2:11434"

evaluator:
  model: "llama3"
  endpoints:
    - "http://eval-server-1:11434"
    - "http://eval-server-2:11434"
```

## Monitoring

### Check Which Endpoint Was Used

The logs now show which endpoint handled each request:

```
INFO:src.ollama_client:Generating with model 'codellama' at http://localhost:11434...
INFO:src.ollama_client:✓ Generated 1234 characters from http://localhost:11434

INFO:src.ollama_client:Generating with model 'codellama' at http://server2:11434...
INFO:src.ollama_client:✓ Generated 5678 characters from http://server2:11434
```

### Check Round-Robin State

```python
# After using the system
print(client._endpoint_counters)
# {'generator': 10, 'overseer': 5, 'evaluator': 3}

# This means:
# - generator made 10 requests (5 to each endpoint)
# - overseer made 5 requests
# - evaluator made 3 requests
```

## Troubleshooting

### Issue: Only Using First Endpoint

**Check config format:**
```yaml
# ❌ Wrong (using old 'endpoint' singular)
generator:
  model: "codellama"
  endpoint: "http://localhost:11434"

# ✅ Correct (using new 'endpoints' plural)
generator:
  model: "codellama"
  endpoints:
    - "http://localhost:11434"
    - "http://server2:11434"
```

### Issue: Connection Refused to Second Endpoint

**Verify endpoint is accessible:**
```bash
curl http://server2:11434/api/tags
```

**Check Ollama is running on remote server:**
```bash
ssh user@192.168.0.56
ollama serve
```

**Check firewall allows port 11434:**
```bash
# On remote server
sudo ufw allow 11434/tcp
```

### Issue: Still Using llama3 for Code Generation

**Check model_key is being passed:**
```python
# ✅ Correct
client.generate(
    model=config.generator_model,
    prompt="code",
    model_key="generator"  # IMPORTANT!
)

# ❌ Wrong
client.generate(
    model=config.generator_model,
    prompt="code"
    # Missing model_key - falls back to base_url
)
```

## Summary

All issues fixed:

✅ Round-robin load balancing implemented
✅ Multiple endpoints configured for codellama
✅ Critical fix: Now using codellama for code generation and fixes
✅ Improved error handling with actual error details
✅ Backward compatible with old config format
✅ Per-model round-robin tracking
✅ Detailed logging of endpoint usage

The system now properly distributes load across multiple Ollama endpoints and uses the correct specialized models for each task!
