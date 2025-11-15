# Hierarchical BDD for Safe Evolution

## Overview

The BDD system uses a **two-level hierarchy** that makes evolving code safer and easier:

1. **Tool-level BDD** (Unit contracts) - Individual tools carry their own behavioral guarantees
2. **Workflow-level BDD** (Integration contracts) - Workflows specify end-to-end behavior

This hierarchical approach means you can evolve tools independently without breaking workflows.

## The Evolution Problem

### Without BDD: Risky Optimization

```
Original Tool (Slow)
    ↓
  Optimize for speed
    ↓
Faster Tool (But does it still work correctly?)
    ↓
  Use in workflow
    ↓
Workflow breaks! (Discovered too late)
```

**Problems:**
- No guarantee tool still works after optimization
- Breaking changes discovered at workflow level
- Can't optimize tools independently
- Fear of making changes

### With BDD: Safe Optimization

```
Tool with BDD Spec (Behavioral contract)
    ↓
  Optimize for speed
    ↓
Run BDD tests against optimized tool
    ↓
All scenarios pass? → Accept optimization
Any scenario fails? → Reject optimization
    ↓
Guaranteed: Tool behavior preserved
    ↓
Use in workflow with confidence
    ↓
Workflow works! (Guaranteed by tool + workflow BDD)
```

**Benefits:**
- Tool behavior guaranteed after optimization
- Breaking changes caught immediately
- Tools can be evolved independently
- Confidence to make improvements

## Hierarchical BDD Architecture

### Level 1: Tool BDD (Unit Contracts)

Each tool has its own BDD specification:

```json
{
  "tool_id": "sentiment_analyzer",
  "name": "Sentiment Analyzer",
  "bdd_specification": {
    "feature": "Sentiment Analysis",
    "scenarios": [
      {
        "name": "Analyze positive sentiment",
        "given": ["text with positive sentiment"],
        "when": ["analyzer runs"],
        "then": ["sentiment should be positive", "confidence >= 0.80"]
      }
    ]
  },
  "source_code": "..."
}
```

### Level 2: Workflow BDD (Integration Contracts)

Workflows specify end-to-end behavior using tools:

```json
{
  "workflow_id": "content_moderation",
  "bdd_specification": {
    "feature": "Content Moderation",
    "scenarios": [
      {
        "name": "Flag toxic content",
        "given": ["user comment with toxic language"],
        "when": ["moderation workflow runs"],
        "then": [
          "sentiment should be analyzed",  // Uses sentiment_analyzer tool
          "toxicity should be detected",   // Uses toxicity_detector tool
          "comment should be flagged"
        ]
      }
    ]
  },
  "steps": [
    {"tool": "sentiment_analyzer", ...},
    {"tool": "toxicity_detector", ...}
  ]
}
```

### Combined Validation

```
User Input
    ↓
┌─────────────────────────────────────────┐
│  Workflow: content_moderation           │
│  ┌─────────────────────────────────┐   │
│  │ Step 1: sentiment_analyzer      │   │ ← Tool BDD validates this step
│  │ Tool BDD: ✅ All scenarios pass  │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ Step 2: toxicity_detector       │   │ ← Tool BDD validates this step
│  │ Tool BDD: ✅ All scenarios pass  │   │
│  └─────────────────────────────────┘   │
│  Workflow BDD: ✅ All scenarios pass    │ ← Workflow BDD validates end-to-end
└─────────────────────────────────────────┘
    ↓
Output (Guaranteed correct at both levels!)
```

## Evolution Scenarios

### Scenario 1: Optimizing a Single Tool

**Situation:** Sentiment analyzer is too slow (450ms), want to optimize to < 200ms

**With Tool-level BDD:**

```python
# Original tool with BDD spec
tool = ToolDefinition.from_json("sentiment_analyzer.json")
# Has scenarios: positive, negative, neutral, edge cases, performance

# Evolution cycle
optimizer = ToolOptimizer(tool)

# Try optimization approach 1: Hybrid heuristics + LLM
candidate_v1 = optimizer.generate_candidate(strategy="hybrid")
validation_v1 = validator.validate_tool(candidate_v1, tool.bdd_specification)

# Results:
# - Performance: 120ms ✅ (meets < 200ms target)
# - Scenario "Analyze positive sentiment": ✅ PASS
# - Scenario "Analyze negative sentiment": ✅ PASS
# - Scenario "Handle empty input": ❌ FAIL (returns error instead of neutral)
# - Decision: REJECT (BDD scenario failed)

# Try optimization approach 2: Fine-tuned smaller model
candidate_v2 = optimizer.generate_candidate(strategy="fine_tuned_model")
validation_v2 = validator.validate_tool(candidate_v2, tool.bdd_specification)

# Results:
# - Performance: 95ms ✅ (even better!)
# - All scenarios: ✅ PASS
# - Quality score: 0.91 ✅ (improved from 0.89)
# - Decision: ACCEPT ✅

# Save optimized tool
tool_v2 = candidate_v2
tool_v2.version = "1.2.0"
tool_v2.save("sentiment_analyzer_v1.2.json")
```

