#!/usr/bin/env python3
"""
Performance Regression Evaluator using LLM assessment.
Determines if performance changes are reasonable given requirement changes.
Prevents getting locked into never accepting performance regressions when justified.
"""
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PerformanceSnapshot:
    """A snapshot of performance metrics at a point in time."""
    execution_time_ms: float
    memory_usage_kb: float
    timestamp: str
    version: str
    complexity_score: Optional[float] = None
    security_issues: Optional[int] = None
    correctness_score: Optional[float] = None


@dataclass
class RequirementChange:
    """Description of a requirement change."""
    previous_requirement: str
    new_requirement: str
    change_summary: str
    feature_additions: List[str]
    feature_removals: List[str]
    breaking_changes: List[str]


@dataclass
class EvaluationResult:
    """Result from LLM evaluation of regression reasonableness."""
    score: int  # 0-100
    reasoning: str
    recommendation: str  # "ACCEPT", "REJECT", "REVIEW"
    confidence: str  # "high", "medium", "low"
    llm_model: str
    timestamp: str


class StaticAnalysisCollector:
    """Collects static analysis findings for context."""

    @staticmethod
    def analyze_code(code: str, language: str = "python") -> Dict[str, Any]:
        """
        Analyze code for complexity, correctness, and security.

        Args:
            code: Source code to analyze
            language: Programming language (default: python)

        Returns:
            Dictionary with analysis findings
        """
        findings = {
            "complexity": StaticAnalysisCollector._analyze_complexity(code),
            "correctness": StaticAnalysisCollector._analyze_correctness(code),
            "security": StaticAnalysisCollector._analyze_security(code),
            "code_quality": StaticAnalysisCollector._analyze_quality(code)
        }
        return findings

    @staticmethod
    def _analyze_complexity(code: str) -> Dict[str, Any]:
        """Analyze code complexity using radon or similar."""
        try:
            # Try using radon for complexity analysis
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['radon', 'cc', '-s', '-a', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    # Parse radon output
                    output = result.stdout
                    # Extract average complexity
                    if "Average complexity:" in output:
                        complexity_line = [l for l in output.split('\n') if 'Average complexity:' in l]
                        if complexity_line:
                            complexity_str = complexity_line[0].split(':')[1].strip().split()[0]
                            return {
                                "average_complexity": float(complexity_str),
                                "grade": complexity_line[0].split('(')[-1].strip(')'),
                                "tool": "radon"
                            }
            finally:
                Path(temp_file).unlink(missing_ok=True)
        except Exception as e:
            pass

        # Fallback: simple line/function count
        lines = code.split('\n')
        non_empty_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]

        return {
            "lines_of_code": len(non_empty_lines),
            "estimated_complexity": "medium" if len(non_empty_lines) > 50 else "low",
            "tool": "simple_counter"
        }

    @staticmethod
    def _analyze_correctness(code: str) -> Dict[str, Any]:
        """Check for syntax errors and type issues."""
        try:
            # Basic syntax check
            compile(code, '<string>', 'exec')
            syntax_valid = True
            syntax_error = None
        except SyntaxError as e:
            syntax_valid = False
            syntax_error = str(e)

        return {
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_error,
            "tool": "python_compile"
        }

    @staticmethod
    def _analyze_security(code: str) -> Dict[str, Any]:
        """Check for security issues using bandit or similar."""
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['bandit', '-f', 'json', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                    try:
                        bandit_output = json.loads(result.stdout)
                        issues = bandit_output.get('results', [])

                        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
                        for issue in issues:
                            severity = issue.get('issue_severity', 'UNDEFINED')
                            if severity in severity_counts:
                                severity_counts[severity] += 1

                        return {
                            "total_issues": len(issues),
                            "severity_counts": severity_counts,
                            "tool": "bandit"
                        }
                    except json.JSONDecodeError:
                        pass
            finally:
                Path(temp_file).unlink(missing_ok=True)
        except Exception as e:
            pass

        # Fallback: simple pattern matching
        dangerous_patterns = [
            'eval(', 'exec(', 'pickle.loads', '__import__',
            'os.system', 'subprocess.call'
        ]

        issues_found = sum(1 for pattern in dangerous_patterns if pattern in code)

        return {
            "potential_issues": issues_found,
            "tool": "pattern_matching"
        }

    @staticmethod
    def _analyze_quality(code: str) -> Dict[str, Any]:
        """Analyze code quality metrics."""
        lines = code.split('\n')

        # Count docstrings
        docstring_count = code.count('"""') // 2 + code.count("'''") // 2

        # Count functions
        function_count = sum(1 for line in lines if line.strip().startswith('def '))

        # Count classes
        class_count = sum(1 for line in lines if line.strip().startswith('class '))

        # Count comments
        comment_count = sum(1 for line in lines if line.strip().startswith('#'))

        return {
            "docstring_count": docstring_count,
            "function_count": function_count,
            "class_count": class_count,
            "comment_count": comment_count,
            "documentation_ratio": docstring_count / max(function_count + class_count, 1)
        }


class PerformanceRegressionEvaluator:
    """Evaluates performance regressions using LLM assessment."""

    def __init__(self, llm_model: str = "qwen2.5-coder:3b"):
        self.llm_model = llm_model

    def evaluate_regression(
        self,
        old_metrics: PerformanceSnapshot,
        new_metrics: PerformanceSnapshot,
        requirement_change: RequirementChange,
        old_code: str,
        new_code: str
    ) -> EvaluationResult:
        """
        Evaluate if performance regression is reasonable given requirement changes.

        Args:
            old_metrics: Performance metrics from previous version
            new_metrics: Performance metrics from new version
            requirement_change: Description of requirement changes
            old_code: Previous version source code
            new_code: New version source code

        Returns:
            EvaluationResult with LLM assessment
        """
        # Calculate performance delta
        time_delta_pct = ((new_metrics.execution_time_ms - old_metrics.execution_time_ms)
                         / old_metrics.execution_time_ms * 100)
        memory_delta_pct = ((new_metrics.memory_usage_kb - old_metrics.memory_usage_kb)
                           / old_metrics.memory_usage_kb * 100)

        # Collect static analysis
        old_analysis = StaticAnalysisCollector.analyze_code(old_code)
        new_analysis = StaticAnalysisCollector.analyze_code(new_code)

        # Build prompt for LLM
        prompt = self._build_evaluation_prompt(
            old_metrics, new_metrics,
            time_delta_pct, memory_delta_pct,
            requirement_change,
            old_analysis, new_analysis
        )

        # Call LLM
        llm_response = self._call_llm(prompt)

        # Parse LLM response
        evaluation = self._parse_llm_response(llm_response)

        return evaluation

    def _build_evaluation_prompt(
        self,
        old_metrics: PerformanceSnapshot,
        new_metrics: PerformanceSnapshot,
        time_delta_pct: float,
        memory_delta_pct: float,
        requirement_change: RequirementChange,
        old_analysis: Dict[str, Any],
        new_analysis: Dict[str, Any]
    ) -> str:
        """Build the evaluation prompt for the LLM."""

        prompt = f"""# Performance Regression Assessment

You are evaluating whether a performance regression is reasonable given changes in requirements.

## Performance Changes

**Execution Time:**
- Old: {old_metrics.execution_time_ms:.4f} ms
- New: {new_metrics.execution_time_ms:.4f} ms
- Change: {time_delta_pct:+.2f}%

**Memory Usage:**
- Old: {old_metrics.memory_usage_kb:.2f} KB
- New: {new_metrics.memory_usage_kb:.2f} KB
- Change: {memory_delta_pct:+.2f}%

## Requirement Changes

**Previous Requirement:**
{requirement_change.previous_requirement}

**New Requirement:**
{requirement_change.new_requirement}

**Change Summary:**
{requirement_change.change_summary}

**Feature Additions:**
{json.dumps(requirement_change.feature_additions, indent=2)}

**Feature Removals:**
{json.dumps(requirement_change.feature_removals, indent=2)}

**Breaking Changes:**
{json.dumps(requirement_change.breaking_changes, indent=2)}

## Static Analysis Comparison

**Old Version:**
- Complexity: {old_analysis.get('complexity', {})}
- Security Issues: {old_analysis.get('security', {}).get('total_issues', 0)}
- Code Quality: {old_analysis.get('code_quality', {})}

**New Version:**
- Complexity: {new_analysis.get('complexity', {})}
- Security Issues: {new_analysis.get('security', {}).get('total_issues', 0)}
- Code Quality: {new_analysis.get('code_quality', {})}

## Your Task

Given these changes since the last test for this tool, is the performance change reasonable for the requirement changes?

Answer with a score between 0 (absolutely not reasonable) and 100 (completely reasonable).

Also provide:
1. Your reasoning (2-3 sentences)
2. A recommendation: ACCEPT, REJECT, or REVIEW
3. Your confidence level: high, medium, or low

Format your response as JSON:
```json
{{
  "score": <0-100>,
  "reasoning": "<your reasoning>",
  "recommendation": "<ACCEPT|REJECT|REVIEW>",
  "confidence": "<high|medium|low>"
}}
```

Consider:
- If significant features were added, moderate performance regression may be acceptable
- If security improvements were made, some performance cost is reasonable
- If complexity decreased but performance worsened, this needs investigation
- If no meaningful features were added but performance degraded significantly, this is concerning
- If the regression is < 10% and features were added, this is usually acceptable
- If the regression is > 50%, it needs strong justification
"""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the evaluation prompt."""
        try:
            # Use ollama to call the LLM
            result = subprocess.run(
                ['ollama', 'run', self.llm_model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                raise Exception(f"LLM call failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise Exception("LLM call timed out")
        except FileNotFoundError:
            raise Exception("ollama not found. Please install ollama.")

    def _parse_llm_response(self, response: str) -> EvaluationResult:
        """Parse the LLM's JSON response."""
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                return EvaluationResult(
                    score=int(data.get('score', 50)),
                    reasoning=data.get('reasoning', 'No reasoning provided'),
                    recommendation=data.get('recommendation', 'REVIEW'),
                    confidence=data.get('confidence', 'medium'),
                    llm_model=self.llm_model,
                    timestamp=datetime.now().isoformat()
                )
            else:
                raise ValueError("No JSON found in LLM response")

        except Exception as e:
            # Fallback response if parsing fails
            return EvaluationResult(
                score=50,
                reasoning=f"Failed to parse LLM response: {e}",
                recommendation="REVIEW",
                confidence="low",
                llm_model=self.llm_model,
                timestamp=datetime.now().isoformat()
            )


def main():
    """CLI interface for performance regression evaluator."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: performance_regression_evaluator.py <command> [args...]",
            "commands": {
                "evaluate": "Evaluate performance regression",
                "analyze": "Run static analysis only"
            }
        }))
        sys.exit(1)

    command = sys.argv[1]

    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
        sys.exit(1)

    if command == "evaluate":
        # Evaluate regression
        old_metrics = PerformanceSnapshot(**input_data['old_metrics'])
        new_metrics = PerformanceSnapshot(**input_data['new_metrics'])
        requirement_change = RequirementChange(**input_data['requirement_change'])
        old_code = input_data['old_code']
        new_code = input_data['new_code']
        llm_model = input_data.get('llm_model', 'qwen2.5-coder:3b')

        evaluator = PerformanceRegressionEvaluator(llm_model=llm_model)

        try:
            result = evaluator.evaluate_regression(
                old_metrics, new_metrics,
                requirement_change,
                old_code, new_code
            )

            print(json.dumps({
                "success": True,
                "evaluation": asdict(result),
                "performance_delta": {
                    "execution_time_pct": ((new_metrics.execution_time_ms - old_metrics.execution_time_ms)
                                          / old_metrics.execution_time_ms * 100),
                    "memory_pct": ((new_metrics.memory_usage_kb - old_metrics.memory_usage_kb)
                                  / old_metrics.memory_usage_kb * 100)
                }
            }, indent=2))
        except Exception as e:
            print(json.dumps({
                "success": False,
                "error": str(e)
            }))
            sys.exit(1)

    elif command == "analyze":
        # Run static analysis only
        code = input_data.get('code', '')

        analysis = StaticAnalysisCollector.analyze_code(code)

        print(json.dumps({
            "success": True,
            "analysis": analysis
        }, indent=2))

    else:
        print(json.dumps({
            "error": f"Unknown command: {command}",
            "available_commands": ["evaluate", "analyze"]
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
