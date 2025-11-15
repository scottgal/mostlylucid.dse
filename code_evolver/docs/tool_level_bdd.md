# Tool-Level BDD Specifications

## Overview

Individual tools can have their own BDD specifications, creating a **hierarchical testing approach**:

- **Tool-level BDD**: Unit-level behavioral contracts for individual tools
- **Workflow-level BDD**: Integration-level contracts for complete workflows

## Benefits for Evolution

When evolving/optimizing tools, the embedded BDD spec ensures:

✅ **Safe Optimization** - Tool behavior is preserved during performance improvements
✅ **Clear Contracts** - Each tool's expected behavior is documented
✅ **Independent Testing** - Tools can be tested in isolation before workflow integration
✅ **Reusability** - Tool carries its quality guarantee when reused across workflows
✅ **Regression Prevention** - Can't accidentally break tool behavior during evolution

## Enhanced ToolDefinition Structure

```python
@dataclass
class ToolDefinition:
    """Definition of a tool with optional BDD specification"""
    tool_id: str
    name: str
    description: str
    tool_type: str  # "llm", "python", "api", "executable"

    # Existing fields...
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    source_code: Optional[str] = None

    # NEW: BDD specification for tool behavior
    bdd_specification: Optional[BDDSpecification] = None
    bdd_enabled: bool = False  # Whether to validate tool execution against BDD

    # Execution conditions
    retry_on_failure: bool = False
    timeout: int = 300
```

## Tool BDD Specification Format

### Simple Tool Example: String Transformer

```gherkin
Feature: Text Case Converter
  Convert text between different cases

  Scenario: Convert to uppercase
    Given the input text "hello world"
    When the converter transforms to uppercase
    Then the output should be "HELLO WORLD"

  Scenario: Convert to title case
    Given the input text "hello world from python"
    When the converter transforms to title case
    Then the output should be "Hello World From Python"

  Scenario: Handle empty input
    Given the input text ""
    When the converter transforms to uppercase
    Then the output should be ""
    And no error should be raised

  Scenario: Performance constraint
    Given the input text with 10000 characters
    When the converter transforms to uppercase
    Then the execution time should be less than 100 milliseconds
    And the memory usage should be less than 10 MB

## Additional Details

### Interface Specification

#### Input Schema
```json
{
  "text": {
    "type": "string",
    "required": true
  },
  "target_case": {
    "type": "string",
    "enum": ["upper", "lower", "title", "camel"],
    "required": true
  }
}
```

#### Output Schema
```json
{
  "transformed_text": {
    "type": "string"
  },
  "original_length": {
    "type": "integer"
  },
  "execution_time_ms": {
    "type": "integer"
  }
}
```

### Quality Specifications

- **Accuracy**: 100% (deterministic transformation)
- **Latency**: < 100ms for strings up to 10K characters
- **Memory**: < 10 MB
- **Character Preservation**: All characters preserved (only case changes)

### Test Results

```yaml
scenario: "Convert to uppercase"
inputs:
  text: "hello world"
  target_case: "upper"
results:
  transformed_text: "HELLO WORLD"
  execution_time_ms: 2
  status: PASS
```
```

### Complex Tool Example: LLM Content Generator

