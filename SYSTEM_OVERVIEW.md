# Code Evolver - Complete System Overview

## Quick Start

### Running the Chat Interface

```bash
cd code_evolver
python chat_cli.py
```

### Enabling Debug Logging

To see full LLM request/response conversations:

**Windows PowerShell:**
```powershell
$env:CODE_EVOLVER_DEBUG="1"
python chat_cli.py
```

**Linux/Mac:**
```bash
export CODE_EVOLVER_DEBUG=1
python chat_cli.py
```

**Windows CMD:**
```cmd
set CODE_EVOLVER_DEBUG=1
python chat_cli.py
```

## System Architecture

### Multi-Model Pipeline

The system uses specialized LLMs for different tasks:

| Model | Purpose | Endpoint(s) |
|-------|---------|-------------|
| **llama3** | Overseer - Strategic planning | localhost:11434 |
| **codellama** | Generator - Code writing | localhost:11434 + 192.168.0.56:11434 (round-robin) |
| **qwen2.5-coder:14b** | Escalation - Bug fixing | localhost:11434 |
| **llama3** | Evaluator - Quality analysis | localhost:11434 |
| **tinyllama** | Triage - Quick decisions | localhost:11434 |
| **nomic-embed-text** | Embeddings - RAG search | localhost:11434 |

### Code Generation Workflow

```
User Request: "generate add 1 plus 1"
    ↓
[1. Tool Selection]
    - Search for specialized tools via RAG
    - If found: Use specialized tool
    - If not found: Use general fallback (qwen2.5-coder:14b)
    ↓
[2. Overseer Planning - llama3]
    - Analyze task requirements
    - Determine approach and strategy
    - Consider available tools
    ↓
[3. Code Generation - codellama]
    - Round-robin between endpoints
    - Receives: Strategy, tools, requirements
    - Returns: JSON structure
      {
        "code": "executable Python code",
        "description": "brief description",
        "tags": ["tag1", "tag2"]
      }
    ↓
[4. JSON Parsing & Cleaning]
    - Extract code from JSON
    - Remove any markdown fences (```python)
    - Clean whitespace
    ↓
[5. Test Generation - codellama]
    - Generate unit tests
    - Clean test code
    ↓
[6. Execution & Validation]
    - Run tests
    - If PASS: Save to registry + RAG
    - If FAIL: Escalate to qwen2.5-coder:14b
    ↓
[7. Escalation (if needed) - qwen2.5-coder:14b]
    - Receives full context:
      * Original goal
      * Overseer strategy
      * Available tools
      * Error output
      * Current code
    - Generates fix with JSON structure
    - Re-test
    - Up to 3 escalation attempts
    ↓
[8. RAG Storage]
    - Store artifact with metadata
    - Auto-generate embeddings
    - Enable semantic search
```

## Key Features

### 1. JSON Structured Output

**Why**: Prevents mixing explanatory text with code (syntax errors)

**How it works**:
- Prompt explicitly requests JSON format
- LLM returns: `{"code": "...", "description": "...", "tags": [...]}`
- System extracts only the `code` field for execution
- Description and tags stored in RAG for search

**Example**:
```json
{
  "code": "import json\nimport sys\n\ndef add(a, b):\n    return a + b\n\nif __name__ == '__main__':\n    data = json.load(sys.stdin)\n    result = add(data['a'], data['b'])\n    print(json.dumps({'result': result}))",
  "description": "Adds two numbers",
  "tags": ["math", "addition", "calculator"]
}
```

### 2. Round-Robin Load Balancing

**Why**: Distribute code generation across multiple Ollama instances

**Configuration**:
```yaml
generator:
  model: "codellama"
  endpoints:
    - "http://localhost:11434"
    - "http://192.168.0.56:11434"
```

**Behavior**:
- Request 1 → localhost:11434
- Request 2 → 192.168.0.56:11434
- Request 3 → localhost:11434
- Pattern repeats

**Per-model tracking**: Each model has independent round-robin counter

### 3. General Fallback Tool

**Why**: Always have a tool available when no specialized match

**Configuration**:
```yaml
tools:
  general:
    name: "General Code Generator"
    type: "llm"
    description: "General purpose code generation for any programming task."
    llm:
      model: "qwen2.5-coder:14b"
      endpoint: null
    tags: ["general", "fallback", "code-generation"]
```

**User feedback**:
```
Using general code generator (fallback)  ← When no specialized tool matches
✓ Selected specialized tool: Code Reviewer  ← When specialized tool found
```

### 4. RAG Integration

**Two backends supported**:

**A. NumPy-based (Default)**
- Simple in-memory storage
- Good for small projects
- No external dependencies

**B. Qdrant (Scalable)**
- External vector database
- Production-grade
- Persistent storage

**Configuration**:
```yaml
rag_memory:
  use_qdrant: false  # Set true to use Qdrant
  qdrant_url: "http://localhost:6333"
  collection_name: "code_evolver_artifacts"
