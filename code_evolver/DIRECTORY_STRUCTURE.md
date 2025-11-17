# mostlylucid DiSE Directory Structure

This document explains the purpose of each directory in the mostlylucid DiSE project.

## Source Code Directories

### `src/`
Core source code for the mostlylucid DiSE system.
- Contains all Python modules and classes
- Includes: LLM clients, registry, node runner, evaluators, workflow systems, RAG memory, etc.

### `tests/`
Unit tests and integration tests for the system.
- Test files for each component
- Integration tests for end-to-end workflows

### `prompts/`
Prompt templates for LLM interactions.
- System prompts for different LLM roles
- Template strings for code generation

### `examples/`
Example code and demonstrations.
- Sample workflows
- Tutorial code
- Reference implementations

## Generated Content Directories (Git-Ignored)

These directories contain runtime-generated content and are excluded from version control.

### `nodes/`
**Auto-generated Python code for each node.**
- Each subdirectory is a node (e.g., `nodes/add_10_and_20/`)
- Contains `main.py` (generated code) and `test_main.py` (generated tests)
- Nodes are created during code generation and stored here
- Git-ignored to prevent pollution

### `registry/`
**Metadata and configuration for each node.**
- Each subdirectory corresponds to a node
- Contains `node.json` with metadata (description, tags, scores, lineage)
- Tracks performance metrics and evaluation results
- Git-ignored as it's runtime data

### `rag_memory/`
**RAG (Retrieval-Augmented Generation) memory storage.**
- Stores embeddings for semantic search
- Contains: `embeddings.npy`, `index.json`, `tags_index.json`
- Used for finding similar past solutions
- Git-ignored as it's a learned database

### `output/`
**User-generated content saved by workflows.**
- Stories, articles, specifications, documentation
- Created by the `file_saver` tool
- Safe directory for workflow outputs
- Git-ignored to keep generated content separate

### `shared_context/`
**Shared state between workflow steps.**
- Temporary data passed between nodes
- Context for multi-step workflows
- Git-ignored as it's ephemeral runtime data

### `test_export/`
**Exported standalone workflow applications.**
- Created by `export_workflow.py`
- Contains portable Python apps generated from workflows
- Git-ignored as these are build artifacts

## Configuration Files

### `config.yaml`
Main configuration file for the system.
- Ollama endpoints and model settings
- Tool definitions (LLM tools, OpenAPI tools, executables)
- Workflow mode settings
- RAG memory configuration

### `node_runtime.py`
Runtime support for generated nodes.
- Provides `call_tool()` function
- Used by generated code to invoke LLM tools
- Must be importable by all nodes

## Main Scripts

### `chat_cli.py`
Interactive CLI for code generation.
- Main entry point for users
- Handles generate, run, evaluate commands
- Implements workflow decomposition

### `orchestrator.py`
Legacy orchestrator (being phased out).
- Original orchestration system
- Use `chat_cli.py` instead

### `export_workflow.py`
Exports workflows as standalone Python applications.
- Creates portable workflow runners
- Generates `run_workflow.py`, `requirements.txt`, `README.md`

## Build and Deployment

### `build.py`
Builds standalone executables for distribution.
- Creates platform-specific binaries
- Uses PyInstaller

## Directory Cleanup

To clean all generated content:
```bash
cd code_evolver
rm -rf nodes/ registry/ rag_memory/ output/ shared_context/ test_export/
```

To reset for a fresh start, also run:
```bash
python cleanup_rag.py
```

## Git Ignore Rules

All generated content directories are git-ignored via `.gitignore`:
- `/code_evolver/nodes/`
- `/code_evolver/registry/`
- `/code_evolver/rag_memory/`
- `/code_evolver/output/`
- `/code_evolver/test_export/`
- `/code_evolver/shared_context/`

This keeps the repository clean and prevents pollution from runtime-generated files.
