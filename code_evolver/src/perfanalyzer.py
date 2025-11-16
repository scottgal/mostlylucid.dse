"""
PerfAnalyzer - Analyzes captured performance data and generates optimizations.

Uses data captured by PerfCatcher to:
1. Query Loki for performance variances
2. Analyze window of requests when thresholds exceeded
3. Identify performance bottlenecks
4. Generate optimization recommendations

This is a special tool used in auto-optimization workflows.
"""
import logging
import json
import requests
import statistics
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class PerfAnalyzer:
    """
    Analyzes captured performance data from PerfCatcher.

    Queries Loki for performance variances, analyzes patterns,
    identifies bottlenecks, and generates optimization recommendations.
    """

    def __init__(
        self,
        loki_url: str = "http://localhost:3100",
        lookback_hours: int = 24
    ):
        """
        Initialize PerfAnalyzer.

        Args:
            loki_url: Loki instance URL
            lookback_hours: How far back to query for performance data
        """
        self.loki_url = loki_url.rstrip('/')
        self.lookback_hours = lookback_hours

    def query_performance_issues(
        self,
        tool_name: Optional[str] = None,
        workflow_id: Optional[str] = None,
        variance_level: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query Loki for captured performance variances.

        Args:
            tool_name: Filter by tool name
            workflow_id: Filter by workflow ID
            variance_level: Filter by variance level (high, medium)
            limit: Maximum number of results

        Returns:
            List of performance variance records
        """
        # Build LogQL query
        labels = {'job': 'code_evolver_perfcatcher'}

        if tool_name:
            labels['tool_name'] = tool_name
        if workflow_id:
            labels['workflow_id'] = workflow_id
        if variance_level:
            labels['variance_level'] = variance_level

        # Create label selector
        label_selector = ','.join(f'{k}="{v}"' for k, v in labels.items())
        query = f'{{{label_selector}}}'

        # Calculate time range
        end_time = int(datetime.now().timestamp() * 1e9)
        start_time = int((datetime.now() - timedelta(hours=self.lookback_hours)).timestamp() * 1e9)

        # Query Loki
        try:
            response = requests.get(
                f"{self.loki_url}/loki/api/v1/query_range",
                params={
                    'query': query,
                    'start': start_time,
                    'end': end_time,
                    'limit': limit
                },
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            # Parse results
            perf_issues = []
            for stream in data.get('data', {}).get('result', []):
                for value in stream.get('values', []):
                    timestamp_ns, log_line = value
                    try:
                        perf_data = json.loads(log_line)
                        perf_data['timestamp'] = timestamp_ns
                        perf_issues.append(perf_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse log line: {log_line[:100]}")

            return perf_issues

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query Loki: {e}")
            return []

    def analyze_performance_patterns(
        self,
        perf_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in performance variances.

        Args:
            perf_issues: List of performance variance records

        Returns:
            Analysis with patterns, trends, bottlenecks
        """
        if not perf_issues:
            return {'total': 0, 'patterns': []}

        # Group by tool
        by_tool = defaultdict(list)
        by_workflow = defaultdict(list)
        variance_distribution = []

        for issue in perf_issues:
            tool_name = issue.get('tool_name', 'Unknown')
            workflow_id = issue.get('workflow_id', 'Unknown')
            variance = issue.get('variance', 0)

            by_tool[tool_name].append(issue)
            by_workflow[workflow_id].append(issue)
            variance_distribution.append(variance)

        # Calculate statistics
        analysis = {
            'total_variance_events': len(perf_issues),
            'affected_tools': len(by_tool),
            'affected_workflows': len(by_workflow),
            'variance_stats': {
                'mean': statistics.mean(variance_distribution) if variance_distribution else 0,
                'median': statistics.median(variance_distribution) if variance_distribution else 0,
                'max': max(variance_distribution) if variance_distribution else 0,
                'min': min(variance_distribution) if variance_distribution else 0
            },
            'tools_by_variance_frequency': self._rank_tools_by_frequency(by_tool),
            'tools_by_severity': self._rank_tools_by_severity(by_tool),
            'time_based_patterns': self._analyze_time_patterns(perf_issues),
            'bottlenecks': self._identify_bottlenecks(by_tool)
        }

        return analysis

    def _rank_tools_by_frequency(
        self,
        by_tool: Dict[str, List[Dict[str, Any]]]
    ) -> List[Tuple[str, int]]:
        """Rank tools by frequency of variance events."""
        return sorted(
            [(tool, len(issues)) for tool, issues in by_tool.items()],
            key=lambda x: x[1],
            reverse=True
        )

    def _rank_tools_by_severity(
        self,
        by_tool: Dict[str, List[Dict[str, Any]]]
    ) -> List[Tuple[str, float]]:
        """Rank tools by average variance severity."""
        severity = []
        for tool, issues in by_tool.items():
            variances = [i.get('variance', 0) for i in issues]
            avg_variance = statistics.mean(variances) if variances else 0
            severity.append((tool, avg_variance))

        return sorted(severity, key=lambda x: x[1], reverse=True)

    def _analyze_time_patterns(
        self,
        perf_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze time-based patterns in performance issues."""
        # Group by hour
        by_hour = defaultdict(int)
        for issue in perf_issues:
            timestamp = issue.get('timestamp', '')
            if timestamp:
                # Convert nanosecond timestamp to datetime
                dt = datetime.fromtimestamp(int(timestamp) / 1e9)
                hour = dt.hour
                by_hour[hour] += 1

        # Find peak hours
        if by_hour:
            peak_hour = max(by_hour.items(), key=lambda x: x[1])
            return {
                'distribution_by_hour': dict(by_hour),
                'peak_hour': peak_hour[0],
                'peak_hour_count': peak_hour[1]
            }
        return {}

    def _identify_bottlenecks(
        self,
        by_tool: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Identify performance bottlenecks.

        A bottleneck is defined as a tool with:
        - High frequency of variance events (> 10)
        - High average variance (> 50%)
        - High max execution time (> 1000ms)
        """
        bottlenecks = []

        for tool_name, issues in by_tool.items():
            if len(issues) < 5:  # Need at least 5 samples
                continue

            variances = [i.get('variance', 0) for i in issues]
            current_times = [i.get('current_time_ms', 0) for i in issues]
            mean_times = [i.get('mean_time_ms', 0) for i in issues]

            avg_variance = statistics.mean(variances)
            max_time = max(current_times) if current_times else 0
            avg_time = statistics.mean(current_times) if current_times else 0
            baseline_avg = statistics.mean(mean_times) if mean_times else 0

            # Check bottleneck criteria
            is_bottleneck = (
                len(issues) >= 10 or  # Frequent variances
                avg_variance > 0.5 or  # High average variance
                max_time > 1000  # Slow execution
            )

            if is_bottleneck:
                bottlenecks.append({
                    'tool_name': tool_name,
                    'frequency': len(issues),
                    'avg_variance': avg_variance,
                    'max_time_ms': max_time,
                    'avg_time_ms': avg_time,
                    'baseline_avg_ms': baseline_avg,
                    'severity': self._calculate_bottleneck_severity(
                        len(issues), avg_variance, max_time
                    ),
                    'optimization_priority': 'critical' if avg_variance > 1.0 else 'high'
                })

        return sorted(bottlenecks, key=lambda x: x['severity'], reverse=True)

    def _calculate_bottleneck_severity(
        self,
        frequency: int,
        avg_variance: float,
        max_time: float
    ) -> float:
        """
        Calculate bottleneck severity score.

        Args:
            frequency: Number of variance events
            avg_variance: Average variance ratio
            max_time: Maximum execution time (ms)

        Returns:
            Severity score (higher = more severe)
        """
        # Weighted combination of factors
        freq_score = min(frequency / 10, 10)  # Cap at 10
        variance_score = avg_variance * 10
        time_score = max_time / 100  # 1000ms = score of 10

        return freq_score + variance_score + time_score

    def generate_optimization_recommendations(
        self,
        tool_name: str,
        perf_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate optimization recommendations for a tool.

        Args:
            tool_name: Name of the tool
            perf_issues: Performance variance records for this tool

        Returns:
            List of optimization recommendations
        """
        if not perf_issues:
            return []

        recommendations = []

        # Calculate statistics
        variances = [i.get('variance', 0) for i in perf_issues]
        current_times = [i.get('current_time_ms', 0) for i in perf_issues]
        mean_times = [i.get('mean_time_ms', 0) for i in perf_issues]

        avg_variance = statistics.mean(variances)
        max_time = max(current_times)
        avg_time = statistics.mean(current_times)
        baseline = statistics.mean(mean_times) if mean_times else 0

        # Recommendation 1: Caching
        if avg_variance > 0.3 and len(perf_issues) > 10:
            recommendations.append({
                'type': 'caching',
                'priority': 'high',
                'description': f'{tool_name} shows high variance ({avg_variance:.1%}). Consider adding caching.',
                'estimated_improvement': '30-50% reduction in response time',
                'implementation': 'Add LRU cache or memoization decorator'
            })

        # Recommendation 2: Optimization
        if max_time > 1000:
            recommendations.append({
                'type': 'optimization',
                'priority': 'critical',
                'description': f'{tool_name} has max execution time of {max_time:.0f}ms. Needs optimization.',
                'estimated_improvement': '50-70% reduction in worst-case time',
                'implementation': 'Profile code, optimize hotspots, consider async execution'
            })

        # Recommendation 3: Rate Limiting
        if len(perf_issues) > 20 and avg_variance < 0.2:
            recommendations.append({
                'type': 'rate_limiting',
                'priority': 'medium',
                'description': f'{tool_name} has frequent variance events but low variance. May be overloaded.',
                'estimated_improvement': '20-30% reduction in variance frequency',
                'implementation': 'Add rate limiting or request throttling'
            })

        # Recommendation 4: Scaling
        if avg_time > baseline * 2:
            recommendations.append({
                'type': 'scaling',
                'priority': 'high',
                'description': f'{tool_name} current avg ({avg_time:.0f}ms) is 2x baseline ({baseline:.0f}ms).',
                'estimated_improvement': 'Return to baseline performance',
                'implementation': 'Scale resources or optimize algorithm'
            })

        # Recommendation 5: Batching
        if len(perf_issues) > 15 and avg_time < 100:
            recommendations.append({
                'type': 'batching',
                'priority': 'low',
                'description': f'{tool_name} has many fast calls. Consider batching.',
                'estimated_improvement': '10-20% overall throughput improvement',
                'implementation': 'Implement batch processing for multiple requests'
            })

        return sorted(recommendations, key=lambda x: {
            'critical': 0, 'high': 1, 'medium': 2, 'low': 3
        }[x['priority']])

    def get_performance_report(
        self,
        tool_name: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> str:
        """
        Generate a comprehensive performance report.

        Args:
            tool_name: Filter by tool name
            workflow_id: Filter by workflow ID

        Returns:
            Human-readable performance report
        """
        # Query performance issues
        perf_issues = self.query_performance_issues(
            tool_name=tool_name,
            workflow_id=workflow_id
        )

        if not perf_issues:
            return "No performance variances found in the specified time range."

        # Analyze patterns
        analysis = self.analyze_performance_patterns(perf_issues)

        # Build report
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("PerfAnalyzer Performance Report")
        report_lines.append("=" * 80)
        report_lines.append(f"Time Range: Last {self.lookback_hours} hours")
        report_lines.append(f"Total Variance Events: {analysis['total_variance_events']}")
        report_lines.append(f"Affected Tools: {analysis['affected_tools']}")
        report_lines.append("")

        # Variance statistics
        vstats = analysis['variance_stats']
        report_lines.append("Variance Statistics:")
        report_lines.append(f"  Mean Variance: {vstats['mean']:.1%}")
        report_lines.append(f"  Median Variance: {vstats['median']:.1%}")
        report_lines.append(f"  Max Variance: {vstats['max']:.1%}")
        report_lines.append("")

        # Top tools by frequency
        report_lines.append("Tools with Most Variance Events:")
        for tool, count in analysis['tools_by_variance_frequency'][:5]:
            report_lines.append(f"  - {tool}: {count} events")
        report_lines.append("")

        # Bottlenecks
        if analysis['bottlenecks']:
            report_lines.append("Identified Bottlenecks:")
            for i, bottleneck in enumerate(analysis['bottlenecks'][:5], 1):
                report_lines.append(f"\n  {i}. {bottleneck['tool_name']}")
                report_lines.append(f"     Severity Score: {bottleneck['severity']:.1f}")
                report_lines.append(f"     Frequency: {bottleneck['frequency']} events")
                report_lines.append(f"     Avg Variance: {bottleneck['avg_variance']:.1%}")
                report_lines.append(f"     Max Time: {bottleneck['max_time_ms']:.0f}ms")
                report_lines.append(f"     Priority: {bottleneck['optimization_priority']}")

                # Get recommendations
                tool_issues = [
                    i for i in perf_issues
                    if i.get('tool_name') == bottleneck['tool_name']
                ]
                recommendations = self.generate_optimization_recommendations(
                    bottleneck['tool_name'],
                    tool_issues
                )

                if recommendations:
                    report_lines.append(f"     Recommendations:")
                    for rec in recommendations[:3]:
                        report_lines.append(f"       - [{rec['priority']}] {rec['type']}: {rec['description']}")

        report_lines.append("\n" + "=" * 80)

        return "\n".join(report_lines)


def analyze_performance(
    tool_name: Optional[str] = None,
    workflow_id: Optional[str] = None,
    generate_recommendations: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to analyze performance and generate optimizations.

    Args:
        tool_name: Filter by tool name
        workflow_id: Filter by workflow ID
        generate_recommendations: Whether to generate optimization recommendations

    Returns:
        Analysis results with optimization recommendations
    """
    analyzer = PerfAnalyzer()

    # Query performance issues
    perf_issues = analyzer.query_performance_issues(
        tool_name=tool_name,
        workflow_id=workflow_id
    )

    if not perf_issues:
        return {'error': 'No performance variances found'}

    # Analyze patterns
    analysis = analyzer.analyze_performance_patterns(perf_issues)

    # Generate recommendations if requested
    all_recommendations = {}
    if generate_recommendations:
        # Get unique tool names
        tool_names = set(i.get('tool_name') for i in perf_issues if i.get('tool_name'))

        for tool in tool_names:
            tool_issues = [i for i in perf_issues if i.get('tool_name') == tool]
            recommendations = analyzer.generate_optimization_recommendations(tool, tool_issues)
            if recommendations:
                all_recommendations[tool] = recommendations

    return {
        'analysis': analysis,
        'performance_issues': perf_issues,
        'recommendations': all_recommendations if generate_recommendations else None,
        'report': analyzer.get_performance_report(tool_name, workflow_id)
    }
