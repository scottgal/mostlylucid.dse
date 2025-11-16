"""
Task Type Evaluator - Uses tinyllama to classify tasks and determine routing.

Prevents over-optimization by ensuring creative/content tasks use appropriate LLMs.
"""
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks for routing decisions."""
    CREATIVE_CONTENT = "creative_content"      # Stories, jokes, poems, articles → needs LLM
    ARITHMETIC = "arithmetic"                  # Math calculations → can use tools
    DATA_PROCESSING = "data_processing"        # Transform, filter, sort → can use tools
    CODE_GENERATION = "code_generation"        # Write functions → needs LLM
    TRANSLATION = "translation"                # Language translation → can use tools for simple, LLM for complex
    QUESTION_ANSWERING = "question_answering"  # Answer questions → needs LLM
    FORMATTING = "formatting"                  # Text formatting → can use tools
    CONVERSION = "conversion"                  # Unit/format conversion → can use tools
    UNKNOWN = "unknown"                        # Needs LLM analysis


class TaskEvaluator:
    """Evaluates task type and routing requirements."""

    # Max tokens for tinyllama context (conservative estimate)
    TINYLLAMA_MAX_TOKENS = 500  # ~2000 chars

    # Input length thresholds
    SHORT_INPUT = 200    # < 200 chars → use tinyllama
    MEDIUM_INPUT = 1000  # < 1000 chars → use phi3 or gemma
    LONG_INPUT = 5000    # < 5000 chars → use llama3

    def __init__(self, ollama_client):
        """
        Initialize task evaluator.

        Args:
            ollama_client: OllamaClient for LLM inference
        """
        self.client = ollama_client

    def evaluate_task_type(self, description: str) -> Dict[str, Any]:
        """
        Classify task type and determine routing.

        Args:
            description: Task description from user

        Returns:
            Dict with:
                - task_type: TaskType enum
                - requires_llm: bool
                - requires_content_llm: bool (medium+ tier for creative tasks)
                - can_use_tools: bool
                - recommended_tier: str
                - reason: str
        """
        input_length = len(description)

        # Choose model based on input length
        if input_length < self.SHORT_INPUT:
            model = "tinyllama"
            tier = "very-fast"
        elif input_length < self.MEDIUM_INPUT:
            model = "phi3:mini"
            tier = "fast"
        elif input_length < self.LONG_INPUT:
            model = "gemma3:4b"
            tier = "fast"
        else:
            model = "llama3"
            tier = "medium"

        logger.info(f"Evaluating task type with {model} (input length: {input_length} chars)")

        prompt = f"""Classify this task into ONE category. Respond with ONLY the category name.

Task: {description}

Categories:
- creative_content: Writing stories, jokes, poems, articles, creative text (MUST use LLM)
- arithmetic: Math calculations, numerical operations (can use calculator tool)
- data_processing: Transform/filter/sort data, manipulate structures (can use code)
- code_generation: Write code/functions (MUST use LLM)
- translation: Translate text between languages (simple: tool, complex: LLM)
- question_answering: Answer questions, explain concepts (MUST use LLM)
- formatting: Format text (uppercase, lowercase, etc.) (can use tool)
- conversion: Convert units, formats (can use tool)
- unknown: Unclear or complex task (needs LLM analysis)

Category:"""

        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                model_key="triage"
            )

            # Parse response
            category = response.strip().lower().replace("-", "_")

            # Map to TaskType
            task_type = self._parse_task_type(category)

            # Determine requirements
            routing = self._determine_routing(task_type, description)

            logger.info(f"Task classified as: {task_type.value} → {routing['recommended_tier']}")

            return {
                "task_type": task_type,
                "input_length": input_length,
                "evaluation_model": model,
                **routing
            }

        except Exception as e:
            logger.error(f"Error evaluating task type: {e}")
            # Safe default: assume needs LLM
            return {
                "task_type": TaskType.UNKNOWN,
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "medium",
                "reason": f"Error during evaluation: {e}",
                "input_length": input_length,
                "evaluation_model": "none"
            }

    def _parse_task_type(self, category: str) -> TaskType:
        """Parse category string to TaskType enum."""
        try:
            # Try direct match
            return TaskType(category)
        except ValueError:
            # Try fuzzy matching
            if "creative" in category or "content" in category or "story" in category or "joke" in category:
                return TaskType.CREATIVE_CONTENT
            elif "math" in category or "arithmetic" in category or "calculate" in category:
                return TaskType.ARITHMETIC
            elif "data" in category or "process" in category:
                return TaskType.DATA_PROCESSING
            elif "code" in category or "function" in category or "program" in category:
                return TaskType.CODE_GENERATION
            elif "translate" in category or "translation" in category:
                return TaskType.TRANSLATION
            elif "question" in category or "answer" in category or "explain" in category:
                return TaskType.QUESTION_ANSWERING
            elif "format" in category or "case" in category:
                return TaskType.FORMATTING
            elif "convert" in category or "conversion" in category:
                return TaskType.CONVERSION
            else:
                return TaskType.UNKNOWN

    def _determine_routing(self, task_type: TaskType, description: str) -> Dict[str, Any]:
        """
        Determine routing requirements based on task type.

        Returns:
            Dict with requires_llm, requires_content_llm, can_use_tools, recommended_tier, reason
        """
        # CRITICAL: Creative content ALWAYS needs LLM (medium+ tier)
        if task_type == TaskType.CREATIVE_CONTENT:
            return {
                "requires_llm": True,
                "requires_content_llm": True,
                "can_use_tools": False,
                "recommended_tier": "content.tier_2",  # Medium content LLM
                "reason": "Creative content requires LLM generation (stories, jokes, poems, articles)"
            }

        # Question answering needs LLM
        elif task_type == TaskType.QUESTION_ANSWERING:
            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "content.tier_2",
                "reason": "Question answering requires LLM knowledge"
            }

        # Code generation needs coding LLM
        elif task_type == TaskType.CODE_GENERATION:
            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "coding.tier_2",
                "reason": "Code generation requires coding LLM"
            }

        # Arithmetic can use calculator tools
        elif task_type == TaskType.ARITHMETIC:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "executable",
                "reason": "Arithmetic can use calculator tool (zero-cost)"
            }

        # Formatting can use text formatter tools
        elif task_type == TaskType.FORMATTING:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "executable",
                "reason": "Text formatting can use formatter tool (zero-cost)"
            }

        # Conversion can use converter tools
        elif task_type == TaskType.CONVERSION:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "executable",
                "reason": "Unit conversion can use converter tool (zero-cost)"
            }

        # Translation - simple can use tool, complex needs LLM
        elif task_type == TaskType.TRANSLATION:
            # Check if it's a simple word/phrase translation
            words = description.split()
            if len(words) <= 10:  # Simple translation
                return {
                    "requires_llm": False,
                    "requires_content_llm": False,
                    "can_use_tools": True,
                    "recommended_tier": "llm.quick_translator",
                    "reason": "Simple translation can use quick_translator tool"
                }
            else:  # Complex translation
                return {
                    "requires_llm": True,
                    "requires_content_llm": True,
                    "can_use_tools": False,
                    "recommended_tier": "content.tier_2",
                    "reason": "Complex translation requires LLM for context/nuance"
                }

        # Data processing can use code
        elif task_type == TaskType.DATA_PROCESSING:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "coding.tier_1",
                "reason": "Data processing can use generated code"
            }

        # Unknown - safe default to LLM
        else:
            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "content.tier_2",
                "reason": "Unknown task type, defaulting to LLM for safety"
            }
