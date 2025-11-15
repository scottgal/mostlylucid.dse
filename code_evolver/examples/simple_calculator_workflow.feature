Feature: Mathematical Calculator Workflow
  Perform multi-step calculations with validation

  # Simple addition scenario
  Scenario: Add two numbers
    Given two numbers 5 and 3
    When the calculator adds them
    Then the result should be 8

  # Chain multiple operations
  Scenario: Chain calculations with memory
    Given a starting value of 10
    When the calculator adds 5
    And the calculator multiplies by 2
    Then the result should be 30
    And the calculation history should have 2 steps

  # Error handling
  Scenario: Handle division by zero
    Given a starting value of 10
    When the calculator divides by 0
    Then an error should be raised
    And the error message should contain "division by zero"

  # Performance scenario
  Scenario: Calculate within time limit
    Given 100 random numbers
    When the calculator computes the sum
    Then the execution time should be less than 1 second
    And the memory usage should be less than 100 MB

## Additional Details

### Interface Specifications

#### Input Schema
```json
{
  "operation": {
    "type": "string",
    "enum": ["add", "subtract", "multiply", "divide"],
    "required": true
  },
  "operands": {
    "type": "array",
    "items": {"type": "number"},
    "min_items": 2,
    "required": true
  }
}
```

#### Output Schema
```json
{
  "result": {
    "type": "number"
  },
  "history": {
    "type": "array",
    "items": {
      "operation": "string",
      "operands": "array",
      "result": "number"
    }
  },
  "execution_time_ms": {
    "type": "integer"
  }
}
```

### Quality Specifications

- **Accuracy**: 100% (exact arithmetic)
- **Latency**: < 100ms for simple operations
- **Memory**: < 50 MB for standard calculations

### Test Results

```yaml
scenario: "Add two numbers"
inputs:
  operands: [5, 3]
  operation: "add"
results:
  result: 8
  execution_time_ms: 12
  status: PASS
```
