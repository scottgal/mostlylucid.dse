"""
RAG (Retrieval-Augmented Generation) Memory System
Stores and retrieves plans, functions, sub-workflows, and workflows using embeddings.
"""
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArtifactType(Enum):
    """Types of artifacts that can be stored in RAG memory."""
    PLAN = "plan"                    # Overseer strategies and approaches
    FUNCTION = "function"            # Reusable code functions
    SUB_WORKFLOW = "sub_workflow"   # Parts of larger workflows
    WORKFLOW = "workflow"            # Complete workflow sequences
    PROMPT = "prompt"                # Reusable prompts
    PATTERN = "pattern"              # Design patterns and solutions


class Artifact:
    """Represents a stored artifact with embeddings."""

    def __init__(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        name: str,
        description: str,
        content: str,
        tags: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ):
        """
        Initialize artifact.

        Args:
            artifact_id: Unique identifier
            artifact_type: Type of artifact
            name: Human-readable name
            description: Detailed description
            content: The actual content (code, plan, workflow definition, etc.)
            tags: List of tags for categorization
            metadata: Additional metadata
            embedding: Optional pre-computed embedding vector
        """
        self.artifact_id = artifact_id
        self.artifact_type = artifact_type
        self.name = name
        self.description = description
        self.content = content
        self.tags = tags
        self.metadata = metadata or {}
        self.embedding = embedding
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.usage_count = 0
        self.quality_score = 0.0  # Can be updated based on user feedback

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "tags": self.tags,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "usage_count": self.usage_count,
            "quality_score": self.quality_score
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Artifact':
        """Create artifact from dictionary."""
        artifact = Artifact(
            artifact_id=data["artifact_id"],
            artifact_type=ArtifactType(data["artifact_type"]),
            name=data["name"],
            description=data["description"],
            content=data["content"],
            tags=data["tags"],
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding")
        )
        artifact.created_at = data.get("created_at", artifact.created_at)
        artifact.usage_count = data.get("usage_count", 0)
        artifact.quality_score = data.get("quality_score", 0.0)
        return artifact