**Impact on Workflows:**

```python
# All workflows using sentiment_analyzer automatically benefit!
workflows_using_tool = [
    "content_moderation",
    "customer_feedback_analysis",
    "social_media_monitoring"
]

# Update workflows to use v1.2
for workflow_id in workflows_using_tool:
    workflow = WorkflowSpec.from_json(f"{workflow_id}.json")
    workflow.update_tool_version("sentiment_analyzer", "1.2.0")

    # Validate workflow still works with new tool version
    validation = validator.validate_workflow(workflow)

    # Results:
    # - Tool-level BDD: ✅ All scenarios pass (guaranteed by tool evolution)
    # - Workflow-level BDD: ✅ All scenarios pass (integration still works)
    # - Performance: Improved (faster tool = faster workflow)
    # - Decision: Deploy new version ✅
```

### Scenario 2: Adding a New Feature to a Tool

**Situation:** Want to add language detection to sentiment analyzer

**With Tool-level BDD:**

```gherkin
# Add new scenario to sentiment_analyzer.feature

Scenario: Detect language automatically
  Given text in Spanish "Me encanta este producto"
  When the sentiment analyzer executes
  Then the sentiment should be "positive"
  And the detected language should be "es"
  And the confidence should be at least 0.75
```

```python
# Update tool with new feature
tool = ToolDefinition.from_json("sentiment_analyzer.json")

# Add language detection capability
tool.add_capability("language_detection")

# Update BDD spec
new_scenario = BDDScenario(
    name="Detect language automatically",
    given=['text in Spanish "Me encanta este producto"'],
    when=["the sentiment analyzer executes"],
    then=[
        'sentiment should be "positive"',
        'detected language should be "es"',
        'confidence should be at least 0.75'
    ]
)
tool.bdd_specification.scenarios.append(new_scenario)

# Implement the feature
tool.source_code = updated_implementation

# Validate:
# - All OLD scenarios still pass ✅ (backward compatibility)
# - New scenario passes ✅ (new feature works)
# - Decision: Accept enhancement ✅

tool.version = "1.3.0"
tool.save()
```

**Workflows automatically get the new feature:**

```python
# Workflows using the tool now have language detection available
# No workflow changes needed - backward compatible
# Workflows can optionally use new detected_language field

# If a workflow wants to use the new feature:
workflow.add_step(
    WorkflowStep(
        step_id="language_routing",
        description="Route to language-specific handler",
        input_mapping={"language": "steps.sentiment.detected_language"},
        ...
    )
)
```

### Scenario 3: Replacing a Tool Implementation

**Situation:** Want to replace LLM-based sentiment analyzer with fine-tuned model

**With Tool-level BDD:**

```python
# Original: LLM-based (slow but accurate)
original_tool = ToolDefinition(
    tool_id="sentiment_analyzer",
    tool_type="llm",
    model="llama3",
    system_prompt="...",
    bdd_specification=existing_bdd_spec
)

# New: Fine-tuned model (fast and accurate)
new_tool = ToolDefinition(
    tool_id="sentiment_analyzer",
    tool_type="python",  # Changed implementation type!
    source_code=fine_tuned_model_code,
    bdd_specification=existing_bdd_spec  # SAME BDD SPEC
)

# Validation:
validator = BDDToolValidator()
results = validator.validate_tool(new_tool, existing_bdd_spec)

# Results:
# - Scenario "Analyze positive sentiment": ✅ PASS
# - Scenario "Analyze negative sentiment": ✅ PASS
# - Scenario "Handle empty input": ✅ PASS
# - Performance < 200ms: ✅ PASS
# - Quality >= 0.80: ✅ PASS (0.91 actual)

# Decision: Accept new implementation ✅
# Completely different implementation, same behavioral guarantee!

new_tool.version = "2.0.0"  # Major version (implementation changed)
new_tool.save()
```

**Workflows don't care about implementation:**

```python
# Workflows continue to work because behavioral contract is preserved
# Tool BDD ensures: same inputs → same quality outputs
# Implementation details (LLM vs fine-tuned model) are hidden

# Workflow just sees:
# - Faster execution (95ms vs 450ms)
# - Same or better quality
# - All workflow BDD scenarios still pass
```

## Benefits for Different Stakeholders

### For Tool Developers

```python
# You can optimize fearlessly
def optimize_tool(tool: ToolDefinition) -> ToolDefinition:
    """Optimize tool knowing BDD will catch any breaking changes"""

    # Try aggressive optimizations
    optimized = aggressive_optimization(tool)

    # BDD tests will catch problems
    if not all_bdd_scenarios_pass(optimized):
        # Roll back and try gentler approach
        optimized = conservative_optimization(tool)

    return optimized  # Guaranteed to work correctly
```

