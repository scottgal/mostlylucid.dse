# Tool Forge - Integration-Optimized, Consensus-Hardened Tool System

## Overview

The Tool Forge is a comprehensive system for generating, validating, optimizing, and serving MCP tools through a RAG-backed, consensus-driven architecture.

## Key Features

- **Multi-LLM Adversarial Hardening**: Tools validated by multiple LLM models
- **Integration Testing as Optimization**: Characterize performance through real workflow execution
- **Lineage Tracking**: Full provenance and evolution history for all tools
- **Trust Weighting**: Automatic quality assessment and consensus scoring
- **Automatic Tool Selection**: Best tool chosen based on constraints and context
- **Provenance & Auditability**: Every execution logged with full context

## Architecture

### Core Components

1. **Forge Registry (RAG-Backed)**
   - Extends existing RAG memory system
   - Stores tool manifests with semantic search
   - Tracks lineage, metrics, and trust levels
   - **Note**: No separate registry database - uses existing RAG infrastructure

2. **Director Shell**
   - Orchestrates intent → tool discovery → execution pipeline
   - Handles fallback tool generation when gaps exist
   - Coordinates validation and metrics collection

3. **Runtime Executor**
   - Executes MCP servers and tools
   - Provides sandboxing and security
   - Logs provenance for auditability

4. **Validation Council**
   - Multi-stage validation pipeline
   - BDD, unit, load, and security tests
   - Multi-LLM consensus review

5. **Consensus Engine**
   - Aggregates metrics from multiple sources
   - Calculates weighted scores
   - Drives automatic tool selection

6. **Integration Optimizer**
   - Tests tool variants in real workflows
   - Characterizes performance
   - Triggers specialization when thresholds met

## Future Vision: Self-Optimizing Forge Mesh

### Distributed Forge Network

The long-term vision is a **self-updating and optimizing mesh of forges**:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Forge A    │◄───►│  Forge B    │◄───►│  Forge C    │
│  (Edge)     │     │  (Cloud)    │     │  (Local)    │
└─────────────┘     └─────────────┘     └─────────────┘
      ▲                   ▲                   ▲
      │                   │                   │
      └───────────────────┴───────────────────┘
              Shared RAG Memory Layer
```

### Key Characteristics

1. **Decentralized Tool Discovery**
   - Each forge can query others for tools
   - Semantic search across mesh
   - Consensus weights propagate

2. **Automatic Specialization Distribution**
   - High-performing variants replicate to other forges
   - Platform-specific optimizations (Pi, Edge, Cloud)
   - Load balancing across forge nodes

3. **Collaborative Validation**
   - Forges share validation results
   - Multi-forge consensus increases trust
   - Distributed security scanning

4. **Self-Healing**
   - Failing tools automatically re-validated
   - Alternative variants promoted
   - Evolution triggered by performance drift

5. **Mesh Optimization**
   - Tool routing based on forge capabilities
   - Cost optimization (route to cheapest capable forge)
   - Latency optimization (route to nearest forge)

### Implementation Roadmap

**Phase 1** (Current): Single-forge with RAG-backed registry
- ✅ Core forge components
- ✅ RAG integration
- ✅ Validation pipeline
- ✅ Consensus engine

**Phase 2**: Cross-forge Communication
- [ ] Forge discovery protocol
- [ ] Tool query federation
- [ ] Consensus score propagation
- [ ] Lineage graph synchronization

**Phase 3**: Mesh Optimization
- [ ] Multi-forge tool routing
- [ ] Load balancing
- [ ] Geographic distribution
- [ ] Fault tolerance

**Phase 4**: Autonomous Evolution
- [ ] Automatic specialization replication
- [ ] Self-healing mechanisms
- [ ] Adaptive mesh topology
- [ ] Economic optimization (cost routing)

## Usage

### CLI Commands

#### Register Tool
```bash
/forge_register my_tool mcp
```

Interactively registers a new tool in the forge.

#### Validate Tool
```bash
/forge_validate my_tool 1.0.0
```

Runs multi-stage validation pipeline.

#### Query Registry
```bash
/forge_query translate_text --latency 500 --risk 0.2
```

Discovers tools matching capability and constraints.

#### Execute Tool
```bash
/forge_execute my_tool --input '{"text": "Hello", "lang": "es"}'
```

Executes tool with provenance tracking.

#### Optimize Workflow
```bash
/forge_optimize translation_pipeline --runs 50
```

Characterizes tool variants and triggers specialization.

#### List Tools
```bash
/forge_list --trust core --type mcp
```

Lists all registered tools with filtering.

## Tool Manifest Format

Tools are defined in YAML manifests following this structure:

```yaml
tool_id: "tool_name"
version: "1.0.0"
name: "Human Readable Name"
type: "mcp"
description: "What this tool does"

