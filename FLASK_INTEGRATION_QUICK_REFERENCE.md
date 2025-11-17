# Quick Reference: Code Evolver Architecture & Flask Integration

## Essential File Paths (Absolute Paths)

### Core Components
- `/home/user/mostlylucid.dse/code_evolver/src/http_server_tool.py` - Flask HTTP server
- `/home/user/mostlylucid.dse/code_evolver/src/tools_manager.py` - Tool registry (107KB!)
- `/home/user/mostlylucid.dse/code_evolver/src/workflow_spec.py` - Workflow definitions
- `/home/user/mostlylucid.dse/code_evolver/src/workflow_builder.py` - Workflow builder
- `/home/user/mostlylucid.dse/code_evolver/src/config_manager.py` - Configuration
- `/home/user/mostlylucid.dse/code_evolver/src/task_evaluator.py` - Task classification
- `/home/user/mostlylucid.dse/code_evolver/chat_cli.py` - Main CLI entry point

### LLM Integration
- `/home/user/mostlylucid.dse/code_evolver/src/llm_client_factory.py` - LLM client factory
- `/home/user/mostlylucid.dse/code_evolver/src/anthropic_client.py` - Anthropic
- `/home/user/mostlylucid.dse/code_evolver/src/openai_client.py` - OpenAI
- `/home/user/mostlylucid.dse/code_evolver/src/ollama_client.py` - Local Ollama

### RAG & Search
- `/home/user/mostlylucid.dse/code_evolver/src/qdrant_rag_memory.py` - Vector search
- `/home/user/mostlylucid.dse/code_evolver/src/rag_memory.py` - Core RAG

### Tools Registry
- `/home/user/mostlylucid.dse/code_evolver/tools/executable/` - 100+ executable tools
- `/home/user/mostlylucid.dse/code_evolver/tools/llm/` - Prompt-based LLM tools
- `/home/user/mostlylucid.dse/code_evolver/tools/index.json` - Tool index

### Configuration
- `/home/user/mostlylucid.dse/code_evolver/config.yaml` - Main config
- `/home/user/mostlylucid.dse/code_evolver/config.anthropic.yaml` - Anthropic config
- `/home/user/mostlylucid.dse/code_evolver/config.local.yaml` - Local Ollama config
- `/home/user/mostlylucid.dse/code_evolver/model_tiers.yaml` - Model definitions

### Examples
- `/home/user/mostlylucid.dse/code_evolver/examples/http_server_demo.py` - Working HTTP demo!
- `/home/user/mostlylucid.dse/code_evolver/test_http_tools_e2e.py` - E2E tests

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FLASK WEB UI                              │
│  (Your new component - wraps existing system)                    │
└────────────────┬────────────────────────────────────────────────┘
                 │
       ┌─────────┴──────────┐
       │                    │
       ▼                    ▼
┌─────────────────┐  ┌──────────────────┐
│  REST API       │  │  WebSocket       │
│  Endpoints      │  │  Real-time Upd.  │
└────────┬────────┘  └────────┬─────────┘
         │                    │
         └────────┬───────────┘
                  │
    ┌─────────────▼────────────────┐
    │  SERVICE LAYER               │
    │ (New business logic)          │
    │ - WorkflowService             │
    │ - ToolService                 │
    │ - TaskService                 │
    │ - ChatService                 │
    └─────────────┬────────────────┘
                  │
    ┌─────────────▼────────────────────────────────┐
    │     CODE EVOLVER INTEGRATION LAYER            │
    │  (Existing components - fully functional)    │
    ├──────────────────────────────────────────────┤
    │ • ConfigManager (config.yaml)                 │
    │ • ToolsManager (100+ tools)                   │
    │ • WorkflowBuilder & WorkflowSpec              │
    │ • TaskEvaluator (task classification)         │
    │ • HTTPServerTool (Flask base!)                │
    └─────────────┬──────────────────────────────┘
                  │
    ┌─────────────┴──────────────────────┐
    │                                    │
    ▼                                    ▼
