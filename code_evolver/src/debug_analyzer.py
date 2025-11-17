"""
Debug Data Analyzer for LLM Consumption

Extracts and packages debug data (code, tests, variants, performance metrics)
into optimized formats for higher-level code model analysis.

Focuses on:
- Context window optimization
- Structured data packaging
- Code variant comparison
- Performance correlation analysis
- Intelligent summarization
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import tiktoken  # For token counting

from debug_store import DebugStore


@dataclass
class CodeVariant:
    """Represents a code variant with its performance data"""
    variant_id: str
    code: str
    code_hash: str
    description: str
    test_results: Optional[Dict[str, Any]]
    performance_stats: Dict[str, float]
    execution_count: int
    success_rate: float
    avg_duration_ms: float
    error_samples: List[str]


@dataclass
class AnalysisPackage:
    """
    Complete analysis package for LLM consumption.
    Optimized for context window efficiency.
    """
    session_id: str
    context_type: str  # 'tool', 'workflow', 'step', 'node'
    context_name: str
    summary: str  # High-level summary
    code_variants: List[CodeVariant]
    performance_comparison: Dict[str, Any]
    error_analysis: Dict[str, Any]
    recommendations: List[str]
    raw_samples: List[Dict[str, Any]]  # Representative samples
    metadata: Dict[str, Any]

    def to_markdown(self, max_tokens: Optional[int] = None) -> str:
        """
        Convert to markdown format optimized for LLM consumption.

        Args:
            max_tokens: If specified, will truncate to fit within token budget
        """
        sections = []

        # Header
        sections.append(f"# Debug Analysis: {self.context_name}")
        sections.append(f"\n**Session ID:** {self.session_id}")
        sections.append(f"**Context Type:** {self.context_type}\n")

        # Summary
        sections.append("## Summary\n")
        sections.append(self.summary)

        # Code Variants
        if self.code_variants:
            sections.append("\n## Code Variants\n")
            for i, variant in enumerate(self.code_variants, 1):
                sections.append(f"### Variant {i}: {variant.description}\n")
                sections.append(f"**Variant ID:** `{variant.variant_id}`\n")
                sections.append(f"**Executions:** {variant.execution_count} | ")
                sections.append(f"**Success Rate:** {variant.success_rate:.1%} | ")
                sections.append(f"**Avg Duration:** {variant.avg_duration_ms:.2f}ms\n")

                sections.append("\n**Code:**\n```python\n")
                sections.append(variant.code)
                sections.append("\n```\n")

                if variant.test_results:
                    sections.append("\n**Test Results:**\n")
                    sections.append(f"```json\n{json.dumps(variant.test_results, indent=2)}\n```\n")

                if variant.error_samples:
                    sections.append("\n**Sample Errors:**\n")
                    for error in variant.error_samples[:3]:  # Limit to 3
                        sections.append(f"- {error}\n")

        # Performance Comparison
        sections.append("\n## Performance Comparison\n")
        sections.append("```json\n")
        sections.append(json.dumps(self.performance_comparison, indent=2))
        sections.append("\n```\n")

        # Error Analysis
        if self.error_analysis.get('total_errors', 0) > 0:
            sections.append("\n## Error Analysis\n")
            sections.append(f"**Total Errors:** {self.error_analysis['total_errors']}\n")
            sections.append(f"**Error Rate:** {self.error_analysis['error_rate']:.1%}\n")

            if 'common_errors' in self.error_analysis:
                sections.append("\n**Common Errors:**\n")
                for error_type, count in self.error_analysis['common_errors'][:5]:
                    sections.append(f"- {error_type}: {count} occurrences\n")

        # Recommendations
        if self.recommendations:
            sections.append("\n## Recommendations\n")
            for rec in self.recommendations:
                sections.append(f"- {rec}\n")

        # Raw Samples (limited)
        if self.raw_samples:
            sections.append("\n## Representative Samples\n")
            sections.append(f"Showing {len(self.raw_samples)} representative executions:\n\n")
            for i, sample in enumerate(self.raw_samples[:5], 1):  # Limit to 5
                sections.append(f"### Sample {i}\n")
                sections.append(f"**Status:** {sample.get('status', 'unknown')} | ")
                sections.append(f"**Duration:** {sample.get('duration_ms', 0):.2f}ms\n")

                if sample.get('request_data'):
                    sections.append(f"\n**Request:**\n```json\n{json.dumps(sample['request_data'], indent=2)}\n```\n")

                if sample.get('response_data'):
                    sections.append(f"\n**Response:**\n```json\n{json.dumps(sample['response_data'], indent=2)}\n```\n")

        # Metadata
        sections.append("\n## Metadata\n")
        sections.append(f"```json\n{json.dumps(self.metadata, indent=2)}\n```\n")

        markdown = "\n".join(sections)

        # Truncate if needed
        if max_tokens:
            markdown = self._truncate_to_tokens(markdown, max_tokens)

        return markdown

    def to_json(self) -> str:
        """Convert to JSON format"""
        return json.dumps(asdict(self), indent=2, default=str)

    @staticmethod
    def _truncate_to_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
        """Truncate text to fit within token budget"""
        try:
            encoding = tiktoken.get_encoding(encoding_name)
            tokens = encoding.encode(text)

            if len(tokens) <= max_tokens:
                return text

            # Truncate and add notice
            truncated_tokens = tokens[:max_tokens - 50]  # Reserve space for notice
            truncated_text = encoding.decode(truncated_tokens)
            truncated_text += f"\n\n[...Truncated to fit {max_tokens} token budget...]"

            return truncated_text
        except Exception:
            # Fallback to simple character truncation
            if len(text) > max_tokens * 4:  # Rough estimate: 1 token ≈ 4 chars
                return text[:max_tokens * 4] + "\n\n[...Truncated...]"
            return text


class DebugAnalyzer:
    """
    Analyzes debug data and creates packages for LLM consumption.

    Usage:
        analyzer = DebugAnalyzer(debug_store)

        # Analyze a specific tool/workflow/step
        package = analyzer.analyze_context(
            context_type="tool",
            context_id="http_fetch",
            include_variants=True,
            max_samples=10
        )

        # Export for LLM
        markdown = package.to_markdown(max_tokens=50000)

        # Save to file
        analyzer.export_to_file(package, "analysis.md")
    """

    def __init__(self, debug_store: DebugStore):
        self.store = debug_store

    def analyze_context(
        self,
        context_type: str,
        context_id: Optional[str] = None,
        context_name: Optional[str] = None,
        include_variants: bool = True,
        max_samples: int = 10,
        error_sample_limit: int = 5
    ) -> AnalysisPackage:
        """
        Analyze a specific context and create an analysis package.

        Args:
            context_type: Type of context ('tool', 'workflow', 'step', 'node')
            context_id: Specific ID to analyze (if None, analyzes all of type)
            context_name: Name of context (for filtering)
            include_variants: Whether to include code variant analysis
            max_samples: Maximum number of raw samples to include
            error_sample_limit: Maximum error samples per variant

        Returns:
            AnalysisPackage ready for LLM consumption
        """
        # Build query
        where_clauses = [f"context_type = '{context_type}'"]
        if context_id:
            where_clauses.append(f"context_id = '{context_id}'")
        if context_name:
            where_clauses.append(f"context_name = '{context_name}'")

        where_sql = " AND ".join(where_clauses)

        # Get all records for this context
        records_df = self.store.query_analytics(
            f"SELECT * FROM records WHERE {where_sql} ORDER BY timestamp DESC"
        ).fetchdf()

        if records_df.empty:
            raise ValueError(f"No records found for {context_type}/{context_id}")

        # Generate summary
        summary = self._generate_summary(records_df)

        # Analyze code variants
        code_variants = []
        if include_variants:
            code_variants = self._analyze_variants(records_df, error_sample_limit)

        # Performance comparison
        performance_comparison = self._compare_performance(records_df)

        # Error analysis
        error_analysis = self._analyze_errors(records_df)

        # Generate recommendations
        recommendations = self._generate_recommendations(records_df, code_variants, error_analysis)

        # Extract representative samples
        raw_samples = self._extract_representative_samples(records_df, max_samples)

        # Metadata
        metadata = {
            'total_records': len(records_df),
            'time_span': {
                'first': str(records_df['timestamp'].min()),
                'last': str(records_df['timestamp'].max())
            },
            'unique_variants': len(records_df['variant_id'].dropna().unique()),
            'data_size_mb': records_df.memory_usage(deep=True).sum() / (1024 * 1024)
        }

        return AnalysisPackage(
            session_id=self.store.session_id,
            context_type=context_type,
            context_name=context_name or context_id or "All",
            summary=summary,
            code_variants=code_variants,
            performance_comparison=performance_comparison,
            error_analysis=error_analysis,
            recommendations=recommendations,
            raw_samples=raw_samples,
            metadata=metadata
        )

    def _generate_summary(self, df) -> str:
        """Generate high-level summary"""
        total = len(df)
        success = len(df[df['status'] == 'success'])
        errors = len(df[df['status'] == 'error'])
        avg_duration = df['duration_ms'].mean()
        p95_duration = df['duration_ms'].quantile(0.95)

        summary = f"""
