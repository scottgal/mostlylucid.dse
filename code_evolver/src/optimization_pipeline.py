"""
Optimization Pipeline - Multi-tier optimization system.

Provides three tiers of optimization:
1. Local optimization - Fast, free, using local models (qwen2.5-coder)
2. Cloud optimization - Expensive, thorough, using cloud LLMs (GPT-4/Claude)
3. Deep system analysis - Comprehensive, using large context models (Claude Sonnet 200K)

Usage:
    pipeline = OptimizationPipeline(config_manager, rag_memory)

    # Quick local optimization
    optimized = pipeline.optimize_artifact(artifact, level="local")

    # Expensive cloud optimization (triggered by reuse count)
    optimized = pipeline.optimize_artifact(artifact, level="cloud")

    # Deep analysis of entire workflows
    optimized = pipeline.optimize_artifact(workflow, level="deep")
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Optimization levels with different cost/quality tradeoffs."""
    LOCAL = "local"      # Fast, free, good enough
    CLOUD = "cloud"      # Expensive, high quality
    DEEP = "deep"        # Very expensive, comprehensive system analysis


@dataclass
class OptimizationResult:
    """Result of an optimization pass."""
    original_artifact: Any
    optimized_content: str
    improvement_score: float
    metrics_before: Dict[str, Any]
    metrics_after: Dict[str, Any]
    cost_usd: float
    optimization_level: OptimizationLevel
    rationale: str
    specific_improvements: List[str]


