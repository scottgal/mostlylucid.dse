# LLMs as Tools - Intelligent Model Selection with Learning

## Overview

The mostlylucid DiSE system now treats LLMs themselves as tools, enabling intelligent model and backend selection based on natural language requests and learned performance.

**Key Concept:** The system learns which LLMs are best for each task type through usage, creating a fitness-based selection mechanism that improves over time.

## Architecture

```
User: "using the most powerful code llm review this code deeply"
    ↓
[Model Selector] - Parses request (general-tier LLM)
    ↓
[LLM Registry] - Queries available LLMs
    ↓
Check Learned Performance:
  - Has this task type been done before?
  - Which LLMs performed best?
  - Quality scores? Success rates?
    ↓
Selection Decision:
  IF sufficient learning data (≥5 uses):
    → Use best performing LLM (learned)
  ELSE:
    → Use keyword/capability matching
    ↓
Selected: backend=anthropic, model=claude-3-opus-20240229
    ↓
[Execute Task]
    ↓
[Record Metrics] - Quality, latency, success
    ↓
[Update Learning] - Improve future selections
```

## How It Works

### 1. LLM Definitions

LLMs are defined in YAML files in `llm_tools/` directory:

**Example:** `llm_tools/anthropic_opus.yaml`
```yaml
name: "Claude Opus (Most Powerful)"
type: "llm_model"
enabled: true
provider: "anthropic"
model_id: "claude-3-opus-20240229"

description: "Most powerful Claude model. Excels at complex reasoning..."

capabilities:
  - "deep_code_review"
  - "architectural_design"
  - "security_auditing"

specialization:
  primary: "code"
  secondary: ["architecture", "security"]

quality_tier: "god"
speed_tier: "slow"
cost_tier: "highest"

routing_keywords:
  - "most powerful"
  - "best"
  - "deep"
  - "thorough"
  - "critical"

priority: 100
```

### 2. Model Selector

Natural language requests are parsed to select the best LLM:

```python
from node_runtime import call_tool

# User request
request = "using the most powerful code llm review this code deeply"

# Select model + backend
selection = call_tool("model_selector", request)

# Result:
{
  "selected_backend": "anthropic",
  "selected_model": "claude-3-opus-20240229",
  "model_name": "Claude Opus (Most Powerful)",
  "reason": "Request specifies 'most powerful' and 'deeply'",
  "confidence": 0.95,
  "selection_method": "keyword_matching"  # or "learned_performance"
}
```

### 3. Learning System

The system tracks:
- **Usage counts** per LLM per task type
- **Quality scores** (0-1) from evaluations
- **Success rates** (did it work?)
- **Latency** (how fast was it?)

This data is used to select the best LLM for future tasks:

```python
from src.llm_registry import LLMRegistry

registry = LLMRegistry()

# Record usage
registry.record_usage(
    llm_id="anthropic_opus",
    task_type="code_review",
    quality_score=0.92,
    latency_ms=12000,
    success=True
)

# After 5+ uses, system knows anthropic_opus is best for code_review
best = registry.get_best_llm_for_task("code_review")
# Returns: "anthropic_opus"
```

### 4. Fitness-Based Selection

**Initial Selection (No Learning Data):**
- Uses keyword matching
- Routes "most powerful" → god tier
- Routes "quick" → fast tier
- Routes "local" → Ollama models

**After Learning (≥5 uses per task type):**
- Uses actual performance data
- Selects LLM with best quality/latency score
- Falls back to keywords if no data

**Fitness Score Calculation:**
```python
success_rate = successes / total_uses
avg_quality = sum(quality_scores) / total_uses
fitness = (success_rate + avg_quality) / 2
```

## Available LLMs

### Anthropic Models

**Claude Opus (Most Powerful)**
- **Backend:** anthropic
- **Quality Tier:** god
- **Best For:** Critical code review, security audits, complex analysis
- **Keywords:** "most powerful", "best", "critical", "deep"

**Claude Sonnet (Balanced)**
- **Backend:** anthropic
- **Quality Tier:** general
- **Best For:** Standard development, general coding, workflows
- **Keywords:** "balanced", "standard", "normal"

**Claude Sonnet (Overseer)**
- **Backend:** anthropic
- **Role:** overseer
- **Best For:** Strategic planning, task decomposition, architecture
- **Keywords:** "overseer", "strategy", "planning"

