# Code Evolver

An intelligent AI-powered system for evolving code through specification-based generation, semantic search, fitness-based tool selection, and continuous optimization using local Ollama models.

## Overview

Code Evolver is an advanced self-improving code generation system that uses multiple AI models working together. The system features:

- **Specification-Based Generation**: Overseer model creates detailed specs, specialized code models implement them
- **Semantic Code Reuse**: Intelligent SAME/RELATED/DIFFERENT classification prevents regenerating similar code
- **Fitness-Based Tool Selection**: Multi-dimensional scoring (similarity + speed + cost + quality) chooses the best tool
- **RAG Memory System**: Stores and retrieves successful solutions with Qdrant vector database
- **Template Modification**: Reuses existing code as templates for related tasks instead of generating from scratch
- **Auto-Evolution**: Continuously monitors and improves code based on performance metrics

## Key Innovations

### 🎯 Specification-Based Planning
The **Overseer (llama3)** creates comprehensive specifications including:
- Problem definition with exact inputs/outputs
- Requirements & constraints (performance, safety limits)
- Implementation plan with algorithms and data structures
- Input/output interface specification
- Test cases and edge case handling

The **Code Generator (codellama)** then implements this specification exactly, ensuring:
- Consistent interfaces across all generated code
- Proper error handling and safety limits
- No hallucinations or missing requirements

### 🧠 Semantic Task Classification
Uses **tinyllama** triage model to classify task relationships:
- **SAME**: Identical tasks (ignore typos/wording) → Reuse as-is
  - "fibonacci sequence" vs "fibonaccie sequence and output" → SAME
- **RELATED**: Same domain, different variation → Use as template and modify
  - "fibonacci sequence" vs "fibonacci backwards" → RELATED
- **DIFFERENT**: Completely different tasks → Generate from scratch
  - "fibonacci" vs "write a story" → DIFFERENT

### 🎯 Fitness-Based Tool Selection
Multi-dimensional fitness function considers:
- **Semantic similarity** (0-100): How well it matches the task
- **Speed tier**: Fast tools get +20 bonus, slow get -20 penalty
- **Cost tier**: Free/low-cost tools get +15 bonus
- **Quality tier**: Excellent quality gets +15 bonus
- **Success rate**: Historical performance adds 0-10 bonus
- **Latency**: <100ms gets +15, >5s gets -10
- **Effort bonus**: Reusing existing code (>90% match) gets +30

Result: **Always picks the best tool for the job**, never uses wrong model for wrong task.

### 🔄 Intelligent Code Reuse
1. **Search RAG** for similar solutions
2. **Classify relationship** (SAME/RELATED/DIFFERENT)
3. **If SAME**: Execute existing code with new input
4. **If RELATED**: Use as template, modify for variation
5. **If DIFFERENT**: Generate from scratch

Example: "fibonacci backwards" finds "fibonacci forward" (77% similar) → Classified as RELATED → Uses forward code as template and adds reversal logic.

### 📊 Clean ChatGPT-Style Interface
- No debug logs cluttering output
- **Prominent result display**: `RESULT: 15` in bold green
- Extracts results from JSON: `result`, `output`, `answer`, `content`
- Shows workflow sequence and tool names
- Progress indicators without Unicode issues (ASCII-only)

### 🛡️ Demo Safety Limits
All generated code includes sensible limits:
- Fibonacci: First 20 numbers (max 100)
- Prime numbers: First 100 primes
- Iterations: Max 1000
- File sizes: Max 10MB
- List lengths: Max 10,000 items

### 📦 Context-Aware Specification Truncation
Respects model context windows:
```python
max_spec_chars = context_window(generator_model) * 2  # ~2 chars/token
if len(specification) > max_spec_chars:
    specification = specification[:max_spec_chars] + "[... truncated ...]"
```

## Features

- **Specification-Based Code Generation**: Overseer creates detailed specs, generator implements them exactly
- **Semantic Code Reuse**: SAME/RELATED/DIFFERENT classification for intelligent workflow reuse
- **Fitness-Based Tool Selection**: Multi-dimensional scoring always picks the right tool for the job
- **RAG Memory with Qdrant**: Vector database for semantic search and fitness-indexed retrieval
- **Template Modification**: Reuses and modifies existing code instead of regenerating
- **Sandboxed Execution**: Safe code execution with timeout and memory limits
- **Multi-Model Evaluation**: Fast triage with tiny model, comprehensive evaluation with llama3
- **Performance Tracking**: Automatic metrics collection (latency, memory, CPU usage)
- **Prominent Result Display**: ChatGPT-style clean output with bold results
- **Interactive CLI**: Modern chat interface with workflow visualization
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

Launch the modern chat interface with intelligent code generation:

```bash
python chat_cli.py
```

## Example Workflows

### Simple Calculation (First Time)
```
CodeEvolver> calculate 5 plus 10

> Searching for relevant tools...
OK Planning: Using general tools

> Consulting llama3...
OK Thinking: Specification complete

Generating code with specialized tool: General Code Generator...
OK Generated Code: calculate_5_plus_10
OK Tests passed
OK Optimization complete (best score: 1.20)

Running workflow...

RESULT: 15
```

### Same Task Again (Intelligent Reuse)
```
CodeEvolver> sum 5 and 10

OK Search RAG: Found calculator (95% match)
Note: Tasks are SAME (ignoring wording differences)

> Running workflow...
RESULT: 15
```
✅ **Instantly reuses** existing code without regenerating!

