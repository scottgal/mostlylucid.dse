# BDD Workflow Specifications - Quick Start Guide

## What is BDD for Workflows?

BDD (Behavior-Driven Development) specifications serve **multiple purposes** in mostlylucid DiSE:

1. **Code Generation Prompt** - Tells the LLM what behavior to implement
2. **Integration Test** - Validates the workflow does what it should
3. **Documentation** - Human-readable description of expected behavior
4. **Evolution Guard** - Ensures optimizations don't break functionality

## Format: Gherkin + Additional Details

### Part 1: Gherkin Scenarios (Human-readable behavior)

```gherkin
Feature: Calculator
  Basic arithmetic operations

  Scenario: Add two numbers
    Given two numbers 5 and 3
    When the calculator adds them
    Then the result should be 8
```

**Key Gherkin Keywords:**
- `Feature:` - High-level description of what the workflow does
- `Scenario:` - Specific example of behavior
- `Given` - Initial conditions/inputs
- `When` - Action that triggers the workflow
- `Then` - Expected outcomes
- `And` - Additional conditions/outcomes
- `But` - Contrasting conditions/outcomes

### Part 2: Additional Details (Technical specifications)

After the Gherkin scenarios, add technical details:

```markdown
## Additional Details

### Interface Specifications
- Input/output schemas (JSON format)
- Tool signatures (function definitions)

### Quality Specifications
- Performance targets (latency, memory)
- Quality metrics (accuracy, completeness)
- Reliability targets (success rate, error handling)

### Expected Test Results
- Baseline execution metrics
- Example test outputs
```

## Quick Start: Creating a BDD Spec

### Step 1: Copy the Template

```bash
cp code_evolver/templates/workflow_bdd_template.feature my_workflow.feature
```

### Step 2: Define Your Feature

```gherkin
Feature: [What does this workflow do?]
  [Why is it useful?]
```

Example:
```gherkin
Feature: Email Newsletter Generator
  Generate personalized newsletters from content topics
```

### Step 3: Write Scenarios

Think of **concrete examples** of how the workflow should behave:

```gherkin
Scenario: Generate newsletter for single topic
  Given a topic "AI advancements"
  And a subscriber list with 100 subscribers
  When the newsletter generator runs
  Then a newsletter should be created
  And the newsletter should include the topic
  And 100 personalized emails should be queued
```

### Step 4: Add Edge Cases

```gherkin
Scenario: Handle empty subscriber list
  Given a topic "AI advancements"
  And an empty subscriber list
  When the newsletter generator runs
  Then a newsletter should be created
  And no emails should be queued
  And a warning should be logged
```

### Step 5: Add Performance Scenarios

```gherkin
Scenario: Complete within time limit
  Given a topic and 1000 subscribers
  When the newsletter generator runs
  Then execution time should be less than 30 seconds
  And memory usage should be less than 512 MB
```

### Step 6: Fill in Additional Details

Add technical specs at the end:

```markdown
## Additional Details

### Interface Specifications

#### Input Schema
{
  "topic": {"type": "string", "required": true},
  "subscribers": {"type": "array", "required": true}
}

### Quality Specifications
- **Latency**: < 30 seconds for 1000 subscribers
- **Success Rate**: ≥ 95%
```

## Using BDD Specs in mostlylucid DiSE

### Option 1: Generate Workflow from BDD Spec

```python
from code_evolver.src.overseer_llm import OverseerLLM
from code_evolver.src.workflow_spec import BDDSpecification

# Load BDD spec from .feature file
bdd_spec = BDDSpecification.from_file("my_workflow.feature")

# Generate workflow implementation
overseer = OverseerLLM(...)
execution_plan = overseer.create_execution_plan(
    task_description="",  # Not needed - BDD has the requirements
    context={"domain": "email_automation"},
    bdd_spec=bdd_spec
)

# The LLM receives structured requirements from BDD scenarios
```

### Option 2: Validate Existing Workflow Against BDD

```python
from code_evolver.src.bdd_validator import BDDWorkflowValidator

# Load workflow with BDD spec
workflow_spec = WorkflowSpec.from_json("my_workflow.json")

# Execute workflow
executor = WorkflowExecutor(workflow_spec)
result = executor.execute(inputs={"topic": "AI", "subscribers": [...]})

# Validate against BDD scenarios
validator = BDDWorkflowValidator(workflow_spec)
validation_results = validator.validate_execution(
    inputs={"topic": "AI", "subscribers": [...]},
    outputs=result.outputs,
    execution_metadata=result.metadata
)

# Check results
if all(validation_results.values()):
    print("✅ All BDD scenarios passed!")
else:
    print("❌ Some scenarios failed:")
    for scenario, passed in validation_results.items():
        if not passed:
            print(f"  - {scenario}")
```

### Option 3: Ensure Optimizations Preserve Behavior

