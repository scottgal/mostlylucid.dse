#!/usr/bin/env python3
"""
Statistical Analysis Tool - Example Usage

Demonstrates various statistical analysis capabilities for code evolution
and pattern validation.
"""

import json
import subprocess
from typing import Dict, Any


def run_analysis(analysis_params: Dict[str, Any]) -> Dict[str, Any]:
    """Run statistical analysis tool"""
    proc = subprocess.run(
        ["python", "tools/stats/statistical_analysis.py"],
        input=json.dumps(analysis_params),
        capture_output=True,
        text=True
    )
    return json.loads(proc.stdout)


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def example_1_descriptive_statistics():
    """Example 1: Analyze error counts across tools"""
    print_section("Example 1: Descriptive Statistics - Error Analysis")

    # Error counts from different code analysis tools over 10 runs
    pylint_errors = [12, 15, 13, 14, 16, 15, 14, 13, 15, 14]
    flake8_errors = [45, 48, 50, 47, 49, 46, 51, 48, 47, 49]

    # Analyze both datasets
    result = run_analysis({
        "analysis_type": "descriptive",
        "data": [pylint_errors, flake8_errors],
        "labels": ["PyLint", "Flake8"]
    })

    print("Error Count Analysis:")
    for tool, stats in result['statistics'].items():
        print(f"\n{tool}:")
        print(f"  Mean: {stats['mean']:.2f}")
        print(f"  Median: {stats['median']:.2f}")
        print(f"  Std Dev: {stats['std']:.2f}")
        print(f"  Range: {stats['min']:.0f} - {stats['max']:.0f}")
        print(f"  IQR: {stats['iqr']:.2f}")
        print(f"  CV: {stats['cv']:.2%}")


def example_2_hypothesis_testing():
    """Example 2: Test if a fix pattern reduces errors"""
    print_section("Example 2: Hypothesis Testing - Pattern Effectiveness")

    # Error counts before and after applying a fix pattern
    errors_before = [45, 48, 50, 47, 49, 46, 51, 48]
    errors_after = [12, 15, 13, 14, 16, 15, 14, 13]

    # Perform paired t-test
    result = run_analysis({
        "analysis_type": "hypothesis_test",
        "data1": errors_before,
        "data2": errors_after,
        "test_type": "paired_ttest",
        "alpha": 0.05
    })

    print("Testing Fix Pattern Effectiveness:")
    print(f"  Test: {result['test']}")
    print(f"  p-value: {result['p_value']:.6f}")
    print(f"  Significant: {'Yes ✓' if result['is_significant'] else 'No ✗'}")
    print(f"  Interpretation: {result['interpretation']}")

    if result['is_significant']:
        reduction = (sum(errors_before) - sum(errors_after)) / sum(errors_before)
        print(f"\n  → Fix pattern reduces errors by {reduction*100:.1f}%")
        print("  → Pattern is statistically validated!")


def example_3_correlation_analysis():
    """Example 3: Correlation between code complexity and bugs"""
    print_section("Example 3: Correlation - Complexity vs Bug Count")

    # Code complexity scores and corresponding bug counts
    complexity = [5, 12, 8, 15, 20, 25, 10, 18, 22, 7, 14, 19, 6, 16, 23]
    bugs = [2, 5, 3, 8, 12, 15, 4, 10, 13, 3, 7, 11, 2, 9, 14]

    # Analyze correlation
    result = run_analysis({
        "analysis_type": "correlation",
        "data1": complexity,
        "data2": bugs,
        "method": "spearman"
    })

    print("Complexity vs Bug Count Correlation:")
    print(f"  Method: {result['method']}")
    print(f"  Correlation: {result['correlation']:.3f}")
    print(f"  Strength: {result['strength']}")
    print(f"  Direction: {result['direction']}")
    print(f"  p-value: {result['p_value']:.6f}")
    print(f"  Significant: {'Yes ✓' if result['is_significant'] else 'No ✗'}")
    print(f"\n  {result['interpretation']}")

    if result['correlation'] > 0.7:
        print("\n  → High complexity strongly predicts more bugs!")
        print("  → Consider refactoring complex code")


