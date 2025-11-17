#!/usr/bin/env python3
"""
CLI for RAG Cluster Optimizer

Allows optimization of RAG artifact clusters via command line or conversational interface.

Usage:
    python optimize_cluster.py --target=cron_parser_cluster
    python optimize_cluster.py --target=all --node_type=function
    python optimize_cluster.py --target=workflow_name --strategy=incremental
"""

import sys
import argparse
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.rag_cluster_optimizer import (
    OptimizerConfigManager,
    NodeType,
    OptimizationStrategy,
    OptimizationCluster,
    RAGClusterOptimizer
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Optimize RAG artifact clusters using iterative self-optimization loop"
    )

    parser.add_argument(
        '--target',
        type=str,
        required=True,
        help="Target to optimize: cluster name, node type, or 'all'"
    )

    parser.add_argument(
        '--node_type',
        type=str,
        choices=['function', 'workflow', 'prompt', 'sub_workflow', 'plan', 'pattern'],
        help="Filter by node type"
    )

    parser.add_argument(
        '--strategy',
        type=str,
        choices=['best_of_breed', 'incremental', 'radical', 'hybrid'],
        help="Optimization strategy to use"
    )

    parser.add_argument(
        '--max_iterations',
        type=int,
        default=10,
        help="Maximum number of optimization iterations"
    )

    parser.add_argument(
        '--apply_trimming',
        type=bool,
        default=True,
        help="Apply trimming policy after optimization"
    )

    parser.add_argument(
        '--config_path',
        type=str,
        default="config/rag_cluster_optimizer.yaml",
        help="Path to custom configuration file"
    )

    parser.add_argument(
        '--output_format',
        type=str,
        choices=['markdown', 'json', 'text'],
        default='markdown',
        help="Output format for report"
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Verbose output"
    )

    return parser.parse_args()


def load_clusters_from_rag(
    target: str,
    node_type: Optional[NodeType] = None
) -> List[OptimizationCluster]:
    """
    Load clusters from RAG memory.

    This is a placeholder - in real implementation, this would:
    1. Connect to RAG memory (Qdrant or local)
    2. Query for clusters matching target and node_type
    3. Return list of OptimizationCluster objects
    """
    logger.info(f"Loading clusters for target: {target}, node_type: {node_type}")

    # Placeholder: Return empty list
    # In real implementation, this would query RAG memory
    clusters = []

    if not clusters:
        logger.warning("No clusters found. This is expected if RAG memory is not configured.")
        logger.info("Returning example cluster for demonstration.")

        # Create example cluster for demonstration
        from src.rag_cluster_optimizer import (
            ArtifactVariant,
            PerformanceMetrics,
            VariantStatus,
            SemanticDelta
        )
        import numpy as np

        canonical = ArtifactVariant(
            variant_id=f"{target}_v1",
            artifact_id=target,
            version="1.0",
            content=f"# {target} implementation v1",
            embedding=np.random.rand(768),
            status=VariantStatus.CANONICAL,
            performance=PerformanceMetrics(
                latency_ms=50.0,
                memory_mb=10.0,
                success_rate=0.85,
                test_coverage=0.70
            )
        )

        # Create a few alternates
        alternates = []
        for i in range(3):
            alt = ArtifactVariant(
                variant_id=f"{target}_v1.{i+1}",
                artifact_id=target,
                version=f"1.{i+1}",
                content=f"# {target} implementation v1.{i+1}",
                embedding=canonical.embedding + np.random.rand(768) * 0.05,
                performance=PerformanceMetrics(
                    latency_ms=50.0 - (i * 5),
                    memory_mb=10.0 - (i * 0.5),
                    success_rate=0.85 + (i * 0.03),
                    test_coverage=0.70 + (i * 0.05)
                ),
                semantic_deltas=[
                    SemanticDelta(
                        delta_type=["algorithm", "error_handling", "refactor"][i],
                        description=f"Improvement {i+1}",
                        impact_areas=["performance"],
                        estimated_benefit=0.6 + (i * 0.1),
                        risk_level=0.2
                    )
                ]
            )
            alternates.append(alt)

        cluster = OptimizationCluster(
            cluster_id=f"{target}_cluster",
            canonical_variant=canonical,
            alternates=alternates
        )

        clusters = [cluster]

    return clusters