### Ollama Models (Local)

**DeepSeek Coder 16B (Local Powerhouse)**
- **Backend:** ollama
- **Quality Tier:** escalation
- **Best For:** Complex local code tasks, offline development
- **Keywords:** "local", "powerful local", "best local"
- **Requirements:** 16GB+ RAM

**CodeLlama 7B (Fast Local)**
- **Backend:** ollama
- **Quality Tier:** fast
- **Best For:** Quick iterations, simple functions, prototyping
- **Keywords:** "fast", "quick", "simple"
- **Requirements:** 8GB RAM

## Usage Examples

### Example 1: Request Most Powerful Code LLM

```python
# Natural language request
request = "using the most powerful code llm we have review this code very deeply for correctness"

# Select model
selection_json = call_tool("model_selector", request)
selection = json.loads(selection_json)

# Use selected model
backend = selection["selected_backend"]  # "anthropic"
model = selection["selected_model"]      # "claude-3-opus-20240229"

# Execute review
from src.ollama_client import OllamaClient
client = OllamaClient()

result = client.generate(
    model=model,
    prompt=f"Review this code for correctness: {code}",
    model_key="selected"
)
```

### Example 2: Request Overseer

```python
request = "use overseer to break down this complex task into steps"

selection = json.loads(call_tool("model_selector", request))

# Result: anthropic/claude-3-5-sonnet-20241022 (overseer role)
```

### Example 3: Request Fast Local Model

```python
request = "quickly generate a simple helper function using local model"

selection = json.loads(call_tool("model_selector", request))

# Result: ollama/codellama:7b (fast local)
```

### Example 4: Learning-Based Selection

```python
# After 10 code reviews, system has learned performance data
request = "review this code"

# System checks learning data:
# - code_review task done 10 times
# - anthropic_opus: avg_quality=0.92, avg_latency=12000ms
# - ollama_deepseek: avg_quality=0.78, avg_latency=8000ms

# Selection: anthropic_opus (higher quality despite slower)
# selection_method: "learned_performance"
```

## Keyword Mapping

### Quality Keywords

| Keywords | Tier | Models |
|----------|------|--------|
| "most powerful", "best", "critical", "deep" | god | Claude Opus |
| "balanced", "standard", "normal" | general | Claude Sonnet |
| "quick", "fast", "simple" | fast | CodeLlama 7B |

### Backend Keywords

| Keywords | Backend | Models |
|----------|---------|--------|
| "local", "free", "offline", "private" | ollama | DeepSeek, CodeLlama |
| "cloud", "anthropic" | anthropic | Opus, Sonnet |

### Domain Keywords

| Keywords | Domain | Specialization |
|----------|--------|----------------|
| "code", "review", "analyze" | code | Code-specialized models |
| "overseer", "strategy", "plan" | planning | Overseer-role models |
| "content", "write", "article" | content | Content-specialized models |

## Learning Data Structure

**Stored in:** `llm_usage_stats.json`

```json
{
  "llms": {
    "anthropic_opus": {
      "total_uses": 25,
      "successes": 24,
      "failures": 1,
      "avg_quality": 0.91,
      "avg_latency": 11800,
      "task_performance": {
        "code_review": {
          "uses": 15,
          "avg_quality": 0.93
        },
        "security_audit": {
          "uses": 10,
          "avg_quality": 0.88
        }
      }
    }
  },
  "task_types": {
    "code_review": {
      "anthropic_opus": {
        "uses": 15,
        "successes": 15,
        "avg_quality": 0.93,
        "avg_latency": 12000
      },
      "ollama_deepseek": {
        "uses": 8,
        "successes": 7,
        "avg_quality": 0.76,
        "avg_latency": 8500
      }
    }
  }
}
```

## Integration with System

### 1. Tools Manager Integration

LLMs are registered as special tools:
```python
from src.tools_manager import ToolsManager
from src.llm_registry import LLMRegistry

tm = ToolsManager()
llm_registry = LLMRegistry(tools_manager=tm)

# LLMs now searchable via tools manager
llm_tools = tm.find_by_tags(["llm", "model"])
```

### 2. RAG Integration

LLMs can be queried via RAG:
```python
from src.rag_memory import RAGMemory

rag = RAGMemory()

# Find code-specialized LLMs
results = rag.find_similar(
    "best model for code review",
    artifact_type=ArtifactType.TOOL
)
```