```

**Starting Qdrant**:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 5. Code Cleaning

**Problem**: LLMs often wrap code in markdown fences

**Solution**: Automatic cleaning at three points:
1. Initial code generation
2. Test code generation
3. Escalation fixes

**Cleaning logic**:
```python
def _clean_code(self, code: str) -> str:
    # Remove markdown fences
    code = re.sub(r'^```python\s*\n', '', code, flags=re.MULTILINE)
    code = re.sub(r'^```\s*\n', '', code, flags=re.MULTILINE)
    code = re.sub(r'\n```\s*$', '', code, flags=re.MULTILINE)
    # Trim whitespace
    return code.strip()
```

### 6. Enhanced Escalation

**Full context passed to debugging model**:
- Original goal/description
- Overseer's strategy
- Available tools
- Error output (stderr)
- Standard output (stdout)
- Current failing code

**Escalation JSON response**:
```json
{
  "code": "fixed Python code",
  "fixes_applied": [
    "Added missing import sys",
    "Fixed JSON output format"
  ],
  "analysis": "Code was missing sys import for stdin/stdout"
}
```

### 7. Debug Logging

**Enable with environment variable**:
```bash
export CODE_EVOLVER_DEBUG=1
```

**What you'll see**:
```
DEBUG:src.ollama_client:Request to http://localhost:11434:
DEBUG:src.ollama_client:  Model: codellama
DEBUG:src.ollama_client:  Prompt (first 200 chars): Based on this strategy:
Write a function that adds two numbers...

