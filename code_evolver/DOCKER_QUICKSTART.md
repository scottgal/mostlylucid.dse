# Docker Workflow - Quick Start Guide

Get running in 5 minutes! 🚀

## Prerequisites

```bash
# 1. Docker installed
docker --version

# 2. Ollama running (if workflow uses LLMs)
ollama serve
ollama pull llama3

# 3. Python 3.11+ (for building)
python --version
```

## 1. Build a Workflow

```bash
cd code_evolver

# Build the example summarizer workflow
python docker_workflow.py build workflows/simple_summarizer.json
```

You'll see:
```
🔍 Dependencies:
  • LLM tools: 1
  • Executable tools: 0
  • Python packages: 1
  • Ollama models: llama3

🔨 Building Docker image: workflow-simple_summarizer:latest
...
✅ Success! Docker image ready: workflow-simple_summarizer:latest
```

## 2. Run the Workflow

```bash
# Run with JSON input
python docker_workflow.py run workflows/simple_summarizer.json \
  '{"text": "Artificial Intelligence (AI) is transforming how we live and work. Machine learning models can now understand natural language, generate images, and even write code. The field is rapidly evolving with new breakthroughs happening every month.", "max_length": 30}'
```

Output:
```json
{
  "success": true,
  "workflow_id": "simple_summarizer",
  "outputs": {
    "summary": "AI is revolutionizing society through machine learning advances in language understanding, image generation, and code creation, with rapid ongoing developments."
  }
}
```

## 3. Direct Docker Run

You can also run the container directly:

```bash
docker run --rm --add-host host.docker.internal:host-gateway \
  workflow-simple_summarizer:latest \
  '{"text": "Your text here...", "max_length": 50}'
```

## Usage Patterns

### Input from File

```bash
# Create input file
echo '{"text": "Long article text...", "max_length": 100}' > input.json

# Run with file
python docker_workflow.py run workflows/simple_summarizer.json --input-file input.json
```

### Force Rebuild

```bash
# Rebuild image before running
python docker_workflow.py run workflows/simple_summarizer.json '{"text": "..."}' --build
```

### Batch Processing

```bash
# Process multiple files
for file in articles/*.txt; do
  python docker_workflow.py run workflows/simple_summarizer.json \
    "{\"text\": \"$(cat $file)\", \"max_length\": 50}" \
    > "summaries/$(basename $file .txt).json"
done
```

## Clean Up

```bash
# Remove specific workflow image
python docker_workflow.py clean workflows/simple_summarizer.json

# Remove all workflow images
python docker_workflow.py clean --all
```

## Next Steps

- Read [DOCKER_WORKFLOWS.md](DOCKER_WORKFLOWS.md) for full documentation
- Create your own workflows in `workflows/` directory
- Check workflow format in `src/workflow_spec.py`

## Troubleshooting

### Can't connect to Ollama?

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Test from container
docker run --rm --add-host host.docker.internal:host-gateway alpine \
  wget -qO- http://host.docker.internal:11434/api/tags
```

### Build fails?

```bash
# Check Docker is running
docker ps

# Check disk space
df -h

# Clear Docker cache
docker system prune -a
```

### Need a specific Python package?

Add to your workflow's `tools.<tool_id>.requirements`:

```json
{
  "tools": {
    "my_tool": {
      "type": "llm",
      "requirements": ["pandas", "numpy"]
    }
  }
}
```

## Examples

### Simple Text Summarizer (Included)

```bash
python docker_workflow.py run workflows/simple_summarizer.json \
  '{"text": "Long article...", "max_length": 50}'
```

### Create Your Own Workflow

```json
{
  "workflow_id": "my_workflow",
  "portable": true,
  "inputs": {
    "my_input": {"type": "string", "required": true}
  },
  "outputs": {
    "my_output": {"type": "string", "source_reference": "steps.step1.output"}
  },
  "steps": [
    {
      "step_id": "step1",
      "type": "llm_call",
      "tool": "my_tool",
      "prompt_template": "Process: {my_input}",
      "input_mapping": {"my_input": "inputs.my_input"},
      "output_name": "output"
    }
  ],
  "tools": {
    "my_tool": {
      "type": "llm",
      "model": "llama3",
      "endpoint": "http://localhost:11434"
    }
  }
}
```

Build and run:
```bash
python docker_workflow.py build my_workflow.json
python docker_workflow.py run my_workflow.json '{"my_input": "test"}'
```

---

**That's it!** You're now running workflows in Docker containers. 🎉

For advanced usage, see [DOCKER_WORKFLOWS.md](DOCKER_WORKFLOWS.md)