```gherkin
Feature: Article Outline Generator
  Generate structured article outlines from topics

  Scenario: Generate outline for technical topic
    Given a topic "Machine Learning Basics"
    And a complexity level "intermediate"
    When the outline generator runs
    Then an outline should be produced
    And the outline should have at least 3 sections
    And each section should have a title
    And each section should have at least 2 key points
    And the outline should be relevant to the topic

  Scenario: Generate outline for simple topic
    Given a topic "Healthy Eating Tips"
    And a complexity level "basic"
    When the outline generator runs
    Then an outline should be produced
    And the outline should have at least 3 sections
    And the language should be accessible to general audience

  Scenario: Handle vague topic gracefully
    Given a topic "stuff"
    And a complexity level "intermediate"
    When the outline generator runs
    Then an outline should be produced
    And a warning should be logged about topic vagueness
    And the outline should request topic clarification

  Scenario Outline: Performance by complexity
    Given a topic "Technology Trends"
    And a complexity level "<complexity>"
    When the outline generator runs
    Then the execution time should be less than <max_time> seconds
    And the quality score should be at least <min_quality>

    Examples:
      | complexity   | max_time | min_quality |
      | basic        | 10       | 0.75        |
      | intermediate | 15       | 0.80        |
      | expert       | 25       | 0.85        |

## Additional Details

### Interface Specification

#### Input Schema
```json
{
  "topic": {
    "type": "string",
    "required": true,
    "min_length": 3,
    "max_length": 200
  },
  "complexity": {
    "type": "string",
    "enum": ["basic", "intermediate", "expert"],
    "default": "intermediate"
  },
  "min_sections": {
    "type": "integer",
    "default": 3,
    "min": 2,
    "max": 10
  }
}
```

#### Output Schema
```json
{
  "outline": {
    "type": "object",
    "structure": {
      "topic": "string",
      "sections": [
        {
          "title": "string",
          "key_points": ["string"],
          "estimated_words": "integer"
        }
      ],
      "total_sections": "integer",
      "complexity_level": "string"
    }
  },
  "metadata": {
    "quality_score": "float (0-1)",
    "execution_time_ms": "integer",
    "model_used": "string"
  }
}
```

### Quality Specifications

- **Relevance Score**: ≥ 0.80 (outline matches topic)
- **Completeness**: 100% (all required fields present)
- **Section Quality**: ≥ 0.75 per section
- **Coherence**: ≥ 0.85 (sections flow logically)
- **Latency (P95)**: < 20 seconds
- **Success Rate**: ≥ 95%

### Tool Implementation

```python
# LLM system prompt
system_prompt = '''You are an expert outline generator. Given a topic and complexity level, generate a well-structured article outline.

Requirements:
- Generate {min_sections} or more sections
- Each section must have a clear title
- Each section must have 2-5 key points
- Tailor complexity to the specified audience level
- Ensure logical flow between sections

Output JSON format:
{
  "sections": [
    {
      "title": "Section Title",
      "key_points": ["Point 1", "Point 2"],
      "estimated_words": 300
    }
  ]
}
'''
```

### Test Results

```yaml
scenario: "Generate outline for technical topic"
inputs:
  topic: "Machine Learning Basics"
  complexity: "intermediate"

results:
  outline:
    topic: "Machine Learning Basics"
    sections:
      - title: "Introduction to Machine Learning"
        key_points:
          - "Definition and core concepts"
          - "Types of ML: supervised, unsupervised, reinforcement"
        estimated_words: 350
      - title: "Common Algorithms"
        key_points:
          - "Linear regression and decision trees"
          - "Neural networks basics"
        estimated_words: 400
      - title: "Practical Applications"
        key_points:
          - "Real-world use cases"
          - "Getting started with ML projects"
        estimated_words: 350
    total_sections: 3
    complexity_level: "intermediate"

  metadata:
    quality_score: 0.87
    execution_time_ms: 8450
    model_used: "llama3"

  validation:
    all_scenarios_passed: true
    relevance_score: 0.89
    section_quality_avg: 0.86
```
```

## Hierarchical Testing: Tool + Workflow BDD

### Tool BDD (Unit Level)

```gherkin
Feature: Translator Tool
  Translate text between languages

  Scenario: Translate English to Spanish
    Given English text "Hello, world!"
    And target language "Spanish"
    When the translator runs
    Then the output should be "¡Hola, mundo!"
    And the translation quality should be at least 0.90
```

### Workflow BDD (Integration Level)

```gherkin
Feature: Multi-language Article Generator
  Generate articles with translations

  Scenario: Generate article with translation
    Given a topic "AI Ethics"
    And a target language "Spanish"
    When the workflow executes
    Then an article should be generated
    And a translation should be produced
    And both article and translation should be coherent
    # Note: This uses the Translator tool internally
    # The tool's BDD spec ensures translation quality
```

### Combined Validation

```python
# When workflow executes:

# 1. Tool-level validation happens automatically
translator_tool.execute(
    inputs={"text": article, "target_language": "Spanish"},
    validate_bdd=True  # Validates against tool's BDD spec
)
# → Ensures translation quality ≥ 0.90 (tool-level requirement)

# 2. Workflow-level validation
workflow.execute(
    inputs={"topic": "AI Ethics", "language": "Spanish"},
    validate_bdd=True  # Validates against workflow's BDD spec
)
# → Ensures article + translation coherence (integration requirement)

# Result: Both unit and integration contracts are enforced!
```

## Tool Evolution with BDD

### Before: Risky Optimization

```python
# Original tool (slow but correct)
def translate(text, target_language):
    # Works but takes 15 seconds
    return slow_but_accurate_translation(text, target_language)

# Optimization attempt (fast but might break behavior)
def translate_optimized(text, target_language):
    # Only takes 3 seconds - but does it still work correctly?
    return fast_translation(text, target_language)

# Problem: How do we know it still works correctly?
```

### After: Safe Optimization with BDD

