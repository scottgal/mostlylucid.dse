# mostlylucid DiSE - System Manual

**For AI Self-Reference and User Questions**

This manual is stored in RAG memory and can be semantically searched by the system
to answer questions about how mostlylucid DiSE works.

---

## System Architecture

### Core Components

1. **RAG Memory** (CRITICAL INFRASTRUCTURE)
   - Stores all artifacts (code, plans, tools, workflows)
   - Provides semantic search capabilities
   - Can use Qdrant (vector DB) or NumPy (local)
   - Location: `rag_memory/` directory
   - **DO NOT DELETE** - System cannot function without RAG

2. **Tools Manager**
   - Manages 194+ tools (LLM-based, executable, workflows)
   - Located in `tools/` directory
   - Indexed in `tools/index.json`
   - **DO NOT DELETE** - Core functionality depends on tools

3. **Node System**
   - Generated code stored as nodes in `nodes/` directory
   - Each node has: main.py, test_main.py, metadata
   - Tracked in registry at `registry/` directory
   - Can be versioned and evolved

4. **Configuration**
   - Main config: `config.yaml`
   - Model registry with role-based assignments
   - Backend configuration (Ollama, Anthropic)
   - **DO NOT DELETE** - System needs config to run

### File Structure (PROTECTED)

```
code_evolver/
├── rag_memory/           # CRITICAL - Artifact storage
│   ├── index.json        # Artifact metadata
│   ├── embeddings.npy    # Vector embeddings
│   └── tags_index.json   # Tag-based index
├── tools/                # CRITICAL - Tool definitions
│   ├── index.json        # Tool registry
│   ├── llm/              # LLM-based tools
│   ├── executable/       # Python executable tools
│   └── workflow/         # Workflow tools
├── nodes/                # Generated code nodes
├── registry/             # Node registry
├── config.yaml           # CRITICAL - System configuration
├── chat_cli.py           # Main CLI interface
└── src/                  # CRITICAL - Core system code
    ├── rag_memory.py
    ├── tools_manager.py
    ├── config_manager.py
    └── ...
```

**PROTECTED DIRECTORIES** (cannot be deleted):
- `rag_memory/` - RAG storage
- `tools/` - Tool definitions
- `src/` - Core system code
- `config.yaml` - Configuration

**SAFE TO MODIFY**:
- `nodes/` - Generated code (can be regenerated)
- `registry/` - Node metadata (can be rebuilt)

---

## How Code Generation Works

### Workflow

1. **User Request** → "Create a function to calculate X"

2. **Triage** (tinyllama)
   - Analyzes task type and complexity
   - Routes to appropriate workflow

3. **Overseer Planning** (codellama/gemma3)
   - Creates strategy for implementation
   - Stored in RAG as PLAN artifact

4. **Code Generation** (codellama/qwen)
   - Generates code based on plan
   - Follows templates and patterns
   - Stored in RAG as FUNCTION artifact

5. **Testing**
   - Runs test_main.py
   - Collects metrics (latency, memory, coverage)

6. **Evaluation** (llama3)
   - Scores code quality
   - Updates artifact quality score in RAG

7. **Storage**
   - Code saved to `nodes/<node_id>/`
   - Metadata stored in registry
   - Artifact indexed in RAG

### Tool Creation

When user says **"Create the tools required to..."**:

1. **Search Existing Tools First**
   ```python
   # System checks:
   - Semantic search in RAG for similar tools
   - Check tools/ directory
   - Find tools that can be reused/adapted
   ```

2. **Recommend Strategy**
   - **Reuse**: Exact match found (>90% similarity)
   - **Adapt**: Close match found (>70% similarity)
   - **Compose**: Multiple tools can be combined
   - **Create**: No suitable tools exist

3. **Prevent Duplicates**
   - Check for existing tool with same purpose
   - Warn user if duplicate detected
   - Suggest using existing tool instead

---

## Tool System

### Tool Types

1. **LLM Tools** (`tools/llm/`)
   - Use language models for tasks
   - Example: code_reviewer, summarizer
   - Defined in YAML with model role

2. **Executable Tools** (`tools/executable/`)
   - Python scripts with stdin/stdout
   - Example: faker_tool, dependency_analyzer
   - Defined in YAML with command/args

3. **Workflow Tools** (`tools/workflow/`)
   - Multi-step workflows
   - Can call other tools
   - Defined as node directories

### How to Use Tools

**From CLI:**
```
CodeEvolver> /manual tool faker_tool
```

**From Code:**
```python
from node_runtime import call_tool

result = call_tool("faker_tool", "Generate 10 users")
```

**Finding Tools:**
```
CodeEvolver> /tools                    # List all tools
CodeEvolver> /tools --search "fake"    # Search tools
```

---

## Commands Reference

### Safety Commands (PROTECTED)

These commands have guardrails to prevent breaking the system:

- `/clear_rag` - Clears RAG memory (REQUIRES CONFIRMATION)
- `/tools --delete` - Delete tool (PROTECTED - only non-core tools)
- `/node --delete` - Delete node (SAFE - can regenerate)

### Safe Commands

