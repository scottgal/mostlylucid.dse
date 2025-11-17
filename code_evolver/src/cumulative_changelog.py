"""
Cumulative changelog system for tracking mutations across evolution lineage.

Maintains a history of all mutations for up to the last 10 ancestors to help
avoid repeating the same mistakes during evolution.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MutationEntry:
    """Represents a single mutation in the changelog."""

    def __init__(
        self,
        artifact_id: str,
        version: str,
        parent_id: Optional[str],
        mutation_type: str,
        changes_description: str,
        success: bool,
        quality_before: Optional[float] = None,
        quality_after: Optional[float] = None,
        test_changes: Optional[str] = None,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.artifact_id = artifact_id
        self.version = version
        self.parent_id = parent_id
        self.mutation_type = mutation_type
        self.changes_description = changes_description
        self.success = success
        self.quality_before = quality_before
        self.quality_after = quality_after
        self.test_changes = test_changes
        self.timestamp = timestamp or datetime.now().isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "artifact_id": self.artifact_id,
            "version": self.version,
            "parent_id": self.parent_id,
            "mutation_type": self.mutation_type,
            "changes_description": self.changes_description,
            "success": self.success,
            "quality_before": self.quality_before,
            "quality_after": self.quality_after,
            "test_changes": self.test_changes,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MutationEntry':
        """Create from dictionary."""
        return cls(
            artifact_id=data["artifact_id"],
            version=data["version"],
            parent_id=data.get("parent_id"),
            mutation_type=data["mutation_type"],
            changes_description=data["changes_description"],
            success=data["success"],
            quality_before=data.get("quality_before"),
            quality_after=data.get("quality_after"),
            test_changes=data.get("test_changes"),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {})
        )


class CumulativeChangelog:
    """
    Manages cumulative changelog for artifact evolution.

    Tracks mutations for the last 10 ancestors to prevent repeating mistakes
    and guide future evolution attempts.
    """

    def __init__(self, storage_dir: str = "evolution_logs"):
        """
        Initialize the cumulative changelog.

        Args:
            storage_dir: Directory to store changelog files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True, parents=True)
        self._cache: Dict[str, List[MutationEntry]] = {}

    def _get_changelog_path(self, artifact_id: str) -> Path:
        """Get the path to the changelog file for an artifact."""
        # Use base artifact ID (without version) for the file
        base_id = artifact_id.split("_v")[0]
        return self.storage_dir / f"{base_id}_changelog.json"

    def record_mutation(
        self,
        artifact_id: str,
        version: str,
        parent_id: Optional[str],
        mutation_type: str,
        changes_description: str,
        success: bool,
        quality_before: Optional[float] = None,
        quality_after: Optional[float] = None,
        test_changes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a mutation in the changelog.

        Args:
            artifact_id: ID of the artifact
            version: Version of the artifact
            parent_id: ID of the parent artifact
            mutation_type: Type of mutation (e.g., "optimization", "bug_fix", "feature_add")
            changes_description: Description of what changed
            success: Whether the mutation was successful
            quality_before: Quality score before mutation
            quality_after: Quality score after mutation
            test_changes: Description of test changes
            metadata: Additional metadata
        """
        entry = MutationEntry(
            artifact_id=artifact_id,
            version=version,
            parent_id=parent_id,
            mutation_type=mutation_type,
            changes_description=changes_description,
            success=success,
            quality_before=quality_before,
            quality_after=quality_after,
            test_changes=test_changes,
            metadata=metadata
        )

        changelog_path = self._get_changelog_path(artifact_id)

        # Load existing changelog
        changelog = []
        if changelog_path.exists():
            try:
                with open(changelog_path, 'r') as f:
                    data = json.load(f)
                    changelog = [MutationEntry.from_dict(e) for e in data]
            except Exception as e:
                logger.error(f"Error loading changelog from {changelog_path}: {e}")

        # Add new entry
        changelog.append(entry)

        # Keep only last 10 entries (configurable if needed)
        changelog = changelog[-10:]

        # Save
        try:
            with open(changelog_path, 'w') as f:
                json.dump([e.to_dict() for e in changelog], f, indent=2)

            # Update cache
            self._cache[artifact_id] = changelog

            logger.info(f"Recorded mutation for {artifact_id} v{version}: {mutation_type}")
        except Exception as e:
            logger.error(f"Error saving changelog to {changelog_path}: {e}")

    def get_ancestor_mutations(
        self,
        artifact_id: str,
        max_ancestors: int = 10
    ) -> List[MutationEntry]:
        """
        Get mutations for the last N ancestors.

        Args:
            artifact_id: ID of the artifact
            max_ancestors: Maximum number of ancestors to retrieve

        Returns:
            List of mutation entries for ancestors
        """
        changelog_path = self._get_changelog_path(artifact_id)

        if not changelog_path.exists():
            return []

        # Check cache first
        if artifact_id in self._cache:
            return self._cache[artifact_id][-max_ancestors:]

        # Load from disk
        try:
            with open(changelog_path, 'r') as f:
                data = json.load(f)
                changelog = [MutationEntry.from_dict(e) for e in data]
                self._cache[artifact_id] = changelog
                return changelog[-max_ancestors:]
        except Exception as e:
            logger.error(f"Error loading changelog from {changelog_path}: {e}")
            return []

    def get_failed_mutations(self, artifact_id: str) -> List[MutationEntry]:
        """Get all failed mutations for an artifact."""
        mutations = self.get_ancestor_mutations(artifact_id)
        return [m for m in mutations if not m.success]

    def get_successful_mutations(self, artifact_id: str) -> List[MutationEntry]:
        """Get all successful mutations for an artifact."""
        mutations = self.get_ancestor_mutations(artifact_id)
        return [m for m in mutations if m.success]

    def format_for_evolution_prompt(self, artifact_id: str) -> str:
        """
        Format the changelog into a prompt section for evolution guidance.

        Args:
            artifact_id: ID of the artifact

        Returns:
            Formatted string for inclusion in evolution prompts
        """
        mutations = self.get_ancestor_mutations(artifact_id)

        if not mutations:
            return "No previous evolution history available."

        lines = [
            "## Evolution History (Last 10 Ancestors)",
            "",
            "The following mutations have been attempted on this artifact lineage.",
            "Use this history to avoid repeating mistakes and build on successes:",
            ""
        ]

        # Separate successful and failed mutations
        successful = [m for m in mutations if m.success]
        failed = [m for m in mutations if not m.success]

        if successful:
            lines.append("### Successful Mutations:")
            for i, mutation in enumerate(successful, 1):
                quality_change = ""
                if mutation.quality_before is not None and mutation.quality_after is not None:
                    delta = mutation.quality_after - mutation.quality_before
                    quality_change = f" (quality: {mutation.quality_before:.2f} → {mutation.quality_after:.2f}, Δ{delta:+.2f})"

                lines.append(f"{i}. **{mutation.mutation_type}** (v{mutation.version}){quality_change}")
                lines.append(f"   - Changes: {mutation.changes_description}")
                if mutation.test_changes:
                    lines.append(f"   - Test changes: {mutation.test_changes}")
                lines.append(f"   - Date: {mutation.timestamp}")
                lines.append("")

        if failed:
            lines.append("### ⚠️ Failed Mutations (AVOID THESE APPROACHES):")
            for i, mutation in enumerate(failed, 1):
                lines.append(f"{i}. **{mutation.mutation_type}** (v{mutation.version})")
                lines.append(f"   - Attempted: {mutation.changes_description}")
                if mutation.metadata.get('failure_reason'):
                    lines.append(f"   - Failure reason: {mutation.metadata['failure_reason']}")
                lines.append(f"   - Date: {mutation.timestamp}")
                lines.append("")

        return "\n".join(lines)

    def get_test_evolution_context(self, artifact_id: str) -> Dict[str, Any]:
        """
        Get test evolution context for improving test coverage.

        Args:
            artifact_id: ID of the artifact

        Returns:
            Dictionary with test evolution insights
        """
        mutations = self.get_ancestor_mutations(artifact_id)

        test_changes = []
        coverage_trends = []

        for mutation in mutations:
            if mutation.test_changes:
                test_changes.append({
                    "version": mutation.version,
                    "changes": mutation.test_changes,
                    "success": mutation.success,
                    "quality_after": mutation.quality_after
                })

            if mutation.metadata.get('test_coverage'):
                coverage_trends.append({
                    "version": mutation.version,
                    "coverage": mutation.metadata['test_coverage']
                })

        return {
            "test_changes": test_changes,
            "coverage_trends": coverage_trends,
            "latest_coverage": coverage_trends[-1]['coverage'] if coverage_trends else None
        }

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()

    def export_lineage(self, artifact_id: str) -> Dict[str, Any]:
        """Export complete lineage for an artifact."""
        mutations = self.get_ancestor_mutations(artifact_id)

        return {
            "artifact_id": artifact_id,
            "total_mutations": len(mutations),
            "successful_count": len([m for m in mutations if m.success]),
            "failed_count": len([m for m in mutations if not m.success]),
            "mutations": [m.to_dict() for m in mutations]
        }