Total Executions: {total}
Success Rate: {success/total:.1%} ({success}/{total})
Error Rate: {errors/total:.1%} ({errors}/{total})
Average Duration: {avg_duration:.2f}ms
P95 Duration: {p95_duration:.2f}ms
Memory Usage: {df['memory_mb'].mean():.2f}MB avg, {df['memory_mb'].max():.2f}MB max
CPU Usage: {df['cpu_percent'].mean():.1f}% avg, {df['cpu_percent'].max():.1f}% max
""".strip()
        return summary

    def _analyze_variants(self, df, error_sample_limit: int) -> List[CodeVariant]:
        """Analyze code variants and their performance"""
        variants = []

        # Group by variant_id
        variant_groups = df.groupby('variant_id', dropna=True)

        for variant_id, group in variant_groups:
            if variant_id is None:
                continue

            # Get code snapshot (take first non-null)
            code = group['code_snapshot'].dropna().iloc[0] if not group['code_snapshot'].dropna().empty else ""
            code_hash = group['code_hash'].dropna().iloc[0] if not group['code_hash'].dropna().empty else ""

            # Performance stats
            performance_stats = {
                'avg_duration_ms': float(group['duration_ms'].mean()),
                'min_duration_ms': float(group['duration_ms'].min()),
                'max_duration_ms': float(group['duration_ms'].max()),
                'p95_duration_ms': float(group['duration_ms'].quantile(0.95)),
                'avg_memory_mb': float(group['memory_mb'].mean()),
                'avg_cpu_percent': float(group['cpu_percent'].mean())
            }

            # Success rate
            success_count = len(group[group['status'] == 'success'])
            total_count = len(group)
            success_rate = success_count / total_count if total_count > 0 else 0.0

            # Error samples
            error_records = group[group['status'] == 'error']
            error_samples = error_records['error'].dropna().head(error_sample_limit).tolist()

            # Test results (if available in metadata)
            test_results = None
            if 'metadata' in group.columns and not group['metadata'].dropna().empty:
                try:
                    first_metadata = json.loads(group['metadata'].dropna().iloc[0])
                    test_results = first_metadata.get('test_results')
                except (json.JSONDecodeError, KeyError):
                    pass

            variants.append(CodeVariant(
                variant_id=str(variant_id),
                code=code,
                code_hash=code_hash,
                description=f"Variant {variant_id[:8]}",
                test_results=test_results,
                performance_stats=performance_stats,
                execution_count=total_count,
                success_rate=success_rate,
                avg_duration_ms=performance_stats['avg_duration_ms'],
                error_samples=error_samples
            ))

        # Sort by performance (avg duration)
        variants.sort(key=lambda v: v.avg_duration_ms)

        return variants

    def _compare_performance(self, df) -> Dict[str, Any]:
        """Compare performance across different dimensions"""
        comparison = {
            'overall': {
                'total_executions': len(df),
                'avg_duration_ms': float(df['duration_ms'].mean()),
                'median_duration_ms': float(df['duration_ms'].median()),
                'p95_duration_ms': float(df['duration_ms'].quantile(0.95)),
                'p99_duration_ms': float(df['duration_ms'].quantile(0.99)),
                'std_duration_ms': float(df['duration_ms'].std())
            },
            'by_status': {}
        }

        # Performance by status
        for status in df['status'].unique():
            status_df = df[df['status'] == status]
            comparison['by_status'][status] = {
                'count': len(status_df),
                'avg_duration_ms': float(status_df['duration_ms'].mean())
            }

        # Performance by variant (if available)
        if 'variant_id' in df.columns and df['variant_id'].notna().any():
            comparison['by_variant'] = {}
            for variant_id in df['variant_id'].dropna().unique():
                variant_df = df[df['variant_id'] == variant_id]
                comparison['by_variant'][str(variant_id)[:8]] = {
                    'count': len(variant_df),
                    'avg_duration_ms': float(variant_df['duration_ms'].mean()),
                    'success_rate': float(len(variant_df[variant_df['status'] == 'success']) / len(variant_df))
                }

        return comparison

    def _analyze_errors(self, df) -> Dict[str, Any]:
        """Analyze error patterns"""
        error_df = df[df['status'] == 'error']
        total_errors = len(error_df)
        total_records = len(df)

        analysis = {
            'total_errors': total_errors,
            'error_rate': total_errors / total_records if total_records > 0 else 0.0,
            'common_errors': []
        }

        if total_errors > 0:
            # Count error types
            error_counts = defaultdict(int)
            for error in error_df['error'].dropna():
                # Extract first line or first 100 chars as error type
                error_type = str(error).split('\n')[0][:100]
                error_counts[error_type] += 1

            # Sort by frequency
            analysis['common_errors'] = sorted(
                error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]  # Top 10

        return analysis

    def _generate_recommendations(
        self,
        df,
        variants: List[CodeVariant],
        error_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Performance recommendations
        p95_duration = df['duration_ms'].quantile(0.95)
        if p95_duration > 1000:
            recommendations.append(
                f"⚠️ P95 duration is {p95_duration:.0f}ms - consider optimization"
            )

        # Error rate recommendations
        error_rate = error_analysis['error_rate']
        if error_rate > 0.1:
            recommendations.append(
                f"🔴 High error rate ({error_rate:.1%}) - investigate common failure patterns"
            )
        elif error_rate > 0.05:
            recommendations.append(
                f"⚠️ Moderate error rate ({error_rate:.1%}) - monitor for stability"
            )

        # Variant recommendations
        if len(variants) > 1:
            best_variant = min(variants, key=lambda v: v.avg_duration_ms)
            worst_variant = max(variants, key=lambda v: v.avg_duration_ms)

            if worst_variant.avg_duration_ms > best_variant.avg_duration_ms * 1.5:
                speedup = (worst_variant.avg_duration_ms / best_variant.avg_duration_ms - 1) * 100
                recommendations.append(
                    f"✅ Variant {best_variant.variant_id[:8]} is {speedup:.0f}% faster than {worst_variant.variant_id[:8]} - consider adopting"
                )

        # Memory recommendations
        max_memory = df['memory_mb'].max()
        if max_memory > 1000:
            recommendations.append(
                f"⚠️ High memory usage detected ({max_memory:.0f}MB) - investigate memory leaks"
            )

        # Success rate recommendations
        if variants:
            for variant in variants:
                if variant.success_rate < 0.9 and variant.execution_count > 5:
                    recommendations.append(
                        f"🔴 Variant {variant.variant_id[:8]} has low success rate ({variant.success_rate:.1%}) - needs investigation"
                    )

        return recommendations

    def _extract_representative_samples(self, df, max_samples: int) -> List[Dict[str, Any]]:
        """Extract representative samples (mix of success, error, fast, slow)"""
        samples = []

        # Get diverse samples
        # 1. Fastest execution
        fastest = df.nsmallest(1, 'duration_ms')
        samples.extend(self._df_to_sample_dicts(fastest))

        # 2. Slowest execution
        slowest = df.nlargest(1, 'duration_ms')
        samples.extend(self._df_to_sample_dicts(slowest))

        # 3. Median execution
        median_idx = df['duration_ms'].argsort().iloc[len(df) // 2]
        median = df.iloc[[median_idx]]
        samples.extend(self._df_to_sample_dicts(median))

        # 4. Sample errors (if any)
        errors = df[df['status'] == 'error'].head(2)
        samples.extend(self._df_to_sample_dicts(errors))

        # 5. Random samples to fill quota
        remaining = max_samples - len(samples)
        if remaining > 0 and len(df) > len(samples):
            random_samples = df.sample(min(remaining, len(df) - len(samples)))
            samples.extend(self._df_to_sample_dicts(random_samples))

        return samples[:max_samples]

    @staticmethod
    def _df_to_sample_dicts(df) -> List[Dict[str, Any]]:
        """Convert DataFrame rows to sample dictionaries"""
        samples = []
        for _, row in df.iterrows():
            sample = {
                'id': row['id'],
                'timestamp': str(row['timestamp']),
                'status': row['status'],
                'duration_ms': float(row['duration_ms']),
                'memory_mb': float(row['memory_mb']),
                'cpu_percent': float(row['cpu_percent'])
            }

            # Parse JSON fields
            if row.get('request_data'):
                try:
                    sample['request_data'] = json.loads(row['request_data'])
                except (json.JSONDecodeError, TypeError):
                    sample['request_data'] = str(row['request_data'])

            if row.get('response_data'):
                try:
                    sample['response_data'] = json.loads(row['response_data'])
                except (json.JSONDecodeError, TypeError):
                    sample['response_data'] = str(row['response_data'])

            if row.get('error'):
                sample['error'] = row['error']

            samples.append(sample)

        return samples

    def export_to_file(
        self,
        package: AnalysisPackage,
        output_path: str,
        format: str = "markdown",
        max_tokens: Optional[int] = None
    ):
        """
        Export analysis package to file.

        Args:
            package: The analysis package to export
            output_path: Path to output file
            format: 'markdown' or 'json'
            max_tokens: Optional token limit for markdown
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if format == "markdown":
            content = package.to_markdown(max_tokens=max_tokens)
        elif format == "json":
            content = package.to_json()
        else:
            raise ValueError(f"Unsupported format: {format}")

        output_file.write_text(content)

    def compare_sessions(
        self,
        session_stores: List[DebugStore],
        context_type: str,
        context_id: Optional[str] = None
    ) -> str:
        """
        Compare the same context across multiple debug sessions.

        Returns:
            Markdown comparison report
        """
        sections = []
        sections.append(f"# Cross-Session Comparison: {context_type}")
        sections.append(f"\n**Sessions:** {len(session_stores)}\n")

        comparison_data = []

        for store in session_stores:
            analyzer = DebugAnalyzer(store)
            try:
                package = analyzer.analyze_context(
                    context_type=context_type,
                    context_id=context_id,
                    include_variants=False,
                    max_samples=0
                )

                comparison_data.append({
                    'session_id': store.session_id,
                    'total_executions': package.metadata['total_records'],
                    'avg_duration_ms': package.performance_comparison['overall']['avg_duration_ms'],
                    'error_rate': package.error_analysis['error_rate']
                })
            except ValueError:
                continue

        if comparison_data:
            sections.append("## Performance Comparison\n")
            sections.append("| Session | Executions | Avg Duration | Error Rate |")
            sections.append("|---------|-----------|--------------|------------|")

            for data in comparison_data:
                sections.append(
                    f"| {data['session_id'][:12]}... | "
                    f"{data['total_executions']} | "
                    f"{data['avg_duration_ms']:.2f}ms | "
                    f"{data['error_rate']:.1%} |"
                )

        return "\n".join(sections)

    def get_optimization_candidates(
        self,
        min_executions: int = 10,
        min_duration_ms: float = 500.0
    ) -> List[Dict[str, Any]]:
        """
        Find contexts that are good candidates for optimization.

        Returns:
            List of optimization candidates with details
        """
        # Query for contexts with significant usage and duration
        results = self.store.query_analytics(f"""
            SELECT
                context_type,
                context_id,
                context_name,
                COUNT(*) as execution_count,
                AVG(duration_ms) as avg_duration,
                SUM(duration_ms) as total_duration,
                AVG(memory_mb) as avg_memory,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as error_rate
            FROM records
            GROUP BY context_type, context_id, context_name
            HAVING COUNT(*) >= {min_executions}
               AND AVG(duration_ms) >= {min_duration_ms}
            ORDER BY total_duration DESC
        """).fetchdf()

        candidates = []
        for _, row in results.iterrows():
            candidates.append({
                'context_type': row['context_type'],
                'context_id': row['context_id'],
                'context_name': row['context_name'],
                'execution_count': int(row['execution_count']),
                'avg_duration_ms': float(row['avg_duration']),
                'total_duration_ms': float(row['total_duration']),
                'avg_memory_mb': float(row['avg_memory']),
                'error_rate': float(row['error_rate']),
                'optimization_score': self._calculate_optimization_score(row)
            })

        # Sort by optimization score
        candidates.sort(key=lambda x: x['optimization_score'], reverse=True)

        return candidates

    @staticmethod
    def _calculate_optimization_score(row) -> float:
        """
        Calculate optimization priority score.

        Higher score = higher priority for optimization.
        Factors:
        - Total time spent (execution_count * avg_duration)
        - Error rate
        - Average duration
        """
        total_time = row['execution_count'] * row['avg_duration']
        error_penalty = 1 + (row['error_rate'] * 5)  # Errors increase priority
        duration_factor = row['avg_duration'] / 100  # Normalize

        score = (total_time * error_penalty * duration_factor) / 1000

        return float(score)