def example_4_regression_analysis():
    """Example 4: Model performance trend over commits"""
    print_section("Example 4: Regression - Performance Trend Analysis")

    # Execution time (ms) over last 15 commits
    commits = list(range(1, 16))
    exec_times = [120, 125, 130, 128, 135, 140, 138, 145, 150, 148, 155, 160, 158, 165, 170]

    # Linear regression
    result = run_analysis({
        "analysis_type": "regression",
        "x_data": commits,
        "y_data": exec_times,
        "regression_type": "linear"
    })

    print("Performance Trend Analysis:")
    print(f"  Regression: {result['type']}")
    print(f"  Equation: {result['equation']}")
    print(f"  R²: {result['r_squared']:.4f}")
    print(f"  RMSE: {result['rmse']:.2f} ms")

    slope = result['coefficients']['slope']
    if slope > 1:
        print(f"\n  ⚠ Performance degrading by ~{slope:.2f} ms per commit")
        print("  → Investigate recent changes for performance issues")
    elif slope < -1:
        print(f"\n  ✓ Performance improving by ~{abs(slope):.2f} ms per commit")
    else:
        print("\n  → Performance relatively stable")


def example_5_outlier_detection():
    """Example 5: Detect anomalous execution times"""
    print_section("Example 5: Outlier Detection - Anomalous Performance")

    # Execution times with some anomalies
    exec_times = [120, 125, 118, 122, 119, 128, 450, 115, 130, 117, 123, 121, 380, 124]

    # Detect outliers using IQR method
    result = run_analysis({
        "analysis_type": "outliers",
        "data": exec_times,
        "method": "iqr",
        "threshold": 1.5
    })

    print("Anomalous Execution Time Detection:")
    print(f"  Method: {result['method']}")
    print(f"  Threshold: {result['threshold']}")
    print(f"  Bounds: [{result['bounds']['lower']:.1f}, {result['bounds']['upper']:.1f}] ms")
    print(f"  Outliers found: {result['outlier_count']}")
    print(f"  Outlier percentage: {result['outlier_percentage']:.1f}%")

    if result['outlier_count'] > 0:
        print(f"\n  Outlier values: {result['outlier_values']}")
        print(f"  Outlier indices: {result['outlier_indices']}")
        print("\n  → Investigate these anomalous runs")
        print("  → Possible causes: GC, I/O, network latency")


def example_6_clustering():
    """Example 6: Cluster similar error patterns"""
    print_section("Example 6: Clustering - Group Similar Errors")

    # Error features: [complexity, frequency]
    # Two natural groups: simple/frequent vs complex/rare
    error_features = [
        [5, 10],   # Simple, frequent
        [4, 12],   # Simple, frequent
        [6, 11],   # Simple, frequent
        [3, 13],   # Simple, frequent
        [25, 2],   # Complex, rare
        [23, 3],   # Complex, rare
        [24, 2],   # Complex, rare
        [26, 1],   # Complex, rare
    ]

    # K-means clustering
    result = run_analysis({
        "analysis_type": "clustering",
        "data": error_features,
        "n_clusters": 2,
        "method": "kmeans"
    })

    print("Error Pattern Clustering:")
    print(f"  Method: {result['method']}")
    print(f"  Clusters: {result['n_clusters']}")
    print(f"  Cluster sizes: {result['cluster_sizes']}")
    print(f"\n  Cluster assignments: {result['labels']}")
    print(f"  Centroids: {result['centroids']}")

    print("\n  → Group 0: Simple, frequent errors (quick fixes)")
    print("  → Group 1: Complex, rare errors (deep investigation)")
    print("\n  Use clusters to prioritize fixing strategies!")


def example_7_comparative_analysis():
    """Example 7: Compare multiple code optimization strategies"""
    print_section("Example 7: Comparative Analysis - A/B/C Testing")

    # Performance of 3 different optimization strategies (ms)
    strategy_a = [120, 125, 118, 122, 119, 128, 115]
    strategy_b = [110, 115, 108, 112, 109, 118, 105]
    strategy_c = [95, 98, 92, 96, 94, 99, 91]

    # Compare all three
    result = run_analysis({
        "analysis_type": "comparative",
        "datasets": [strategy_a, strategy_b, strategy_c],
        "labels": ["Strategy A", "Strategy B", "Strategy C"]
    })

    print("Comparing Optimization Strategies:")
    for strategy, stats in result['descriptive_statistics'].items():
        print(f"\n{strategy}:")
        print(f"  Mean: {stats['mean']:.2f} ms")
        print(f"  Std: {stats['std']:.2f} ms")

    print(f"\nStatistical Comparison:")
    anova = result['comparison_tests']['parametric_test']
    print(f"  {anova['name']}")
    print(f"  p-value: {anova['p_value']:.6f}")
    print(f"  Significant: {'Yes ✓' if anova['is_significant'] else 'No ✗'}")
    print(f"  {anova['interpretation']}")

    if anova['is_significant']:
        print("\n  → Strategies perform significantly differently")
        print("  → Recommend Strategy C (lowest mean)")


