# Code Evolver - Quick Start Guide

Get up and running with Code Evolver in 5 minutes!

## Step 1: Install Prerequisites

### Install Python 3.11+
Make sure you have Python 3.11 or higher installed:
```bash
python --version
```

### Install Ollama

**Windows:**
1. Download from [https://ollama.com](https://ollama.com)
2. Run the installer
3. Ollama starts automatically

**Linux/macOS:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Pull Required Models
```bash
# Main models for code generation (REQUIRED)
ollama pull llama3
ollama pull codellama
ollama pull tinyllama

# Embedding model for RAG memory (OPTIONAL but recommended)
# Use this for semantic search in RAG memory
ollama pull nomic-embed-text
```

## Step 2: Install Code Evolver

```bash
cd code_evolver
pip install -r requirements.txt
```

## Step 3: Verify Setup

```bash
python orchestrator.py check
```

You should see:
```
✓ Connected to Ollama server
Available models: codellama:latest, llama3:latest, tinyllama:latest, ...
✓ Setup OK
```

If you see a warning about missing `nomic-embed-text`, that's fine - it's optional.

The system uses:
- **llama3**: Strategic planning (overseer) and evaluation
- **codellama**: Code generation
- **tinyllama**: Quick triage/testing
- **nomic-embed-text** (optional): Semantic embeddings for RAG memory (small & efficient)

## Step 4: Try Your First Generation

### Option A: Interactive Chat (Recommended)

```bash
python chat_cli.py
```

Then type:
```
generate Write a function that reverses a string
```

The system will:
1. Consult the overseer LLM for strategy
2. Generate code with codellama
3. Run unit tests
4. Evaluate performance
5. Store in registry

### Option B: Command Line

```bash
python orchestrator.py full my_reverser "String Reverser" \
  "Write a Python function that reverses a string" \
  --input '{"text":"hello"}'
```

## Step 5: Run Your Generated Code

```bash
python orchestrator.py run my_reverser --input '{"text":"world"}'
```

## Step 6: List All Nodes

```bash
python orchestrator.py list
```

## Common Commands

### Interactive Chat
```bash
python chat_cli.py
```

**Inside chat:**
- `generate <description>` - Create new code
- `run <node_id>` - Execute code
- `list` - Show all nodes
- `status` - Check system status
- `auto on` - Enable auto-evolution
- `help` - Show all commands
- `exit` - Quit

### Command Line

**Generate a node:**
```bash
python orchestrator.py generate <node_id> "<title>" "<prompt>"
```

**Run a node:**
```bash
python orchestrator.py run <node_id> --input '{"key":"value"}'
```

**Evaluate:**
```bash
python orchestrator.py evaluate <node_id>
```

**Full workflow:**
```bash
python orchestrator.py full <node_id> "<title>" "<prompt>"
```

## Configuration

Edit `config.yaml` to customize:

```yaml
ollama:
  models:
    overseer: "llama3"      # Plans approach
    generator: "codellama"   # Writes code
    evaluator: "llama3"      # Evaluates results
    escalation: "llama3"     # Fixes issues

auto_evolution:
  enabled: true
  performance_threshold: 0.15

testing:
  enabled: true
  auto_escalate_on_failure: true
```

## Examples

### Example 1: Text Processor

**Chat:**
```
> generate Write a function that counts word frequency in text
```

**CLI:**
```bash
python orchestrator.py full word_counter "Word Counter" \
  "Write a function that counts word frequency in text"
```

### Example 2: Data Transformer

**Chat:**
```
> generate Convert JSON to CSV format
```

### Example 3: Run Example Script

```bash
python examples/text_compressor.py
```

## Features

### 🤖 Overseer LLM
The overseer LLM analyzes your request and plans the approach before code generation. This results in better, more thoughtful solutions.

### 🧪 Automatic Testing
Generated code includes unit tests that run automatically. If tests fail, the system can escalate to a more powerful LLM to fix issues.

### 🧬 Auto-Evolution
Enable auto-evolution to let the system monitor performance and automatically improve code when needed:
```
> auto on
```

### 💾 Solution Memory
The system remembers solutions to problems and can reuse them for identical or similar tasks, saving time and compute.

### 📊 Performance Tracking
Every run is tracked with metrics (latency, memory, CPU) and stored for analysis and evolution.

## Building Executables

### Build for Your Platform
```bash
python build.py
```

### Build for Specific Platform
```bash
python build.py --platform windows
python build.py --platform linux
python build.py --platform macos
```

### Build for All Platforms
```bash
python build.py --all
```

Output will be in `dist/` directory.

## Troubleshooting

### "Cannot connect to Ollama"

**Check if running:**
```bash
curl http://localhost:11434/api/tags
```

**Start Ollama:**
- Windows: Check system tray or run `ollama serve`
- Linux/macOS: `ollama serve`

### "Model not found"

Pull the missing models:
```bash
ollama pull llama3
ollama pull codellama
ollama pull tinyllama
ollama pull nomic-embed-text
```

### Code Generation is Slow

This is normal - code generation can take 30-60 seconds depending on your hardware. The overseer consultation adds 10-20 seconds.

**Speed tips:**
- Use smaller models for testing
- Disable overseer for simple tasks (edit config.yaml)
- Run on GPU-enabled system

### Generated Code Has Errors

The system includes automatic error fixing:
1. Tests run automatically
2. If tests fail, escalation happens automatically (if enabled)
3. Up to 3 fix attempts with higher-level LLM

Enable in config:
```yaml
testing:
  auto_escalate_on_failure: true
  max_escalation_attempts: 3
```

## Next Steps

1. **Try the examples:**
   ```bash
   python examples/text_compressor.py
   ```

2. **Enable auto-evolution:**
   ```
   > auto on
   ```

3. **Explore the registry:**
   ```bash
   ls -la registry/
   ```

4. **Check solution memory:**
   ```python
   from src import SolutionMemory
   memory = SolutionMemory()
   stats = memory.get_statistics()
   print(stats)
   ```

5. **Build an executable:**
   ```bash
   python build.py
   ```

## Tips & Best Practices

### Writing Good Prompts

**Good:**
```
Write a function that validates email addresses using regex.
Include tests for common cases and edge cases.
Return True/False and a message explaining why.
```

**Not as good:**
```
email validator
```

### Using Tags

Organize your nodes with tags:
```bash
python orchestrator.py generate validator "Email Validator" \
  "..." --tags validation email utility
```

### Monitoring Performance

The system tracks all metrics automatically. Check them:
```bash
cat registry/<node_id>/metrics.json
cat registry/<node_id>/evaluation.json
```

## Support & Resources

- **Documentation:** See README.md for detailed info
- **Configuration:** Edit config.yaml for customization
- **Examples:** Check examples/ directory
- **Logs:** Check code_evolver.log for debugging

## What's Next?

- ✅ Basic code generation
- ✅ Auto-evolution
- ✅ Solution memory
- 🔄 Tools system (Python functions, workflows)
- 🔄 RAG for similar problem finding
- 🔄 Multi-language support
- 🔄 Web UI

---

**Happy coding! 🚀**
