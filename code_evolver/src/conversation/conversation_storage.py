"""
Conversation Storage Manager

Manages volatile Qdrant collections for conversations.
Collections are created per conversation and can be deleted when conversation ends.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import requests

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConversationStorage:
    """
    Manages volatile Qdrant storage for conversations.

    Each conversation gets its own collection in Qdrant with:
    - Message text and embeddings
    - Role (user/assistant)
    - Timestamp
    - Performance metrics (response time, tokens, etc.)
    - Conversation ID (GUID)
    """

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "nomic-embed-text",
        embedding_endpoint: str = "http://localhost:11434",
        vector_size: int = 768
    ):
        """
        Initialize conversation storage.

        Args:
            qdrant_url: URL for Qdrant server
            embedding_model: Model to use for embeddings
            embedding_endpoint: Endpoint for embedding generation
            vector_size: Dimension of embedding vectors
        """
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client required. Install with: pip install qdrant-client")

        self.qdrant_url = qdrant_url
        self.embedding_model = embedding_model
        self.embedding_endpoint = embedding_endpoint
        self.vector_size = vector_size

        # Connect to Qdrant
        self.qdrant = QdrantClient(url=qdrant_url)
        logger.info(f"Connected to Qdrant at {qdrant_url}")

        # Track active conversations
        self.active_conversations: Dict[str, str] = {}  # topic -> conversation_id
        self.conversation_metadata: Dict[str, Dict[str, Any]] = {}  # conversation_id -> metadata

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Ollama.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = requests.post(
                f"{self.embedding_endpoint}/api/embed",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=90
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]

            if len(embedding) != self.vector_size:
                logger.warning(
                    f"Embedding size mismatch: expected {self.vector_size}, got {len(embedding)}"
                )

            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self.vector_size

    def _get_collection_name(self, conversation_id: str) -> str:
        """Get Qdrant collection name for conversation."""
        return f"conversation_{conversation_id}"

    def create_conversation(
        self,
        topic: str = "general",
        preferred_tools: Optional[List[str]] = None
    ) -> str:
        """
        Create a new conversation collection.

        Args:
            topic: Topic/name of the conversation
            preferred_tools: Optional list of preferred tool names to prioritize

        Returns:
            Conversation ID (GUID)
        """
        conversation_id = str(uuid.uuid4())
        collection_name = self._get_collection_name(conversation_id)

        # Create Qdrant collection
        try:
            self.qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created conversation collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

        # Track conversation
        self.active_conversations[topic] = conversation_id
        self.conversation_metadata[conversation_id] = {
            "topic": topic,
            "created_at": datetime.now().isoformat(),
            "message_count": 0,
            "total_response_time": 0.0,
            "collection_name": collection_name,
            "preferred_tools": preferred_tools or []
        }

        logger.info(f"Created conversation '{topic}' with ID {conversation_id}")
        if preferred_tools:
            logger.info(f"Preferred tools for this conversation: {', '.join(preferred_tools)}")
        return conversation_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        performance_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to the conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant)
            content: Message content
            performance_data: Optional performance metrics

        Returns:
            Message ID
        """
        collection_name = self._get_collection_name(conversation_id)
        message_id = str(uuid.uuid4())

        # Generate embedding
        embedding = self._generate_embedding(content)

        # Prepare payload
        payload = {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        # Add performance data if available
        if performance_data:
            payload["performance"] = performance_data

            # Update conversation metadata
            if conversation_id in self.conversation_metadata:
                response_time = performance_data.get("response_time", 0.0)
                self.conversation_metadata[conversation_id]["total_response_time"] += response_time

        # Store in Qdrant
        try:
            self.qdrant.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=message_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )

            # Update message count
            if conversation_id in self.conversation_metadata:
                self.conversation_metadata[conversation_id]["message_count"] += 1

            logger.debug(f"Added {role} message to conversation {conversation_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise

    def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all messages from a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Optional limit on number of messages

        Returns:
            List of messages
        """
        collection_name = self._get_collection_name(conversation_id)

        try:
            # Scroll through all points in collection
            messages = []
            offset = None

            while True:
                result = self.qdrant.scroll(
                    collection_name=collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )

                points, next_offset = result

                for point in points:
                    messages.append(point.payload)

                if next_offset is None or (limit and len(messages) >= limit):
                    break

                offset = next_offset

            # Sort by timestamp
            messages.sort(key=lambda x: x.get("timestamp", ""))

            # Apply limit
            if limit:
                messages = messages[-limit:]

            return messages
        except Exception as e:
            logger.error(f"Failed to retrieve messages: {e}")
            return []

    def search_similar_messages(
        self,
        conversation_id: str,
        query: str,
        limit: int = 5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar messages in the conversation.

        Args:
            conversation_id: Conversation ID
            query: Search query
            limit: Number of results

        Returns:
            List of (message, score) tuples
        """
        collection_name = self._get_collection_name(conversation_id)

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        try:
            results = self.qdrant.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True
            )

            return [(hit.payload, hit.score) for hit in results]
        except Exception as e:
            logger.error(f"Failed to search messages: {e}")
            return []

    def end_conversation(self, conversation_id: str, delete_collection: bool = True) -> bool:
        """
        End a conversation and optionally delete its collection.

        Args:
            conversation_id: Conversation ID
            delete_collection: Whether to delete the Qdrant collection

        Returns:
            True if successful
        """
        collection_name = self._get_collection_name(conversation_id)

        # Remove from active conversations
        topic_to_remove = None
        for topic, cid in self.active_conversations.items():
            if cid == conversation_id:
                topic_to_remove = topic
                break

        if topic_to_remove:
            del self.active_conversations[topic_to_remove]

        # Delete collection if requested
        if delete_collection:
            try:
                self.qdrant.delete_collection(collection_name=collection_name)
                logger.info(f"Deleted conversation collection: {collection_name}")
            except Exception as e:
                logger.error(f"Failed to delete collection: {e}")
                return False

        # Remove metadata
        if conversation_id in self.conversation_metadata:
            del self.conversation_metadata[conversation_id]

        logger.info(f"Ended conversation {conversation_id}")
        return True

    def get_conversation_by_topic(self, topic: str) -> Optional[str]:
        """
        Get conversation ID by topic.

        Args:
            topic: Conversation topic

        Returns:
            Conversation ID or None
        """
        return self.active_conversations.get(topic)

    def get_active_conversations(self) -> Dict[str, str]:
        """
        Get all active conversations.

        Returns:
            Dict of topic -> conversation_id
        """
        return self.active_conversations.copy()

    def get_conversation_metadata(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Metadata dict or None
        """
        return self.conversation_metadata.get(conversation_id)
