Feature: Multi-step Article Generation with Translation
  As a content creator
  I want to generate well-structured articles with translations
  So that I can produce multilingual content efficiently

  Background:
    Given the workflow has access to outline_generator tool
    And the workflow has access to article_writer tool
    And the workflow has access to translator tool

  Scenario: Generate article with Spanish translation
    Given a topic "AI in Healthcare"
    And a target language "Spanish"
    When the workflow executes
    Then an outline should be generated with at least 3 sections
    And the outline should include section titles and key points
    And an article should be written based on the outline
    And the article should be at least 500 words
    And the article should reference all outline sections
    And a translation should be produced in Spanish
    And the translation should preserve the article structure
    And the translation should maintain technical terminology accuracy

  Scenario: Generate article without translation
    Given a topic "Climate Change Solutions"
    And no target language is specified
    When the workflow executes
    Then an outline should be generated with at least 3 sections
    And an article should be written based on the outline
    And the article should be at least 500 words
    And no translation step should execute
    And the workflow should complete successfully

  Scenario: Handle complex technical topic
    Given a topic "Quantum Computing Algorithms"
    And a target language "German"
    And a complexity level "expert"
    When the workflow executes
    Then an outline should be generated with at least 5 sections
    And the outline should include technical depth markers
    And an article should be written with technical accuracy
    And the article should be at least 1000 words
    And the article should include code examples or diagrams
    And a translation should preserve technical terminology
    And the translation should include German equivalents for key terms

  Scenario Outline: Performance constraints by topic complexity
    Given a topic "<topic>"
    And a complexity level "<complexity>"
    When the workflow executes
    Then the total execution time should be less than <max_time> seconds
    And the memory usage should be less than <max_memory> MB
    And the quality score should be at least <min_quality>

    Examples:
      | topic                  | complexity | max_time | max_memory | min_quality |
      | Simple Tech Topic      | basic      | 30       | 512        | 0.80        |
      | Complex Research Topic | expert     | 90       | 1024       | 0.85        |
      | Medium Analysis        | intermediate| 60      | 768        | 0.82        |

  Scenario: Recover from translation service failure
    Given a topic "Machine Learning Basics"
    And a target language "French"
    And the translator tool is unavailable
    When the workflow executes
    Then an outline should be generated
    And an article should be written
    And the workflow should log a translation failure
    And the workflow should return the English article
    And the workflow should complete with partial success status

## Additional Workflow Details

### Interface Specifications

#### Input Schema
```json
{
  "topic": {
    "type": "string",
    "required": true,
    "description": "The main topic for article generation",
    "min_length": 5,
    "max_length": 200
  },
  "target_language": {
    "type": "string",
    "required": false,
    "enum": ["Spanish", "French", "German", "Italian", "Portuguese"],
    "description": "Target language for translation. If omitted, no translation occurs."
  },
  "complexity": {
    "type": "string",
    "required": false,
    "default": "intermediate",
    "enum": ["basic", "intermediate", "expert"],
    "description": "Target audience complexity level"
  },
  "min_word_count": {
    "type": "integer",
    "required": false,
    "default": 500,
    "min": 200,
    "max": 5000,
    "description": "Minimum word count for generated article"
  }
}
```

#### Output Schema
```json
{
  "outline": {
    "type": "object",
    "structure": {
      "sections": [
        {
          "title": "string",
          "key_points": ["string"],
          "estimated_words": "integer"
        }
      ],
      "total_sections": "integer"
    }
  },
  "article": {
    "type": "object",
    "structure": {
      "title": "string",
      "content": "string",
      "word_count": "integer",
      "sections": ["string"],
      "metadata": {
        "complexity_level": "string",
        "reading_time_minutes": "integer"
      }
    }
  },
  "translation": {
    "type": "object",
    "required": false,
    "structure": {
      "language": "string",
      "translated_content": "string",
      "word_count": "integer",
      "terminology_glossary": {
        "english_term": "translated_term"
      }
    }
  },
  "execution_metadata": {
    "type": "object",
    "structure": {
      "status": "string (success|partial_success|failure)",
      "execution_time_ms": "integer",
      "memory_used_mb": "integer",
      "steps_completed": "integer",
      "steps_failed": "integer"
    }
  }
}
```

#### Tool Signatures

**outline_generator**
```python
def generate_outline(
    topic: str,
    complexity: str = "intermediate",
    min_sections: int = 3
) -> dict:
    """
    Generate structured outline for article.

    Returns:
        {
            "sections": [{"title": str, "key_points": [str]}],
            "total_sections": int
        }
    """
```

**article_writer**
```python
def write_article(
    topic: str,
    outline: dict,
    min_words: int = 500,
    complexity: str = "intermediate"
) -> dict:
    """
    Write article based on outline.

    Returns:
        {
            "title": str,
            "content": str,
            "word_count": int,
            "sections": [str]
        }
    """
```

**translator**
```python
def translate_article(
    article: dict,
    target_language: str,
    preserve_structure: bool = True
) -> dict:
    """
    Translate article to target language.

    Returns:
        {
            "language": str,
            "translated_content": str,
            "word_count": int,
            "terminology_glossary": dict
        }
    """
```

### Quality Specifications

