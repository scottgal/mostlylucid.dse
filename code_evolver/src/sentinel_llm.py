"""
Sentinel LLM - Fast Intent Detection Layer

A tiny, fast LLM (1b model) that runs BEFORE the main workflow to:

1. Detect execution mode from natural language:
   - "Take your time and..." → OPTIMIZE mode
   - "As quickly as possible..." → INTERACTIVE mode
   - "Quickly write..." → INTERACTIVE mode
   - "Carefully design..." → OPTIMIZE mode

2. Extract task requirements:
   - What the user actually wants
   - Priority level
   - Quality expectations

3. Route to appropriate workflow:
   - INTERACTIVE: Quick spec → LLM → result
   - OPTIMIZE: Multi-step workflow → parallel experiments → best result

Benefits:
- User doesn't need to specify mode explicitly
- Natural conversation flow
- Appropriate workflow selected automatically
- 1b model is VERY fast (~500ms)
"""

import logging
import re
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class IntentSignal(Enum):
    """Intent signals detected from user input."""

    SPEED_PRIORITY = "speed"          # "quickly", "asap", "fast"
    QUALITY_PRIORITY = "quality"       # "carefully", "robust", "thorough"
    TIME_AVAILABLE = "take_time"       # "take your time", "no rush"
    TIME_CONSTRAINED = "urgent"        # "urgent", "immediate", "now"
    EXPLORATORY = "experiment"         # "try", "experiment", "explore"
    PRODUCTION = "production"          # "production", "critical", "important"


