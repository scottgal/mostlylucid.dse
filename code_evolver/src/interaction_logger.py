"""
Interaction Logger

Comprehensive logging of ALL tool and LLM interactions with:
- Semantic embeddings for input caching
- Quality tracking per input pattern
- Similar interaction search
- Intelligent cache hits

Every interaction (tool call, LLM query, command check) is logged with:
- tool_id: What was called
- input_text: What was sent (embedded for similarity search)
- output: What was returned
- success: Did it work?
- quality_score: How good was the result?
- latency_ms: How long did it take?
- timestamp: When did it happen?

This builds an intelligent system that learns from every interaction.
"""

import json
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import hashlib


class InteractionLogger:
    """
    Logs ALL tool and LLM interactions for intelligent caching and learning
    """

    def __init__(self, rag_memory=None, ollama_client=None):
        """
        Initialize interaction logger

        Args:
            rag_memory: RAG memory instance (optional, will create if needed)
            ollama_client: Ollama client for embeddings (optional)
        """
        self.rag = rag_memory
        self.client = ollama_client

        # Lazy initialization
        if self.rag is None:
            self._init_rag()

    def _init_rag(self):
        """Lazy initialize RAG memory"""
        try:
            from src.config_manager import ConfigManager
            from src.ollama_client import OllamaClient
            from src.rag_memory import RAGMemory

            if self.client is None:
                config = ConfigManager()
                self.client = OllamaClient(config_manager=config)

            self.rag = RAGMemory(ollama_client=self.client)
        except Exception as e:
            # Fallback: continue without RAG (just in-memory logging)
            print(f"Warning: Could not initialize RAG for interaction logging: {e}")
            self.rag = None

    def log_interaction(
        self,
        tool_id: str,
        input_data: Any,
        output_data: Any = None,
        success: bool = True,
        quality_score: Optional[float] = None,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        interaction_type: str = "tool",
        auto_embed: bool = True,
        cacheable_output: bool = True
    ) -> Dict[str, Any]:
        """
        Log a tool or LLM interaction

        Args:
            tool_id: ID of tool/LLM called
            input_data: Input to tool (will be stringified and embedded)
            output_data: Output from tool
            success: Whether interaction succeeded
            quality_score: Quality of result (0.0-1.0)
            latency_ms: How long interaction took
            error: Error message if failed
            metadata: Additional metadata
            interaction_type: 'tool', 'llm', 'command_check', etc.
            auto_embed: Whether to generate embedding for similarity search
            cacheable_output: Whether output can be cached for reuse (False for creative/non-deterministic tasks)

        Returns:
            Logged interaction info
        """
        # Convert input to string for embedding
        if isinstance(input_data, dict):
            input_text = json.dumps(input_data, sort_keys=True)
        elif isinstance(input_data, str):
            input_text = input_data
        else:
            input_text = str(input_data)

        # Generate interaction ID
        timestamp = datetime.utcnow()
        interaction_hash = hashlib.md5(
            f"{tool_id}:{input_text}:{timestamp.isoformat()}".encode()
        ).hexdigest()[:12]
        interaction_id = f"interaction_{interaction_hash}"

        # Build interaction record
        interaction = {
            'interaction_id': interaction_id,
            'tool_id': tool_id,
            'interaction_type': interaction_type,
            'input_text': input_text,
            'input_hash': hashlib.md5(input_text.encode()).hexdigest(),
            'output': output_data,
            'success': success,
            'quality_score': quality_score,
            'latency_ms': latency_ms,
            'error': error,
            'timestamp': timestamp.isoformat() + 'Z',
            'cacheable_output': cacheable_output,
            'metadata': metadata or {}
        }

        # Store in RAG for semantic search
        if self.rag is not None:
            try:
                # Create content summary
                content = f"""Tool Interaction: {tool_id}

Type: {interaction_type}

Input:
{input_text[:500]}

Output:
{str(output_data)[:500] if output_data else 'N/A'}

Success: {success}
Quality: {quality_score if quality_score is not None else 'N/A'}
Latency: {latency_ms}ms
"""

                # Store as artifact
                from src.rag_memory import ArtifactType

                self.rag.store_artifact(
                    artifact_id=interaction_id,
                    artifact_type=ArtifactType.PATTERN,  # Use PATTERN for interactions
                    name=f"{interaction_type}: {tool_id}",
                    description=f"{interaction_type} interaction with {tool_id}",
                    content=content,
                    tags=[
                        'interaction',
                        interaction_type,
                        tool_id,
                        f"success:{success}",
                        f"type:{interaction_type}",
                        f"cacheable:{cacheable_output}"
                    ],
                    metadata={
                        'tool_id': tool_id,
                        'interaction_type': interaction_type,
                        'input_hash': interaction['input_hash'],
                        'success': success,
                        'quality_score': quality_score,
                        'latency_ms': latency_ms,
                        'timestamp': interaction['timestamp'],
                        'cacheable_output': cacheable_output,
                        **(metadata or {})
                    },
                    auto_embed=auto_embed
                )

            except Exception as e:
                print(f"Warning: Could not store interaction in RAG: {e}")

        return interaction

    def find_similar_interactions(
        self,
        tool_id: str,
        input_data: Any,
        similarity_threshold: float = 0.85,
        top_k: int = 5,
        min_quality: Optional[float] = None,
        require_success: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find similar past interactions for cache hits

        Args:
            tool_id: Tool to search interactions for
            input_data: Input to search for similar cases
            similarity_threshold: Minimum similarity (0.0-1.0)
            top_k: Maximum results to return
            min_quality: Minimum quality score filter
            require_success: Only return successful interactions

        Returns:
            List of similar interactions with similarity scores
        """
        if self.rag is None:
            return []

        # Convert input to text
        if isinstance(input_data, dict):
            input_text = json.dumps(input_data, sort_keys=True)
        elif isinstance(input_data, str):
            input_text = input_data
        else:
            input_text = str(input_data)

        try:
            # Search for similar interactions
            search_query = f"{tool_id}: {input_text}"

            results = self.rag.find_similar(
                search_query,
                artifact_type=None,  # Search all types
                top_k=top_k * 2  # Get more, filter later
            )

            # Filter and format results
            similar = []
            for artifact, similarity in results:
                # Check if this is an interaction artifact
                metadata = artifact.metadata or {}

                if metadata.get('tool_id') != tool_id:
                    continue  # Different tool

                if 'interaction' not in artifact.tags:
                    continue  # Not an interaction

                # Apply filters
                if require_success and not metadata.get('success', False):
                    continue

                if min_quality is not None:
                    quality = metadata.get('quality_score')
                    if quality is None or quality < min_quality:
                        continue

                if similarity < similarity_threshold:
                    continue

                # CRITICAL: Skip non-cacheable outputs (creative/non-deterministic tasks)
                if not metadata.get('cacheable_output', True):
                    continue

                # Include this result
                similar.append({
                    'interaction_id': artifact.artifact_id,
                    'tool_id': metadata.get('tool_id'),
                    'similarity': similarity,
                    'quality_score': metadata.get('quality_score'),
                    'latency_ms': metadata.get('latency_ms'),
                    'success': metadata.get('success'),
                    'timestamp': metadata.get('timestamp'),
                    'artifact': artifact
                })

            # Sort by quality * similarity
            similar.sort(
                key=lambda x: (x['quality_score'] or 0.5) * x['similarity'],
                reverse=True
            )

            return similar[:top_k]

        except Exception as e:
            print(f"Warning: Error searching for similar interactions: {e}")
            return []

    def compare_prompts_semantically(
        self,
        prompt1: str,
        prompt2: str
    ) -> int:
        """
        Use semantic comparator LLM to get precise similarity score

        Args:
            prompt1: First prompt
            prompt2: Second prompt

        Returns:
            Similarity score 0-100:
            - 100 = Exact same meaning
            - 50-99 = Similar (can mutate)
            - 0-49 = Different (generate new)
        """
        try:
            # Import here to avoid circular dependency
            import sys
            sys.path.insert(0, '.')
            from node_runtime import call_tool
            import json

            result = call_tool("semantic_comparator", json.dumps({
                "prompt1": prompt1,
                "prompt2": prompt2
            }))

            # Parse the score from the result
            try:
                score = int(result.strip())
                # Clamp to 0-100 range
                return max(0, min(100, score))
            except ValueError:
                # If can't parse, try to extract number from response
                import re
                numbers = re.findall(r'\d+', result)
                if numbers:
                    score = int(numbers[0])
                    return max(0, min(100, score))
                # If still can't parse, return low similarity
                return 0

        except Exception as e:
            # If comparator fails, return low similarity (safe default)
            print(f"Warning: Semantic comparator failed: {e}")
            return 0

    def get_cached_result(
        self,
        tool_id: str,
        input_data: Any,
        similarity_threshold: float = 0.90,
        max_age_hours: Optional[float] = None,
        use_semantic_comparator: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Try to get a cached result using SMART two-stage comparison:
        1. Embedding similarity (fast) - must be >= 90% to proceed
        2. Semantic comparator LLM (precise) - returns final decision

        DECISION LOGIC:
        - Embedding < 90% → Generate new (too different)
        - Embedding >= 90% → Call semantic comparator:
          - Score = 100 → IDENTICAL - Full reuse (or fresh content if creative)
          - Score 70-99 → SIMILAR - Mutate/adapt workflow
          - Score < 70 → DIFFERENT - Generate new

        This ensures we:
        1. Only call expensive LLM when embedding is promising (>90%)
        2. Get precise semantic understanding for final decision
        3. Maximize intelligent reuse while preventing false positives

        Args:
            tool_id: Tool being called
            input_data: Input to tool
            similarity_threshold: Embedding threshold (default: 0.90 = 90%)
            max_age_hours: Only use results newer than this
            use_semantic_comparator: Use LLM for final decision (default: True)

        Returns:
            Dict with:
            - 'cached': Cached interaction data
            - 'similarity_score': Semantic score (0-100) from LLM
            - 'decision': 'reuse' (100), 'mutate' (70-99), or 'generate_new' (<70)
            - 'embedding_similarity': Original embedding score
            Or None if embedding < threshold
        """
        similar = self.find_similar_interactions(
            tool_id=tool_id,
            input_data=input_data,
            similarity_threshold=similarity_threshold,
            top_k=1,
            require_success=True,
            min_quality=0.7  # Only cache good results
        )

        if not similar:
            return None

        cached = similar[0]

        # Check age if specified
        if max_age_hours is not None:
            try:
                timestamp_str = cached['timestamp']
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                age_hours = (datetime.utcnow() - timestamp.replace(tzinfo=None)).total_seconds() / 3600

                if age_hours > max_age_hours:
                    return None  # Too old
            except:
                pass  # If timestamp parsing fails, allow cache

        # If semantic comparator is enabled, use it for final decision
        semantic_score = None
        if use_semantic_comparator:
            # Convert input_data to string for comparison
            if isinstance(input_data, dict):
                current_prompt = json.dumps(input_data, sort_keys=True)
            else:
                current_prompt = str(input_data)

            # Get cached input
            cached_artifact = cached.get('artifact')
            if cached_artifact and hasattr(cached_artifact, 'metadata'):
                cached_input = cached_artifact.metadata.get('input_text', '')
            else:
                # Fallback to cached interaction's input
                cached_input = cached.get('input_text', '')

            # Call semantic comparator for precise decision
            semantic_score = self.compare_prompts_semantically(cached_input, current_prompt)

            # Make final decision based on semantic score
            if semantic_score == 100:
                # IDENTICAL - Full reuse
                decision = 'reuse'
            elif semantic_score >= 70:
                # SIMILAR - Can mutate/adapt
                decision = 'mutate'
            else:
                # DIFFERENT - Generate new (score < 70)
                decision = 'generate_new'

            # Return result with all info
            return {
                'cached': cached,
                'similarity_score': semantic_score,
                'decision': decision,
                'embedding_similarity': cached.get('similarity', 0.0),
                'reason': self._get_decision_reason(semantic_score)
            }
        else:
            # No semantic comparator - fallback to embedding only
            # Use stricter thresholds since we don't have LLM validation
            if cached.get('similarity', 0) >= 0.95:
                # Very high embedding similarity - assume identical
                return {
                    'cached': cached,
                    'similarity_score': 100,
                    'decision': 'reuse',
                    'embedding_similarity': cached.get('similarity', 0.0),
                    'reason': 'High embedding similarity (no LLM check)'
                }
            elif cached.get('similarity', 0) >= 0.90:
                # High embedding - assume can mutate
                return {
                    'cached': cached,
                    'similarity_score': int(cached.get('similarity', 0) * 100),
                    'decision': 'mutate',
                    'embedding_similarity': cached.get('similarity', 0.0),
                    'reason': 'Medium embedding similarity (no LLM check)'
                }
            else:
                # Below threshold - generate new
                return None

    def _get_decision_reason(self, semantic_score: int) -> str:
        """Get human-readable reason for caching decision"""
        if semantic_score == 100:
            return "Identical meaning - full reuse"
        elif semantic_score >= 70:
            return f"Similar (score: {semantic_score}) - can adapt/mutate"
        else:
            return f"Too different (score: {semantic_score}) - generate new"

    def update_interaction_quality(
        self,
        interaction_id: str,
        quality_score: float,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update quality score for an interaction after evaluation

        Args:
            interaction_id: ID of interaction to update
            quality_score: New quality score (0.0-1.0)
            additional_metadata: Additional metadata to add

        Returns:
            True if updated successfully
        """
        if self.rag is None:
            return False

        try:
            # Update quality score in RAG
            self.rag.update_quality_score(interaction_id, quality_score)

            # Update metadata if provided
            if additional_metadata:
                artifact = self.rag.get_artifact(interaction_id)
                if artifact:
                    artifact.metadata.update(additional_metadata)
                    # Re-store with updated metadata
                    # (RAG should have update method, but if not, this works)

            return True

        except Exception as e:
            print(f"Warning: Could not update interaction quality: {e}")
            return False

    def get_tool_statistics(
        self,
        tool_id: str,
        hours: Optional[int] = 24
    ) -> Dict[str, Any]:
        """
        Get statistics for a tool's interactions

        Args:
            tool_id: Tool to get stats for
            hours: Hours to look back (None = all time)

        Returns:
            Statistics dict
        """
        if self.rag is None:
            return {
                'total_interactions': 0,
                'success_rate': 0.0,
                'average_quality': 0.0,
                'average_latency_ms': 0.0
            }

        try:
            # Search for all interactions with this tool
            results = self.rag.find_by_tags(['interaction', tool_id])

            if not results:
                return {
                    'total_interactions': 0,
                    'success_rate': 0.0,
                    'average_quality': 0.0,
                    'average_latency_ms': 0.0
                }

            # Filter by time if specified
            if hours is not None:
                cutoff = datetime.utcnow().timestamp() - (hours * 3600)
                filtered_results = []
                for artifact in results:
                    try:
                        ts = datetime.fromisoformat(
                            artifact.metadata.get('timestamp', '').replace('Z', '+00:00')
                        )
                        if ts.timestamp() >= cutoff:
                            filtered_results.append(artifact)
                    except:
                        filtered_results.append(artifact)  # Include if can't parse timestamp
                results = filtered_results

            # Calculate statistics
            total = len(results)
            successes = sum(1 for r in results if r.metadata.get('success', False))
            qualities = [r.metadata.get('quality_score') for r in results if r.metadata.get('quality_score') is not None]
            latencies = [r.metadata.get('latency_ms') for r in results if r.metadata.get('latency_ms') is not None]

            return {
                'total_interactions': total,
                'success_rate': successes / total if total > 0 else 0.0,
                'average_quality': sum(qualities) / len(qualities) if qualities else 0.0,
                'average_latency_ms': sum(latencies) / len(latencies) if latencies else 0.0,
                'total_successes': successes,
                'total_failures': total - successes
            }

        except Exception as e:
            print(f"Warning: Error calculating tool statistics: {e}")
            return {
                'total_interactions': 0,
                'success_rate': 0.0,
                'average_quality': 0.0,
                'average_latency_ms': 0.0,
                'error': str(e)
            }