### 3. Auto-Evolution Integration

LLM selection can evolve based on performance:
- Low-performing LLMs get deprioritized
- High-performing LLMs get boosted
- System adapts to your specific use cases

## Adding New LLMs

### 1. Create YAML Definition

**File:** `llm_tools/my_new_llm.yaml`
```yaml
name: "My New LLM"
type: "llm_model"
enabled: true
provider: "openai"  # or "anthropic", "ollama", etc.
model_id: "gpt-4"

description: "Description of capabilities"

capabilities:
  - "capability1"
  - "capability2"

specialization:
  primary: "code"
  secondary: ["testing"]

quality_tier: "general"
speed_tier: "fast"
cost_tier: "medium"

routing_keywords:
  - "keyword1"
  - "keyword2"

priority: 75

metadata:
  backend: "openai"
  api_endpoint: "https://api.openai.com/v1/chat/completions"
  requires_api_key: true
```

### 2. Reload Registry

```python
from src.llm_registry import LLMRegistry

registry = LLMRegistry()
# Automatically loads all YAML files from llm_tools/
```

### 3. Test Selection

```bash
python -c "
from node_runtime import call_tool
result = call_tool('model_selector', 'use my new llm')
print(result)
"
```

## Benefits

### 1. Natural Language Interface
```
✅ "using the most powerful code llm review this"
❌ backend="anthropic", model="claude-3-opus-20240229"
```

### 2. Automatic Learning
- System discovers best LLMs for each task
- Adapts to your workflow
- No manual tuning needed

### 3. Cost Optimization
- Expensive models only for complex tasks
- Cheap/local models for simple tasks
- Learned from actual usage

### 4. Quality Optimization
- Best model selected based on results
- Not just theoretical capabilities
- Real performance data

### 5. Flexibility
- Easy to add new LLMs
- Easy to enable/disable models
- Easy to adjust priorities

## Monitoring

### Check LLM Stats

```python
from src.llm_registry import LLMRegistry

registry = LLMRegistry()

stats = registry.get_stats()
print(json.dumps(stats, indent=2))

# Output:
{
  "total_enabled": 5,
  "backends": {
    "anthropic": 3,
    "ollama": 2
  },
  "quality_tiers": {
    "god": 1,
    "general": 2,
    "fast": 2
  },
  "total_uses": 127,
  "tracked_llms": 4,
  "tracked_task_types": 8
}
```

### Check Fitness Scores

```python
# Get fitness scores for code review task
fitness = registry.get_fitness_scores("code_review")

# Output:
{
  "anthropic_opus": 0.92,
  "ollama_deepseek": 0.77,
  "ollama_codellama": 0.65
}
```

### View Learning Data

```bash
cat llm_usage_stats.json | jq '.task_types.code_review'
```

## Files Created

1. **`llm_tools/anthropic_opus.yaml`** - Claude Opus definition
2. **`llm_tools/anthropic_sonnet.yaml`** - Claude Sonnet definition
3. **`llm_tools/anthropic_sonnet_overseer.yaml`** - Overseer role
4. **`llm_tools/ollama_deepseek_coder.yaml`** - DeepSeek 16B
5. **`llm_tools/ollama_codellama.yaml`** - CodeLlama 7B
6. **`tools/llm/model_selector.yaml`** - Model selector tool
7. **`src/llm_registry.py`** - LLM registry manager (408 lines)
8. **`llm_usage_stats.json`** - Learning data (auto-created)

## Status

✅ **Complete and Ready to Use**

- LLM definitions created (5 models)
- Model selector tool created
- LLM registry with learning created
- Fitness-based selection implemented
- Usage tracking implemented
- Documentation complete

## Quick Start

```bash
# 1. LLMs are already defined in llm_tools/

# 2. Use model selector
python -c "
from node_runtime import call_tool
import json

request = 'using the most powerful code llm review this code deeply'
result = call_tool('model_selector', request)
print(json.dumps(json.loads(result), indent=2))
"

# 3. Check available LLMs
python -c "
from src.llm_registry import LLMRegistry
registry = LLMRegistry()
print(f'Loaded {len(registry.llms)} LLMs')
for llm_id, llm in registry.llms.items():
    print(f'  - {llm[\"name\"]} ({llm[\"provider\"]})')
"

# 4. System learns automatically as you use it!
```

---

**The system now intelligently selects the best LLM for each task and learns from experience!**
