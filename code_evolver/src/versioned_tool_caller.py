"""
Versioned Tool Caller - Version-Aware Tool Execution

This module provides a wrapper for calling tools with version tracking.
All tool calls are logged with name + version for cluster identification.

Usage:
    from code_evolver.src.versioned_tool_caller import call_tool, ToolCallRegistry

    # Call a tool with automatic version tracking
    result = call_tool("parse_cron", args={"expression": "0 0 * * *"}, version="best")

    # Get call history for analysis
    history = ToolCallRegistry.get_call_history("parse_cron")
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

from .versioned_tool_manager import VersionedToolManager
from .tools_manager import Tool

logger = logging.getLogger(__name__)


@dataclass
class ToolCallRecord:
    """Record of a single tool call."""
    tool_name: str
    version: str
    timestamp: datetime
    args: Dict[str, Any]
    result: Any
    success: bool
    execution_time_ms: float
    error: Optional[str] = None


class ToolCallRegistry:
    """
    Registry of all tool calls with version tracking.

    Maintains a history of calls for:
    - Cluster identification
    - Performance analysis
    - Version usage tracking
    """

    _instance = None
    _call_history: Dict[str, List[ToolCallRecord]] = {}
    _tool_manager: Optional[VersionedToolManager] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, tool_manager: Optional[VersionedToolManager] = None):
        """
        Initialize the registry.

        Args:
            tool_manager: VersionedToolManager instance (will create if None)
        """
        instance = cls()
        if instance._tool_manager is None:
            instance._tool_manager = tool_manager or VersionedToolManager()
        return instance

    @classmethod
    def record_call(
        cls,
        tool_name: str,
        version: str,
        args: Dict[str, Any],
        result: Any,
        success: bool,
        execution_time_ms: float,
        error: Optional[str] = None
    ):
        """
        Record a tool call.

        Args:
            tool_name: Base tool name
            version: Version used
            args: Arguments passed
            result: Result returned
            success: Whether call succeeded
            execution_time_ms: Execution time in milliseconds
            error: Error message if failed
        """
        instance = cls()

        record = ToolCallRecord(
            tool_name=tool_name,
            version=version,
            timestamp=datetime.now(),
            args=args,
            result=result,
            success=success,
            execution_time_ms=execution_time_ms,
            error=error
        )

        if tool_name not in instance._call_history:
            instance._call_history[tool_name] = []

        instance._call_history[tool_name].append(record)

    @classmethod
    def get_call_history(
        cls,
        tool_name: Optional[str] = None,
        version: Optional[str] = None
    ) -> List[ToolCallRecord]:
        """
        Get call history.

        Args:
            tool_name: Filter by tool name (None for all)
            version: Filter by version (None for all)

        Returns:
            List of call records
        """
        instance = cls()

        if tool_name is None:
            # Return all calls
            all_calls = []
            for calls in instance._call_history.values():
                all_calls.extend(calls)
            return all_calls

        calls = instance._call_history.get(tool_name, [])

        if version is not None:
            calls = [c for c in calls if c.version == version]

        return calls

    @classmethod
    def get_version_usage_stats(cls) -> Dict[str, Dict[str, int]]:
        """
        Get usage statistics by tool and version.

        Returns:
            Dictionary: tool_name -> {version -> call_count}
        """
        instance = cls()
        stats = {}

        for tool_name, calls in instance._call_history.items():
            version_counts = {}
            for call in calls:
                if call.version not in version_counts:
                    version_counts[call.version] = 0
                version_counts[call.version] += 1

            stats[tool_name] = version_counts

        return stats

    @classmethod
    def export_to_file(cls, file_path: Path):
        """
        Export call history to JSON file.

        Args:
            file_path: Path to export file
        """
        instance = cls()

        data = {
            'export_time': datetime.now().isoformat(),
            'total_calls': sum(len(calls) for calls in instance._call_history.values()),
            'call_history': {}
        }

        for tool_name, calls in instance._call_history.items():
            data['call_history'][tool_name] = [
                {
                    'tool_name': call.tool_name,
                    'version': call.version,
                    'timestamp': call.timestamp.isoformat(),
                    'args': str(call.args),  # Simplified serialization
                    'success': call.success,
                    'execution_time_ms': call.execution_time_ms,
                    'error': call.error
                }
                for call in calls
            ]

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported call history to {file_path}")


def call_tool(
    tool_name: str,
    args: Optional[Dict[str, Any]] = None,
    version: Optional[str] = None,
    strategy: str = "best",
    tool_manager: Optional[VersionedToolManager] = None
) -> Any:
    """
    Call a tool with version tracking.

    Args:
        tool_name: Base tool name
        args: Arguments to pass to the tool
        version: Version specification:
            - Exact version: "1.2.3"
            - Major.minor: "1.2" (any patch in 1.2.x)
            - "latest" (highest version number)
            - "best" (highest fitness score)
            - None (use strategy)
        strategy: Selection strategy when version is None:
            - "best" (default): Highest fitness score
            - "latest": Highest version number
            - "stable": Highest stable version
        tool_manager: VersionedToolManager instance (will create if None)

    Returns:
        Tool execution result

    Example:
        result = call_tool("parse_cron", args={"expression": "0 0 * * *"}, version="best")
    """
    import time

    args = args or {}

    # Get tool manager
    if tool_manager is None:
        registry = ToolCallRegistry.initialize()
        tool_manager = registry._tool_manager

    # Find the appropriate version
    start_time = time.time()

    try:
        tool = tool_manager.get_tool_by_version(
            tool_name=tool_name,
            version=version,
            strategy=strategy
        )

        if tool is None:
            error_msg = f"Tool '{tool_name}' not found"
            logger.error(error_msg)

            execution_time_ms = (time.time() - start_time) * 1000

            ToolCallRegistry.record_call(
                tool_name=tool_name,
                version="unknown",
                args=args,
                result=None,
                success=False,
                execution_time_ms=execution_time_ms,
                error=error_msg
            )

            raise ValueError(error_msg)

        # Execute the tool
        logger.debug(f"Calling {tool_name} v{tool.version} with args: {args}")

        result = execute_tool(tool, args)

        execution_time_ms = (time.time() - start_time) * 1000

        # Record successful call
        ToolCallRegistry.record_call(
            tool_name=tool_name,
            version=tool.version,
            args=args,
            result=result,
            success=True,
            execution_time_ms=execution_time_ms
        )

        # Update usage count
        tool.usage_count += 1

        return result

    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000

        # Record failed call
        ToolCallRegistry.record_call(
            tool_name=tool_name,
            version=tool.version if tool else "unknown",
            args=args,
            result=None,
            success=False,
            execution_time_ms=execution_time_ms,
            error=str(e)
        )

        logger.error(f"Error calling {tool_name}: {e}")
        raise


def execute_tool(tool: Tool, args: Dict[str, Any]) -> Any:
    """
    Execute a tool with the given arguments.

    Args:
        tool: Tool to execute
        args: Arguments to pass

    Returns:
        Tool execution result
    """
    implementation = tool.implementation

    if implementation is None:
        raise ValueError(f"Tool {tool.tool_id} has no implementation")

    # Handle different implementation types
    if callable(implementation):
        # Direct function call
        return implementation(**args)

    elif isinstance(implementation, dict):
        # Configuration-based tool (e.g., LLM config, API spec)
        # Would need specific handlers for each type
        raise NotImplementedError(f"Config-based tools not yet supported")

    elif isinstance(implementation, str):
        # Code string - would need to exec it
        # This is potentially unsafe - use with caution
        raise NotImplementedError(f"String-based implementations not yet supported")

    else:
        raise TypeError(f"Unknown implementation type: {type(implementation)}")


def call_tool_with_fallback(
    tool_name: str,
    args: Optional[Dict[str, Any]] = None,
    preferred_version: Optional[str] = None,
    fallback_versions: Optional[List[str]] = None,
    tool_manager: Optional[VersionedToolManager] = None
) -> Tuple[Any, str]:
    """
    Call a tool with version fallback.

    Tries preferred version first, then falls back to other versions if it fails.

    Args:
        tool_name: Base tool name
        args: Arguments to pass
        preferred_version: Preferred version to try first
        fallback_versions: List of fallback versions to try
        tool_manager: VersionedToolManager instance

    Returns:
        (result, version_used) tuple

    Example:
        result, version = call_tool_with_fallback(
            "parse_cron",
            args={"expression": "0 0 * * *"},
            preferred_version="2.0.0",
            fallback_versions=["1.9.5", "1.9.0", "best"]
        )
    """
    fallback_versions = fallback_versions or ["latest", "best"]

    # Try preferred version first
    if preferred_version:
        try:
            result = call_tool(
                tool_name=tool_name,
                args=args,
                version=preferred_version,
                tool_manager=tool_manager
            )
            return result, preferred_version
        except Exception as e:
            logger.warning(
                f"Preferred version {preferred_version} failed: {e}. "
                f"Trying fallbacks..."
            )

    # Try fallback versions
    for fallback_version in fallback_versions:
        try:
            result = call_tool(
                tool_name=tool_name,
                args=args,
                version=fallback_version,
                tool_manager=tool_manager
            )
            return result, fallback_version
        except Exception as e:
            logger.warning(f"Fallback version {fallback_version} failed: {e}")
            continue

    # All versions failed
    raise RuntimeError(f"All versions of {tool_name} failed")


def analyze_version_clusters(
    tool_manager: Optional[VersionedToolManager] = None
) -> Dict[str, Any]:
    """
    Analyze version clusters based on call history.

    Identifies:
    - Most used versions per tool
    - Version migration patterns
    - Cluster formation around versions

    Args:
        tool_manager: VersionedToolManager instance

    Returns:
        Dictionary with cluster analysis
    """
    if tool_manager is None:
        registry = ToolCallRegistry.initialize()
        tool_manager = registry._tool_manager

    usage_stats = ToolCallRegistry.get_version_usage_stats()

    analysis = {
        'clusters': {},
        'migration_patterns': {},
        'recommendations': []
    }

    for tool_name, version_counts in usage_stats.items():
        # Get cluster stats
        cluster_stats = tool_manager.get_cluster_stats(tool_name)

        # Find dominant version (most used)
        dominant_version = max(version_counts, key=version_counts.get)
        dominant_usage = version_counts[dominant_version]
        total_usage = sum(version_counts.values())

        # Calculate cluster metrics
        analysis['clusters'][tool_name] = {
            'total_versions': cluster_stats.get('total_versions', 0),
            'dominant_version': dominant_version,
            'dominant_usage_percent': (dominant_usage / total_usage * 100) if total_usage > 0 else 0,
            'version_distribution': version_counts,
            'prime_version': cluster_stats.get('prime_version'),
            'best_version': cluster_stats.get('best_version'),
            'latest_version': cluster_stats.get('latest_version')
        }

        # Generate recommendations
        if dominant_version != cluster_stats.get('best_version'):
            analysis['recommendations'].append(
                f"{tool_name}: Consider promoting v{cluster_stats.get('best_version')} "
                f"(currently using v{dominant_version})"
            )

        # Identify fragmentation (too many versions in use)
        if len(version_counts) > 3:
            analysis['recommendations'].append(
                f"{tool_name}: High version fragmentation "
                f"({len(version_counts)} versions in use). Consider consolidation."
            )

    return analysis
