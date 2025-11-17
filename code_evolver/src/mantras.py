"""
Mantras - Personality Traits for Operations

Mantras define HOW an operation should approach a task - the "character"
of the execution. Different operations have different mantras.

Examples:
- "carefully, diligently" → thorough, methodical, high quality
- "quickly, accurately" → balanced speed and correctness
- "very quickly, accurate" → emphasize speed, maintain accuracy
- "experimentally, creatively" → try novel approaches
- "conservatively, safely" → minimize risk, proven approaches

Mantras affect:
- Model selection (fast vs powerful)
- Temperature (conservative vs creative)
- Validation strictness (loose vs strict)
- Time budgets (seconds vs minutes)
- Prompt engineering (tone and emphasis)
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MantraTrait(Enum):
    """Individual mantra traits."""

    # Speed traits
    VERY_QUICKLY = "very_quickly"
    QUICKLY = "quickly"
    DELIBERATELY = "deliberately"
    METHODICALLY = "methodically"

    # Quality traits
    ACCURATELY = "accurately"
    PRECISELY = "precisely"
    CAREFULLY = "carefully"
    DILIGENTLY = "diligently"
    THOROUGHLY = "thoroughly"

    # Approach traits
    CONSERVATIVELY = "conservatively"
    CREATIVELY = "creatively"
    EXPERIMENTALLY = "experimentally"
    PRAGMATICALLY = "pragmatically"

    # Risk traits
    SAFELY = "safely"
    BOLDLY = "boldly"
    CAUTIOUSLY = "cautiously"


@dataclass
class Mantra:
    """
    A mantra defines personality and approach for an operation.

    Each mantra translates to specific execution parameters.
    """

    name: str
    traits: List[MantraTrait]
    description: str

    # Execution parameters influenced by mantra
    speed_priority: float = 0.5  # 0-1 (0=quality, 1=speed)
    quality_floor: float = 0.5   # Minimum acceptable quality
    temperature: float = 0.5     # Model temperature
    max_time: float = 30.0       # Seconds
    validation_strictness: float = 0.5  # 0=loose, 1=strict
    retry_attempts: int = 3

    def __str__(self):
        trait_names = [t.value.replace('_', ' ') for t in self.traits]
        return f"{self.name}: {', '.join(trait_names)}"


class MantraLibrary:
    """
    Library of pre-defined mantras for common operation types.

    Users can select mantras, or they're auto-selected based on task type.
    """

    # Pre-defined mantras
    MANTRAS = {
        # Speed-focused mantras
        "lightning_fast": Mantra(
            name="Lightning Fast",
            traits=[MantraTrait.VERY_QUICKLY, MantraTrait.ACCURATELY],
            description="Get result ASAP, maintain basic accuracy",
            speed_priority=0.9,
            quality_floor=0.4,
            temperature=0.3,
            max_time=10.0,
            validation_strictness=0.3,
            retry_attempts=1
        ),

        "quick_and_accurate": Mantra(
            name="Quick & Accurate",
            traits=[MantraTrait.QUICKLY, MantraTrait.ACCURATELY],
            description="Balanced speed and correctness",
            speed_priority=0.7,
            quality_floor=0.6,
            temperature=0.4,
            max_time=20.0,
            validation_strictness=0.5,
            retry_attempts=2
        ),

        # Quality-focused mantras
        "carefully_diligent": Mantra(
            name="Carefully Diligent",
            traits=[MantraTrait.CAREFULLY, MantraTrait.DILIGENTLY],
            description="Thorough, methodical, high quality",
            speed_priority=0.3,
            quality_floor=0.8,
            temperature=0.2,
            max_time=60.0,
            validation_strictness=0.8,
            retry_attempts=5
        ),

        "thoroughly_precise": Mantra(
            name="Thoroughly Precise",
            traits=[MantraTrait.THOROUGHLY, MantraTrait.PRECISELY],
            description="Maximum quality, no rush",
            speed_priority=0.1,
            quality_floor=0.9,
            temperature=0.1,
            max_time=120.0,
            validation_strictness=0.9,
            retry_attempts=10
        ),

        # Creative mantras
        "experimentally_creative": Mantra(
            name="Experimentally Creative",
            traits=[MantraTrait.EXPERIMENTALLY, MantraTrait.CREATIVELY],
            description="Try novel approaches, explore solutions",
            speed_priority=0.4,
            quality_floor=0.5,
            temperature=0.9,
            max_time=90.0,
            validation_strictness=0.4,
            retry_attempts=7
        ),

        "boldly_innovative": Mantra(
            name="Boldly Innovative",
            traits=[MantraTrait.BOLDLY, MantraTrait.CREATIVELY],
            description="Push boundaries, try new things",
            speed_priority=0.5,
            quality_floor=0.4,
            temperature=1.0,
            max_time=60.0,
            validation_strictness=0.3,
            retry_attempts=5
        ),

        # Safe mantras
        "conservatively_safe": Mantra(
            name="Conservatively Safe",
            traits=[MantraTrait.CONSERVATIVELY, MantraTrait.SAFELY],
            description="Proven approaches, minimize risk",
            speed_priority=0.3,
            quality_floor=0.9,
            temperature=0.1,
            max_time=90.0,
            validation_strictness=0.9,
            retry_attempts=8
        ),

        "cautiously_precise": Mantra(
            name="Cautiously Precise",
            traits=[MantraTrait.CAUTIOUSLY, MantraTrait.PRECISELY],
            description="Careful validation, high standards",
            speed_priority=0.2,
            quality_floor=0.85,
            temperature=0.15,
            max_time=75.0,
            validation_strictness=0.85,
            retry_attempts=6
        ),

        # Balanced mantras
        "pragmatically_effective": Mantra(
            name="Pragmatically Effective",
            traits=[MantraTrait.PRAGMATICALLY, MantraTrait.ACCURATELY],
            description="Get it done right, no overthinking",
            speed_priority=0.5,
            quality_floor=0.7,
            temperature=0.4,
            max_time=40.0,
            validation_strictness=0.6,
            retry_attempts=3
        ),

        "deliberately_thorough": Mantra(
            name="Deliberately Thorough",
            traits=[MantraTrait.DELIBERATELY, MantraTrait.THOROUGHLY],
            description="Take time to do it right",
            speed_priority=0.25,
            quality_floor=0.85,
            temperature=0.2,
            max_time=100.0,
            validation_strictness=0.8,
            retry_attempts=7
        )
    }

    @classmethod
    def get(cls, mantra_name: str) -> Optional[Mantra]:
        """Get a mantra by name."""
        return cls.MANTRAS.get(mantra_name)

    @classmethod
    def list_all(cls) -> List[Mantra]:
        """Get all available mantras."""
        return list(cls.MANTRAS.values())

    @classmethod
    def recommend_for_task(cls, task_type: str, execution_mode: str) -> Mantra:
        """
        Recommend a mantra based on task type and execution mode.

        Args:
            task_type: Type of task (api, validation, data_processing, etc.)
            execution_mode: "interactive" or "optimize"

        Returns:
            Recommended mantra
        """

        # Interactive mode: favor speed
        if execution_mode == "interactive":
            if task_type in ["simple_function", "utility", "helper"]:
                return cls.MANTRAS["lightning_fast"]
            elif task_type in ["validation", "parsing"]:
                return cls.MANTRAS["quick_and_accurate"]
            else:
                return cls.MANTRAS["pragmatically_effective"]

        # Optimize mode: favor quality
        else:
            if task_type in ["api_integration", "database", "security"]:
                return cls.MANTRAS["conservatively_safe"]
            elif task_type in ["algorithm", "optimization"]:
                return cls.MANTRAS["deliberately_thorough"]
            elif task_type in ["experiment", "prototype"]:
                return cls.MANTRAS["experimentally_creative"]
            else:
                return cls.MANTRAS["carefully_diligent"]

    @classmethod
    def from_user_input(cls, user_input: str) -> Optional[Mantra]:
        """
        Detect mantra from user's natural language.

        Examples:
        - "quickly write..." → lightning_fast
        - "carefully create..." → carefully_diligent
        - "safely implement..." → conservatively_safe
        """

        input_lower = user_input.lower()

        # Speed signals
        if "very quickly" in input_lower or "asap" in input_lower:
            return cls.MANTRAS["lightning_fast"]
        elif "quickly" in input_lower or "fast" in input_lower:
            return cls.MANTRAS["quick_and_accurate"]

        # Quality signals
        elif "carefully" in input_lower and "diligent" in input_lower:
            return cls.MANTRAS["carefully_diligent"]
        elif "thoroughly" in input_lower or "comprehensive" in input_lower:
            return cls.MANTRAS["thoroughly_precise"]

        # Safe signals
        elif "safely" in input_lower or "conservative" in input_lower:
            return cls.MANTRAS["conservatively_safe"]
        elif "cautiously" in input_lower or "careful" in input_lower:
            return cls.MANTRAS["cautiously_precise"]

        # Creative signals
        elif "experimental" in input_lower or "creative" in input_lower:
            return cls.MANTRAS["experimentally_creative"]
        elif "innovative" in input_lower or "bold" in input_lower:
            return cls.MANTRAS["boldly_innovative"]

        # Pragmatic signals
        elif "pragmatic" in input_lower or "practical" in input_lower:
            return cls.MANTRAS["pragmatically_effective"]

        return None  # No clear mantra detected


class MantraApplicator:
    """
    Applies mantra traits to execution configuration.

    Translates high-level mantra into concrete execution parameters.
    """

    @staticmethod
    def apply_to_generator_config(
        mantra: Mantra,
        base_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply mantra to generator configuration.

        Args:
            mantra: Mantra to apply
            base_config: Base configuration

        Returns:
            Updated configuration with mantra applied
        """

        config = base_config.copy()

        # Model selection based on speed priority
        if mantra.speed_priority > 0.7:
            # Fast models
            config["model"] = config.get("fast_model", "codellama")
        elif mantra.speed_priority < 0.3:
            # Powerful models
            config["model"] = config.get("powerful_model", "deepseek-coder:16b")

        # Temperature from mantra
        config["temperature"] = mantra.temperature

        # Max tokens based on time budget
        if mantra.max_time < 20:
            config["max_tokens"] = 2000
        elif mantra.max_time < 60:
            config["max_tokens"] = 4000
        else:
            config["max_tokens"] = 8000

        # System prompt influenced by mantra traits
        config["system_prompt"] = MantraApplicator._build_system_prompt(mantra)

        return config

    @staticmethod
    def apply_to_workflow(
        mantra: Mantra,
        workflow_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply mantra to workflow execution.

        Args:
            mantra: Mantra to apply
            workflow_config: Workflow configuration

        Returns:
            Updated workflow configuration
        """

        config = workflow_config.copy()

        # Time budget
        config["max_time"] = mantra.max_time

        # Quality settings
        config["quality_floor"] = mantra.quality_floor
        config["validation_strictness"] = mantra.validation_strictness

        # Retry strategy
        config["max_retries"] = mantra.retry_attempts

        # Parallel experiments (only if time allows)
        if mantra.max_time > 60:
            config["use_parallel"] = True
            config["num_experiments"] = 5
        else:
            config["use_parallel"] = False

        # Logging verbosity
        if mantra.speed_priority > 0.7:
            config["log_level"] = "WARNING"  # Minimal logging
        else:
            config["log_level"] = "INFO"  # Detailed logging

        return config

    @staticmethod
    def apply_to_selection_criteria(
        mantra: Mantra,
        base_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply mantra to result selection criteria.

        Args:
            mantra: Mantra to apply
            base_criteria: Base selection criteria

        Returns:
            Updated criteria
        """

        criteria = base_criteria.copy()

        # Quality vs speed weights from mantra
        criteria["quality_weight"] = 1.0 - mantra.speed_priority
        criteria["speed_weight"] = mantra.speed_priority

        # Quality floor
        criteria["min_quality_score"] = mantra.quality_floor

        # Time constraints
        criteria["max_generation_time"] = mantra.max_time

        return criteria

    @staticmethod
    def _build_system_prompt(mantra: Mantra) -> str:
        """Build system prompt that embodies the mantra."""

        trait_instructions = {
            MantraTrait.VERY_QUICKLY: "Work VERY QUICKLY. Prioritize speed above all.",
            MantraTrait.QUICKLY: "Work efficiently and quickly, but maintain quality.",
            MantraTrait.CAREFULLY: "Work carefully and pay attention to details.",
            MantraTrait.DILIGENTLY: "Be thorough and diligent in your approach.",
            MantraTrait.THOROUGHLY: "Be comprehensive and leave nothing out.",
            MantraTrait.ACCURATELY: "Focus on correctness and accuracy.",
            MantraTrait.PRECISELY: "Be precise and exact in your implementation.",
            MantraTrait.CONSERVATIVELY: "Use proven, conservative approaches.",
            MantraTrait.SAFELY: "Prioritize safety and minimize risk.",
            MantraTrait.CREATIVELY: "Think creatively and explore novel solutions.",
            MantraTrait.EXPERIMENTALLY: "Try experimental approaches.",
            MantraTrait.BOLDLY: "Be bold and innovative.",
            MantraTrait.PRAGMATICALLY: "Be pragmatic and focus on what works.",
            MantraTrait.DELIBERATELY: "Work deliberately and methodically.",
            MantraTrait.METHODICALLY: "Use a systematic, step-by-step approach.",
            MantraTrait.CAUTIOUSLY: "Proceed cautiously and validate each step."
        }

        instructions = [trait_instructions.get(trait, "") for trait in mantra.traits]
        instructions = [i for i in instructions if i]  # Remove empty

        prompt = f"""You are a code generation assistant with this approach:

{mantra.description.upper()}

Your operating principles:
"""
        for i, instruction in enumerate(instructions, 1):
            prompt += f"{i}. {instruction}\n"

        prompt += f"\nQuality floor: {mantra.quality_floor:.0%}"
        prompt += f"\nTime budget: {mantra.max_time:.0f} seconds"

        return prompt


# Example usage
def example_usage():
    """Examples of using mantras."""

    # Get a specific mantra
    mantra = MantraLibrary.get("lightning_fast")
    print(f"Mantra: {mantra}")
    print(f"Speed priority: {mantra.speed_priority}")
    print(f"Temperature: {mantra.temperature}")

    # Recommend mantra for task
    recommended = MantraLibrary.recommend_for_task(
        task_type="api_integration",
        execution_mode="optimize"
    )
    print(f"\nRecommended: {recommended}")

    # Detect from user input
    user_mantra = MantraLibrary.from_user_input("Quickly write a validator")
    print(f"\nDetected: {user_mantra}")

    # Apply to configuration
    base_config = {"fast_model": "codellama", "powerful_model": "deepseek-coder:16b"}
    applied = MantraApplicator.apply_to_generator_config(mantra, base_config)
    print(f"\nApplied config: {applied}")

    # List all mantras
    print("\n\nAll available mantras:")
    for m in MantraLibrary.list_all():
        print(f"- {m}")


if __name__ == "__main__":
    example_usage()