- `/help` - Show all commands
- `/tools` - List all tools
- `/manual tool <name>` - Show tool documentation
- `/conversation_start <topic>` - Start conversation mode
- `/conversation_end` - End conversation
- `/status` - System status

### Code Generation Commands

- `<natural language>` - Generate code from description
- `/run <node_id>` - Run generated code
- `/test <node_id>` - Run tests for code

---

## Guardrails (CANNOT BE BYPASSED)

### 1. Critical File Protection

**PROTECTED FILES** (cannot delete or overwrite):
```
config.yaml
rag_memory/index.json
rag_memory/embeddings.npy
rag_memory/tags_index.json
tools/index.json
src/*.py (all core system files)
```

**ACTION IF ATTEMPTED:**
- Display error: "CRITICAL: Cannot delete protected file"
- Explain why file is protected
- Suggest safe alternative
- **DO NOT EXECUTE** the destructive operation

### 2. Tool Deletion Protection

**PROTECTED TOOLS** (cannot delete):
- Core LLM tools (code_generator, code_reviewer, etc.)
- Essential executable tools (conversation_manager, etc.)
- Any tool marked with `protected: true` in metadata

**ACTION IF ATTEMPTED:**
- Display error: "CRITICAL: Cannot delete protected tool"
- List tools that CAN be deleted
- **DO NOT EXECUTE** the deletion

### 3. RAG Memory Protection

**PROTECTED OPERATIONS:**
- Deleting RAG memory directory
- Corrupting index files
- Deleting all artifacts

**SAFE OPERATIONS:**
- Clearing specific artifacts (with confirmation)
- Cleaning up old/unused artifacts
- Optimizing/compacting RAG

### 4. Configuration Protection

**PROTECTED:**
- Deleting config.yaml
- Setting invalid backend values
- Removing critical model definitions

**SAFE:**
- Changing model roles
- Adjusting timeouts
- Adding new models

---

## How to Answer User Questions

### Question: "How does code generation work?"

**Answer:**
1. Search this manual: "code generation workflow"
2. Find relevant section
3. Summarize in user-friendly terms
4. Reference actual code if needed

### Question: "Can I delete the RAG memory?"

**Answer:**
1. Check guardrails section
2. Explain RAG is CRITICAL infrastructure
3. Warn about consequences
4. Suggest safe alternative (clear specific artifacts)
5. **DO NOT** execute if user insists

### Question: "Create tools for X"

**Answer:**
1. Search existing tools first (tool_discovery.py)
2. Show matching tools if found
3. Ask: "Would you like to use/adapt tool Y instead?"
4. Only create if no suitable tool exists

---

## Troubleshooting

### RAG Initialization Failed

**Symptoms:** "CRITICAL ERROR: RAG memory initialization failed"

**Solution:**
1. Check if Qdrant is running (if using Qdrant):
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```
2. Check if RAG files exist and are not corrupted
3. System will retry 3 times with exponential backoff
4. If all retries fail, system will exit (cannot continue without RAG)

### Tool Loading Timeout

**Symptoms:** Background loader times out after 30s

**Solution:**
- This is NON-CRITICAL
- Tools load successfully in background
- System continues normally
- 194 tools take ~30-40s to load (expected)

### Model Not Found

**Symptoms:** "404 Error" from Ollama

**Solution:**
1. Check available models: `ollama list`
2. Pull missing model: `ollama pull <model_name>`
3. Check config.yaml model names match available models

---

## Best Practices

### For Code Generation

1. **Be Specific** - Provide clear, detailed descriptions
2. **Use Examples** - Show input/output examples
3. **Specify Constraints** - Memory limits, performance requirements
4. **Review Generated Code** - Always test before using

### For Tool Creation

1. **Search First** - Always check for existing tools
2. **Compose Before Creating** - Can existing tools be combined?
3. **Document Well** - Clear descriptions for future discovery
4. **Add Tags** - Helps with semantic search

### For System Maintenance

1. **Regular Backups** - Backup RAG memory periodically
2. **Clean Old Artifacts** - Use `/clear_rag` carefully
3. **Monitor Performance** - Check tool usage stats
4. **Update Documentation** - Keep manual current

---

## Emergency Recovery

### RAG Memory Corrupted

```bash
# Backup current state
cp -r rag_memory rag_memory.backup

# Reinitialize RAG
rm rag_memory/index.json
rm rag_memory/embeddings.npy
# System will rebuild on next start
```

### Configuration Broken

```bash
# Restore from git
git checkout config.yaml

# Or use backup
cp config.yaml.backup config.yaml
```

### System Won't Start

1. Check RAG memory exists: `ls rag_memory/`
2. Check config exists: `ls config.yaml`
3. Check Ollama is running: `curl http://localhost:11434`
4. Check Python dependencies: `pip install -r requirements.txt`

---

## Version Information

- **System Version**: 2.0
- **Last Updated**: 2025-11-17
- **Critical Dependencies**:
  - Python 3.9+
  - Ollama (for LLM inference)
  - Qdrant (optional, for vector storage)
  - NumPy, PyYAML, Rich, etc. (see requirements.txt)

---

**This manual is indexed in RAG and can be searched by the system to answer questions about itself.**
