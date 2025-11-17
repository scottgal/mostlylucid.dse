"""
System Guardrails - Protection Against Breaking the App

This module implements robust guardrails to prevent users from accidentally
or intentionally breaking critical system functionality.

CORE PRINCIPLE: "You cannot break the app"
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class GuardrailViolation(Exception):
    """Raised when a guardrail prevents an operation."""
    pass


class SystemGuardrails:
    """
    Implements protection mechanisms for critical system components.

    Prevents:
    - Deletion of critical files/directories
    - Modification of core system code
    - Corruption of RAG memory
    - Removal of protected tools
    - Invalid configuration changes
    """

    # CRITICAL PATHS - Cannot be deleted or moved
    CRITICAL_PATHS = [
        "rag_memory/",
        "rag_memory/index.json",
        "rag_memory/embeddings.npy",
        "rag_memory/tags_index.json",
        "tools/",
        "tools/index.json",
        "src/",
        "config.yaml",
        "chat_cli.py",
        "requirements.txt"
    ]

    # PROTECTED TOOLS - Cannot be deleted
    PROTECTED_TOOLS = [
        "code_generator",
        "code_reviewer",
        "conversation_manager",
        "cron_deconstructor",
        "cron_querier",
        "faker_tool",
        "dependency_analyzer"
    ]

    # DANGEROUS PATTERNS - Require confirmation
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf",
        r"del\s+/s",
        r"DROP\s+TABLE",
        r"DELETE\s+FROM",
        r"TRUNCATE",
        r"FORMAT",
        r"--force"
    ]

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize guardrails.

        Args:
            base_path: Base directory for the system (default: current directory)
        """
        self.base_path = Path(base_path) if base_path else Path(".")

    def check_file_deletion(self, file_path: str) -> Dict[str, Any]:
        """
        Check if a file can be safely deleted.

        Args:
            file_path: Path to file to delete

        Returns:
            Dict with:
            - allowed: bool
            - reason: str (if not allowed)
            - severity: str (warning, error, critical)
            - alternative: str (suggested safe alternative)

        Raises:
            GuardrailViolation: If deletion would break the system
        """
        normalized_path = str(Path(file_path).as_posix())

        # Check against critical paths
        for critical in self.CRITICAL_PATHS:
            if normalized_path.startswith(critical) or normalized_path.endswith(critical):
                raise GuardrailViolation(
                    f"CRITICAL: Cannot delete '{file_path}' - this is critical infrastructure.\n"
                    f"Reason: {self._get_protection_reason(critical)}\n"
                    f"Alternative: {self._get_safe_alternative('delete', critical)}"
                )

        # Check if it's a core source file
        if normalized_path.startswith("src/") and normalized_path.endswith(".py"):
            raise GuardrailViolation(
                f"CRITICAL: Cannot delete core system file '{file_path}'.\n"
                f"Reason: This is part of the system's core functionality.\n"
                f"Alternative: Create a custom module in a different directory."
            )

        # Safe to delete (but recommend caution)
        if normalized_path.startswith("nodes/"):
            return {
                "allowed": True,
                "reason": "Node can be deleted (but you may want to back it up first)",
                "severity": "warning",
                "alternative": "Consider archiving instead of deleting"
            }

        return {"allowed": True, "severity": "info"}

    def check_tool_deletion(self, tool_id: str) -> Dict[str, Any]:
        """
        Check if a tool can be safely deleted.

        Args:
            tool_id: Tool identifier

        Returns:
            Dict with allowed status and reasons

        Raises:
            GuardrailViolation: If tool is protected
        """
        if tool_id in self.PROTECTED_TOOLS:
            raise GuardrailViolation(
                f"CRITICAL: Cannot delete protected tool '{tool_id}'.\n"
                f"Reason: This tool is essential for core functionality.\n"
                f"Protected tools: {', '.join(self.PROTECTED_TOOLS)}\n"
                f"Alternative: You can create a custom variant of this tool instead."
            )

        return {
            "allowed": True,
            "severity": "warning",
            "message": f"Tool '{tool_id}' can be deleted, but ensure no workflows depend on it."
        }

    def check_rag_operation(self, operation: str, details: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if a RAG operation is safe.

        Args:
            operation: Operation type (clear, delete, modify)
            details: Additional operation details

        Returns:
            Dict with allowed status and requirements

        Raises:
            GuardrailViolation: If operation would corrupt RAG
        """
        if operation == "clear_all":
            return {
                "allowed": True,
                "requires_confirmation": True,
                "severity": "critical",
                "warning": (
                    "WARNING: This will delete ALL artifacts from RAG memory!\n"
                    "This includes:\n"
                    "  - All generated code patterns\n"
                    "  - All tool definitions (non-YAML)\n"
                    "  - All workflows\n"
                    "  - All plans and evaluations\n"
                    "\nYAML-based tools will be preserved and reloaded.\n"
                    "This action CANNOT be undone."
                ),
                "confirmation_phrase": "yes, clear all rag data"
            }

        if operation == "delete_directory":
            raise GuardrailViolation(
                "CRITICAL: Cannot delete RAG memory directory.\n"
                "Reason: System cannot function without RAG.\n"
                "Alternative: Use /clear_rag command to safely clear artifacts."
            )

        if operation == "corrupt_index":
            raise GuardrailViolation(
                "CRITICAL: Cannot modify RAG index files directly.\n"
                "Reason: This will corrupt the RAG memory.\n"
                "Alternative: Use RAG API methods for modifications."
            )

        return {"allowed": True}

    def check_config_modification(
        self,
        key: str,
        value: Any,
        current_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if a configuration modification is safe.

        Args:
            key: Config key to modify
            value: New value
            current_config: Current configuration

        Returns:
            Dict with validation results

        Raises:
            GuardrailViolation: If modification would break the system
        """
        # Prevent deletion of critical config keys
        if value is None and key in ["llm", "llm.backends", "llm.models"]:
            raise GuardrailViolation(
                f"CRITICAL: Cannot delete config key '{key}'.\n"
                f"Reason: This configuration is required for system operation.\n"
                f"Alternative: Set it to a valid value instead."
            )

        # Validate backend settings
        if key == "llm.backend" and value not in ["ollama", "anthropic"]:
            raise GuardrailViolation(
                f"CRITICAL: Invalid backend '{value}'.\n"
                f"Valid backends: ollama, anthropic\n"
                f"Current backend: {current_config.get('llm', {}).get('backend', 'unknown')}"
            )

        # Validate model references
        if "model" in key and isinstance(value, str):
            # Check if model exists in registry
            models = current_config.get("llm", {}).get("models", {})
            if value not in models and not value.startswith("claude-"):
                return {
                    "allowed": True,
                    "severity": "warning",
                    "message": f"Model '{value}' not found in registry. Ensure it exists."
                }

        return {"allowed": True}

    def check_command_safety(self, command: str) -> Dict[str, Any]:
        """
        Check if a shell command is safe to execute.

        Args:
            command: Shell command to check

        Returns:
            Dict with safety assessment

        Raises:
            GuardrailViolation: If command is dangerous
        """
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                raise GuardrailViolation(
                    f"CRITICAL: Dangerous command detected.\n"
                    f"Pattern: {pattern}\n"
                    f"Command: {command}\n"
                    f"Reason: This command could destroy data or break the system.\n"
                    f"Alternative: Use safer, targeted operations instead."
                )

        # Check for deletion of critical paths
        for critical in self.CRITICAL_PATHS:
            if critical in command and any(del_cmd in command for del_cmd in ["rm", "del", "delete"]):
                raise GuardrailViolation(
                    f"CRITICAL: Command attempts to delete protected path '{critical}'.\n"
                    f"Reason: {self._get_protection_reason(critical)}\n"
                    f"Alternative: {self._get_safe_alternative('delete', critical)}"
                )

        return {"allowed": True, "severity": "info"}

    def _get_protection_reason(self, path: str) -> str:
        """Get human-readable reason for path protection."""
        reasons = {
            "rag_memory/": "RAG memory is critical infrastructure - system cannot function without it",
            "tools/": "Tool definitions are essential for all system functionality",
            "src/": "Core system code - modifying this can break the entire system",
            "config.yaml": "Configuration file required for system initialization",
            "chat_cli.py": "Main CLI interface - deleting this removes all user interaction"
        }

        for key, reason in reasons.items():
            if path.startswith(key) or path == key:
                return reason

        return "This is a protected system file"

    def _get_safe_alternative(self, operation: str, path: str) -> str:
        """Get safe alternative to a dangerous operation."""
        if operation == "delete":
            if path.startswith("rag_memory/"):
                return "Use /clear_rag command to safely clear specific artifacts"
            elif path.startswith("tools/"):
                return "Use /tools --delete <tool_id> to delete specific non-protected tools"
            elif path.startswith("nodes/"):
                return "Safe to delete nodes, but consider archiving first"
            elif path.startswith("src/"):
                return "Create custom modules in a separate directory instead"

        return "Contact system administrator or check documentation"

    def validate_bulk_operation(
        self,
        operation: str,
        targets: List[str]
    ) -> Dict[str, Any]:
        """
        Validate a bulk operation (e.g., delete multiple files).

        Args:
            operation: Operation type
            targets: List of targets

        Returns:
            Dict with validation results and protected targets

        Raises:
            GuardrailViolation: If operation would affect protected resources
        """
        protected = []
        allowed = []

        for target in targets:
            try:
                if operation == "delete":
                    self.check_file_deletion(target)
                    allowed.append(target)
            except GuardrailViolation:
                protected.append(target)

        if protected:
            raise GuardrailViolation(
                f"CRITICAL: Bulk operation blocked - some targets are protected.\n"
                f"Protected targets ({len(protected)}): {', '.join(protected[:5])}\n"
                f"Allowed targets ({len(allowed)}): {', '.join(allowed[:5])}\n"
                f"Reason: Cannot perform bulk operation that includes protected resources.\n"
                f"Alternative: Perform operation only on allowed targets."
            )

        return {
            "allowed": True,
            "protected_count": 0,
            "allowed_count": len(allowed)
        }

    def require_confirmation(
        self,
        operation: str,
        details: str,
        expected_phrase: str = "yes"
    ) -> bool:
        """
        Require user confirmation for dangerous operations.

        Args:
            operation: Operation description
            details: Detailed explanation of consequences
            expected_phrase: Exact phrase user must type

        Returns:
            True if user confirms, False otherwise

        Note:
            This is a helper for CLI integration. The actual confirmation
            prompt should be implemented in the CLI layer.
        """
        return {
            "requires_confirmation": True,
            "operation": operation,
            "details": details,
            "expected_phrase": expected_phrase,
            "severity": "critical"
        }
