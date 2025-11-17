"""
Execution Modes - Interactive vs Optimize

TWO CORE MODES:

1. INTERACTIVE MODE ("make it work")
   - Goal: Get result QUICKLY for the user
   - Strategy: Single best-known generator
   - No experiments, no optimization
   - Store metrics for later
   - User sees result in 5-15 seconds

2. OPTIMIZE MODE ("make it better")
   - Goal: Improve quality over time
   - Strategy: Parallel experiments, aggressive evolution
   - Run AFTER interactive mode (background)
   - Guided by unit tests (safe evolution)
   - No user waiting

The overseer chooses mode based on context:
- User requests workflow → INTERACTIVE (fast result)
- Background optimization → OPTIMIZE (improve for future)
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution modes for code generation."""

    INTERACTIVE = "interactive"  # Fast, single-shot, user waiting
    OPTIMIZE = "optimize"         # Slow, experimental, background


@dataclass
class InteractiveConfig:
    """Configuration for interactive mode."""

    # Speed-focused
    max_generation_time: float = 30.0  # seconds
    use_best_known_generator: bool = True  # No experiments
    single_attempt: bool = True  # No retries (unless critical error)
    minimal_logging: bool = True  # Less verbose

    # Store metrics for later optimization
    track_quality: bool = True
    track_speed: bool = True


@dataclass
class OptimizeConfig:
    """Configuration for optimize mode."""

    # Quality-focused, no time pressure
    max_generation_time: float = 300.0  # 5 minutes per generator
    parallel_experiments: int = 5  # Run 5 generators in parallel
    aggressive_evolution: bool = True  # Mutate tools
    run_ablation_tests: bool = True  # Test variations

    # Safety: guided by unit tests
    require_test_pass: bool = True  # All variants must pass tests
    preserve_compatibility: bool = True  # Don't break existing code


