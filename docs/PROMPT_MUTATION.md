# Prompt Mutation System

## Overview

The Prompt Mutation System treats LLM tools like code tools, enabling mutation and specialization for specific use cases instead of forcing overly general prompts to fit all scenarios.

**Core Philosophy:**
- Prefer mutating prompts over using overly general prompts
- Ask overseer whether mutation is beneficial (efficiency, necessity)
- Track lineage and enable rollback
- Robust versioning and metadata tracking

## Why Mutation?

### Problem: Overly General Prompts

When you have a general-purpose tool (e.g., "code_reviewer"), you face a dilemma:

1. **Keep it general** - Works for many cases but suboptimal for specific needs
2. **Make it specific** - Better results but loses generality
3. **Add parameters** - Complexity grows, harder to use

### Solution: Mutation

Instead of choosing, **mutate** the tool when needed:

- Start with general tool
- When specific use case emerges, create specialized mutation
- Track performance of both
- Use the right tool for each job

## Key Components

### 1. PromptMutator (`src/prompt_mutator.py`)

Core mutation engine that:
- Orchestrates all mutations
- Integrates with overseer for intelligent decisions
- Manages versioning and lineage
- Tracks performance metrics

### 2. Mutation Strategies

Different ways to mutate prompts:

| Strategy | Purpose | When to Use |
|----------|---------|-------------|
| **SPECIALIZE** | Make prompt more specific for a use case | Need domain-specific language/expertise |
| **OPTIMIZE** | Improve clarity and effectiveness | Prompt is ambiguous or inconsistent |
| **CONSTRAIN** | Add requirements/constraints | Need specific output format or rules |
| **SIMPLIFY** | Remove unnecessary complexity | Prompt has too many parameters |
| **EXPAND** | Add more detail/context | Need more consistent output |
| **REFRAME** | Change approach while keeping intent | Current approach isn't working |

### 3. Overseer Integration

The overseer makes intelligent decisions about when to mutate based on:

- **Efficiency**: Is specialized version more efficient?
- **Necessity**: Is use case different enough to warrant specialization?
- **Cost/Benefit**: Worth the maintenance overhead?
- **Frequency**: How often will this specialized version be used?

### 4. Mutation Metadata & Versioning

Every mutation tracks:
- Parent tool ID and original prompts
- Mutation strategy used
- Specific use case
- Performance metrics (quality, speed)
- Creation timestamp
- Lineage for rollback

## Usage

### CLI Tool

```bash
# Interactive mode
python code_evolver/tools/executable/mutate_tool.py

# Auto-mutate (with overseer consultation)
python code_evolver/tools/executable/mutate_tool.py \
  --tool code_reviewer \
  --use-case "Security audit of authentication code" \
  --auto

# Force mutation without overseer
python code_evolver/tools/executable/mutate_tool.py \
  --tool code_reviewer \
  --use-case "Security audit" \
  --strategy specialize \
  --constraints "Check OWASP Top 10,Include exploit scenarios"

# List mutations for a tool
python code_evolver/tools/executable/mutate_tool.py \
  --tool code_reviewer \
  --list

# Get best mutation for use case
python code_evolver/tools/executable/mutate_tool.py \
  --tool code_reviewer \
  --best-for "security review"

# Export mutation as new tool YAML
python code_evolver/tools/executable/mutate_tool.py \
  --mutation-id code_reviewer_specialize_security_20250118_120000 \
  --export code_evolver/tools/llm/security_code_reviewer.yaml
```

### Programmatic API

