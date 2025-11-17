# Adaptive Timeout & Response Time Management

## Overview

mostlylucid DiSE features a **self-adjusting timeout system** that intelligently manages LLM request timeouts and automatically adapts to infrastructure performance. The system learns from actual response times, predicts optimal timeouts using statistical analysis, and provides automatic fallback to smaller/faster models when requests timeout.

## Key Features

### 1. **Model-Specific Timeout Calculation**

The system assigns different base timeouts based on model characteristics:

```python
# From src/ollama_client.py:148-209
MODEL_SPECIFIC_TIMEOUTS = {
    "tinyllama": 30,           # Very fast, tiny model
    "codellama": 120,          # Medium coding model
    "qwen2.5-coder:14b": 600,  # Large model (10 min)
    "deepseek-coder:33b": 900, # Very large model (15 min)
}

SPEED_TIERS = {
    "very-fast": 30,
    "fast": 60,
    "medium": 120,
    "slow": 240,
    "very-slow": 480,
}
```

**Resolution order:**
1. Model-specific timeout (exact match)
2. Speed tier from configuration
3. Config lookup by model name
4. Default timeout (120s)

### 2. **Adaptive Learning from Response Times**

The system tracks performance metrics for each model and learns optimal timeouts over time.

**Location:** `src/tools_manager.py:1963-2074` (`_update_adaptive_timeout()`)

**Tracked Metrics:**
- Last 50 response times (rolling window)
- Success/timeout counts and rates
- Average, median, and **95th percentile** response times
- Recommended timeout = **p95 × 1.2** (95th percentile + 20% safety buffer)

**Storage:**
- Stored in RAG memory with artifact ID: `timeout_stats_{model_name}`
- Persists across sessions for long-term learning
- Automatically updated after every successful request

**Example Metrics:**
```json
{
  "model": "codellama",
  "response_times": [8.45, 12.3, 9.8, 11.2, 7.9, ...],
  "success_count": 48,
  "timeout_count": 2,
  "timeout_rate": 0.04,
  "avg_response_time": 10.12,
  "median_response_time": 9.8,
  "p95_response_time": 15.2,
  "recommended_timeout": 18.24,
  "last_updated": "2025-11-16T10:30:00Z"
}
```

### 3. **Automatic Timeout Fallback**

When a request times out, the system automatically falls back to smaller/faster models in the same capability tier.

**Location:** `src/tools_manager.py:840-928` (`invoke_llm_tool_with_fallback()`)

**Fallback Chain Example:**
```
tier_3 (deepseek-coder-v2:16b, timeout=600s) → timeout
  ↓ Fall back to
tier_2 (codellama:7b, timeout=120s) → timeout
  ↓ Fall back to
tier_1 (qwen2.5-coder:3b, timeout=30s) → timeout
  ↓ Return empty result or error
```

**Configuration:** `code_evolver/model_tiers.yaml`

```yaml
tier_3_coding:
  model: "deepseek-coder-v2:16b"
  backend: "ollama"
  temperature: 0.2
  timeout_fallback: "tier_2_coding"  # Fall back to tier 2 on timeout

tier_2_coding:
  model: "codellama:7b"
  backend: "ollama"
  temperature: 0.3
  timeout_fallback: "tier_1_coding"  # Fall back to tier 1 on timeout

tier_1_coding:
  model: "qwen2.5-coder:3b"
  backend: "ollama"
  temperature: 0.4
  timeout_fallback: null  # No further fallback
```

### 4. **Multi-Backend Support**

All LLM clients use the centralized `calculate_timeout()` method:

- **Ollama:** `src/ollama_client.py:148`
- **OpenAI:** `src/openai_client.py:160`
- **Anthropic:** `src/anthropic_client.py:167`
- **Azure OpenAI:** `src/azure_client.py:200`
- **LM Studio:** `src/lmstudio_client.py:146`
- **Base Client:** `src/llm_client_base.py:290-318`

This ensures consistent timeout behavior across all backends.

## Complete Flow

Here's how the adaptive timeout system works end-to-end:

### Step 1: Calculate Initial Timeout

```python
# When a request is made
timeout = client.calculate_timeout(
    model="codellama",
    speed_tier="fast",
    default=120
)
# Result: 120s (from model-specific timeout)
```

### Step 2: Execute Request

```python
try:
    response = client.generate(
        model="codellama",
        prompt="Write a function to parse JSON",
        timeout=timeout  # 120s
    )
    execution_time = 8.45  # seconds
except TimeoutError:
    # Fall back to tier_1 model
    execution_time = None
```

### Step 3: Update Metrics

```python
# After successful completion
_update_adaptive_timeout(
    model="codellama",
    execution_time=8.45,
    success=True
)

# Stored in RAG:
# - Append 8.45s to response_times list
# - Recalculate p95 = 15.2s
# - Recommend timeout = 18.24s (15.2 × 1.2)
```

### Step 4: Future Requests Use Learned Timeout

```python
# Next request retrieves metrics from RAG
metrics = rag_memory.retrieve("timeout_stats_codellama")
recommended_timeout = metrics.get("recommended_timeout", 120)

# Use the learned timeout (18.24s)
response = client.generate(
    model="codellama",
    prompt="Another task",
    timeout=recommended_timeout
)
```

## Key Innovation: 95th Percentile Algorithm

