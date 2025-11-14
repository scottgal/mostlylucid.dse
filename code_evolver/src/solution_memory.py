"""
Solution Memory System - Caches solutions and strategies for reuse.
Stores problem descriptions, strategies, and solutions for quick lookup.
Future: Will integrate with RAG system for semantic similarity search.
"""
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SolutionMemory:
    """
    In-memory and persistent storage for solutions and strategies.
    Enables reuse of known solutions for identical or similar problems.
    """

    def __init__(self, memory_path: str = "./memory"):
        """
        Initialize solution memory.

        Args:
            memory_path: Path to memory storage directory
        """
        self.memory_path = Path(memory_path)
        self.memory_path.mkdir(parents=True, exist_ok=True)

        self.index_path = self.memory_path / "index.json"
        self.solutions_path = self.memory_path / "solutions"
        self.solutions_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache for fast lookup
        self.cache: Dict[str, Dict[str, Any]] = {}

        self._load_index()

    def _load_index(self):
        """Load solution index into memory."""
        if not self.index_path.exists():
            self._save_index({})
            return

        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)

            # Load recent solutions into cache
            for solution_id, metadata in index.items():
                if len(self.cache) < 100:  # Keep top 100 in memory
                    solution = self._load_solution(solution_id)
                    if solution:
                        self.cache[solution_id] = solution

            logger.info(f"✓ Loaded {len(index)} solutions from memory")

        except Exception as e:
            logger.error(f"Error loading index: {e}")

    def _save_index(self, index: Dict[str, Any]):
        """Save solution index to disk."""
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def _load_solution(self, solution_id: str) -> Optional[Dict[str, Any]]:
        """Load a solution from disk."""
        solution_file = self.solutions_path / f"{solution_id}.json"

        if not solution_file.exists():
            return None

        try:
            with open(solution_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading solution {solution_id}: {e}")
            return None

    def _save_solution(self, solution_id: str, solution: Dict[str, Any]):
        """Save a solution to disk."""
        solution_file = self.solutions_path / f"{solution_id}.json"

        try:
            with open(solution_file, 'w', encoding='utf-8') as f:
                json.dump(solution, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving solution {solution_id}: {e}")

    def _hash_problem(self, description: str) -> str:
        """
        Create a hash of the problem description for quick lookup.

        Args:
            description: Problem description

        Returns:
            Hash string
        """
        # Normalize description
        normalized = description.lower().strip()
        normalized = ' '.join(normalized.split())  # Normalize whitespace

        # Create hash
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def store_solution(
        self,
        problem_description: str,
        strategy: str,
        code: str,
        node_id: str,
        tags: List[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        evaluation: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a solution in memory.

        Args:
            problem_description: Original problem description
            strategy: Overseer's strategy/approach
            code: Generated code solution
            node_id: Associated node ID
            tags: Problem tags for categorization
            metrics: Execution metrics
            evaluation: Evaluation results

        Returns:
            Solution ID
        """
        solution_id = self._hash_problem(problem_description)

        solution = {
            "solution_id": solution_id,
            "problem": problem_description,
            "strategy": strategy,
            "code": code,
            "node_id": node_id,
            "tags": tags or [],
            "metrics": metrics or {},
            "evaluation": evaluation or {},
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "reuse_count": 0
        }

        # Save to disk
        self._save_solution(solution_id, solution)

        # Update cache
        self.cache[solution_id] = solution

        # Update index
        self._update_index(solution_id, solution)

        logger.info(f"✓ Stored solution: {solution_id}")
        return solution_id

    def _update_index(self, solution_id: str, solution: Dict[str, Any]):
        """Update the index with solution metadata."""
        # Load current index
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {}

        # Add/update entry
        index[solution_id] = {
            "problem": solution["problem"][:100],
            "node_id": solution["node_id"],
            "tags": solution["tags"],
            "score": solution.get("evaluation", {}).get("score_overall", 0),
            "created_at": solution["created_at"],
            "reuse_count": solution.get("reuse_count", 0)
        }

        # Save index
        self._save_index(index)

    def find_exact(self, problem_description: str) -> Optional[Dict[str, Any]]:
        """
        Find an exact match for a problem.

        Args:
            problem_description: Problem description

        Returns:
            Solution dictionary or None
        """
        solution_id = self._hash_problem(problem_description)

        # Check cache first
        if solution_id in self.cache:
            logger.info(f"✓ Found exact match in cache: {solution_id}")
            self._increment_reuse(solution_id)
            return self.cache[solution_id]

        # Check disk
        solution = self._load_solution(solution_id)
        if solution:
            logger.info(f"✓ Found exact match on disk: {solution_id}")
            self.cache[solution_id] = solution
            self._increment_reuse(solution_id)
            return solution

        return None

    def _increment_reuse(self, solution_id: str):
        """Increment reuse counter for a solution."""
        solution = self.cache.get(solution_id) or self._load_solution(solution_id)
        if solution:
            solution["reuse_count"] = solution.get("reuse_count", 0) + 1
            solution["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self._save_solution(solution_id, solution)
            self.cache[solution_id] = solution

    def find_by_tags(self, tags: List[str], min_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find solutions by tags.

        Args:
            tags: List of tags to search for
            min_score: Minimum evaluation score

        Returns:
            List of matching solutions
        """
        matches = []

        # Load index
        if not self.index_path.exists():
            return matches

        with open(self.index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)

        # Find matches
        for solution_id, metadata in index.items():
            solution_tags = set(metadata.get("tags", []))
            search_tags = set(tags)

            # Check for tag overlap
            if solution_tags & search_tags:  # Intersection
                score = metadata.get("score", 0)
                if score >= min_score:
                    solution = self._load_solution(solution_id)
                    if solution:
                        matches.append(solution)

        # Sort by score
        matches.sort(key=lambda x: x.get("evaluation", {}).get("score_overall", 0), reverse=True)

        logger.info(f"✓ Found {len(matches)} solutions matching tags: {tags}")
        return matches

    def find_similar(self, problem_description: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        Find similar problems (placeholder for future RAG implementation).

        Args:
            problem_description: Problem description
            threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            List of similar solutions

        Note:
            Current implementation uses simple keyword matching.
            Future: Will use embeddings and vector similarity.
        """
        # Simple keyword-based similarity for now
        keywords = set(problem_description.lower().split())

        matches = []

        # Load index
        if not self.index_path.exists():
            return matches

        with open(self.index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)

        # Find similar problems
        for solution_id, metadata in index.items():
            problem = metadata.get("problem", "").lower()
            problem_keywords = set(problem.split())

            # Calculate simple similarity (Jaccard index)
            intersection = keywords & problem_keywords
            union = keywords | problem_keywords

            if len(union) > 0:
                similarity = len(intersection) / len(union)

                if similarity >= threshold:
                    solution = self._load_solution(solution_id)
                    if solution:
                        solution["similarity"] = similarity
                        matches.append(solution)

        # Sort by similarity
        matches.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        logger.info(f"✓ Found {len(matches)} similar solutions")
        return matches

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Statistics dictionary
        """
        if not self.index_path.exists():
            return {"total_solutions": 0}

        with open(self.index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)

        total_reuses = sum(m.get("reuse_count", 0) for m in index.values())
        avg_score = sum(m.get("score", 0) for m in index.values()) / len(index) if index else 0

        # Get tag distribution
        tag_counts = {}
        for metadata in index.values():
            for tag in metadata.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_solutions": len(index),
            "cached_solutions": len(self.cache),
            "total_reuses": total_reuses,
            "average_score": round(avg_score, 2),
            "tag_distribution": tag_counts
        }

    def clear_cache(self):
        """Clear in-memory cache."""
        self.cache.clear()
        logger.info("✓ Cache cleared")

    def prune_low_quality(self, min_score: float = 0.3):
        """
        Remove low-quality solutions.

        Args:
            min_score: Minimum score to keep
        """
        if not self.index_path.exists():
            return

        with open(self.index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)

        removed = 0
        new_index = {}

        for solution_id, metadata in index.items():
            if metadata.get("score", 0) >= min_score:
                new_index[solution_id] = metadata
            else:
                # Remove solution file
                solution_file = self.solutions_path / f"{solution_id}.json"
                if solution_file.exists():
                    solution_file.unlink()
                removed += 1

        self._save_index(new_index)
        logger.info(f"✓ Pruned {removed} low-quality solutions")
