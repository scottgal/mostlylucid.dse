"""
Static Analysis Result Tracker

Captures and stores static analysis results for code quality tracking,
RAG retrieval, and optimizer feedback loops.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import time


@dataclass
class ValidatorResult:
    """Result from a single static validator."""
    validator_name: str
    passed: bool
    exit_code: int
    output: str
    execution_time_ms: float
    auto_fixed: bool = False
    fix_applied: str = ""


@dataclass
class StaticAnalysisReport:
    """Complete static analysis report for a code file."""
    node_id: str
    file_path: str
    timestamp: float

    # Overall metrics
    total_validators: int
    passed_validators: int
    failed_validators: int
    auto_fixes_applied: int

    # Individual validator results
    results: List[ValidatorResult]

    # Quality scores
    syntax_score: float  # 0-1
    structure_score: float  # 0-1
    import_score: float  # 0-1
    usage_score: float  # 0-1
    overall_score: float  # 0-1

    # Performance metrics
    total_analysis_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'node_id': self.node_id,
            'file_path': self.file_path,
            'timestamp': self.timestamp,
            'metrics': {
                'total_validators': self.total_validators,
                'passed_validators': self.passed_validators,
                'failed_validators': self.failed_validators,
                'auto_fixes_applied': self.auto_fixes_applied,
                'syntax_score': self.syntax_score,
                'structure_score': self.structure_score,
                'import_score': self.import_score,
                'usage_score': self.usage_score,
                'overall_score': self.overall_score,
                'total_analysis_time_ms': self.total_analysis_time_ms
            },
            'results': [asdict(r) for r in self.results]
        }

    def get_quality_summary(self) -> str:
        """Get human-readable quality summary."""
        if self.overall_score >= 0.9:
            grade = "A+"
        elif self.overall_score >= 0.8:
            grade = "A"
        elif self.overall_score >= 0.7:
            grade = "B"
        elif self.overall_score >= 0.6:
            grade = "C"
        else:
            grade = "D"

        return (
            f"Quality Grade: {grade} ({self.overall_score:.2f})\n"
            f"  Validators Passed: {self.passed_validators}/{self.total_validators}\n"
            f"  Auto-Fixes Applied: {self.auto_fixes_applied}\n"
            f"  Syntax: {self.syntax_score:.2f} | "
            f"Structure: {self.structure_score:.2f} | "
            f"Imports: {self.import_score:.2f} | "
            f"Usage: {self.usage_score:.2f}"
        )


class StaticAnalysisTracker:
    """Tracks static analysis results and stores them in registry and RAG."""

    # Validator definitions with categories
    VALIDATORS = [
        {
            'name': 'Python Syntax',
            'category': 'syntax',
            'script': 'python_syntax_validator.py',
            'priority': 200,
            'auto_fix': False
        },
        {
            'name': 'Main Function',
            'category': 'structure',
            'script': 'main_function_checker.py',
            'priority': 180,
            'auto_fix': False
        },
        {
            'name': 'JSON Output',
            'category': 'structure',
            'script': 'json_output_validator.py',
            'priority': 150,
            'auto_fix': False
        },
        {
            'name': 'Stdin Usage',
            'category': 'usage',
            'script': 'stdin_usage_validator.py',
            'priority': 140,
            'auto_fix': False
        },
        {
            'name': 'Node Runtime Import',
            'category': 'import',
            'script': 'node_runtime_import_validator.py',
            'priority': 100,
            'auto_fix': True
        },
        {
            'name': 'call_tool() Usage',
            'category': 'usage',
            'script': 'call_tool_validator.py',
            'priority': 90,
            'auto_fix': False
        },
    ]

    def __init__(self, tools_dir: str = "tools/executable"):
        """
        Initialize tracker.

        Args:
            tools_dir: Directory containing validator scripts
        """
        self.tools_dir = Path(tools_dir)

    def run_validator(
        self,
        validator: Dict[str, Any],
        code_file: str,
        auto_fix: bool = True
    ) -> ValidatorResult:
        """
        Run a single validator.

        Args:
            validator: Validator configuration
            code_file: Path to code file
            auto_fix: Apply auto-fix if available

        Returns:
            ValidatorResult
        """
        script_path = self.tools_dir / validator['script']

        # Build command
        cmd = ['python', str(script_path), code_file]

        # Add --fix flag if auto-fix is enabled and available
        if auto_fix and validator['auto_fix']:
            cmd.append('--fix')

        # Run validator
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        # Check if auto-fix was applied
        auto_fixed = 'FIXED' in result.stdout if auto_fix else False

        return ValidatorResult(
            validator_name=validator['name'],
            passed=result.returncode == 0,
            exit_code=result.returncode,
            output=result.stdout.strip(),
            execution_time_ms=execution_time,
            auto_fixed=auto_fixed,
            fix_applied=result.stdout.strip() if auto_fixed else ""
        )

    def analyze_file(
        self,
        code_file: str,
        node_id: str,
        auto_fix: bool = True
    ) -> StaticAnalysisReport:
        """
        Run all validators on a code file.

        Args:
            code_file: Path to code file
            node_id: Node identifier
            auto_fix: Apply auto-fixes where available

        Returns:
            StaticAnalysisReport with all results
        """
        start_time = time.time()
        results = []

        # Sort validators by priority (higher first)
        sorted_validators = sorted(
            self.VALIDATORS,
            key=lambda v: v['priority'],
            reverse=True
        )

        # Run each validator
        for validator in sorted_validators:
            result = self.run_validator(validator, code_file, auto_fix)
            results.append(result)

        # Calculate category scores
        category_scores = self._calculate_category_scores(results)

        # Calculate overall metrics
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        auto_fixed = sum(1 for r in results if r.auto_fixed)

        # Calculate overall score (weighted by category)
        overall_score = (
            category_scores['syntax'] * 0.3 +
            category_scores['structure'] * 0.3 +
            category_scores['import'] * 0.2 +
            category_scores['usage'] * 0.2
        )

        total_time = (time.time() - start_time) * 1000

        return StaticAnalysisReport(
            node_id=node_id,
            file_path=code_file,
            timestamp=time.time(),
            total_validators=len(results),
            passed_validators=passed,
            failed_validators=failed,
            auto_fixes_applied=auto_fixed,
            results=results,
            syntax_score=category_scores['syntax'],
            structure_score=category_scores['structure'],
            import_score=category_scores['import'],
            usage_score=category_scores['usage'],
            overall_score=overall_score,
            total_analysis_time_ms=total_time
        )

    def _calculate_category_scores(
        self,
        results: List[ValidatorResult]
    ) -> Dict[str, float]:
        """
        Calculate scores by category.

        Args:
            results: List of validator results

        Returns:
            Dict mapping category to score (0-1)
        """
        categories = {}

        for validator in self.VALIDATORS:
            category = validator['category']
            if category not in categories:
                categories[category] = {'passed': 0, 'total': 0}

            # Find result for this validator
            result = next((r for r in results if r.validator_name == validator['name']), None)
            if result:
                categories[category]['total'] += 1
                if result.passed:
                    categories[category]['passed'] += 1

        # Calculate scores
        scores = {}
        for category, data in categories.items():
            if data['total'] > 0:
                scores[category] = data['passed'] / data['total']
            else:
                scores[category] = 1.0  # No validators = perfect score

        return scores

    def save_to_registry(
        self,
        report: StaticAnalysisReport,
        registry_path: str = "registry"
    ) -> None:
        """
        Save analysis report to registry.

        Args:
            report: Analysis report
            registry_path: Path to registry directory
        """
        registry_dir = Path(registry_path) / report.node_id

        # Create static_analysis.json
        analysis_file = registry_dir / "static_analysis.json"
        registry_dir.mkdir(parents=True, exist_ok=True)

        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2)

    def save_to_rag(
        self,
        report: StaticAnalysisReport,
        rag_memory: Any
    ) -> None:
        """
        Save quality metrics to RAG for retrieval.

        Args:
            report: Analysis report
            rag_memory: RAG memory instance
        """
        from .rag_memory import ArtifactType

        # Store quality metrics as a pattern artifact
        artifact_id = f"{report.node_id}_static_analysis"

        quality_metadata = {
            'overall_score': report.overall_score,
            'syntax_score': report.syntax_score,
            'structure_score': report.structure_score,
            'import_score': report.import_score,
            'usage_score': report.usage_score,
            'validators_passed': report.passed_validators,
            'validators_total': report.total_validators,
            'auto_fixes_applied': report.auto_fixes_applied,
            'analysis_time_ms': report.total_analysis_time_ms
        }

        # Create searchable content
        content = json.dumps(report.to_dict(), indent=2)

        rag_memory.store_artifact(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.PATTERN,
            name=f"Static Analysis: {report.node_id}",
            description=(
                f"Code quality: {report.overall_score:.2f} "
                f"({report.passed_validators}/{report.total_validators} checks passed)"
            ),
            content=content,
            tags=[
                'static-analysis',
                'code-quality',
                f'score-{int(report.overall_score * 100)}',
                f'fixes-{report.auto_fixes_applied}'
            ],
            metadata=quality_metadata,
            quality_score=report.overall_score
        )
