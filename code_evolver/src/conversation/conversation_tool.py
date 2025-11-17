"""
Conversation Tool

Main coordinator for the conversation system.
Orchestrates all conversation components for smart, context-aware conversations.
"""
import logging
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from .conversation_storage import ConversationStorage
from .context_manager import ContextMemoryManager
from .summarizer import ConversationSummarizer
from .intent_detector import ConversationIntentDetector
from .embedder import ConversationEmbedder
from .smart_orchestrator import SmartConversationOrchestrator

logger = logging.getLogger(__name__)


class ConversationTool:
    """
    Main conversation tool coordinator.

    Features:
    - Multi-chat context memory
    - Auto-summarization with context window awareness
    - Volatile Qdrant storage
    - Semantic search for related conversations
    - Performance tracking
    - Smart orchestration with dynamic tool calling and workflow generation
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        conversation_model: str = "gemma3:1b"
    ):
        """
        Initialize conversation tool.

        Args:
            config: Configuration dict (optional)
            conversation_model: Model for conversation management (summarization, intent detection)
        """
        config = config or {}

        # Extract config
        qdrant_url = config.get("qdrant_url", "http://localhost:6333")
        embedding_model = config.get("embedding_model", "nomic-embed-text")
        embedding_endpoint = config.get("embedding_endpoint", "http://localhost:11434")
        ollama_endpoint = config.get("ollama_endpoint", "http://localhost:11434")
        vector_size = config.get("vector_size", 768)

        # Initialize components
        self.storage = ConversationStorage(
            qdrant_url=qdrant_url,
            embedding_model=embedding_model,
            embedding_endpoint=embedding_endpoint,
            vector_size=vector_size
        )

        self.context_manager = ContextMemoryManager(model_name=conversation_model)

        self.summarizer = ConversationSummarizer(
            model_name=conversation_model,
            ollama_endpoint=ollama_endpoint
        )

        self.intent_detector = ConversationIntentDetector(
            model_name=conversation_model,
            ollama_endpoint=ollama_endpoint
        )

        self.embedder = ConversationEmbedder(
            qdrant_url=qdrant_url,
            embedding_model=embedding_model,
            embedding_endpoint=embedding_endpoint,
            vector_size=vector_size
        )

        # Initialize smart orchestrator for tool calling and workflow generation
        self.orchestrator = SmartConversationOrchestrator(
            model_name=conversation_model,
            ollama_endpoint=ollama_endpoint,
            tools_manager=config.get("tools_manager"),
            workflow_engine=config.get("workflow_engine")
        )

        # Track active conversation
        self.current_conversation_id: Optional[str] = None
        self.current_summary: Optional[str] = None

        logger.info(f"Conversation tool initialized with model: {conversation_model}")

    def start_conversation(self, topic: str = "general") -> Dict[str, Any]:
        """
        Start a new conversation.

        Args:
            topic: Conversation topic

        Returns:
            Dict with conversation info
        """
        # End current conversation if any
        if self.current_conversation_id:
            logger.info("Ending previous conversation before starting new one")
            self.end_conversation()

        # Create new conversation
        conversation_id = self.storage.create_conversation(topic=topic)
        self.current_conversation_id = conversation_id
        self.current_summary = None

        logger.info(f"Started conversation '{topic}' (ID: {conversation_id})")

        return {
            "conversation_id": conversation_id,
            "topic": topic,
            "started_at": datetime.now().isoformat(),
            "status": "active"
        }

    def add_user_message(self, content: str) -> Dict[str, Any]:
        """
        Add a user message to the conversation.

        Args:
            content: Message content

        Returns:
            Dict with message info
        """
        if not self.current_conversation_id:
            raise ValueError("No active conversation. Start a conversation first.")

        # Add message to storage
        message_id = self.storage.add_message(
            conversation_id=self.current_conversation_id,
            role="user",
            content=content
        )

        return {
            "message_id": message_id,
            "conversation_id": self.current_conversation_id,
            "role": "user",
            "timestamp": datetime.now().isoformat()
        }

    def prepare_context_for_response(
        self,
        user_message: str,
        response_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare optimized context for generating a response.

        This is the core method that:
        1. Retrieves conversation history
        2. Gets related context from past conversations
        3. Summarizes if needed
        4. Optimizes context for the model's window

        Args:
            user_message: Latest user message
            response_model: Model that will generate the response (for context sizing)

        Returns:
            Dict with optimized context:
            - summary: Conversation summary
            - related_context: Related conversation snippets
            - messages: Recent messages
            - metadata: Context metadata
        """
        if not self.current_conversation_id:
            raise ValueError("No active conversation")

        start_time = time.time()

        # Update context manager for response model if specified
        if response_model:
            self.context_manager = ContextMemoryManager(model_name=response_model)

        # Get conversation messages
        messages = self.storage.get_conversation_messages(self.current_conversation_id)

        # Check if we should summarize
        if self.context_manager.should_summarize(messages):
            logger.info("Conversation length threshold reached, summarizing...")

            # Get messages to summarize and keep
            to_summarize, to_keep = self.context_manager.get_messages_for_summary(messages)

            # Summarize
            summary_result = self.summarizer.summarize_with_context(
                messages=to_summarize,
                keep_recent=len(to_keep),
                previous_summary=self.current_summary,
                topic=self.storage.conversation_metadata.get(
                    self.current_conversation_id, {}
                ).get("topic")
            )

            self.current_summary = summary_result["summary"]
            messages = to_keep  # Use only recent messages
        else:
            # No summarization needed
            pass

        # Get related context from past conversations
        related_context = self.embedder.get_related_context(
            query=user_message,
            max_snippets=3,
            exclude_conversation_id=self.current_conversation_id
        )

        # Optimize context for model's window
        optimized = self.context_manager.optimize_context(
            messages=messages,
            summary=self.current_summary,
            related_context=related_context
        )

        elapsed = time.time() - start_time

        logger.info(
            f"Context prepared in {elapsed:.2f}s: "
            f"{optimized['token_count']}/{optimized['available_tokens']} tokens, "
            f"truncated={optimized['truncated']}"
        )

        return {
            **optimized,
            "metadata": {
                "preparation_time": elapsed,
                "conversation_id": self.current_conversation_id,
                "context_info": self.context_manager.get_context_info()
            }
        }

    def add_assistant_message(
        self,
        content: str,
        performance_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add an assistant message to the conversation.

        Args:
            content: Message content
            performance_data: Optional performance metrics

        Returns:
            Dict with message info
        """
        if not self.current_conversation_id:
            raise ValueError("No active conversation")

        # Add message to storage
        message_id = self.storage.add_message(
            conversation_id=self.current_conversation_id,
            role="assistant",
            content=content,
            performance_data=performance_data
        )

        return {
            "message_id": message_id,
            "conversation_id": self.current_conversation_id,
            "role": "assistant",
            "timestamp": datetime.now().isoformat()
        }

    def end_conversation(
        self,
        topic: Optional[str] = None,
        save_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        End the current or specified conversation.

        Args:
            topic: Optional topic to end (if None, ends current conversation)
            save_metadata: Whether to save conversation metadata for future retrieval

        Returns:
            Dict with end conversation info
        """
        # Determine conversation ID
        if topic:
            conversation_id = self.storage.get_conversation_by_topic(topic)
            if not conversation_id:
                raise ValueError(f"No conversation found with topic: {topic}")
        else:
            conversation_id = self.current_conversation_id
            if not conversation_id:
                raise ValueError("No active conversation to end")

        # Get conversation messages and metadata
        messages = self.storage.get_conversation_messages(conversation_id)
        metadata = self.storage.get_conversation_metadata(conversation_id)

        result = {
            "conversation_id": conversation_id,
            "topic": metadata.get("topic") if metadata else "Unknown",
            "message_count": len(messages),
            "ended_at": datetime.now().isoformat()
        }

        # Save metadata if requested
        if save_metadata and messages:
            logger.info("Saving conversation metadata for future retrieval...")

            # Generate final summary
            summary_result = self.summarizer.summarize_messages(
                messages=messages,
                topic=metadata.get("topic") if metadata else None
            )

            # Extract key points
            key_points_result = self.summarizer.extract_key_points(messages)

            # Store metadata
            self.embedder.store_conversation_metadata(
                conversation_id=conversation_id,
                topic=metadata.get("topic", "Unknown") if metadata else "Unknown",
                summary=summary_result["summary"],
                key_points=key_points_result["key_points"],
                metadata={
                    "message_count": len(messages),
                    "created_at": metadata.get("created_at") if metadata else None,
                    "ended_at": datetime.now().isoformat(),
                    "total_response_time": metadata.get("total_response_time", 0.0) if metadata else 0.0
                }
            )

            result["summary"] = summary_result["summary"]
            result["key_points"] = key_points_result["key_points"]

        # End conversation and delete collection
        self.storage.end_conversation(conversation_id, delete_collection=True)

        # Clear current conversation if it's the one we ended
        if conversation_id == self.current_conversation_id:
            self.current_conversation_id = None
            self.current_summary = None

        logger.info(f"Ended conversation {conversation_id}")

        return result

    def detect_conversation_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Detect if user wants to start a conversation.

        Args:
            user_input: User input

        Returns:
            Intent detection result
        """
        return self.intent_detector.detect_intent(user_input)

    def get_conversation_status(self) -> Dict[str, Any]:
        """
        Get current conversation status.

        Returns:
            Status dict
        """
        if not self.current_conversation_id:
            return {
                "active": False,
                "conversation_id": None
            }

        metadata = self.storage.get_conversation_metadata(self.current_conversation_id)
        messages = self.storage.get_conversation_messages(self.current_conversation_id)

        return {
            "active": True,
            "conversation_id": self.current_conversation_id,
            "topic": metadata.get("topic") if metadata else "Unknown",
            "message_count": len(messages),
            "has_summary": self.current_summary is not None,
            "metadata": metadata
        }

    def list_active_conversations(self) -> List[Dict[str, Any]]:
        """
        List all active conversations.

        Returns:
            List of active conversation info
        """
        active = self.storage.get_active_conversations()

        result = []
        for topic, conversation_id in active.items():
            metadata = self.storage.get_conversation_metadata(conversation_id)
            result.append({
                "conversation_id": conversation_id,
                "topic": topic,
                "metadata": metadata
            })

        return result

    @staticmethod
    def create_from_config_file(
        config_path: str,
        conversation_model: str = "gemma3:1b"
    ) -> "ConversationTool":
        """
        Create conversation tool from config file.

        Args:
            config_path: Path to YAML config file
            conversation_model: Model for conversation management

        Returns:
            ConversationTool instance
        """
        import yaml

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Extract conversation-specific config
        conversation_config = config.get("conversation", {})

        # Merge with qdrant and embedding config
        qdrant_config = config.get("rag_memory", {})
        llm_config = config.get("llm", {})
        embedding_config = llm_config.get("embedding", {})

        combined_config = {
            **conversation_config,
            "qdrant_url": qdrant_config.get("qdrant_url", "http://localhost:6333"),
            "embedding_model": embedding_config.get("default", "nomic-embed-text"),
            "embedding_endpoint": llm_config.get("backends", {}).get("ollama", {}).get("base_url", "http://localhost:11434"),
            "ollama_endpoint": llm_config.get("backends", {}).get("ollama", {}).get("base_url", "http://localhost:11434"),
        }

        return ConversationTool(config=combined_config, conversation_model=conversation_model)
