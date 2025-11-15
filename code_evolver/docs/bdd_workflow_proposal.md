# BDD-Enhanced Workflow Specification Proposal

## Overview

Enhance WorkflowSpec to include BDD (Behavior-Driven Development) specifications that serve **multiple purposes**:
1. **Code Generation Prompt** - Initial specification for LLM to generate workflow
2. **Intrinsic Integration Test** - Self-validating behavior contract
3. **Living Documentation** - Human-readable workflow behavior description
4. **Evolution Constraint** - Ensures optimizations preserve expected behavior
5. **Portability Aid** - Clear contract for cross-system understanding

## Architecture Changes

### 1. Enhanced WorkflowSpec Data Structure

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List

@dataclass
class BDDScenario:
    """Individual BDD scenario within a workflow"""
    name: str
    given: List[str]  # Preconditions
    when: List[str]   # Actions
    then: List[str]   # Expected outcomes
    examples: Optional[List[Dict[str, Any]]] = None  # For scenario outlines
    tags: List[str] = field(default_factory=list)  # e.g., ["@smoke", "@critical"]

@dataclass
class BDDSpecification:
    """Complete BDD specification for a workflow"""
    feature: str  # Feature description
    background: Optional[List[str]] = None  # Common preconditions
    scenarios: List[BDDScenario] = field(default_factory=list)

    def to_gherkin(self) -> str:
        """Convert to Gherkin format for testing/documentation"""
        lines = [f"Feature: {self.feature}"]

        if self.background:
            lines.append("\n  Background:")
            lines.extend([f"    {step}" for step in self.background])

        for scenario in self.scenarios:
            lines.append(f"\n  Scenario: {scenario.name}")
            for step in scenario.given:
                lines.append(f"    Given {step}")
            for step in scenario.when:
                lines.append(f"    When {step}")
            for step in scenario.then:
                lines.append(f"    Then {step}")

        return "\n".join(lines)

    def to_llm_prompt(self) -> str:
        """Convert to structured prompt for code generation"""
        prompt = f"# Workflow Requirements\n\n{self.feature}\n\n"
        prompt += "## Expected Behavior\n\n"

        for i, scenario in enumerate(self.scenarios, 1):
            prompt += f"### Scenario {i}: {scenario.name}\n\n"
            prompt += "**Preconditions:**\n"
            for step in scenario.given:
                prompt += f"- {step}\n"
            prompt += "\n**Actions:**\n"
            for step in scenario.when:
                prompt += f"- {step}\n"
            prompt += "\n**Expected Results:**\n"
            for step in scenario.then:
                prompt += f"- {step}\n"
            prompt += "\n"

        return prompt

@dataclass
class WorkflowSpec:
    """Enhanced workflow specification with BDD support"""
    workflow_id: str
    description: str
    version: str = "1.0.0"

    # NEW: BDD Specification
    bdd_specification: Optional[BDDSpecification] = None
    bdd_enabled: bool = False  # Whether to use BDD for testing/validation

    # ... existing fields ...
    inputs: List[WorkflowInput] = field(default_factory=list)
    outputs: List[WorkflowOutput] = field(default_factory=list)
    steps: List[WorkflowStep] = field(default_factory=list)

    # ... rest of existing structure ...
```

### 2. Multi-Purpose Usage Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    BDD Specification                            │
│  (Single source of truth - stored in WorkflowSpec)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │  Generate   │   │    Test     │   │  Document   │
    │    Code     │   │  Behavior   │   │   Workflow  │
    └─────────────┘   └─────────────┘   └─────────────┘
           │                  │                  │
           │                  │                  │
           ▼                  ▼                  ▼
    OverseerLLM       pytest-bdd         docs/workflows/
    uses BDD as       validates           feature_name.md
    prompt for        workflow            (auto-generated
    generation        execution           documentation)
                      results
```

### 3. Integration Points

#### A. Code Generation (OverseerLLM)