```python
# During evolution/optimization
optimizer = HierarchicalOptimizer(...)

# Optimize workflow
optimized_workflow = optimizer.optimize(
    workflow_spec,
    target_metric="speed",
    constraints={"preserve_bdd_scenarios": True}  # Critical!
)

# Automatically validates:
# 1. All original BDD scenarios still pass
# 2. Performance improvements are real
# 3. No quality regressions

# Result: Faster workflow with guaranteed behavior preservation
```

## BDD Scenario Patterns

### Pattern 1: Input/Output Validation

```gherkin
Scenario: Transform data format
  Given input data in JSON format
  When the transformer processes it
  Then output should be in XML format
  And all fields should be preserved
```

### Pattern 2: Multi-Step Workflows

```gherkin
Scenario: Chain operations
  Given a starting value of 10
  When step 1 multiplies by 2
  And step 2 adds 5
  Then the final result should be 25
```

### Pattern 3: Conditional Behavior

```gherkin
Scenario: Skip optional steps
  Given a required field "name"
  But no optional field "email"
  When the workflow executes
  Then the name should be processed
  And email validation should be skipped
```

### Pattern 4: Error Handling

```gherkin
Scenario: Graceful degradation
  Given a valid input
  And an unavailable external service
  When the workflow executes
  Then partial results should be returned
  And an error should be logged
  And status should be "partial_success"
```

### Pattern 5: Performance Requirements

```gherkin
Scenario Outline: Scale with input size
  Given <input_size> items to process
  When the workflow executes
  Then execution time should be less than <max_time> seconds

  Examples:
    | input_size | max_time |
    | 100        | 5        |
    | 1000       | 30       |
    | 10000      | 180      |
```

## Best Practices

### ✅ DO:

1. **Use concrete examples** - "Given a word with 5 letters" not "Given a word"
2. **One scenario per behavior** - Don't combine unrelated tests
3. **Focus on behavior, not implementation** - "Then result should be 8" not "Then the add() function should return 8"
4. **Include edge cases** - Empty inputs, errors, boundary conditions
5. **Specify quality requirements** - Performance, accuracy, reliability

### ❌ DON'T:

1. **Be too vague** - "Then it should work" ❌ → "Then output should contain 3 sections" ✅
2. **Test implementation details** - "Then the SQL query should use JOIN" ❌
3. **Combine too many scenarios** - Keep scenarios focused and independent
4. **Forget error cases** - Always include failure scenarios
5. **Skip performance specs** - Always define acceptable latency/memory

## Example: Complete BDD Spec

See the template and examples:
- **Template**: `code_evolver/templates/workflow_bdd_template.feature`
- **Simple Example**: `code_evolver/examples/simple_calculator_workflow.feature`
- **Complex Example**: `code_evolver/examples/article_generation_workflow.feature`

## Integration with Existing Workflows

### Retrofitting BDD to Existing Workflows

```python
# 1. Load existing workflow
workflow = WorkflowSpec.from_json("existing_workflow.json")

# 2. Create BDD spec based on observed behavior
bdd_spec = BDDSpecification(
    feature="Existing workflow behavior",
    scenarios=[
        BDDScenario(
            name="Current behavior",
            given=["inputs that currently work"],
            when=["workflow executes"],
            then=["outputs currently produced"]
        )
    ]
)

# 3. Attach to workflow
workflow.bdd_specification = bdd_spec
workflow.bdd_enabled = True

# 4. Now future optimizations must preserve this behavior!
```

## Benefits Summary

| Benefit | How BDD Helps |
|---------|---------------|
| **Better Code Generation** | LLM gets structured, unambiguous requirements |
| **Automatic Testing** | Every workflow is self-validating |
| **Safe Evolution** | Optimizations can't break documented behavior |
| **Clear Documentation** | Human-readable specification of what workflow does |
| **Cross-team Communication** | Non-technical stakeholders can review scenarios |
| **Regression Prevention** | Behavior contract survives through changes |

## Next Steps

1. **Try the template**: Copy `workflow_bdd_template.feature` and create your first BDD spec
2. **Review examples**: Look at `simple_calculator_workflow.feature` for patterns
3. **Read full proposal**: See `bdd_workflow_proposal.md` for architecture details
4. **Start simple**: Begin with one or two scenarios, expand as needed

## Questions?

- **Q: Do I need to write BDD specs for every workflow?**
  A: No, it's optional. Use BDD when behavior preservation is critical or requirements are complex.

- **Q: Can I use BDD with existing workflows?**
  A: Yes! Add `bdd_specification` to any WorkflowSpec and start validating.

- **Q: What if my scenario fails after optimization?**
  A: The optimizer will reject changes that break BDD scenarios, ensuring behavior is preserved.

- **Q: How detailed should scenarios be?**
  A: Include enough detail to validate correct behavior, but avoid implementation specifics.
