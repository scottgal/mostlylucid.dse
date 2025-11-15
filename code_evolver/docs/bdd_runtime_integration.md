# BDD Specification as Runtime Context

## Core Concept

The BDD specification is **embedded in the WorkflowSpec** and travels with the workflow. This means:

1. ✅ The workflow carries its own behavioral contract
2. ✅ Standard BDD testing tools (pytest-bdd, behave, cucumber) can validate it
3. ✅ No separate test files needed - the spec IS the test
4. ✅ CI/CD integration is straightforward
5. ✅ Self-validating workflows

## Architecture

```python
@dataclass
class WorkflowSpec:
    workflow_id: str
    description: str

    # The BDD spec is PART of the workflow
    bdd_specification: Optional[BDDSpecification] = None

    # Workflow structure
    steps: List[WorkflowStep] = field(default_factory=list)
    inputs: List[WorkflowInput] = field(default_factory=list)
    outputs: List[WorkflowOutput] = field(default_factory=list)

    # ... other fields ...
```

When the workflow executes, the runtime has **full access** to the BDD spec.

## Using Standard BDD Testing Tools

### Option 1: pytest-bdd (Python)

The workflow can export its BDD spec and run pytest-bdd against it:

```python
from pytest_bdd import scenarios, given, when, then, parsers
import pytest

class WorkflowBDDRunner:
    """Run standard pytest-bdd tests against workflow execution"""

    def __init__(self, workflow_spec: WorkflowSpec):
        self.workflow_spec = workflow_spec
        self.executor = WorkflowExecutor(workflow_spec)

    def export_feature_file(self) -> str:
        """Export embedded BDD spec to .feature file for pytest-bdd"""
        feature_content = self.workflow_spec.bdd_specification.to_gherkin()

        # Write to temp file or specific location
        feature_path = f"/tmp/{self.workflow_spec.workflow_id}.feature"
        with open(feature_path, 'w') as f:
            f.write(feature_content)

        return feature_path

    def generate_test_file(self, feature_path: str) -> str:
        """Generate pytest-bdd test implementation"""

        test_code = f'''
"""Auto-generated BDD tests for {self.workflow_spec.workflow_id}"""
from pytest_bdd import scenarios, given, when, then, parsers
import pytest
from code_evolver.src.workflow_executor import WorkflowExecutor
from code_evolver.src.workflow_spec import WorkflowSpec

# Load the workflow spec
WORKFLOW_SPEC = WorkflowSpec.from_json("{self.workflow_spec.workflow_id}.json")

# Load all scenarios from the feature file
scenarios("{feature_path}")

# Shared context for scenario execution
@pytest.fixture
def workflow_context():
    return {{
        "executor": WorkflowExecutor(WORKFLOW_SPEC),
        "inputs": {{}},
        "outputs": {{}},
        "metadata": {{}}
    }}

# =============================================================================
# Step Definitions
# =============================================================================

# --- Given Steps (Setup) ---

@given(parsers.parse("a topic \\"{topic}\\""))
def given_topic(workflow_context, topic):
    workflow_context["inputs"]["topic"] = topic

@given(parsers.parse("a target language \\"{language}\\""))
def given_language(workflow_context, language):
    workflow_context["inputs"]["target_language"] = language

@given(parsers.parse("{{number:d}} random numbers"))
def given_random_numbers(workflow_context, number):
    import random
    workflow_context["inputs"]["numbers"] = [random.random() for _ in range(number)]

@given("no target language is specified")
def given_no_language(workflow_context):
    # Don't set language - leave it undefined
    pass

# --- When Steps (Actions) ---

@when("the workflow executes")
def when_workflow_executes(workflow_context):
    executor = workflow_context["executor"]
    inputs = workflow_context["inputs"]

    # Execute the workflow
    result = executor.execute(inputs=inputs)

    # Store results in context
    workflow_context["outputs"] = result.outputs
    workflow_context["metadata"] = result.metadata

# --- Then Steps (Assertions) ---

@then(parsers.parse("an outline should be generated with at least {{count:d}} sections"))
def then_outline_has_sections(workflow_context, count):
    outputs = workflow_context["outputs"]
    assert "outline" in outputs
    assert len(outputs["outline"]["sections"]) >= count

@then(parsers.parse("an article should be at least {{words:d}} words"))
def then_article_word_count(workflow_context, words):
    outputs = workflow_context["outputs"]
    assert "article" in outputs
    assert outputs["article"]["word_count"] >= words

@then(parsers.parse("the execution time should be less than {{seconds:d}} seconds"))
def then_execution_time(workflow_context, seconds):
    metadata = workflow_context["metadata"]
    assert metadata["execution_time_ms"] < (seconds * 1000)

@then(parsers.parse("the memory usage should be less than {{mb:d}} MB"))
def then_memory_usage(workflow_context, mb):
    metadata = workflow_context["metadata"]
    assert metadata["memory_used_mb"] < mb

@then(parsers.parse("a translation should be produced in {{language}}"))
def then_translation_produced(workflow_context, language):
    outputs = workflow_context["outputs"]
    assert "translation" in outputs
    assert outputs["translation"]["language"] == language

@then("no translation step should execute")
def then_no_translation(workflow_context):
    outputs = workflow_context["outputs"]
    assert "translation" not in outputs or outputs["translation"] is None

@then("the workflow should complete successfully")
def then_workflow_success(workflow_context):
    metadata = workflow_context["metadata"]
    assert metadata["status"] in ["success", "partial_success"]
'''

        test_path = f"tests/test_{self.workflow_spec.workflow_id}.py"
        with open(test_path, 'w') as f:
            f.write(test_code)

        return test_path


# Usage:
# 1. Load workflow with embedded BDD spec
workflow = WorkflowSpec.from_json("article_workflow.json")

# 2. Export to pytest-bdd format
runner = WorkflowBDDRunner(workflow)
feature_file = runner.export_feature_file()
test_file = runner.generate_test_file(feature_file)

# 3. Run with pytest (standard tool!)
# $ pytest tests/test_article_workflow.py -v
#
# Output:
# tests/test_article_workflow.py::test_generate_article_with_spanish_translation PASSED
# tests/test_article_workflow.py::test_generate_article_without_translation PASSED
# tests/test_article_workflow.py::test_handle_complex_technical_topic PASSED
```

