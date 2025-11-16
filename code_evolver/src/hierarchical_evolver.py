"""
Hierarchical Evolution System
Tracks node-level metrics and enables parent nodes to learn from child performance.
Each node contributes to shared plan context that evolves over time.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict

from .overseer_llm import OverseerLlm, ExecutionPlan
from .evaluator_llm import EvaluatorLlm, FitnessEvaluation
from .rag_memory import RAGMemory, ArtifactType
from .ollama_client import OllamaClient
from .node_runner import NodeRunner
from .registry import Registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NodeMetrics:
    """Metrics for a single node execution."""
    node_id: str
    parent_id: Optional[str]
    depth: int  # 0 for root, 1 for child, etc.
    quality_score: float
    speed_ms: int
    memory_mb: float
    success: bool
    timestamp: str
    input_hash: str  # Hash of input to identify similar contexts
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NodeLearning:
    """Learning captured from a node's execution."""
    node_id: str
    context_signature: str  # Identifies what context this learning applies to
    lesson: str  # What was learned
    quality_achieved: float
    speed_achieved: int
    recommendation: str  # What to do in similar situations
    confidence: float  # Confidence in this learning (0.0-1.0)
    usage_count: int  # How many times this learning has been applied
    success_rate: float  # Success rate when applied

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SharedPlanContext:
    """
    Shared context that evolves based on node learnings.
    Parent nodes contribute learnings that affect future planning.
    """

    def __init__(self, storage_path: str = "./shared_context"):
        """
        Initialize shared plan context.

        Args:
            storage_path: Path to store context
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Learnings indexed by context signature
        self.learnings: Dict[str, List[NodeLearning]] = defaultdict(list)

        # Performance tracking by node type/pattern
        self.performance_stats: Dict[str, Dict[str, Any]] = {}

        # Strategy preferences (e.g., "for task X, prefer approach Y")
        self.strategy_preferences: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        self._load_context()

    def _load_context(self):
        """Load shared context from disk."""
        context_file = self.storage_path / "shared_context.json"

        if context_file.exists():
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Load learnings
                for signature, learnings_list in data.get("learnings", {}).items():
                    self.learnings[signature] = [
                        NodeLearning(**l) for l in learnings_list
                    ]

                # Load stats and preferences
                self.performance_stats = data.get("performance_stats", {})
                # Convert loaded dict back to defaultdict to maintain type
                loaded_prefs = data.get("strategy_preferences", {})
                self.strategy_preferences = defaultdict(list, loaded_prefs)

                logger.info(f"✓ Loaded shared context with {len(self.learnings)} learning entries")

            except Exception as e:
                logger.error(f"Error loading shared context: {e}")

    def _save_context(self):
        """Save shared context to disk."""
        context_file = self.storage_path / "shared_context.json"

        try:
            # Convert learnings to serializable format
            learnings_dict = {
                sig: [l.to_dict() for l in learnings]
                for sig, learnings in self.learnings.items()
            }

            data = {
                "learnings": learnings_dict,
                "performance_stats": self.performance_stats,
                "strategy_preferences": self.strategy_preferences,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }

            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving shared context: {e}")

    def add_learning(self, learning: NodeLearning):
        """Add a learning to the shared context."""
        self.learnings[learning.context_signature].append(learning)
        self._save_context()
        logger.info(f"✓ Added learning for context '{learning.context_signature}'")

    def get_learnings(self, context_signature: str, min_confidence: float = 0.5) -> List[NodeLearning]:
        """
        Get learnings for a specific context.

        Args:
            context_signature: Context to retrieve learnings for
            min_confidence: Minimum confidence threshold

        Returns:
            List of relevant learnings, sorted by confidence and success rate
        """
        learnings = self.learnings.get(context_signature, [])

        # Filter by confidence
        filtered = [l for l in learnings if l.confidence >= min_confidence]

        # Sort by success rate and confidence
        filtered.sort(key=lambda l: (l.success_rate, l.confidence), reverse=True)

        return filtered

    def record_strategy_preference(
        self,
        task_pattern: str,
        strategy: str,
        quality: float,
        speed: int
    ):
        """Record that a strategy worked well for a task pattern."""
        self.strategy_preferences[task_pattern].append({
            "strategy": strategy,
            "quality": quality,
            "speed": speed,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

        # Keep only top 10 for each pattern
        self.strategy_preferences[task_pattern] = sorted(
            self.strategy_preferences[task_pattern],
            key=lambda x: x["quality"],
            reverse=True
        )[:10]

        self._save_context()

    def get_best_strategy(self, task_pattern: str) -> Optional[str]:
        """Get the best known strategy for a task pattern."""
        strategies = self.strategy_preferences.get(task_pattern, [])
        return strategies[0]["strategy"] if strategies else None


class HierarchicalEvolver:
    """
    Hierarchical evolution system that enables:
    1. Node-level quality/speed tracking
    2. Parent nodes learning from child performance
    3. Shared plan context that evolves
    """

    def __init__(
        self,
        overseer: Optional[OverseerLlm] = None,
        evaluator: Optional[EvaluatorLlm] = None,
        rag_memory: Optional[RAGMemory] = None,
        runner: Optional[NodeRunner] = None,
        registry: Optional[Registry] = None,
        shared_context: Optional[SharedPlanContext] = None
    ):
        """
        Initialize hierarchical evolver.

        Args:
            overseer: OverseerLlm instance
            evaluator: EvaluatorLlm instance
            rag_memory: RAG memory for storage
            runner: NodeRunner for execution
            registry: Registry for node management
            shared_context: Shared plan context
        """
        self.client = OllamaClient()
        self.overseer = overseer or OverseerLlm(self.client, rag_memory)
        self.evaluator = evaluator or EvaluatorLlm(self.client)
        self.rag_memory = rag_memory
        self.runner = runner or NodeRunner()
        self.registry = registry or Registry()
        self.shared_context = shared_context or SharedPlanContext()

        # Node hierarchy tracking
        self.node_hierarchy: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
        self.node_metrics: Dict[str, List[NodeMetrics]] = defaultdict(list)

    def execute_with_plan(
        self,
        task_description: str,
        node_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        parent_node_id: Optional[str] = None,
        depth: int = 0,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Tuple[ExecutionPlan, Dict[str, Any], FitnessEvaluation]:
        """
        Execute a task with plan -> execute -> evaluate flow.

        Args:
            task_description: What to do
            node_id: Node identifier
            input_data: Input for execution
            parent_node_id: Parent node (if this is a sub-task)
            depth: Depth in hierarchy (0 = root)
            constraints: Execution constraints

        Returns:
            Tuple of (plan, execution_result, evaluation)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Executing task: {task_description}")
        logger.info(f"Node: {node_id} (depth: {depth})")
        logger.info(f"{'='*60}")

        # Track hierarchy
        if parent_node_id:
            if parent_node_id not in self.node_hierarchy:
                self.node_hierarchy[parent_node_id] = []
            self.node_hierarchy[parent_node_id].append(node_id)

        # Get learnings from shared context
        context_sig = self._get_context_signature(task_description, input_data)
        learnings = self.shared_context.get_learnings(context_sig)

        # Augment context with learnings
        context = {
            "learnings": [l.to_dict() for l in learnings[:3]],  # Top 3 learnings
            "best_strategy": self.shared_context.get_best_strategy(context_sig)
        }

        # PHASE 1: PLAN (Overseer creates execution plan)
        plan = self.overseer.create_execution_plan(
            task_description=task_description,
            context=context,
            constraints=constraints
        )

        # PHASE 2: EXECUTE (Run based on plan)
        execution_result = self._execute_plan(plan, node_id, input_data)

        # PHASE 3: EVALUATE (Evaluator determines fitness)
        evaluation = self.evaluator.evaluate_fitness(
            node_id=node_id,
            task_description=task_description,
            execution_result=execution_result,
            plan_id=plan.plan_id,
            quality_targets=constraints
        )

        # Record metrics
        metrics = NodeMetrics(
            node_id=node_id,
            parent_id=parent_node_id,
            depth=depth,
            quality_score=evaluation.overall_score,
            speed_ms=execution_result["metrics"]["latency_ms"],
            memory_mb=execution_result["metrics"]["memory_mb_peak"],
            success=execution_result["metrics"]["success"],
            timestamp=datetime.utcnow().isoformat() + "Z",
            input_hash=context_sig,
            metadata={"plan_id": plan.plan_id}
        )

        self.node_metrics[node_id].append(metrics)

        # Record execution in plan
        plan.record_execution(
            actual_quality=evaluation.overall_score,
            actual_speed_ms=metrics.speed_ms,
            node_id=node_id,
            success=metrics.success
        )

        # Contribute learning to shared context
        self._contribute_learning(
            node_id=node_id,
            context_sig=context_sig,
            evaluation=evaluation,
            metrics=metrics,
            plan=plan
        )

        logger.info(f"\n✓ Execution complete: {evaluation.verdict} (score: {evaluation.overall_score:.2f})")

        return plan, execution_result, evaluation

    def evolve_with_feedback(
        self,
        plan: ExecutionPlan,
        execution_result: Dict[str, Any],
        evaluation: FitnessEvaluation,
        iterations: int = 3
    ) -> Tuple[ExecutionPlan, FitnessEvaluation]:
        """
        PHASE 4: EVOLUTION with feedback loop.
        Send solution + evaluation back to overseer to improve.

        Args:
            plan: Original execution plan
            execution_result: Execution results
            evaluation: Fitness evaluation
            iterations: Max improvement iterations

        Returns:
            Tuple of (best_plan, best_evaluation)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting evolution feedback loop (max {iterations} iterations)")
        logger.info(f"{'='*60}")

        best_plan = plan
        best_evaluation = evaluation
        best_score = evaluation.overall_score

        for i in range(iterations):
            logger.info(f"\nIteration {i+1}/{iterations}")

            # Should we continue improving?
            if best_score >= 0.9:
                logger.info(f"Score {best_score:.2f} is excellent, stopping evolution")
                break

            # IMPROVE: Overseer creates improved plan
            improved_plan = self.overseer.improve_solution(
                plan=best_plan,
                execution_result=execution_result,
                evaluation=best_evaluation.to_dict()
            )

            # EXECUTE: Run improved plan
            # (In real implementation, would generate new code based on improved plan)
            # For now, we'll simulate this
            logger.info("Note: Full re-execution would happen here in production")

            # Track improvement attempt
            logger.info(f"  Iteration {i+1}: Previous score {best_score:.2f}")

            # In a full implementation:
            # - Generate new code based on improved_plan
            # - Execute new code
            # - Evaluate new results
            # - Compare and keep best

            # For now, we'll record the improved plan
            if self.rag_memory:
                self.rag_memory.store_artifact(
                    artifact_id=improved_plan.plan_id,
                    artifact_type=ArtifactType.PLAN,
                    name=f"Improved Plan Iteration {i+1}",
                    description=improved_plan.strategy,
                    content=json.dumps(improved_plan.to_dict(), indent=2),
                    tags=["evolved", "improved", f"iteration_{i+1}"],
                    metadata={
                        "parent_plan": best_plan.plan_id,
                        "iteration": i + 1
                    }
                )

        return best_plan, best_evaluation

    def learn_from_children(
        self,
        parent_node_id: str,
        optimization_goal: str = "balanced"
    ) -> Optional[NodeLearning]:
        """
        Parent node learns from child node performance.
        Example: If child A achieved quality 0.9 and child B achieved 0.6,
        record that approach A should be preferred for similar contexts.

        Args:
            parent_node_id: Parent node ID
            optimization_goal: What to optimize (balanced/quality/speed)

        Returns:
            NodeLearning if learning was generated
        """
        child_ids = self.node_hierarchy.get(parent_node_id, [])

        if len(child_ids) < 2:
            logger.info(f"Parent {parent_node_id} has <2 children, no comparison learning")
            return None

        logger.info(f"\nParent {parent_node_id} learning from {len(child_ids)} children...")

        # Get metrics for all children
        child_metrics = []
        for child_id in child_ids:
            metrics_list = self.node_metrics.get(child_id, [])
            if metrics_list:
                # Get most recent metrics
                child_metrics.append((child_id, metrics_list[-1]))

        if len(child_metrics) < 2:
            return None

        # Find best child based on optimization goal
        if optimization_goal == "quality":
            best_child_id, best_metrics = max(child_metrics, key=lambda x: x[1].quality_score)
        elif optimization_goal == "speed":
            best_child_id, best_metrics = min(child_metrics, key=lambda x: x[1].speed_ms)
        else:  # balanced
            best_child_id, best_metrics = max(
                child_metrics,
                key=lambda x: (x[1].quality_score - x[1].speed_ms / 10000)  # Normalize speed
            )

        # Create learning
        learning = NodeLearning(
            node_id=parent_node_id,
            context_signature=best_metrics.input_hash,
            lesson=f"For similar contexts, prefer approach from child {best_child_id}",
            quality_achieved=best_metrics.quality_score,
            speed_achieved=best_metrics.speed_ms,
            recommendation=f"Use node {best_child_id} strategy for future similar tasks",
            confidence=0.8,  # Initial confidence
            usage_count=0,
            success_rate=1.0 if best_metrics.success else 0.0
        )

        # Add to shared context
        self.shared_context.add_learning(learning)

        logger.info(f"✓ Parent learned: Prefer {best_child_id} (quality: {best_metrics.quality_score:.2f})")
        return learning

    def _execute_plan(
        self,
        plan: ExecutionPlan,
        node_id: str,
        input_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a plan (simplified - delegates to runner)."""
        # In full implementation, would translate plan steps to code execution

        # For now, run existing node if it exists
        if self.runner.node_exists(node_id):
            stdout, stderr, metrics = self.runner.run_node(
                node_id=node_id,
                input_payload=input_data or {},
                timeout_ms=plan.expected_speed_ms * 2  # Give 2x expected time
            )

            return {
                "stdout": stdout,
                "stderr": stderr,
                "metrics": metrics
            }

        # If node doesn't exist, return placeholder
        return {
            "stdout": json.dumps({"result": "simulated"}),
            "stderr": "",
            "metrics": {
                "exit_code": 0,
                "latency_ms": plan.expected_speed_ms,
                "memory_mb_peak": 64,
                "success": True
            }
        }

    def _contribute_learning(
        self,
        node_id: str,
        context_sig: str,
        evaluation: FitnessEvaluation,
        metrics: NodeMetrics,
        plan: ExecutionPlan
    ):
        """Node contributes learning to shared context."""
        # Extract key lessons from evaluation
        if evaluation.recommendations:
            lesson = "; ".join(evaluation.recommendations[:2])
        else:
            lesson = f"Achieved {evaluation.overall_score:.2f} quality in {metrics.speed_ms}ms"

        learning = NodeLearning(
            node_id=node_id,
            context_signature=context_sig,
            lesson=lesson,
            quality_achieved=evaluation.overall_score,
            speed_achieved=metrics.speed_ms,
            recommendation=evaluation.recommendations[0] if evaluation.recommendations else "",
            confidence=evaluation.overall_score,  # Use score as initial confidence
            usage_count=0,
            success_rate=1.0 if metrics.success else 0.0
        )

        self.shared_context.add_learning(learning)

        # Also record strategy preference if successful
        if metrics.success and evaluation.overall_score >= 0.7:
            self.shared_context.record_strategy_preference(
                task_pattern=context_sig,
                strategy=plan.strategy,
                quality=evaluation.overall_score,
                speed=metrics.speed_ms
            )

    def _get_context_signature(
        self,
        task: str,
        input_data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate a signature for the context to identify similar situations."""
        import hashlib

        # Create a normalized representation
        context_str = f"{task.lower()}"

        if input_data:
            # Add input structure (not values) to signature
            input_types = {k: type(v).__name__ for k, v in input_data.items()}
            context_str += f"_{json.dumps(input_types, sort_keys=True)}"

        # Hash to create signature
        return hashlib.md5(context_str.encode()).hexdigest()[:16]

    def get_node_statistics(self, node_id: str) -> Dict[str, Any]:
        """Get statistics for a node."""
        metrics_list = self.node_metrics.get(node_id, [])

        if not metrics_list:
            return {"error": "No metrics found"}

        quality_scores = [m.quality_score for m in metrics_list]
        speeds = [m.speed_ms for m in metrics_list]
        success_count = sum(1 for m in metrics_list if m.success)

        return {
            "node_id": node_id,
            "executions": len(metrics_list),
            "success_rate": success_count / len(metrics_list),
            "avg_quality": sum(quality_scores) / len(quality_scores),
            "avg_speed_ms": sum(speeds) / len(speeds),
            "best_quality": max(quality_scores),
            "best_speed_ms": min(speeds)
        }
