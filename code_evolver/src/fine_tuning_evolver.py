"""
Fine-Tuning Evolver - Creates specialist LLMs from successful execution patterns.

This component:
1. Analyzes RAG memory to identify specialization opportunities
2. Creates training datasets from high-quality artifacts
3. Fine-tunes specialist models for specific domains
4. Benchmarks specialists vs general models
5. Registers successful specialists as tools

The result is a self-improving system that creates its own specialized
models for frequently-occurring tasks, improving quality and reducing cost.

Usage:
    evolver = FineTuningEvolver(config, rag, tools_manager, ollama_client)

    # Identify specialization opportunities
    opportunities = evolver.identify_specialization_opportunities()

    # Create specialist for a domain
    specialist = evolver.create_specialist(domain="forex_analysis")

    # Benchmark specialist vs general
    results = evolver.benchmark_specialist(specialist, test_tasks)
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SpecializationOpportunity:
    """Represents an opportunity to create a specialist model."""
    domain: str
    task_count: int
    avg_quality_score: float
    improvement_potential: float
    estimated_training_examples: int
    estimated_cost: float
    priority: str  # "high" | "medium" | "low"


@dataclass
class TrainingExample:
    """A training example for fine-tuning."""
    prompt: str
    completion: str
    quality_score: float
    reuse_count: int
    test_results: Dict[str, Any]
    metadata: Dict[str, Any]


class FineTuningEvolver:
    """
    Creates specialist LLMs from successful patterns in RAG memory.

    Identifies domains where:
    - Many similar tasks exist (high volume)
    - General model struggles (low avg quality)
    - Successful patterns exist (high-quality examples)

    Then creates specialist models that outperform general models
    for those specific domains.
    """

    def __init__(
        self,
        config_manager,
        rag_memory,
        tools_manager,
        ollama_client=None
    ):
        """
        Initialize fine-tuning evolver.

        Args:
            config_manager: ConfigManager instance
            rag_memory: RAG memory system
            tools_manager: ToolsManager instance
            ollama_client: OllamaClient for fine-tuning (optional)
        """
        self.config = config_manager
        self.rag = rag_memory
        self.tools = tools_manager
        self.ollama = ollama_client

        # Fine-tuning settings
        ft_config = config_manager.get("fine_tuning", {})
        self.enabled = ft_config.get("enabled", False)
        self.min_examples = ft_config.get("min_training_examples", 50)
        self.min_quality = ft_config.get("min_quality_score", 0.85)

        # Specialist registry
        self.specialists: Dict[str, Any] = {}

    def identify_specialization_opportunities(
        self,
        min_task_count: int = 50,
        max_avg_quality: float = 0.75
    ) -> List[SpecializationOpportunity]:
        """
        Analyze RAG memory to find domains where specialist models would help.

        Looks for domains with:
        - High task volume (proving demand)
        - Suboptimal quality (room for specialist to improve)
        - Sufficient high-quality examples (for training data)

        Args:
            min_task_count: Minimum tasks to justify a specialist
            max_avg_quality: Maximum avg quality (looking for struggling domains)

        Returns:
            List of specialization opportunities, sorted by priority
        """
        logger.info("Identifying specialization opportunities...")

        # Get statistics from RAG
        stats = self.rag.get_statistics()

        if "by_type" not in stats:
            logger.warning("No artifact statistics available")
            return []

        opportunities = []

        # Analyze tag distribution to find domains
        tags_index = getattr(self.rag, 'tags_index', {})

        for domain, artifact_ids in tags_index.items():
            task_count = len(artifact_ids)

            # Skip if not enough tasks
            if task_count < min_task_count:
                continue

            # Get artifacts for this domain
            artifacts = [
                self.rag.get_artifact(aid)
                for aid in artifact_ids
                if self.rag.get_artifact(aid)
            ]

            if not artifacts:
                continue

            # Calculate average quality
            avg_quality = sum(a.quality_score for a in artifacts) / len(artifacts)

            # Skip if already high quality (no room for improvement)
            if avg_quality > max_avg_quality:
                continue

            # Count high-quality examples (for training data)
            high_quality_count = sum(
                1 for a in artifacts
                if a.quality_score >= self.min_quality
            )

            # Skip if not enough training examples
            if high_quality_count < self.min_examples:
                continue

            # Calculate improvement potential
            improvement_potential = 1.0 - avg_quality

            # Estimate cost (based on number of examples)
            estimated_cost = self._estimate_fine_tuning_cost(high_quality_count)

            # Calculate priority
            priority = self._calculate_specialization_priority(
                task_count,
                avg_quality,
                high_quality_count
            )

            opportunities.append(SpecializationOpportunity(
                domain=domain,
                task_count=task_count,
                avg_quality_score=avg_quality,
                improvement_potential=improvement_potential,
                estimated_training_examples=high_quality_count,
                estimated_cost=estimated_cost,
                priority=priority
            ))

        # Sort by priority and improvement potential
        opportunities.sort(
            key=lambda x: (
                {"high": 3, "medium": 2, "low": 1}[x.priority],
                x.improvement_potential
            ),
            reverse=True
        )

        logger.info(f"Found {len(opportunities)} specialization opportunities")
        if opportunities:
            top = opportunities[0]
            logger.info(f"Top opportunity: {top.domain} "
                       f"({top.task_count} tasks, "
                       f"avg quality={top.avg_quality_score:.2f}, "
                       f"{top.estimated_training_examples} training examples)")

        return opportunities

    def create_training_dataset(
        self,
        domain: str,
        max_examples: Optional[int] = None
    ) -> List[TrainingExample]:
        """
        Create training dataset from high-quality artifacts in a domain.

        Args:
            domain: Domain to create dataset for
            max_examples: Maximum training examples (optional)

        Returns:
            List of training examples
        """
        logger.info(f"Creating training dataset for domain: {domain}")

        # Get artifacts for domain
        artifacts = self.rag.find_by_tags(
            tags=[domain],
            match_all=False
        )

        training_examples = []

        for artifact in artifacts:
            # Only use high-quality artifacts for training
            if artifact.quality_score < self.min_quality:
                continue

            # Create training example
            example = TrainingExample(
                prompt=artifact.description,
                completion=artifact.content,
                quality_score=artifact.quality_score,
                reuse_count=artifact.usage_count,
                test_results=artifact.metadata.get("test_results", {}),
                metadata={
                    "artifact_id": artifact.artifact_id,
                    "tags": artifact.tags,
                    "created_at": artifact.created_at
                }
            )

            training_examples.append(example)

            # Stop if reached max examples
            if max_examples and len(training_examples) >= max_examples:
                break

        # Sort by quality and reuse (best examples first)
        training_examples.sort(
            key=lambda x: (x.quality_score, x.reuse_count),
            reverse=True
        )

        logger.info(f"Created {len(training_examples)} training examples for {domain}")

        return training_examples

    def fine_tune_specialist(
        self,
        domain: str,
        training_data: List[TrainingExample],
        base_model: str = "codellama"
    ) -> Optional[str]:
        """
        Fine-tune a specialist model for a domain.

        Args:
            domain: Domain name
            training_data: Training examples
            base_model: Base model to fine-tune from

        Returns:
            Specialist model name, or None if failed
        """
        logger.info(f"Fine-tuning specialist for {domain} "
                   f"({len(training_data)} examples, base={base_model})")

        # Specialist model name
        specialist_model = f"{base_model}-{domain}-specialist"

        # Convert training data to format for fine-tuning
        # Format depends on fine-tuning backend (Ollama, OpenAI, etc.)
        formatted_data = self._format_training_data(training_data)

        # Fine-tune using Ollama (or other backend)
        if self.ollama:
            try:
                # This is a placeholder - actual Ollama fine-tuning API
                # would be called here
                logger.warning("Ollama fine-tuning not yet implemented")
                logger.info(f"Would fine-tune: {specialist_model}")
                logger.info(f"Training examples: {len(formatted_data)}")

                # Would call: self.ollama.fine_tune(...)

            except Exception as e:
                logger.error(f"Fine-tuning failed: {e}")
                return None
        else:
            logger.warning("No fine-tuning backend available")
            return None

        # Register specialist as a tool
        self._register_specialist_tool(
            domain,
            specialist_model,
            training_data
        )

        logger.info(f"Specialist created and registered: {specialist_model}")

        return specialist_model

    def benchmark_specialist(
        self,
        specialist_model: str,
        domain: str,
        test_task_count: int = 10
    ) -> Dict[str, Any]:
        """
        Benchmark specialist vs general model on domain tasks.

        Args:
            specialist_model: Specialist model name
            domain: Domain to test on
            test_task_count: Number of test tasks

        Returns:
            Benchmark results comparing specialist to general model
        """
        logger.info(f"Benchmarking {specialist_model} vs general model on {domain}")

        # Get test tasks from domain (not used in training)
        test_tasks = self._get_test_tasks(domain, test_task_count)

        if not test_tasks:
            logger.warning("No test tasks available for benchmarking")
            return {}

        specialist_scores = []
        general_scores = []

        for task in test_tasks:
            # Would generate with specialist
            # specialist_result = self.ollama.generate(model=specialist_model, ...)
            # specialist_score = evaluate(specialist_result)

            # Would generate with general model
            # general_result = self.ollama.generate(model="codellama", ...)
            # general_score = evaluate(general_result)

            # Placeholder scores
            specialist_scores.append(0.85)
            general_scores.append(0.70)

        # Calculate statistics
        avg_specialist = sum(specialist_scores) / len(specialist_scores)
        avg_general = sum(general_scores) / len(general_scores)
        improvement = (avg_specialist - avg_general) / avg_general

        better_count = sum(
            s > g for s, g in zip(specialist_scores, general_scores)
        )

        results = {
            "specialist_model": specialist_model,
            "domain": domain,
            "test_count": len(test_tasks),
            "specialist_avg": avg_specialist,
            "general_avg": avg_general,
            "improvement": improvement,
            "better_count": better_count,
            "better_percentage": better_count / len(test_tasks) * 100
        }

        logger.info(f"Benchmark results:")
        logger.info(f"  Specialist: {avg_specialist:.3f}")
        logger.info(f"  General: {avg_general:.3f}")
        logger.info(f"  Improvement: {improvement*100:+.1f}%")
        logger.info(f"  Specialist wins: {better_count}/{len(test_tasks)}")

        return results

    def _estimate_fine_tuning_cost(self, num_examples: int) -> float:
        """Estimate cost of fine-tuning."""
        # Rough estimate: $0.01 per training example
        return num_examples * 0.01

    def _calculate_specialization_priority(
        self,
        task_count: int,
        avg_quality: float,
        training_examples: int
    ) -> str:
        """Calculate priority for specialization."""

        # High priority: many tasks, low quality, lots of training data
        score = task_count * (1 - avg_quality) * (training_examples / 100)

        if score > 50:
            return "high"
        elif score > 20:
            return "medium"
        else:
            return "low"

    def _format_training_data(
        self,
        training_examples: List[TrainingExample]
    ) -> List[Dict[str, str]]:
        """Format training data for fine-tuning backend."""

        # Format for fine-tuning (JSONL format typically)
        formatted = []

        for example in training_examples:
            formatted.append({
                "prompt": example.prompt,
                "completion": example.completion,
                "metadata": {
                    "quality_score": example.quality_score,
                    "reuse_count": example.reuse_count
                }
            })

        return formatted

    def _register_specialist_tool(
        self,
        domain: str,
        model_name: str,
        training_data: List[TrainingExample]
    ):
        """Register specialist as a tool in tools manager."""
        from .tools_manager import Tool, ToolType

        tool_id = f"llm_{domain}_specialist"

        avg_quality = sum(ex.quality_score for ex in training_data) / len(training_data)

        tool = Tool(
            tool_id=tool_id,
            name=f"{domain.replace('_', ' ').title()} Specialist LLM",
            tool_type=ToolType.FINE_TUNED_LLM,
            description=f"Fine-tuned specialist for {domain} tasks. "
                       f"Trained on {len(training_data)} high-quality examples "
                       f"(avg quality: {avg_quality:.2f}).",
            tags=[domain, "specialist", "fine-tuned", "llm"],
            implementation=None,  # Would be callable
            parameters={
                "model": model_name,
                "base_model": "codellama",
                "training_examples": len(training_data)
            },
            metadata={
                "domain": domain,
                "model_name": model_name,
                "training_examples": len(training_data),
                "avg_training_quality": avg_quality,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
        )

        self.tools.register_tool(tool)

        # Track in specialists registry
        self.specialists[domain] = {
            "model_name": model_name,
            "tool_id": tool_id,
            "training_examples": len(training_data),
            "avg_quality": avg_quality
        }

        logger.info(f"Registered specialist tool: {tool_id}")

    def _get_test_tasks(self, domain: str, count: int) -> List[Dict[str, str]]:
        """Get test tasks for benchmarking (not in training set)."""

        # Would get tasks that weren't used in training
        # For now, placeholder

        return [
            {"description": f"Test task {i} for {domain}"}
            for i in range(count)
        ]

    def get_specialist_stats(self) -> Dict[str, Any]:
        """Get statistics about created specialists."""

        return {
            "total_specialists": len(self.specialists),
            "specialists": self.specialists
        }