DEBUG:src.ollama_client:Response from http://localhost:11434:
DEBUG:src.ollama_client:  Length: 1234 characters
DEBUG:src.ollama_client:  First 300 chars: {
  "code": "import json\nimport sys\n\ndef add(a, b):\n    ...
```

**Production mode** (default):
```
INFO:src.ollama_client:Generating with model 'codellama' at http://localhost:11434...
✓ Generated 856 characters
```

## Common Operations

### Generate Code

```
CodeEvolver> generate fibonacci calculator
```

Output:
```
Consulting overseer LLM (llama3) for approach...
✓ Strategy received

Generating code with codellama...
INFO:src.ollama_client:Generating with model 'codellama' at http://localhost:11434...
✓ Generated code

Generating unit tests...
✓ Tests generated

Running tests...
✓ Tests passed

✓ Node 'fibonacci_calculator_12345' created successfully!
```

### Run Existing Node

```
CodeEvolver> run fibonacci_calculator_12345 {"n": 10}
```

### List All Nodes

```
CodeEvolver> list
```

### Search RAG

```
CodeEvolver> search "calculate fibonacci"
```

### Exit

```
CodeEvolver> exit
```

## Configuration Reference

### Model Configuration

**Simple format** (single endpoint):
```yaml
overseer:
  model: "llama3"
  endpoint: null  # Uses base_url
```

**Multi-endpoint format** (round-robin):
```yaml
generator:
  model: "codellama"
  endpoints:
    - "http://localhost:11434"
    - "http://192.168.0.56:11434"
```

### Context Windows

```yaml
context_windows:
  llama3: 8192
  codellama: 16384
  tinyllama: 2048
  nomic-embed-text: 8192
  qwen2.5-coder:14b: 32768
  default: 4096
```

### Execution Settings

```yaml
execution:
  default_timeout_ms: 5000
  max_memory_mb: 256
  max_retries: 3

  sandbox:
    allow_network: false
    allow_file_write: false
    temp_dir: "./temp"
```

## Troubleshooting

### Issue: Code still has markdown fences

**Symptom**: Files start with ```python

**Check**:
1. Are you in code_evolver directory?
2. Did you restart chat_cli.py after changes?

**Fix**:
```bash
cd code_evolver  # Important!
python chat_cli.py
```

### Issue: Still using llama3 for escalation

**Check config**:
```bash
cat config.yaml | grep -A 2 "escalation:"
```

**Should show**:
```yaml
escalation:
  model: "qwen2.5-coder:14b"
```

**Fix**: Restart chat_cli.py to reload config

### Issue: Model not found

**Pull model**:
```bash
ollama pull qwen2.5-coder:14b
```

**Verify**:
```bash
ollama list | grep qwen
```

### Issue: Remote endpoint not working

**Test connectivity**:
```bash
curl http://192.168.0.56:11434/api/tags
```

**Should return**: JSON list of available models

### Issue: RAG not storing artifacts

**Check Qdrant** (if use_qdrant: true):
```bash
curl http://localhost:6333/collections/code_evolver_artifacts
```

**Check NumPy backend**:
```bash
ls -la rag_memory/
```

Should see: `artifacts.json`, `embeddings.npy`, `index.json`

## Performance Metrics

### Typical Generation Time

| Operation | Duration | Notes |
|-----------|----------|-------|
| Overseer planning | 2-5s | llama3 strategic thinking |
| Code generation | 5-15s | codellama code writing |
| Test generation | 3-8s | codellama test writing |
| Test execution | 0.5-2s | Python runtime |
| Escalation | 10-30s | qwen2.5-coder:14b debugging |
| RAG embedding | 1-3s | nomic-embed-text |

### Load Balancing Impact

**Single endpoint**: 15s per generation
**Two endpoints**: ~7.5s per generation (near-linear scaling)

### Memory Usage

| Component | RAM Usage |
|-----------|-----------|
| Chat CLI | ~50MB |
| NumPy RAG | ~100MB + (artifacts * 0.5KB) |
| Qdrant | External process (~200MB base) |
| Ollama models | Per model (2-14GB) |

## Advanced Features

### Custom Tools

Add specialized tools in config.yaml:

```yaml
tools:
  email_validator:
    name: "Email Validator"
    type: "llm"
    description: "Validates and checks email addresses"
    llm:
      model: "llama3"
      endpoint: null
    tags: ["email", "validation", "regex"]
```

System will use semantic search to match tasks to tools.

### Auto-Evolution

```yaml
auto_evolution:
  enabled: true
  performance_threshold: 0.15  # 15% improvement triggers evolution
  min_runs_before_evolution: 3
  check_interval_minutes: 60
  max_versions_per_node: 10
  keep_best_n_versions: 3
```

System automatically evolves underperforming nodes.

### Hierarchical Task Decomposition

For complex tasks, the system can:
1. Break into subtasks
2. Create sub-nodes for each
3. Compose results
4. Optimize coordination

## Security Considerations

### Sandbox Settings

```yaml
sandbox:
  allow_network: false  # Prevent network access
  allow_file_write: false  # Prevent file writes
  temp_dir: "./temp"  # Isolated temp directory
```

### Code Execution

- All code runs in subprocess
- Timeout enforced (default: 5000ms)
- Memory limit enforced (default: 256MB)
- Standard input/output via JSON

### Model Endpoints

- Local endpoints trusted by default
- Remote endpoints should use HTTPS in production
- Consider firewall rules for multi-machine setup

## Best Practices

### 1. Task Descriptions

**Good**: "generate a function that validates email addresses using regex"
**Better**: "generate email validator that checks format, domain, and returns detailed error messages"

### 2. Tool Organization

- Create specialized tools for frequent tasks
- Use descriptive tags for semantic search
- Keep general tool as ultimate fallback

### 3. Model Selection

- Use llama3 for strategic/analytical tasks
- Use codellama for code generation
- Use qwen2.5-coder:14b for debugging complex issues
- Use tinyllama for quick yes/no decisions

### 4. Performance Optimization

- Use round-robin with multiple endpoints
- Enable Qdrant for large projects (>1000 artifacts)
- Set appropriate context windows
- Monitor debug logs to identify bottlenecks

### 5. Error Handling

- Let escalation handle most errors automatically
- Review failed escalations manually
- Update prompts based on common failure patterns
- Consider creating specialized tools for recurring tasks

## System Requirements

### Minimum

- Python 3.8+
- 8GB RAM
- Ollama installed with at least codellama model
- 10GB disk space

### Recommended

- Python 3.10+
- 16GB RAM
- Multiple Ollama instances for load balancing
- Qdrant for RAG storage
- 50GB disk space

### Production

- Python 3.11+
- 32GB RAM
- Distributed Ollama across multiple machines
- Qdrant cluster
- SSD storage
- Monitoring and logging infrastructure

## Files Overview

| File | Purpose | Key Features |
|------|---------|--------------|
| `chat_cli.py` | Interactive CLI | Code generation, testing, RAG integration |
| `orchestrator.py` | Task orchestration | Hierarchical decomposition, coordination |
| `src/ollama_client.py` | LLM communication | Round-robin, debug logging, retries |
| `src/config_manager.py` | Configuration | Model endpoints, validation, defaults |
| `src/tools_manager.py` | Tool selection | RAG search, fallback, specialization |
| `src/rag_memory.py` | NumPy RAG | In-memory embeddings, semantic search |
| `src/qdrant_rag_memory.py` | Qdrant RAG | Scalable vector storage |
| `src/node_runner.py` | Code execution | Sandboxing, I/O, timeout enforcement |
| `src/evaluator_llm.py` | Quality analysis | Code review, scoring |
| `config.yaml` | Main configuration | All system settings |

## What's Next

The system is fully operational with:

✅ JSON structured output separating code from metadata
✅ Round-robin load balancing across multiple endpoints
✅ General fallback tool for any task
✅ Enhanced escalation with full context
✅ Debug logging for troubleshooting
✅ RAG integration with Qdrant support
✅ Automatic code cleaning
✅ Windows compatibility

You can now:
1. Start generating code with `python chat_cli.py`
2. Enable debug mode with `CODE_EVOLVER_DEBUG=1`
3. Add specialized tools in config.yaml
4. Scale across multiple Ollama instances
5. Deploy Qdrant for production RAG

For questions or issues, refer to the implementation documentation:
- `JSON_STRUCTURED_OUTPUT.md` - JSON format details
- `FINAL_FIXES.md` - Recent bug fixes
- `IMPLEMENTATION_SUMMARY.md` - Architecture overview
- `QUICKSTART.md` - Getting started guide