```python
from src.prompt_mutator import PromptMutator, MutationStrategy
from src import OllamaClient, ConfigManager
from src.overseer_llm import OverseerLlm

# Setup
config = ConfigManager("config.yaml")
client = OllamaClient(config.ollama_url, config_manager=config)
overseer = OverseerLlm(client=client)

mutator = PromptMutator(
    ollama_client=client,
    overseer_llm=overseer
)

# Step 1: Ask overseer if mutation is beneficial
decision = mutator.should_mutate(
    tool_id="code_reviewer",
    use_case="Security audit of authentication code",
    context={
        "frequency": "daily",
        "current_quality": 0.6,
        "target_quality": 0.95
    }
)

print(f"Should mutate: {decision.should_mutate}")
print(f"Reasoning: {decision.reasoning}")

# Step 2: Mutate if recommended
if decision.should_mutate:
    mutated = mutator.mutate_prompt(
        tool_id="code_reviewer",
        system_prompt="You are a code reviewer.",
        prompt_template="Review this code:\n{code}",
        use_case="Security audit of authentication code",
        strategy=decision.recommended_strategy
    )

    print(f"Mutation ID: {mutated.mutation_id}")
    print(f"New system prompt: {mutated.mutated_system_prompt}")

# Or use auto_mutate for one-step process
mutated = mutator.auto_mutate(
    tool_id="code_reviewer",
    system_prompt="You are a code reviewer.",
    prompt_template="Review this code:\n{code}",
    use_case="Security audit of authentication code",
    context={"frequency": "daily"}
)
```

### Using Mutated Prompts

```python
# Get best mutation for a use case
best = mutator.get_best_mutation_for_use_case(
    tool_id="code_reviewer",
    use_case="security audit",
    min_quality=0.9
)

if best:
    # Use the mutated prompts
    response = client.generate(
        model="llama3",
        prompt=best.mutated_prompt_template.format(code=my_code),
        system=best.mutated_system_prompt
    )

    # Record performance
    best.record_performance(
        quality=0.95,
        speed_ms=1200,
        success=True,
        context="Authentication review"
    )
```

## Examples

See `code_evolver/examples/prompt_mutation_example.py` for comprehensive examples:

1. **Overseer Decision** - Ask overseer if mutation is beneficial
2. **Auto-Mutation** - Automatic mutation with overseer consultation
3. **Force Mutation** - Force mutation with specific strategy
4. **Performance Tracking** - Track and optimize based on metrics
5. **Export Mutation** - Export as new tool YAML

Run examples:
```bash
python code_evolver/examples/prompt_mutation_example.py
```

## Workflow

### 1. Identify Need for Specialization

You notice that:
- General tool doesn't perform well for specific use case
- You're repeatedly using same tool with similar constraints
- Use case is frequent and well-defined

### 2. Consult Overseer

Ask overseer if mutation is beneficial:

```python
decision = mutator.should_mutate(
    tool_id="general_tool",
    use_case="Specific use case",
    context={"frequency": "daily", "current_quality": 0.6}
)
```

Overseer evaluates:
- Is specialized version more efficient?
- Is this use case different enough?
- Worth the maintenance overhead?

### 3. Create Mutation

If overseer recommends, create mutation:

```python
mutated = mutator.mutate_prompt(
    tool_id="general_tool",
    system_prompt="...",
    prompt_template="...",
    use_case="Specific use case",
    strategy=MutationStrategy.SPECIALIZE
)
```

### 4. Track Performance

Use the mutation and track metrics:

```python
# Use mutation
result = use_mutated_prompt(mutated)

# Record performance
mutated.record_performance(
    quality=calculate_quality(result),
    speed_ms=measure_speed(),
    success=True
)
```

### 5. Export or Rollback

If mutation performs well, export as permanent tool:

```bash
python mutate_tool.py \
  --mutation-id xxx \
  --export code_evolver/tools/llm/specialized_tool.yaml
```

If it underperforms, you still have the original tool.

## Integration with Existing Tools

### Tools Manager

The mutation system integrates seamlessly with ToolsManager:

```python
from src import ToolsManager

tools = ToolsManager(...)

# Get original tool
original = tools.get_tool("code_reviewer")

# Create mutation
mutated = mutator.mutate_prompt(...)

# Use either based on context
if use_case_is_specific:
    prompt = mutated.mutated_prompt_template
else:
    prompt = original.metadata['prompt_template']
```

### RAG Memory

Mutations are automatically stored in RAG memory for:
- Semantic search
- Performance tracking
- Usage analytics
- Learning from patterns

### Versioning

