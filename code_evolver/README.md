# Code Evolver

A Python-based system for evolving code through AI-assisted generation, execution, and evaluation using local Ollama models.

## Overview

Code Evolver is a minimal, buildable system for code-evolving nodes with execution, evaluation, and a shared registry. It uses local Ollama models (tiny, llama3, codellama) to:

- Generate code from natural language prompts
- Execute code in sandboxed environments with metrics collection
- Evaluate performance using AI models
- Store and track node evolution in a file-based registry
- Auto-evolve code based on performance metrics

## Features

- **AI-Powered Code Generation**: Uses Ollama's codellama model to generate Python code
- **Sandboxed Execution**: Safe code execution with timeout and memory limits
- **Multi-Model Evaluation**: Fast triage with tiny model, comprehensive evaluation with llama3
- **Performance Tracking**: Automatic metrics collection (latency, memory, CPU usage)
- **Registry System**: File-based storage of nodes, metrics, and evaluations
- **Interactive CLI**: Chat-based interface for natural interaction
- **Auto-Evolution**: Monitors performance and triggers improvements automatically
- **Cross-Platform**: Builds to standalone executables for Windows, Linux, and macOS

## Prerequisites

### 1. Install Python

Python 3.11 or higher is required.

### 2. Install Ollama

Download and install Ollama from [https://ollama.com](https://ollama.com)

**Windows 11:**
- Download the Windows installer
- Run the installer
- Ollama will start automatically in the system tray

**Linux/macOS:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 3. Pull Required Models

```bash
ollama pull codellama
ollama pull llama3
ollama pull tiny
```

Verify models are available:
```bash
ollama list
```

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies:**

```bash
cd code_evolver
pip install -r requirements.txt
```

3. **Verify setup:**

```bash
python orchestrator.py check
```

You should see:
```
✓ Connected to Ollama server
Available models: codellama, llama3, tiny
✓ Setup OK
```

## Usage

### Command-Line Interface

#### Check Setup
```bash
python orchestrator.py check
```

#### Generate a Node
```bash
python orchestrator.py generate compress_text_v1 "Text Compressor" \
  "Write a Python function that compresses text using run-length encoding"
```

#### Run a Node
```bash
python orchestrator.py run compress_text_v1 --input '{"text":"AAAABBB"}'
```

#### Full Workflow (Generate + Run + Evaluate)
```bash
python orchestrator.py full compress_text_v1 "Text Compressor" \
  "Write a Python function for text compression using RLE" \
  --input '{"text":"AAAABBBCCDAA"}'
```

#### List All Nodes
```bash
python orchestrator.py list
```

#### Evaluate a Node
```bash
python orchestrator.py evaluate compress_text_v1
```

### Interactive CLI Chat Interface

Launch the interactive chat interface:

```bash
python chat_cli.py
```

Commands in chat mode:
- `generate <node_id>` - Start interactive node generation
- `run <node_id>` - Run an existing node
- `list` - List all nodes in registry
- `evaluate <node_id>` - Evaluate a node
- `config` - Show current configuration
- `auto on/off` - Enable/disable auto-evolution
- `help` - Show available commands
- `exit` or `quit` - Exit the chat

### Python API

```python
from src import OllamaClient, Registry, NodeRunner, Evaluator

# Initialize
client = OllamaClient()
registry = Registry("./registry")
runner = NodeRunner("./nodes")
evaluator = Evaluator(client)

# Generate code
code = client.generate_code(
    "Write a function to compress text using RLE"
)

# Save and run
runner.save_code("my_node", code)
stdout, stderr, metrics = runner.run_node(
    "my_node",
    {"text": "AAABBB"}
)

# Evaluate
result = evaluator.evaluate_full(stdout, stderr, metrics)
print(f"Score: {result['final_score']}")
```

## Configuration

Configuration is managed through `config.yaml`:

```yaml
# Ollama settings
ollama:
  base_url: "http://localhost:11434"
  models:
    generator: "codellama"
    evaluator: "llama3"
    triage: "tiny"

# Execution settings
execution:
  default_timeout_ms: 5000
  max_memory_mb: 256

# Auto-evolution settings
auto_evolution:
  enabled: true
  performance_threshold: 0.15  # Trigger evolution if score improves by 15%
  min_runs_before_evolution: 3
  check_interval_minutes: 60

# Registry settings
registry:
  path: "./registry"
  backup_enabled: true
  max_versions_per_node: 10

# Logging
logging:
  level: "INFO"
  file: "code_evolver.log"
```

Create a config file:
```bash
python orchestrator.py init-config
```

## Auto-Evolution

Auto-evolution monitors node performance and triggers improvements when performance degrades or opportunities for optimization are detected.

### How It Works

1. **Performance Monitoring**: Tracks metrics for each node run
2. **Threshold Detection**: Compares current vs. historical performance
3. **Mutation Trigger**: When threshold is crossed, generates improved version
4. **A/B Testing**: Runs both versions and keeps the better one
5. **Registry Update**: Updates lineage and version history

### Enable Auto-Evolution

Via CLI:
```bash
python orchestrator.py config --auto-evolution on
```

Via config file:
```yaml
auto_evolution:
  enabled: true
  performance_threshold: 0.15
```

Via interactive chat:
```
> auto on
Auto-evolution enabled
```

## Building Executables

### Windows

```bash
python build.py --platform windows
```

Output: `dist/code_evolver.exe`

### Linux

```bash
python build.py --platform linux
```

Output: `dist/code_evolver`

### macOS

```bash
python build.py --platform macos
```

Output: `dist/code_evolver.app`

### Build for All Platforms

```bash
python build.py --all
```

## Examples

### Example 1: Text Compressor

```bash
python examples/text_compressor.py
```

This example demonstrates:
- Generating a RLE compression algorithm
- Testing with multiple inputs
- Collecting performance metrics
- Evaluating correctness and performance

### Example 2: Custom Node

```python
from src import OllamaClient, Registry, NodeRunner, Evaluator

# Create orchestrator
client = OllamaClient()
registry = Registry()
runner = NodeRunner()
evaluator = Evaluator(client)

# Define and generate
node_id = "palindrome_checker"
prompt = """
Write a Python function:
- def is_palindrome(text: str) -> bool
- Returns True if text is a palindrome
- Include __main__ that reads JSON {"text": "..."} from stdin
- Prints {"is_palindrome": bool, "text": "..."}
"""

code = client.generate_code(prompt)
runner.save_code(node_id, code)

# Test
result = runner.run_node(node_id, {"text": "racecar"})
print(result)
```

## Directory Structure

```
code_evolver/
├── orchestrator.py          # Main CLI entry point
├── chat_cli.py             # Interactive chat interface
├── build.py                # Build script for executables
├── config.yaml             # Configuration file
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── src/                   # Core modules
│   ├── __init__.py
│   ├── ollama_client.py   # Ollama API client
│   ├── registry.py        # File-based registry
│   ├── node_runner.py     # Code execution engine
│   ├── evaluator.py       # Performance evaluation
│   ├── config_manager.py  # Configuration management
│   └── auto_evolver.py    # Auto-evolution engine
│
├── prompts/               # Prompt templates
│   ├── code_generation.txt
│   ├── evaluation.txt
│   └── triage.txt
│
├── examples/              # Example scripts
│   └── text_compressor.py
│
├── nodes/                 # Generated node code
│   └── [node_id]/
│       └── main.py
│
└── registry/              # Node registry
    ├── index.json
    └── [node_id]/
        ├── node.json
        ├── metrics.json
        ├── evaluation.json
        └── run.log
```

## Workflows

### Workflow A: Generate Code and Run

1. Select or define a node concept
2. Prompt codellama with specifications
3. Generate and save code
4. Execute in sandbox with test inputs
5. Collect metrics (latency, memory, exit code)
6. Quick triage with tiny model
7. Comprehensive evaluation with llama3
8. Store results in registry

### Workflow B: Auto-Evolution

1. Monitor node performance over time
2. Detect performance degradation or improvement opportunities
3. Generate mutation prompt based on metrics and goals
4. Create new version (v1.1.0) with targeted improvements
5. A/B test: run both versions
6. Select best version based on scores
7. Update registry with lineage information

## Troubleshooting

### "Cannot connect to Ollama"

1. Check if Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. If not running, start it:
   - Windows: Check system tray, or run `ollama serve`
   - Linux/macOS: `ollama serve`

### "Model not found"

Pull the required models:
```bash
ollama pull codellama
ollama pull llama3
ollama pull tiny
```

### Code Generation Timeout

Increase timeout in config:
```yaml
execution:
  default_timeout_ms: 10000  # 10 seconds
```

### Poor Evaluation Quality

1. Ensure you're using appropriate models
2. Check prompt templates in `prompts/`
3. Adjust temperature in `ollama_client.py`

## Performance Optimization

- **Use triage model first**: The tiny model is fast for quick pass/fail checks
- **Cache generated code**: Don't regenerate if code hasn't changed
- **Batch evaluations**: Run multiple test cases before evaluation
- **Adjust timeouts**: Set realistic timeouts based on task complexity

## Security Considerations

**⚠️ Warning**: This system executes AI-generated code. While it includes basic sandboxing:

- **Timeout limits**: Prevents infinite loops
- **Memory limits**: Prevents excessive memory usage
- **No network access by default**: Generated code can't make network calls (unless Python allows it)

**Best Practices**:
1. Review generated code before running
2. Run in isolated environment (VM, container)
3. Don't run with elevated privileges
4. Monitor system resources
5. Keep backups of important data

## Roadmap

### v0.2
- ✅ Interactive CLI chat interface
- ✅ Configuration management
- ✅ Auto-evolution engine
- ✅ Executable builds

### v1.0
- [ ] Distributed registry with consensus
- [ ] Multi-language support (JavaScript, Go, Rust)
- [ ] Web UI dashboard
- [ ] Docker container support
- [ ] Advanced sandboxing (cgroups, namespaces)
- [ ] Fine-tuned specialist evaluator models
- [ ] Storage and evaluator node types
- [ ] Git integration for version control

## Contributing

This is a starter system. Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built on [Ollama](https://ollama.com) for local LLM inference
- Inspired by genetic algorithms and code evolution research
- Uses Python's subprocess for sandboxed execution

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review example scripts

---

**Happy Code Evolving! 🧬🤖**