```python
# In overseer_llm.py
def create_execution_plan(
    task_description: str,
    context: dict,
    bdd_spec: Optional[BDDSpecification] = None
) -> ExecutionPlan:
    """
    Create execution plan, optionally using BDD spec as base.

    If bdd_spec is provided, it becomes the primary requirement definition.
    """
    if bdd_spec:
        # Use BDD as structured prompt
        prompt = self._build_bdd_planning_prompt(bdd_spec, context)
    else:
        # Fallback to traditional text-based prompts
        prompt = self._build_planning_prompt(task_description, context)

    # ... rest of planning logic ...

def _build_bdd_planning_prompt(
    self,
    bdd_spec: BDDSpecification,
    context: dict
) -> str:
    """Build planning prompt from BDD specification"""

    prompt = f"""You are designing a workflow implementation.

{bdd_spec.to_llm_prompt()}

## Context
{json.dumps(context, indent=2)}

## Task
Design a WorkflowSpec that implements the behavior described above.

Return a JSON ExecutionPlan with:
1. strategy: High-level approach to implementing these scenarios
2. steps: Specific implementation steps
3. expected_quality: Confidence the plan will meet all scenarios (0-1)
4. expected_speed_ms: Estimated execution time

The implementation MUST satisfy all scenarios defined in the BDD specification.
"""
    return prompt
```

#### B. Behavior Testing (New Component)

```python
# In src/bdd_validator.py (NEW FILE)
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from typing import Dict, Any

class BDDWorkflowValidator:
    """Validates workflow execution against BDD specification"""

    def __init__(self, workflow_spec: WorkflowSpec):
        self.workflow_spec = workflow_spec
        self.bdd_spec = workflow_spec.bdd_specification
        self.execution_context: Dict[str, Any] = {}

    def generate_test_file(self, output_path: str):
        """Generate pytest-bdd test file from BDD spec"""
        if not self.bdd_spec:
            raise ValueError("WorkflowSpec has no BDD specification")

        # Write .feature file
        feature_path = output_path.replace('.py', '.feature')
        with open(feature_path, 'w') as f:
            f.write(self.bdd_spec.to_gherkin())

        # Generate test implementation
        test_code = self._generate_test_code(feature_path)
        with open(output_path, 'w') as f:
            f.write(test_code)

    def validate_execution(
        self,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        execution_metadata: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Validate a workflow execution against BDD scenarios.

        Returns dict mapping scenario names to pass/fail status.
        """
        results = {}

        for scenario in self.bdd_spec.scenarios:
            try:
                # Execute scenario validation
                passed = self._validate_scenario(
                    scenario,
                    inputs,
                    outputs,
                    execution_metadata
                )
                results[scenario.name] = passed
            except Exception as e:
                results[scenario.name] = False
                results[f"{scenario.name}_error"] = str(e)

        return results

    def _validate_scenario(
        self,
        scenario: BDDScenario,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> bool:
        """Validate a single scenario against execution results"""

        # Step 1: Verify "Given" conditions (preconditions)
        for given_step in scenario.given:
            if not self._verify_precondition(given_step, inputs):
                return False

        # Step 2: Verify "When" conditions (workflow was executed)
        # (Implicit - we have outputs, so workflow ran)

        # Step 3: Verify "Then" conditions (expected outcomes)
        for then_step in scenario.then:
            if not self._verify_outcome(then_step, outputs, metadata):
                return False

        return True

    def _verify_outcome(
        self,
        then_step: str,
        outputs: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> bool:
        """Verify a single 'Then' assertion"""

        # Parse common assertion patterns
        if "should be at least" in then_step:
            # Example: "the article should be at least 500 words"
            return self._verify_minimum_value(then_step, outputs)

        elif "should be less than" in then_step:
            # Example: "execution time should be less than 30 seconds"
            return self._verify_maximum_value(then_step, metadata)

        elif "should contain" in then_step:
            # Example: "outline should contain at least 3 sections"
            return self._verify_contains(then_step, outputs)

        elif "should be produced" in then_step:
            # Example: "a translation should be produced"
            return self._verify_output_exists(then_step, outputs)

        # Add more patterns as needed
        return True  # Default to passing unknown patterns

    # ... more validation methods ...
```

#### C. Documentation Generation

