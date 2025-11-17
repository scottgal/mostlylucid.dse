"""
Conversation Embedder

Embeds conversations and retrieves related context from past conversations.
Uses semantic search to find relevant conversation snippets.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
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


class ConversationEmbedder:
    """
    Embeds and retrieves related conversations.

    Features:
    - Stores conversation metadata with embeddings
    - Retrieves similar past conversations
    - Finds relevant conversation snippets
    - Optimizes context size for inclusion
    """

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "nomic-embed-text",
        embedding_endpoint: str = "http://localhost:11434",
        vector_size: int = 768,
        collection_name: str = "conversation_metadata"
    ):
        """
        Initialize conversation embedder.

        Args:
            qdrant_url: Qdrant server URL
            embedding_model: Embedding model
            embedding_endpoint: Embedding API endpoint
            vector_size: Embedding vector size
            collection_name: Qdrant collection for conversation metadata
        """
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client required. Install with: pip install qdrant-client")

        self.qdrant_url = qdrant_url
        self.embedding_model = embedding_model
        self.embedding_endpoint = embedding_endpoint
        self.vector_size = vector_size
        self.collection_name = collection_name

        # Connect to Qdrant
        self.qdrant = QdrantClient(url=qdrant_url)
        logger.info(f"Connected to Qdrant at {qdrant_url}")

        # Initialize metadata collection
        self._init_collection()

    def _init_collection(self):
        """Initialize Qdrant collection for conversation metadata."""
        try:
            collections = self.qdrant.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)

            if not collection_exists:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = requests.post(
                f"{self.embedding_endpoint}/api/embeddings",
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
            return [0.0] * self.vector_size

    def store_conversation_metadata(
        self,
        conversation_id: str,
        topic: str,
        summary: str,
        key_points: List[str],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store conversation metadata with embedding.

        Args:
            conversation_id: Unique conversation ID
            topic: Conversation topic
            summary: Conversation summary
            key_points: List of key points
            metadata: Additional metadata (duration, message_count, etc.)

        Returns:
            True if successful
        """
        # Create searchable text from summary and key points
        searchable_text = f"{topic}\n\n{summary}\n\n" + "\n".join(key_points)

        # Generate embedding
        embedding = self._generate_embedding(searchable_text)

        # Prepare payload
        payload = {
            "conversation_id": conversation_id,
            "topic": topic,
            "summary": summary,
            "key_points": key_points,
            **metadata
        }

        try:
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=conversation_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            logger.info(f"Stored metadata for conversation: {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store conversation metadata: {e}")
            return False

    def find_related_conversations(
        self,
        query: str,
        limit: int = 3,
        exclude_conversation_id: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find conversations related to a query.

        Args:
            query: Search query
            limit: Number of results
            exclude_conversation_id: Conversation ID to exclude from results

        Returns:
            List of (conversation_metadata, similarity_score) tuples
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        try:
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit + 1 if exclude_conversation_id else limit,
                with_payload=True
            )

            # Filter and format results
            related = []
            for hit in results:
                # Skip excluded conversation
                if exclude_conversation_id and hit.payload.get("conversation_id") == exclude_conversation_id:
                    continue

                related.append((hit.payload, hit.score))

                if len(related) >= limit:
                    break

            return related
        except Exception as e:
            logger.error(f"Failed to find related conversations: {e}")
            return []

    def get_related_context(
        self,
        query: str,
        max_snippets: int = 3,
        max_chars_per_snippet: int = 300,
        exclude_conversation_id: Optional[str] = None
    ) -> List[str]:
        """
        Get related context snippets for inclusion in current conversation.

        Args:
            query: Current conversation context/prompt
            max_snippets: Maximum number of snippets to return
            max_chars_per_snippet: Maximum characters per snippet
            exclude_conversation_id: Conversation to exclude

        Returns:
            List of context snippets
        """
        related = self.find_related_conversations(
            query,
            limit=max_snippets,
            exclude_conversation_id=exclude_conversation_id
        )

        snippets = []
        for conversation, score in related:
            # Build snippet from topic, summary, and key points
            topic = conversation.get("topic", "Unknown")
            summary = conversation.get("summary", "")
            key_points = conversation.get("key_points", [])

            # Create compact snippet
            snippet_parts = [f"[Related: {topic}]"]

            # Add summary (truncated if needed)
            if summary:
                if len(summary) > max_chars_per_snippet // 2:
                    summary = summary[:max_chars_per_snippet // 2] + "..."
                snippet_parts.append(summary)

            # Add top key points
            if key_points:
                points_text = "; ".join(key_points[:2])
                if len(points_text) > max_chars_per_snippet // 2:
                    points_text = points_text[:max_chars_per_snippet // 2] + "..."
                snippet_parts.append(f"Key points: {points_text}")

            snippet = " ".join(snippet_parts)

            # Ensure snippet doesn't exceed max length
            if len(snippet) > max_chars_per_snippet:
                snippet = snippet[:max_chars_per_snippet] + "..."

            snippets.append(snippet)

        return snippets

    def delete_conversation_metadata(self, conversation_id: str) -> bool:
        """
        Delete conversation metadata.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if successful
        """
        try:
            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=[conversation_id]
            )
            logger.info(f"Deleted metadata for conversation: {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation metadata: {e}")
            return False

    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored conversations.

        Returns:
            Dict with conversation statistics
        """
        try:
            collection_info = self.qdrant.get_collection(self.collection_name)

            return {
                "total_conversations": collection_info.points_count,
                "vector_size": self.vector_size,
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            logger.error(f"Failed to get conversation stats: {e}")
            return {
                "total_conversations": 0,
                "vector_size": self.vector_size,
                "embedding_model": self.embedding_model
            }
