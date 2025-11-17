#!/usr/bin/env python3
"""
Tools CLI - Command-Line Interface for Tool Management

Provides commands for testing and optimizing tools in the ecosystem.

Commands:
- /tools optimize all - Optimize all tools
- /tools optimize --n <name> - Optimize specific tool
- /tools test all - Test all tools
- /tools test --n <name> - Test specific tool and dependencies

USAGE:
    from src.tools_cli import ToolsCLI

    cli = ToolsCLI(tools_manager, rag, client)
    result = cli.handle_command("/tools test all")
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from src.tools_manager import ToolsManager
from src.rag_memory import RAGMemory
from src.ollama_client import OllamaClient


class CommandType(Enum):
    """Command types."""
    OPTIMIZE_ALL = "optimize_all"
    OPTIMIZE_SINGLE = "optimize_single"
    TEST_ALL = "test_all"
    TEST_SINGLE = "test_single"
    UNKNOWN = "unknown"


@dataclass
class CommandResult:
    """Result from a tools command."""
    success: bool
    command_type: CommandType
    message: str
    details: Dict[str, Any]
    duration: float


class ToolsCLI:
    """
    CLI for tool management.

    Handles optimization and testing of tools.
    """

    def __init__(
        self,
        tools_manager: ToolsManager,
        rag: RAGMemory,
        client: OllamaClient,
        verbose: bool = True
    ):
        """
        Initialize tools CLI.

        Args:
            tools_manager: Tools manager instance
            rag: RAG memory for usage tracking
            client: Ollama client for optimization
            verbose: Whether to print progress
        """
        self.tools = tools_manager
        self.rag = rag
        self.client = client
        self.verbose = verbose

        # Import optimizer and tester lazily
        self._optimizer = None
        self._tester = None

    @property
    def optimizer(self):
        """Lazy load tool optimizer."""
        if self._optimizer is None:
            from src.tool_optimizer import ToolOptimizer
            self._optimizer = ToolOptimizer(
                self.tools,
                self.rag,
                self.client,
                verbose=self.verbose
            )
        return self._optimizer

    @property
    def tester(self):
        """Lazy load tool tester."""
        if self._tester is None:
            from src.tool_tester import ToolTester
            self._tester = ToolTester(
                self.tools,
                verbose=self.verbose
            )
        return self._tester

    def handle_command(self, command: str) -> CommandResult:
        """
        Handle a /tools command.

        Args:
            command: Full command string (e.g., "/tools test all")

        Returns:
            CommandResult with outcome
        """
        start_time = time.time()

        # Parse command
        cmd_type, tool_name = self._parse_command(command)

        if cmd_type == CommandType.UNKNOWN:
            return CommandResult(
                success=False,
                command_type=cmd_type,
                message="Unknown command. Use: /tools optimize all|--n <name> or /tools test all|--n <name>",
                details={},
                duration=time.time() - start_time
            )

        # Route to appropriate handler
        if cmd_type == CommandType.OPTIMIZE_ALL:
            result = self._optimize_all()
        elif cmd_type == CommandType.OPTIMIZE_SINGLE:
            result = self._optimize_single(tool_name)
        elif cmd_type == CommandType.TEST_ALL:
            result = self._test_all()
        elif cmd_type == CommandType.TEST_SINGLE:
            result = self._test_single(tool_name)
        else:
            result = {
                "success": False,
                "message": "Command not implemented",
                "details": {}
            }

        duration = time.time() - start_time

        return CommandResult(
            success=result.get("success", False),
            command_type=cmd_type,
            message=result.get("message", ""),
            details=result.get("details", {}),
            duration=duration
        )

    def _parse_command(self, command: str) -> tuple[CommandType, Optional[str]]:
        """
        Parse command string into type and optional tool name.

        Args:
            command: Command string

        Returns:
            (command_type, tool_name)
        """
        parts = command.strip().split()

        if len(parts) < 2 or parts[0] != "/tools":
            return (CommandType.UNKNOWN, None)

        action = parts[1].lower()

        # Check for --n flag
        tool_name = None
        if "--n" in parts:
            try:
                n_index = parts.index("--n")
                if n_index + 1 < len(parts):
                    tool_name = parts[n_index + 1]
            except (ValueError, IndexError):
                pass

        # Determine command type
        if action == "optimize":
            if tool_name:
                return (CommandType.OPTIMIZE_SINGLE, tool_name)
            elif "all" in parts:
                return (CommandType.OPTIMIZE_ALL, None)
        elif action == "test":
            if tool_name:
                return (CommandType.TEST_SINGLE, tool_name)
            elif "all" in parts:
                return (CommandType.TEST_ALL, None)

        return (CommandType.UNKNOWN, None)

    def _optimize_all(self) -> Dict[str, Any]:
        """
        Optimize all tools.

        Returns:
            Result dictionary
        """
        if self.verbose:
            print("\n[OPTIMIZE] Starting optimization of all tools...")

        results = self.optimizer.optimize_all_tools()

        success_count = sum(1 for r in results if r.get("improved", False))
        total_count = len(results)

        return {
            "success": True,
            "message": f"Optimized {total_count} tools, {success_count} improved",
            "details": {
                "total_tools": total_count,
                "improved_count": success_count,
                "results": results
            }
        }

    def _optimize_single(self, tool_name: str) -> Dict[str, Any]:
        """
        Optimize a specific tool.

        Args:
            tool_name: Tool to optimize

        Returns:
            Result dictionary
        """
        if self.verbose:
            print(f"\n[OPTIMIZE] Optimizing tool: {tool_name}")

        result = self.optimizer.optimize_tool(tool_name)

        if result.get("improved", False):
            message = f"Tool '{tool_name}' optimized successfully"
        else:
            message = f"Tool '{tool_name}' already optimal or no improvements found"

        return {
            "success": True,
            "message": message,
            "details": result
        }

    def _test_all(self) -> Dict[str, Any]:
        """
        Test all tools.

        Returns:
            Result dictionary
        """
        if self.verbose:
            print("\n[TEST] Running tests for all tools...")

        results = self.tester.test_all_tools()

        passed_count = sum(1 for r in results if r.get("passed", False))
        total_count = len(results)

        return {
            "success": passed_count == total_count,
            "message": f"Tests: {passed_count}/{total_count} passed",
            "details": {
                "total_tests": total_count,
                "passed": passed_count,
                "failed": total_count - passed_count,
                "results": results
            }
        }

    def _test_single(self, tool_name: str) -> Dict[str, Any]:
        """
        Test a specific tool and its dependencies.

        Args:
            tool_name: Tool to test

        Returns:
            Result dictionary
        """
        if self.verbose:
            print(f"\n[TEST] Testing tool: {tool_name}")

        result = self.tester.test_tool(tool_name, test_dependencies=True)

        if result.get("passed", False):
            message = f"Tool '{tool_name}' passed all tests"
        else:
            message = f"Tool '{tool_name}' failed tests"

        return {
            "success": result.get("passed", False),
            "message": message,
            "details": result
        }


def main():
    """CLI entry point for testing."""
    from src.config_manager import ConfigManager

    config = ConfigManager()
    client = OllamaClient(config_manager=config)
    rag = RAGMemory(ollama_client=client)
    tools = ToolsManager(config_manager=config, rag_memory=rag, ollama_client=client)

    cli = ToolsCLI(tools, rag, client, verbose=True)

    # Test commands
    test_commands = [
        "/tools test all",
        "/tools test --n content_splitter",
        "/tools optimize all",
        "/tools optimize --n content_summarizer"
    ]

    for cmd in test_commands:
        print(f"\n{'='*60}")
        print(f"Command: {cmd}")
        print('='*60)

        result = cli.handle_command(cmd)

        print(f"\nSuccess: {result.success}")
        print(f"Message: {result.message}")
        print(f"Duration: {result.duration:.2f}s")

        if result.details:
            print(f"\nDetails:")
            print(json.dumps(result.details, indent=2))


if __name__ == "__main__":
    main()
