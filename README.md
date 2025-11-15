# Code Evolver: Self-Optimizing Multi-LLM Workflow System

> **An experiment in Directed Synthetic Evolution** - accompanying the blog series at [mostlylucid.net](https://www.mostlylucid.net/blog/category/Emergent%20Intelligence)

An AI-powered system that generates, executes, evaluates, and optimizes Python code using multiple LLM models. Features intelligent task classification, RAG-powered tool selection, automatic code generation, and self-optimization through iterative improvement.

## 🎯 What It Does

Code Evolver is a **self-assembling, self-optimizing workflow system** that:

1. **Understands** your task using intelligent LLM-based classification
2. **Plans** the optimal approach using an overseer model
3. **Generates** Python code with appropriate tool selection
4. **Tests** the code automatically with generated unit tests
5. **Optimizes** performance through iterative improvement
6. **Learns** from successful solutions via RAG memory

```mermaid
graph TD
    A[User Request] --> B[Task Classification]
    B --> C{Task Type?}
    C -->|ARITHMETIC| D[Fast Code Generator<br/>gemma3:4b]
    C -->|SIMPLE_CONTENT| E[Content Generator<br/>llama3 via call_tool]
    C -->|COMPLEX_CONTENT| E
    C -->|ALGORITHM| F[Powerful Model<br/>codellama/qwen]

    D --> G[Code Generation]
    E --> G
    F --> G

    G --> H[Unit Tests]
    H --> I{Tests Pass?}
    I -->|No| J[Adaptive Escalation<br/>3 attempts]
    J --> G
    I -->|Yes| K[Static Analysis<br/>flake8, pylint]
    K --> L[Optimization Loop<br/>3 iterations]
    L --> M[RAG Storage]
    M --> N[Executable Node]

    style B fill:#e1f5ff
    style G fill:#ffe1e1
    style L fill:#e1ffe1
    style M fill:#fff3e1
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/code_evolver
cd code_evolver

# Install dependencies
pip install -r requirements.txt

# Install Ollama models
ollama pull llama3
ollama pull codellama
ollama pull gemma3:4b

# Optional: Install Qdrant for scalable RAG
docker run -p 6333:6333 qdrant/qdrant
```

### Basic Usage

```bash
# Start interactive CLI
cd code_evolver
python chat_cli.py
```

```
CodeEvolver> add 10 and 20
> Task classified as ARITHMETIC
> Using Fast Code Generator (gemma3:4b)
✓ Code generated and tested
✓ Optimization complete (best score: 1.10)

RESULT: 30
```

## 📊 System Architecture

### High-Level Flow

```mermaid
sequenceDiagram
    participant User
    participant Classifier as Task Classifier<br/>(llama3)
    participant Overseer as Overseer LLM<br/>(llama3)
    participant Generator as Code Generator<br/>(codellama/gemma3)
    participant Tests as Unit Tests
    participant Optimizer as Optimizer
    participant RAG as RAG Memory<br/>(Qdrant)

    User->>Classifier: "write me a joke"
    Classifier->>Classifier: Analyze task complexity
    Classifier-->>User: SIMPLE_CONTENT

    User->>Overseer: Request specification
    Overseer->>RAG: Search similar specs
    RAG-->>Overseer: Related patterns
    Overseer-->>User: Detailed plan

    User->>Generator: Generate code
    Generator-->>User: Python code with call_tool()

    User->>Tests: Run unit tests
    Tests-->>User: ✓ Pass

    User->>Optimizer: Optimize (3 iterations)
    loop 3 times
        Optimizer->>Optimizer: Measure performance
        Optimizer->>Generator: Request improvements
        Generator-->>Optimizer: Optimized code
        Optimizer->>Tests: Verify
    end
    Optimizer-->>User: Best version

    User->>RAG: Store successful solution
    RAG-->>User: ✓ Stored for reuse
```

### Content Generation Flow

```mermaid
graph LR
    A[User: write me a joke] --> B[Classifier: SIMPLE_CONTENT]
    B --> C[Overseer: Create spec]
    C --> D[Generator: Create Python code]
    D --> E["Code:<br/>from node_runtime import call_tool<br/>content = call_tool('content_generator', prompt)"]
    E --> F[Runtime: Execute]
    F --> G[content_generator LLM<br/>llama3]
    G --> H[Creative Output:<br/>Why did the computer...?]
    H --> I[User receives joke]

    style B fill:#e1f5ff
    style E fill:#ffe1e1
    style G fill:#e1ffe1
    style H fill:#fff3e1
```

## 💡 Examples

### Example 1: Simple Arithmetic

```bash
CodeEvolver> add 5 and 8

> Task classified as ARITHMETIC (basic arithmetic operation)
> Using Fast Code Generator (gemma3:4b)
> Generating code...
✓ Generated 15 lines of code
✓ Tests passed
✓ Optimization complete (score: 1.10)

RESULT: 13
```

**Generated Code:**
```python
import json
import sys

def main():
    input_data = json.load(sys.stdin)

    # Extract numbers from description
    desc = input_data.get("description", "")
    numbers = [int(s) for s in desc.split() if s.isdigit()]

    if len(numbers) >= 2:
        result = numbers[0] + numbers[1]
    else:
        result = 0

    print(json.dumps({"result": result}))

if __name__ == "__main__":
    main()
```

### Example 2: Content Generation

```bash
CodeEvolver> write me a joke about programmers

> Task classified as SIMPLE_CONTENT (short joke generation)
> Using powerful model for content generation
> Generating code...
✓ Generated code with call_tool()
✓ Tests passed

RESULT:
"Why do programmers prefer dark mode?
Because light attracts bugs!"
```

**Generated Code:**
```python
import json
import sys
from node_runtime import call_tool

def main():
    input_data = json.load(sys.stdin)

    # Use LLM tool for creative content generation
    content = call_tool("content_generator", input_data.get("description"))

    print(json.dumps({"result": content}))

if __name__ == "__main__":
    main()
```

### Example 3: Complex Algorithm

```bash
CodeEvolver> calculate fibonacci sequence

> Task classified as ALGORITHM (fibonacci computation)
> Using powerful model (qwen2.5-coder:14b)
> Generating code...
✓ Generated optimized implementation
✓ Tests passed
✓ Optimization complete (score: 1.15)
```

**Generated Code:**
```python
import json
import sys

def fibonacci(n):
    """Calculate first n fibonacci numbers with safety limit."""
    # Safety limit to prevent infinite computation
    n = min(n, 100)

    if n <= 0:
        return []
    elif n == 1:
        return [0]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])

    return fib[:n]

def main():
    input_data = json.load(sys.stdin)
    desc = input_data.get("description", "")

    # Extract number from description, default to 10
    n = 10
    for word in desc.split():
        if word.isdigit():
            n = int(word)
            break

    result = fibonacci(n)
    print(json.dumps({"result": result}))

if __name__ == "__main__":
    main()
```

## 🔄 Optimization System

### How Optimization Works

```mermaid
graph TD
    A[Initial Code<br/>Score: 1.0] --> B[Iteration 1]
    B --> C{Measure Performance}
    C --> D[Latency: 950ms<br/>Memory: 2.1MB]
    D --> E[Analyze Bottlenecks]
    E --> F[Generate Improvement]
    F --> G[Test Improved Code]
    G --> H{Better?}
    H -->|Yes| I[Score: 1.08<br/>Keep changes]
    H -->|No| J[Discard changes]

    I --> K[Iteration 2]
    J --> K
    K --> L[Further optimize]
    L --> M[Score: 1.12]

    M --> N[Iteration 3]
    N --> O[Final optimization]
    O --> P[Best Score: 1.15<br/>Latency: 850ms<br/>Memory: 1.9MB]

    P --> Q[Store in RAG]
    Q --> R[Available for reuse]

    style A fill:#ffe1e1
    style I fill:#e1ffe1
    style M fill:#e1ffe1
    style P fill:#e1f5ff
    style Q fill:#fff3e1
```

### Optimization Example

```python
# Iteration 1: Initial code
def process_data(data):
    result = []
    for item in data:
        result.append(expensive_operation(item))
    return result

# Score: 1.0 (baseline)
# Latency: 1200ms
# Memory: 3.5MB

# Iteration 2: Optimized - use list comprehension
def process_data(data):
    return [expensive_operation(item) for item in data]

# Score: 1.05 (5% improvement)
# Latency: 1100ms
# Memory: 3.2MB

# Iteration 3: Optimized - add caching
_cache = {}
def process_data(data):
    return [
        _cache.setdefault(item, expensive_operation(item))
        for item in data
    ]

# Score: 1.15 (15% improvement)
# Latency: 850ms
# Memory: 2.8MB
```

## 🧠 RAG Memory System

### What Gets Stored

```mermaid
graph TB
    A[Successful Execution] --> B{Artifact Type}

    B -->|Specification| C[Overseer Plan<br/>- Task description<br/>- Strategy<br/>- Requirements]
    B -->|Code| D[Generated Code<br/>- Implementation<br/>- Tags<br/>- Quality score]
    B -->|Workflow| E[Complete Workflow<br/>- Steps taken<br/>- Tools used<br/>- Performance]
    B -->|Pattern| F[Reusable Pattern<br/>- Common solution<br/>- Best practices<br/>- Use cases]

    C --> G[Qdrant Vector DB]
    D --> G
    E --> G
    F --> G

    G --> H[Semantic Search]
    H --> I[Future Tasks]
    I --> J[Reuse & Adapt]

    style G fill:#e1f5ff
    style H fill:#e1ffe1
    style J fill:#fff3e1
```

### RAG Workflow Reuse

```mermaid
sequenceDiagram
    participant User
    participant Classifier
    participant RAG
    participant Overseer
    participant Generator

    User->>Classifier: "write a story about space"
    Classifier->>RAG: Search similar tasks
    RAG-->>Classifier: Found: "write a story about dragons"<br/>Similarity: 85%

    RAG->>Overseer: Here's a similar spec
    Note over Overseer: Original task: dragons<br/>New task: space<br/>Adapt the structure

    Overseer-->>Generator: Modified specification
    Note over Generator: Reuse proven structure<br/>Change theme to space<br/>Keep what works

    Generator-->>User: Optimized code (faster)<br/>Based on previous success
```

## 🛠️ Configuration

### Multi-Endpoint Setup

```yaml
# config.yaml
ollama:
  base_url: "http://localhost:11434"

  models:
    overseer:
      model: "llama3"
      endpoint: "http://powerful-cpu-machine:11434"

    generator:
      model: "codellama"
      endpoints:  # Round-robin load balancing
        - "http://gpu-machine-1:11434"
        - "http://gpu-machine-2:11434"

    evaluator:
      model: "llama3"
      endpoint: "http://localhost:11434"
```

### Tool Configuration

```yaml
tools:
  content_generator:
    name: "Content Generator"
    type: "llm"
    description: "Generates creative content (jokes, stories, articles)"
    llm:
      model: "llama3"
      endpoint: null
    cost_tier: "medium"
    speed_tier: "fast"
    quality_tier: "excellent"
    tags: ["content", "creative", "writing"]
```

## 📈 Performance Metrics

### Tracked Metrics

- **Latency**: Execution time in milliseconds
- **Memory**: Peak memory usage in MB
- **CPU Time**: Actual CPU processing time
- **Success Rate**: Percentage of successful executions
- **Quality Score**: Combined metric (latency + memory + correctness)

### Example Metrics

```
Optimization Results:
├─ Iteration 1: Score 1.00 (baseline)
│  ├─ Latency: 1200ms
│  └─ Memory: 3.5MB
├─ Iteration 2: Score 1.05 (+5%)
│  ├─ Latency: 1100ms
│  └─ Memory: 3.2MB
└─ Iteration 3: Score 1.15 (+15%)
   ├─ Latency: 850ms
   └─ Memory: 2.8MB

Best version selected: Iteration 3
```

## 🔧 Advanced Features

### Adaptive Escalation

When code fails tests, the system automatically escalates through multiple attempts:

1. **Attempt 1**: Fast model (codellama) with low temperature (0.1)
2. **Attempt 2**: Fast model with higher temperature (0.3) - more creative
3. **Attempt 3**: Powerful model (qwen2.5-coder:14b) with temp 0.5

### Static Analysis

Automatically runs multiple code quality tools:
- **flake8**: PEP 8 style checking
- **pylint**: Code quality analysis
- **mypy**: Type checking
- **black**: Code formatting validation

### Workflow Tracking

```mermaid
graph LR
    A[rag] --> B[llm: overseer]
    B --> C[keyword: classify]
    C --> D[llm: generate]
    D --> E[test: unit tests]
    E --> F[optimize: 3 iterations]
    F --> G[run: execute]

    style A fill:#e1f5ff
    style B fill:#ffe1e1
    style D fill:#ffe1e1
    style F fill:#e1ffe1
```

## 🎓 Use Cases

### 1. Rapid Prototyping
Generate working code for quick experiments and proof-of-concepts.

### 2. Code Learning
See how different LLMs approach the same problem, learn optimization techniques.

### 3. Automated Testing
Generate comprehensive unit tests automatically for your code.

### 4. Content Generation
Create stories, jokes, articles, and other creative content via LLM tools.

### 5. Algorithm Optimization
Let the system iteratively improve your algorithms for better performance.

## 📝 API Reference

### Command-Line Interface

```bash
# Generate code
python chat_cli.py
> add 10 and 20

# List available commands
> help

# Check system status
> status

# Toggle auto-evolution
> auto on/off
```

### Programmatic Usage

```python
from src import ChatCLI, ConfigManager

# Initialize
config = ConfigManager()
cli = ChatCLI(config)

# Generate code
success = cli.generate_code("calculate fibonacci")

# Execute node
stdout, stderr, metrics = cli.runner.run_node(
    "fibonacci_node",
    {"description": "calculate first 10 fibonacci numbers"}
)
```

## 🔍 Troubleshooting

### Common Issues

**Problem**: "Cannot connect to Ollama server"
```bash
# Solution: Start Ollama
ollama serve

# Verify models are available
ollama list
```

**Problem**: "Module 'node_runtime' not found"
```bash
# Solution: PYTHONPATH is automatically set by node_runner
# If running manually, set it:
export PYTHONPATH=/path/to/code_evolver:$PYTHONPATH
```

**Problem**: "Tests always fail"
```bash
# Check if dependencies are installed
pip install -r requirements.txt

# Verify static analysis tools
pip install flake8 pylint mypy black
```

## 🤝 Contributing

This is an experimental project. Contributions welcome!

### Areas for Improvement

- [ ] More sophisticated optimization algorithms
- [ ] Better error handling and recovery
- [ ] Additional LLM tool integrations
- [ ] Web UI for easier interaction
- [ ] Distributed execution across machines
- [ ] More comprehensive test coverage

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.ai) - Local LLM inference
- [Qdrant](https://qdrant.tech) - Vector database for RAG
- [Rich](https://github.com/Textualize/rich) - Terminal UI
- Multiple open-source LLMs (llama3, codellama, gemma3, qwen)

---

**Built with ❤️ for the AI community**

*An experiment in emergent intelligence through directed synthetic evolution*