def format_report_markdown(report: Dict[str, Any]) -> str:
    """Format optimization report as markdown."""
    md = []
    md.append("# RAG Cluster Optimization Report\n")

    md.append(f"## Cluster: {report['cluster_id']}")
    md.append(f"**Status**: {report['status']}\n")

    if report['status'] == 'completed':
        md.append("### Summary")
        summary = report['summary']
        md.append(f"- **Total Iterations**: {summary['total_iterations']}")
        md.append(f"- **Total Promotions**: {summary['total_promotions']}")
        md.append(f"- **Total Archived**: {summary['total_archived']}")
        md.append(f"- **Initial Fitness**: {summary['initial_fitness']}")
        md.append(f"- **Final Fitness**: {summary['final_fitness']}")
        md.append(f"- **Total Improvement**: +{summary['total_improvement']} ({summary['improvement_percentage']}%)\n")

        if report.get('iterations'):
            md.append("### Iterations\n")
            for iteration in report['iterations']:
                md.append(f"#### Iteration {iteration['iteration']}")
                md.append(f"- **Promoted**: {'Yes' if iteration['promoted'] else 'No'}")
                md.append(f"- **Fitness**: {iteration['fitness']}")
                if iteration.get('insights'):
                    md.append("- **Insights**:")
                    for insight in iteration['insights']:
                        md.append(f"  - {insight}")
                md.append("")

        if report.get('learned_patterns'):
            md.append("### Learned Patterns\n")
            for pattern_type, patterns in report['learned_patterns'].items():
                if patterns:
                    avg_improvement = sum(p['improvement'] for p in patterns) / len(patterns)
                    md.append(f"- **{pattern_type}**: Average improvement +{avg_improvement:.1%} ({len(patterns)} samples)")

        md.append("\n### Final Canonical Variant")
        canonical = report['canonical_variant']
        md.append(f"- **Variant ID**: {canonical['variant_id']}")
        md.append(f"- **Version**: {canonical['version']}")
        md.append(f"- **Fitness**: {canonical['fitness']}")
        md.append("\n**Performance**:")
        perf = canonical['performance']
        md.append(f"- Latency: {perf['latency_ms']}ms")
        md.append(f"- Memory: {perf['memory_mb']}MB")
        md.append(f"- Success Rate: {perf['success_rate']}")
        md.append(f"- Test Coverage: {perf['test_coverage']}")

        md.append("\n### Cluster Statistics")
        stats = report['cluster_stats']
        md.append(f"- **Total Variants**: {stats['total_variants']}")
        md.append(f"- **Active Variants**: {stats['active_variants']}")
        md.append(f"- **Archived Variants**: {stats['archived_variants']}")
        md.append(f"- **Median Fitness**: {stats['median_fitness']}")

    return "\n".join(md)


def format_report_json(report: Dict[str, Any]) -> str:
    """Format optimization report as JSON."""
    return json.dumps(report, indent=2)


def format_report_text(report: Dict[str, Any]) -> str:
    """Format optimization report as plain text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"RAG CLUSTER OPTIMIZATION REPORT")
    lines.append("=" * 60)
    lines.append(f"Cluster: {report['cluster_id']}")
    lines.append(f"Status: {report['status']}")

    if report['status'] == 'completed':
        lines.append("\nSUMMARY")
        lines.append("-" * 60)
        summary = report['summary']
        lines.append(f"Total Iterations:    {summary['total_iterations']}")
        lines.append(f"Total Promotions:    {summary['total_promotions']}")
        lines.append(f"Total Archived:      {summary['total_archived']}")
        lines.append(f"Initial Fitness:     {summary['initial_fitness']}")
        lines.append(f"Final Fitness:       {summary['final_fitness']}")
        lines.append(f"Total Improvement:   +{summary['total_improvement']} ({summary['improvement_percentage']}%)")

        canonical = report['canonical_variant']
        lines.append(f"\nFINAL CANONICAL VARIANT")
        lines.append("-" * 60)
        lines.append(f"Variant ID: {canonical['variant_id']}")
        lines.append(f"Version:    {canonical['version']}")
        lines.append(f"Fitness:    {canonical['fitness']}")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting RAG Cluster Optimizer")
    logger.info(f"Target: {args.target}")
    logger.info(f"Node Type: {args.node_type}")
    logger.info(f"Strategy: {args.strategy}")

    # Load configuration
    logger.info(f"Loading configuration from {args.config_path}")
    config_manager = OptimizerConfigManager(config_path=args.config_path)

    # Parse node type
    node_type = None
    if args.node_type:
        node_type = NodeType(args.node_type)

    # Load clusters
    logger.info("Loading clusters from RAG memory")
    clusters = load_clusters_from_rag(args.target, node_type)

    if not clusters:
        logger.error("No clusters found to optimize")
        return

    logger.info(f"Found {len(clusters)} cluster(s) to optimize")

    # Optimize each cluster
    all_reports = []

    for cluster in clusters:
        logger.info(f"\nOptimizing cluster: {cluster.cluster_id}")

        # Determine node type from cluster if not specified
        if node_type is None:
            # In real implementation, get from cluster metadata
            node_type = NodeType.FUNCTION

        # Get optimizer for node type
        optimizer_wrapper = config_manager.get_optimizer(node_type)

        # Override strategy if specified
        if args.strategy:
            strategy = OptimizationStrategy(args.strategy)
            optimizer_wrapper.optimizer.strategy = strategy

        # Override max iterations if specified
        if args.max_iterations:
            optimizer_wrapper.optimizer.max_iterations = args.max_iterations

        # Run optimization
        logger.info(f"Running optimization with {optimizer_wrapper.config.strategy.value} strategy")
        iterations = optimizer_wrapper.optimize_cluster(cluster)

        # Generate report
        report = optimizer_wrapper.optimizer.get_optimization_report(cluster, iterations)
        all_reports.append(report)

        # Format and print report
        if args.output_format == 'markdown':
            output = format_report_markdown(report)
        elif args.output_format == 'json':
            output = format_report_json(report)
        else:  # text
            output = format_report_text(report)

        print(output)
        print("\n")

    # Summary for multiple clusters
    if len(all_reports) > 1:
        logger.info(f"\nOptimized {len(all_reports)} clusters")
        total_promotions = sum(r['summary'].get('total_promotions', 0) for r in all_reports if r['status'] == 'completed')
        total_archived = sum(r['summary'].get('total_archived', 0) for r in all_reports if r['status'] == 'completed')
        logger.info(f"Total promotions across all clusters: {total_promotions}")
        logger.info(f"Total archived across all clusters: {total_archived}")

    logger.info("\nOptimization complete!")


if __name__ == "__main__":
    main()
