"""
Overseer LLM - Plans execution strategies and improves solutions.
Separate from code generation - focuses on high-level planning and optimization.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ollama_client import OllamaClient
from .rag_memory import RAGMemory, ArtifactType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExecutionPlan:
    """Represents an execution plan created by the overseer."""

    def __init__(
        self,
        plan_id: str,
        task_description: str,
        strategy: str,
        steps: List[Dict[str, Any]],
        expected_quality: float = 0.8,
        expected_speed_ms: int = 1000,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize execution plan.

        Args:
            plan_id: Unique plan identifier
            task_description: Description of the task
            strategy: High-level strategy
            steps: List of execution steps
            expected_quality: Expected quality score (0.0-1.0)
            expected_speed_ms: Expected execution time in ms
            metadata: Additional metadata
        """
        self.plan_id = plan_id
        self.task_description = task_description
        self.strategy = strategy
        self.steps = steps
        self.expected_quality = expected_quality
        self.expected_speed_ms = expected_speed_ms
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat() + "Z"

        # Performance tracking
        self.executions: List[Dict[str, Any]] = []
        self.quality_history: List[float] = []
        self.speed_history: List[int] = []

    def record_execution(
        self,
        actual_quality: float,
        actual_speed_ms: int,
        node_id: str,
        success: bool,
        notes: Optional[str] = None
    ):
        """Record an execution of this plan."""
        self.executions.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "node_id": node_id,
            "quality": actual_quality,
            "speed_ms": actual_speed_ms,
            "success": success,
            "notes": notes
        })

        if success:
            self.quality_history.append(actual_quality)
            self.speed_history.append(actual_speed_ms)

    def get_average_quality(self) -> float:
        """Get average quality across executions."""
        return sum(self.quality_history) / len(self.quality_history) if self.quality_history else 0.0

    def get_average_speed(self) -> float:
        """Get average speed across executions."""
        return sum(self.speed_history) / len(self.speed_history) if self.speed_history else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "task_description": self.task_description,
            "strategy": self.strategy,
            "steps": self.steps,
            "expected_quality": self.expected_quality,
            "expected_speed_ms": self.expected_speed_ms,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "executions": self.executions,
            "avg_quality": self.get_average_quality(),
            "avg_speed": self.get_average_speed()
        }


