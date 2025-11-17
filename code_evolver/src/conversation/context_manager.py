"""
Context Memory Manager

Manages conversation context with size optimization based on model context window.
Ensures optimal balance between context richness and response speed.
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ContextWindow:
    """Model context window configuration."""
    model_name: str
    context_window: int  # Total context window size
    reserved_for_response: int  # Tokens reserved for model response
    reserved_for_system: int  # Tokens reserved for system prompts

    @property
    def available_for_context(self) -> int:
        """Calculate available tokens for conversation context."""
        return self.context_window - self.reserved_for_response - self.reserved_for_system


class ContextMemoryManager:
    """
    Manages conversation context with size optimization.

    Features:
    - Dynamic context window management based on model
    - Smart truncation to fit context limits
    - Message prioritization (keep recent + important)
    - Token estimation for context sizing
    """

    # Default context windows for common models
    DEFAULT_WINDOWS = {
        "gemma3:1b": ContextWindow("gemma3:1b", 8192, 2048, 512),
        "gemma3:4b": ContextWindow("gemma3:4b", 8192, 2048, 512),
        "llama3": ContextWindow("llama3", 8192, 2048, 512),
        "qwen2.5-coder:3b": ContextWindow("qwen2.5-coder:3b", 32768, 4096, 512),
        "qwen2.5-coder:14b": ContextWindow("qwen2.5-coder:14b", 32768, 4096, 512),
        "deepseek-coder-v2:16b": ContextWindow("deepseek-coder-v2:16b", 131072, 8192, 1024),
        "claude-3-haiku-20240307": ContextWindow("claude-3-haiku-20240307", 200000, 4096, 1024),
        "claude-3-5-sonnet-20241022": ContextWindow("claude-3-5-sonnet-20241022", 200000, 8192, 1024),
    }

    def __init__(self, model_name: str = "gemma3:1b"):
        """
        Initialize context memory manager.

        Args:
            model_name: Name of the model being used
        """
        self.model_name = model_name
        self.context_window = self._get_context_window(model_name)

        logger.info(
            f"Context manager initialized for {model_name}: "
            f"{self.context_window.available_for_context} tokens available for context"
        )

    def _get_context_window(self, model_name: str) -> ContextWindow:
        """
        Get context window configuration for model.

        Args:
            model_name: Model name

        Returns:
            ContextWindow configuration
        """
        # Try exact match
        if model_name in self.DEFAULT_WINDOWS:
            return self.DEFAULT_WINDOWS[model_name]

        # Try partial match (e.g., "llama3:8b" -> "llama3")
        for key in self.DEFAULT_WINDOWS:
            if model_name.startswith(key.split(":")[0]):
                return self.DEFAULT_WINDOWS[key]

        # Default fallback
        logger.warning(f"Unknown model {model_name}, using default context window")
        return ContextWindow(model_name, 8192, 2048, 512)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses simple heuristic: ~4 characters per token (conservative estimate).

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Conservative estimate: 4 chars per token
        # This ensures we don't exceed limits
        return len(text) // 4

    def estimate_message_tokens(self, message: Dict[str, Any]) -> int:
        """
        Estimate tokens for a message.

        Args:
            message: Message dict with 'role' and 'content'

        Returns:
            Estimated token count
        """
        content = message.get("content", "")
        role = message.get("role", "")

        # Add overhead for role and formatting
        overhead = 10
        return self.estimate_tokens(content) + self.estimate_tokens(role) + overhead

    def optimize_context(
        self,
        messages: List[Dict[str, Any]],
        summary: Optional[str] = None,
        related_context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Optimize context to fit within model's context window.

        Strategy:
        1. Always include summary (if provided)
        2. Always include related context (if provided)
        3. Include as many recent messages as possible
        4. Truncate older messages if needed

        Args:
            messages: List of conversation messages
            summary: Optional conversation summary
            related_context: Optional related conversation snippets

        Returns:
            Optimized context dict with:
            - summary: Conversation summary
            - related_context: Related conversation snippets
            - messages: Optimized message list
            - truncated: Whether messages were truncated
            - token_count: Estimated token count
        """
        available_tokens = self.context_window.available_for_context
        used_tokens = 0

        # Include summary
        summary_tokens = 0
        if summary:
            summary_tokens = self.estimate_tokens(summary) + 20  # overhead
            used_tokens += summary_tokens

        # Include related context
        related_tokens = 0
        if related_context:
            related_text = "\n\n".join(related_context)
            related_tokens = self.estimate_tokens(related_text) + 50  # overhead
            used_tokens += related_tokens

        # Calculate tokens available for messages
        available_for_messages = available_tokens - used_tokens

        # Optimize messages (keep most recent that fit)
        optimized_messages = []
        messages_tokens = 0
        truncated = False

        # Start from most recent and work backwards
        for message in reversed(messages):
            message_tokens = self.estimate_message_tokens(message)

            if messages_tokens + message_tokens <= available_for_messages:
                optimized_messages.insert(0, message)
                messages_tokens += message_tokens
            else:
                # Can't fit more messages
                truncated = True
                break

        # If we couldn't fit any messages but have room, try to fit at least one
        if not optimized_messages and messages and available_for_messages > 100:
            # Truncate the most recent message to fit
            last_message = messages[-1].copy()
            max_content_tokens = available_for_messages - 20  # overhead

            # Estimate how much content we can include
            max_chars = max_content_tokens * 4
            content = last_message.get("content", "")

            if len(content) > max_chars:
                last_message["content"] = content[:max_chars] + "... [truncated]"
                truncated = True

            optimized_messages = [last_message]
            messages_tokens = self.estimate_message_tokens(last_message)

        total_tokens = used_tokens + messages_tokens

        logger.debug(
            f"Context optimization: "
            f"total={total_tokens}, summary={summary_tokens}, "
            f"related={related_tokens}, messages={messages_tokens}, "
            f"truncated={truncated}"
        )

        return {
            "summary": summary,
            "related_context": related_context,
            "messages": optimized_messages,
            "truncated": truncated,
            "token_count": total_tokens,
            "available_tokens": available_tokens
        }

    def should_summarize(
        self,
        messages: List[Dict[str, Any]],
        threshold_ratio: float = 0.7
    ) -> bool:
        """
        Determine if conversation should be summarized.

        Args:
            messages: List of messages
            threshold_ratio: Ratio of context window to trigger summarization

        Returns:
            True if summarization is recommended
        """
        total_tokens = sum(self.estimate_message_tokens(msg) for msg in messages)
        threshold = self.context_window.available_for_context * threshold_ratio

        return total_tokens >= threshold

    def get_messages_for_summary(
        self,
        messages: List[Dict[str, Any]],
        keep_recent: int = 3
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Split messages into those to summarize and those to keep.

        Args:
            messages: All messages
            keep_recent: Number of recent messages to keep unsummarized

        Returns:
            Tuple of (messages_to_summarize, messages_to_keep)
        """
        if len(messages) <= keep_recent:
            return [], messages

        return messages[:-keep_recent], messages[-keep_recent:]

    def get_context_info(self) -> Dict[str, Any]:
        """
        Get information about current context configuration.

        Returns:
            Context info dict
        """
        return {
            "model_name": self.model_name,
            "total_context_window": self.context_window.context_window,
            "available_for_context": self.context_window.available_for_context,
            "reserved_for_response": self.context_window.reserved_for_response,
            "reserved_for_system": self.context_window.reserved_for_system
        }
