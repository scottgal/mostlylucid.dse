"""
Pattern Clustering and Optimization

Analyzes RAG memory to find clusters of similar operations and suggests
parameterized tools for optimization.

This implements SRP (Single Responsibility Principle) optimization by:
1. Finding clusters of similar operations (e.g., "translate to French", "translate to Spanish")
2. Suggesting parameterized tools (e.g., translate(text, target_language))
3. Refactoring workflows to use reusable components
"""

import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class OperationCluster:
    """Represents a cluster of similar operations"""
    cluster_id: int
    operation_type: str
    artifacts: List[Any]
    centroid: np.ndarray
    similarity_score: float
    suggested_tool_name: str
    suggested_parameters: List[str]
    example_operations: List[str]
    optimization_potential: float = 0.0


class PatternClusterer:
    """
    Analyzes RAG memory to find patterns and optimization opportunities.

    Uses multiple clustering algorithms:
    - K-means for general pattern discovery
    - DBSCAN for density-based anomaly detection
    - Hierarchical clustering for operation taxonomy
    """

    def __init__(self, rag_memory, min_cluster_size: int = 3, similarity_threshold: float = 0.75):
        """
        Initialize pattern clusterer.

        Args:
            rag_memory: RAG memory instance to analyze
            min_cluster_size: Minimum artifacts to form a cluster
            similarity_threshold: Minimum similarity to consider clustering
        """
        self.rag = rag_memory
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold

    def analyze_patterns(self, target_filter: Optional[str] = None) -> List[OperationCluster]:
        """
        Analyze all artifacts in RAG to find optimization opportunities.

        Args:
            target_filter: Optional target function/code to focus optimization pressure on.
                         Only artifacts containing this string will be analyzed.

        Returns:
            List of operation clusters with optimization suggestions
        """
        # Get all artifacts with embeddings
        all_artifacts = self.rag.get_all_artifacts()

        # Apply target filter if specified (optimization pressure)
        if target_filter:
            filtered_artifacts = []
            for artifact in all_artifacts:
                # Check if artifact description or content contains the target
                description = artifact.description.lower() if hasattr(artifact, 'description') else ""
                content = artifact.content.lower() if hasattr(artifact, 'content') else ""

                if target_filter.lower() in description or target_filter.lower() in content:
                    filtered_artifacts.append(artifact)

            all_artifacts = filtered_artifacts
            print(f"🎯 Applying optimization pressure to '{target_filter}'")
            print(f"   Filtered to {len(all_artifacts)} relevant artifacts\n")

        if len(all_artifacts) < self.min_cluster_size:
            print(f"Not enough artifacts ({len(all_artifacts)}) for clustering (need {self.min_cluster_size})")
            return []

        # Extract embeddings and descriptions
        embeddings = []
        artifacts = []

        for artifact in all_artifacts:
            if hasattr(artifact, 'embedding') and artifact.embedding is not None:
                embeddings.append(artifact.embedding)
                artifacts.append(artifact)

        if len(embeddings) < self.min_cluster_size:
            print(f"Not enough embeddings ({len(embeddings)}) for clustering")
            return []

        embeddings_array = np.array(embeddings)

        # Use simple similarity-based clustering (no sklearn needed)
        clusters = self._simple_similarity_clustering(embeddings_array, artifacts)

        # Filter out small clusters
        significant_clusters = [
            c for c in clusters
            if len(c.artifacts) >= self.min_cluster_size
        ]

        # Analyze each cluster for optimization opportunities
        optimized_clusters = []
        for cluster in significant_clusters:
            optimized = self._analyze_cluster_for_optimization(cluster)
            if optimized:
                optimized_clusters.append(optimized)

        return optimized_clusters

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors (no sklearn needed)."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _simple_similarity_clustering(
        self,
        embeddings: np.ndarray,
        artifacts: List[Any]
    ) -> List[OperationCluster]:
        """
        Simple similarity-based clustering without sklearn.

        Uses greedy algorithm:
        1. Find most similar pairs
        2. Merge them into clusters
        3. Continue until no more merges possible

        Args:
            embeddings: Array of embeddings
            artifacts: Corresponding artifacts

        Returns:
            List of operation clusters
        """
        n = len(embeddings)
        clusters_map = {i: [i] for i in range(n)}  # Each item starts in its own cluster
        cluster_centers = {i: embeddings[i].copy() for i in range(n)}

        # Greedy clustering: merge similar clusters
        merged = True
        while merged:
            merged = False
            best_similarity = self.similarity_threshold
            best_pair = None

            # Find best pair to merge
            cluster_ids = list(clusters_map.keys())
            for i in range(len(cluster_ids)):
                for j in range(i + 1, len(cluster_ids)):
                    id_i = cluster_ids[i]
                    id_j = cluster_ids[j]

                    # Calculate similarity between cluster centers
                    sim = self._cosine_similarity(cluster_centers[id_i], cluster_centers[id_j])

                    if sim > best_similarity:
                        best_similarity = sim
                        best_pair = (id_i, id_j)

            # Merge best pair
            if best_pair:
                id_i, id_j = best_pair
                # Merge j into i
                clusters_map[id_i].extend(clusters_map[id_j])

                # Update center (average of all embeddings in cluster)
                cluster_embeddings = embeddings[clusters_map[id_i]]
                cluster_centers[id_i] = cluster_embeddings.mean(axis=0)

                # Remove j
                del clusters_map[id_j]
                del cluster_centers[id_j]

                merged = True

        # Convert to OperationCluster objects
        operation_clusters = []

        for cluster_id, indices in clusters_map.items():
            if len(indices) < self.min_cluster_size:
                continue

            cluster_artifacts = [artifacts[i] for i in indices]
            cluster_embeddings = embeddings[indices]

            # Calculate average intra-cluster similarity
            avg_similarity = 0.0
            count = 0
            for i in range(len(cluster_embeddings)):
                for j in range(i + 1, len(cluster_embeddings)):
                    avg_similarity += self._cosine_similarity(
                        cluster_embeddings[i],
                        cluster_embeddings[j]
                    )
                    count += 1

            if count > 0:
                avg_similarity /= count
            else:
                avg_similarity = 1.0

            operation_type = self._infer_operation_type(cluster_artifacts)

            operation_clusters.append(OperationCluster(
                cluster_id=cluster_id,
                operation_type=operation_type,
                artifacts=cluster_artifacts,
                centroid=cluster_centers[cluster_id],
                similarity_score=float(avg_similarity),
                suggested_tool_name="",
                suggested_parameters=[],
                example_operations=[a.description[:100] for a in cluster_artifacts[:3]]
            ))

        return operation_clusters

    def _infer_operation_type(self, artifacts: List[Any]) -> str:
        """
        Infer the operation type from artifact descriptions.

        Args:
            artifacts: List of artifacts in cluster

        Returns:
            Operation type string
        """
        # Extract common words from descriptions
        descriptions = [a.description.lower() for a in artifacts]

        # Common operation keywords
        operation_keywords = {
            'translate': 'translation',
            'fetch': 'fetching',
            'process': 'processing',
            'parse': 'parsing',
            'validate': 'validation',
            'convert': 'conversion',
            'format': 'formatting',
            'extract': 'extraction',
            'transform': 'transformation',
            'filter': 'filtering',
            'sort': 'sorting',
            'aggregate': 'aggregation',
            'summarize': 'summarization',
            'analyze': 'analysis'
        }

        # Count keyword occurrences
        keyword_counts = defaultdict(int)
        for desc in descriptions:
            for keyword, op_type in operation_keywords.items():
                if keyword in desc:
                    keyword_counts[op_type] += 1

        if keyword_counts:
            return max(keyword_counts.items(), key=lambda x: x[1])[0]

        return "general_operation"

    def _analyze_cluster_for_optimization(self, cluster: OperationCluster) -> Optional[OperationCluster]:
        """
        Analyze a cluster to suggest parameterized tool optimization.

        Args:
            cluster: Operation cluster to analyze

        Returns:
            Optimized cluster with suggestions, or None if no optimization needed
        """
        # Only suggest optimization for high-similarity clusters
        if cluster.similarity_score < self.similarity_threshold:
            return None

        # Analyze descriptions to extract parameters
        parameters = self._extract_common_parameters(cluster.artifacts)

        if not parameters:
            return None

        # Generate tool name
        tool_name = self._generate_tool_name(cluster.operation_type, parameters)

        # Update cluster with suggestions
        cluster.suggested_tool_name = tool_name
        cluster.suggested_parameters = parameters

        # Calculate optimization potential
        cluster.optimization_potential = self._calculate_optimization_potential(cluster)

        return cluster

    def _extract_common_parameters(self, artifacts: List[Any]) -> List[str]:
        """
        Extract common parameters from artifact descriptions.

        Examples:
        - "translate to French", "translate to Spanish" → ["target_language"]
        - "fetch from URL", "fetch from API" → ["source"]
        - "format as JSON", "format as XML" → ["output_format"]

        Args:
            artifacts: List of artifacts

        Returns:
            List of parameter names
        """
        import re

        descriptions = [a.description.lower() for a in artifacts]

        parameters = []

        # Pattern 1: "to X" patterns (translate to X, convert to X)
        to_pattern = re.compile(r'to\s+(\w+)')
        to_values = []
        for desc in descriptions:
            matches = to_pattern.findall(desc)
            to_values.extend(matches)

        if len(set(to_values)) >= 2:  # Multiple different values
            # Infer parameter name from context
            if any(kw in ' '.join(descriptions) for kw in ['translate', 'language']):
                parameters.append('target_language')
            elif any(kw in ' '.join(descriptions) for kw in ['convert', 'format']):
                parameters.append('target_format')
            else:
                parameters.append('target')

        # Pattern 2: "from X" patterns (fetch from X, read from X)
        from_pattern = re.compile(r'from\s+(\w+)')
        from_values = []
        for desc in descriptions:
            matches = from_pattern.findall(desc)
            from_values.extend(matches)

        if len(set(from_values)) >= 2:
            if any(kw in ' '.join(descriptions) for kw in ['url', 'http', 'api', 'web']):
                parameters.append('source_url')
            else:
                parameters.append('source')

        # Pattern 3: "as X" patterns (format as X, output as X)
        as_pattern = re.compile(r'as\s+(\w+)')
        as_values = []
        for desc in descriptions:
            matches = as_pattern.findall(desc)
            as_values.extend(matches)

        if len(set(as_values)) >= 2:
            parameters.append('output_format')

        # Pattern 4: "using X" or "with X" patterns
        using_pattern = re.compile(r'(?:using|with)\s+(\w+)')
        using_values = []
        for desc in descriptions:
            matches = using_pattern.findall(desc)
            using_values.extend(matches)

        if len(set(using_values)) >= 2:
            parameters.append('method')

        return parameters

    def _generate_tool_name(self, operation_type: str, parameters: List[str]) -> str:
        """
        Generate a tool name based on operation type and parameters.

        Args:
            operation_type: Type of operation (e.g., "translation")
            parameters: List of parameter names

        Returns:
            Suggested tool name
        """
        # Convert operation type to verb form
        verb_map = {
            'translation': 'translate',
            'fetching': 'fetch',
            'processing': 'process',
            'parsing': 'parse',
            'validation': 'validate',
            'conversion': 'convert',
            'formatting': 'format',
            'extraction': 'extract',
            'transformation': 'transform',
            'filtering': 'filter',
            'sorting': 'sort',
            'aggregation': 'aggregate',
            'summarization': 'summarize',
            'analysis': 'analyze'
        }

        verb = verb_map.get(operation_type, operation_type.rstrip('ing'))

        # Add context from parameters
        if 'target_language' in parameters:
            return f"{verb}_text"
        elif 'source_url' in parameters:
            return f"{verb}_from_url"
        elif 'output_format' in parameters:
            return f"{verb}_as"
        else:
            return f"parameterized_{verb}"

    def generate_tool_definition(self, cluster: OperationCluster) -> Dict[str, Any]:
        """
        Generate a YAML tool definition from a cluster.

        Args:
            cluster: Operation cluster with optimization suggestions

        Returns:
            Tool definition dictionary
        """
        # Analyze artifacts to get implementation hints
        example_artifact = cluster.artifacts[0]

        # Determine if this should be an LLM tool or code tool
        is_llm_task = any(kw in cluster.operation_type for kw in
                         ['translation', 'summarization', 'analysis', 'generation'])

        if is_llm_task:
            tool_def = {
                'name': cluster.suggested_tool_name.replace('_', ' ').title(),
                'type': 'llm',
                'description': f"Performs {cluster.operation_type} with parameterized inputs",
                'llm': {
                    'model': 'llama3',  # Default, can be optimized
                    'endpoint': None  # Use default endpoint
                },
                'parameters': cluster.suggested_parameters,
                'tags': [cluster.operation_type, 'parameterized', 'optimized'],
                'examples': cluster.example_operations,
                'cluster_info': {
                    'cluster_id': cluster.cluster_id,
                    'similarity_score': cluster.similarity_score,
                    'artifact_count': len(cluster.artifacts)
                }
            }
        else:
            tool_def = {
                'name': cluster.suggested_tool_name.replace('_', ' ').title(),
                'type': 'code',
                'description': f"Performs {cluster.operation_type} with parameterized inputs",
                'parameters': cluster.suggested_parameters,
                'tags': [cluster.operation_type, 'parameterized', 'optimized'],
                'examples': cluster.example_operations,
                'cluster_info': {
                    'cluster_id': cluster.cluster_id,
                    'similarity_score': cluster.similarity_score,
                    'artifact_count': len(cluster.artifacts)
                }
            }

        return tool_def

    def save_optimization_report(self, clusters: List[OperationCluster], output_path: Path):
        """
        Save optimization report to file.

        Args:
            clusters: List of optimized clusters
            output_path: Path to save report
        """
        report = {
            'timestamp': str(Path(output_path).stat().st_mtime if output_path.exists() else 'N/A'),
            'total_clusters': len(clusters),
            'clusters': []
        }

        for cluster in clusters:
            cluster_info = {
                'cluster_id': cluster.cluster_id,
                'operation_type': cluster.operation_type,
                'artifact_count': len(cluster.artifacts),
                'similarity_score': cluster.similarity_score,
                'suggested_tool_name': cluster.suggested_tool_name,
                'suggested_parameters': cluster.suggested_parameters,
                'example_operations': cluster.example_operations,
                'optimization_potential': self._calculate_optimization_potential(cluster)
            }
            report['clusters'].append(cluster_info)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

    def _calculate_optimization_potential(self, cluster: OperationCluster) -> float:
        """
        Calculate optimization potential (0-1) based on cluster characteristics.

        Higher potential means more benefit from creating parameterized tool.

        Args:
            cluster: Operation cluster

        Returns:
            Optimization potential score (0-1)
        """
        # Factors:
        # 1. Number of artifacts (more = higher potential)
        # 2. Similarity score (higher = better candidate)
        # 3. Number of parameters (more = more flexible)

        artifact_score = min(len(cluster.artifacts) / 10, 1.0)  # Cap at 10 artifacts
        similarity_score = cluster.similarity_score
        parameter_score = min(len(cluster.suggested_parameters) / 3, 1.0)  # Cap at 3 params

        # Weighted average
        potential = (
            artifact_score * 0.4 +
            similarity_score * 0.4 +
            parameter_score * 0.2
        )

        return round(potential, 2)
