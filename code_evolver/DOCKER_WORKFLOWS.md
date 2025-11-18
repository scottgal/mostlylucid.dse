# Docker Workflow Execution

Run workflows in **super-compact**, **ephemeral Docker containers** with full LLM and tool access.

## 🎯 Overview

This feature allows you to:
- **Build** tiny Docker images (~10-20MB) for individual workflows
- **Run** workflows in isolated containers with Ollama access
- **Tree-shake** dependencies to include ONLY what's needed
- **Compile** Python to single binary executables for minimal size
- **Execute** ephemeral containers that spin up, run, and tear down

Perfect for:
- **Production deployments** - Deploy workflows as containerized microservices
- **Edge computing** - Run on resource-constrained devices
- **Batch processing** - Execute thousands of workflow instances
- **CI/CD pipelines** - Integrate workflows into automated pipelines
- **Distributed systems** - Scale workflow execution across clusters

## 🚀 Quick Start

### 1. Build a Workflow Docker Image

```bash
python docker_workflow.py build workflows/simple_summarizer.json
```

This will:
- ✅ Analyze the workflow and determine dependencies
- ✅ Tree-shake to include ONLY required tools and configs
- ✅ Generate a standalone Python runner with everything inlined
- ✅ Compile to a single binary executable with Nuitka
- ✅ Build a multi-stage Docker image (~10-20MB)
- ✅ Configure Ollama access via `host.docker.internal`

### 2. Run the Workflow

```bash
docker run --rm --add-host host.docker.internal:host-gateway \
  workflow-simple_summarizer:latest \
  '{"text": "Your long text here...", "max_length": 50}'
```

Or use the CLI wrapper:

```bash
python docker_workflow.py run workflows/simple_summarizer.json \
  '{"text": "Your long text here...", "max_length": 50}'
```

### 3. One-Shot Build and Run

```bash
python docker_workflow.py run workflows/simple_summarizer.json \
  '{"text": "Your text here"}' --build
```

## 📋 Requirements

### System Requirements
- Docker installed and running
- Python 3.11+ (for building)
- 2GB disk space for build cache

### Ollama Access (if workflow uses LLMs)
- Ollama running on `localhost:11434`
- Required models pulled (e.g., `ollama pull llama3`)

Docker containers access Ollama via `host.docker.internal:11434` automatically.

## 🏗️ Architecture

### Multi-Stage Build Process

```
┌─────────────────────────────────────────────────────────┐
│  Stage 1: Analyzer                                      │
│  - Parse workflow.json                                  │
│  - Tree-shake dependencies (tools, configs)             │
│  - Generate standalone runner with embedded workflow    │
├─────────────────────────────────────────────────────────┤
│  Stage 2: Compiler                                      │
│  - Install Nuitka                                       │
│  - Compile Python → single binary (~5-10MB)             │
├─────────────────────────────────────────────────────────┤
│  Stage 3: Runtime Image (Final)                         │
│  - Alpine Linux base (~5MB)                             │
│  - Compiled binary executable                           │
│  - Ollama endpoint configured                           │
│  - Total: ~10-20MB                                      │
└─────────────────────────────────────────────────────────┘
```

### Tree-Shaking Process

The builder analyzes your workflow and includes ONLY:

**From this (300+ tools):**
```
code_evolver/
├── tools/
│   ├── llm/ (50+ tools)
│   ├── executable/ (30+ tools)
│   ├── openapi/ (20+ tools)
│   └── ... (200+ more)
```

**To this (just what you need):**
```
workflow_container/
└── Binary with embedded:
    ├── Workflow spec
    ├── 1-3 actual tool definitions
    └── Minimal runtime
```

## 📦 CLI Reference

### `build` - Build Docker Image

```bash
python docker_workflow.py build <workflow.json> [options]

Options:
  --tag, -t <name>          Docker image tag (default: workflow-<id>:latest)
  --output, -o <dir>        Build output directory (default: ./docker_build)
  --code-evolver-root <dir> Code evolver root (default: .)
```

**Example:**
```bash
python docker_workflow.py build workflows/article_writer.json -t my-writer:v1
```

### `run` - Run Workflow in Docker

```bash
python docker_workflow.py run <workflow.json> <inputs> [options]

Arguments:
  <workflow.json>  Path to workflow
  <inputs>         JSON string of inputs (default: {})

Options:
  --input-file, -f <file>   Read inputs from JSON file
  --tag, -t <name>          Docker image tag
  --build, -b               Force rebuild image first
  --output, -o <dir>        Build output directory
```

**Examples:**

With JSON string:
```bash
python docker_workflow.py run workflows/summarizer.json \
  '{"text": "Long article...", "max_length": 100}'
```

With input file:
```bash
python docker_workflow.py run workflows/summarizer.json \
  --input-file inputs.json
```

Force rebuild:
```bash
python docker_workflow.py run workflows/summarizer.json \
  '{"text": "..."}' --build
```