**Benefits:**
- Safe to experiment with optimizations
- Breaking changes caught immediately
- Can optimize without fear
- Quality guarantees preserved

### For Workflow Developers

```python
# You can use tools with confidence
def build_workflow(tool_registry: ToolRegistry) -> WorkflowSpec:
    """Build workflow knowing tools have behavioral guarantees"""

    # Use any tool from registry
    sentiment_tool = tool_registry.get("sentiment_analyzer")

    # Tool comes with BDD spec - you know exactly what it does
    print(sentiment_tool.bdd_specification.to_gherkin())

    # Build workflow using tool
    workflow = WorkflowSpec(...)
    workflow.add_step(use_tool=sentiment_tool)

    return workflow  # Tool behavior is guaranteed
```

**Benefits:**
- Tools come with clear behavioral contracts
- No surprises when tools are updated
- Can compose workflows confidently
- Integration issues caught early

### For System Maintainers

```python
# You can evolve the system safely
def update_system():
    """Update tools and workflows with confidence"""

    # Update a tool
    tool_v2 = optimize_tool(tool_v1)

    # Find affected workflows
    affected = find_workflows_using_tool(tool_v1.tool_id)

    # Validate each workflow with new tool
    for workflow in affected:
        # Both tool-level and workflow-level BDD are checked
        validation = validate_workflow_with_tool(workflow, tool_v2)

        if validation.passed:
            deploy_update(workflow, tool_v2)
        else:
            rollback(tool_v2)
            investigate(validation.failures)
```

**Benefits:**
- Safe system evolution
- Impact analysis automated
- Regression prevention
- Confident deployments

## Evolution Workflow Pattern

### Standard Evolution Cycle

```
1. SELECT tool or workflow to optimize
       ↓
2. IDENTIFY optimization target (speed, quality, cost)
       ↓
3. GENERATE candidate implementation
       ↓
4. VALIDATE against BDD specification
       ↓
   ┌───┴───┐
   ↓       ↓
 PASS    FAIL → Analyze failures → Adjust approach → Back to step 3
   ↓
5. ACCEPT optimization
       ↓
6. UPDATE version
       ↓
7. TEST affected workflows (if tool was optimized)
       ↓
8. DEPLOY
```

### Automated Evolution Pipeline

```yaml
# .github/workflows/tool-evolution.yml
name: Automated Tool Evolution

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly optimization attempt

jobs:
  evolve-tools:
    runs-on: ubuntu-latest

    steps:
      - name: Load tools
        run: |
          python -m code_evolver.scripts.load_tools \
            --registry tools/

      - name: Attempt optimization
        run: |
          # Try to optimize each tool
          python -m code_evolver.scripts.optimize_tools \
            --target speed \
            --preserve-bdd true

      - name: Validate with BDD
        run: |
          # Export BDD specs and run tests
          python -m code_evolver.scripts.export_tool_bdd_tests
          pytest tests/tools/ -v

      - name: Test affected workflows
        run: |
          # Find workflows using optimized tools
          # Run workflow-level BDD tests
          python -m code_evolver.scripts.test_affected_workflows

      - name: Create PR if successful
        if: success()
        run: |
          # Create PR with optimized tools
          gh pr create --title "Automated tool optimization" \
            --body "BDD-validated performance improvements"
```

## Key Insights

### 1. Independence

Tools can be evolved **independently** of workflows:
- Tool BDD ensures tool behavior is preserved
- Workflow BDD ensures integration still works
- No coupling between tool optimization and workflow changes

### 2. Composability

Tools with BDD specs are **composable building blocks**:
- Clear behavioral contracts
- Predictable behavior
- Safe to combine in workflows

### 3. Confidence

BDD provides **confidence at every level**:
- Tool level: Unit behavior guaranteed
- Workflow level: Integration behavior guaranteed
- System level: Complete system behavior guaranteed

### 4. Evolution Velocity

Hierarchical BDD **accelerates evolution**:
- Safe to optimize frequently
- Breaking changes caught immediately
- No fear of improvement
- Automated validation

## Summary

| Aspect | Without BDD | With Hierarchical BDD |
|--------|-------------|----------------------|
| **Tool Optimization** | Risky, manual testing | Safe, automated validation |
| **Workflow Impact** | Unknown until tested | Guaranteed compatible |
| **Evolution Speed** | Slow (fear of breaking) | Fast (confidence to change) |
| **Quality Assurance** | Manual, error-prone | Automated, reliable |
| **Regression Prevention** | Hope and pray | Provably prevented |
| **Team Confidence** | Low (afraid to change) | High (tests guarantee safety) |

**Bottom Line:** Tool-level + Workflow-level BDD creates a safety net that makes evolution not just possible, but **safe and fast**.
