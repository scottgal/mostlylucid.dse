"""
Qdrant-integrated RAG Memory System
Uses Qdrant vector database for efficient similarity search.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue, MatchAny
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("qdrant-client not installed. Install with: pip install qdrant-client")

from .rag_memory import Artifact, ArtifactType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QdrantRAGMemory:
    """
    RAG-based memory system using Qdrant vector database.

    Features:
    - Efficient vector similarity search via Qdrant
    - Scalable storage (can handle millions of vectors)
    - Filtered search by artifact type and tags
    - Persistent storage in Qdrant + JSON metadata
    """

    def __init__(
        self,
        memory_path: str = "./rag_memory",
        ollama_client: Optional[Any] = None,
        embedding_model: str = "nomic-embed-text",
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "code_evolver_artifacts",
        vector_size: int = 768  # Default for nomic-embed-text (768), llama3 is 4096
    ):
        """
        Initialize Qdrant RAG memory.

        Args:
            memory_path: Path to memory storage directory (for metadata)
            ollama_client: OllamaClient for generating embeddings
            embedding_model: Model to use for embeddings
            qdrant_url: URL for Qdrant server
            collection_name: Name of Qdrant collection
            vector_size: Dimension of embedding vectors
        """
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client is required. Install with: pip install qdrant-client")

        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)

        self.ollama_client = ollama_client
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.vector_size = vector_size

        # Connect to Qdrant
        self.qdrant = QdrantClient(url=qdrant_url)
        logger.info(f"Connected to Qdrant at {qdrant_url}")

        # Initialize collection
        self._init_collection()

        # Storage paths for metadata
        self.index_path = self.memory_path / "index.json"
        self.tags_index_path = self.memory_path / "tags_index.json"

        # In-memory storage for metadata
        self.artifacts: Dict[str, Artifact] = {}
        self.tags_index: Dict[str, List[str]] = {}

        self._load_metadata()

    def _init_collection(self):
        """Initialize Qdrant collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = self.qdrant.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)

            if not collection_exists:
                # Create collection
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✓ Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"✓ Using existing Qdrant collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Error initializing Qdrant collection: {e}")
            raise

    def _load_metadata(self):
        """Load artifact metadata from disk."""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    index = json.load(f)

                for artifact_id, artifact_data in index.items():
                    artifact = Artifact.from_dict(artifact_data)
                    self.artifacts[artifact_id] = artifact

                logger.info(f"✓ Loaded {len(self.artifacts)} artifacts from metadata")

            except Exception as e:
                logger.error(f"Error loading metadata: {e}")

        # Load tags index
        if self.tags_index_path.exists():
            try:
                with open(self.tags_index_path, 'r', encoding='utf-8') as f:
                    self.tags_index = json.load(f)

                logger.info(f"✓ Loaded tags index with {len(self.tags_index)} tags")

            except Exception as e:
                logger.error(f"Error loading tags index: {e}")

    def _save_metadata(self):
        """Save artifact metadata to disk."""
        try:
            index = {aid: artifact.to_dict() for aid, artifact in self.artifacts.items()}

            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def _save_tags_index(self):
        """Save tags index to disk."""
        try:
            with open(self.tags_index_path, 'w', encoding='utf-8') as f:
                json.dump(self.tags_index, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tags index: {e}")

    def _update_tags_index(self, artifact_id: str, tags: List[str]):
        """Update tags index with artifact."""
        for tag in tags:
            if tag not in self.tags_index:
                self.tags_index[tag] = []

            if artifact_id not in self.tags_index[tag]:
                self.tags_index[tag].append(artifact_id)

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using Ollama.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if generation fails
        """
        if not self.ollama_client:
            logger.warning("OllamaClient not configured, cannot generate embeddings")
            return None

        try:
            import requests

            endpoint = self.ollama_client.base_url
            response = requests.post(
                f"{endpoint}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            embedding = data.get("embedding")
            if embedding:
                logger.debug(f"✓ Generated embedding of dimension {len(embedding)}")

                # Update vector size if different
                if len(embedding) != self.vector_size:
                    logger.warning(f"Embedding size {len(embedding)} differs from configured {self.vector_size}")
                    self.vector_size = len(embedding)

                return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")

        return None

    def store_artifact(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        name: str,
        description: str,
        content: str,
        tags: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        auto_embed: bool = True
    ) -> Artifact:
        """
        Store an artifact in Qdrant RAG memory.

        Args:
            artifact_id: Unique identifier
            artifact_type: Type of artifact
            name: Human-readable name
            description: Detailed description
            content: Actual content
            tags: List of tags
            metadata: Additional metadata
            auto_embed: Whether to automatically generate embedding

        Returns:
            Created Artifact object
        """
        # Generate embedding if requested
        embedding = None
        if auto_embed:
            embed_text = f"{name}\n{description}\n{content[:500]}"
            embedding = self._generate_embedding(embed_text)

        # Create artifact
        artifact = Artifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            name=name,
            description=description,
            content=content,
            tags=tags,
            metadata=metadata,
            embedding=embedding
        )

        # Store metadata in memory and disk
        self.artifacts[artifact_id] = artifact
        self._update_tags_index(artifact_id, tags)
        self._save_metadata()
        self._save_tags_index()

        # Store vector in Qdrant
        if embedding:
            try:
                point = PointStruct(
                    id=hash(artifact_id) & 0x7FFFFFFFFFFFFFFF,  # Convert to positive int
                    vector=embedding,
                    payload={
                        "artifact_id": artifact_id,
                        "artifact_type": artifact_type.value,
                        "name": name,
                        "description": description,
                        "tags": tags,
                        "quality_score": artifact.quality_score,
                        "created_at": artifact.created_at
                    }
                )

                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )

                logger.info(f"✓ Stored {artifact_type.value} in Qdrant: {artifact_id}")

            except Exception as e:
                logger.error(f"Error storing vector in Qdrant: {e}")

        return artifact

    def find_similar(
        self,
        query: str,
        artifact_type: Optional[ArtifactType] = None,
        tags: Optional[List[str]] = None,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[Tuple[Artifact, float]]:
        """
        Find similar artifacts using Qdrant vector search.

        Args:
            query: Query text
            artifact_type: Optional filter by artifact type
            tags: Optional filter by tags (any match)
            top_k: Number of results to return
            min_similarity: Minimum similarity score

        Returns:
            List of (Artifact, similarity_score) tuples
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        if not query_embedding:
            logger.warning("Cannot perform semantic search without embedding, falling back to keyword search")
            return self.search_by_keywords(query, artifact_type, tags, top_k)

        try:
            # Build filter
            filter_conditions = []

            if artifact_type:
                filter_conditions.append(
                    FieldCondition(
                        key="artifact_type",
                        match=MatchValue(value=artifact_type.value)
                    )
                )

            if tags:
                filter_conditions.append(
                    FieldCondition(
                        key="tags",
                        match=MatchAny(any=tags)
                    )
                )

            search_filter = Filter(must=filter_conditions) if filter_conditions else None

            # Search in Qdrant
            search_results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=top_k,
                score_threshold=min_similarity
            )

            # Convert results to artifacts
            results = []
            for hit in search_results:
                artifact_id = hit.payload.get("artifact_id")
                if artifact_id in self.artifacts:
                    artifact = self.artifacts[artifact_id]
                    similarity = hit.score
                    results.append((artifact, similarity))

            logger.info(f"✓ Found {len(results)} similar artifacts via Qdrant")
            return results

        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            return []

    def search_by_keywords(
        self,
        query: str,
        artifact_type: Optional[ArtifactType] = None,
        tags: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Tuple[Artifact, float]]:
        """
        Keyword-based search fallback.

        Args:
            query: Query text
            artifact_type: Optional filter by type
            tags: Optional filter by tags
            top_k: Number of results

        Returns:
            List of (Artifact, score) tuples
        """
        query_words = set(query.lower().split())
        results = []

        for artifact in self.artifacts.values():
            # Apply filters
            if artifact_type and artifact.artifact_type != artifact_type:
                continue

            if tags and not any(tag in artifact.tags for tag in tags):
                continue

            # Calculate keyword overlap score
            artifact_text = f"{artifact.name} {artifact.description} {' '.join(artifact.tags)}"
            artifact_words = set(artifact_text.lower().split())

            intersection = query_words & artifact_words
            union = query_words | artifact_words

            if union:
                score = len(intersection) / len(union)
                if score > 0:
                    results.append((artifact, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def find_by_tags(
        self,
        tags: List[str],
        artifact_type: Optional[ArtifactType] = None,
        match_all: bool = False
    ) -> List[Artifact]:
        """
        Find artifacts by tags.

        Args:
            tags: List of tags to search for
            artifact_type: Optional type filter
            match_all: If True, artifact must have all tags; if False, any tag

        Returns:
            List of matching artifacts
        """
        matching_ids = set()

        for tag in tags:
            if tag in self.tags_index:
                if not matching_ids:
                    matching_ids = set(self.tags_index[tag])
                else:
                    if match_all:
                        matching_ids &= set(self.tags_index[tag])
                    else:
                        matching_ids |= set(self.tags_index[tag])

        results = []
        for artifact_id in matching_ids:
            if artifact_id in self.artifacts:
                artifact = self.artifacts[artifact_id]

                if artifact_type and artifact.artifact_type != artifact_type:
                    continue

                results.append(artifact)

        # Sort by usage count and quality
        results.sort(
            key=lambda a: (a.quality_score, a.usage_count),
            reverse=True
        )

        return results

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID."""
        return self.artifacts.get(artifact_id)

    def increment_usage(self, artifact_id: str):
        """Increment usage counter for artifact."""
        if artifact_id in self.artifacts:
            self.artifacts[artifact_id].usage_count += 1
            self._save_metadata()

    def update_quality_score(self, artifact_id: str, score: float):
        """
        Update quality score for artifact.

        Args:
            artifact_id: Artifact identifier
            score: Quality score (0.0 to 1.0)
        """
        if artifact_id in self.artifacts:
            self.artifacts[artifact_id].quality_score = max(0.0, min(1.0, score))
            self._save_metadata()

            # Also update in Qdrant
            try:
                point_id = hash(artifact_id) & 0x7FFFFFFFFFFFFFFF
                self.qdrant.set_payload(
                    collection_name=self.collection_name,
                    payload={"quality_score": score},
                    points=[point_id]
                )
            except Exception as e:
                logger.warning(f"Could not update quality score in Qdrant: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics."""
        type_counts = {}
        for artifact in self.artifacts.values():
            type_name = artifact.artifact_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Most used artifacts
        most_used = sorted(
            self.artifacts.values(),
            key=lambda a: a.usage_count,
            reverse=True
        )[:5]

        # Highest quality artifacts
        highest_quality = sorted(
            self.artifacts.values(),
            key=lambda a: a.quality_score,
            reverse=True
        )[:5]

        # Qdrant collection info
        try:
            collection_info = self.qdrant.get_collection(self.collection_name)
            vector_count = collection_info.points_count
        except:
            vector_count = 0

        return {
            "total_artifacts": len(self.artifacts),
            "vectors_in_qdrant": vector_count,
            "by_type": type_counts,
            "total_tags": len(self.tags_index),
            "vector_size": self.vector_size,
            "most_used": [
                {"id": a.artifact_id, "name": a.name, "type": a.artifact_type.value, "usage": a.usage_count}
                for a in most_used
            ],
            "highest_quality": [
                {"id": a.artifact_id, "name": a.name, "type": a.artifact_type.value, "score": a.quality_score}
                for a in highest_quality
            ]
        }

    def list_all(
        self,
        artifact_type: Optional[ArtifactType] = None,
        tags: Optional[List[str]] = None
    ) -> List[Artifact]:
        """
        List all artifacts with optional filters.

        Args:
            artifact_type: Optional type filter
            tags: Optional tags filter

        Returns:
            List of artifacts
        """
        results = []

        for artifact in self.artifacts.values():
            if artifact_type and artifact.artifact_type != artifact_type:
                continue

            if tags and not any(tag in artifact.tags for tag in tags):
                continue

            results.append(artifact)

        results.sort(key=lambda a: (a.quality_score, a.usage_count), reverse=True)
        return results

    def delete_artifact(self, artifact_id: str) -> bool:
        """Delete an artifact."""
        if artifact_id not in self.artifacts:
            return False

        artifact = self.artifacts[artifact_id]

        # Remove from tags index
        for tag in artifact.tags:
            if tag in self.tags_index:
                self.tags_index[tag] = [aid for aid in self.tags_index[tag] if aid != artifact_id]
                if not self.tags_index[tag]:
                    del self.tags_index[tag]

        # Remove from artifacts
        del self.artifacts[artifact_id]

        # Remove from Qdrant
        try:
            point_id = hash(artifact_id) & 0x7FFFFFFFFFFFFFFF
            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
        except Exception as e:
            logger.warning(f"Could not delete from Qdrant: {e}")

        # Save changes
        self._save_metadata()
        self._save_tags_index()

        logger.info(f"✓ Deleted artifact: {artifact_id}")
        return True

    def clear_collection(self):
        """Clear all vectors from Qdrant collection (use with caution!)."""
        try:
            self.qdrant.delete_collection(self.collection_name)
            self._init_collection()
            logger.info(f"✓ Cleared Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