### `clean` - Clean Up Images

```bash
python docker_workflow.py clean [workflow.json] [options]

Options:
  --all, -a   Clean all workflow images
  --yes, -y   Skip confirmation
```

**Examples:**

Clean specific workflow:
```bash
python docker_workflow.py clean workflows/summarizer.json
```

Clean all workflow images:
```bash
python docker_workflow.py clean --all
```

## 🔧 How It Works

### 1. Dependency Analysis & Tree-Shaking

The builder analyzes your `workflow.json` to determine:

- **LLM tools** - Which LLM tools are called
- **Executable tools** - Which Python tools are needed
- **Models** - Which Ollama models are required
- **Python packages** - Which pip packages are needed
- **Python files** - Which source files to include

Example analysis output:
```
📊 Analyzing workflow: simple_summarizer

🔍 Dependencies:
  • LLM tools: 1
  • Executable tools: 0
  • Python packages: 1 (requests)
  • Ollama models: llama3
```

Only the tools and dependencies that are **actually used** get included.

### 2. Standalone Runner Generation

The builder generates a self-contained Python script with:

✅ **Embedded workflow spec** - No external workflow.json needed
✅ **Embedded tool definitions** - All tool configs inlined
✅ **Ollama client** - Direct API calls to Ollama
✅ **Input/output handling** - JSON in, JSON out
✅ **Error handling** - Proper error propagation
✅ **Logging** - Execution progress to stderr

Example runner structure:
```python
#!/usr/bin/env python3
# Standalone runner for: simple_summarizer

import json, requests, sys

class WorkflowRunner:
    def __init__(self):
        # Embedded workflow (no external files!)
        self.workflow = {...}
        self.ollama_endpoint = "http://host.docker.internal:11434"

    def run(self, inputs):
        # Execute workflow steps
        ...
        return outputs

if __name__ == "__main__":
    runner = WorkflowRunner()
    outputs = runner.run(json.loads(sys.argv[1]))
    print(json.dumps(outputs))
```

### 3. Binary Compilation with Nuitka

The Python runner is compiled to a **single binary executable**:

**Before:**
```
runner.py           5 KB
+ Python runtime    ~30 MB
+ Dependencies      ~10 MB
= Total: ~40 MB
```

**After (Nuitka):**
```
workflow (binary)   ~8 MB
= Total: ~8 MB
```

Benefits:
- ✅ **Faster startup** - No Python interpreter initialization
- ✅ **Smaller size** - Only includes used code
- ✅ **Better performance** - Compiled C code
- ✅ **Portability** - Single binary, no dependencies

### 4. Multi-Stage Docker Build

The Dockerfile uses multi-stage builds for minimal final size:

```dockerfile
# Stage 1: Build (large)
FROM python:3.11-slim AS builder
RUN pip install nuitka
COPY runner.py /app/
RUN nuitka --standalone --onefile runner.py

# Stage 2: Runtime (tiny!)
FROM alpine:latest
RUN apk add --no-cache libstdc++ libgcc
COPY --from=builder /app/workflow /usr/local/bin/
ENV OLLAMA_ENDPOINT=http://host.docker.internal:11434
ENTRYPOINT ["/usr/local/bin/workflow"]
```

**Final image layers:**
- Alpine base: ~5 MB
- Runtime libs: ~2 MB
- Binary: ~8 MB
- **Total: ~15 MB** 🎉

### 5. Ollama Access via `host.docker.internal`

Docker containers can't normally access `localhost` on the host.

**Solution:** Use `host.docker.internal` special DNS name.

When running the container:
```bash
docker run --rm --add-host host.docker.internal:host-gateway workflow-name
```

This maps `host.docker.internal` → host's IP, allowing the container to call:
```
http://host.docker.internal:11434/api/generate
```

Which reaches Ollama on the host's `localhost:11434`.

## 📝 Creating Portable Workflows

For Docker execution, workflows must be **portable** (self-contained).

### Required Fields

```json
{
  "workflow_id": "my_workflow",
  "portable": true,  // ← REQUIRED!

  "steps": [...],

  "tools": {  // ← Embed tool definitions
    "my_llm_tool": {
      "type": "llm",
      "model": "llama3",
      "endpoint": "http://localhost:11434",
      ...
    }
  }
}
```

### Making Existing Workflows Portable

Use the workflow exporter:

```bash
python export_workflow.py my_workflow.json --output ./portable/ --platform edge
```

This converts a lightweight workflow (with external tool references) to a portable workflow (with embedded tools).

## 🎯 Use Cases

### 1. Production Microservices

Deploy workflows as containerized microservices:

```bash
# Build production image
python docker_workflow.py build workflows/content_generator.json -t prod/content:v1

# Deploy to k8s
kubectl run content-generator --image=prod/content:v1 \
  --restart=Never \
  --env="INPUT={\"topic\":\"AI\"}"
```

### 2. Batch Processing