```python
# In src/workflow_docs_generator.py (NEW FILE)
class WorkflowDocumentationGenerator:
    """Generate documentation from BDD specifications"""

    def generate_markdown_docs(self, workflow_spec: WorkflowSpec) -> str:
        """Generate human-readable markdown documentation"""

        if not workflow_spec.bdd_specification:
            return self._generate_traditional_docs(workflow_spec)

        bdd = workflow_spec.bdd_specification

        doc = f"""# {workflow_spec.workflow_id}

## Description
{workflow_spec.description}

## Feature
{bdd.feature}

## Behavior Scenarios

"""
        for i, scenario in enumerate(bdd.scenarios, 1):
            doc += f"### Scenario {i}: {scenario.name}\n\n"

            doc += "**Prerequisites:**\n"
            for step in scenario.given:
                doc += f"- {step}\n"

            doc += "\n**Execution:**\n"
            for step in scenario.when:
                doc += f"- {step}\n"

            doc += "\n**Expected Outcome:**\n"
            for step in scenario.then:
                doc += f"- {step}\n"

            doc += "\n---\n\n"

        # Add technical details
        doc += "## Technical Specification\n\n"
        doc += f"**Version:** {workflow_spec.version}\n"
        doc += f"**Created:** {workflow_spec.created_at}\n\n"

        doc += "### Inputs\n"
        for inp in workflow_spec.inputs:
            doc += f"- `{inp.name}` ({inp.type}): {inp.description}\n"

        doc += "\n### Outputs\n"
        for out in workflow_spec.outputs:
            doc += f"- `{out.name}` ({out.type}): {out.description}\n"

        return doc
```

## Example: Article Generation Workflow with BDD

### BDD Specification (Stored in WorkflowSpec)

```python
article_workflow_bdd = BDDSpecification(
    feature="Multi-step Article Generation with Translation",
    background=[
        "the workflow has access to outline_generator tool",
        "the workflow has access to article_writer tool",
        "the workflow has access to translator tool"
    ],
    scenarios=[
        BDDScenario(
            name="Generate article with Spanish translation",
            given=[
                'a topic "AI in Healthcare"',
                'a target language "Spanish"'
            ],
            when=[
                "the workflow executes"
            ],
            then=[
                "an outline should be generated with at least 3 sections",
                "an article should be written based on the outline",
                "the article should be at least 500 words",
                "a translation should be produced in Spanish",
                "the translation should preserve the article structure"
            ]
        ),
        BDDScenario(
            name="Performance within constraints",
            given=[
                'a simple topic "Technology Trends"'
            ],
            when=[
                "the workflow executes"
            ],
            then=[
                "the total execution time should be less than 30 seconds",
                "the memory usage should be less than 512 MB"
            ],
            tags=["@performance"]
        )
    ]
)
```

### Usage Flow

```python
# 1. CREATE WORKFLOW WITH BDD
workflow_spec = WorkflowSpec(
    workflow_id="article_generator_v2",
    description="Generate articles with translations",
    bdd_specification=article_workflow_bdd,
    bdd_enabled=True
)

# 2. GENERATE CODE FROM BDD
overseer = OverseerLLM(...)
execution_plan = overseer.create_execution_plan(
    task_description="",  # Not needed - BDD provides requirements
    context={"domain": "content_generation"},
    bdd_spec=article_workflow_bdd
)

# OverseerLLM receives this prompt:
# """
# You are designing a workflow implementation.
#
# # Workflow Requirements
#
# Multi-step Article Generation with Translation
#
# ## Expected Behavior
#
# ### Scenario 1: Generate article with Spanish translation
#
# **Preconditions:**
# - a topic "AI in Healthcare"
# - a target language "Spanish"
#
# **Actions:**
# - the workflow executes
#
# **Expected Results:**
# - an outline should be generated with at least 3 sections
# - an article should be written based on the outline
# - ...
# """

# 3. EXECUTE WORKFLOW
executor = WorkflowExecutor(workflow_spec)
result = executor.execute(inputs={"topic": "AI in Healthcare", "language": "Spanish"})

# 4. VALIDATE AGAINST BDD
validator = BDDWorkflowValidator(workflow_spec)
validation_results = validator.validate_execution(
    inputs={"topic": "AI in Healthcare", "language": "Spanish"},
    outputs=result.outputs,
    execution_metadata=result.metadata
)

# Results:
# {
#   "Generate article with Spanish translation": True,
#   "Performance within constraints": True
# }

# 5. GENERATE DOCUMENTATION
doc_generator = WorkflowDocumentationGenerator()
markdown_docs = doc_generator.generate_markdown_docs(workflow_spec)

# Write to docs/workflows/article_generator_v2.md
# Users can now read human-friendly behavior documentation!
```