#### Performance Targets
- **Latency (P95)**: < 60 seconds for intermediate complexity
- **Latency (P99)**: < 90 seconds for expert complexity
- **Memory Usage**: < 768 MB average, < 1024 MB peak
- **Throughput**: Minimum 10 articles per hour under sustained load

#### Quality Metrics
- **Content Quality Score**: ≥ 0.80 (measured by evaluator LLM)
- **Outline Coherence**: ≥ 0.85 (section relevance to topic)
- **Article Completeness**: 100% of outline sections covered
- **Translation Accuracy**: ≥ 0.90 (for supported languages)
- **Terminology Consistency**: ≥ 0.95 (technical term preservation)

#### Reliability Targets
- **Success Rate**: ≥ 95% for standard inputs
- **Partial Success Rate**: ≥ 99% (at least outline + article)
- **Graceful Degradation**: 100% (never fail completely, return partial results)
- **Recovery from Tool Failures**: Automatic retry with exponential backoff (max 3 attempts)

### Workflow Step Dependencies

```
┌─────────────────┐
│  Input: topic   │
│  + complexity   │
│  + language     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Step 1: Generate       │
│  Outline                │
│  Tool: outline_generator│
│  Timeout: 15s           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Step 2: Write Article  │
│  Tool: article_writer   │
│  Inputs: topic, outline │
│  Timeout: 45s           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Step 3: Translate      │
│  Tool: translator       │
│  Inputs: article, lang  │
│  Timeout: 30s           │
│  Conditional: if lang   │
│  On failure: continue   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Output: article +      │
│  translation (optional) │
└─────────────────────────┘
```

### Expected Test Results

#### Baseline Execution (from initial generation)
```yaml
test_case: "Generate article with Spanish translation"
inputs:
  topic: "AI in Healthcare"
  target_language: "Spanish"
  complexity: "intermediate"

actual_results:
  execution_time_ms: 42350
  memory_used_mb: 645
  quality_score: 0.87

  outline:
    sections_generated: 4
    coherence_score: 0.91

  article:
    word_count: 782
    completeness: 1.0  # All outline sections covered
    readability_score: 0.84

  translation:
    accuracy_score: 0.93
    terminology_preservation: 0.96

  status: "success"
  all_scenarios_passed: true
```

#### Performance Comparison (after optimization)
```yaml
optimization_cycle: 3
test_case: "Generate article with Spanish translation"

baseline:
  execution_time_ms: 42350
  memory_used_mb: 645
  quality_score: 0.87

optimized:
  execution_time_ms: 28200  # 33% improvement
  memory_used_mb: 520       # 19% improvement
  quality_score: 0.88       # Maintained/improved

  improvements:
    - Parallel outline + article planning
    - Cached translation terminology
    - Optimized prompt templates

  scenarios_status:
    "Generate article with Spanish translation": PASS
    "Performance constraints by topic complexity": PASS (28s < 30s limit)
    "Handle complex technical topic": PASS

  regression_tests:
    all_passed: true
    behavior_preserved: true
```

#### Edge Case Handling
```yaml
test_case: "Recover from translation service failure"

simulated_failure:
  translator_tool: "unavailable"

actual_results:
  status: "partial_success"
  execution_time_ms: 35100

  completed_steps:
    - outline_generation: SUCCESS
    - article_writing: SUCCESS
    - translation: FAILED (service unavailable)

  error_handling:
    logged_error: true
    returned_fallback: true  # English article returned
    user_notified: true

  graceful_degradation: PASS
  scenario_validation: PASS
```

### Validation Criteria

#### BDD Scenario Validation Rules

Each scenario "Then" step maps to specific validation logic:

| Then Step Pattern | Validation Logic | Pass Criteria |
|------------------|------------------|---------------|
| "outline should be generated with at least N sections" | `len(output['outline']['sections']) >= N` | Count check |
| "article should be at least N words" | `output['article']['word_count'] >= N` | Numeric comparison |
| "translation should be produced in X" | `output['translation']['language'] == X` | String equality |
| "execution time should be less than N seconds" | `metadata['execution_time_ms'] < N * 1000` | Performance check |
| "quality score should be at least N" | `metadata['quality_score'] >= N` | Quality threshold |
| "should preserve structure" | `compare_structure(original, translated)` | Structural analysis |

#### Continuous Validation

During evolution/optimization cycles:
1. **Pre-execution**: Validate inputs against schema
2. **Post-execution**: Run all BDD scenarios against results
3. **Regression check**: Compare with baseline quality metrics
4. **Performance tracking**: Log execution metadata for trending

#### Acceptance Criteria

A workflow implementation is considered valid if:
- ✅ All BDD scenarios pass (100%)
- ✅ Quality score ≥ minimum specified in scenarios
- ✅ Performance within constraints (execution time, memory)
- ✅ No regressions from baseline (quality maintained or improved)
- ✅ Error handling scenarios pass (graceful degradation)

### Metadata

**Workflow Version**: 2.1.0
**BDD Specification Version**: 1.0.0
**Created**: 2025-11-15
**Last Validated**: 2025-11-15
**Validation Status**: ✅ All scenarios passing
**Performance Tier**: Production-ready
**Optimization Cycles Completed**: 3
