#!/usr/bin/env python3
"""
Statistical Analysis Tool

Comprehensive statistical analysis tool using scikit-learn, scipy, and numpy.
Supports descriptive statistics, hypothesis testing, correlation, regression,
clustering, outlier detection, and more.
"""

import json
import sys
import numpy as np
from typing import Dict, Any, List, Union, Optional
import warnings
warnings.filterwarnings('ignore')


def descriptive_statistics(data: Union[List[float], List[List[float]]],
                          labels: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Calculate comprehensive descriptive statistics for dataset(s)

    Args:
        data: Single dataset or list of datasets
        labels: Optional labels for each dataset

    Returns:
        Dictionary with statistical measures
    """
    try:
        from scipy import stats

        # Handle single vs multiple datasets
        if not data:
            return {'error': 'No data provided'}

        # Check if this is a single dataset or multiple
        is_single = not isinstance(data[0], (list, np.ndarray))
        datasets = [data] if is_single else data

        if labels and len(labels) != len(datasets):
            labels = [f"Dataset {i+1}" for i in range(len(datasets))]
        elif not labels:
            labels = [f"Dataset {i+1}" for i in range(len(datasets))]

        results = {}

        for label, dataset in zip(labels, datasets):
            arr = np.array(dataset, dtype=float)

            # Remove NaN values
            arr = arr[~np.isnan(arr)]

            if len(arr) == 0:
                results[label] = {'error': 'No valid data points'}
                continue

            # Calculate statistics
            stats_dict = {
                'count': len(arr),
                'mean': float(np.mean(arr)),
                'median': float(np.median(arr)),
                'mode': float(stats.mode(arr, keepdims=True)[0][0]) if len(arr) > 1 else float(arr[0]),
                'std': float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
                'variance': float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0,
                'min': float(np.min(arr)),
                'max': float(np.max(arr)),
                'range': float(np.ptp(arr)),
                'q1': float(np.percentile(arr, 25)),
                'q3': float(np.percentile(arr, 75)),
                'iqr': float(np.percentile(arr, 75) - np.percentile(arr, 25)),
                'skewness': float(stats.skew(arr)) if len(arr) > 2 else 0.0,
                'kurtosis': float(stats.kurtosis(arr)) if len(arr) > 3 else 0.0,
                'percentiles': {
                    'p10': float(np.percentile(arr, 10)),
                    'p25': float(np.percentile(arr, 25)),
                    'p50': float(np.percentile(arr, 50)),
                    'p75': float(np.percentile(arr, 75)),
                    'p90': float(np.percentile(arr, 90)),
                    'p95': float(np.percentile(arr, 95)),
                    'p99': float(np.percentile(arr, 99))
                }
            }

            # Coefficient of variation
            if stats_dict['mean'] != 0:
                stats_dict['cv'] = float(stats_dict['std'] / abs(stats_dict['mean']))
            else:
                stats_dict['cv'] = 0.0

            results[label] = stats_dict

        return {
            'success': True,
            'statistics': results if not is_single else results[labels[0]]
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def hypothesis_testing(data1: List[float], data2: Optional[List[float]] = None,
                       test_type: str = 'ttest', alpha: float = 0.05) -> Dict[str, Any]:
    """
    Perform various hypothesis tests

    Args:
        data1: First dataset
        data2: Second dataset (for two-sample tests)
        test_type: Type of test (ttest, paired_ttest, anova, mann_whitney, wilcoxon, ks_test, shapiro)
        alpha: Significance level

    Returns:
        Test results with p-value and interpretation
    """
    try:
        from scipy import stats as sp_stats

        arr1 = np.array(data1, dtype=float)
        arr1 = arr1[~np.isnan(arr1)]

        if test_type == 'shapiro':
            # Shapiro-Wilk normality test
            statistic, p_value = sp_stats.shapiro(arr1)
            return {
                'success': True,
                'test': 'Shapiro-Wilk Normality Test',
                'statistic': float(statistic),
                'p_value': float(p_value),
                'alpha': alpha,
                'is_significant': p_value < alpha,
                'interpretation': 'Data is NOT normally distributed' if p_value < alpha else 'Data appears normally distributed',
                'null_hypothesis': 'Data is normally distributed'
            }

        if data2 is None:
            return {'success': False, 'error': f'{test_type} requires two datasets'}

        arr2 = np.array(data2, dtype=float)
        arr2 = arr2[~np.isnan(arr2)]

        if test_type == 'ttest':
            # Independent t-test
            statistic, p_value = sp_stats.ttest_ind(arr1, arr2)
            return {
                'success': True,
                'test': 'Independent Samples t-test',
                'statistic': float(statistic),
                'p_value': float(p_value),
                'alpha': alpha,
                'is_significant': p_value < alpha,
                'interpretation': 'Means are significantly different' if p_value < alpha else 'No significant difference in means',
                'null_hypothesis': 'Means are equal',
                'effect_size_cohens_d': float((np.mean(arr1) - np.mean(arr2)) / np.sqrt((np.var(arr1) + np.var(arr2)) / 2))
            }

        elif test_type == 'paired_ttest':
            # Paired t-test
            statistic, p_value = sp_stats.ttest_rel(arr1, arr2)
            return {
                'success': True,
                'test': 'Paired Samples t-test',
                'statistic': float(statistic),
                'p_value': float(p_value),
                'alpha': alpha,
                'is_significant': p_value < alpha,
                'interpretation': 'Paired means are significantly different' if p_value < alpha else 'No significant difference in paired means',
                'null_hypothesis': 'Paired means are equal'
            }

        elif test_type == 'mann_whitney':
            # Mann-Whitney U test (non-parametric)
            statistic, p_value = sp_stats.mannwhitneyu(arr1, arr2, alternative='two-sided')
            return {
                'success': True,
                'test': 'Mann-Whitney U Test',
                'statistic': float(statistic),
                'p_value': float(p_value),
                'alpha': alpha,
                'is_significant': p_value < alpha,
                'interpretation': 'Distributions are significantly different' if p_value < alpha else 'No significant difference in distributions',
                'null_hypothesis': 'Distributions are equal'
            }

        elif test_type == 'wilcoxon':
            # Wilcoxon signed-rank test (non-parametric paired)
            statistic, p_value = sp_stats.wilcoxon(arr1, arr2)
            return {
                'success': True,
                'test': 'Wilcoxon Signed-Rank Test',
                'statistic': float(statistic),
                'p_value': float(p_value),
                'alpha': alpha,
                'is_significant': p_value < alpha,
                'interpretation': 'Paired distributions are significantly different' if p_value < alpha else 'No significant difference in paired distributions',
                'null_hypothesis': 'Paired distributions are equal'
            }

        elif test_type == 'ks_test':
            # Kolmogorov-Smirnov test
            statistic, p_value = sp_stats.ks_2samp(arr1, arr2)
            return {
                'success': True,
                'test': 'Kolmogorov-Smirnov Test',
                'statistic': float(statistic),
                'p_value': float(p_value),
                'alpha': alpha,
                'is_significant': p_value < alpha,
                'interpretation': 'Distributions are significantly different' if p_value < alpha else 'Distributions appear similar',
                'null_hypothesis': 'Distributions are from the same distribution'
            }

        else:
            return {'success': False, 'error': f'Unknown test type: {test_type}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def correlation_analysis(data1: List[float], data2: List[float],
                         method: str = 'pearson') -> Dict[str, Any]:
    """
    Calculate correlation between two datasets

    Args:
        data1: First dataset
        data2: Second dataset
        method: Correlation method (pearson, spearman, kendall)

    Returns:
        Correlation coefficient and p-value
    """
    try:
        from scipy import stats

        arr1 = np.array(data1, dtype=float)
        arr2 = np.array(data2, dtype=float)

        # Remove pairs with NaN
        mask = ~(np.isnan(arr1) | np.isnan(arr2))
        arr1 = arr1[mask]
        arr2 = arr2[mask]

        if len(arr1) < 3:
            return {'success': False, 'error': 'Need at least 3 data points for correlation'}

        if method == 'pearson':
            corr, p_value = stats.pearsonr(arr1, arr2)
            method_name = 'Pearson'
        elif method == 'spearman':
            corr, p_value = stats.spearmanr(arr1, arr2)
            method_name = 'Spearman'
        elif method == 'kendall':
            corr, p_value = stats.kendalltau(arr1, arr2)
            method_name = 'Kendall'
        else:
            return {'success': False, 'error': f'Unknown correlation method: {method}'}

        # Interpret strength
        abs_corr = abs(corr)
        if abs_corr >= 0.9:
            strength = 'very strong'
        elif abs_corr >= 0.7:
            strength = 'strong'
        elif abs_corr >= 0.5:
            strength = 'moderate'
        elif abs_corr >= 0.3:
            strength = 'weak'
        else:
            strength = 'very weak'

        direction = 'positive' if corr > 0 else 'negative'

        return {
            'success': True,
            'method': f'{method_name} Correlation',
            'correlation': float(corr),
            'p_value': float(p_value),
            'is_significant': p_value < 0.05,
            'strength': strength,
            'direction': direction,
            'interpretation': f'{strength.capitalize()} {direction} correlation (r={corr:.3f}, p={p_value:.4f})',
            'r_squared': float(corr ** 2)
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def regression_analysis(x_data: List[float], y_data: List[float],
                       regression_type: str = 'linear') -> Dict[str, Any]:
    """
    Perform regression analysis

    Args:
        x_data: Independent variable
        y_data: Dependent variable
        regression_type: Type of regression (linear, polynomial)

    Returns:
        Regression results including coefficients, R², and predictions
    """
    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import PolynomialFeatures
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

        X = np.array(x_data).reshape(-1, 1)
        y = np.array(y_data)

        # Remove NaN values
        mask = ~(np.isnan(X.flatten()) | np.isnan(y))
        X = X[mask]
        y = y[mask]

        if len(X) < 2:
            return {'success': False, 'error': 'Need at least 2 data points for regression'}

        if regression_type == 'linear':
            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)

            return {
                'success': True,
                'type': 'Linear Regression',
                'coefficients': {
                    'intercept': float(model.intercept_),
                    'slope': float(model.coef_[0])
                },
                'equation': f'y = {model.coef_[0]:.4f}x + {model.intercept_:.4f}',
                'r_squared': float(r2_score(y, y_pred)),
                'adjusted_r_squared': float(1 - (1 - r2_score(y, y_pred)) * (len(y) - 1) / (len(y) - 2)) if len(y) > 2 else 0.0,
                'mse': float(mean_squared_error(y, y_pred)),
                'rmse': float(np.sqrt(mean_squared_error(y, y_pred))),
                'mae': float(mean_absolute_error(y, y_pred)),
                'predictions': y_pred.tolist()
            }

        elif regression_type.startswith('polynomial'):
            # Extract degree from type like "polynomial_2"
            try:
                degree = int(regression_type.split('_')[1]) if '_' in regression_type else 2
            except:
                degree = 2

            poly_features = PolynomialFeatures(degree=degree)
            X_poly = poly_features.fit_transform(X)

            model = LinearRegression()
            model.fit(X_poly, y)
            y_pred = model.predict(X_poly)

            return {
                'success': True,
                'type': f'Polynomial Regression (degree {degree})',
                'degree': degree,
                'coefficients': model.coef_.tolist(),
                'intercept': float(model.intercept_),
                'r_squared': float(r2_score(y, y_pred)),
                'adjusted_r_squared': float(1 - (1 - r2_score(y, y_pred)) * (len(y) - 1) / (len(y) - len(model.coef_) - 1)) if len(y) > len(model.coef_) + 1 else 0.0,
                'mse': float(mean_squared_error(y, y_pred)),
                'rmse': float(np.sqrt(mean_squared_error(y, y_pred))),
                'mae': float(mean_absolute_error(y, y_pred)),
                'predictions': y_pred.tolist()
            }

        else:
            return {'success': False, 'error': f'Unknown regression type: {regression_type}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def outlier_detection(data: List[float], method: str = 'iqr',
                     threshold: float = 1.5) -> Dict[str, Any]:
    """
    Detect outliers in dataset

    Args:
        data: Dataset to analyze
        method: Detection method (iqr, zscore, isolation_forest)
        threshold: Threshold for outlier detection (1.5 for IQR, 3 for z-score)

    Returns:
        Outlier indices and values
    """
    try:
        arr = np.array(data, dtype=float)
        arr_clean = arr[~np.isnan(arr)]

        if len(arr_clean) < 3:
            return {'success': False, 'error': 'Need at least 3 data points for outlier detection'}

        if method == 'iqr':
            q1 = np.percentile(arr_clean, 25)
            q3 = np.percentile(arr_clean, 75)
            iqr = q3 - q1

            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr

            outlier_mask = (arr < lower_bound) | (arr > upper_bound)
            outlier_indices = np.where(outlier_mask)[0].tolist()
            outlier_values = arr[outlier_mask].tolist()

            return {
                'success': True,
                'method': 'IQR (Interquartile Range)',
                'threshold': threshold,
                'bounds': {
                    'lower': float(lower_bound),
                    'upper': float(upper_bound)
                },
                'outlier_count': len(outlier_indices),
                'outlier_indices': outlier_indices,
                'outlier_values': outlier_values,
                'outlier_percentage': float(len(outlier_indices) / len(arr) * 100)
            }

        elif method == 'zscore':
            mean = np.mean(arr_clean)
            std = np.std(arr_clean)

            if std == 0:
                return {'success': False, 'error': 'Standard deviation is zero'}

            z_scores = np.abs((arr - mean) / std)
            outlier_mask = z_scores > threshold
            outlier_indices = np.where(outlier_mask)[0].tolist()
            outlier_values = arr[outlier_mask].tolist()

            return {
                'success': True,
                'method': 'Z-Score',
                'threshold': threshold,
                'mean': float(mean),
                'std': float(std),
                'outlier_count': len(outlier_indices),
                'outlier_indices': outlier_indices,
                'outlier_values': outlier_values,
                'outlier_percentage': float(len(outlier_indices) / len(arr) * 100)
            }

        elif method == 'isolation_forest':
            from sklearn.ensemble import IsolationForest

            X = arr_clean.reshape(-1, 1)
            clf = IsolationForest(contamination=threshold, random_state=42)
            predictions = clf.fit_predict(X)

            outlier_mask = predictions == -1
            outlier_indices = np.where(outlier_mask)[0].tolist()
            outlier_values = arr_clean[outlier_mask].tolist()

            return {
                'success': True,
                'method': 'Isolation Forest',
                'contamination': threshold,
                'outlier_count': len(outlier_indices),
                'outlier_indices': outlier_indices,
                'outlier_values': outlier_values,
                'outlier_percentage': float(len(outlier_indices) / len(arr_clean) * 100)
            }

        else:
            return {'success': False, 'error': f'Unknown outlier detection method: {method}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def clustering_analysis(data: List[List[float]], n_clusters: int = 3,
                       method: str = 'kmeans') -> Dict[str, Any]:
    """
    Perform clustering analysis

    Args:
        data: Dataset (2D array)
        n_clusters: Number of clusters
        method: Clustering method (kmeans, dbscan, hierarchical)

    Returns:
        Cluster assignments and centroids
    """
    try:
        X = np.array(data, dtype=float)

        if X.ndim == 1:
            X = X.reshape(-1, 1)

        if method == 'kmeans':
            from sklearn.cluster import KMeans

            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)

            return {
                'success': True,
                'method': 'K-Means Clustering',
                'n_clusters': n_clusters,
                'labels': labels.tolist(),
                'centroids': kmeans.cluster_centers_.tolist(),
                'inertia': float(kmeans.inertia_),
                'cluster_sizes': [int(np.sum(labels == i)) for i in range(n_clusters)]
            }

        elif method == 'dbscan':
            from sklearn.cluster import DBSCAN

            dbscan = DBSCAN(eps=0.5, min_samples=5)
            labels = dbscan.fit_predict(X)

            n_clusters_found = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)

            return {
                'success': True,
                'method': 'DBSCAN Clustering',
                'n_clusters_found': n_clusters_found,
                'labels': labels.tolist(),
                'n_noise_points': n_noise,
                'cluster_sizes': [int(np.sum(labels == i)) for i in set(labels) if i != -1]
            }

        elif method == 'hierarchical':
            from sklearn.cluster import AgglomerativeClustering

            clustering = AgglomerativeClustering(n_clusters=n_clusters)
            labels = clustering.fit_predict(X)

            return {
                'success': True,
                'method': 'Hierarchical Clustering',
                'n_clusters': n_clusters,
                'labels': labels.tolist(),
                'cluster_sizes': [int(np.sum(labels == i)) for i in range(n_clusters)]
            }

        else:
            return {'success': False, 'error': f'Unknown clustering method: {method}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def comparative_analysis(datasets: List[List[float]],
                        labels: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Compare multiple datasets statistically

    Args:
        datasets: List of datasets to compare
        labels: Optional labels for each dataset

    Returns:
        Comparative statistics and ANOVA results
    """
    try:
        from scipy import stats

        if not labels:
            labels = [f"Dataset {i+1}" for i in range(len(datasets))]

        # Descriptive stats for each
        desc_stats = descriptive_statistics(datasets, labels)

        # ANOVA if more than 2 groups
        if len(datasets) >= 2:
            # Clean data
            cleaned_datasets = [np.array(d)[~np.isnan(np.array(d))] for d in datasets]

            if len(datasets) == 2:
                # Two groups: use t-test
                t_stat, p_value = stats.ttest_ind(cleaned_datasets[0], cleaned_datasets[1])
                test_name = 'Independent t-test'
                statistic = t_stat
            else:
                # Multiple groups: use ANOVA
                f_stat, p_value = stats.f_oneway(*cleaned_datasets)
                test_name = 'One-way ANOVA'
                statistic = f_stat

            # Kruskal-Wallis (non-parametric alternative)
            h_stat, h_p_value = stats.kruskal(*cleaned_datasets)

            comparison = {
                'parametric_test': {
                    'name': test_name,
                    'statistic': float(statistic),
                    'p_value': float(p_value),
                    'is_significant': p_value < 0.05,
                    'interpretation': 'Groups differ significantly' if p_value < 0.05 else 'No significant difference between groups'
                },
                'non_parametric_test': {
                    'name': 'Kruskal-Wallis H-test',
                    'statistic': float(h_stat),
                    'p_value': float(h_p_value),
                    'is_significant': h_p_value < 0.05,
                    'interpretation': 'Groups differ significantly' if h_p_value < 0.05 else 'No significant difference between groups'
                }
            }
        else:
            comparison = {'note': 'Need at least 2 datasets for comparison'}

        return {
            'success': True,
            'descriptive_statistics': desc_stats.get('statistics', {}),
            'comparison_tests': comparison
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_text = sys.stdin.read().strip()

        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({
                'success': False,
                'error': f'Invalid JSON input: {str(e)}'
            }))
            sys.exit(1)

        # Get analysis type
        analysis_type = input_data.get('analysis_type', '')

        if not analysis_type:
            print(json.dumps({
                'success': False,
                'error': 'Missing required parameter: analysis_type'
            }))
            sys.exit(1)

        # Route to appropriate analysis
        if analysis_type == 'descriptive':
            result = descriptive_statistics(
                data=input_data.get('data', []),
                labels=input_data.get('labels')
            )

        elif analysis_type == 'hypothesis_test':
            result = hypothesis_testing(
                data1=input_data.get('data1', []),
                data2=input_data.get('data2'),
                test_type=input_data.get('test_type', 'ttest'),
                alpha=input_data.get('alpha', 0.05)
            )

        elif analysis_type == 'correlation':
            result = correlation_analysis(
                data1=input_data.get('data1', []),
                data2=input_data.get('data2', []),
                method=input_data.get('method', 'pearson')
            )

        elif analysis_type == 'regression':
            result = regression_analysis(
                x_data=input_data.get('x_data', []),
                y_data=input_data.get('y_data', []),
                regression_type=input_data.get('regression_type', 'linear')
            )

        elif analysis_type == 'outliers':
            result = outlier_detection(
                data=input_data.get('data', []),
                method=input_data.get('method', 'iqr'),
                threshold=input_data.get('threshold', 1.5)
            )

        elif analysis_type == 'clustering':
            result = clustering_analysis(
                data=input_data.get('data', []),
                n_clusters=input_data.get('n_clusters', 3),
                method=input_data.get('method', 'kmeans')
            )

        elif analysis_type == 'comparative':
            result = comparative_analysis(
                datasets=input_data.get('datasets', []),
                labels=input_data.get('labels')
            )

        else:
            result = {
                'success': False,
                'error': f'Unknown analysis type: {analysis_type}'
            }

        # Output result
        print(json.dumps(result, indent=2))

        if not result.get('success', False):
            sys.exit(1)

    except Exception as e:
        import traceback
        print(json.dumps({
            'success': False,
            'error': f'Fatal error: {str(e)}',
            'traceback': traceback.format_exc()
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
