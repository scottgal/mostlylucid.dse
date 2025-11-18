# Optimize Workflow Integration

Run integration optimization to characterize tool variants and trigger specialization.

## Usage
```
/forge_optimize <workflow_id> [options]
```

## Parameters
- `workflow_id`: Workflow to optimize

## Options
- `--runs <n>`: Number of characterization runs (default: 50)
- `--constraints <json>`: Performance constraints
- `--dataset <path>`: Test dataset for characterization
- `--specialization`: Enable automatic specialization triggers

## What This Command Does

1. **Workflow Analysis**:
   - Parse workflow tasks and dependencies
   - Identify tool swap opportunities
   - Load candidate variants for each role

2. **Variant Characterization**:
   - Run each variant multiple times
   - Collect metrics: correctness, latency, cost, failure_rate
   - Calculate p50, p95, p99 latencies
   - Measure success rates

3. **Best Variant Selection**:
   - Score each variant across dimensions
   - Apply constraint-based weighting
   - Select optimal variant per task

4. **Specialization Triggers**:
   - Check trigger conditions
   - Create specialized variants when thresholds met
   - Fork and tag new variants
   - Register in forge registry

5. **Registry Update**:
   - Store optimization results in RAG
   - Update consensus weights
   - Record specialization lineage

## Examples

### Basic Optimization
```bash
/forge_optimize translation_pipeline --runs 50
```

Output:
```
Optimizing workflow: translation_pipeline
Tasks: 3 (summarize, translate_fr, translate_es)

Characterizing task: summarize
  Testing variant: sum_fast_v2 (50 runs)
    ✓ correctness: 0.92, latency_p95: 250ms
  Testing variant: sum_accurate_v5 (50 runs)
    ✓ correctness: 0.98, latency_p95: 480ms
  Testing variant: sum_safe_v3 (50 runs)
    ✓ correctness: 0.95, latency_p95: 320ms

  Best variant: sum_accurate_v5 (score: 0.94)

Characterizing task: translate_fr
  Testing variant: nmt_fast_v1 (50 runs)
    ✓ correctness: 0.89, latency_p95: 180ms
  Testing variant: nmt_accurate_v2 (50 runs)
    ✓ correctness: 0.96, latency_p95: 420ms

  Best variant: nmt_accurate_v2 (score: 0.91)

Checking specialization triggers...
  ✓ Trigger met: correctness >= 0.99 AND latency <= 400
  Creating specialized variant: nmt_prime_v1
  Tags: [prime, accurate_and_fast]

Optimization Results:
  best_variants:
    summarize: sum_accurate_v5
    translate_fr: nmt_accurate_v2 → nmt_prime_v1 (specialized)
    translate_es: nmt_accurate_v2

  specializations: 1 new variant created
  registry: Updated with results
```

### With Constraints
```bash
/forge_optimize data_pipeline --runs 100 --constraints '{"max_latency_ms_p95": 800, "max_risk_score": 0.2}'
```

Output:
```
Optimizing with constraints:
  max_latency_ms_p95: 800
  max_risk_score: 0.2

Filtering variants by constraints...
  Excluded 3 variants (constraint violations)

Testing 7 variants...
  ✓ All variants meet constraints

Best variants selected (constraint-aware):
  ...
```

### With Dataset
```bash
/forge_optimize summarization_workflow --dataset datasets/pdf_benchmark_2025 --runs 100
```

Output:
```
Loading dataset: datasets/pdf_benchmark_2025
  Files: 100 PDFs
  Total size: 250MB

Characterizing with real data...
  variant: pdf_sum_v1
    ✓ 95/100 successful (95%)
    ✓ avg_latency: 650ms
  variant: pdf_sum_v2
    ✓ 98/100 successful (98%)
    ✓ avg_latency: 820ms

Best variant: pdf_sum_v2 (higher reliability)
```

## Specialization Triggers

Triggers defined in workflow config:

```yaml
specialization_triggers:
  - condition: "candidate.correctness >= 0.99 AND candidate.latency_ms_p95 <= 400"
    action: "fork_variant"
    variant_tags: ["prime", "accurate_and_fast"]

  - condition: "candidate.cost_per_call <= 0.0001 AND candidate.correctness >= 0.90"
    action: "fork_variant"
    variant_tags: ["ultra_cheap", "good_quality"]
```

## Notes
- Optimization runs are resource-intensive
- Use smaller run counts for quick tests
- Specializations inherit from best-performing variants
- Results automatically update forge registry
- Integrates with recursive optimizer