## Benefits

### 1. Single Source of Truth
- BDD spec defines behavior once
- Used for generation, testing, documentation
- No duplication or drift between specs and tests

### 2. Self-Validating Workflows
- Every workflow carries its own behavioral contract
- Automatic integration testing after execution
- Catches regressions during evolution/optimization

### 3. Better Code Generation
- Structured, unambiguous requirements for LLM
- Clear success criteria
- Example scenarios guide implementation

### 4. Evolution Safety
- When optimizing code, BDD scenarios must still pass
- Prevents behavior changes during performance improvements
- Clear regression testing

### 5. Improved Portability
- Other systems can understand expected behavior
- Not just code - also guarantees
- Easier integration and troubleshooting

## Implementation Plan

### Phase 1: Core Data Structures
- [ ] Add `BDDSpecification` and `BDDScenario` dataclasses
- [ ] Extend `WorkflowSpec` with `bdd_specification` field
- [ ] Update `to_dict()` and `from_dict()` to serialize BDD specs
- [ ] Add `to_gherkin()` and `to_llm_prompt()` methods

### Phase 2: Code Generation Integration
- [ ] Update `OverseerLLM.create_execution_plan()` to accept BDD specs
- [ ] Implement `_build_bdd_planning_prompt()` method
- [ ] Update prompt templates to leverage structured BDD format
- [ ] Test generation quality with BDD vs. free-text specs

### Phase 3: Validation & Testing
- [ ] Create `BDDWorkflowValidator` class
- [ ] Implement scenario validation logic
- [ ] Add assertion pattern matching (at least, less than, contains, etc.)
- [ ] Integrate validation into workflow execution pipeline

### Phase 4: Documentation
- [ ] Create `WorkflowDocumentationGenerator`
- [ ] Auto-generate markdown docs from BDD specs
- [ ] Add CLI command to export workflow documentation
- [ ] Generate .feature files for pytest-bdd integration

### Phase 5: Optional - pytest-bdd Integration
- [ ] Add pytest-bdd dependency
- [ ] Generate runnable test files from BDD specs
- [ ] Create step definition templates
- [ ] Enable CI/CD testing of workflows

## Migration Strategy

### Backwards Compatibility
- `bdd_specification` is optional (`Optional[BDDSpecification]`)
- Existing workflows continue to work without changes
- Gradual migration: add BDD specs to new workflows first

### Hybrid Approach
- Support both text-based and BDD-based specifications
- OverseerLLM checks for BDD spec first, falls back to text
- Allows experimentation before full commitment

## Example CLI Usage

```bash
# Generate workflow from BDD specification
python chat_cli.py --bdd-spec article_workflow.feature --output article_workflow.json

# Validate workflow execution against BDD
python chat_cli.py --validate-bdd article_workflow.json --inputs '{"topic": "AI"}'

# Generate documentation from BDD specs
python chat_cli.py --generate-docs article_workflow.json --output docs/

# Run pytest-bdd tests
python chat_cli.py --export-tests article_workflow.json --test-output tests/
pytest tests/test_article_workflow.py
```

## Conclusion

Adding BDD specifications to WorkflowSpec creates a **self-documenting, self-testing, multi-purpose** artifact that serves as:
- Generation prompt
- Integration test
- Behavior documentation
- Evolution constraint
- Portability contract

This aligns perfectly with the existing architecture (declarative workflows, RAG storage, evolution-based optimization) while adding behavior guarantees that survive through optimization cycles.