class SentinelLLM:
    """
    Fast 1b LLM that detects user intent and execution mode.

    Runs BEFORE main workflow to route appropriately.
    """

    def __init__(self, ollama_client):
        """
        Initialize sentinel LLM.

        Args:
            ollama_client: OllamaClient for LLM calls
        """
        self.client = ollama_client
        self.sentinel_model = "tinyllama"  # 1b model, very fast (~500ms)

    def detect_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Detect user intent from natural language.

        Args:
            user_input: User's request

        Returns:
            Dict with:
            - execution_mode: "interactive" or "optimize"
            - priority: "speed" or "quality"
            - urgency: "high" or "normal"
            - signals: List of detected intent signals
            - reasoning: Why this mode was selected
        """

        # Fast pattern matching first (no LLM needed for obvious cases)
        quick_result = self._quick_pattern_match(user_input)
        if quick_result:
            logger.info(f"Quick mode detection: {quick_result['execution_mode']}")
            return quick_result

        # Use sentinel LLM for ambiguous cases
        llm_result = self._llm_intent_detection(user_input)

        logger.info(f"LLM mode detection: {llm_result['execution_mode']}")
        return llm_result

    def _quick_pattern_match(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Quick pattern matching for obvious intent signals.

        No LLM needed for clear cases like "quickly write..."
        """

        input_lower = user_input.lower()

        # SPEED signals (→ INTERACTIVE mode)
        speed_patterns = [
            r'\bquickly\b', r'\bfast\b', r'\basap\b', r'\bas soon as possible\b',
            r'\brapid(ly)?\b', r'\bimmediate(ly)?\b', r'\bright now\b',
            r'\bin a hurry\b', r'\bsimple\b', r'\bjust\b'
        ]

        # QUALITY signals (→ OPTIMIZE mode)
        quality_patterns = [
            r'\btake your time\b', r'\bcarefully\b', r'\bthorough(ly)?\b',
            r'\brobust\b', r'\bproduction\b', r'\bcritical\b',
            r'\bimportant\b', r'\bwell[-\s]designed\b', r'\bcomprehensive\b'
        ]

        # Count matches
        speed_score = sum(1 for p in speed_patterns if re.search(p, input_lower))
        quality_score = sum(1 for p in quality_patterns if re.search(p, input_lower))

        # Clear speed priority
        if speed_score >= 2 and speed_score > quality_score:
            return {
                "execution_mode": "interactive",
                "priority": "speed",
                "urgency": "high",
                "signals": ["speed_priority", "time_constrained"],
                "reasoning": "Detected speed/urgency keywords",
                "confidence": 0.9
            }

        # Clear quality priority
        if quality_score >= 2 and quality_score > speed_score:
            return {
                "execution_mode": "optimize",
                "priority": "quality",
                "urgency": "normal",
                "signals": ["quality_priority", "time_available"],
                "reasoning": "Detected quality/thoroughness keywords",
                "confidence": 0.9
            }

        # Ambiguous - need LLM
        return None

    def _llm_intent_detection(self, user_input: str) -> Dict[str, Any]:
        """
        Use sentinel LLM to detect intent for ambiguous cases.
        """

        prompt = f"""Analyze this user request and determine execution mode.

USER REQUEST:
"{user_input}"

QUESTION: Should this be handled in INTERACTIVE (fast) or OPTIMIZE (thorough) mode?

INTERACTIVE mode (fast):
- User wants result quickly
- Simple, straightforward task
- "quickly", "asap", "simple"
- Single-shot approach

OPTIMIZE mode (thorough):
- User wants high quality
- Complex, critical task
- "carefully", "robust", "production"
- Multi-step, experimental approach

Respond with ONLY a JSON object:
{{
    "execution_mode": "interactive" or "optimize",
    "priority": "speed" or "quality",
    "urgency": "high" or "normal",
    "reasoning": "why this mode"
}}
"""

        try:
            # Use tiny 1b model (VERY fast, ~500ms)
            response = self.client.generate(
                model=self.sentinel_model,
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent decisions
                max_tokens=100  # Short response
            )

            # Parse JSON response
            import json
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # Add confidence
                result["confidence"] = 0.7  # LLM-based, slightly lower confidence
                result["signals"] = [result["priority"] + "_priority"]

                return result

        except Exception as e:
            logger.warning(f"Sentinel LLM failed: {e}")

        # Default: Interactive (favor speed for user experience)
        return {
            "execution_mode": "interactive",
            "priority": "speed",
            "urgency": "normal",
            "signals": [],
            "reasoning": "Default (sentinel detection failed)",
            "confidence": 0.5
        }

    def should_use_simple_workflow(self, user_input: str) -> bool:
        """
        Determine if a simple spec → LLM workflow is sufficient.

        For VERY simple requests, skip complex multi-step workflow.

        Args:
            user_input: User's request

        Returns:
            True if simple workflow (spec → LLM) is sufficient
        """

        intent = self.detect_intent(user_input)

        # Interactive mode with high urgency → simple workflow
        if intent["execution_mode"] == "interactive" and intent["urgency"] == "high":
            return True

        # Check for "simple" keywords
        simple_keywords = ["simple", "basic", "quick", "just", "write a"]
        if any(kw in user_input.lower() for kw in simple_keywords):
            return True

        # Otherwise, use full workflow
        return False

    def route_workflow(self, user_input: str) -> Dict[str, Any]:
        """
        Route user request to appropriate workflow.

        Args:
            user_input: User's request

        Returns:
            Workflow configuration:
            - workflow_type: "simple_spec", "interactive", "optimize"
            - execution_mode: "interactive" or "optimize"
            - config: Additional configuration
        """

        intent = self.detect_intent(user_input)

        # VERY simple request → spec → LLM (no multi-step)
        if self.should_use_simple_workflow(user_input):
            return {
                "workflow_type": "simple_spec",
                "execution_mode": "interactive",
                "steps": ["generate_spec", "generate_code", "test"],
                "max_time": 15,  # 15 seconds max
                "reasoning": "Simple request, use quick spec-to-code workflow"
            }

        # Interactive mode → single best generator
        if intent["execution_mode"] == "interactive":
            return {
                "workflow_type": "interactive",
                "execution_mode": "interactive",
                "steps": [
                    "consult_overseer",
                    "generate_code",
                    "test",
                    "auto_fix_if_needed"
                ],
                "max_time": 30,  # 30 seconds max
                "use_parallel": False,
                "reasoning": intent["reasoning"]
            }

        # Optimize mode → parallel experiments
        else:
            return {
                "workflow_type": "optimize",
                "execution_mode": "optimize",
                "steps": [
                    "consult_overseer",
                    "parallel_generation",
                    "test_all_variants",
                    "select_best",
                    "evolve_tools"
                ],
                "max_time": 300,  # 5 minutes
                "use_parallel": True,
                "num_experiments": 5,
                "reasoning": intent["reasoning"]
            }

    def extract_task_requirements(self, user_input: str) -> Dict[str, Any]:
        """
        Extract what the user actually wants.

        Args:
            user_input: User's request

        Returns:
            Dict with:
            - task_type: "api_integration", "data_processing", etc.
            - main_goal: What the user wants to achieve
            - constraints: Any specific requirements
            - quality_level: Expected quality
        """

        prompt = f"""Extract task requirements from this request.

USER REQUEST:
"{user_input}"

What are the key requirements?

Respond with ONLY a JSON object:
{{
    "task_type": "api_integration" | "data_processing" | "simple_function" | "workflow" | "other",
    "main_goal": "brief description of what user wants",
    "constraints": ["constraint 1", "constraint 2"],
    "quality_level": "basic" | "production" | "critical"
}}
"""

        try:
            response = self.client.generate(
                model=self.sentinel_model,
                prompt=prompt,
                temperature=0.1,
                max_tokens=150
            )

            import json
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            logger.warning(f"Could not extract requirements: {e}")

        # Default
        return {
            "task_type": "other",
            "main_goal": user_input[:100],
            "constraints": [],
            "quality_level": "production"
        }


# Example usage
def example_usage():
    """
    Examples of sentinel LLM detecting modes from natural language.
    """

    sentinel = SentinelLLM(ollama_client)

    # Example 1: Speed priority
    result1 = sentinel.detect_intent("Quickly write a function to validate emails")
    # Returns: {"execution_mode": "interactive", "priority": "speed"}

    # Example 2: Quality priority
    result2 = sentinel.detect_intent("Take your time and create a robust API client for Stripe")
    # Returns: {"execution_mode": "optimize", "priority": "quality"}

    # Example 3: Urgent
    result3 = sentinel.detect_intent("I need this ASAP - write a CSV parser")
    # Returns: {"execution_mode": "interactive", "urgency": "high"}

    # Example 4: Production quality
    result4 = sentinel.detect_intent("Carefully design a production-ready authentication system")
    # Returns: {"execution_mode": "optimize", "quality_level": "critical"}

    # Routing
    workflow1 = sentinel.route_workflow("Quickly write a function")
    # Returns: {"workflow_type": "simple_spec", "max_time": 15}

    workflow2 = sentinel.route_workflow("Create a robust API integration")
    # Returns: {"workflow_type": "optimize", "use_parallel": True}