def example_8_normality_testing():
    """Example 8: Test if data is normally distributed"""
    print_section("Example 8: Normality Testing - Distribution Check")

    # Test data
    test_times = [120, 125, 118, 122, 119, 128, 115, 130, 117, 123, 121, 124, 116, 127, 122]

    # Shapiro-Wilk test
    result = run_analysis({
        "analysis_type": "hypothesis_test",
        "data1": test_times,
        "test_type": "shapiro"
    })

    print("Testing Normality of Execution Times:")
    print(f"  Test: {result['test']}")
    print(f"  Statistic: {result['statistic']:.4f}")
    print(f"  p-value: {result['p_value']:.4f}")
    print(f"  Significant: {'Yes' if result['is_significant'] else 'No'}")
    print(f"\n  {result['interpretation']}")

    if result['is_significant']:
        print("\n  → Use non-parametric tests (Mann-Whitney, Wilcoxon)")
    else:
        print("\n  → Safe to use parametric tests (t-test, ANOVA)")


def example_9_integration_with_patterns():
    """Example 9: Validate pattern effectiveness pipeline"""
    print_section("Example 9: Integration - Pattern Validation Pipeline")

    print("Simulating pattern effectiveness validation workflow:\n")

    # Step 1: Collect fix pattern usage data
    print("1. Collecting pattern usage data...")
    pattern_usage_counts = [5, 12, 8, 15, 20, 25, 10, 18, 22, 7]

    # Step 2: Descriptive statistics
    print("2. Analyzing usage distribution...")
    stats_result = run_analysis({
        "analysis_type": "descriptive",
        "data": pattern_usage_counts
    })
    print(f"   Mean usage: {stats_result['statistics']['mean']:.1f}")
    print(f"   Median usage: {stats_result['statistics']['median']:.1f}")

    # Step 3: Detect exceptional patterns
    print("3. Detecting exceptional patterns...")
    outlier_result = run_analysis({
        "analysis_type": "outliers",
        "data": pattern_usage_counts,
        "method": "zscore",
        "threshold": 1.5
    })
    print(f"   Found {outlier_result['outlier_count']} exceptional patterns")

    if outlier_result['outlier_count'] > 0:
        print(f"   Exceptional usage counts: {outlier_result['outlier_values']}")
        print("   → These patterns are particularly effective!")

    # Step 4: Before/after effectiveness test
    print("\n4. Testing pattern effectiveness...")
    errors_before = [45, 48, 50, 47, 49]
    errors_after = [12, 15, 13, 14, 16]

    test_result = run_analysis({
        "analysis_type": "hypothesis_test",
        "data1": errors_before,
        "data2": errors_after,
        "test_type": "paired_ttest"
    })

    print(f"   p-value: {test_result['p_value']:.6f}")
    print(f"   {test_result['interpretation']}")

    # Step 5: Decision
    print("\n5. Pattern validation decision:")
    if test_result['is_significant']:
        print("   ✓ Pattern is statistically validated")
        print("   → Update pattern quality score to 0.95")
        print("   → Recommend for similar errors")
    else:
        print("   ✗ Pattern effectiveness not proven")
        print("   → Keep pattern but mark as unvalidated")
        print("   → Collect more data")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("  STATISTICAL ANALYSIS TOOL - EXAMPLES")
    print("="*70)

    try:
        example_1_descriptive_statistics()
        example_2_hypothesis_testing()
        example_3_correlation_analysis()
        example_4_regression_analysis()
        example_5_outlier_detection()
        example_6_clustering()
        example_7_comparative_analysis()
        example_8_normality_testing()
        example_9_integration_with_patterns()

        print("\n" + "="*70)
        print("  All examples completed successfully!")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
