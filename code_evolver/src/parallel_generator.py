"""
Parallel Code Generator - Run Multiple Generators Simultaneously

The Overseer can run multiple "content writers" (code generators) in parallel
to experiment with different approaches and select the best based on:
- Code quality (tests pass, code review score)
- Speed (generation time, execution time)
- Configurable quality/speed tradeoff weights

This creates a competitive, evolutionary system where the best generators
for each task type are learned over time.
"""

import logging
import time
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class GeneratorConfig:
    """Configuration for a single code generator."""
    name: str
    model: str  # or role like "base", "powerful"
    temperature: float = 0.7
    max_tokens: int = 4000
    system_prompt: Optional[str] = None
    weight: float = 1.0  # For weighted selection


@dataclass
class GenerationResult:
    """Result from a single generator."""
    generator_name: str
    code: str
    generation_time: float  # seconds
    model_used: str
    temperature: float
    success: bool
    error: Optional[str] = None

    # Measured after testing
    test_passed: bool = False
    test_time: float = 0.0
    quality_score: float = 0.0  # 0-1
    execution_time: float = 0.0  # Runtime performance

    # Final score (computed)
    combined_score: float = 0.0


class ParallelGenerator:
    """
    Runs multiple code generators in parallel and selects the best result.

    The Overseer uses this to experiment with different approaches:
    - Different models (codellama, qwen, deepseek)
    - Different temperatures (0.1, 0.5, 0.9)
    - Different prompt variations
    - Different system prompts

    Selection criteria (configurable):
    - Quality weight: How much to prioritize test success and quality score
    - Speed weight: How much to prioritize fast generation and execution
    """

    def __init__(
        self,
        ollama_client,
        node_runner,
        evaluator,
        quality_weight: float = 0.7,
        speed_weight: float = 0.3
    ):
        """
        Initialize parallel generator.

        Args:
            ollama_client: OllamaClient for code generation
            node_runner: NodeRunner for executing tests
            evaluator: Evaluator for scoring quality
            quality_weight: Weight for quality (0-1)
            speed_weight: Weight for speed (0-1)
        """
        self.client = ollama_client
        self.runner = node_runner
        self.evaluator = evaluator
        self.quality_weight = quality_weight
        self.speed_weight = speed_weight

        # Normalize weights
        total = quality_weight + speed_weight
        self.quality_weight /= total
        self.speed_weight /= total

        # Track which generators work best for which tasks
        self.generator_stats = {}  # {generator_name: {task_type: success_rate}}

    def generate_parallel(
        self,
        prompt: str,
        generators: List[GeneratorConfig],
        node_id: str,
        description: str,
        max_workers: int = 3
    ) -> List[GenerationResult]:
        """
        Generate code using multiple generators in parallel.

        Args:
            prompt: Code generation prompt
            generators: List of generator configurations
            node_id: Node ID for saving/testing
            description: Task description
            max_workers: Max parallel workers

        Returns:
            List of generation results with scores
        """
        logger.info(f"Running {len(generators)} generators in parallel...")

        results = []

        # Run generators in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all generation tasks
            future_to_generator = {
                executor.submit(
                    self._generate_single,
                    prompt,
                    gen,
                    node_id,
                    description
                ): gen
                for gen in generators
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_generator):
                gen = future_to_generator[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(
                        f"Generator {result.generator_name} completed in {result.generation_time:.2f}s"
                    )
                except Exception as e:
                    logger.error(f"Generator {gen.name} failed: {e}")
                    results.append(GenerationResult(
                        generator_name=gen.name,
                        code="",
                        generation_time=0.0,
                        model_used=gen.model,
                        temperature=gen.temperature,
                        success=False,
                        error=str(e)
                    ))

        # Test and score all results in parallel
        results = self._test_and_score_parallel(results, node_id)

        # Compute combined scores
        results = self._compute_scores(results)

        # Sort by combined score
        results.sort(key=lambda r: r.combined_score, reverse=True)

        logger.info(f"Parallel generation complete. Best: {results[0].generator_name if results else 'none'}")

        return results

    def _generate_single(
        self,
        prompt: str,
        gen_config: GeneratorConfig,
        node_id: str,
        description: str
    ) -> GenerationResult:
        """Generate code with a single generator."""

        start_time = time.time()

        try:
            # Build full prompt with system prompt if provided
            full_prompt = prompt
            if gen_config.system_prompt:
                full_prompt = f"{gen_config.system_prompt}\n\n{prompt}"

            # Generate code
            code = self.client.generate(
                model=gen_config.model,
                prompt=full_prompt,
                temperature=gen_config.temperature,
                max_tokens=gen_config.max_tokens
            )

            generation_time = time.time() - start_time

            return GenerationResult(
                generator_name=gen_config.name,
                code=code,
                generation_time=generation_time,
                model_used=gen_config.model,
                temperature=gen_config.temperature,
                success=True
            )

        except Exception as e:
            logger.error(f"Generation failed for {gen_config.name}: {e}")
            return GenerationResult(
                generator_name=gen_config.name,
                code="",
                generation_time=time.time() - start_time,
                model_used=gen_config.model,
                temperature=gen_config.temperature,
                success=False,
                error=str(e)
            )

    def _test_and_score_parallel(
        self,
        results: List[GenerationResult],
        node_id: str
    ) -> List[GenerationResult]:
        """Test and score all generation results in parallel."""

        def test_and_score_one(result: GenerationResult) -> GenerationResult:
            """Test and score a single result."""

            if not result.success:
                return result

            try:
                # Save code to temp node
                temp_node_id = f"{node_id}_{result.generator_name}"
                self.runner.save_code(temp_node_id, result.code)

                # Run tests
                test_start = time.time()
                stdout, stderr, metrics = self.runner.run_node(temp_node_id, {})
                result.test_time = time.time() - test_start

                result.test_passed = metrics.get("exit_code", 1) == 0
                result.execution_time = metrics.get("latency", 0.0)

                # Evaluate quality
                if result.test_passed:
                    eval_result = self.evaluator.evaluate_full(stdout, stderr, metrics)
                    result.quality_score = eval_result.get("final_score", 0.0)
                else:
                    result.quality_score = 0.0

            except Exception as e:
                logger.error(f"Testing failed for {result.generator_name}: {e}")
                result.test_passed = False
                result.quality_score = 0.0

            return result

        # Test all results in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(results)) as executor:
            results = list(executor.map(test_and_score_one, results))

        return results

    def _compute_scores(self, results: List[GenerationResult]) -> List[GenerationResult]:
        """
        Compute combined scores based on quality and speed weights.

        Score = (quality_weight * quality_score) + (speed_weight * speed_score)

        Quality score:
        - Test passed: +0.5
        - Quality score: 0-0.5 (from evaluator)

        Speed score:
        - Faster generation: higher score
        - Faster execution: higher score
        """

        # Normalize generation times (0-1, where 1 is fastest)
        if results:
            max_gen_time = max(r.generation_time for r in results if r.success)
            min_gen_time = min(r.generation_time for r in results if r.success)
            gen_time_range = max_gen_time - min_gen_time or 1.0

        for result in results:
            if not result.success:
                result.combined_score = 0.0
                continue

            # Quality component (0-1)
            quality_component = 0.0
            if result.test_passed:
                quality_component = 0.5 + (result.quality_score * 0.5)

            # Speed component (0-1)
            # Faster generation time = higher score
            gen_speed_score = 1.0 - ((result.generation_time - min_gen_time) / gen_time_range)

            # Execution speed score (lower execution time = higher score)
            # Cap at 10 seconds for normalization
            exec_speed_score = max(0, 1.0 - (result.execution_time / 10.0))

            # Combined speed score
            speed_component = (gen_speed_score * 0.5) + (exec_speed_score * 0.5)

            # Final combined score
            result.combined_score = (
                self.quality_weight * quality_component +
                self.speed_weight * speed_component
            )

        return results

    def select_best(
        self,
        results: List[GenerationResult],
        min_quality: float = 0.5
    ) -> Optional[GenerationResult]:
        """
        Select the best result based on combined score.

        Args:
            results: List of generation results
            min_quality: Minimum quality threshold (0-1)

        Returns:
            Best result, or None if none meet threshold
        """

        # Filter by minimum quality
        qualified = [
            r for r in results
            if r.success and r.test_passed and r.quality_score >= min_quality
        ]

        if not qualified:
            logger.warning("No results meet minimum quality threshold")
            return None

        # Return highest scored result
        return max(qualified, key=lambda r: r.combined_score)

    def get_generator_recommendations(
        self,
        task_type: str,
        top_k: int = 3
    ) -> List[str]:
        """
        Get recommended generators for a task type based on past success.

        Args:
            task_type: Type of task (e.g., "data_processing", "api_integration")
            top_k: Number of recommendations

        Returns:
            List of generator names, sorted by success rate
        """

        if task_type not in self.generator_stats:
            return []

        # Sort by success rate
        stats = self.generator_stats[task_type]
        sorted_gens = sorted(
            stats.items(),
            key=lambda x: x[1]["success_rate"],
            reverse=True
        )

        return [name for name, _ in sorted_gens[:top_k]]

    def record_success(
        self,
        generator_name: str,
        task_type: str,
        success: bool
    ):
        """
        Record success/failure for a generator on a task type.

        Args:
            generator_name: Name of generator
            task_type: Type of task
            success: Whether it succeeded
        """

        if task_type not in self.generator_stats:
            self.generator_stats[task_type] = {}

        if generator_name not in self.generator_stats[task_type]:
            self.generator_stats[task_type][generator_name] = {
                "success_count": 0,
                "total_count": 0,
                "success_rate": 0.0
            }

        stats = self.generator_stats[task_type][generator_name]
        stats["total_count"] += 1
        if success:
            stats["success_count"] += 1
        stats["success_rate"] = stats["success_count"] / stats["total_count"]

    def create_default_generators(self) -> List[GeneratorConfig]:
        """
        Create default generator configurations for parallel experiments.

        Returns:
            List of 3-5 generator configs with different models/temperatures
        """

        return [
            # Fast, conservative
            GeneratorConfig(
                name="codellama_conservative",
                model="codellama",
                temperature=0.1,
                weight=1.0
            ),

            # Balanced
            GeneratorConfig(
                name="qwen_balanced",
                model="qwen2.5-coder:14b",
                temperature=0.5,
                weight=1.2  # Prefer this one
            ),

            # Creative
            GeneratorConfig(
                name="qwen_creative",
                model="qwen2.5-coder:14b",
                temperature=0.9,
                weight=0.8
            ),

            # Powerful, conservative
            GeneratorConfig(
                name="deepseek_conservative",
                model="deepseek-coder:6.7b",
                temperature=0.1,
                weight=0.9
            ),

            # Powerful, balanced
            GeneratorConfig(
                name="deepseek_balanced",
                model="deepseek-coder:6.7b",
                temperature=0.5,
                weight=1.1
            )
        ]
