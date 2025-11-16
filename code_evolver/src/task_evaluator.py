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
    ACCIDENTAL = "accidental"                  # Nonsense/accidental input → ask for clarification
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
                - is_accidental: bool
                - suggestions: list (if accidental)
        """
        input_length = len(description)

        # Quick check for obviously accidental input
        accidental_check = self._check_if_accidental(description)
        if accidental_check['is_accidental']:
            return {
                "task_type": TaskType.ACCIDENTAL,
                "understanding": accidental_check['understanding'],
                "key_aspects": "unclear, needs clarification",
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "none",
                "reason": "Input appears accidental or unclear",
                "is_accidental": True,
                "suggestions": accidental_check['suggestions'],
                "input_length": input_length,
                "evaluation_model": "rule-based"
            }

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

        prompt = f"""Task: "{description}"

Classify as ONE:
- creative_content: stories, jokes, articles, poems, OR GENERATING SAMPLE/TEST/RANDOM DATA
- arithmetic: math calculations, number operations
- data_processing: filtering, sorting, transforming EXISTING data (NOT generating new data)
- code_generation: writing functions, programs
- translation: language translation
- question_answering: answering questions, explaining concepts
- formatting: changing text format/case
- conversion: converting between formats
- unknown: unclear tasks

IMPORTANT: "generate data", "create sample data", "random data" → creative_content (needs LLM)
           "filter data", "sort data" → data_processing (can use code)

Also rate COMPLEXITY:
simple, moderate, complex