Mutations follow semantic versioning:
- **Major** - Breaking changes (incompatible with original)
- **Minor** - Backward compatible improvements
- **Patch** - Small fixes or optimizations

## Best Practices

### ✅ Do

1. **Always consult overseer first** - Don't mutate without consultation
2. **Track performance metrics** - Record quality and speed
3. **Export successful mutations** - Make them permanent tools
4. **Document use cases clearly** - Enables reuse and discovery
5. **Clean up unused mutations** - Prevent proliferation
6. **Use semantic versioning** - Track compatibility

### ❌ Don't

1. **Force mutate without overseer** - Unless you have good reason
2. **Mutate for one-off use cases** - Not worth the overhead
3. **Ignore performance metrics** - Can't optimize without data
4. **Create too many similar mutations** - Consolidate instead
5. **Skip lineage tracking** - Need rollback capability
6. **Over-specialize** - Keep some generality

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Prompt Mutator                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐      ┌──────────────┐                │
│  │  Overseer   │◄────►│   Mutation   │                │
│  │ Integration │      │  Strategies  │                │
│  └─────────────┘      └──────────────┘                │
│         │                     │                         │
│         ▼                     ▼                         │
│  ┌─────────────────────────────────┐                   │
│  │      Mutation Engine            │                   │
│  ├─────────────────────────────────┤                   │
│  │  • Decision Making              │                   │
│  │  • Prompt Transformation        │                   │
│  │  • Lineage Tracking             │                   │
│  │  • Performance Monitoring       │                   │
│  └─────────────────────────────────┘                   │
│         │                     │                         │
│         ▼                     ▼                         │
│  ┌─────────────┐      ┌──────────────┐                │
│  │ RAG Memory  │      │   Storage    │                │
│  │  (Semantic) │      │   (Disk)     │                │
│  └─────────────┘      └──────────────┘                │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │    Tools Manager      │
              │  (Seamless Usage)     │
              └───────────────────────┘
```

## Performance Considerations

### Storage

Mutations are stored:
1. **In memory** - Active mutations cache
2. **On disk** - JSON files in `mutations/` directory
3. **In RAG** - Semantic search and analytics

### Efficiency

- Overseer consultation: ~500ms
- Mutation creation: ~2-5 seconds
- Using mutation: Same as original tool
- Finding best mutation: ~100ms (cached)

### Scalability

- Mutations are lazy-loaded
- RAG enables efficient search across thousands of mutations
- Performance metrics guide optimization

## Troubleshooting

### Mutation quality is poor

1. Check mutation strategy - try different strategy
2. Add more constraints - be more specific
3. Provide more context - help the LLM understand
4. Review parent prompt - may need better base

### Overseer always says "don't mutate"

1. Increase frequency in context - show it's used often
2. Improve quality gap - show current quality is insufficient
3. Provide better use case description - be more specific
4. Override with force mode - if you know better

### Too many mutations

1. Review and consolidate - merge similar mutations
2. Export best as permanent tools - reduce mutation count
3. Clean up low-performance mutations - keep only winners
4. Be more selective - don't mutate for every use case

## Future Enhancements

1. **Automatic mutation based on usage patterns** - Learn when to mutate
2. **A/B testing framework** - Compare mutation vs original
3. **Mutation composition** - Combine multiple mutations
4. **Smart consolidation** - Automatically merge similar mutations
5. **Performance-based evolution** - Evolve mutations over time

## Related Components

- **Prompt Genericiser** (`tools/llm/prompt_genericiser.yaml`) - Opposite direction
- **Overseer LLM** (`src/overseer_llm.py`) - Strategic planning
- **Tools Manager** (`src/tools_manager.py`) - Tool registry
- **RAG Memory** (`src/rag_memory.py`) - Storage and search

## Summary

The Prompt Mutation System enables **intelligent specialization** of LLM tools:

- **Ask** overseer if mutation is beneficial
- **Mutate** prompts for specific use cases
- **Track** performance and lineage
- **Optimize** based on metrics
- **Export** successful mutations as permanent tools

This treats LLM tools like code - enabling evolution, specialization, and optimization while maintaining robustness through versioning and rollback capabilities.
