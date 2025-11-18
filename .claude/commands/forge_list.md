# List Forge Tools

List all tools registered in the forge registry with filtering options.

## Usage
```
/forge_list [options]
```

## Options
- `--trust <level>`: Filter by trust level (core, third_party, experimental)
- `--type <type>`: Filter by tool type (mcp, llm, executable, etc.)
- `--tags <tag1,tag2>`: Filter by tags
- `--sort <field>`: Sort by field (weight, validation_score, created_at)
- `--format <format>`: Output format (table, json, yaml)

## What This Command Does

1. **Query Registry**:
   - Fetch all forge-registered tools
   - Apply filter criteria
   - Sort by specified field

2. **Enrich Data**:
   - Load consensus scores
   - Add latest metrics
   - Calculate ages and decay

3. **Format Output**:
   - Display in requested format
   - Show key metrics
   - Highlight trust levels

## Examples

### List All Tools
```bash
/forge_list
```

Output:
```
Forge Registry Tools (12 total)

CORE TOOLS (validation_score >= 0.95)
┌─────────────────────┬─────────┬────────┬───────────┬───────────┐
│ Tool ID             │ Version │ Weight │ Latency   │ Created   │
├─────────────────────┼─────────┼────────┼───────────┼───────────┤
│ nmt_translator      │ 2.1.0   │ 0.96   │ 180ms     │ 2025-10-15│
│ pdf_summarizer      │ 3.0.0   │ 0.94   │ 420ms     │ 2025-10-20│
│ secure_translator   │ 1.5.0   │ 0.93   │ 250ms     │ 2025-11-01│
└─────────────────────┴─────────┴────────┴───────────┴───────────┘

THIRD_PARTY TOOLS (0.80 <= validation_score < 0.95)
┌─────────────────────┬─────────┬────────┬───────────┬───────────┐
│ fast_translator     │ 1.2.0   │ 0.88   │ 120ms     │ 2025-11-05│
│ data_processor      │ 2.0.0   │ 0.85   │ 350ms     │ 2025-11-10│
└─────────────────────┴─────────┴────────┴───────────┴───────────┘

EXPERIMENTAL TOOLS (validation_score < 0.80)
┌─────────────────────┬─────────┬────────┬───────────┬───────────┐
│ new_translator      │ 0.1.0   │ 0.45   │ ?         │ 2025-11-18│
│ test_tool           │ 0.1.0   │ 0.30   │ ?         │ 2025-11-18│
└─────────────────────┴─────────┴────────┴───────────┴───────────┘
```

### Filter by Trust Level
```bash
/forge_list --trust core
```

Output:
```
CORE TOOLS (3 total)

nmt_translator v2.1.0
  Trust: CORE (validation_score: 0.98)
  Weight: 0.96
  Metrics:
    correctness: 0.98
    latency_ms_p95: 180
    cost_per_call: $0.0003
    failure_rate: 0.5%
  Tags: [translation, nmt, secure, gdpr]

pdf_summarizer v3.0.0
  Trust: CORE (validation_score: 0.96)
  Weight: 0.94
  Metrics:
    correctness: 0.95
    latency_ms_p95: 420
    cost_per_call: $0.0012
  Tags: [summarization, pdf, document]

...
```

### Filter by Type
```bash
/forge_list --type mcp --format json
```

Output:
```json
{
  "tools": [
    {
      "tool_id": "nmt_translator",
      "version": "2.1.0",
      "type": "mcp",
      "trust_level": "core",
      "weight": 0.96,
      "metrics": {
        "correctness": 0.98,
        "latency_ms_p95": 180
      }
    },
    ...
  ]
}
```

### Filter by Tags
```bash
/forge_list --tags "translation,secure"
```

Output:
```
Tools matching tags: [translation, secure]

secure_translator v1.5.0
  Trust: CORE
  Weight: 0.93
  Tags: [translation, secure, encryption, gdpr]

nmt_translator v2.1.0
  Trust: CORE
  Weight: 0.96
  Tags: [translation, nmt, secure, gdpr]
```

### Sort by Weight
```bash
/forge_list --sort weight --format table
```

Output (sorted by consensus weight, highest first):
```
┌─────────────────────┬─────────┬────────┬────────────┐
│ Tool ID             │ Version │ Weight │ Trust      │
├─────────────────────┼─────────┼────────┼────────────┤
│ nmt_translator      │ 2.1.0   │ 0.96   │ core       │
│ pdf_summarizer      │ 3.0.0   │ 0.94   │ core       │
│ secure_translator   │ 1.5.0   │ 0.93   │ core       │
│ fast_translator     │ 1.2.0   │ 0.88   │ third_party│
│ ...                 │ ...     │ ...    │ ...        │
└─────────────────────┴─────────┴────────┴────────────┘
```

## Notes
- Trust levels auto-update after validation
- Weights recalculate after each execution
- Experimental tools need validation to upgrade
- Use `--format json` for programmatic access