origin:
  author: "system|third_party"
  source_model: "claude-3.5-sonnet"
  created_at: "2025-11-18T..."

lineage:
  ancestor_tool_id: "previous_version"
  mutation_reason: "performance improvement"
  commits: [...]

mcp:
  server_name: "server_name"
  command: "npx"
  args: [...]
  env: {...}

capabilities:
  - name: "capability_name"
    description: "What it does"
    parameters: {...}

trust:
  level: "core|third_party|experimental"
  validation_score: 0.0-1.0
  risk_score: 0.0-1.0

metrics:
  latest:
    correctness: 0.98
    latency_ms_p95: 180
    cost_per_call: 0.0003
    failure_rate: 0.005

tags: ["mcp", "translation", ...]
```

## Trust Levels

- **core**: validation_score >= 0.95, fully validated, low risk
- **third_party**: validation_score >= 0.80, contributed tools
- **experimental**: validation_score < 0.80, newly generated tools

## Integration with Existing Systems

### RAG Memory
- Tool manifests stored as artifacts (ArtifactType.TOOL)
- Semantic search for tool discovery
- Lineage tracked in metadata

### Tools Manager
- Forge tools registered in existing tool system
- Compatible with MCP tool adapter
- Version management through existing versioning

### Optimization System
- Integrates with recursive optimizer
- Leverages existing optimization pipeline
- Compatible with offline batch optimizer

## Security & Provenance

### Sandboxing
- Network: restricted/none
- Filesystem: readonly/restricted
- Environment: whitelisted variables

### Provenance Logs
Per-call records include:
- call_id (unique identifier)
- Input/output hashes
- Timestamps
- Metrics
- Sandbox configuration

### Lineage Graph
- DAG of tool evolution
- Ancestor tracking
- Mutation reasons
- Validation outcomes

## Metrics & Consensus

### Dimensions
- **Correctness**: Validation score, test pass rate
- **Latency**: p50, p95, p99 execution time
- **Cost**: Per-call cost, resource usage
- **Safety**: Security findings, risk score
- **Resilience**: Success rate, error handling

### Weight Calculation
```
weight = Σ(dimension_value × dimension_weight)
```

Weights dynamically adjusted based on task constraints:
- Latency-critical tasks → increase latency weight
- Safety-critical tasks → increase safety weight
- Cost-sensitive tasks → increase cost weight

### Temporal Decay
Recent performance favored through exponential decay:
```
decayed_weight = weight × exp(-decay_factor × age_days)
```

## Examples

### Example 1: Simple Translation
```python
# Query for translator
results = registry.query_tools(
    capability="translate_text",
    constraints={
        'latency_ms_p95': 500,
        'risk_score': 0.2
    }
)

# Execute best tool
tool = results['best_tool']
result = runtime.execute(
    tool_id=tool['tool_id'],
    version=tool['version'],
    input_data={
        'text': 'Hello world',
        'target_lang': 'es'
    }
)
```

### Example 2: Workflow Optimization
```python
# Optimize translation pipeline
results = optimizer.optimize_workflow(
    workflow_id='translation_pipeline',
    tasks=[
        {
            'id': 'translate',
            'role': 'translator',
            'candidates': [
                {'tool_id': 'nmt_v1', 'variant_tag': 'fast'},
                {'tool_id': 'nmt_v2', 'variant_tag': 'accurate'}
            ]
        }
    ],
    runs={'count': 50, 'constraints': {'latency_ms_p95': 500}}
)

# Best variant selected based on characterization
best = results['best_variants']['translate']
```

## Testing

Run forge tests:
```bash
pytest code_evolver/forge/tests/
```

## Documentation

- [Architecture](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [CLI Guide](CLI_GUIDE.md)
- [Mesh Vision](MESH_VISION.md)

## Contributing

The forge system is designed to be extensible:
- Add new validation stages
- Implement custom consensus algorithms
- Create specialized optimizers
- Extend tool manifest schema

## License

MIT License - Same as parent project
