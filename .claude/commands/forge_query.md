# Query Forge Registry

Query the forge registry for tools matching capabilities and constraints.

## Usage
```
/forge_query <capability> [options]
```

## Parameters
- `capability`: Required capability (e.g., "summarize_pdf", "translate_text")

## Options
- `--latency <ms>`: Maximum latency in milliseconds (p95)
- `--risk <score>`: Maximum risk score (0.0-1.0)
- `--trust <level>`: Minimum trust level (core, third_party, experimental)
- `--tags <tag1,tag2>`: Filter by tags
- `--limit <n>`: Maximum results (default: 5)

## What This Command Does

1. **Semantic Search**:
   - Search RAG memory for matching tools
   - Use embeddings for semantic similarity
   - Filter by forge registry tags

2. **Constraint Filtering**:
   - Apply performance constraints (latency, cost)
   - Filter by risk score and trust level
   - Check capability compatibility

3. **Consensus Ranking**:
   - Retrieve consensus scores for candidates
   - Sort by weight (quality × recency)
   - Apply temporal decay for old tools

4. **Return Results**:
   - Best tool (highest weight)
   - Alternatives (top N)
   - Metrics and trust levels

## Examples

### Basic Query
```bash
/forge_query translate_text
```

Output:
```
Best Tool:
  tool_id: nmt_translator_v3
  version: 2.1.0
  trust_level: core
  weight: 0.94
  metrics:
    correctness: 0.98
    latency_ms_p95: 180
    cost_per_call: $0.0003

Alternatives:
  1. fast_translator_v1 (weight: 0.88)
  2. accurate_translator_v2 (weight: 0.85)
```

### With Constraints
```bash
/forge_query summarize_pdf --latency 500 --risk 0.2 --trust third_party
```

Output:
```
Best Tool:
  tool_id: pdf_summarizer_fast
  version: 1.5.0
  trust_level: third_party
  weight: 0.91
  metrics:
    correctness: 0.95
    latency_ms_p95: 420
    risk_score: 0.15

Meets all constraints: ✓
```

### With Tags
```bash
/forge_query translate_text --tags "finance,secure" --trust core
```

Output:
```
Best Tool:
  tool_id: secure_finance_translator
  version: 3.0.0
  trust_level: core
  weight: 0.96
  tags: [finance, secure, gdpr, translation]
```

## Notes
- Query uses semantic search, not exact keyword matching
- Tools with higher consensus weights appear first
- Temporal decay favors recently validated tools
- Trust level filtering ensures quality standards