The **95th percentile + 20% buffer** algorithm provides optimal balance:

### Why 95th Percentile?

- **Handles variability:** Accommodates occasional slow responses without being overly conservative
- **Ignores outliers:** 5% slowest requests don't skew the timeout
- **Infrastructure-aware:** Adapts to your specific hardware/network conditions
- **Model-aware:** Different models have different performance characteristics

### Why 20% Buffer?

- **Safety margin:** Prevents edge cases from timing out
- **Headroom for variation:** Allows for natural performance fluctuations
- **Cost-effective:** Not so large that you waste time waiting unnecessarily

### Example Calculation

Given response times: `[8, 9, 10, 11, 12, 15, 18, 20, 25, 90]` (seconds)

```python
# Sort: [8, 9, 10, 11, 12, 15, 18, 20, 25, 90]
# p95 (95th percentile) = 25s
# Recommended timeout = 25 × 1.2 = 30s

# This means:
# - 95% of requests will complete in < 25s
# - 20% buffer handles variability
# - Outlier (90s) doesn't dominate the timeout
```

## Configuration

### Enable Adaptive Timeouts

```yaml
# config.yaml
llm:
  backend: "ollama"

  # Enable adaptive timeout learning
  adaptive_timeouts:
    enabled: true
    percentile: 95          # Use 95th percentile
    safety_buffer: 1.2      # 20% buffer
    min_samples: 10         # Need 10+ samples before adapting
    max_timeout: 900        # Never exceed 15 minutes

  # Model-specific overrides
  models:
    "deepseek-coder:33b":
      timeout: 900          # Base timeout for large model
      speed_tier: "very-slow"
```

### Configure Timeout Fallback

```yaml
# model_tiers.yaml
tier_3_coding:
  model: "deepseek-coder-v2:16b"
  backend: "ollama"
  timeout_fallback: "tier_2_coding"  # Automatic fallback

tier_2_coding:
  model: "codellama:7b"
  backend: "ollama"
  timeout_fallback: "tier_1_coding"

tier_1_coding:
  model: "qwen2.5-coder:3b"
  backend: "ollama"
  timeout_fallback: null  # No fallback, return error
```

## Testing

Comprehensive test suite: `code_evolver/tests/test_dynamic_timeout.py`

**Test Coverage:**
- Model-specific timeout lookup
- Speed tier resolution
- Fallback chain execution
- Adaptive learning updates
- Edge cases (missing models, no fallback)
- Multi-backend consistency

**Run Tests:**
```bash
cd code_evolver
pytest tests/test_dynamic_timeout.py -v
```

## Performance Benefits

### Auto-Scaling to Infrastructure

The adaptive timeout system automatically adjusts to your infrastructure:

| Infrastructure | Base Timeout | After Learning | Improvement |
|---------------|--------------|----------------|-------------|
| **High-end GPU** | 120s | 45s (learned fast) | 62% faster |
| **Mid-range CPU** | 120s | 180s (learned slow) | Fewer timeouts |
| **Cloud API** | 120s | 15s (API is fast) | 87% faster |

### Reduced Wasted Time

Without adaptive timeouts:
- Fixed timeout: 120s
- Actual response: 10s
- Wasted time on timeout: 110s

With adaptive timeouts:
- Learned timeout: 18s (p95 × 1.2)
- Actual response: 10s
- Wasted time: 8s
- **85% reduction in wasted time**

### Intelligent Fallback

Example workflow with timeout fallback:

```
Request: "Generate complex algorithm"

Attempt 1: tier_3 (deepseek-coder-v2:16b)
  Timeout: 600s
  Status: TIMEOUT after 600s

Attempt 2: tier_2 (codellama:7b) [automatic fallback]
  Timeout: 120s
  Status: SUCCESS in 85s
  Result: ✓ Working algorithm generated

Total time: 685s
Without fallback: Would have failed, required manual retry
```

## Future Enhancements

See [SPECIFICATION_BASED_SELECTION.md](./SPECIFICATION_BASED_SELECTION.md) for upcoming features:

- **Specification-driven selection:** "Respond within 10 seconds"
- **Predictive model selection:** Choose model based on task + time constraint
- **Cost-aware optimization:** Balance timeout, cost, and quality
- **Real-time adjustment:** Adjust timeouts during high-load periods

## Code References

Key implementation files:

- **Timeout calculation:** `src/ollama_client.py:148-209`
- **Adaptive learning:** `src/tools_manager.py:1963-2074`
- **Timeout fallback:** `src/tools_manager.py:840-928`
- **Multi-backend support:** `src/llm_client_base.py:290-318`
- **Configuration:** `code_evolver/model_tiers.yaml`
- **Tests:** `code_evolver/tests/test_dynamic_timeout.py`

## Summary

The adaptive timeout system provides:

1. **Self-learning:** Automatically learns optimal timeouts from real performance data
2. **Intelligent fallback:** Gracefully degrades to smaller models on timeout
3. **Infrastructure-aware:** Adapts to your specific hardware/network conditions
4. **Multi-backend:** Works consistently across Ollama, OpenAI, Anthropic, Azure, and LM Studio
5. **Statistical rigor:** Uses 95th percentile + 20% buffer for optimal balance
6. **Long-term memory:** Persists metrics in RAG for continuous improvement

**Result:** Faster responses, fewer wasted cycles, and automatic recovery from timeouts.