Process thousands of items:

```bash
#!/bin/bash
# Process batch of articles

for article in articles/*.txt; do
  docker run --rm --add-host host.docker.internal:host-gateway \
    workflow-summarizer:latest \
    "{\"text\": \"$(cat $article)\", \"max_length\": 100}" \
    > "summaries/$(basename $article .txt).json"
done
```

### 3. CI/CD Integration

Run workflows in CI pipelines:

```yaml
# .github/workflows/content-check.yml
steps:
  - name: Check Content Quality
    run: |
      python docker_workflow.py run workflows/quality_checker.json \
        --input-file article.json
```

### 4. Edge Deployment

Deploy to edge devices with minimal resources:

```bash
# Build for ARM64
docker buildx build --platform linux/arm64 -t workflow-edge:latest .

# Deploy to Raspberry Pi
docker save workflow-edge | ssh pi@edge 'docker load'
ssh pi@edge 'docker run workflow-edge ...'
```

### 5. Distributed Workflow Execution

Scale across cluster nodes:

```bash
# Run same workflow on 100 nodes
for node in node{1..100}; do
  ssh $node "docker run workflow-process:latest '{\"shard\": $node}'" &
done
wait
```

## 🔒 Security Considerations

### Network Access
- Containers are isolated by default
- Only have access to Ollama via explicit `--add-host` flag
- No access to host filesystem unless mounted

### Best Practices
1. **Don't embed secrets** in workflow.json (use env vars)
2. **Use read-only containers** (`--read-only` flag)
3. **Limit resources** (`--memory=512m --cpus=1`)
4. **Use specific tags** (not `latest` in production)

Example secure run:
```bash
docker run --rm --read-only --memory=512m --cpus=1 \
  --add-host host.docker.internal:host-gateway \
  --env OLLAMA_API_KEY=${OLLAMA_KEY} \
  workflow-name:v1.2.3 \
  '{"input": "value"}'
```

## 🐛 Troubleshooting

### Issue: "Connection refused to Ollama"

**Cause:** Container can't reach Ollama on host.

**Solution:** Ensure:
1. Ollama is running: `ollama list`
2. Using `--add-host` flag in docker run
3. Firewall allows connections from Docker network

Test connection:
```bash
docker run --rm --add-host host.docker.internal:host-gateway alpine \
  wget -O- http://host.docker.internal:11434/api/tags
```

### Issue: "Model not found"

**Cause:** Ollama model not pulled.

**Solution:**
```bash
# Check workflow's required models
docker inspect workflow-name | grep workflow.models

# Pull missing models
ollama pull llama3
```

### Issue: "Build failed - Nuitka errors"

**Cause:** Nuitka compilation issues.

**Workaround:** Use PyInstaller instead (modify Dockerfile):
```dockerfile
RUN pip install pyinstaller
RUN pyinstaller --onefile runner.py
```

### Issue: "Image too large"

**Cause:** Including unnecessary dependencies.

**Solution:**
1. Ensure workflow is portable (embedded tools only)
2. Check pip packages list - remove unused packages
3. Use Alpine base (not Ubuntu/Debian)

Check image size:
```bash
docker images workflow-name
```

## 📊 Performance

### Build Times
- First build: ~5-10 minutes (Nuitka compilation)
- Cached builds: ~30 seconds
- Size: ~10-20 MB final image

### Runtime Performance
- Container startup: ~100ms
- Workflow execution: Same as native Python
- Ollama calls: Network latency only (local = fast)

### Resource Usage
- Memory: ~50-100 MB per container
- CPU: 1 core recommended
- Disk: ~20 MB per image

## 🔮 Future Enhancements

Planned features:
- [ ] **WASM compilation** - Run in browsers
- [ ] **GPU support** - For local LLM inference
- [ ] **Workflow chaining** - Link multiple containers
- [ ] **Streaming output** - Real-time results
- [ ] **ARM builds** - Native Raspberry Pi support
- [ ] **PyInstaller option** - Alternative to Nuitka
- [ ] **Webhook triggers** - HTTP API for workflows

## 📚 Examples

See `code_evolver/workflows/` for example workflows:

- **simple_summarizer.json** - Text summarization with Ollama
- **article_writer.json** - Multi-step article generation
- **code_reviewer.json** - Automated code review

Build and try them:
```bash
python docker_workflow.py build workflows/simple_summarizer.json
python docker_workflow.py run workflows/simple_summarizer.json \
  '{"text": "Your text here", "max_length": 50}'
```

## 🤝 Contributing

To add new features to Docker workflow execution:

1. **Modify builder:** `src/docker_workflow_builder.py`
2. **Update CLI:** `docker_workflow.py`
3. **Add tests:** Create test workflows
4. **Update docs:** This file

## 📄 License

Same as code_evolver main project.

---

**Questions?** Check the main [README](README.md) or [ARCHITECTURE](ARCHITECTURE.md) docs.
