Feature: [Short descriptive name of the workflow feature]
  [Brief description of what this workflow does]
  [Why this workflow is valuable - user benefit]

  # Optional: Common setup for all scenarios
  Background:
    Given [common precondition 1]
    And [common precondition 2]

  # Basic happy path scenario
  Scenario: [Descriptive name of what happens]
    Given [initial condition or input]
    When [action that triggers the workflow]
    Then [expected outcome]
    And [additional expected outcome]

  # Scenario with multiple steps
  Scenario: [Another scenario name]
    Given [precondition with specific value like "the word is silky"]
    And [another precondition]
    When [first action]
    And [second action]
    Then [expected result]
    And [another expected result]

  # Error handling scenario
  Scenario: [Handle error case]
    Given [setup that will cause error]
    When [action is attempted]
    Then [error should be handled gracefully]
    And [appropriate error message or fallback]

  # Performance scenario
  Scenario: [Performance requirement]
    Given [input size or complexity]
    When [workflow executes]
    Then [execution time should be less than X seconds]
    And [memory usage should be less than Y MB]
    And [quality score should be at least Z]

  # Scenario with examples (data-driven testing)
  Scenario Outline: [Scenario that tests multiple cases]
    Given [input parameter "<param1>"]
    And [another parameter "<param2>"]
    When [workflow executes]
    Then [expected result should be "<expected>"]

    Examples:
      | param1  | param2 | expected |
      | value1  | valueA | result1  |
      | value2  | valueB | result2  |
      | value3  | valueC | result3  |

## Additional Details

### Interface Specifications

#### Input Schema
```json
{
  "parameter_name": {
    "type": "string|number|boolean|object|array",
    "required": true|false,
    "description": "What this parameter is for",
    "enum": ["option1", "option2"],  // Optional: for restricted values
    "default": "default_value",       // Optional: if not required
    "min_length": 1,                  // Optional: for strings
    "max_length": 100,                // Optional: for strings
    "min": 0,                         // Optional: for numbers
    "max": 1000                       // Optional: for numbers
  }
}
```

#### Output Schema
```json
{
  "output_field": {
    "type": "string|number|boolean|object|array",
    "description": "What this output contains",
    "structure": {
      // For complex objects, describe the structure
      "nested_field": "type"
    }
  },
  "execution_metadata": {
    "type": "object",
    "structure": {
      "status": "success|partial_success|failure",
      "execution_time_ms": "integer",
      "memory_used_mb": "integer"
    }
  }
}
```

#### Tool Signatures

**tool_name**
```python
def tool_name(
    param1: type,
    param2: type = default_value
) -> return_type:
    """
    Brief description of what this tool does.

    Args:
        param1: Description of parameter
        param2: Description of parameter

    Returns:
        Description of return value structure
    """
```

### Quality Specifications

#### Performance Targets
- **Latency (P95)**: < X seconds
- **Latency (P99)**: < Y seconds
- **Memory Usage**: < Z MB average
- **Throughput**: Minimum N operations per hour

#### Quality Metrics
- **Accuracy**: ≥ 0.XX (describe how measured)
- **Completeness**: ≥ 0.XX (e.g., all required fields present)
- **Consistency**: ≥ 0.XX (e.g., results match expected format)

#### Reliability Targets
- **Success Rate**: ≥ XX%
- **Graceful Degradation**: Describe fallback behavior
- **Recovery from Failures**: Describe retry strategy

### Workflow Step Dependencies

```
[Visual representation of workflow steps and dependencies]

┌─────────────────┐
│  Input: X       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Step 1: [Name]         │
│  Tool: [tool_name]      │
│  Timeout: Xs            │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Step 2: [Name]         │
│  Inputs: [from step 1]  │
│  Conditional: [if X]    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Output: [Name]         │
└─────────────────────────┘
```

### Expected Test Results

#### Baseline Execution
```yaml
test_case: "[Scenario name]"
inputs:
  parameter1: value1
  parameter2: value2

actual_results:
  execution_time_ms: XXX
  memory_used_mb: XXX
  quality_score: 0.XX

  output_field:
    metric1: value
    metric2: value

  status: "success|partial_success|failure"
  all_scenarios_passed: true|false
```

### Validation Criteria

#### BDD Scenario Validation Rules

| Then Step Pattern | Validation Logic | Pass Criteria |
|------------------|------------------|---------------|
| "result should be X" | `output['result'] == X` | Exact match |
| "should be at least N" | `value >= N` | Numeric comparison |
| "should contain X" | `X in output` | Contains check |
| "should be less than N" | `value < N` | Upper bound |

### Metadata

**Workflow ID**: [unique_workflow_id]
**Version**: 1.0.0
**BDD Specification Version**: 1.0.0
**Created**: YYYY-MM-DD
**Author**: [Your name or tool name]
**Status**: [draft|validated|production]
**Tags**: [tag1, tag2, tag3]
