"""
Ask User Tool for Code Evolver.
Interactive CLI input with LLM fallback for non-interactive mode.
"""
import json
import logging
import sys
import select
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class AskUserTool:
    """
    Interactive user input tool with LLM fallback.

    Features:
    - Interactive CLI prompts when terminal is available
    - LLM fallback for non-interactive mode
    - Multiple question types (text, yes/no, confirm, choice)
    - Timeout handling
    - Default answers
    - Context-aware LLM decisions
    """

    def __init__(
        self,
        timeout_seconds: int = 60,
        default_to_llm: bool = True,
        ollama_client: Optional[Any] = None,
        config_manager: Optional[Any] = None
    ):
        """
        Initialize Ask User tool.

        Args:
            timeout_seconds: Input timeout in seconds
            default_to_llm: Use LLM for non-interactive by default
            ollama_client: Ollama client for LLM fallback
            config_manager: Config manager for settings
        """
        self.timeout = timeout_seconds
        self.default_to_llm = default_to_llm
        self.ollama_client = ollama_client
        self.config_manager = config_manager

        logger.info(f"AskUserTool initialized (timeout={timeout_seconds}s, llm_fallback={default_to_llm})")

    def is_interactive(self) -> bool:
        """
        Check if running in interactive mode.

        Returns:
            True if stdin and stdout are TTY (terminal)
        """
        return sys.stdin.isatty() and sys.stdout.isatty()

    def _prompt_user(
        self,
        question: str,
        question_type: str = "text",
        choices: Optional[List[str]] = None,
        default_answer: Optional[str] = None
    ) -> Optional[str]:
        """
        Prompt user for input with timeout.

        Args:
            question: Question to ask
            question_type: Type of question (text, yes_no, confirm, choice)
            choices: Available choices (for choice type)
            default_answer: Default answer

        Returns:
            User's answer or None if timeout
        """
        try:
            # Format question based on type
            if question_type == "yes_no":
                prompt = f"{question} [yes/no]"
                if default_answer:
                    prompt += f" (default: {default_answer})"
                prompt += ": "
            elif question_type == "choice" and choices:
                prompt = f"{question}\n"
                for i, choice in enumerate(choices, 1):
                    prompt += f"  {i}. {choice}\n"
                prompt += "Enter choice number or name"
                if default_answer:
                    prompt += f" (default: {default_answer})"
                prompt += ": "
            elif question_type == "confirm":
                prompt = f"{question}: "
            else:  # text
                prompt = f"{question}"
                if default_answer:
                    prompt += f" (default: {default_answer})"
                prompt += ": "

            # Display prompt
            print(f"\n[?] {prompt}", end="", flush=True)

            # Wait for input with timeout
            if sys.platform == "win32":
                # Windows doesn't support select on stdin
                # Use simple input() with no timeout
                answer = input().strip()
            else:
                # Unix-like systems can use select for timeout
                ready, _, _ = select.select([sys.stdin], [], [], self.timeout)
                if ready:
                    answer = sys.stdin.readline().strip()
                else:
                    print(f"\n[!] Timeout after {self.timeout}s")
                    return None

            # Process answer
            if not answer and default_answer:
                answer = default_answer
                print(f"[i] Using default: {default_answer}")

            # Validate answer based on type
            if question_type == "yes_no":
                answer = answer.lower()
                if answer not in ["yes", "no", "y", "n"]:
                    print(f"[!] Invalid answer. Please enter yes or no.")
                    return None
                answer = "yes" if answer in ["yes", "y"] else "no"

            elif question_type == "choice" and choices:
                # Try to match by number or name
                if answer.isdigit():
                    idx = int(answer) - 1
                    if 0 <= idx < len(choices):
                        answer = choices[idx]
                    else:
                        print(f"[!] Invalid choice number.")
                        return None
                elif answer not in choices:
                    print(f"[!] Invalid choice. Please select from: {', '.join(choices)}")
                    return None

            return answer

        except KeyboardInterrupt:
            print("\n[!] Cancelled by user")
            return None
        except Exception as e:
            logger.error(f"Error prompting user: {e}")
            return None

    def _ask_llm(
        self,
        question: str,
        question_type: str = "text",
        choices: Optional[List[str]] = None,
        context: Optional[str] = None,
        default_answer: Optional[str] = None
    ) -> Optional[str]:
        """
        Ask LLM to answer question based on context.

        Args:
            question: Question to answer
            question_type: Type of question
            choices: Available choices
            context: Additional context
            default_answer: Default answer

        Returns:
            LLM's answer
        """
        if not self.ollama_client:
            logger.warning("No Ollama client available for LLM fallback")
            return default_answer

        try:
            # Build prompt for LLM
            prompt = f"""You are helping make a decision for a workflow that cannot ask the user interactively.

Question: {question}
Question Type: {question_type}
"""

            if choices:
                prompt += f"\nAvailable Choices: {', '.join(choices)}"

            if context:
                prompt += f"\nContext: {context}"

            if default_answer:
                prompt += f"\nDefault Answer: {default_answer}"

            prompt += "\n\nProvide ONLY the answer, no explanation. "

            if question_type == "yes_no":
                prompt += "Answer with 'yes' or 'no'."
            elif question_type == "choice" and choices:
                prompt += f"Answer with one of: {', '.join(choices)}"
            elif question_type == "confirm":
                prompt += "Answer with the exact confirmation text or 'no'."

            # Get LLM response
            logger.debug(f"Asking LLM: {question}")

            response = self.ollama_client.generate(
                model=self._get_llm_model(),
                prompt=prompt,
                options={
                    "temperature": 0.3,  # Low temperature for consistent decisions
                    "max_tokens": 100
                }
            )

            answer = response.get("response", "").strip()

            # Validate answer
            if question_type == "yes_no":
                answer = answer.lower()
                if answer not in ["yes", "no"]:
                    logger.warning(f"LLM gave invalid yes/no answer: {answer}")
                    return default_answer or "no"

            elif question_type == "choice" and choices:
                if answer not in choices:
                    logger.warning(f"LLM gave invalid choice: {answer}")
                    return default_answer or choices[0]

            logger.info(f"LLM answered: {answer}")
            return answer

        except Exception as e:
            logger.error(f"Error asking LLM: {e}")
            return default_answer

    def _get_llm_model(self) -> str:
        """
        Get LLM model to use for decisions.

        Returns:
            Model name (uses fast model for quick decisions)
        """
        if self.config_manager:
            try:
                # Use 'veryfast' tier for quick decisions
                llm_config = self.config_manager.get("llm", {})
                defaults = llm_config.get("defaults", {})
                model_id = defaults.get("veryfast", "gemma3:1b")

                # Get actual model name from registry
                models = llm_config.get("models", {})
                if model_id in models:
                    return models[model_id].get("name", model_id)

                return model_id
            except Exception as e:
                logger.error(f"Error getting LLM model from config: {e}")

        # Fallback to default
        return "gemma3:1b"

    def ask(
        self,
        question: str,
        question_type: str = "text",
        choices: Optional[List[str]] = None,
        default_answer: Optional[str] = None,
        context: Optional[str] = None,
        allow_llm_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Ask user a question (or LLM if non-interactive).

        Args:
            question: Question to ask
            question_type: Type of question
            choices: Available choices
            default_answer: Default answer
            context: Context for LLM
            allow_llm_fallback: Allow LLM to answer

        Returns:
            Result dictionary
        """
        is_interactive_mode = self.is_interactive()

        # Try interactive mode first
        if is_interactive_mode:
            logger.info(f"Asking user (interactive): {question}")
            answer = self._prompt_user(question, question_type, choices, default_answer)

            if answer is not None:
                return {
                    "success": True,
                    "answer": answer,
                    "answered_by": "user",
                    "is_interactive": True
                }

        # Fall back to LLM or default
        if allow_llm_fallback and self.default_to_llm:
            logger.info(f"Asking LLM (non-interactive or timeout): {question}")
            answer = self._ask_llm(question, question_type, choices, context, default_answer)

            if answer is not None:
                return {
                    "success": True,
                    "answer": answer,
                    "answered_by": "llm",
                    "is_interactive": False
                }

        # Last resort: use default
        if default_answer:
            logger.info(f"Using default answer: {default_answer}")
            return {
                "success": True,
                "answer": default_answer,
                "answered_by": "default",
                "is_interactive": is_interactive_mode
            }

        # No answer available
        return {
            "success": False,
            "error": "No answer available (no user input, LLM failed, and no default)",
            "is_interactive": is_interactive_mode
        }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute ask user action.

        Args:
            params: Action parameters

        Returns:
            Result dictionary
        """
        question = params.get("question")
        if not question:
            return {
                "success": False,
                "error": "No question provided"
            }

        question_type = params.get("question_type", "text")
        choices = params.get("choices")
        default_answer = params.get("default_answer")
        context = params.get("context")
        allow_llm_fallback = params.get("allow_llm_fallback", True)

        return self.ask(
            question=question,
            question_type=question_type,
            choices=choices,
            default_answer=default_answer,
            context=context,
            allow_llm_fallback=allow_llm_fallback
        )
