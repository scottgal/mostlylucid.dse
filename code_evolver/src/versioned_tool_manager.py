"""
Versioned Tool Manager - Enhanced Tool Manager with Version-Aware Lookups

This module extends the ToolsManager with:
1. Version-aware tool lookups (name + version)
2. Automatic cluster formation around versions
3. Best version selection based on fitness scores
4. Version compatibility checking

Supports calling tools like:
- get_tool("parse_cron", version="1.2.3")  # Exact version
- get_tool("parse_cron", version="1.2")     # Any patch in 1.2.x
- get_tool("parse_cron", version="latest")  # Highest version
- get_tool("parse_cron", version="best")    # Highest fitness score
"""

import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re

from .tools_manager import ToolsManager, Tool, ToolType
from .rag_memory import RAGMemory

logger = logging.getLogger(__name__)


class VersionedToolManager(ToolsManager):
    """
    Extended ToolsManager with version-aware capabilities.

    Maintains a version index for fast lookups and automatic clustering.
    """

    def __init__(self, registry_path: str = "registry"):
        """
        Initialize versioned tool manager.

        Args:
            registry_path: Path to tool registry
        """
        super().__init__(registry_path=registry_path)

        # Version index: tool_name -> {version -> Tool}
        self.version_index: Dict[str, Dict[str, Tool]] = {}

        # Build version index from existing tools
        self._build_version_index()

    def _build_version_index(self):
        """Build index of tools by name and version."""
        logger.info("Building version index...")

        for tool_id, tool in self.tools.items():
            base_name = self._extract_base_name(tool_id)
            version = tool.version

            if base_name not in self.version_index:
                self.version_index[base_name] = {}

            self.version_index[base_name][version] = tool

        logger.info(f"Indexed {len(self.version_index)} tools with versions")

    def _extract_base_name(self, tool_id: str) -> str:
        """
        Extract base name from tool_id (remove version suffix).

        Examples:
            parse_cron_v1.2.3 -> parse_cron
            parse_cron@1.2.3 -> parse_cron
            parse_cron -> parse_cron
        """
        # Remove version-like suffixes
        base = re.sub(r'[@_]v?\d+\.\d+.*$', '', tool_id)
        return base

    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool and update version index.

        Args:
            tool: Tool to register
        """
        # Call parent registration
        super().register_tool(tool)

        # Update version index
        base_name = self._extract_base_name(tool.tool_id)
        version = tool.version

        if base_name not in self.version_index:
            self.version_index[base_name] = {}

        self.version_index[base_name][version] = tool

        logger.debug(f"Registered {tool.tool_id} (v{version}) in version index")

    def get_tool_by_version(
        self,
        tool_name: str,
        version: Optional[str] = None,
        strategy: str = "best"
    ) -> Optional[Tool]:
        """
        Get a tool by name and version with flexible matching.

        Args:
            tool_name: Base tool name (without version)
            version: Version specification:
                - Exact version: "1.2.3"
                - Major.minor: "1.2" (any patch in 1.2.x)
                - "latest" (highest version number)
                - "best" (highest fitness score)
                - None (use strategy to select)
            strategy: Selection strategy when version is None:
                - "best" (default): Highest fitness score
                - "latest": Highest version number
                - "stable": Highest stable version (no pre-release)

        Returns:
            Tool matching the criteria, or None if not found
        """
        # Normalize tool name
        base_name = self._extract_base_name(tool_name)

        if base_name not in self.version_index:
            logger.warning(f"Tool '{base_name}' not found in version index")
            return None

        versions_dict = self.version_index[base_name]

        if not versions_dict:
            return None

        # Handle version specifications
        if version is None:
            version = strategy

        if version == "latest":
            return self._get_latest_version(versions_dict)
        elif version == "best":
            return self._get_best_version(versions_dict)
        elif version == "stable":
            return self._get_stable_version(versions_dict)
        elif "." in version:
            # Exact or prefix match
            return self._get_matching_version(versions_dict, version)
        else:
            logger.warning(f"Invalid version specification: {version}")
            return None

    def _get_latest_version(self, versions_dict: Dict[str, Tool]) -> Optional[Tool]:
        """Get tool with highest version number."""
        if not versions_dict:
            return None

        def version_key(version: str) -> Tuple[int, int, int]:
            try:
                parts = version.split('.')
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                return (0, 0, 0)

        latest_version = max(versions_dict.keys(), key=version_key)
        return versions_dict[latest_version]

    def _get_best_version(self, versions_dict: Dict[str, Tool]) -> Optional[Tool]:
        """Get tool with highest fitness score."""
        if not versions_dict:
            return None

        def fitness_key(tool: Tool) -> float:
            # Get fitness from metadata or usage count as proxy
            metadata = tool.metadata
            if 'fitness_score' in metadata:
                return metadata['fitness_score']
            elif 'quality_score' in metadata:
                return metadata['quality_score']
            else:
                # Use usage count as proxy for fitness
                return tool.usage_count / 100.0

        best_tool = max(versions_dict.values(), key=fitness_key)
        return best_tool

    def _get_stable_version(self, versions_dict: Dict[str, Tool]) -> Optional[Tool]:
        """Get highest stable version (no pre-release tags)."""
        stable_versions = {
            v: tool for v, tool in versions_dict.items()
            if not any(tag in v for tag in ['-alpha', '-beta', '-rc', '-dev'])
        }

        if not stable_versions:
            return None

        return self._get_latest_version(stable_versions)

    def _get_matching_version(
        self,
        versions_dict: Dict[str, Tool],
        version_spec: str
    ) -> Optional[Tool]:
        """
        Get tool matching version specification.

        Supports:
        - Exact: "1.2.3"
        - Prefix: "1.2" (matches 1.2.0, 1.2.1, etc.)
        """
        # Try exact match first
        if version_spec in versions_dict:
            return versions_dict[version_spec]

        # Try prefix match (e.g., "1.2" matches "1.2.0", "1.2.1", etc.)
        matching = [
            (v, tool) for v, tool in versions_dict.items()
            if v.startswith(version_spec + ".")
        ]

        if not matching:
            logger.warning(f"No tool found matching version {version_spec}")
            return None

        # Return latest matching version
        def version_key(item):
            version = item[0]
            try:
                parts = version.split('.')
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                return (0, 0, 0)

        return max(matching, key=version_key)[1]

    def get_version_cluster(self, tool_name: str) -> List[Tool]:
        """
        Get all versions of a tool (version cluster).

        Args:
            tool_name: Base tool name

        Returns:
            List of all tool versions, sorted by version number
        """
        base_name = self._extract_base_name(tool_name)

        if base_name not in self.version_index:
            return []

        versions_dict = self.version_index[base_name]

        def version_key(item):
            version = item[0]
            try:
                parts = version.split('.')
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                return (0, 0, 0)

        sorted_versions = sorted(versions_dict.items(), key=version_key, reverse=True)
        return [tool for _, tool in sorted_versions]

    def find_compatible_versions(
        self,
        tool_name: str,
        required_version: str,
        compatibility_mode: str = "patch"
    ) -> List[Tool]:
        """
        Find all compatible versions for a tool.

        Args:
            tool_name: Base tool name
            required_version: Required version (e.g., "1.2.3")
            compatibility_mode:
                - "patch": Compatible with same major.minor (1.2.x)
                - "minor": Compatible with same major (1.x.x)
                - "major": Any version

        Returns:
            List of compatible tools
        """
        base_name = self._extract_base_name(tool_name)

        if base_name not in self.version_index:
            return []

        try:
            req_parts = required_version.split('.')
            req_major = int(req_parts[0])
            req_minor = int(req_parts[1]) if len(req_parts) > 1 else 0
        except:
            logger.warning(f"Invalid version format: {required_version}")
            return []

        compatible = []

        for version, tool in self.version_index[base_name].items():
            try:
                parts = version.split('.')
                major = int(parts[0])
                minor = int(parts[1]) if len(parts) > 1 else 0

                if compatibility_mode == "patch":
                    if major == req_major and minor == req_minor:
                        compatible.append(tool)
                elif compatibility_mode == "minor":
                    if major == req_major:
                        compatible.append(tool)
                elif compatibility_mode == "major":
                    compatible.append(tool)

            except:
                continue

        return compatible

    def promote_to_prime(self, tool_id: str):
        """
        Promote a tool version to be the "prime" (best) in its cluster.

        Updates metadata to mark this as the canonical version.

        Args:
            tool_id: Tool ID to promote
        """
        tool = self.tools.get(tool_id)
        if not tool:
            logger.warning(f"Tool {tool_id} not found")
            return

        base_name = self._extract_base_name(tool_id)

        # Update metadata
        tool.metadata['is_prime'] = True
        tool.metadata['promoted_at'] = datetime.utcnow().isoformat() + "Z"

        # Mark others as non-prime
        if base_name in self.version_index:
            for version, other_tool in self.version_index[base_name].items():
                if other_tool.tool_id != tool_id:
                    other_tool.metadata['is_prime'] = False

        logger.info(f"Promoted {tool_id} to prime version of {base_name}")

        # Save updated tools
        self.save_to_json()

    def get_prime_version(self, tool_name: str) -> Optional[Tool]:
        """
        Get the prime (canonical) version of a tool.

        Args:
            tool_name: Base tool name

        Returns:
            Prime tool version, or None if no prime is marked
        """
        base_name = self._extract_base_name(tool_name)

        if base_name not in self.version_index:
            return None

        # Look for explicitly marked prime
        for version, tool in self.version_index[base_name].items():
            if tool.metadata.get('is_prime', False):
                return tool

        # Fall back to best version
        return self._get_best_version(self.version_index[base_name])

    def list_version_clusters(self) -> Dict[str, List[str]]:
        """
        List all version clusters in the registry.

        Returns:
            Dictionary mapping tool_name -> list of versions
        """
        clusters = {}

        for tool_name, versions_dict in self.version_index.items():
            versions = sorted(versions_dict.keys(), reverse=True)
            if len(versions) > 1:  # Only show clusters with multiple versions
                clusters[tool_name] = versions

        return clusters

    def get_cluster_stats(self, tool_name: str) -> Dict:
        """
        Get statistics for a version cluster.

        Args:
            tool_name: Base tool name

        Returns:
            Dictionary with cluster statistics
        """
        base_name = self._extract_base_name(tool_name)

        if base_name not in self.version_index:
            return {}

        versions_dict = self.version_index[base_name]
        tools = list(versions_dict.values())

        prime = self.get_prime_version(tool_name)
        latest = self._get_latest_version(versions_dict)
        best = self._get_best_version(versions_dict)

        return {
            'tool_name': base_name,
            'total_versions': len(versions_dict),
            'versions': list(versions_dict.keys()),
            'prime_version': prime.version if prime else None,
            'latest_version': latest.version if latest else None,
            'best_version': best.version if best else None,
            'total_usage': sum(t.usage_count for t in tools),
            'avg_usage_per_version': sum(t.usage_count for t in tools) / len(tools) if tools else 0
        }


# Import datetime for promote_to_prime
from datetime import datetime
