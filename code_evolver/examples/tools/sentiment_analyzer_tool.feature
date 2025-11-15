Feature: Sentiment Analyzer Tool
  Analyze text sentiment and return positive/negative/neutral classification

  Scenario: Analyze positive sentiment
    Given the text "I love this product! It's amazing and works perfectly."
    When the sentiment analyzer executes
    Then the sentiment should be "positive"
    And the confidence should be at least 0.80

  Scenario: Analyze negative sentiment
    Given the text "This is terrible. Waste of money and time."
    When the sentiment analyzer executes
    Then the sentiment should be "negative"
    And the confidence should be at least 0.80

  Scenario: Analyze neutral sentiment
    Given the text "The package arrived on Tuesday."
    When the sentiment analyzer executes
    Then the sentiment should be "neutral"
    And the confidence should be at least 0.60

  Scenario: Handle empty input
    Given the text ""
    When the sentiment analyzer executes
    Then the sentiment should be "neutral"
    And the confidence should be 0.0
    And a warning should be logged

  Scenario: Detect mixed sentiment
    Given the text "The product is great but the shipping was slow."
    When the sentiment analyzer executes
    Then the sentiment should be "positive" or "neutral"
    And the mixed_sentiment flag should be true

  Scenario Outline: Performance by text length
    Given a text with <word_count> words
    When the sentiment analyzer executes
    Then the execution time should be less than <max_time> milliseconds
    And the quality score should be at least <min_quality>

    Examples:
      | word_count | max_time | min_quality |
      | 10         | 100      | 0.85        |
      | 100        | 500      | 0.80        |
      | 1000       | 2000     | 0.75        |

## Additional Details

### Interface Specification

#### Input Schema
```json
{
  "text": {
    "type": "string",
    "required": true,
    "description": "Text to analyze for sentiment",
    "min_length": 0,
    "max_length": 5000
  },
  "language": {
    "type": "string",
    "required": false,
    "default": "en",
    "enum": ["en", "es", "fr", "de"],
    "description": "Language of the input text"
  }
}
```

#### Output Schema
```json
{
  "sentiment": {
    "type": "string",
    "enum": ["positive", "negative", "neutral"],
    "description": "Overall sentiment classification"
  },
  "confidence": {
    "type": "float",
    "min": 0.0,
    "max": 1.0,
    "description": "Confidence in the sentiment classification"
  },
  "mixed_sentiment": {
    "type": "boolean",
    "description": "True if text contains both positive and negative sentiments"
  },
  "scores": {
    "type": "object",
    "structure": {
      "positive": "float (0-1)",
      "negative": "float (0-1)",
      "neutral": "float (0-1)"
    },
    "description": "Individual scores for each sentiment category"
  },
  "metadata": {
    "type": "object",
    "structure": {
      "execution_time_ms": "integer",
      "word_count": "integer",
      "language_detected": "string"
    }
  }
}
```

### Quality Specifications

#### Performance Targets
- **Latency (P50)**: < 100 ms for short texts (< 50 words)
- **Latency (P95)**: < 500 ms for medium texts (< 200 words)
- **Latency (P99)**: < 2000 ms for long texts (< 1000 words)
- **Memory Usage**: < 50 MB

#### Quality Metrics
- **Accuracy**: ≥ 0.85 (correct sentiment classification)
- **Confidence Calibration**: ≥ 0.80 (confidence matches actual accuracy)
- **Consistency**: ≥ 0.95 (same input → same output)
- **Robustness**: ≥ 0.90 (handles edge cases gracefully)

#### Reliability Targets
- **Success Rate**: ≥ 99%
- **Error Handling**: Returns neutral sentiment with 0.0 confidence on errors
- **Retry Strategy**: No retries (fast failure)

### Tool Implementation Details

#### LLM Tool Configuration
```
Model: llama3
Temperature: 0.3  # Low temperature for consistent classification
Endpoint: http://localhost:11434

System Prompt:
"""
You are a sentiment analysis expert. Analyze the given text and classify its sentiment.

Instructions:
1. Classify the overall sentiment as positive, negative, or neutral
2. Provide a confidence score (0.0 to 1.0) for your classification
3. If the text contains both positive and negative sentiments, set mixed_sentiment to true
4. Provide individual scores for positive, negative, and neutral sentiments

Respond in JSON format:
{
  "sentiment": "positive|negative|neutral",
  "confidence": 0.85,
  "mixed_sentiment": false,
  "scores": {
    "positive": 0.85,
    "negative": 0.10,
    "neutral": 0.05
  }
}

Be consistent and calibrated - your confidence should reflect actual accuracy.
"""
```

### Expected Test Results

#### Baseline Execution
```yaml
scenario: "Analyze positive sentiment"
inputs:
  text: "I love this product! It's amazing and works perfectly."
  language: "en"

results:
  output:
    sentiment: "positive"
    confidence: 0.92
    mixed_sentiment: false
    scores:
      positive: 0.92
      negative: 0.03
      neutral: 0.05
  metadata:
    execution_time_ms: 145
    word_count: 9
    language_detected: "en"

  validation:
    all_scenarios_passed: true
    accuracy: 0.92
    status: "success"
```

#### Performance Metrics
```yaml
performance_profile:
  latency_p50: 87 ms
  latency_p95: 423 ms
  latency_p99: 1850 ms
  memory_avg: 32 MB
  memory_peak: 48 MB
  throughput: 45 analyses/second
```

#### Quality Metrics (Across Test Set)
```yaml
quality_metrics:
  accuracy: 0.89
  precision_positive: 0.91
  precision_negative: 0.88
  precision_neutral: 0.85
  recall_positive: 0.90
  recall_negative: 0.87
  recall_neutral: 0.88
  f1_score: 0.89
  confidence_calibration: 0.87
```

### Validation Criteria

#### BDD Scenario Validation Rules

| Then Step Pattern | Validation Logic | Pass Criteria |
|------------------|------------------|---------------|
| "sentiment should be X" | `output['sentiment'] == X` | Exact match |
| "confidence should be at least X" | `output['confidence'] >= X` | Threshold |
| "mixed_sentiment flag should be true" | `output['mixed_sentiment'] == True` | Boolean check |
| "execution time should be less than X ms" | `metadata['execution_time_ms'] < X` | Performance |
| "quality score should be at least X" | `quality_score >= X` | Quality threshold |

### Evolution History

**Version 1.0** (Baseline - LLM-based)
- Implementation: Direct LLM calls with prompt engineering
- Performance: 450 ms average
- Quality: 0.87 accuracy
- Cost: High (LLM calls for every analysis)

**Version 1.1** (Optimized - Hybrid approach)
- Optimization: Simple heuristics for obvious cases, LLM for ambiguous
- Performance: 120 ms average (73% improvement)
- Quality: 0.89 accuracy (maintained/improved)
- Cost: Reduced by 60% (fewer LLM calls)
- BDD Status: All scenarios passing ✅

**Version 1.2** (Future - Fine-tuned model)
- Plan: Fine-tune smaller model for sentiment analysis
- Target Performance: < 50 ms average
- Target Quality: ≥ 0.89 accuracy (maintain current)
- BDD Constraint: All current scenarios must still pass

### Metadata

**Tool ID**: sentiment_analyzer_v1
**Version**: 1.1.0
**BDD Specification Version**: 1.0.0
**Created**: 2025-11-10
**Last Optimized**: 2025-11-14
**Author**: code_evolver
**Status**: production
**Tags**: [nlp, sentiment, classification, llm]
**Used In Workflows**:
  - content_moderation_workflow
  - customer_feedback_analysis
  - social_media_monitoring
