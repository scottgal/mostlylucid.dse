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
        embedding_endpoint: str = "http://localhost:11434",
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "code_evolver_artifacts",
        vector_size: int = 768  # Default for nomic-embed-text (768), llama3 is 4096
    ):
        """
        Initialize Qdrant RAG memory.

        Args:
            memory_path: Path to memory storage directory (for metadata)
            ollama_client: OllamaClient for generating embeddings (optional, uses endpoint if not provided)
            embedding_model: Model to use for embeddings
            embedding_endpoint: Explicit endpoint for embedding generation (default: local Ollama)
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
        self.embedding_endpoint = embedding_endpoint  # Explicit endpoint for embeddings
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

            except json.JSONDecodeError as e:
                # Try to repair JSON with control characters
                logger.warning(f"JSON decode error in metadata: {e}")
                logger.warning("Attempting to repair JSON by escaping control characters...")

                try:
                    import re
                    with open(self.index_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Proper JSON repair: only escape control characters inside string values
                    # Use a regex to find string values and escape control chars within them
                    def escape_string_contents(match):
                        """Escape control characters inside a JSON string value."""
                        string_content = match.group(0)
                        # Escape control characters inside the string
                        string_content = string_content.replace('\t', '\\t')
                        string_content = string_content.replace('\r', '\\r')
                        string_content = string_content.replace('\n', '\\n')
                        string_content = string_content.replace('\b', '\\b')
                        string_content = string_content.replace('\f', '\\f')
                        return string_content

                    # Match JSON strings (accounting for escaped quotes)
                    # Pattern: " followed by any chars (non-greedy), but skip already-escaped sequences
                    content_fixed = re.sub(
                        r'"(?:[^"\\]|\\.)*"',
                        escape_string_contents,
                        content
                    )

                    # Try parsing the fixed content
                    index = json.loads(content_fixed)

                    for artifact_id, artifact_data in index.items():
                        artifact = Artifact.from_dict(artifact_data)
                        self.artifacts[artifact_id] = artifact

                    logger.info(f"✓ Repaired and loaded {len(self.artifacts)} artifacts from metadata")

                    # Save the repaired version
                    logger.info("Saving repaired metadata file...")
                    self._save_metadata()

                except Exception as repair_error:
                    logger.error(f"Could not repair metadata: {repair_error}")
                    logger.warning("Backing up corrupted file and starting fresh...")

                    # Backup corrupted file
                    import shutil
                    from datetime import datetime
                    backup_path = self.index_path.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                    shutil.copy2(self.index_path, backup_path)
                    logger.info(f"Backed up to {backup_path}")

                    # Remove corrupted file to start fresh
                    self.index_path.unlink()
                    self.artifacts = {}

            except Exception as e:
                logger.error(f"Error loading metadata: {e}")

        # Load tags index
        if self.tags_index_path.exists():
            try:
                with open(self.tags_index_path, 'r', encoding='utf-8') as f:
                    self.tags_index = json.load(f)

                logger.info(f"✓ Loaded tags index with {len(self.tags_index)} tags")

            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error in tags index: {e}")
                logger.warning("Starting with empty tags index...")
                # If tags index is corrupted, just start fresh (it can be rebuilt)
                import shutil
                from datetime import datetime
                backup_path = self.tags_index_path.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                try:
                    shutil.copy2(self.tags_index_path, backup_path)
                    logger.info(f"Backed up corrupted tags index to {backup_path}")
                except Exception:
                    pass
                self.tags_index_path.unlink()
                self.tags_index = {}

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
        Generate embedding for text using Ollama endpoint.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if generation fails
        """
        try:
            import requests

            # Use explicit embedding endpoint (not ollama_client.base_url)
            # This ensures embeddings always use local Ollama even when LLM uses cloud API
            response = requests.post(
                f"{self.embedding_endpoint}/api/embed",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=90  # Increased from 30s to allow for busy Ollama instances
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
            logger.error(f"  Endpoint: {self.embedding_endpoint}")
            logger.error(f"  Model: {self.embedding_model}")

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
                # Extract fitness dimensions from metadata for indexing
                meta = metadata or {}

                point = PointStruct(
                    id=hash(artifact_id) & 0x7FFFFFFFFFFFFFFF,  # Convert to positive int
                    vector=embedding,
                    payload={
                        "artifact_id": artifact_id,
                        "artifact_type": artifact_type.value,
                        "name": name,
                        "description": description,
                        "content": content,  # Store actual content in Qdrant
                        "tags": tags,
                        "quality_score": artifact.quality_score,
                        "created_at": artifact.created_at,
                        "metadata": meta,

                        # FITNESS DIMENSIONS (indexed for fast filtering/search)
                        # These enable queries like "find fast, cheap tools for this task"
                        "speed_tier": meta.get("speed_tier", "medium"),
                        "cost_tier": meta.get("cost_tier", "medium"),
                        "quality_tier": meta.get("quality_tier", "good"),
                        "latency_ms": float(meta.get("latency_ms", 0)),
                        "memory_mb_peak": float(meta.get("memory_mb_peak", 0)),
                        "success_count": int(meta.get("success_count", 0)),
                        "total_runs": int(meta.get("total_runs", 0)),
                        "success_rate": float(meta.get("success_count", 0)) / max(float(meta.get("total_runs", 1)), 1.0),

                        # Tool characteristics for filtering
                        "is_tool": bool(meta.get("is_tool", False)),
                        "tool_id": str(meta.get("tool_id", "")),
                        "max_output_length": meta.get("max_output_length", "medium"),
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

                # Try to get from local cache first
                if artifact_id in self.artifacts:
                    artifact = self.artifacts[artifact_id]
                    similarity = hit.score
                    results.append((artifact, similarity))
                else:
                    # Fallback: reconstruct from Qdrant payload
                    # This allows retrieval even if local JSON is missing
                    try:
                        # Reconstruct metadata including fitness dimensions
                        metadata = hit.payload.get("metadata", {})

                        # Add fitness dimensions to metadata if not already present
                        if "speed_tier" not in metadata:
                            metadata.update({
                                "speed_tier": hit.payload.get("speed_tier", "medium"),
                                "cost_tier": hit.payload.get("cost_tier", "medium"),
                                "quality_tier": hit.payload.get("quality_tier", "good"),
                                "latency_ms": hit.payload.get("latency_ms", 0),
                                "memory_mb_peak": hit.payload.get("memory_mb_peak", 0),
                                "success_count": hit.payload.get("success_count", 0),
                                "total_runs": hit.payload.get("total_runs", 0),
                                "success_rate": hit.payload.get("success_rate", 0),
                                "is_tool": hit.payload.get("is_tool", False),
                                "tool_id": hit.payload.get("tool_id", ""),
                                "max_output_length": hit.payload.get("max_output_length", "medium"),
                            })

                        artifact = Artifact(
                            artifact_id=artifact_id,
                            artifact_type=ArtifactType(hit.payload.get("artifact_type")),
                            name=hit.payload.get("name", ""),
                            description=hit.payload.get("description", ""),
                            content=hit.payload.get("content", ""),
                            tags=hit.payload.get("tags", []),
                            metadata=metadata,
                            quality_score=hit.payload.get("quality_score", 0.0),
                            created_at=hit.payload.get("created_at"),
                            embedding=None  # Don't need embedding for retrieval
                        )
                        similarity = hit.score
                        results.append((artifact, similarity))
                    except Exception as e:
                        logger.warning(f"Could not reconstruct artifact {artifact_id} from Qdrant payload: {e}")

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
        match_all: bool = False,
        limit: Optional[int] = None
    ) -> List[Artifact]:
        """
        Find artifacts by tags.

        Args:
            tags: List of tags to search for
            artifact_type: Optional type filter
            match_all: If True, artifact must have all tags; if False, any tag
            limit: Optional maximum number of results to return

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

        # Apply limit if specified
        if limit is not None and limit > 0:
            results = results[:limit]

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
        """
        Clear all vectors from Qdrant collection AND all file-based metadata (use with caution!).

        This completely resets the RAG memory to an empty state, including:
        - Qdrant collection vectors
        - File-based artifact metadata
        - Tags index
        - All stored artifacts on disk
        """
        import shutil

        try:
            # Clear Qdrant collection
            self.qdrant.delete_collection(self.collection_name)
            self._init_collection()
            logger.info(f"OK Cleared Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error clearing Qdrant collection: {e}")

        # Clear all file-based metadata and artifacts
        try:
            # Clear in-memory artifacts dict
            self.artifacts.clear()
            self.tags_index.clear()

            # Clear artifacts directory (contains actual artifact JSON files)
            if self.artifacts_path.exists():
                shutil.rmtree(self.artifacts_path)
                self.artifacts_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"OK Cleared artifacts directory: {self.artifacts_path}")

            # Reset index.json
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump({"artifacts": []}, f, indent=2)
            logger.info(f"OK Reset metadata index: {self.index_path}")

            # Reset tags_index.json
            with open(self.tags_index_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
            logger.info(f"OK Reset tags index: {self.tags_index_path}")

            logger.info("OK ALL RAG memory cleared (vectors + metadata + artifacts)")

        except Exception as e:
            logger.error(f"Error clearing file-based metadata: {e}")