┌──────────────────┐            ┌──────────────────┐
│  LLM CLIENTS     │            │  RAG SYSTEM      │
├──────────────────┤            ├──────────────────┤
│ • Anthropic      │            │ • Qdrant (Vector)│
│ • OpenAI         │            │ • SQLite (Meta)  │
│ • Ollama (local) │            │ • File Storage   │
│ • Azure OpenAI   │            └──────────────────┘
└──────────────────┘

    ┌─────────────────────────────────────┐
    │  EXECUTION & OPTIMIZATION LAYER     │
    │ • AutoEvolver (performance monitor) │
    │ • WorkflowDistributor (multi-plat) │
    │ • Registry (artifact storage)       │
    │ • QualityEvaluator (testing)        │
    └─────────────────────────────────────┘
```

## Key Data Structures

### WorkflowSpec
```python
{
    "workflow_id": "unique_id",
    "name": "Workflow Name",
    "version": "1.0.0",
    "inputs": [{"name": "input1", "type": "string"}],
    "outputs": [{"name": "output1", "type": "string"}],
    "steps": [
        {
            "step_id": "step1",
            "step_type": "LLM_CALL",
            "tool_name": "content_generator",
            "input_mapping": {"prompt": "input1"}
        }
    ]
}
```

### Tool Definition
```yaml
name: my_tool
type: executable
description: Tool description
tags: [category1, category2]
inputs:
  param1:
    type: string
    required: true
outputs:
  result:
    type: string
```

## 3 Critical Integration Points

### 1. Configuration
```python
from src.config_manager import ConfigManager
config = ConfigManager('config.yaml')
models = config.get('llm.models')
```

### 2. Tool Registry
```python
from src.tools_manager import ToolsManager
tools_mgr = ToolsManager(config)
tools = tools_mgr.list_tools()
tool = tools_mgr.get_tool('tool_name')
```

### 3. HTTP Server (Already Flask!)
```python
from src.http_server_tool import HTTPServerTool
server = HTTPServerTool(port=8080)
server.add_route('/api/generate', ['POST'], handler_func)
server.start(blocking=False)  # Background thread!
```

## Workflow Execution Process

```
User Request
    ↓
[1] TaskEvaluator.classify() → Task type
    ↓
[2] RAG.search() → Similar tools/patterns
    ↓
[3] OverseerLLM.plan() → Strategy & steps
    ↓
[4] WorkflowBuilder.build() → WorkflowSpec
    ↓
[5] CodeGenLLM.generate() → Python code
    ↓
[6] TestGenerator.generate() → Unit tests
    ↓
[7] Execute & Validate
    ✓ Pass → Save to registry + RAG
    ✗ Fail → Escalate to better LLM (up to 3x)
    ↓
[8] AutoEvolver monitors performance
    → Triggers optimization if drift detected
    ↓
Result → Store in workflow database
```

## Available Tools (100+ in Registry)

**Code Tools**: formatter, linter, optimizer, reviewer, translator
**Testing Tools**: test generator, test runner, coverage analyzer
**Data Tools**: faker, data generator, CSV parser, JSON validator
**Integration Tools**: HTTP client, API parser, webhook handler
**Security Tools**: security scanner (bandit), import fixer
**System Tools**: file ops, config generator, environment checker

## Configuration Files Location

- Main: `/home/user/mostlylucid.dse/code_evolver/config.yaml`
- Cloud: `/home/user/mostlylucid.dse/code_evolver/config.anthropic.yaml`
- Local: `/home/user/mostlylucid.dse/code_evolver/config.local.yaml`
- Models: `/home/user/mostlylucid.dse/code_evolver/model_tiers.yaml`

## Database Locations

- **Registry** (file-based): `/home/user/mostlylucid.dse/registry/`
- **RAG Memory** (Qdrant): `/home/user/mostlylucid.dse/code_evolver/rag_memory/`
- **Workflows**: `/home/user/mostlylucid.dse/code_evolver/workflows/`
- **Logs**: `/home/user/mostlylucid.dse/code_evolver/logs/`

## Next Steps for Flask UI

1. **Phase 1**: Wrap existing HTTPServerTool with Flask UI
   - Add HTML templates and static files
   - Create REST API endpoints using existing infrastructure
   
2. **Phase 2**: Implement service layer
   - WorkflowService (execute workflows)
   - ToolService (discover/manage tools)
   - ChatService (conversation management)

3. **Phase 3**: Add real-time features
   - WebSocket for live updates
   - SSE for task progress
   - Database for persistence

4. **Phase 4**: Advanced features
   - Workflow editor (visual/text)
   - Performance monitoring dashboard
   - Tool management UI
   - Configuration editor

All existing components are production-ready and fully integrated!
