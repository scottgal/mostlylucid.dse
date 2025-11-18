# Statistical Analysis Tool

Comprehensive statistical analysis capabilities for data-driven code evolution and pattern validation.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Analysis Types](#analysis-types)
- [Common Prompts](#common-prompts)
- [Integration Examples](#integration-examples)
- [Best Practices](#best-practices)
- [Use Cases](#use-cases)

## Overview

The Statistical Analysis tool provides rigorous statistical methods to complement the pattern recognition system. It enables data-driven decision making, pattern validation, and anomaly detection across your codebase.

### Key Features

- **Descriptive Statistics**: Comprehensive data summaries with 20+ metrics
- **Hypothesis Testing**: 6 different statistical tests for validating patterns
- **Correlation Analysis**: Find relationships between variables
- **Regression Analysis**: Model trends and make predictions
- **Outlier Detection**: Identify anomalous patterns (3 methods)
- **Clustering**: Group similar patterns (3 algorithms)
- **Comparative Analysis**: Statistical comparison of multiple datasets

### Complements Pattern Recognition

While the pattern recognition tool finds and applies code fix patterns, the statistical analysis tool:
- Validates whether fixes are statistically effective
- Detects anomalous error patterns
- Identifies correlations between code metrics
- Clusters similar error types for better organization
- Provides confidence intervals for pattern effectiveness

## Quick Start

### Basic Descriptive Statistics

```bash
echo '{
  "analysis_type": "descriptive",
  "data": [23, 45, 67, 89, 34, 56, 78, 90, 12, 45]
}' | python tools/executable/statistical_analysis.py
```

**Output:**
```json
{
  "success": true,
  "statistics": {
    "count": 10,
    "mean": 53.9,
    "median": 50.5,
    "mode": 45.0,
    "std": 25.18,
    "variance": 634.10,
    "min": 12,
    "max": 90,
    "range": 78,
    "q1": 34.75,
    "q3": 74.25,
    "iqr": 39.5,
    "skewness": -0.35,
    "kurtosis": -0.89,
    "cv": 0.47
  }
}
```

### Compare Two Datasets

```bash
echo '{
  "analysis_type": "hypothesis_test",
  "data1": [23, 45, 67, 89, 34],
  "data2": [56, 78, 90, 12, 45],
  "test_type": "ttest"
}' | python tools/executable/statistical_analysis.py
```

## Analysis Types

### 1. Descriptive Statistics

**Purpose**: Understand data distribution and central tendencies

**Metrics Provided**:
- Central tendency: mean, median, mode
- Dispersion: std, variance, range, IQR, CV
- Shape: skewness, kurtosis
- Percentiles: 10th, 25th, 50th, 75th, 90th, 95th, 99th

**Parameters**:
- `data`: Single array or array of arrays
- `labels`: Optional names for each dataset

**Example**:
```json
{
  "analysis_type": "descriptive",
  "data": [
    [12, 15, 18, 20, 22],
    [45, 48, 50, 52, 55]
  ],
  "labels": ["Before Fix", "After Fix"]
}
```

### 2. Hypothesis Testing

**Purpose**: Test statistical significance of differences

**Available Tests**:

#### Independent t-test
Compare means of two independent groups
```json
{
  "analysis_type": "hypothesis_test",
  "data1": [error_counts_before],
  "data2": [error_counts_after],
  "test_type": "ttest",
  "alpha": 0.05
}
```

#### Paired t-test
Compare means of paired observations
```json
{
  "analysis_type": "hypothesis_test",
  "data1": [performance_before],
  "data2": [performance_after],
  "test_type": "paired_ttest"
}
```

#### Mann-Whitney U test
Non-parametric alternative to t-test
```json
{
  "analysis_type": "hypothesis_test",
  "data1": [dataset1],
  "data2": [dataset2],
  "test_type": "mann_whitney"
}
```

#### Wilcoxon Signed-Rank
Non-parametric alternative to paired t-test
```json
{
  "analysis_type": "hypothesis_test",
  "data1": [paired_before],
  "data2": [paired_after],
  "test_type": "wilcoxon"
}
```

#### Kolmogorov-Smirnov Test
Test if two samples come from same distribution
```json
{
  "analysis_type": "hypothesis_test",
  "data1": [distribution1],
  "data2": [distribution2],
  "test_type": "ks_test"
}
```

#### Shapiro-Wilk Test
Test normality of data
```json
{
  "analysis_type": "hypothesis_test",
  "data1": [your_data],
  "test_type": "shapiro"
}
```

### 3. Correlation Analysis

**Purpose**: Measure strength and direction of relationships

**Methods**:

#### Pearson Correlation
Linear correlation (assumes normality)
```json
{
  "analysis_type": "correlation",
  "data1": [code_complexity],
  "data2": [bug_count],
  "method": "pearson"
}
```

#### Spearman Correlation
Rank-based (non-parametric)
```json
{
  "analysis_type": "correlation",
  "data1": [lines_of_code],
  "data2": [maintenance_time],
  "method": "spearman"
}
```

#### Kendall Tau
Rank correlation (robust to outliers)
```json
{
  "analysis_type": "correlation",
  "data1": [cyclomatic_complexity],
  "data2": [test_coverage],
  "method": "kendall"
}
```

**Output Interpretation**:
- Correlation: -1 (perfect negative) to +1 (perfect positive)
- Strength: very weak (<0.3), weak (0.3-0.5), moderate (0.5-0.7), strong (0.7-0.9), very strong (>0.9)
- p-value: < 0.05 indicates significant correlation

### 4. Regression Analysis

**Purpose**: Model relationships and make predictions

#### Linear Regression
```json
{
  "analysis_type": "regression",
  "x_data": [1, 2, 3, 4, 5],
  "y_data": [2.1, 4.2, 5.9, 8.1, 10.2],
  "regression_type": "linear"
}
```

**Returns**:
- Coefficients (slope, intercept)
- R² (goodness of fit)
- Adjusted R²
- MSE, RMSE, MAE
- Predictions

#### Polynomial Regression
```json
{
  "analysis_type": "regression",
  "x_data": [1, 2, 3, 4, 5],
  "y_data": [1, 4, 9, 16, 25],
  "regression_type": "polynomial_2"
}
```

### 5. Outlier Detection

**Purpose**: Identify anomalous data points

#### IQR Method
Traditional box plot method
```json
{
  "analysis_type": "outliers",
  "data": [23, 45, 67, 89, 34, 56, 78, 90, 12, 450],
  "method": "iqr",
  "threshold": 1.5
}
```
- Threshold 1.5 = standard outliers
- Threshold 3.0 = extreme outliers

#### Z-Score Method
Standard deviations from mean
```json
{
  "analysis_type": "outliers",
  "data": [23, 45, 67, 89, 34, 56, 78, 90, 12, 450],
  "method": "zscore",
  "threshold": 3
}
```
- Threshold 2 = moderate
- Threshold 3 = standard (99.7% rule)

#### Isolation Forest
ML-based anomaly detection
```json
{
  "analysis_type": "outliers",
  "data": [23, 45, 67, 89, 34, 56, 78, 90, 12, 450],
  "method": "isolation_forest",
  "threshold": 0.1
}
```
- Threshold = contamination rate (expected % of outliers)

### 6. Clustering Analysis

**Purpose**: Group similar data points

#### K-Means Clustering
```json
{
  "analysis_type": "clustering",
  "data": [[1, 2], [1.5, 1.8], [5, 8], [8, 8], [1, 0.6], [9, 11]],
  "n_clusters": 2,
  "method": "kmeans"
}
```

#### DBSCAN
Density-based clustering (finds arbitrary shapes)
```json
{
  "analysis_type": "clustering",
  "data": [[1, 2], [1.5, 1.8], [5, 8], [8, 8], [1, 0.6], [9, 11]],
  "method": "dbscan"
}
```

#### Hierarchical Clustering
```json
{
  "analysis_type": "clustering",
  "data": [[1, 2], [1.5, 1.8], [5, 8], [8, 8], [1, 0.6], [9, 11]],
  "n_clusters": 3,
  "method": "hierarchical"
}
```

### 7. Comparative Analysis

**Purpose**: Compare multiple datasets statistically

```json
{
  "analysis_type": "comparative",
  "datasets": [
    [23, 45, 67, 89, 34],
    [56, 78, 90, 12, 45],
    [34, 56, 78, 90, 23]
  ],
  "labels": ["Tool A", "Tool B", "Tool C"]
}
```

**Returns**:
- Descriptive stats for each dataset
- ANOVA (parametric) or t-test for 2 groups
- Kruskal-Wallis (non-parametric)
- Significance testing

## Common Prompts

### Data Quality Analysis

**Prompt**: "Analyze the distribution of error counts across all tools and identify any outliers"

```json
{
  "analysis_type": "descriptive",
  "data": [12, 15, 13, 14, 16, 89, 15, 14, 13, 15]
}
```

Then:
```json
{
  "analysis_type": "outliers",
  "data": [12, 15, 13, 14, 16, 89, 15, 14, 13, 15],
  "method": "iqr"
}
```

### Pattern Effectiveness Validation

**Prompt**: "Test whether applying this fix pattern actually reduces error rates"

```json
{
  "analysis_type": "hypothesis_test",
  "data1": [45, 48, 50, 47, 49],
  "data2": [12, 15, 13, 14, 16],
  "test_type": "ttest",
  "alpha": 0.05
}
```

**Interpretation**: If p-value < 0.05, the fix is statistically effective!

### Performance Regression Detection

**Prompt**: "Did the latest code change cause a statistically significant performance regression?"

```json
{
  "analysis_type": "hypothesis_test",
  "data1": [120, 125, 118, 122, 119],
  "data2": [145, 150, 148, 152, 147],
  "test_type": "mann_whitney"
}
```

### Code Complexity Correlation

**Prompt**: "Is there a correlation between cyclomatic complexity and bug count?"

```json
{
  "analysis_type": "correlation",
  "data1": [5, 12, 8, 15, 20, 25, 10, 18],
  "data2": [2, 5, 3, 8, 12, 15, 4, 10],
  "method": "spearman"
}
```

### Error Pattern Clustering

**Prompt**: "Cluster similar error types based on their characteristics"

```json
{
  "analysis_type": "clustering",
  "data": [
    [10, 2],
    [15, 3],
    [100, 5],
    [95, 4],
    [12, 2],
    [105, 6]
  ],
  "n_clusters": 2,
  "method": "kmeans"
}
```

### Performance Trend Analysis

**Prompt**: "Model the trend in execution time over the last 10 commits"

```json
{
  "analysis_type": "regression",
  "x_data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "y_data": [120, 125, 130, 128, 135, 140, 138, 145, 150, 148],
  "regression_type": "linear"
}
```

### Multi-Tool Comparison

**Prompt**: "Compare error rates across different code analysis tools"

```json
{
  "analysis_type": "comparative",
  "datasets": [
    [12, 15, 13, 14, 16],
    [45, 48, 50, 47, 49],
    [23, 25, 22, 24, 26]
  ],
  "labels": ["PyLint", "Flake8", "MyPy"]
}
```

### Normality Testing

**Prompt**: "Check if performance metrics follow a normal distribution"

```json
{
  "analysis_type": "hypothesis_test",
  "data1": [120, 125, 118, 122, 119, 128, 115, 130, 117, 123],
  "test_type": "shapiro"
}
```

## Integration Examples

### With Pattern Recognition

```python
# 1. Find similar fix patterns
fixes = call_tool("find_code_fix_pattern", {
    "error_message": "TypeError: unsupported operand type(s)",
    "top_k": 10
})

# 2. Analyze usage counts statistically
if fixes['found']:
    usage_counts = [p['usage_count'] for p in fixes['all_patterns']]

    stats = call_tool("statistical_analysis", {
        "analysis_type": "descriptive",
        "data": usage_counts
    })

    # Find outlier patterns (unusually high/low usage)
    outliers = call_tool("statistical_analysis", {
        "analysis_type": "outliers",
        "data": usage_counts,
        "method": "zscore",
        "threshold": 2
    })

    print(f"Mean usage: {stats['statistics']['mean']}")
    print(f"Found {outliers['outlier_count']} exceptional patterns")
```

### Performance Analysis Workflow

```python
# Collect performance data before and after optimization
before = [120, 125, 118, 122, 119, 128, 115, 130]
after = [95, 98, 92, 96, 94, 99, 91, 100]

# 1. Descriptive statistics
before_stats = call_tool("statistical_analysis", {
    "analysis_type": "descriptive",
    "data": before
})

after_stats = call_tool("statistical_analysis", {
    "analysis_type": "descriptive",
    "data": after
})

print(f"Before: {before_stats['statistics']['mean']:.2f} ms")
print(f"After: {after_stats['statistics']['mean']:.2f} ms")

# 2. Test if improvement is significant
significance = call_tool("statistical_analysis", {
    "analysis_type": "hypothesis_test",
    "data1": before,
    "data2": after,
    "test_type": "paired_ttest",
    "alpha": 0.05
})

if significance['is_significant']:
    effect_size = (before_stats['statistics']['mean'] -
                   after_stats['statistics']['mean']) / before_stats['statistics']['mean']
    print(f"✓ Optimization is statistically significant!")
    print(f"  Effect size: {effect_size*100:.1f}% improvement")
else:
    print("⚠ Improvement not statistically significant")

# 3. Check for outliers in after data
outliers = call_tool("statistical_analysis", {
    "analysis_type": "outliers",
    "data": after,
    "method": "iqr"
})

if outliers['outlier_count'] > 0:
    print(f"Warning: {outliers['outlier_count']} outlier measurements detected")
```

### Error Correlation Analysis

```python
# Analyze relationship between code metrics and errors
complexity_scores = [5, 12, 8, 15, 20, 25, 10, 18, 22, 7]
error_counts = [2, 5, 3, 8, 12, 15, 4, 10, 13, 3]

# Correlation analysis
correlation = call_tool("statistical_analysis", {
    "analysis_type": "correlation",
    "data1": complexity_scores,
    "data2": error_counts,
    "method": "spearman"
})

print(f"Correlation: {correlation['correlation']:.3f}")
print(f"Strength: {correlation['strength']}")
print(f"Significant: {correlation['is_significant']}")

if correlation['is_significant'] and correlation['correlation'] > 0.7:
    # Build predictive model
    regression = call_tool("statistical_analysis", {
        "analysis_type": "regression",
        "x_data": complexity_scores,
        "y_data": error_counts,
        "regression_type": "linear"
    })

    print(f"Prediction equation: {regression['equation']}")
    print(f"R²: {regression['r_squared']:.3f}")
```

## Best Practices

### 1. Choose the Right Test

- **Normal data, comparing means**: t-test
- **Non-normal data**: Mann-Whitney or Wilcoxon
- **Multiple groups**: ANOVA or Kruskal-Wallis
- **Paired observations**: Paired t-test or Wilcoxon

### 2. Check Assumptions

Always test normality before parametric tests:
```json
{
  "analysis_type": "hypothesis_test",
  "data1": [your_data],
  "test_type": "shapiro"
}
```

If p < 0.05, data is NOT normal → use non-parametric tests

### 3. Interpret Effect Size

A statistically significant result may not be practically important:
- Calculate Cohen's d for t-tests
- Look at R² for regressions
- Consider practical significance alongside statistical significance

### 4. Handle Outliers Carefully

1. Detect them (IQR, Z-score, Isolation Forest)
2. Investigate why they exist
3. Decide: remove, transform, or keep
4. Document your decision

### 5. Use Multiple Methods

When in doubt, use both:
- Parametric AND non-parametric tests
- Multiple outlier detection methods
- Different correlation methods

## Use Cases

### 1. Pattern Effectiveness Validation

**Scenario**: You have 50 uses of a fix pattern. Is it actually effective?

```python
# Get error counts before and after applying the pattern
errors_before = [10, 12, 11, 13, 9, 14, 10, 12]
errors_after = [3, 4, 2, 5, 3, 4, 2, 3]

result = call_tool("statistical_analysis", {
    "analysis_type": "hypothesis_test",
    "data1": errors_before,
    "data2": errors_after,
    "test_type": "paired_ttest"
})

# If significant, update pattern quality score
if result['is_significant']:
    rag.update_quality_score(pattern_id,
                            score=0.95,
                            reason="Statistically validated effectiveness")
```

### 2. Performance Regression Detection

**Scenario**: Detect if a commit caused performance regression

```python
# Benchmark performance across commits
baseline = [120, 122, 118, 121, 119]  # Last 5 stable commits
current = [145, 148, 150, 147, 149]   # After recent change

result = call_tool("statistical_analysis", {
    "analysis_type": "hypothesis_test",
    "data1": baseline,
    "data2": current,
    "test_type": "mann_whitney",
    "alpha": 0.01  # Stricter threshold for regressions
})

if result['is_significant']:
    print("⚠ PERFORMANCE REGRESSION DETECTED!")
    print(f"p-value: {result['p_value']:.6f}")
    # Trigger alert, block merge, etc.
```

### 3. Error Type Clustering

**Scenario**: Automatically group similar errors

```python
# Extract features from errors (e.g., [complexity, frequency])
error_features = [
    [5, 10],   # Low complexity, high frequency
    [4, 12],   # Low complexity, high frequency
    [25, 2],   # High complexity, low frequency
    [23, 3],   # High complexity, low frequency
    [6, 11],   # Low complexity, high frequency
    [24, 2]    # High complexity, low frequency
]

result = call_tool("statistical_analysis", {
    "analysis_type": "clustering",
    "data": error_features,
    "n_clusters": 2,
    "method": "kmeans"
})

# Store cluster labels with error patterns
for idx, label in enumerate(result['labels']):
    cluster_tag = f"error_cluster_{label}"
    # Add tag to error pattern in RAG
```

### 4. Code Quality Metrics Correlation

**Scenario**: Find which metrics predict bugs

```python
metrics = {
    "complexity": [5, 12, 8, 15, 20, 25, 10, 18],
    "loc": [50, 120, 80, 150, 200, 250, 100, 180],
    "test_coverage": [95, 60, 85, 45, 30, 20, 75, 50]
}
bug_counts = [2, 8, 4, 12, 18, 22, 6, 14]

for metric_name, metric_values in metrics.items():
    result = call_tool("statistical_analysis", {
        "analysis_type": "correlation",
        "data1": metric_values,
        "data2": bug_counts,
        "method": "spearman"
    })

    print(f"{metric_name}: r={result['correlation']:.3f}, "
          f"p={result['p_value']:.4f}")

    if result['is_significant'] and abs(result['correlation']) > 0.7:
        print(f"  → Strong predictor of bugs!")
```

### 5. A/B Testing Code Changes

**Scenario**: Compare two different implementations

```python
# Performance of implementation A vs B
impl_a_times = [120, 125, 118, 122, 119, 128, 115, 130]
impl_b_times = [110, 115, 108, 112, 109, 118, 105, 120]

# Compare
result = call_tool("statistical_analysis", {
    "analysis_type": "comparative",
    "datasets": [impl_a_times, impl_b_times],
    "labels": ["Implementation A", "Implementation B"]
})

if result['comparison_tests']['parametric_test']['is_significant']:
    # Implementation B is significantly faster
    mean_a = result['descriptive_statistics']['Implementation A']['mean']
    mean_b = result['descriptive_statistics']['Implementation B']['mean']
    improvement = (mean_a - mean_b) / mean_a * 100

    print(f"Implementation B is {improvement:.1f}% faster (p < 0.05)")
    print("→ Recommend using Implementation B")
```

## Advanced Techniques

### Confidence Intervals

Calculate confidence intervals for means:

```python
import scipy.stats as stats
import numpy as np

data = [120, 125, 118, 122, 119]
confidence = 0.95

mean = np.mean(data)
std_err = stats.sem(data)
ci = stats.t.interval(confidence, len(data)-1, loc=mean, scale=std_err)

print(f"95% CI: [{ci[0]:.2f}, {ci[1]:.2f}]")
```

### Power Analysis

Determine if you have enough data:

```python
from statsmodels.stats.power import ttest_power

# Calculate required sample size for desired power
effect_size = 0.5  # Medium effect
alpha = 0.05
power = 0.80

# Use external library or approximation
# Generally need 30+ samples for medium effects
```

### Bonferroni Correction

When doing multiple comparisons:

```python
n_comparisons = 5
adjusted_alpha = 0.05 / n_comparisons  # 0.01

# Use adjusted alpha in all tests
result = call_tool("statistical_analysis", {
    "analysis_type": "hypothesis_test",
    "data1": data1,
    "data2": data2,
    "test_type": "ttest",
    "alpha": adjusted_alpha
})
```

## Troubleshooting

### "Not enough data points"

Most tests need at least 3-5 data points. For robust results:
- T-test: 20+ per group
- Correlation: 10+ pairs
- Regression: 10+ points
- Clustering: 20+ points

### "Data not normally distributed"

Use non-parametric alternatives:
- t-test → Mann-Whitney U
- Paired t-test → Wilcoxon
- Pearson → Spearman or Kendall
- ANOVA → Kruskal-Wallis

### "High variance in results"

- Collect more data points
- Remove outliers (carefully!)
- Check for confounding variables
- Use robust statistical methods

### "Correlation but no causation"

Remember: correlation ≠ causation
- Look for confounding variables
- Consider experimental design
- Use domain knowledge
- Be cautious with conclusions

## Further Reading

- [SciPy Statistics Documentation](https://docs.scipy.org/doc/scipy/reference/stats.html)
- [Scikit-learn Clustering](https://scikit-learn.org/stable/modules/clustering.html)
- [Statistical Power Analysis](https://en.wikipedia.org/wiki/Statistical_power)
- [Effect Size](https://en.wikipedia.org/wiki/Effect_size)

---

**Tool Location**: `code_evolver/tools/stats/statistical_analysis.py`
**Configuration**: `code_evolver/tools/stats/statistical_analysis.yaml`
**Version**: 1.0.0
**Status**: Stable