### Related Task (Template Modification)
```
CodeEvolver> calculate fibonacci sequence backwards

OK Search RAG: Found Fibonacci generator (77% match)
Note: Tasks are RELATED (same algorithm, different variation)
Using existing code as template and modifying...

> Consulting llama3...
OK Thinking: Specification complete (modification plan)

Generating code with template modifications...
OK Generated Code: fibonacci_backwards
OK Tests passed

RESULT: [89, 55, 34, 21, 13, 8, 5, 3, 2, 1, 1, 0]
```
✅ **Reuses forward Fibonacci** as template, adds reversal logic!

### Different Task (Generate from Scratch)
```
CodeEvolver> write a technical article about Python

OK Search RAG: Found code generators (60% match)
Note: Tasks are DIFFERENT (code vs writing)
Generating new solution from scratch...

Generating code with specialized tool: Long-Form Content Writer...
```
✅ **Correctly selects writing tool** for writing tasks!

### File I/O - Save Generated Content
```
CodeEvolver> generate a funny story about a programmer and save it to disk

> Consulting llama3...
OK Thinking: Specification complete

Generating content with specialized tool: Long-Form Content Writer...
OK Generated story (1,247 chars)

Saving to disk...
OK Saved to: ./output/programmer_story.txt

RESULT: Story saved successfully!
```
✅ **Safely saves to ./output/** directory only!

### File I/O - Load and Optimize
```
CodeEvolver> load src/ollama_client.py and suggest optimizations

Loading from disk...
OK Loaded: src/ollama_client.py (15,234 chars)

> Consulting llama3...
OK Thinking: Analyzing code for optimizations

Generating optimizations...
OK Found 5 optimization opportunities

Saving optimized version...
OK Saved to: ./output/ollama_client_optimized.py

RESULT: Optimizations saved!
```
✅ **Can load from anywhere** for self-optimization!

### Multi-File Generation
```
CodeEvolver> generate a microservice architecture with API gateway and user service

> Consulting llama3...
OK Thinking: Multi-file architecture specification

Generating api_gateway.py...
OK Saved to: ./output/api_gateway.py

Generating user_service.py...
OK Saved to: ./output/user_service.py

Generating docker-compose.yml...
OK Saved to: ./output/docker-compose.yml

RESULT: Microservice architecture generated in ./output/
```
✅ **Generates entire project structures**!

### Clear RAG Memory (Reset Test Data)
```
CodeEvolver> clear_rag

WARNING: This will clear all RAG memory and test data!
Type 'yes' to confirm: yes

OK RAG memory cleared

Also clear registry and generated nodes?
Type 'yes' to also delete all nodes: yes

OK Cleared nodes directory
OK Cleared registry
```

Commands in chat mode:
- `generate <node_id>` - Start interactive node generation
- `run <node_id>` - Run an existing node
- `list` - List all nodes in registry
- `evaluate <node_id>` - Evaluate a node
- `clear_rag` - Clear RAG memory and optionally registry/nodes (for testing)
- `config` - Show current configuration
- `auto on/off` - Enable/disable auto-evolution
- `help` - Show available commands
- `exit` or `quit` - Exit the chat

**💡 Tip**: Just type natural language! The system will interpret it as a generate command automatically.
Examples: `calculate fibonacci`, `write a story`, `add 10 and 20`

---

## 🚀 How It Works

For a deep dive into the advanced features, see **[ADVANCED_FEATURES.md](ADVANCED_FEATURES.md)**:
- Specification-Based Code Generation (Overseer → Generator pattern)
- Semantic Task Classification (SAME/RELATED/DIFFERENT)
- Fitness-Based Tool Selection (multi-dimensional scoring)
- RAG Memory System with Qdrant
- Template Modification for related tasks
- Context-aware specification truncation
- Demo safety limits

---

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

### v0.2 ✅ COMPLETED
- ✅ Interactive CLI chat interface with ChatGPT-style UX
- ✅ Configuration management with immutable config.yaml
- ✅ Auto-evolution engine with performance monitoring
- ✅ Executable builds for cross-platform deployment
- ✅ **Specification-based code generation** (Overseer → Generator pattern)
- ✅ **Semantic task classification** (SAME/RELATED/DIFFERENT)
- ✅ **Fitness-based tool selection** (multi-dimensional scoring)
- ✅ **RAG memory with Qdrant** vector database
- ✅ **Template modification** for code reuse
- ✅ **Context-aware truncation** for large specifications
- ✅ **Demo safety limits** for resource-intensive tasks
- ✅ **Prominent result display** with JSON extraction
- ✅ **clear_rag command** for test data cleanup

### v1.0
- [ ] Frontier model support (Claude, GPT-4, Gemini as backends)
- [ ] Multi-language support (JavaScript, Go, Rust)
- [ ] Web UI dashboard with workflow visualization
- [ ] Docker container support
- [ ] Advanced sandboxing (cgroups, namespaces)
- [ ] Distributed registry with consensus
- [ ] Fine-tuned specialist evaluator models
- [ ] Storage and evaluator node types
- [ ] Git integration for version control
- [ ] Self-improvement: Code Evolver evolving itself

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
- **Qdrant** vector database for semantic search and fitness indexing
- Inspired by genetic algorithms and code evolution research
- Uses Python's subprocess for sandboxed execution

### Development Credits

The advanced features in v0.2 were designed and implemented through collaboration:

**System Architecture & Direction**: Human-directed design decisions including:
- Specification-based planning architecture
- Semantic task classification (SAME/RELATED/DIFFERENT)
- Fitness-based tool selection concept
- Template modification workflow
- Input interface standardization
- Demo safety requirements
- Clean ChatGPT-style UX vision

**Implementation & Code**: Claude (Anthropic) - Implementation of features based on specifications and architectural guidance

This collaborative approach demonstrates the power of human insight combined with AI implementation capabilities.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation in `ADVANCED_FEATURES.md`
- Review example scripts

---

**Happy Code Evolving! 🧬🤖**

*"The best code is code that writes itself... and then improves itself."*
