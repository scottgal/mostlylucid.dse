Feature: [Tool Name]
  [Brief description of what this tool does]

  # Basic functionality test
  Scenario: [Primary use case]
    Given [input parameter] "[value]"
    And [another parameter] "[value]"
    When the tool executes
    Then the output should [expected result]
    And [additional validation]

  # Test with different inputs
  Scenario: [Alternative use case]
    Given [different input] "[value]"
    When the tool executes
    Then the output should [expected result]

  # Edge case handling
  Scenario: Handle [edge case description]
    Given [edge case input]
    When the tool executes
    Then [expected graceful handling]
    And [error handling or default behavior]

  # Performance requirement
  Scenario: Execute within performance constraints
    Given [typical input size]
    When the tool executes
    Then the execution time should be less than [X] milliseconds
    And the memory usage should be less than [Y] MB
    And the quality score should be at least [Z]

  # Data-driven testing
  Scenario Outline: [Test multiple variations]
    Given an input "[input]"
    When the tool executes with parameters "<params>"
    Then the output should match "<expected>"

    Examples:
      | input    | params | expected |
      | value1   | param1 | result1  |
      | value2   | param2 | result2  |
      | value3   | param3 | result3  |

## Additional Details

### Interface Specification

#### Input Schema
```json
{
  "parameter_name": {
    "type": "string|number|boolean|object|array",
    "required": true|false,
    "description": "What this parameter is for",
    "default": "default_value",
    "enum": ["option1", "option2"],  // For restricted values
    "min": 0,                        // For numbers
    "max": 100,                      // For numbers
    "min_length": 1,                 // For strings/arrays
    "max_length": 1000               // For strings/arrays
  }
}
```

#### Output Schema
```json
{
  "result": {
    "type": "string|number|boolean|object|array",
    "description": "Primary output of the tool"
  },
  "metadata": {
    "type": "object",
    "structure": {
      "execution_time_ms": "integer",
      "quality_score": "float (0-1)",
      "confidence": "float (0-1)"
    }
  }
}
```

### Quality Specifications

#### Performance Targets
- **Latency (P50)**: < X ms
- **Latency (P95)**: < Y ms
- **Latency (P99)**: < Z ms
- **Memory Usage**: < N MB

#### Quality Metrics
- **Accuracy**: ≥ 0.XX (how correct the output is)
- **Completeness**: ≥ 0.XX (all required fields present)
- **Consistency**: ≥ 0.XX (same input → same output)
- **Robustness**: ≥ 0.XX (handles edge cases gracefully)

#### Reliability Targets
- **Success Rate**: ≥ XX%
- **Error Handling**: Describe graceful degradation
- **Retry Strategy**: Number of retries and backoff

### Tool Implementation Details

#### For LLM Tools
```
Model: [model name, e.g., llama3]
Temperature: [0.0 - 1.0]
System Prompt:
"""
[The system prompt that defines the tool's behavior]
"""
```

#### For Python Tools
```python
def tool_function(param1: type, param2: type) -> return_type:
    """
    Brief description of what this tool does.

    Args:
        param1: Description
        param2: Description

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this error occurs
    """
    # Implementation
```

#### For API Tools
```
Endpoint: [URL]
Method: GET|POST|PUT|DELETE
Headers: [Required headers]
Authentication: [Auth method]
Rate Limit: [Requests per time period]
```

### Expected Test Results

#### Baseline Execution
```yaml
scenario: "[Scenario name]"
inputs:
  parameter1: value1
  parameter2: value2

results:
  output:
    result: expected_value
  metadata:
    execution_time_ms: XXX
    quality_score: 0.XX
    confidence: 0.XX

  validation:
    all_scenarios_passed: true
    status: "success"
```

#### Performance Metrics
```yaml
performance_profile:
  latency_p50: XX ms
  latency_p95: XX ms
  latency_p99: XX ms
  memory_avg: XX MB
  memory_peak: XX MB
  throughput: XX operations/second
```

### Validation Criteria

#### BDD Scenario Validation Rules

| Then Step Pattern | Validation Logic | Pass Criteria |
|------------------|------------------|---------------|
| "output should be X" | `result == X` | Exact match |
| "output should contain X" | `X in result` | Contains check |
| "output should match pattern X" | `regex.match(X, result)` | Pattern match |
| "quality score should be at least X" | `score >= X` | Threshold check |
| "execution time should be less than X" | `time_ms < X` | Performance check |

### Evolution History

**Version 1.0** (Baseline)
- Initial implementation
- Performance: XXX ms average
- Quality: 0.XX average

**Version 1.1** (Optimized)
- Optimization: [What was optimized]
- Performance: XXX ms average (X% improvement)
- Quality: 0.XX average (maintained/improved)
- BDD Status: All scenarios passing

### Metadata

**Tool ID**: [unique_tool_id]
**Version**: 1.0.0
**BDD Specification Version**: 1.0.0
**Created**: YYYY-MM-DD
**Last Optimized**: YYYY-MM-DD
**Author**: [Your name or tool name]
**Status**: [draft|validated|production]
**Tags**: [tag1, tag2, tag3]
**Used In Workflows**: [workflow_id1, workflow_id2, ...]
