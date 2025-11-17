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

    def __init__(self, ollama_client, rag_memory=None):
        """
        Initialize sentinel LLM.

        Args:
            ollama_client: OllamaClient for LLM calls
            rag_memory: Optional RAG memory for duplicate detection
        """
        self.client = ollama_client
        self.rag = rag_memory
        self.sentinel_model = "gemma3:1b"  # 1b model, very fast (~500ms)
        self.reviewer_model = "gemma3:4b"  # 4b model for reviewing near-duplicates
        self.clarification_history = []  # Store Q&A for context

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
            - mantra: Detected mantra (optional)
        """

        # Fast pattern matching first (no LLM needed for obvious cases)
        quick_result = self._quick_pattern_match(user_input)
        if quick_result:
            logger.info(f"Quick mode detection: {quick_result['execution_mode']}")
            # Also detect mantra
            quick_result["mantra"] = self._detect_mantra(user_input)
            return quick_result

        # Use sentinel LLM for ambiguous cases
        llm_result = self._llm_intent_detection(user_input)

        logger.info(f"LLM mode detection: {llm_result['execution_mode']}")
        # Also detect mantra
        llm_result["mantra"] = self._detect_mantra(user_input)
        return llm_result

    def _detect_mantra(self, user_input: str) -> Optional[str]:
        """
        Detect mantra from user input.

        Args:
            user_input: User's request

        Returns:
            Mantra name, or None if no clear mantra
        """
        try:
            from src.mantras import MantraLibrary

            mantra = MantraLibrary.from_user_input(user_input)
            if mantra:
                logger.info(f"Detected mantra: {mantra.name}")
                return mantra.name

        except Exception as e:
            logger.debug(f"Could not detect mantra: {e}")

        return None

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

    def check_for_duplicate(self, user_input: str, task_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if this request is identical or very similar to existing artifacts in RAG.

        Flow:
        - 100% semantic match (similarity >= 0.98) → Return artifact directly (FAST)
        - >95% match → Ask 4b LLM to review if mutation needed
        - <95% match → Run full workflow

        Args:
            user_input: User's request
            task_type: Optional task type for filtering (e.g., "translation", "api_integration")

        Returns:
            Dict with:
            - is_duplicate: bool
            - confidence: float (0.0-1.0)
            - existing_artifact: Artifact if duplicate found
            - should_reuse: bool
            - reasoning: str
        """
        if not self.rag:
            return {
                "is_duplicate": False,
                "confidence": 0.0,
                "should_reuse": False,
                "reasoning": "RAG not available"
            }

        try:
            from src.rag_memory import ArtifactType

            # Search for similar functions in RAG
            similar_results = self.rag.find_similar(
                query=user_input,
                artifact_type=ArtifactType.FUNCTION,
                top_k=3
            )

            if not similar_results:
                return {
                    "is_duplicate": False,
                    "confidence": 0.0,
                    "should_reuse": False,
                    "reasoning": "No similar artifacts found"
                }

            best_match, similarity = similar_results[0]

            logger.info(f"Found similar artifact: {best_match.name} (similarity: {similarity:.2%})")

            # 100% match (or very close) → Use directly, no review needed
            if similarity >= 0.98:
                logger.info(f"✓ 100% match - reusing existing artifact directly")
                return {
                    "is_duplicate": True,
                    "confidence": similarity,
                    "existing_artifact": best_match,
                    "should_reuse": True,
                    "reasoning": "100% semantic match - identical request",
                    "review_needed": False
                }

            # Very similar (95-98%) → Ask 4b LLM to review
            elif similarity >= 0.95:
                logger.info(f"High similarity ({similarity:.2%}) - asking 4b LLM for review")

                review_result = self._review_duplicate(user_input, best_match)

                return {
                    "is_duplicate": review_result["is_same_task"],
                    "confidence": similarity,
                    "existing_artifact": best_match,
                    "should_reuse": review_result["is_same_task"],
                    "reasoning": review_result["reasoning"],
                    "review_needed": True,
                    "review": review_result
                }

            # Low similarity (<95%) → Run full workflow
            else:
                logger.info(f"Low similarity ({similarity:.2%}) - running full workflow")
                return {
                    "is_duplicate": False,
                    "confidence": similarity,
                    "existing_artifact": best_match,
                    "should_reuse": False,
                    "reasoning": f"Similarity {similarity:.2%} too low - needs new implementation"
                }

        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return {
                "is_duplicate": False,
                "confidence": 0.0,
                "should_reuse": False,
                "reasoning": f"Error during duplicate check: {e}"
            }

    def _review_duplicate(self, user_request: str, existing_artifact) -> Dict[str, Any]:
        """
        Use 4b LLM to review if near-duplicate is the same task or needs mutation.

        Args:
            user_request: New user request
            existing_artifact: Existing artifact from RAG

        Returns:
            Dict with is_same_task (bool) and reasoning (str)
        """
        prompt = f"""Compare these two tasks and determine if they are IDENTICAL or need different implementations.

NEW REQUEST:
"{user_request}"

EXISTING ARTIFACT:
Name: {existing_artifact.name}
Description: {existing_artifact.description}
Tags: {', '.join(existing_artifact.tags)}

QUESTION: Is the NEW REQUEST asking for the EXACT SAME thing as the EXISTING ARTIFACT?

Consider:
- Are the core requirements identical?
- Do any parameter differences require code changes?
- Is the task semantically the same even if worded differently?

Examples of SAME:
- "translate hello to french" vs "translate 'hello' into french" → SAME
- "validate email addresses" vs "check if emails are valid" → SAME
- "sort list of numbers" vs "arrange numbers in order" → SAME

Examples of DIFFERENT (need mutation):
- "translate hello to french" vs "translate hello to spanish" → DIFFERENT (language changed)
- "validate emails with regex" vs "validate emails with API" → DIFFERENT (method changed)
- "sort ascending" vs "sort descending" → DIFFERENT (order changed)

Respond with ONLY "yes" or "no":
- yes: Exact same task, reuse existing artifact
- no: Different task, needs new implementation

Answer (yes/no):"""

        try:
            response = self.client.generate(
                model=self.reviewer_model,
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent binary decisions
                max_tokens=10
            ).strip().lower()

            is_same = "yes" in response

            return {
                "is_same_task": is_same,
                "reasoning": f"4b review: {'Identical task - reuse existing' if is_same else 'Different task - needs mutation'}",
                "review_response": response
            }

        except Exception as e:
            logger.error(f"4b review failed: {e}")
            # Default to false (run new workflow) on error
            return {
                "is_same_task": False,
                "reasoning": f"Review failed, running new workflow for safety: {e}",
                "review_response": ""
            }

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

    def should_interrupt_background_process(
        self,
        process_info: Dict[str, Any],
        user_input: str
    ) -> Dict[str, Any]:
        """
        Decide if user input requires interrupting a background process.

        Uses the sentinel LLM (gemma3:1b) to intelligently decide when to interrupt.

        Args:
            process_info: Info about the running background process
            user_input: New user input/command

        Returns:
            Dict with:
            - should_interrupt: bool
            - reason: str
            - urgency: str ("low", "medium", "high")
        """

        # Extract process details
        process_id = process_info.get('process_id', 'unknown')
        description = process_info.get('description', 'unknown task')
        status = process_info.get('status', 'unknown')
        progress = process_info.get('progress_percent', 0)
        latest_update = process_info.get('latest_update', {})
        latest_message = latest_update.get('message', 'no update') if latest_update else 'no update'

        prompt = f"""A background process is currently running:

Process ID: {process_id}
Task: {description}
Status: {status}
Progress: {progress}%
Latest update: {latest_message}

User says: "{user_input}"

Should we interrupt the background process to handle this user input?

Decision Rules:
1. User asking ABOUT the background process (status, progress, etc.) → DON'T interrupt, just answer from status
2. User starting a NEW unrelated task → DON'T interrupt, warn about background process or queue
3. User requesting CANCELLATION (stop, cancel, abort, etc.) → INTERRUPT, cancel the process
4. User providing CORRECTIONS or MODIFICATIONS to current task → INTERRUPT, need to restart with new requirements
5. User saying WAIT or similar → DON'T interrupt, they acknowledge background process
6. Emergency commands (exit, shutdown, etc.) → INTERRUPT immediately

Format your response:
DECISION: <CONTINUE|INTERRUPT>
URGENCY: <LOW|MEDIUM|HIGH>
REASON: <brief explanation in one sentence>
"""

        try:
            response = self.client.generate(
                model=self.sentinel_model,  # gemma3:1b - very fast
                prompt=prompt,
                temperature=0.1,
                max_tokens=150
            ).strip()

            # Parse response
            import re
            decision_match = re.search(r'DECISION:\s*(CONTINUE|INTERRUPT)', response, re.IGNORECASE)
            urgency_match = re.search(r'URGENCY:\s*(LOW|MEDIUM|HIGH)', response, re.IGNORECASE)
            reason_match = re.search(r'REASON:\s*(.+)', response, re.DOTALL)

            decision = decision_match.group(1).upper() if decision_match else "CONTINUE"
            urgency = urgency_match.group(1).upper() if urgency_match else "LOW"
            reason = reason_match.group(1).strip() if reason_match else "Unknown reason"

            # Clean up reason (take first line only)
            reason = reason.split('\n')[0].strip()

            should_interrupt = (decision == "INTERRUPT")

            logger.info(
                f"Interrupt decision for process {process_id}: "
                f"{'INTERRUPT' if should_interrupt else 'CONTINUE'} "
                f"(urgency: {urgency}) - {reason}"
            )

            return {
                "should_interrupt": should_interrupt,
                "reason": reason,
                "urgency": urgency.lower(),
                "decision": decision.lower()
            }

        except Exception as e:
            logger.error(f"Error in interrupt decision: {e}")
            # Default to not interrupting on error
            return {
                "should_interrupt": False,
                "reason": f"Error making decision: {str(e)}",
                "urgency": "low",
                "decision": "continue"
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