class ExecutionModeManager:
    """
    Manages execution modes for code generation.

    Interactive Mode Flow:
    1. User requests workflow
    2. Select best-known generator for this task type
    3. Generate code (single shot)
    4. Test and return to user FAST
    5. Store metrics in background

    Optimize Mode Flow:
    1. Triggered by scheduler or manual request
    2. Load existing code + tests
    3. Run 5 parallel generators
    4. Test all variants
    5. Select best (quality + speed)
    6. Evolve tool definitions
    7. Update "best generator" registry
    """

    def __init__(self, rag_memory, tools_manager, parallel_generator):
        """
        Initialize execution mode manager.

        Args:
            rag_memory: RAGMemory for storing metrics
            tools_manager: ToolsManager for tool evolution
            parallel_generator: ParallelGenerator for experiments
        """
        self.rag = rag_memory
        self.tools = tools_manager
        self.parallel_gen = parallel_generator

        # Track best generators for each task type
        self.best_generators = {}  # {task_type: generator_name}

        # Load historical best generators from RAG
        self._load_best_generators()

    def get_mode(self, context: Dict[str, Any]) -> ExecutionMode:
        """
        Determine execution mode based on context.

        Args:
            context: Request context

        Returns:
            ExecutionMode (INTERACTIVE or OPTIMIZE)
        """

        # Explicit mode request
        if context.get("mode"):
            mode_str = context["mode"].lower()
            if mode_str == "optimize":
                return ExecutionMode.OPTIMIZE
            return ExecutionMode.INTERACTIVE

        # User waiting? → Interactive
        if context.get("user_waiting", True):
            return ExecutionMode.INTERACTIVE

        # Background job? → Optimize
        if context.get("background", False):
            return ExecutionMode.OPTIMIZE

        # Optimization request? → Optimize
        if context.get("optimize", False):
            return ExecutionMode.OPTIMIZE

        # Default: Interactive (user experience first)
        return ExecutionMode.INTERACTIVE

    def select_generator_for_interactive(
        self,
        task_type: str,
        fallback: str = "codellama"
    ) -> Dict[str, Any]:
        """
        Select the single best generator for interactive mode.

        Args:
            task_type: Type of task (api, data_processing, etc.)
            fallback: Fallback generator if no history

        Returns:
            Generator configuration
        """

        # Use best known generator for this task type
        if task_type in self.best_generators:
            generator_name = self.best_generators[task_type]
            logger.info(f"Using best known generator for {task_type}: {generator_name}")

            return self._get_generator_config(generator_name)

        # No history for this task type - use conservative default
        logger.info(f"No history for {task_type}, using fallback: {fallback}")
        return {
            "name": f"{fallback}_interactive",
            "model": fallback,
            "temperature": 0.3,  # Conservative
            "mode": "interactive"
        }

    def execute_interactive(
        self,
        prompt: str,
        task_type: str,
        node_id: str,
        client
    ) -> Dict[str, Any]:
        """
        Execute in interactive mode: Fast, single-shot.

        Args:
            prompt: Code generation prompt
            task_type: Type of task
            node_id: Node ID
            client: OllamaClient

        Returns:
            Result with code and metrics
        """

        logger.info(f"INTERACTIVE MODE: Generating code for {node_id}")

        # Select best generator
        gen_config = self.select_generator_for_interactive(task_type)

        # Generate (single shot)
        import time
        start_time = time.time()

        code = client.generate(
            model=gen_config["model"],
            prompt=prompt,
            temperature=gen_config["temperature"]
        )

        generation_time = time.time() - start_time

        logger.info(f"Generated in {generation_time:.2f}s")

        # Store metrics for later optimization
        self._store_interactive_metrics(
            node_id=node_id,
            task_type=task_type,
            generator=gen_config["name"],
            generation_time=generation_time,
            code=code
        )

        return {
            "code": code,
            "generator": gen_config["name"],
            "generation_time": generation_time,
            "mode": "interactive"
        }

    def execute_optimize(
        self,
        prompt: str,
        task_type: str,
        node_id: str,
        existing_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute in optimize mode: Slow, experimental, aggressive.

        Args:
            prompt: Code generation prompt
            task_type: Type of task
            node_id: Node ID
            existing_code: Existing code to improve (optional)

        Returns:
            Best result from experiments + evolution data
        """

        logger.info(f"OPTIMIZE MODE: Experimenting with {node_id}")

        # Create multiple generator variants
        generators = self._create_experiment_generators(task_type)

        logger.info(f"Running {len(generators)} parallel experiments...")

        # Run parallel experiments
        results = self.parallel_gen.generate_parallel(
            prompt=prompt,
            generators=generators,
            node_id=node_id,
            description=task_type
        )

        # Select best result
        best = results[0]  # Already sorted by combined score

        # Update best generator for this task type
        self._update_best_generator(task_type, best.generator_name)

        # Evolve tool definitions if aggressive mode
        if existing_code and best.combined_score > 0.8:
            self._evolve_tool_definition(
                task_type=task_type,
                winning_generator=best.generator_name,
                success_metrics=best
            )

        logger.info(f"Best: {best.generator_name} (score: {best.combined_score:.2f})")

        return {
            "code": best.code,
            "generator": best.generator_name,
            "generation_time": best.generation_time,
            "quality_score": best.quality_score,
            "combined_score": best.combined_score,
            "mode": "optimize",
            "all_results": results,  # For analysis
            "evolved_tools": best.combined_score > 0.8
        }

    def _create_experiment_generators(self, task_type: str) -> List:
        """Create 5 generator variants for optimization experiments."""

        from src.parallel_generator import GeneratorConfig

        # Task-specific temperature ranges
        if task_type in ["api_integration", "database", "security"]:
            # Conservative for critical tasks
            temps = [0.1, 0.2, 0.3, 0.4, 0.5]
        else:
            # More creative for general tasks
            temps = [0.3, 0.5, 0.7, 0.9, 1.0]

        # Models to experiment with
        models = [
            ("codellama", "codellama"),
            ("qwen_14b", "qwen2.5-coder:14b"),
            ("qwen_14b", "qwen2.5-coder:14b"),
            ("deepseek", "deepseek-coder:6.7b"),
            ("deepseek", "deepseek-coder:6.7b")
        ]

        generators = []
        for (name, model), temp in zip(models, temps):
            generators.append(GeneratorConfig(
                name=f"{name}_temp{temp}",
                model=model,
                temperature=temp
            ))

        return generators

    def _store_interactive_metrics(
        self,
        node_id: str,
        task_type: str,
        generator: str,
        generation_time: float,
        code: str
    ):
        """Store metrics from interactive mode for later optimization."""

        try:
            from src.rag_memory import ArtifactType
            import json

            self.rag.store_artifact(
                artifact_id=f"metrics_{node_id}_{task_type}",
                artifact_type=ArtifactType.PATTERN,
                name=f"Interactive Metrics: {node_id}",
                description=f"Metrics from interactive generation for {task_type}",
                content=json.dumps({
                    "node_id": node_id,
                    "task_type": task_type,
                    "generator": generator,
                    "generation_time": generation_time,
                    "code_length": len(code),
                    "mode": "interactive"
                }),
                tags=["metrics", "interactive", task_type, generator],
                auto_embed=False  # Don't embed metrics
            )

        except Exception as e:
            logger.warning(f"Could not store metrics: {e}")

    def _update_best_generator(self, task_type: str, generator_name: str):
        """Update the best known generator for a task type."""

        old_best = self.best_generators.get(task_type, "none")
        self.best_generators[task_type] = generator_name

        logger.info(f"Updated best generator for {task_type}: {old_best} → {generator_name}")

        # Store in RAG for persistence
        try:
            from src.rag_memory import ArtifactType
            import json

            self.rag.store_artifact(
                artifact_id=f"best_generator_{task_type}",
                artifact_type=ArtifactType.PATTERN,
                name=f"Best Generator: {task_type}",
                description=f"Best known generator for {task_type} tasks",
                content=json.dumps({
                    "task_type": task_type,
                    "generator": generator_name,
                    "updated_at": "2025-11-17"
                }),
                tags=["best_generator", task_type],
                auto_embed=False
            )

        except Exception as e:
            logger.warning(f"Could not store best generator: {e}")

    def _load_best_generators(self):
        """Load historical best generators from RAG."""

        try:
            results = self.rag.find_by_tags(
                tags=["best_generator"],
                limit=100
            )

            import json
            for artifact in results:
                data = json.loads(artifact.content)
                task_type = data["task_type"]
                generator = data["generator"]
                self.best_generators[task_type] = generator

            logger.info(f"Loaded {len(self.best_generators)} best generators from history")

        except Exception as e:
            logger.debug(f"Could not load best generators: {e}")

    def _get_generator_config(self, generator_name: str) -> Dict[str, Any]:
        """Get configuration for a generator by name."""

        # Parse generator name (e.g., "qwen_temp0.5")
        parts = generator_name.split("_")

        if "codellama" in generator_name:
            model = "codellama"
        elif "qwen" in generator_name:
            model = "qwen2.5-coder:14b"
        elif "deepseek" in generator_name:
            model = "deepseek-coder:6.7b"
        else:
            model = "codellama"  # Fallback

        # Extract temperature
        temperature = 0.3  # Default
        for part in parts:
            if part.startswith("temp"):
                try:
                    temperature = float(part.replace("temp", ""))
                except:
                    pass

        return {
            "name": generator_name,
            "model": model,
            "temperature": temperature
        }

    def _evolve_tool_definition(
        self,
        task_type: str,
        winning_generator: str,
        success_metrics: Any
    ):
        """
        Evolve tool definitions based on successful experiments.

        Creates specialized tools for tasks where a generator consistently wins.
        """

        logger.info(f"Evolving tool for {task_type} based on {winning_generator}")

        # Check if this generator has won multiple times for this task
        # (simplified - in production, check actual history)

        # Create specialized tool definition
        from src.rag_memory import ArtifactType
        import json

        gen_config = self._get_generator_config(winning_generator)

        tool_def = {
            "name": f"{task_type.replace('_', ' ').title()} Expert",
            "type": "llm",
            "description": f"Specialized generator for {task_type} tasks",
            "llm": {
                "model": gen_config["model"],
                "temperature": gen_config["temperature"],
                "role": "specialized"
            },
            "tags": [task_type, "evolved", "expert"],
            "metadata": {
                "evolved_from": winning_generator,
                "success_rate": success_metrics.combined_score,
                "specialized_for": task_type
            }
        }

        # Store evolved tool in RAG
        try:
            self.rag.store_artifact(
                artifact_id=f"evolved_tool_{task_type}",
                artifact_type=ArtifactType.TOOL,
                name=tool_def["name"],
                description=tool_def["description"],
                content=json.dumps(tool_def),
                tags=["evolved_tool", task_type, "expert"],
                auto_embed=True
            )

            logger.info(f"Created evolved tool: {tool_def['name']}")

        except Exception as e:
            logger.warning(f"Could not create evolved tool: {e}")