### Option 2: Self-Validation During Execution

The workflow can validate itself **as it runs**:

```python
class WorkflowExecutor:
    """Executes workflows with optional BDD validation"""

    def execute(
        self,
        inputs: Dict[str, Any],
        validate_bdd: bool = True  # NEW: Auto-validate against BDD
    ) -> WorkflowResult:

        # Execute workflow steps
        outputs, metadata = self._execute_steps(inputs)

        # If BDD validation is enabled and spec exists
        if validate_bdd and self.workflow_spec.bdd_enabled:
            bdd_results = self._validate_against_bdd(
                inputs,
                outputs,
                metadata
            )

            # Add BDD validation results to metadata
            metadata["bdd_validation"] = bdd_results
            metadata["all_scenarios_passed"] = all(bdd_results.values())

            # Optional: Fail execution if BDD scenarios don't pass
            if not metadata["all_scenarios_passed"]:
                metadata["status"] = "bdd_validation_failed"
                metadata["failed_scenarios"] = [
                    name for name, passed in bdd_results.items()
                    if not passed
                ]

        return WorkflowResult(
            outputs=outputs,
            metadata=metadata
        )

    def _validate_against_bdd(
        self,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Validate execution against embedded BDD scenarios"""

        validator = BDDValidator(self.workflow_spec.bdd_specification)
        return validator.validate_execution(inputs, outputs, metadata)


# Usage example:
executor = WorkflowExecutor(workflow_spec)

result = executor.execute(
    inputs={"topic": "AI in Healthcare"},
    validate_bdd=True  # Automatically validates against BDD spec
)

# Check if BDD scenarios passed
if result.metadata["all_scenarios_passed"]:
    print("✅ Workflow executed correctly - all BDD scenarios passed!")
else:
    print("❌ BDD validation failed:")
    for scenario in result.metadata["failed_scenarios"]:
        print(f"  - {scenario}")
```

## CI/CD Integration

Since the BDD spec is embedded, CI/CD is straightforward:

```yaml
# .github/workflows/test-workflows.yml
name: Test Workflows

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Install dependencies
        run: |
          pip install pytest pytest-bdd
          pip install -r requirements.txt

      - name: Export BDD specs from workflows
        run: |
          # For each workflow JSON, export its BDD spec
          python -m code_evolver.scripts.export_bdd_tests \
            --workflows workflows/*.json \
            --output tests/

      - name: Run BDD tests
        run: |
          # Standard pytest command!
          pytest tests/ -v --tb=short

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: bdd-test-results
          path: test-results/
```

## Workflow Storage Format

The workflow JSON includes the BDD spec:

```json
{
  "workflow_id": "article_generator_v2",
  "version": "2.0.0",
  "description": "Generate articles with translations",

  "bdd_specification": {
    "feature": "Multi-step Article Generation with Translation",
    "background": [
      "the workflow has access to outline_generator tool",
      "the workflow has access to article_writer tool"
    ],
    "scenarios": [
      {
        "name": "Generate article with Spanish translation",
        "given": [
          "a topic \"AI in Healthcare\"",
          "a target language \"Spanish\""
        ],
        "when": [
          "the workflow executes"
        ],
        "then": [
          "an outline should be generated with at least 3 sections",
          "an article should be written based on the outline",
          "the article should be at least 500 words"
        ]
      }
    ]
  },

  "bdd_enabled": true,

  "inputs": [...],
  "outputs": [...],
  "steps": [...]
}
```

## Benefits of Runtime Context

### 1. Workflow is Self-Contained
```python
# Everything you need is in one file
workflow = WorkflowSpec.from_json("my_workflow.json")

# Includes:
# - Step definitions
# - Tool dependencies
# - BDD test specification
# - Quality requirements

# Can be executed and tested anywhere
```

### 2. Automatic Regression Testing
```python
# During optimization
optimizer = HierarchicalOptimizer(...)

# Every optimization attempt automatically:
# 1. Executes the optimized workflow
# 2. Validates against embedded BDD spec
# 3. Rejects changes that break scenarios
# 4. Only accepts improvements that preserve behavior

optimized = optimizer.optimize(
    workflow_spec,
    target_metric="speed"
)

# Guaranteed: All BDD scenarios still pass
```

### 3. Use Any BDD Testing Tool

Because the BDD spec is in standard Gherkin format, you can use:

- **pytest-bdd** (Python)
- **behave** (Python)
- **Cucumber** (Ruby, JavaScript, Java, etc.)
- **SpecFlow** (.NET)
- **JBehave** (Java)

Just export the embedded spec and run!

### 4. Documentation is Always Current

```python
# Generate docs from workflow
doc_generator = WorkflowDocumentationGenerator()

# Reads BDD spec directly from workflow
markdown_docs = doc_generator.generate_markdown_docs(workflow_spec)

# Docs are always in sync because they come from the same source
```

## Example: Complete Flow

```python
# ============================================================================
# 1. CREATE WORKFLOW WITH EMBEDDED BDD SPEC
# ============================================================================

workflow_spec = WorkflowSpec(
    workflow_id="calculator",
    description="Basic calculator workflow",
    bdd_specification=BDDSpecification(
        feature="Mathematical Calculator",
        scenarios=[
            BDDScenario(
                name="Add two numbers",
                given=["two numbers 5 and 3"],
                when=["the calculator adds them"],
                then=["the result should be 8"]
            )
        ]
    ),
    bdd_enabled=True,
    steps=[...]  # Workflow implementation
)

# Save to JSON (includes BDD spec)
workflow_spec.to_json_file("calculator.json")

# ============================================================================
# 2. EXECUTE WITH AUTOMATIC BDD VALIDATION
# ============================================================================

executor = WorkflowExecutor(workflow_spec)
result = executor.execute(
    inputs={"numbers": [5, 3], "operation": "add"},
    validate_bdd=True  # Validates against embedded spec
)

print(f"Result: {result.outputs['result']}")  # 8
print(f"BDD Valid: {result.metadata['all_scenarios_passed']}")  # True

# ============================================================================
# 3. EXPORT FOR STANDARD BDD TESTING TOOLS
# ============================================================================

runner = WorkflowBDDRunner(workflow_spec)
feature_file = runner.export_feature_file()  # calculator.feature
test_file = runner.generate_test_file(feature_file)  # test_calculator.py

# Now run with standard pytest
# $ pytest test_calculator.py -v

# ============================================================================
# 4. CI/CD AUTOMATICALLY TESTS ALL WORKFLOWS
# ============================================================================

# In CI pipeline:
# 1. Load all workflow JSON files
# 2. Export their embedded BDD specs
# 3. Run pytest-bdd on all of them
# 4. Fail if any scenario fails

# No separate test maintenance needed!
```

## Key Insight

The BDD specification is **not a separate artifact** - it's an **intrinsic part of the workflow**. This means:

✅ **Single source of truth** - One file contains behavior contract AND implementation
✅ **Always in sync** - Spec can't drift from implementation
✅ **Portable** - Share one JSON file, get tests included
✅ **Validatable** - Use standard BDD tools without extra setup
✅ **Evolvable** - Optimizations must preserve the spec

The workflow carries its own quality guarantee with it wherever it goes.