class OptimizationPipeline:
    """
    Multi-tier optimization using local → cloud progression.
    Can optimize at ANY level: code → workflow → tool → system.
    """

    def __init__(self, config_manager, rag_memory, ollama_client=None):
        """
        Initialize optimization pipeline.

        Args:
            config_manager: ConfigManager instance
            rag_memory: RAG memory for context
            ollama_client: OllamaClient instance (optional)
        """
        self.config = config_manager
        self.rag = rag_memory
        self.ollama = ollama_client

        # Get optimization settings
        opt_config = config_manager.get("optimization", {})
        self.enabled = opt_config.get("enabled", True)
        self.cloud_config = opt_config.get("cloud_optimization", {})

        # Cost tracking
        self.total_cost_today = 0.0
        self.max_cost_per_day = self.cloud_config.get("max_cost_per_day", 50.0)

        # Optimization history
        self.optimization_history: List[OptimizationResult] = []

    def optimize_artifact(
        self,
        artifact: Any,
        level: str = "local",
        context: Optional[Dict[str, Any]] = None
    ) -> OptimizationResult:
        """
        Optimize any artifact: code, workflow, tool, or system component.

        Args:
            artifact: The artifact to optimize (from RAG memory)
            level: "local" | "cloud" | "deep"
            context: Additional context for optimization

        Returns:
            OptimizationResult with optimized content and metrics
        """
        if not self.enabled:
            logger.info("Optimization disabled in config")
            return None

        level_enum = OptimizationLevel(level)

        # Check cost limits for cloud/deep optimizations
        if level_enum in [OptimizationLevel.CLOUD, OptimizationLevel.DEEP]:
            if self.total_cost_today >= self.max_cost_per_day:
                logger.warning(f"Daily cost limit reached (${self.max_cost_per_day}), falling back to local")
                level_enum = OptimizationLevel.LOCAL

        logger.info(f"Optimizing {artifact.artifact_id} at {level_enum.value} level")

        # Route to appropriate optimizer
        if level_enum == OptimizationLevel.LOCAL:
            return self._local_optimization(artifact, context)
        elif level_enum == OptimizationLevel.CLOUD:
            return self._cloud_optimization(artifact, context)
        elif level_enum == OptimizationLevel.DEEP:
            return self._deep_system_analysis(artifact, context)

    def _local_optimization(
        self,
        artifact: Any,
        context: Optional[Dict[str, Any]]
    ) -> OptimizationResult:
        """
        Fast local optimization using qwen2.5-coder or escalation model.

        Cost: $0 (local inference)
        Time: 10-30 seconds
        Quality: 10-20% improvement typically
        """
        logger.info(f"Running local optimization on {artifact.artifact_id}")

        # Get local optimizer model
        optimizer_model = self.config.get("ollama.models.escalation.model", "qwen2.5-coder:14b")

        # Build optimization prompt
        prompt = self._build_local_optimization_prompt(artifact, context)

        # Generate optimized version
        if self.ollama:
            optimized_content = self.ollama.generate(
                model=optimizer_model,
                prompt=prompt,
                temperature=0.4,
                model_key="escalation"
            )
        else:
            logger.warning("No ollama client available, returning original")
            return OptimizationResult(
                original_artifact=artifact,
                optimized_content=artifact.content,
                improvement_score=0.0,
                metrics_before={},
                metrics_after={},
                cost_usd=0.0,
                optimization_level=OptimizationLevel.LOCAL,
                rationale="No optimizer available",
                specific_improvements=[]
            )

        # Clean up code blocks if present
        optimized_content = self._clean_code_fences(optimized_content)

        return OptimizationResult(
            original_artifact=artifact,
            optimized_content=optimized_content,
            improvement_score=0.0,  # Would need to benchmark to calculate
            metrics_before=artifact.metadata.get("metrics", {}),
            metrics_after={},  # Would need to execute to measure
            cost_usd=0.0,  # Local inference is free
            optimization_level=OptimizationLevel.LOCAL,
            rationale="Local optimization using qwen2.5-coder",
            specific_improvements=["Code quality", "Edge case handling", "Performance"]
        )

    def _cloud_optimization(
        self,
        artifact: Any,
        context: Optional[Dict[str, Any]]
    ) -> OptimizationResult:
        """
        Deep cloud optimization using GPT-4/Claude with context from similar solutions.

        Cost: $0.10-$0.50 per optimization
        Time: 30-60 seconds
        Quality: 20-40% improvement typically
        """
        logger.info(f"Running cloud optimization on {artifact.artifact_id}")

        # Get similar artifacts for context
        similar = self.rag.find_similar(
            query=artifact.description,
            artifact_type=artifact.artifact_type,
            top_k=10,
            min_similarity=0.5
        )

        # Build rich context
        optimization_context = self._build_optimization_context(artifact, similar, context)

        # Build cloud optimization prompt
        prompt = self._build_cloud_optimization_prompt(artifact, optimization_context)

        # This would call cloud API (GPT-4/Claude)
        # For now, placeholder - would need actual API integration
        logger.warning("Cloud optimization not yet implemented - needs API integration")

        estimated_cost = 0.25  # Estimated $0.25 per optimization

        return OptimizationResult(
            original_artifact=artifact,
            optimized_content=artifact.content,  # Placeholder
            improvement_score=0.0,
            metrics_before=artifact.metadata.get("metrics", {}),
            metrics_after={},
            cost_usd=estimated_cost,
            optimization_level=OptimizationLevel.CLOUD,
            rationale="Cloud optimization (not yet implemented)",
            specific_improvements=[]
        )

    def _deep_system_analysis(
        self,
        artifact: Any,
        context: Optional[Dict[str, Any]]
    ) -> OptimizationResult:
        """
        Deep analysis using Claude Sonnet's 200K context.
        Can analyze ENTIRE workflows or system architecture.

        Cost: $1.00-$5.00 per analysis
        Time: 2-5 minutes
        Quality: System-level architectural improvements
        """
        logger.info(f"Running deep system analysis on {artifact.artifact_id}")

        # Load full context (workflow chain, execution history, etc.)
        full_context = self._load_full_workflow_context(artifact)

        # Build comprehensive analysis prompt
        prompt = self._build_deep_analysis_prompt(artifact, full_context)

        # This would call Claude Sonnet with 200K context
        logger.warning("Deep system analysis not yet implemented - needs Claude API")

        estimated_cost = 2.50  # Estimated $2.50 per deep analysis

        return OptimizationResult(
            original_artifact=artifact,
            optimized_content=artifact.content,  # Placeholder
            improvement_score=0.0,
            metrics_before=artifact.metadata.get("metrics", {}),
            metrics_after={},
            cost_usd=estimated_cost,
            optimization_level=OptimizationLevel.DEEP,
            rationale="Deep system analysis (not yet implemented)",
            specific_improvements=[]
        )

    def _build_local_optimization_prompt(
        self,
        artifact: Any,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for local optimization."""

        return f"""Optimize this {artifact.artifact_type.value}:

CURRENT CODE:
{artifact.content}

CURRENT METRICS:
- Quality score: {artifact.quality_score}
- Usage count: {artifact.usage_count}
- Performance: {artifact.metadata.get('metrics', {})}

TASK:
Provide an improved version focusing on:
1. Better performance (faster execution, lower memory)
2. Cleaner code (readability, maintainability)
3. Edge case handling (robustness)
4. Best practices (Python idioms, type hints)

Return ONLY the improved code, no explanations.
"""

    def _build_cloud_optimization_prompt(
        self,
        artifact: Any,
        optimization_context: Dict[str, Any]
    ) -> str:
        """Build prompt for cloud optimization."""

        return f"""You are an expert system optimizer with access to patterns across multiple similar solutions.

ARTIFACT TO OPTIMIZE:
{artifact.content}

CURRENT PERFORMANCE:
- Quality: {artifact.quality_score}
- Latency: {artifact.metadata.get('metrics', {}).get('latency_ms', 'N/A')}
- Memory: {artifact.metadata.get('metrics', {}).get('memory_mb', 'N/A')}
- Reuse: {artifact.usage_count} times

SUCCESSFUL PATTERNS FROM SIMILAR SOLUTIONS:
{optimization_context.get('successful_patterns', 'None available')}

COMMON ANTI-PATTERNS TO AVOID:
{optimization_context.get('anti_patterns', 'None identified')}

TASK:
Provide a significantly improved version that:
1. Learns from the successful patterns above
2. Eliminates performance bottlenecks
3. Handles edge cases better
4. Is more maintainable and readable

Include:
- The optimized code
- Specific improvements made
- Expected performance gains
"""

    def _build_deep_analysis_prompt(
        self,
        artifact: Any,
        full_context: Dict[str, Any]
    ) -> str:
        """Build prompt for deep system analysis."""

        return f"""You are analyzing an entire workflow system with 200K context window.

WORKFLOW SPECIFICATION:
{full_context.get('workflow_spec', 'N/A')}

ALL TOOLS USED:
{full_context.get('tools', [])}

EXECUTION HISTORY (last 100 runs):
{full_context.get('execution_history', [])}

PERFORMANCE TRENDS:
{full_context.get('performance_trends', {})}

TASK: Comprehensive system-level optimization
Analyze:
1. Workflow structure - can steps be parallelized?
2. Tool selection - are optimal tools being used?
3. Bottlenecks - where is time/memory wasted?
4. Patterns - what anti-patterns exist?
5. Evolution - how has performance changed over time?

Provide:
- Specific architectural improvements
- Tool replacement suggestions
- Refactoring recommendations
- Performance predictions after optimization
"""

    def _build_optimization_context(
        self,
        artifact: Any,
        similar: List[Tuple[Any, float]],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build rich context for optimization from similar solutions."""

        # Extract patterns from high-quality similar solutions
        successful_patterns = []
        for similar_artifact, similarity in similar:
            if similar_artifact.quality_score >= 0.85:
                successful_patterns.append({
                    "similarity": similarity,
                    "quality": similar_artifact.quality_score,
                    "approach": similar_artifact.content[:500]  # First 500 chars
                })

        return {
            "artifact_id": artifact.artifact_id,
            "similar_count": len(similar),
            "successful_patterns": successful_patterns[:5],  # Top 5
            "anti_patterns": [],  # Would analyze low-quality solutions
            "user_context": context or {}
        }

    def _load_full_workflow_context(self, artifact: Any) -> Dict[str, Any]:
        """Load complete workflow context for deep analysis."""

        return {
            "workflow_spec": artifact.content if artifact.artifact_type.value == "workflow" else None,
            "tools": artifact.metadata.get("tools", []),
            "execution_history": artifact.metadata.get("execution_history", []),
            "performance_trends": artifact.metadata.get("performance_trends", {})
        }

    def _clean_code_fences(self, code: str) -> str:
        """Remove markdown code fences from generated code."""
        import re

        # Remove ```python and ``` fences
        code = re.sub(r'^```python\s*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```\s*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n```\s*$', '', code, flags=re.MULTILINE)

        return code.strip()

    def should_trigger_cloud_optimization(self, artifact: Any) -> bool:
        """
        Determine if artifact is worth expensive cloud optimization.

        Triggers:
        - High reuse (>10 uses) but suboptimal quality (<0.75)
        - Explicit user request
        - Scheduled batch optimization
        """
        triggers = self.cloud_config.get("triggers", {})

        # Check reuse threshold
        reuse_threshold = triggers.get("reuse_threshold", 10)
        quality_threshold = triggers.get("quality_threshold", 0.65)

        if (artifact.usage_count >= reuse_threshold and
            artifact.quality_score < quality_threshold):
            logger.info(f"Artifact {artifact.artifact_id} qualifies for cloud optimization "
                       f"(reuse={artifact.usage_count}, quality={artifact.quality_score})")
            return True

        return False

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get statistics about optimization history."""

        if not self.optimization_history:
            return {
                "total_optimizations": 0,
                "total_cost": 0.0
            }

        by_level = {}
        for result in self.optimization_history:
            level = result.optimization_level.value
            if level not in by_level:
                by_level[level] = {"count": 0, "cost": 0.0, "avg_improvement": 0.0}

            by_level[level]["count"] += 1
            by_level[level]["cost"] += result.cost_usd
            by_level[level]["avg_improvement"] += result.improvement_score

        # Calculate averages
        for level in by_level:
            if by_level[level]["count"] > 0:
                by_level[level]["avg_improvement"] /= by_level[level]["count"]

        return {
            "total_optimizations": len(self.optimization_history),
            "total_cost": sum(r.cost_usd for r in self.optimization_history),
            "by_level": by_level,
            "cost_today": self.total_cost_today,
            "cost_limit": self.max_cost_per_day
        }
