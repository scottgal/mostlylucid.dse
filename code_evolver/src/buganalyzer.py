"""
BugAnalyzer - Analyzes captured exceptions and generates fixes.

Uses data captured by BugCatcher to:
1. Query Loki for exception patterns
2. Reproduce issues with captured state
3. Run tests with captured request/exception details
4. Generate fixes automatically

This is a special tool used in auto-repair workflows.
"""
import logging
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BugAnalyzer:
    """
    Analyzes captured bug data from BugCatcher and generates fixes.

    Queries Loki for exceptions, analyzes patterns, reproduces issues,
    and generates fixes for auto-repair workflows.
    """

    def __init__(
        self,
        loki_url: str = "http://localhost:3100",
        lookback_hours: int = 24
    ):
        """
        Initialize BugAnalyzer.

        Args:
            loki_url: Loki instance URL
            lookback_hours: How far back to query for exceptions
        """
        self.loki_url = loki_url.rstrip('/')
        self.lookback_hours = lookback_hours

    def query_exceptions(
        self,
        tool_name: Optional[str] = None,
        workflow_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query Loki for captured exceptions.

        Args:
            tool_name: Filter by tool name
            workflow_id: Filter by workflow ID
            severity: Filter by severity (error, critical)
            limit: Maximum number of results

        Returns:
            List of exception records with full context
        """
        # Build LogQL query
        labels = {'job': 'code_evolver_bugcatcher'}

        if tool_name:
            labels['tool_name'] = tool_name
        if workflow_id:
            labels['workflow_id'] = workflow_id
        if severity:
            labels['severity'] = severity

        # Create label selector
        label_selector = ','.join(f'{k}="{v}"' for k, v in labels.items())
        query = f'{{{label_selector}}}'

        # Calculate time range
        end_time = int(datetime.now().timestamp() * 1e9)  # nanoseconds
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
            exceptions = []
            for stream in data.get('data', {}).get('result', []):
                for value in stream.get('values', []):
                    timestamp_ns, log_line = value
                    try:
                        exception_data = json.loads(log_line)
                        exception_data['timestamp'] = timestamp_ns
                        exceptions.append(exception_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse log line: {log_line[:100]}")

            return exceptions

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to query Loki: {e}")
            return []

    def analyze_exception_patterns(
        self,
        exceptions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in captured exceptions.

        Args:
            exceptions: List of exception records

        Returns:
            Analysis with patterns, frequencies, common causes
        """
        if not exceptions:
            return {'total': 0, 'patterns': []}

        # Group by exception type
        by_type = {}
        by_tool = {}
        by_workflow = {}

        for exc in exceptions:
            exc_type = exc.get('exception_type', 'Unknown')
            tool_name = exc.get('tool_name', 'Unknown')
            workflow_id = exc.get('workflow_id', 'Unknown')

            # Count by type
            if exc_type not in by_type:
                by_type[exc_type] = []
            by_type[exc_type].append(exc)

            # Count by tool
            if tool_name not in by_tool:
                by_tool[tool_name] = []
            by_tool[tool_name].append(exc)

            # Count by workflow
            if workflow_id not in by_workflow:
                by_workflow[workflow_id] = []
            by_workflow[workflow_id].append(exc)

        # Build analysis
        analysis = {
            'total_exceptions': len(exceptions),
            'by_exception_type': {
                k: len(v) for k, v in sorted(
                    by_type.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )
            },
            'by_tool': {
                k: len(v) for k, v in sorted(
                    by_tool.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )
            },
            'by_workflow': {
                k: len(v) for k, v in sorted(
                    by_workflow.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )
            },
            'top_failing_tool': max(by_tool.items(), key=lambda x: len(x[1]))[0] if by_tool else None,
            'most_common_exception': max(by_type.items(), key=lambda x: len(x[1]))[0] if by_type else None,
            'patterns': self._identify_patterns(exceptions)
        }

        return analysis

    def _identify_patterns(
        self,
        exceptions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identify common patterns in exceptions.

        Args:
            exceptions: List of exception records

        Returns:
            List of identified patterns
        """
        patterns = []

        # Pattern 1: Same error message
        error_messages = {}
        for exc in exceptions:
            msg = exc.get('exception_message', '')[:100]  # First 100 chars
            if msg:
                if msg not in error_messages:
                    error_messages[msg] = []
                error_messages[msg].append(exc)

        for msg, exc_list in error_messages.items():
            if len(exc_list) >= 3:  # Pattern if 3+ occurrences
                patterns.append({
                    'type': 'repeated_error_message',
                    'message': msg,
                    'count': len(exc_list),
                    'tool_names': list(set(e.get('tool_name') for e in exc_list)),
                    'sample_exception': exc_list[0]
                })

        # Pattern 2: Same tool failing repeatedly
        # (Already in by_tool, but highlight if > 10 failures)
        # This is handled in the analysis dict

        return patterns

    def reproduce_exception(
        self,
        exception_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Attempt to reproduce an exception with captured state.

        Args:
            exception_data: Exception record from BugCatcher

        Returns:
            Reproduction result with success status and details
        """
        tool_name = exception_data.get('tool_name')
        inputs = exception_data.get('inputs', {})
        workflow_id = exception_data.get('workflow_id')
        step_id = exception_data.get('step_id')

        logger.info(f"Attempting to reproduce exception in {tool_name}")

        # This would integrate with actual tool execution
        # For now, return structure for auto-repair integration
        return {
            'tool_name': tool_name,
            'reproduced': False,  # Would be True if successfully reproduced
            'exception_type': exception_data.get('exception_type'),
            'exception_message': exception_data.get('exception_message'),
            'inputs': inputs,
            'context': {
                'workflow_id': workflow_id,
                'step_id': step_id
            },
            'traceback': exception_data.get('traceback'),
            'suggested_fixes': self._generate_suggested_fixes(exception_data)
        }

    def _generate_suggested_fixes(
        self,
        exception_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate suggested fixes based on exception data.

        Args:
            exception_data: Exception record

        Returns:
            List of suggested fixes
        """
        fixes = []
        exc_type = exception_data.get('exception_type')
        exc_msg = exception_data.get('exception_message', '')

        # Pattern-based fix suggestions
        if exc_type == 'ValueError':
            if 'invalid literal' in exc_msg.lower():
                fixes.append({
                    'type': 'input_validation',
                    'description': 'Add input validation before conversion',
                    'priority': 'high',
                    'suggested_code': 'if not isinstance(value, expected_type): raise TypeError(...)'
                })

        if exc_type == 'KeyError':
            fixes.append({
                'type': 'safe_dict_access',
                'description': 'Use dict.get() instead of direct access',
                'priority': 'medium',
                'suggested_code': 'value = data.get(key, default)'
            })

        if exc_type == 'AttributeError':
            fixes.append({
                'type': 'check_attribute',
                'description': 'Check attribute exists before access',
                'priority': 'medium',
                'suggested_code': 'if hasattr(obj, attr): ...'
            })

        if exc_type in ('ConnectionError', 'Timeout'):
            fixes.append({
                'type': 'retry_logic',
                'description': 'Add retry logic with exponential backoff',
                'priority': 'high',
                'suggested_code': 'for attempt in range(max_retries): ...'
            })

        if exc_type == 'FileNotFoundError':
            fixes.append({
                'type': 'path_validation',
                'description': 'Validate file exists before operation',
                'priority': 'high',
                'suggested_code': 'if not os.path.exists(path): ...'
            })

        return fixes

    def generate_test_case(
        self,
        exception_data: Dict[str, Any]
    ) -> str:
        """
        Generate a test case from captured exception data.

        Args:
            exception_data: Exception record

        Returns:
            Test case code as string
        """
        tool_name = exception_data.get('tool_name', 'unknown_tool')
        exc_type = exception_data.get('exception_type', 'Exception')
        inputs = exception_data.get('inputs', {})

        test_code = f"""
# Test case generated from BugCatcher data
# Tool: {tool_name}
# Exception: {exc_type}

import pytest

def test_{tool_name}_exception():
    \"\"\"
    Test case for {exc_type} in {tool_name}.

    Generated from captured exception at {exception_data.get('timestamp', 'unknown time')}.
    \"\"\"
    # Inputs from captured exception
    inputs = {json.dumps(inputs, indent=4)}

    # Expected exception
    with pytest.raises({exc_type}):
        # This should reproduce the exception
        result = {tool_name}(**inputs)

def test_{tool_name}_fix():
    \"\"\"
    Test case for fixed version of {tool_name}.

    Should handle the input that caused {exc_type}.
    \"\"\"
    # Same inputs as failing case
    inputs = {json.dumps(inputs, indent=4)}

    # Should not raise exception after fix
    result = {tool_name}(**inputs)
    assert result is not None
"""
        return test_code

    def get_exception_report(
        self,
        tool_name: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> str:
        """
        Generate a comprehensive exception report.

        Args:
            tool_name: Filter by tool name
            workflow_id: Filter by workflow ID

        Returns:
            Human-readable exception report
        """
        # Query exceptions
        exceptions = self.query_exceptions(
            tool_name=tool_name,
            workflow_id=workflow_id
        )

        if not exceptions:
            return "No exceptions found in the specified time range."

        # Analyze patterns
        analysis = self.analyze_exception_patterns(exceptions)

        # Build report
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("BugAnalyzer Exception Report")
        report_lines.append("=" * 80)
        report_lines.append(f"Time Range: Last {self.lookback_hours} hours")
        report_lines.append(f"Total Exceptions: {analysis['total_exceptions']}")
        report_lines.append("")

        report_lines.append("Top Failing Tools:")
        for tool, count in list(analysis['by_tool'].items())[:5]:
            report_lines.append(f"  - {tool}: {count} exceptions")
        report_lines.append("")

        report_lines.append("Most Common Exception Types:")
        for exc_type, count in list(analysis['by_exception_type'].items())[:5]:
            report_lines.append(f"  - {exc_type}: {count} occurrences")
        report_lines.append("")

        if analysis['patterns']:
            report_lines.append("Identified Patterns:")
            for i, pattern in enumerate(analysis['patterns'][:5], 1):
                report_lines.append(f"  {i}. {pattern['type']}")
                report_lines.append(f"     Count: {pattern['count']}")
                report_lines.append(f"     Tools: {', '.join(pattern['tool_names'])}")
                report_lines.append("")

        report_lines.append("=" * 80)

        return "\n".join(report_lines)


def analyze_bugs(
    tool_name: Optional[str] = None,
    workflow_id: Optional[str] = None,
    generate_tests: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to analyze bugs and generate fixes.

    Args:
        tool_name: Filter by tool name
        workflow_id: Filter by workflow ID
        generate_tests: Whether to generate test cases

    Returns:
        Analysis results with suggested fixes
    """
    analyzer = BugAnalyzer()

    # Query exceptions
    exceptions = analyzer.query_exceptions(
        tool_name=tool_name,
        workflow_id=workflow_id
    )

    if not exceptions:
        return {'error': 'No exceptions found'}

    # Analyze patterns
    analysis = analyzer.analyze_exception_patterns(exceptions)

    # Generate reproduction attempts and fixes for top issues
    reproduction_results = []
    for exc in exceptions[:5]:  # Top 5 exceptions
        result = analyzer.reproduce_exception(exc)
        reproduction_results.append(result)

    # Generate test cases if requested
    test_cases = []
    if generate_tests:
        for exc in exceptions[:5]:
            test_code = analyzer.generate_test_case(exc)
            test_cases.append({
                'tool_name': exc.get('tool_name'),
                'exception_type': exc.get('exception_type'),
                'test_code': test_code
            })

    return {
        'analysis': analysis,
        'exceptions': exceptions,
        'reproduction_results': reproduction_results,
        'test_cases': test_cases if generate_tests else None,
        'report': analyzer.get_exception_report(tool_name, workflow_id)
    }
