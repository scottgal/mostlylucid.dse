"""
Version Replacement System - Automatically replaces old versions with closest fit.

Enables safe trimming of old versions by automatically updating dependent workflows
to use the closest available version (usually the strongest/best version).
"""
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class VersionReplacementManager:
    """
    Manages automatic version replacement during trimming.

    When an old version is trimmed, this manager:
    1. Finds all workflows that depend on the old version
    2. Determines the closest/best replacement version
    3. Updates workflows to use the replacement version
    4. Records the replacement for audit purposes
    """

    def __init__(self, registry, config_manager):
        """
        Initialize version replacement manager.

        Args:
            registry: Registry instance for accessing node/tool definitions
            config_manager: ConfigManager instance
        """
        self.registry = registry
        self.config = config_manager
        self.replacement_log: List[Dict[str, Any]] = []

    def find_dependent_workflows(
        self,
        artifact_id: str,
        version: str
    ) -> List[Dict[str, Any]]:
        """
        Find all workflows that depend on a specific artifact version.

        Args:
            artifact_id: ID of the artifact
            version: Version string (e.g., "1.2.0")

        Returns:
            List of workflow definitions that use this artifact version
        """
        dependent_workflows = []

        # Get all workflows from registry
        all_workflows = self.registry.list_workflows() if hasattr(self.registry, 'list_workflows') else []

        # Search for references to the artifact
        versioned_id = f"{artifact_id}_v{version.replace('.', '_')}"
        base_id = artifact_id

        for workflow in all_workflows:
            # Check workflow definition for references
            workflow_content = self.registry.get_workflow(workflow.get("workflow_id"))

            if self._contains_reference(workflow_content, base_id, versioned_id):
                dependent_workflows.append(workflow)

        logger.info(f"Found {len(dependent_workflows)} workflows depending on {artifact_id} v{version}")

        return dependent_workflows

    def _contains_reference(
        self,
        content: Any,
        base_id: str,
        versioned_id: str
    ) -> bool:
        """
        Check if content contains a reference to an artifact.

        Args:
            content: Workflow content (dict, string, etc.)
            base_id: Base artifact ID
            versioned_id: Versioned artifact ID

        Returns:
            True if content references the artifact
        """
        # Convert to string for searching
        content_str = str(content)

        # Check for both versioned and base IDs
        return base_id in content_str or versioned_id in content_str

    def find_closest_replacement(
        self,
        artifact_id: str,
        old_version: str,
        prefer_strongest: bool = True
    ) -> Optional[Tuple[str, str]]:
        """
        Find the closest/best replacement version for an artifact.

        Args:
            artifact_id: Base artifact ID
            old_version: Version being replaced
            prefer_strongest: If True, prefer highest quality score; if False, prefer latest

        Returns:
            Tuple of (replacement_version, replacement_id) or None if no replacement found
        """
        # Get all versions of this artifact
        all_nodes = self.registry.list_nodes()

        # Filter to get all versions of this artifact
        artifact_versions = []
        base_id = artifact_id.split("_v")[0]  # Remove version suffix if present

        for node in all_nodes:
            node_id = node.get("node_id", "")
            if node_id.startswith(base_id):
                artifact_versions.append(node)

        if not artifact_versions:
            logger.warning(f"No versions found for {artifact_id}")
            return None

        # Sort by quality score (descending) or by version
        if prefer_strongest:
            # Sort by quality score (highest first)
            artifact_versions.sort(key=lambda x: x.get("score_overall", 0), reverse=True)
            replacement = artifact_versions[0]
            logger.info(f"Selected strongest version: {replacement.get('node_id')} "
                       f"(score={replacement.get('score_overall', 0):.2f})")
        else:
            # Sort by version (latest first)
            artifact_versions.sort(
                key=lambda x: self._parse_version(x.get("version", "0.0.0")),
                reverse=True
            )
            replacement = artifact_versions[0]
            logger.info(f"Selected latest version: {replacement.get('node_id')} "
                       f"(v{replacement.get('version', 'unknown')})")

        return (replacement.get("version"), replacement.get("node_id"))

    def _parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """
        Parse version string into tuple for comparison.

        Args:
            version_str: Version string (e.g., "1.2.3")

        Returns:
            Tuple of (major, minor, patch)
        """
        try:
            parts = version_str.split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return (major, minor, patch)
        except (ValueError, IndexError):
            return (0, 0, 0)

    def replace_version_in_workflow(
        self,
        workflow_id: str,
        old_artifact_id: str,
        new_artifact_id: str
    ) -> bool:
        """
        Replace old artifact version with new version in a workflow.

        Args:
            workflow_id: Workflow to update
            old_artifact_id: Old artifact ID to replace
            new_artifact_id: New artifact ID to use

        Returns:
            True if replacement was successful
        """
        try:
            # Get workflow definition
            workflow = self.registry.get_workflow(workflow_id)

            if not workflow:
                logger.error(f"Workflow not found: {workflow_id}")
                return False

            # Replace references (this depends on workflow structure)
            updated = self._replace_references(workflow, old_artifact_id, new_artifact_id)

            if updated:
                # Save updated workflow
                self.registry.update_workflow(workflow_id, workflow)
                logger.info(f"Updated {workflow_id}: {old_artifact_id} → {new_artifact_id}")
                return True
            else:
                logger.warning(f"No replacements made in {workflow_id}")
                return False

        except Exception as e:
            logger.error(f"Error replacing version in {workflow_id}: {e}")
            return False

    def _replace_references(
        self,
        content: Any,
        old_id: str,
        new_id: str
    ) -> bool:
        """
        Replace references in content (recursively for dicts/lists).

        Args:
            content: Content to update (dict, list, string, etc.)
            old_id: Old artifact ID
            new_id: New artifact ID

        Returns:
            True if any replacements were made
        """
        replaced = False

        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, str) and old_id in value:
                    content[key] = value.replace(old_id, new_id)
                    replaced = True
                elif isinstance(value, (dict, list)):
                    if self._replace_references(value, old_id, new_id):
                        replaced = True

        elif isinstance(content, list):
            for i, item in enumerate(content):
                if isinstance(item, str) and old_id in item:
                    content[i] = item.replace(old_id, new_id)
                    replaced = True
                elif isinstance(item, (dict, list)):
                    if self._replace_references(item, old_id, new_id):
                        replaced = True

        return replaced

    def auto_replace_on_trim(
        self,
        artifact_id: str,
        version: str,
        prefer_strongest: bool = True
    ) -> Dict[str, Any]:
        """
        Automatically replace an artifact version when trimming.

        Args:
            artifact_id: Artifact being trimmed
            version: Version being trimmed
            prefer_strongest: Prefer strongest version over latest

        Returns:
            Dictionary with replacement results
        """
        logger.info(f"Auto-replacing {artifact_id} v{version} before trimming...")

        # Find replacement
        replacement = self.find_closest_replacement(artifact_id, version, prefer_strongest)

        if not replacement:
            logger.error(f"No replacement found for {artifact_id} v{version}")
            return {
                "success": False,
                "error": "No replacement version available"
            }

        replacement_version, replacement_id = replacement

        # Find dependent workflows
        dependents = self.find_dependent_workflows(artifact_id, version)

        if not dependents:
            logger.info(f"No dependent workflows found for {artifact_id} v{version}")
            return {
                "success": True,
                "replacement_id": replacement_id,
                "replacement_version": replacement_version,
                "updated_workflows": []
            }

        # Update each dependent workflow
        updated_workflows = []
        failed_workflows = []

        versioned_id = f"{artifact_id}_v{version.replace('.', '_')}"

        for workflow in dependents:
            workflow_id = workflow.get("workflow_id")

            success = self.replace_version_in_workflow(
                workflow_id,
                versioned_id,
                replacement_id
            )

            if success:
                updated_workflows.append(workflow_id)
            else:
                failed_workflows.append(workflow_id)

        # Record in log
        log_entry = {
            "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z",
            "artifact_id": artifact_id,
            "old_version": version,
            "replacement_id": replacement_id,
            "replacement_version": replacement_version,
            "updated_workflows": updated_workflows,
            "failed_workflows": failed_workflows
        }
        self.replacement_log.append(log_entry)

        logger.info(f"Replacement complete: {len(updated_workflows)} workflows updated, "
                   f"{len(failed_workflows)} failed")

        return {
            "success": len(failed_workflows) == 0,
            "replacement_id": replacement_id,
            "replacement_version": replacement_version,
            "updated_workflows": updated_workflows,
            "failed_workflows": failed_workflows
        }

    def can_safely_trim(
        self,
        artifact_id: str,
        version: str
    ) -> Tuple[bool, str]:
        """
        Check if an artifact version can be safely trimmed.

        Args:
            artifact_id: Artifact to check
            version: Version to check

        Returns:
            Tuple of (can_trim, reason)
        """
        # Check if there's a replacement available
        replacement = self.find_closest_replacement(artifact_id, version)

        if not replacement:
            return False, "No replacement version available"

        # Check if there are dependent workflows
        dependents = self.find_dependent_workflows(artifact_id, version)

        if dependents:
            return True, f"Can trim after updating {len(dependents)} dependent workflows"
        else:
            return True, "No dependent workflows"
