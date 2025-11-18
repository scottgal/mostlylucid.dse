# Validate Forge Tool

Run the multi-stage validation pipeline on a forge-registered tool.

## Usage
```
/forge_validate <tool_id> [version]
```

## Parameters
- `tool_id`: Tool identifier
- `version`: Tool version (optional, uses latest if not specified)

## What This Command Does

1. **BDD Acceptance Tests**:
   - Run behave tests if defined
   - Verify behavior matches specifications
   - Success threshold: 100%

2. **Unit Tests**:
   - Run pytest on tool implementation
   - Check code coverage
   - Success threshold: 95%

3. **Load Tests**:
   - Execute locust performance tests
   - Measure latency (p50, p95, p99)
   - Check failure rates
   - Thresholds: latency_p95 < 500ms, failure_rate < 2%

4. **Security Scanning**:
   - Static analysis with semgrep
   - Check for vulnerabilities
   - Threshold: 0 critical findings

5. **LLM Consensus Review**:
   - Multi-LLM evaluation
   - Dimensions: correctness, safety, resilience
   - Aggregate scores from multiple models

6. **Trust Level Update**:
   - validation_score >= 0.95 → "core"
   - validation_score >= 0.80 → "third_party"
   - validation_score < 0.80 → "experimental"

## Example
```bash
/forge_validate my_translator 1.0.0
```

Output:
```
Validating tool: my_translator v1.0.0

Stage 1: BDD Acceptance Tests
  ✓ All scenarios passed (5/5)
  Score: 1.0

Stage 2: Unit Tests
  ✓ Tests passed: 23/24 (95.8%)
  Score: 0.96

Stage 3: Load Tests
  ✓ Latency p95: 320ms
  ✓ Failure rate: 0.5%
  Score: 1.0

Stage 4: Security Scanning
  ✓ No critical findings
  ✓ 2 low severity findings
  Score: 0.95

Stage 5: LLM Consensus
  ✓ Correctness: 0.92
  ✓ Safety: 0.98
  ✓ Resilience: 0.89
  Score: 0.93

Overall Validation Score: 0.968
Trust Level: CORE ✓

Tool trust level upgraded: experimental → core
```

## Notes
- Validation updates the tool's trust level automatically
- Failed validation keeps tool at current trust level
- Re-run validation after fixing issues
- Validation results stored in consensus engine
