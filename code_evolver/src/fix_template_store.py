"""
Fix Template Store - Save and reuse successful bug/performance fixes.

When a bug or performance issue is fixed, save:
1. The data that helped fix it (with embedding)
2. The fix as a reusable tool/template
3. Pattern matching for future similar issues

Uses RAG/vector search to find similar issues and apply template fixes.
"""
import logging
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FixTemplate:
    """
    Represents a successful fix that can be reused.

    Contains:
    - Problem description and data
    - Fix implementation
    - Conditions for when to apply
    - Embedding for similarity search
    """

    def __init__(
        self,
        template_id: str,
        problem_type: str,  # 'bug' or 'perf'
        tool_name: str,
        problem_description: str,
        problem_data: Dict[str, Any],
        fix_description: str,
        fix_implementation: str,
        conditions: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize fix template.

        Args:
            template_id: Unique template ID
            problem_type: Type of problem (bug/perf)
            tool_name: Name of the tool that was fixed
            problem_description: Human-readable problem description
            problem_data: Data that helped identify the issue
            fix_description: Human-readable fix description
            fix_implementation: Code/configuration for the fix
            conditions: Conditions for when to apply this fix
            metadata: Additional metadata
        """
        self.template_id = template_id
        self.problem_type = problem_type
        self.tool_name = tool_name
        self.problem_description = problem_description
        self.problem_data = problem_data
        self.fix_description = fix_description
        self.fix_implementation = fix_implementation
        self.conditions = conditions
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.applied_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'template_id': self.template_id,
            'problem_type': self.problem_type,
            'tool_name': self.tool_name,
            'problem_description': self.problem_description,
            'problem_data': self.problem_data,
            'fix_description': self.fix_description,
            'fix_implementation': self.fix_implementation,
            'conditions': self.conditions,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'applied_count': self.applied_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FixTemplate':
        """Create from dictionary."""
        template = cls(
            template_id=data['template_id'],
            problem_type=data['problem_type'],
            tool_name=data['tool_name'],
            problem_description=data['problem_description'],
            problem_data=data['problem_data'],
            fix_description=data['fix_description'],
            fix_implementation=data['fix_implementation'],
            conditions=data['conditions'],
            metadata=data.get('metadata', {})
        )
        template.created_at = data.get('created_at', template.created_at)
        template.applied_count = data.get('applied_count', 0)
        return template

    def matches_problem(self, problem: Dict[str, Any]) -> bool:
        """
        Check if this template matches a given problem.

        Args:
            problem: Problem description (exception or perf data)

        Returns:
            True if template applies to this problem
        """
        # Check problem type
        if problem.get('type') != self.problem_type:
            return False

        # Check tool name (if specified in conditions)
        if 'tool_name' in self.conditions:
            if problem.get('tool_name') != self.conditions['tool_name']:
                return False

        # Check exception type (for bugs)
        if self.problem_type == 'bug':
            if 'exception_type' in self.conditions:
                if problem.get('exception_type') != self.conditions['exception_type']:
                    return False

        # Check variance threshold (for perf)
        if self.problem_type == 'perf':
            if 'min_variance' in self.conditions:
                if problem.get('variance', 0) < self.conditions['min_variance']:
                    return False

        return True

    def get_embedding_text(self) -> str:
        """
        Get text representation for embedding.

        Returns:
            Text to embed for similarity search
        """
        parts = [
            f"Problem Type: {self.problem_type}",
            f"Tool: {self.tool_name}",
            f"Description: {self.problem_description}",
            f"Fix: {self.fix_description}"
        ]

        # Add problem-specific details
        if self.problem_type == 'bug':
            if 'exception_type' in self.problem_data:
                parts.append(f"Exception: {self.problem_data['exception_type']}")
            if 'exception_message' in self.problem_data:
                parts.append(f"Message: {self.problem_data['exception_message']}")

        elif self.problem_type == 'perf':
            if 'optimization_type' in self.metadata:
                parts.append(f"Optimization: {self.metadata['optimization_type']}")

        return " | ".join(parts)


class FixTemplateStore:
    """
    Stores and retrieves fix templates using RAG/vector search.

    Saves successful fixes with embeddings for similarity matching.
    """

    def __init__(
        self,
        storage_path: str = "./fix_templates",
        use_qdrant: bool = True,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "fix_templates"
    ):
        """
        Initialize fix template store.

        Args:
            storage_path: Path to store template files
            use_qdrant: Whether to use Qdrant for vector search
            qdrant_url: Qdrant instance URL
            collection_name: Qdrant collection name
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.use_qdrant = use_qdrant
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name

        # Load templates from disk
        self.templates: Dict[str, FixTemplate] = {}
        self._load_templates()

        # Initialize Qdrant if enabled
        if self.use_qdrant:
            self._init_qdrant()

    def _load_templates(self):
        """Load templates from disk."""
        for template_file in self.storage_path.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    data = json.load(f)
                template = FixTemplate.from_dict(data)
                self.templates[template.template_id] = template
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")

    def _init_qdrant(self):
        """Initialize Qdrant collection."""
        try:
            from .qdrant_rag_memory import QdrantRAGMemory

            self.qdrant = QdrantRAGMemory(
                url=self.qdrant_url,
                collection_name=self.collection_name,
                vector_size=768  # nomic-embed-text size
            )

            logger.info(f"Initialized Qdrant for fix templates: {self.collection_name}")

        except Exception as e:
            logger.warning(f"Failed to initialize Qdrant: {e}")
            self.use_qdrant = False

    def save_fix_template(
        self,
        problem_type: str,
        tool_name: str,
        problem_description: str,
        problem_data: Dict[str, Any],
        fix_description: str,
        fix_implementation: str,
        conditions: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FixTemplate:
        """
        Save a successful fix as a reusable template.

        Args:
            problem_type: Type of problem (bug/perf)
            tool_name: Name of the tool that was fixed
            problem_description: Human-readable problem description
            problem_data: Data that helped fix the issue
            fix_description: Human-readable fix description
            fix_implementation: Code/configuration for the fix
            conditions: Conditions for when to apply
            metadata: Additional metadata

        Returns:
            Created FixTemplate
        """
        # Generate template ID
        template_id = self._generate_template_id(
            problem_type, tool_name, problem_description
        )

        # Create template
        template = FixTemplate(
            template_id=template_id,
            problem_type=problem_type,
            tool_name=tool_name,
            problem_description=problem_description,
            problem_data=problem_data,
            fix_description=fix_description,
            fix_implementation=fix_implementation,
            conditions=conditions or {},
            metadata=metadata or {}
        )

        # Save to memory
        self.templates[template_id] = template

        # Save to disk
        template_file = self.storage_path / f"{template_id}.json"
        with open(template_file, 'w') as f:
            json.dump(template.to_dict(), f, indent=2)

        # Save to Qdrant with embedding
        if self.use_qdrant:
            self._store_in_qdrant(template)

        logger.info(f"Saved fix template: {template_id}")

        return template

    def _generate_template_id(
        self,
        problem_type: str,
        tool_name: str,
        problem_description: str
    ) -> str:
        """Generate unique template ID."""
        content = f"{problem_type}:{tool_name}:{problem_description}"
        hash_digest = hashlib.sha256(content.encode()).hexdigest()
        return f"{problem_type}_{tool_name}_{hash_digest[:8]}"

    def _store_in_qdrant(self, template: FixTemplate):
        """Store template in Qdrant with embedding."""
        try:
            embedding_text = template.get_embedding_text()

            # Store in Qdrant
            self.qdrant.store(
                content=embedding_text,
                metadata={
                    'template_id': template.template_id,
                    'problem_type': template.problem_type,
                    'tool_name': template.tool_name,
                    'created_at': template.created_at
                },
                doc_id=template.template_id
            )

        except Exception as e:
            logger.error(f"Failed to store template in Qdrant: {e}")

    def find_similar_fixes(
        self,
        problem: Dict[str, Any],
        top_k: int = 5
    ) -> List[FixTemplate]:
        """
        Find similar fixes using vector similarity search.

        Args:
            problem: Problem description (exception or perf data)
            top_k: Number of similar fixes to return

        Returns:
            List of similar FixTemplate objects
        """
        if not self.use_qdrant:
            # Fallback: rule-based matching
            return self._find_matching_templates(problem)

        try:
            # Build query text
            query_parts = [
                f"Problem Type: {problem.get('type', 'unknown')}",
                f"Tool: {problem.get('tool_name', 'unknown')}"
            ]

            if problem.get('type') == 'bug':
                if 'exception_type' in problem:
                    query_parts.append(f"Exception: {problem['exception_type']}")
                if 'exception_message' in problem:
                    query_parts.append(f"Message: {problem['exception_message']}")

            elif problem.get('type') == 'perf':
                query_parts.append(f"Performance issue")

            query = " | ".join(query_parts)

            # Search Qdrant
            results = self.qdrant.search(query, top_k=top_k)

            # Get templates
            templates = []
            for result in results:
                template_id = result.get('metadata', {}).get('template_id')
                if template_id and template_id in self.templates:
                    templates.append(self.templates[template_id])

            return templates

        except Exception as e:
            logger.error(f"Failed to search Qdrant: {e}")
            return self._find_matching_templates(problem)

    def _find_matching_templates(
        self,
        problem: Dict[str, Any]
    ) -> List[FixTemplate]:
        """
        Find matching templates using rule-based matching.

        Fallback when Qdrant is unavailable.

        Args:
            problem: Problem description

        Returns:
            List of matching templates
        """
        matching = []
        for template in self.templates.values():
            if template.matches_problem(problem):
                matching.append(template)

        # Sort by applied_count (most successful first)
        return sorted(matching, key=lambda t: t.applied_count, reverse=True)

    def apply_template(
        self,
        template_id: str,
        tool_name: str
    ) -> Dict[str, Any]:
        """
        Apply a fix template to a tool.

        Args:
            template_id: ID of the template to apply
            tool_name: Name of the tool to fix

        Returns:
            Result with fix implementation and instructions
        """
        if template_id not in self.templates:
            return {'error': f'Template {template_id} not found'}

        template = self.templates[template_id]

        # Increment applied count
        template.applied_count += 1

        # Save updated template
        template_file = self.storage_path / f"{template_id}.json"
        with open(template_file, 'w') as f:
            json.dump(template.to_dict(), f, indent=2)

        # Return fix instructions
        return {
            'success': True,
            'template_id': template_id,
            'tool_name': tool_name,
            'fix_description': template.fix_description,
            'fix_implementation': template.fix_implementation,
            'conditions': template.conditions,
            'applied_count': template.applied_count
        }

    def get_template_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored templates.

        Returns:
            Dict with template statistics
        """
        bug_templates = [t for t in self.templates.values() if t.problem_type == 'bug']
        perf_templates = [t for t in self.templates.values() if t.problem_type == 'perf']

        return {
            'total_templates': len(self.templates),
            'bug_templates': len(bug_templates),
            'perf_templates': len(perf_templates),
            'most_applied': sorted(
                self.templates.values(),
                key=lambda t: t.applied_count,
                reverse=True
            )[:5],
            'by_tool': self._count_by_tool()
        }

    def _count_by_tool(self) -> Dict[str, int]:
        """Count templates by tool name."""
        counts = {}
        for template in self.templates.values():
            tool = template.tool_name
            counts[tool] = counts.get(tool, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


# Global instance
_global_fix_store: Optional[FixTemplateStore] = None


def get_fix_template_store() -> FixTemplateStore:
    """
    Get the global fix template store.

    Returns:
        FixTemplateStore singleton
    """
    global _global_fix_store

    if _global_fix_store is None:
        _global_fix_store = FixTemplateStore()

    return _global_fix_store


def save_bug_fix(
    tool_name: str,
    exception_data: Dict[str, Any],
    fix_implementation: str,
    fix_description: str
) -> FixTemplate:
    """
    Convenience function to save a bug fix template.

    Args:
        tool_name: Name of the tool
        exception_data: Exception data from BugCatcher
        fix_implementation: Code for the fix
        fix_description: Human-readable fix description

    Returns:
        Created FixTemplate
    """
    store = get_fix_template_store()

    return store.save_fix_template(
        problem_type='bug',
        tool_name=tool_name,
        problem_description=f"{exception_data.get('exception_type')}: {exception_data.get('exception_message')}",
        problem_data=exception_data,
        fix_description=fix_description,
        fix_implementation=fix_implementation,
        conditions={
            'tool_name': tool_name,
            'exception_type': exception_data.get('exception_type')
        }
    )


def save_perf_optimization(
    tool_name: str,
    perf_data: Dict[str, Any],
    optimization_implementation: str,
    optimization_description: str,
    optimization_type: str
) -> FixTemplate:
    """
    Convenience function to save a performance optimization template.

    Args:
        tool_name: Name of the tool
        perf_data: Performance data from PerfCatcher
        optimization_implementation: Code for the optimization
        optimization_description: Human-readable description
        optimization_type: Type of optimization (caching, scaling, etc.)

    Returns:
        Created FixTemplate
    """
    store = get_fix_template_store()

    return store.save_fix_template(
        problem_type='perf',
        tool_name=tool_name,
        problem_description=f"Performance variance {perf_data.get('variance', 0):.1%}",
        problem_data=perf_data,
        fix_description=optimization_description,
        fix_implementation=optimization_implementation,
        conditions={
            'tool_name': tool_name,
            'min_variance': perf_data.get('variance', 0) * 0.8  # Apply if 80%+ of original variance
        },
        metadata={
            'optimization_type': optimization_type
        }
    )