```python
# Tool has embedded BDD spec
tool_def = ToolDefinition(
    tool_id="translator",
    name="Text Translator",
    bdd_specification=BDDSpecification.from_file("translator.feature"),
    bdd_enabled=True,
    source_code=translate_code
)

# Evolution cycle
optimizer = ToolOptimizer(tool_def)

# Optimize for speed while preserving behavior
optimized_tool = optimizer.optimize(
    target_metric="speed",
    preserve_bdd=True  # CRITICAL: Must pass all BDD scenarios
)

# During optimization:
# 1. Generate faster implementation
# 2. Test against BDD scenarios
# 3. If any scenario fails → reject optimization
# 4. If all pass → accept optimization

# Result: 3-second translation that provably maintains quality!
```

### Evolution Cycle with BDD Validation

```
┌─────────────────────────────────────────────────────────────┐
│  Tool Definition (v1.0)                                     │
│  - source_code: original implementation                     │
│  - bdd_specification: behavioral contract                   │
│  - execution_time: 15s                                      │
│  - quality_score: 0.92                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   Optimize   │
                  │  for Speed   │
                  └──────┬───────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  Generate Candidate    │
            │  Implementation        │
            │  (faster code)         │
            └────────┬───────────────┘
                     │
                     ▼
            ┌────────────────────────┐
            │  Execute BDD Tests     │
            │  Against Candidate     │
            └────────┬───────────────┘
                     │
            ┌────────┴────────┐
            │                 │
            ▼                 ▼
     ┌──────────┐      ┌──────────┐
     │ All Pass │      │ Any Fail │
     └─────┬────┘      └─────┬────┘
           │                 │
           │                 ▼
           │         ┌───────────────┐
           │         │ Reject        │
           │         │ Keep Original │
           │         └───────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│  Tool Definition (v1.1)                                  │
│  - source_code: optimized implementation                 │
│  - bdd_specification: SAME behavioral contract           │
│  - execution_time: 3s  ← IMPROVED                        │
│  - quality_score: 0.93 ← MAINTAINED/IMPROVED             │
│  - all_bdd_scenarios_passed: true ← GUARANTEED           │
└──────────────────────────────────────────────────────────┘
```

## Tool BDD Storage Format

Tools with BDD specs are stored in JSON:

```json
{
  "tool_id": "text_translator",
  "name": "Text Translator",
  "description": "Translates text between languages",
  "tool_type": "llm",
  "model": "llama3",
  "system_prompt": "You are an expert translator...",

  "bdd_specification": {
    "feature": "Text Translation Tool",
    "scenarios": [
      {
        "name": "Translate English to Spanish",
        "given": [
          "English text \"Hello, world!\"",
          "target language \"Spanish\""
        ],
        "when": [
          "the translator runs"
        ],
        "then": [
          "the output should be \"¡Hola, mundo!\"",
          "the translation quality should be at least 0.90"
        ]
      }
    ]
  },

  "bdd_enabled": true,

  "timeout": 30,
  "retry_on_failure": true
}
```

## CI/CD: Tool-Level Testing

```yaml
# .github/workflows/test-tools.yml
name: Test Individual Tools

on: [push, pull_request]

jobs:
  test-tools:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Install dependencies
        run: |
          pip install pytest pytest-bdd
          pip install -r requirements.txt

      - name: Export tool BDD specs
        run: |
          # Export BDD specs from all tools
          python -m code_evolver.scripts.export_tool_bdd_tests \
            --tools tools/*.json \
            --output tests/tools/

      - name: Run tool-level BDD tests
        run: |
          pytest tests/tools/ -v --tb=short

      - name: Report tool quality
        run: |
          python -m code_evolver.scripts.tool_quality_report \
            --test-results test-results/
```

## Best Practices

### ✅ DO:

1. **Add BDD to reusable tools** - Tools used across multiple workflows benefit most
2. **Test edge cases** - Empty inputs, malformed data, boundary conditions
3. **Specify performance** - Include latency/quality thresholds
4. **Test in isolation** - Tool BDD should not depend on workflow context
5. **Version with tool** - BDD spec version should match tool version

### ❌ DON'T:

1. **Skip BDD for simple tools** - It's optional, use judgment
2. **Test implementation details** - Focus on input/output behavior
3. **Make scenarios depend on each other** - Keep them independent
4. **Forget quality metrics** - Always specify acceptable quality levels
5. **Over-specify** - Don't constrain implementation unnecessarily

## Summary

Tool-level BDD specifications enable:

| Benefit | How It Helps |
|---------|-------------|
| **Safe Evolution** | Can't break tool behavior during optimization |
| **Reusability** | Tool carries quality guarantee across workflows |
| **Independent Testing** | Test tools before workflow integration |
| **Clear Contracts** | Documents expected behavior for each tool |
| **Regression Prevention** | Changes must preserve BDD scenarios |
| **Hierarchical Quality** | Tool quality + workflow quality = total quality |

**Key Insight**: Tools with BDD specs can be evolved independently and safely. When used in workflows, both tool-level and workflow-level contracts are enforced, creating a comprehensive quality guarantee.