class OverseerLlm:
    """
    Overseer LLM responsible for planning and strategic improvements.
    NOT responsible for code generation - focuses on high-level strategy.
    """

    def __init__(
        self,
        client: Optional[OllamaClient] = None,
        rag_memory: Optional[RAGMemory] = None,
        model: str = "llama3"
    ):
        """
        Initialize overseer.

        Args:
            client: OllamaClient instance
            rag_memory: RAG memory for plan storage/retrieval
            model: Model to use for overseer decisions
        """
        self.client = client or OllamaClient()
        self.rag_memory = rag_memory
        self.model = model

        # Plan cache
        self.plans: Dict[str, ExecutionPlan] = {}

    def create_execution_plan(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """
        Create an execution plan for a task.

        Args:
            task_description: Description of what needs to be done
            context: Additional context (similar past tasks, requirements, etc.)
            constraints: Constraints (timeout, memory, quality targets, etc.)

        Returns:
            ExecutionPlan object
        """
        logger.info("Creating execution plan with overseer...")

        # Search for similar plans in RAG memory
        similar_plans = []
        if self.rag_memory:
            similar_artifacts = self.rag_memory.find_similar(
                query=task_description,
                artifact_type=ArtifactType.PLAN,
                top_k=3,
                min_similarity=0.6
            )
            similar_plans = [
                {"name": artifact.name, "strategy": artifact.content, "quality": artifact.quality_score}
                for artifact, _ in similar_artifacts
            ]

        # Build prompt for overseer
        prompt = self._build_planning_prompt(
            task_description,
            context or {},
            constraints or {},
            similar_plans
        )

        # Get plan from overseer LLM
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            temperature=0.7
        )

        # Parse response
        plan_data = self._parse_plan_response(response)

        # Create ExecutionPlan
        plan_id = f"plan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        plan = ExecutionPlan(
            plan_id=plan_id,
            task_description=task_description,
            strategy=plan_data.get("strategy", ""),
            steps=plan_data.get("steps", []),
            expected_quality=plan_data.get("expected_quality", 0.8),
            expected_speed_ms=plan_data.get("expected_speed_ms", 1000),
            metadata={
                "constraints": constraints,
                "context": context
            }
        )

        # Cache plan
        self.plans[plan_id] = plan

        # Store in RAG memory
        if self.rag_memory:
            self.rag_memory.store_artifact(
                artifact_id=plan_id,
                artifact_type=ArtifactType.PLAN,
                name=f"Plan: {task_description[:50]}",
                description=plan.strategy,
                content=json.dumps(plan.to_dict(), indent=2),
                tags=["overseer", "plan", "initial"],
                metadata={"task": task_description}
            )

        logger.info(f"✓ Created plan {plan_id} with {len(plan.steps)} steps")
        return plan

    def improve_solution(
        self,
        plan: ExecutionPlan,
        execution_result: Dict[str, Any],
        evaluation: Dict[str, Any]
    ) -> ExecutionPlan:
        """
        Improve a solution based on execution results and evaluation.
        This is the feedback loop for evolution.

        Args:
            plan: Original execution plan
            execution_result: Results from execution (output, metrics, etc.)
            evaluation: Evaluation from EvaluatorLlm (fitness, quality scores)

        Returns:
            Improved ExecutionPlan
        """
        logger.info(f"Improving solution for plan {plan.plan_id}...")

        # Analyze performance gap
        actual_quality = evaluation.get("final_score", 0.0)
        actual_speed = execution_result.get("metrics", {}).get("latency_ms", 0)

        quality_gap = plan.expected_quality - actual_quality
        speed_gap = actual_speed - plan.expected_speed_ms

        # Build improvement prompt
        prompt = self._build_improvement_prompt(
            plan,
            execution_result,
            evaluation,
            quality_gap,
            speed_gap
        )

        # Get improvement strategy from overseer
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            temperature=0.7
        )

        # Parse improved plan
        improved_data = self._parse_plan_response(response)

        # Create improved plan
        improved_plan_id = f"{plan.plan_id}_improved_{len(plan.executions)}"
        improved_plan = ExecutionPlan(
            plan_id=improved_plan_id,
            task_description=plan.task_description,
            strategy=improved_data.get("strategy", plan.strategy),
            steps=improved_data.get("steps", plan.steps),
            expected_quality=improved_data.get("expected_quality", plan.expected_quality),
            expected_speed_ms=improved_data.get("expected_speed_ms", plan.expected_speed_ms),
            metadata={
                **plan.metadata,
                "parent_plan": plan.plan_id,
                "improvement_iteration": len(plan.executions),
                "previous_quality": actual_quality,
                "previous_speed": actual_speed
            }
        )

        # Cache improved plan
        self.plans[improved_plan_id] = improved_plan

        # Store in RAG memory
        if self.rag_memory:
            self.rag_memory.store_artifact(
                artifact_id=improved_plan_id,
                artifact_type=ArtifactType.PLAN,
                name=f"Improved Plan: {plan.task_description[:50]}",
                description=improved_plan.strategy,
                content=json.dumps(improved_plan.to_dict(), indent=2),
                tags=["overseer", "plan", "improved"],
                metadata={
                    "parent_plan": plan.plan_id,
                    "quality_improvement": improved_plan.expected_quality - plan.expected_quality,
                    "speed_improvement": plan.expected_speed_ms - improved_plan.expected_speed_ms
                }
            )

        logger.info(f"✓ Created improved plan {improved_plan_id}")
        return improved_plan

    def _build_planning_prompt(
        self,
        task: str,
        context: Dict[str, Any],
        constraints: Dict[str, Any],
        similar_plans: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for initial planning."""
        prompt = f"""You are an AI Overseer responsible for creating execution plans.

Task: {task}

Context:
{json.dumps(context, indent=2) if context else "None provided"}

Constraints:
- Quality Target: {constraints.get('quality_target', 0.8)}
- Speed Target: {constraints.get('speed_target_ms', 1000)}ms
- Memory Limit: {constraints.get('memory_limit_mb', 256)}MB

Similar Past Plans:
{json.dumps(similar_plans, indent=2) if similar_plans else "No similar plans found"}

Create an execution plan with:
1. A high-level strategy (what approach to take)
2. Specific execution steps (ordered list)
3. Expected quality score (0.0-1.0)
4. Expected execution time (milliseconds)

CRITICAL REQUIREMENT:
- ALL tasks MUST produce visible output - no exceptions!
- Content generation tasks MUST always output the generated content
- Every tool/task must print its result to stdout as JSON
- If a task doesn't produce output, it's considered broken

Respond in JSON format:
{{
  "strategy": "Brief description of the approach",
  "steps": [
    {{"step": 1, "action": "...", "description": "..."}},
    ...
  ],
  "expected_quality": 0.8,
  "expected_speed_ms": 1000,
  "reasoning": "Why this approach should work"
}}
"""
        return prompt

    def _build_improvement_prompt(
        self,
        plan: ExecutionPlan,
        execution_result: Dict[str, Any],
        evaluation: Dict[str, Any],
        quality_gap: float,
        speed_gap: int
    ) -> str:
        """Build prompt for improving existing plan."""
        prompt = f"""You are an AI Overseer improving an execution plan.

Original Task: {plan.task_description}

Original Plan Strategy:
{plan.strategy}

Original Steps:
{json.dumps(plan.steps, indent=2)}

Execution Results:
- Expected Quality: {plan.expected_quality:.2f}
- Actual Quality: {evaluation.get('final_score', 0.0):.2f}
- Quality Gap: {quality_gap:.2f}

- Expected Speed: {plan.expected_speed_ms}ms
- Actual Speed: {execution_result.get('metrics', {}).get('latency_ms', 0)}ms
- Speed Gap: {speed_gap}ms

Evaluation Details:
{json.dumps(evaluation, indent=2)}

Goal: RETAIN or IMPROVE quality while INCREASING speed.

Analyze:
1. Why did quality differ from expectations?
2. What caused the speed difference?
3. Which steps can be optimized?
4. Are there alternative approaches?

Create an IMPROVED plan in JSON format:
{{
  "strategy": "Updated strategy focusing on speed optimization",
  "steps": [
    {{"step": 1, "action": "...", "description": "...", "optimization": "..."}},
    ...
  ],
  "expected_quality": <target quality>,
  "expected_speed_ms": <improved target speed>,
  "reasoning": "Specific improvements and why they'll work",
  "optimizations": ["list of key optimizations applied"]
}}
"""
        return prompt

    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM into plan data."""
        import re

        # Try to find JSON in response
        json_match = re.search(r'\{[\s\S]*\}', response)

        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse plan JSON: {e}")

        # Fallback: extract basic info from text
        logger.warning("Could not parse plan as JSON, using fallback")

        return {
            "strategy": response[:200],
            "steps": [
                {"step": 1, "action": "execute_task", "description": "Execute based on general strategy"}
            ],
            "expected_quality": 0.7,
            "expected_speed_ms": 1000,
            "reasoning": "Fallback plan - LLM response was not parseable"
        }

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Retrieve a plan by ID."""
        return self.plans.get(plan_id)