class RAGMemory:
    """
    RAG-based memory system for storing and retrieving artifacts.
    Uses embeddings for semantic similarity search.
    """

    def __init__(
        self,
        memory_path: str = "./rag_memory",
        ollama_client: Optional[Any] = None,
        embedding_model: str = "llama3"
    ):
        """
        Initialize RAG memory.

        Args:
            memory_path: Path to memory storage directory
            ollama_client: OllamaClient for generating embeddings
            embedding_model: Model to use for embeddings
        """
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)

        self.ollama_client = ollama_client
        self.embedding_model = embedding_model

        # Storage paths
        self.artifacts_path = self.memory_path / "artifacts"
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        self.index_path = self.memory_path / "index.json"
        self.embeddings_path = self.memory_path / "embeddings.npy"
        self.tags_index_path = self.memory_path / "tags_index.json"

        # In-memory storage
        self.artifacts: Dict[str, Artifact] = {}
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.artifact_id_to_index: Dict[str, int] = {}
        self.tags_index: Dict[str, List[str]] = {}  # tag -> [artifact_ids]

        self._load_memory()

    def _load_memory(self):
        """Load artifacts and embeddings from disk."""
        # Load index
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    index = json.load(f)

                for artifact_id, artifact_data in index.items():
                    artifact = Artifact.from_dict(artifact_data)
                    self.artifacts[artifact_id] = artifact

                logger.info(f"✓ Loaded {len(self.artifacts)} artifacts")

            except Exception as e:
                logger.error(f"Error loading artifacts index: {e}")

        # Load embeddings matrix
        if self.embeddings_path.exists():
            try:
                self.embeddings_matrix = np.load(self.embeddings_path)

                # Rebuild artifact_id_to_index mapping
                artifact_ids = sorted(self.artifacts.keys())
                self.artifact_id_to_index = {aid: i for i, aid in enumerate(artifact_ids)}

                logger.info(f"✓ Loaded embeddings matrix: {self.embeddings_matrix.shape}")

            except Exception as e:
                logger.error(f"Error loading embeddings: {e}")

        # Load tags index
        if self.tags_index_path.exists():
            try:
                with open(self.tags_index_path, 'r', encoding='utf-8') as f:
                    self.tags_index = json.load(f)

                logger.info(f"✓ Loaded tags index with {len(self.tags_index)} tags")

            except Exception as e:
                logger.error(f"Error loading tags index: {e}")

    def _save_index(self):
        """Save artifacts index to disk."""
        try:
            index = {aid: artifact.to_dict() for aid, artifact in self.artifacts.items()}

            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def _save_embeddings(self):
        """Save embeddings matrix to disk."""
        if self.embeddings_matrix is not None:
            try:
                np.save(self.embeddings_path, self.embeddings_matrix)
            except Exception as e:
                logger.error(f"Error saving embeddings: {e}")

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
            # Use Ollama's embeddings API
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
        Store an artifact in RAG memory.

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
            embed_text = f"{name}\n{description}\n{content[:500]}"  # Limit content length
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

        # Store in memory
        self.artifacts[artifact_id] = artifact

        # Update tags index
        self._update_tags_index(artifact_id, tags)

        # Update embeddings matrix
        if embedding:
            self._add_embedding(artifact_id, embedding)

        # Save to disk
        self._save_index()
        self._save_embeddings()
        self._save_tags_index()

        logger.info(f"✓ Stored {artifact_type.value}: {artifact_id}")

        return artifact

    def _add_embedding(self, artifact_id: str, embedding: List[float]):
        """Add embedding to the matrix."""
        embedding_array = np.array(embedding, dtype=np.float32)

        if self.embeddings_matrix is None:
            # Initialize matrix
            self.embeddings_matrix = embedding_array.reshape(1, -1)
            self.artifact_id_to_index = {artifact_id: 0}
        else:
            # Append to matrix
            self.embeddings_matrix = np.vstack([self.embeddings_matrix, embedding_array])
            self.artifact_id_to_index[artifact_id] = len(self.artifact_id_to_index)

    def find_similar(
        self,
        query: str,
        artifact_type: Optional[ArtifactType] = None,
        tags: Optional[List[str]] = None,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[Tuple[Artifact, float]]:
        """
        Find similar artifacts using embedding similarity.

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

        if not query_embedding or self.embeddings_matrix is None:
            logger.warning("Cannot perform semantic search, falling back to keyword search")
            return self.search_by_keywords(query, artifact_type, tags, top_k)

        # Calculate cosine similarity
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        # Normalize query vector
        query_vec = query_vec / query_norm

        # Calculate similarities
        similarities = []
        artifact_ids = sorted(self.artifacts.keys())

        for i, artifact_id in enumerate(artifact_ids):
            artifact = self.artifacts[artifact_id]

            # Apply filters
            if artifact_type and artifact.artifact_type != artifact_type:
                continue

            if tags and not any(tag in artifact.tags for tag in tags):
                continue

            # Get embedding vector
            if i < len(self.embeddings_matrix):
                artifact_vec = self.embeddings_matrix[i]
                artifact_norm = np.linalg.norm(artifact_vec)

                if artifact_norm > 0:
                    artifact_vec = artifact_vec / artifact_norm
                    similarity = np.dot(query_vec, artifact_vec)

                    if similarity >= min_similarity:
                        similarities.append((artifact, float(similarity)))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

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
            self._save_index()

    def update_quality_score(self, artifact_id: str, score: float):
        """
        Update quality score for artifact.

        Args:
            artifact_id: Artifact identifier
            score: Quality score (0.0 to 1.0)
        """
        if artifact_id in self.artifacts:
            self.artifacts[artifact_id].quality_score = max(0.0, min(1.0, score))
            self._save_index()

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

        return {
            "total_artifacts": len(self.artifacts),
            "by_type": type_counts,
            "total_tags": len(self.tags_index),
            "has_embeddings": self.embeddings_matrix is not None,
            "embedding_dimension": self.embeddings_matrix.shape[1] if self.embeddings_matrix is not None else 0,
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

        # TODO: Remove from embeddings matrix (requires rebuilding)

        # Save changes
        self._save_index()
        self._save_tags_index()

        logger.info(f"✓ Deleted artifact: {artifact_id}")
        return True
