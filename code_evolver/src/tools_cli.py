#!/usr/bin/env python3
"""
Tools CLI - Command-Line Interface for Tool Management

Provides commands for testing and optimizing tools in the ecosystem.

Commands:
- /tools optimize all - Optimize all tools
- /tools optimize --n <name> - Optimize specific tool
- /tools test all - Test all tools
- /tools test --n <name> - Test specific tool and dependencies
- /tools weight --n <name> - Get weight/priority for a specific tool
- /tools weight --n <name> --set <value> - Set manual weight for a tool
- /tools search --prompt "<query>" - Search tools and show fitness scores

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
    WEIGHT_GET = "weight_get"
    WEIGHT_SET = "weight_set"
    SEARCH = "search"
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
        elif cmd_type == CommandType.WEIGHT_GET:
            result = self._weight_get(tool_name)
        elif cmd_type == CommandType.WEIGHT_SET:
            # Parse weight value from command
            weight_value = self._parse_weight_value(command)
            result = self._weight_set(tool_name, weight_value)
        elif cmd_type == CommandType.SEARCH:
            # Parse search prompt from command
            search_prompt = self._parse_search_prompt(command)
            result = self._search_tools(search_prompt)
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
        elif action == "weight":
            if tool_name:
                # Check if --set flag is present
                if "--set" in parts:
                    return (CommandType.WEIGHT_SET, tool_name)
                else:
                    return (CommandType.WEIGHT_GET, tool_name)
        elif action == "search":
            # Search command uses --prompt flag
            return (CommandType.SEARCH, None)

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

    def _parse_weight_value(self, command: str) -> Optional[float]:
        """
        Parse weight value from command.

        Args:
            command: Command string

        Returns:
            Weight value or None
        """
        parts = command.strip().split()
        if "--set" in parts:
            try:
                set_index = parts.index("--set")
                if set_index + 1 < len(parts):
                    return float(parts[set_index + 1])
            except (ValueError, IndexError):
                pass
        return None

    def _parse_search_prompt(self, command: str) -> str:
        """
        Parse search prompt from command.

        Args:
            command: Command string

        Returns:
            Search prompt
        """
        # Extract text after --prompt flag
        if "--prompt" in command:
            prompt_part = command.split("--prompt", 1)[1].strip()
            # Remove quotes if present
            if prompt_part.startswith('"') and prompt_part.endswith('"'):
                return prompt_part[1:-1]
            elif prompt_part.startswith("'") and prompt_part.endswith("'"):
                return prompt_part[1:-1]
            return prompt_part
        return ""

    def _weight_get(self, tool_name: str) -> Dict[str, Any]:
        """
        Get weight/priority for a tool.

        Args:
            tool_name: Tool name

        Returns:
            Result dictionary
        """
        tool = self.tools.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "message": f"Tool '{tool_name}' not found",
                "details": {}
            }

        # Get manual weight from metadata
        manual_weight = tool.metadata.get("manual_weight", None)

        # Calculate base fitness score
        metadata = tool.metadata or {}
        base_fitness = 0

        # Speed tier
        speed_tier = metadata.get('speed_tier', 'medium')
        if speed_tier == 'very-fast':
            base_fitness += 20
        elif speed_tier == 'fast':
            base_fitness += 10
        elif speed_tier == 'slow':
            base_fitness -= 10
        elif speed_tier == 'very-slow':
            base_fitness -= 20

        # Cost tier
        cost_tier = metadata.get('cost_tier', 'medium')
        if cost_tier == 'free':
            base_fitness += 15
        elif cost_tier == 'low':
            base_fitness += 10
        elif cost_tier == 'high':
            base_fitness -= 10
        elif cost_tier == 'very-high':
            base_fitness -= 15

        # Quality tier
        quality_tier = metadata.get('quality_tier', 'good')
        if quality_tier == 'excellent':
            base_fitness += 15
        elif quality_tier == 'very-good':
            base_fitness += 10
        elif quality_tier == 'poor':
            base_fitness -= 15

        # MCP penalty
        from src.tools_manager import ToolType
        if tool.tool_type == ToolType.MCP:
            base_fitness -= 40

        details = {
            "tool_name": tool_name,
            "tool_type": tool.tool_type.value,
            "manual_weight": manual_weight,
            "base_fitness": base_fitness,
            "speed_tier": metadata.get('speed_tier', 'medium'),
            "cost_tier": metadata.get('cost_tier', 'medium'),
            "quality_tier": metadata.get('quality_tier', 'good')
        }

        if manual_weight is not None:
            message = f"Tool '{tool_name}' has manual weight: {manual_weight} (base fitness: {base_fitness})"
        else:
            message = f"Tool '{tool_name}' has no manual weight set (base fitness: {base_fitness})"

        return {
            "success": True,
            "message": message,
            "details": details
        }

    def _weight_set(self, tool_name: str, weight: Optional[float]) -> Dict[str, Any]:
        """
        Set manual weight for a tool.

        Args:
            tool_name: Tool name
            weight: Weight value

        Returns:
            Result dictionary
        """
        if weight is None:
            return {
                "success": False,
                "message": "Weight value not provided. Use: /tools weight --n <name> --set <value>",
                "details": {}
            }

        tool = self.tools.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "message": f"Tool '{tool_name}' not found",
                "details": {}
            }

        # Set manual weight in metadata
        tool.metadata["manual_weight"] = weight

        # Save to tool file if it's a YAML-based tool
        if tool.metadata.get("from_yaml"):
            # TODO: Update YAML file with new weight
            # For now, just store in memory
            pass

        return {
            "success": True,
            "message": f"Set manual weight for '{tool_name}' to {weight}",
            "details": {
                "tool_name": tool_name,
                "weight": weight
            }
        }

    def _search_tools(self, prompt: str) -> Dict[str, Any]:
        """
        Search for tools and show fitness scores.

        Args:
            prompt: Search prompt

        Returns:
            Result dictionary with top 10 matches
        """
        if not prompt:
            return {
                "success": False,
                "message": "Search prompt not provided. Use: /tools search --prompt \"<query>\"",
                "details": {}
            }

        if self.verbose:
            print(f"\n[SEARCH] Searching tools for: {prompt}")

        # Use tools manager's search function
        matching_tools = self.tools.search(prompt, top_k=10, use_rag=True)

        results = []
        for tool in matching_tools:
            metadata = tool.metadata or {}

            # Calculate fitness score (same as in search function)
            base_fitness = 0

            # Speed tier
            speed_tier = metadata.get('speed_tier', 'medium')
            if speed_tier == 'very-fast':
                base_fitness += 20
            elif speed_tier == 'fast':
                base_fitness += 10
            elif speed_tier == 'slow':
                base_fitness -= 10
            elif speed_tier == 'very-slow':
                base_fitness -= 20

            # Cost tier
            cost_tier = metadata.get('cost_tier', 'medium')
            if cost_tier == 'free':
                base_fitness += 15
            elif cost_tier == 'low':
                base_fitness += 10
            elif cost_tier == 'high':
                base_fitness -= 10
            elif cost_tier == 'very-high':
                base_fitness -= 15

            # Quality tier
            quality_tier = metadata.get('quality_tier', 'good')
            if quality_tier == 'excellent':
                base_fitness += 15
            elif quality_tier == 'very-good':
                base_fitness += 10
            elif quality_tier == 'poor':
                base_fitness -= 15

            # MCP penalty
            from src.tools_manager import ToolType
            if tool.tool_type == ToolType.MCP:
                base_fitness -= 40

            # Manual weight
            manual_weight = metadata.get("manual_weight", None)
            if manual_weight is not None:
                base_fitness += manual_weight

            results.append({
                "name": tool.name,
                "tool_id": tool.tool_id,
                "type": tool.tool_type.value,
                "description": tool.description[:100] + "..." if len(tool.description) > 100 else tool.description,
                "fitness": base_fitness,
                "speed_tier": speed_tier,
                "cost_tier": cost_tier,
                "quality_tier": quality_tier,
                "manual_weight": manual_weight,
                "tags": tool.tags[:5]  # Limit tags for display
            })

        return {
            "success": True,
            "message": f"Found {len(results)} matching tools",
            "details": {
                "query": prompt,
                "count": len(results),
                "results": results
            }
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