CATEGORY: [pick one]
COMPLEXITY: [pick one]"""

        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                model_key="triage"
            )

            # Parse structured response - extract category and complexity
            lines = response.strip().split('\n')
            category_line = next((l for l in lines if l.startswith('CATEGORY:')), '')
            complexity_line = next((l for l in lines if l.startswith('COMPLEXITY:')), '')

            category = category_line.replace('CATEGORY:', '').strip().lower().replace("-", "_")
            complexity = complexity_line.replace('COMPLEXITY:', '').strip().lower()

            # CRITICAL: Override category for data GENERATION requests
            # (even if tinyllama classified it as data_processing)
            desc_lower = description.lower()
            if any(keyword in desc_lower for keyword in ["generate data", "create data", "sample data",
                                                         "random data", "fake data", "mock data",
                                                         "test data", "dummy data", "synthetic data",
                                                         "generate sample", "create sample", "make up data"]):
                # Data generation needs LLM, not code loops
                logger.info(f"Detected data generation request - overriding to creative_content")
                category = 'creative_content'

            # Don't try to parse understanding or key_aspects - tinyllama is too unreliable
            understanding = ""
            key_aspects = ""

            # Fallback: Try to extract from unstructured response
            if not category or not complexity:
                # Try to infer from response content
                response_lower = response.lower()

                # Extract category from keywords
                if not category:
                    if any(word in response_lower for word in ['joke', 'story', 'poem', 'creative', 'article', 'content']):
                        category = 'creative_content'
                    elif any(word in response_lower for word in ['math', 'calculate', 'arithmetic', 'number']):
                        category = 'arithmetic'
                    elif any(word in response_lower for word in ['code', 'function', 'program']):
                        category = 'code_generation'
                    elif any(word in response_lower for word in ['question', 'answer', 'explain']):
                        category = 'question_answering'
                    elif any(word in response_lower for word in ['accidental', 'unclear', 'nonsense', 'invalid']):
                        category = 'accidental'
                    else:
                        category = 'unknown'

                # Extract complexity from keywords if not found
                if not complexity:
                    desc_lower = description.lower()
                    # Keyword-based complexity detection
                    if any(word in desc_lower for word in ['simple', 'basic', 'quick', 'small', 'easy']):
                        complexity = 'simple'
                    elif any(word in desc_lower for word in ['complex', 'advanced', 'system', 'architecture', 'multi', 'design']):
                        complexity = 'complex'
                    else:
                        complexity = 'moderate'

            # Map to TaskType
            task_type = self._parse_task_type(category)

            # Determine requirements (pass complexity for better routing)
            routing = self._determine_routing(task_type, description, complexity)

            logger.info(f"Task classified as: {task_type.value} (complexity: {complexity}) → {routing['recommended_tier']}")

            return {
                "task_type": task_type,
                "complexity": complexity,
                "understanding": understanding,
                "key_aspects": key_aspects,
                "input_length": input_length,
                "evaluation_model": model,
                **routing
            }

        except Exception as e:
            logger.error(f"Error evaluating task type: {e}")
            # Safe default: assume needs LLM
            return {
                "task_type": TaskType.UNKNOWN,
                "complexity": "moderate",
                "understanding": "Unable to evaluate task due to an error",
                "key_aspects": "error, unknown",
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "code.general",  # Updated from coding.tier_2
                "reason": f"Error during evaluation: {e}",
                "input_length": input_length,
                "evaluation_model": "none"
            }

    def _check_if_accidental(self, description: str) -> Dict[str, Any]:
        """
        Check if input appears to be accidental or nonsense.

        Returns:
            Dict with is_accidental, understanding, suggestions
        """
        desc_lower = description.lower().strip()
        desc_clean = ''.join(c for c in desc_lower if c.isalnum() or c.isspace())
        words = desc_lower.split()

        # Patterns that suggest accidental input
        accidental_patterns = [
            # Very short nonsense (but allow short math tasks like "add 10 and 20")
            len(description) <= 2,
            # Common test inputs (single word only)
            len(words) == 1 and desc_lower in ['test', 'testing', 'asdf', 'qwerty', 'hello', 'hi', 'abc'],
            # Just numbers with no context (but allow "add 10 and 20")
            len(words) == 1 and desc_clean.isdigit(),
            # Random keypresses (3+ consecutive same char)
            any(description.count(c * 3) > 0 for c in set(description) if c.isalpha()),
            # Just punctuation
            desc_clean == '',
            # Mostly consonants with no real words (unlikely to be real)
            len(desc_clean) > 3 and len(words) == 1 and sum(1 for c in desc_clean if c in 'aeiou') < len(desc_clean) * 0.2,
        ]

        is_accidental = any(accidental_patterns)

        if is_accidental:
            # Generate helpful suggestions based on what we detected
            suggestions = []

            if desc_lower in ['test', 'testing']:
                suggestions = [
                    "Try: 'write a function to add two numbers'",
                    "Try: 'create a fibonacci sequence generator'",
                    "Try: 'write a joke about programming'"
                ]
                understanding = "This looks like a test input"
            elif len(description) <= 2:
                suggestions = [
                    "Describe what you want to create",
                    "Try: 'sort a list of numbers'",
                    "Try: 'translate text to french'"
                ]
                understanding = "Input is too short to understand"
            elif desc_clean == '':
                suggestions = [
                    "Please enter a task description",
                    "Example: 'write a story about a robot'",
                    "Example: 'calculate prime numbers'"
                ]
                understanding = "No meaningful text detected"
            else:
                suggestions = [
                    "Please rephrase your request more clearly",
                    "Example: 'write a function that...'",
                    "Example: 'create a program to...'"
                ]
                understanding = "Input is unclear or may be accidental"

            return {
                'is_accidental': True,
                'understanding': understanding,
                'suggestions': suggestions
            }

        return {'is_accidental': False}

    def _parse_task_type(self, category: str) -> TaskType:
        """Parse category string to TaskType enum."""
        try:
            # Try direct match
            return TaskType(category)
        except ValueError:
            # Try fuzzy matching
            # IMPORTANT: Check for data GENERATION first (needs LLM)
            # before generic data processing (can use code)
            if any(keyword in category for keyword in ["generate data", "create data", "sample data",
                                                       "random data", "fake data", "mock data",
                                                       "test data", "dummy data", "synthetic data"]):
                # Data generation needs LLM for realistic results
                return TaskType.CREATIVE_CONTENT
            elif "creative" in category or "content" in category or "story" in category or "joke" in category:
                return TaskType.CREATIVE_CONTENT
            elif "math" in category or "arithmetic" in category or "calculate" in category:
                return TaskType.ARITHMETIC
            elif "data" in category or "process" in category:
                # Generic data processing (filter, sort, transform) can use code
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

    def _determine_routing(self, task_type: TaskType, description: str, complexity: str = "moderate") -> Dict[str, Any]:
        """
        Determine routing requirements based on task type and complexity.

        Args:
            task_type: The type of task
            description: Task description
            complexity: Task complexity (simple, moderate, complex)

        Returns:
            Dict with requires_llm, requires_content_llm, can_use_tools, recommended_tier, reason
        """
        # Accidental input - should not proceed
        if task_type == TaskType.ACCIDENTAL:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "none",
                "reason": "Input appears accidental or unclear - needs clarification"
            }

        # CRITICAL: Creative content ALWAYS needs LLM (medium+ tier)
        if task_type == TaskType.CREATIVE_CONTENT:
            return {
                "requires_llm": True,
                "requires_content_llm": True,
                "can_use_tools": False,
                "recommended_tier": "content.general",  # Updated from content.tier_2
                "reason": "Creative content requires LLM generation (stories, jokes, poems, articles)"
            }

        # Question answering needs LLM
        elif task_type == TaskType.QUESTION_ANSWERING:
            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "content.general",  # Updated from content.tier_2
                "reason": "Question answering requires LLM knowledge"
            }

        # Code generation needs coding LLM - tier based on complexity
        elif task_type == TaskType.CODE_GENERATION:
            # Select tier based on complexity assessment
            if complexity == "simple":
                tier = "code.fast"  # Updated from coding.tier_1
                reason = "Simple code generation (basic functions, straightforward logic)"
            elif complexity == "complex":
                tier = "code.escalation"  # Updated from coding.tier_3
                reason = "Complex code generation (advanced algorithms, system design)"
            else:  # moderate
                tier = "code.general"  # Updated from coding.tier_2
                reason = "Standard code generation (multi-step workflows, moderate complexity)"

            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": tier,
                "reason": reason
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
                    "recommended_tier": "content.general",  # Updated from content.tier_2
                    "reason": "Complex translation requires LLM for context/nuance"
                }

        # Data processing can use code
        elif task_type == TaskType.DATA_PROCESSING:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "code.fast",  # Updated from coding.tier_1
                "reason": "Data processing can use generated code"
            }

        # Unknown - safe default to LLM
        else:
            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "content.general",  # Updated from content.tier_2
                "reason": "Unknown task type, defaulting to LLM for safety"
            }
