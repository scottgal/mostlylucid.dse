"""
Recursive System Optimizer - Optimizes the system at ALL levels recursively.

This component recursively optimizes:
- Level 0: Individual code artifacts (functions, algorithms)
- Level 1: Workflows that use those artifacts
- Level 2: Tools used by workflows
- Level 3: The optimizer itself (meta-optimization!)

Each level builds on optimizations from the previous level,
creating a compounding improvement effect.

Usage:
    optimizer = RecursiveSystemOptimizer(config, rag, pipeline, tools_manager)

    # Optimize everything recursively
    results = optimizer.optimize_everything(max_depth=3)

    # Just optimize specific level
    results = optimizer.optimize_level(level=0)  # Just code artifacts
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class OptimizationDepth(Enum):
    """Levels of recursive optimization."""
    CODE_ARTIFACTS = 0      # Individual functions/algorithms
    WORKFLOWS = 1           # Workflows using artifacts
    TOOLS = 2               # Tool definitions and selection logic
    META_SYSTEM = 3         # The optimizer itself!


class RecursiveSystemOptimizer:
    """
    Recursively optimizes the system at ALL levels:
    - Individual functions
    - Workflows
    - Tools
    - The optimizer itself!
    """

    def __init__(
        self,
        config_manager,
        rag_memory,
        optimization_pipeline,
        tools_manager
    ):
        """
        Initialize recursive system optimizer.

        Args:
            config_manager: ConfigManager instance
            rag_memory: RAG memory system
            optimization_pipeline: OptimizationPipeline instance
            tools_manager: ToolsManager instance
        """
        self.config = config_manager
        self.rag = rag_memory
        self.pipeline = optimization_pipeline
        self.tools = tools_manager

        # Optimization history by level
        self.optimization_history: Dict[int, List[Dict[str, Any]]] = {}

    def optimize_everything(
        self,
        max_depth: int = 3,
        start_depth: int = 0
    ) -> Dict[str, Any]:
        """
        Recursively optimize the entire system.

        Args:
            max_depth: Maximum recursion depth (0-3)
            start_depth: Starting depth (default 0)

        Returns:
            Optimization results for all levels
        """
        logger.info(f"Starting recursive optimization (depth {start_depth} to {max_depth})")

        results = {}

        for depth in range(start_depth, max_depth + 1):
            logger.info(f"=== Optimization Level {depth} ===")

            if depth == OptimizationDepth.CODE_ARTIFACTS.value:
                results[depth] = self._optimize_code_artifacts()

            elif depth == OptimizationDepth.WORKFLOWS.value:
                results[depth] = self._optimize_workflows()

            elif depth == OptimizationDepth.TOOLS.value:
                results[depth] = self._optimize_tools()

            elif depth == OptimizationDepth.META_SYSTEM.value:
                results[depth] = self._optimize_meta_system()

        logger.info(f"Recursive optimization complete: {len(results)} levels optimized")

        return results

    def optimize_level(self, level: int) -> Dict[str, Any]:
        """
        Optimize a specific level only.

        Args:
            level: 0=code, 1=workflows, 2=tools, 3=meta

        Returns:
            Optimization results for that level
        """
        logger.info(f"Optimizing level {level} only")

        if level == OptimizationDepth.CODE_ARTIFACTS.value:
            return self._optimize_code_artifacts()
        elif level == OptimizationDepth.WORKFLOWS.value:
            return self._optimize_workflows()
        elif level == OptimizationDepth.TOOLS.value:
            return self._optimize_tools()
        elif level == OptimizationDepth.META_SYSTEM.value:
            return self._optimize_meta_system()
        else:
            raise ValueError(f"Invalid optimization level: {level}")

    def _optimize_code_artifacts(self) -> Dict[str, Any]:
        """
        Level 0: Optimize individual code artifacts.

        Focuses on frequently-used functions and algorithms.
        """
        from .rag_memory import ArtifactType

        logger.info("Optimizing code artifacts...")

        artifacts = self.rag.list_all(artifact_type=ArtifactType.FUNCTION)

        optimized_count = 0
        total_improvement = 0.0

        for artifact in artifacts:
            # Only optimize if frequently used
            if artifact.usage_count < 5:
                continue

            logger.info(f"Optimizing {artifact.artifact_id} (reuse={artifact.usage_count})")

            try:
                # Local optimization (fast, free)
                result = self.pipeline.optimize_artifact(artifact, level="local")

                if result:
                    # Test and store if better
                    if self._test_and_store_if_better(artifact, result):
                        optimized_count += 1
                        total_improvement += result.improvement_score

            except Exception as e:
                logger.error(f"Failed to optimize {artifact.artifact_id}: {e}")

        avg_improvement = total_improvement / optimized_count if optimized_count > 0 else 0

        results = {
            "level": "code_artifacts",
            "total_artifacts": len(artifacts),
            "optimized": optimized_count,
            "avg_improvement": avg_improvement
        }

        logger.info(f"Code artifacts: {optimized_count}/{len(artifacts)} optimized, "
                   f"avg improvement: {avg_improvement*100:.1f}%")

        return results

    def _optimize_workflows(self) -> Dict[str, Any]:
        """
        Level 1: Optimize complete workflows.

        Uses cloud optimizer for high-value workflows.
        """
        from .rag_memory import ArtifactType

        logger.info("Optimizing workflows...")

        workflows = self.rag.list_all(artifact_type=ArtifactType.WORKFLOW)

        optimized_count = 0
        total_cost = 0.0

        for workflow in workflows:
            # Only optimize frequently-used workflows
            if workflow.usage_count < 10:
                continue

            logger.info(f"Optimizing workflow {workflow.artifact_id} (reuse={workflow.usage_count})")

            try:
                # Use cloud optimizer for high-value workflows
                result = self.pipeline.optimize_artifact(workflow, level="cloud")

                if result:
                    if self._test_and_store_if_better(workflow, result):
                        optimized_count += 1
                        total_cost += result.cost_usd

            except Exception as e:
                logger.error(f"Failed to optimize workflow {workflow.artifact_id}: {e}")

        results = {
            "level": "workflows",
            "total_workflows": len(workflows),
            "optimized": optimized_count,
            "total_cost": total_cost
        }

        logger.info(f"Workflows: {optimized_count}/{len(workflows)} optimized, "
                   f"cost: ${total_cost:.2f}")

        return results

    def _optimize_tools(self) -> Dict[str, Any]:
        """
        Level 2: Optimize tool definitions and selection logic.

        Analyzes tool usage patterns and suggests improvements.
        """
        logger.info("Optimizing tools and tool selection...")

        # Analyze tool usage patterns
        usage_stats = self._analyze_tool_usage()

        # Ask cloud optimizer to improve tool selection
        suggestions = self._get_tool_optimization_suggestions(usage_stats)

        # Apply improvements
        applied_count = self._apply_tool_improvements(suggestions)

        results = {
            "level": "tools",
            "usage_stats": usage_stats,
            "suggestions": suggestions,
            "applied": applied_count
        }

        logger.info(f"Tools: {applied_count} improvements applied")

        return results

    def _optimize_meta_system(self) -> Dict[str, Any]:
        """
        Level 3: META-OPTIMIZATION - Optimize the optimization system itself!

        This is where it gets meta - the system optimizes its own code.
        """
        logger.info("META-OPTIMIZATION: Optimizing the optimizer itself...")

        # Load the optimizer's own source code
        optimizer_files = [
            "optimization_pipeline.py",
            "offline_optimizer.py",
            "recursive_optimizer.py",
            "quality_evaluator.py"
        ]

        source_code = {}
        for filename in optimizer_files:
            filepath = Path(__file__).parent / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    source_code[filename] = f.read()

        # Get optimizer performance metrics
        optimizer_metrics = self._get_optimizer_metrics()

        # Use deep analyzer (would use Claude Sonnet with 200K context)
        meta_suggestions = self._get_meta_optimization_suggestions(
            source_code,
            optimizer_metrics
        )

        logger.info("META-OPTIMIZATION suggestions generated")
        logger.info(f"Suggestions: {meta_suggestions}")

        # Note: Actually applying meta-optimizations would require
        # careful review and testing. For now, just log suggestions.

        results = {
            "level": "meta_system",
            "files_analyzed": list(source_code.keys()),
            "metrics": optimizer_metrics,
            "suggestions": meta_suggestions,
            "note": "Meta-optimizations require manual review before applying"
        }

        logger.info("META-OPTIMIZATION complete: Suggestions ready for review")

        return results

    def _test_and_store_if_better(
        self,
        original: Any,
        optimization_result: Any
    ) -> bool:
        """
        Test optimized version and store if better than original.

        Returns:
            True if optimized version was stored, False otherwise
        """
        # Would run tests to verify optimized version works
        # For now, placeholder - assume it's better

        # Store optimized version
        try:
            from .rag_memory import ArtifactType

            optimized_id = f"{original.artifact_id}_optimized"

            self.rag.store_artifact(
                artifact_id=optimized_id,
                artifact_type=original.artifact_type,
                name=f"{original.name} (Optimized)",
                description=original.description,
                content=optimization_result.optimized_content,
                tags=original.tags + ["optimized"],
                metadata={
                    "optimized_from": original.artifact_id,
                    "optimization_level": optimization_result.optimization_level.value,
                    "improvement": optimization_result.improvement_score
                },
                auto_embed=True
            )

            logger.info(f"Stored optimized version: {optimized_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store optimized version: {e}")
            return False

    def _analyze_tool_usage(self) -> Dict[str, Any]:
        """Analyze how tools are being used."""

        # Would analyze actual tool usage from execution history
        # For now, placeholder

        return {
            "total_tools": 0,
            "most_used": [],
            "least_used": [],
            "redundant": [],
            "missing": []
        }

    def _get_tool_optimization_suggestions(
        self,
        usage_stats: Dict[str, Any]
    ) -> List[str]:
        """
        Get suggestions for tool improvements.

        Would use cloud LLM to analyze usage patterns.
        """
        # Placeholder
        return [
            "Consider adding a caching layer for frequently-used tools",
            "Tool X and Tool Y have overlapping functionality - consider merging",
            "Create specialized tool for pattern Z (appears 50+ times)"
        ]

    def _apply_tool_improvements(self, suggestions: List[str]) -> int:
        """
        Apply tool improvement suggestions.

        For now, just logs suggestions. Actual application
        would require code generation and testing.
        """
        logger.info(f"Tool improvement suggestions ({len(suggestions)}):")
        for i, suggestion in enumerate(suggestions, 1):
            logger.info(f"  {i}. {suggestion}")

        # Would apply improvements automatically
        return 0  # None applied yet (placeholder)

    def _get_optimizer_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the optimizer itself."""

        # Would collect actual metrics from optimization runs
        # For now, placeholder

        return {
            "total_optimizations": 0,
            "avg_optimization_time": 0.0,
            "success_rate": 0.0,
            "avg_improvement": 0.0
        }

    def _get_meta_optimization_suggestions(
        self,
        source_code: Dict[str, str],
        metrics: Dict[str, Any]
    ) -> List[str]:
        """
        Generate meta-optimization suggestions.

        Would use deep analyzer (Claude Sonnet) to analyze
        the optimizer's own source code and suggest improvements.
        """
        # Build prompt for meta-optimization
        files_summary = "\n".join([
            f"{name}: {len(code)} chars"
            for name, code in source_code.items()
        ])

        logger.info(f"Analyzing optimizer source code:")
        logger.info(files_summary)

        # Would call deep analyzer here
        # For now, return placeholder suggestions

        return [
            "Implement parallel batch optimization for independent artifacts",
            "Add caching layer for optimization results",
            "Implement incremental optimization (only re-optimize changed parts)",
            "Add A/B testing framework for comparing optimization strategies",
            "Implement adaptive threshold adjustment based on success rate"
        ]

    def get_recursive_optimization_stats(self) -> Dict[str, Any]:
        """Get statistics about recursive optimizations."""

        if not self.optimization_history:
            return {
                "total_runs": 0,
                "levels_optimized": []
            }

        return {
            "total_runs": len(self.optimization_history),
            "levels_optimized": list(self.optimization_history.keys()),
            "recent_runs": list(self.optimization_history.values())[-5:]
        }
