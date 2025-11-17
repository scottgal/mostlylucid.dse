"""
Conversation Summarizer

Auto-summarizes conversations using fast LLM (gemma3:1b) with context window awareness.
Optimizes for response speed while maintaining accuracy.
"""
import logging
from typing import List, Dict, Any, Optional
import requests
import time

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """
    Summarizes conversations using fast LLM.

    Features:
    - Uses gemma3:1b for very fast summarization
    - Context-aware summarization based on conversation length
    - Incremental summarization for long conversations
    - Performance tracking
    """

    def __init__(
        self,
        model_name: str = "gemma3:1b",
        ollama_endpoint: str = "http://localhost:11434",
        max_summary_length: int = 500
    ):
        """
        Initialize conversation summarizer.

        Args:
            model_name: LLM model to use for summarization (default: gemma3:1b for speed)
            ollama_endpoint: Ollama API endpoint
            max_summary_length: Maximum tokens in summary
        """
        self.model_name = model_name
        self.ollama_endpoint = ollama_endpoint
        self.max_summary_length = max_summary_length

        logger.info(f"Summarizer initialized with model: {model_name}")

    def _call_llm(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.3
    ) -> tuple[str, float]:
        """
        Call LLM for summarization.

        Args:
            prompt: Prompt text
            max_tokens: Maximum tokens in response
            temperature: LLM temperature (lower for more focused summaries)

        Returns:
            Tuple of (response_text, time_taken)
        """
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.ollama_endpoint}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens or self.max_summary_length
                    }
                },
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            text = result.get("response", "").strip()
            elapsed = time.time() - start_time

            logger.debug(f"LLM call completed in {elapsed:.2f}s")
            return text, elapsed

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            elapsed = time.time() - start_time
            return f"[Summarization failed: {e}]", elapsed

    def summarize_messages(
        self,
        messages: List[Dict[str, Any]],
        previous_summary: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Summarize a list of messages.

        Args:
            messages: List of messages to summarize
            previous_summary: Previous summary to build upon (for incremental summarization)
            topic: Optional conversation topic

        Returns:
            Dict with:
            - summary: Generated summary
            - time_taken: Time to generate summary
            - message_count: Number of messages summarized
        """
        if not messages:
            return {
                "summary": previous_summary or "",
                "time_taken": 0.0,
                "message_count": 0
            }

        # Build conversation text
        conversation_text = self._format_messages_for_summary(messages)

        # Build prompt
        if previous_summary:
            prompt = f"""You are summarizing a conversation. Here is the previous summary:

{previous_summary}

Now summarize the following new messages and combine with the previous summary.
Be concise and focus on key points, decisions, and important details.

New messages:
{conversation_text}

Provide a comprehensive but concise summary (max {self.max_summary_length} words):"""
        else:
            topic_context = f" about {topic}" if topic else ""
            prompt = f"""Summarize the following conversation{topic_context}.
Be concise and focus on key points, decisions, and important details.

Conversation:
{conversation_text}

Provide a concise summary (max {self.max_summary_length} words):"""

        # Generate summary
        summary, time_taken = self._call_llm(prompt, max_tokens=self.max_summary_length)

        return {
            "summary": summary,
            "time_taken": time_taken,
            "message_count": len(messages)
        }

    def _format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages for summarization.

        Args:
            messages: List of messages

        Returns:
            Formatted conversation text
        """
        formatted = []

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            # Format: [USER/ASSISTANT] message
            role_label = role.upper()
            formatted.append(f"[{role_label}] {content}")

        return "\n".join(formatted)

    def summarize_with_context(
        self,
        messages: List[Dict[str, Any]],
        keep_recent: int = 3,
        previous_summary: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Summarize conversation while keeping recent messages unsummarized.

        This enables a sliding window approach where:
        - Old messages are summarized
        - Recent messages are kept in full
        - Context window is optimized

        Args:
            messages: All conversation messages
            keep_recent: Number of recent messages to keep unsummarized
            previous_summary: Previous summary
            topic: Conversation topic

        Returns:
            Dict with:
            - summary: Summary of older messages
            - recent_messages: Recent messages to keep
            - time_taken: Time to generate summary
            - total_messages: Total number of messages
            - summarized_count: Number of messages summarized
        """
        if len(messages) <= keep_recent:
            # No need to summarize
            return {
                "summary": previous_summary or "",
                "recent_messages": messages,
                "time_taken": 0.0,
                "total_messages": len(messages),
                "summarized_count": 0
            }

        # Split messages
        messages_to_summarize = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        # Summarize older messages
        result = self.summarize_messages(
            messages_to_summarize,
            previous_summary=previous_summary,
            topic=topic
        )

        return {
            "summary": result["summary"],
            "recent_messages": recent_messages,
            "time_taken": result["time_taken"],
            "total_messages": len(messages),
            "summarized_count": len(messages_to_summarize)
        }

    def extract_key_points(
        self,
        messages: List[Dict[str, Any]],
        max_points: int = 5
    ) -> Dict[str, Any]:
        """
        Extract key points from conversation.

        Args:
            messages: Conversation messages
            max_points: Maximum number of key points

        Returns:
            Dict with:
            - key_points: List of key points
            - time_taken: Time to extract
        """
        if not messages:
            return {
                "key_points": [],
                "time_taken": 0.0
            }

        conversation_text = self._format_messages_for_summary(messages)

        prompt = f"""Extract the {max_points} most important key points from this conversation.
Format each point as a short bullet point.

Conversation:
{conversation_text}

Key points (one per line, start each with "-"):"""

        response, time_taken = self._call_llm(prompt, max_tokens=200)

        # Parse key points
        key_points = []
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                key_points.append(line.lstrip("-*").strip())

        return {
            "key_points": key_points[:max_points],
            "time_taken": time_taken
        }

    def generate_conversation_title(
        self,
        messages: List[Dict[str, Any]],
        current_topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a descriptive title for the conversation.

        Args:
            messages: Conversation messages
            current_topic: Current topic name

        Returns:
            Dict with:
            - title: Generated title
            - time_taken: Time to generate
        """
        if not messages:
            return {
                "title": current_topic or "Conversation",
                "time_taken": 0.0
            }

        # Use first few messages to determine topic
        sample_messages = messages[:5]
        conversation_text = self._format_messages_for_summary(sample_messages)

        prompt = f"""Based on the following conversation start, generate a short descriptive title (3-5 words maximum).

Conversation:
{conversation_text}

Title:"""

        title, time_taken = self._call_llm(prompt, max_tokens=20, temperature=0.5)

        # Clean up title
        title = title.strip().strip('"\'')

        return {
            "title": title or current_topic or "Conversation",
            "time_taken": time_taken
        }
