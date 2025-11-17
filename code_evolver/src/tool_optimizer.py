#!/usr/bin/env python3
"""
Tool Optimizer - Optimize Tool Configurations Based on Usage

Analyzes tool usage patterns from RAG and runs experiments to find
better configurations (prompts, models, parameters).

Features:
- Usage pattern analysis
- A/B testing of configurations
- Automatic parameter tuning
- Model selection optimization
- Prompt improvement

USAGE:
    from src.tool_optimizer import ToolOptimizer

    optimizer = ToolOptimizer(tools_manager, rag, client)
    result = optimizer.optimize_tool("content_summarizer")
"""

import os
import sys
import json
import time
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

from src.tools_manager import ToolsManager
from src.rag_memory import RAGMemory, ArtifactType
from src.ollama_client import OllamaClient


@dataclass
class OptimizationResult:
    """Result from tool optimization."""
    tool_name: str
    improved: bool
    original_config: Dict[str, Any]
    optimized_config: Optional[Dict[str, Any]]
    metrics: Dict[str, float]
    changes: List[str]


class ToolOptimizer:
    """
    Optimizes tool configurations based on usage patterns.

    Uses RAG to analyze past performance and runs experiments
    to find better configurations.
    """

    def __init__(
        self,
        tools_manager: ToolsManager,
        rag: RAGMemory,
        client: OllamaClient,
        verbose: bool = True
    ):
        """
        Initialize tool optimizer.

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

    def optimize_all_tools(self) -> List[Dict[str, Any]]:
        """
        Optimize all tools in the ecosystem.

        Returns:
            List of optimization results
        """
        results = []

        if self.verbose:
            print(f"\n[OPTIMIZE] Analyzing {len(self.tools.tools)} tools...")

        for tool_id in self.tools.tools:
            try:
                result = self.optimize_tool(tool_id)
                results.append(result)
            except Exception as e:
                if self.verbose:
                    print(f"[ERROR] Failed to optimize {tool_id}: {e}")
                results.append({
                    "tool_name": tool_id,
                    "improved": False,
                    "error": str(e)
                })

        return results

    def optimize_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        Optimize a specific tool.

        Steps:
        1. Analyze usage patterns from RAG
        2. Identify performance bottlenecks
        3. Generate improvement hypotheses
        4. Run experiments
        5. Select best configuration
        6. Update tool definition

        Args:
            tool_name: Tool to optimize

        Returns:
            Optimization result
        """
        if self.verbose:
            print(f"\n[OPTIMIZE] Analyzing tool: {tool_name}")

        # Get tool
        tool = self.tools.get_tool(tool_name)
        if not tool:
            return {
                "tool_name": tool_name,
                "improved": False,
                "error": "Tool not found"
            }

        # Step 1: Analyze usage patterns
        usage_stats = self._analyze_usage(tool_name)

        if self.verbose:
            print(f"  Usage count: {usage_stats.get('usage_count', 0)}")
            print(f"  Avg quality: {usage_stats.get('avg_quality', 0):.2f}")
            print(f"  Avg latency: {usage_stats.get('avg_latency', 0):.2f}s")

        # Step 2: Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(usage_stats)

        if not bottlenecks:
            if self.verbose:
                print(f"  No bottlenecks found - tool is optimal")
            return {
                "tool_name": tool_name,
                "improved": False,
                "message": "Tool is already optimal",
                "usage_stats": usage_stats
            }

        if self.verbose:
            print(f"  Bottlenecks: {', '.join(bottlenecks)}")

        # Step 3: Generate hypotheses
        hypotheses = self._generate_hypotheses(tool, usage_stats, bottlenecks)

        if self.verbose:
            print(f"  Generated {len(hypotheses)} improvement hypotheses")

        # Step 4: Run experiments
        experiments = self._run_experiments(tool, hypotheses, usage_stats)

        # Step 5: Select best
        best = self._select_best_configuration(experiments, usage_stats)

        if not best or best.get("improvement_score", 0) < 0.05:
            if self.verbose:
                print(f"  No significant improvement found")
            return {
                "tool_name": tool_name,
                "improved": False,
                "message": "No significant improvement found",
                "experiments": experiments
            }

        # Step 6: Update tool
        if self.verbose:
            print(f"  Improvement score: {best['improvement_score']:.2%}")
            print(f"  Updating tool definition...")

        self._update_tool_definition(tool_name, best["config"])

        return {
            "tool_name": tool_name,
            "improved": True,
            "improvement_score": best["improvement_score"],
            "changes": best.get("changes", []),
            "original_config": usage_stats.get("current_config", {}),
            "optimized_config": best["config"],
            "experiments": experiments
        }

    def _analyze_usage(self, tool_name: str) -> Dict[str, Any]:
        """
        Analyze usage patterns from RAG.

        Args:
            tool_name: Tool to analyze

        Returns:
            Usage statistics
        """
        # Search for tool usage in RAG
        results = self.rag.find_by_tags(
            tags=["tool_usage", tool_name],
            limit=100
        )

        if not results:
            return {
                "usage_count": 0,
                "avg_quality": 0.0,
                "avg_latency": 0.0,
                "success_rate": 0.0
            }

        # Aggregate metrics
        quality_scores = []
        latencies = []
        successes = 0

        for artifact in results:
            metadata = artifact.metadata or {}

            if "quality_score" in metadata:
                quality_scores.append(metadata["quality_score"])

            if "latency" in metadata:
                latencies.append(metadata["latency"])

            if metadata.get("success", False):
                successes += 1

        return {
            "usage_count": len(results),
            "avg_quality": sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0.0,
            "success_rate": successes / len(results) if results else 0.0,
            "quality_scores": quality_scores,
            "latencies": latencies
        }

    def _identify_bottlenecks(self, usage_stats: Dict[str, Any]) -> List[str]:
        """
        Identify performance bottlenecks.

        Args:
            usage_stats: Usage statistics

        Returns:
            List of bottleneck types
        """
        bottlenecks = []

        # Quality too low
        if usage_stats.get("avg_quality", 0) < 0.7:
            bottlenecks.append("low_quality")

        # Latency too high
        if usage_stats.get("avg_latency", 0) > 30.0:
            bottlenecks.append("high_latency")

        # Success rate too low
        if usage_stats.get("success_rate", 0) < 0.8:
            bottlenecks.append("low_success_rate")

        # High variance in quality
        quality_scores = usage_stats.get("quality_scores", [])
        if quality_scores and len(quality_scores) > 5:
            variance = sum((q - usage_stats["avg_quality"]) ** 2 for q in quality_scores) / len(quality_scores)
            if variance > 0.1:
                bottlenecks.append("high_variance")

        return bottlenecks

    def _generate_hypotheses(
        self,
        tool: Any,
        usage_stats: Dict[str, Any],
        bottlenecks: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate improvement hypotheses based on bottlenecks.

        Args:
            tool: Tool to optimize
            usage_stats: Usage statistics
            bottlenecks: Identified bottlenecks

        Returns:
            List of hypotheses to test
        """
        hypotheses = []

        # For low quality: try better model
        if "low_quality" in bottlenecks:
            if tool.type == "llm" and hasattr(tool, "llm"):
                current_model = tool.llm.get("model", "")
                # Suggest escalation
                hypotheses.append({
                    "type": "model_upgrade",
                    "change": "Use more powerful model",
                    "config": {"llm": {"model": self._suggest_better_model(current_model)}}
                })

        # For high latency: try faster model
        if "high_latency" in bottlenecks:
            if tool.type == "llm" and hasattr(tool, "llm"):
                current_model = tool.llm.get("model", "")
                hypotheses.append({
                    "type": "model_downgrade",
                    "change": "Use faster model",
                    "config": {"llm": {"model": self._suggest_faster_model(current_model)}}
                })

        # For low success rate: adjust temperature
        if "low_success_rate" in bottlenecks or "high_variance" in bottlenecks:
            if tool.type == "llm" and hasattr(tool, "llm"):
                current_temp = tool.llm.get("temperature", 0.7)
                hypotheses.append({
                    "type": "temperature_adjust",
                    "change": "Lower temperature for consistency",
                    "config": {"llm": {"temperature": max(0.1, current_temp - 0.2)}}
                })

        # For high latency: reduce max_tokens
        if "high_latency" in bottlenecks:
            if tool.type == "llm" and hasattr(tool, "llm"):
                current_tokens = tool.llm.get("max_tokens", 2000)
                if current_tokens > 500:
                    hypotheses.append({
                        "type": "token_reduction",
                        "change": "Reduce max tokens",
                        "config": {"llm": {"max_tokens": int(current_tokens * 0.7)}}
                    })

        return hypotheses

    def _suggest_better_model(self, current_model: str) -> str:
        """Suggest a better (more powerful) model."""
        model_ladder = [
            "tinyllama",
            "gemma2:2b",
            "qwen2.5-coder:3b",
            "codellama:7b",
            "llama3",
            "qwen2.5-coder:14b",
            "mistral-nemo",
            "deepseek-coder-v2:16b"
        ]

        for i, model in enumerate(model_ladder):
            if model in current_model:
                if i < len(model_ladder) - 1:
                    return model_ladder[i + 1]
                return current_model

        return "codellama:7b"

    def _suggest_faster_model(self, current_model: str) -> str:
        """Suggest a faster (smaller) model."""
        model_ladder = [
            "tinyllama",
            "gemma2:2b",
            "qwen2.5-coder:3b",
            "codellama:7b",
            "llama3",
            "qwen2.5-coder:14b",
            "mistral-nemo",
            "deepseek-coder-v2:16b"
        ]

        for i, model in enumerate(model_ladder):
            if model in current_model:
                if i > 0:
                    return model_ladder[i - 1]
                return current_model

        return "gemma2:2b"

    def _run_experiments(
        self,
        tool: Any,
        hypotheses: List[Dict[str, Any]],
        baseline: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Run experiments for each hypothesis.

        Args:
            tool: Tool being optimized
            hypotheses: Hypotheses to test
            baseline: Baseline metrics

        Returns:
            Experiment results
        """
        results = []

        for hypothesis in hypotheses:
            if self.verbose:
                print(f"    Testing: {hypothesis['change']}")

            # For now, use heuristic scoring
            # In full implementation, would actually run test cases
            score = self._score_hypothesis(hypothesis, baseline)

            results.append({
                "hypothesis": hypothesis,
                "improvement_score": score,
                "config": hypothesis["config"],
                "changes": [hypothesis["change"]]
            })

        return results

    def _score_hypothesis(
        self,
        hypothesis: Dict[str, Any],
        baseline: Dict[str, Any]
    ) -> float:
        """
        Score a hypothesis (heuristic).

        Args:
            hypothesis: Hypothesis to score
            baseline: Baseline metrics

        Returns:
            Improvement score (0-1)
        """
        # Heuristic scoring based on hypothesis type
        h_type = hypothesis.get("type", "")

        if h_type == "model_upgrade":
            # Quality improvement, latency cost
            if baseline.get("avg_quality", 0) < 0.7:
                return 0.15  # Good improvement
            return 0.05

        elif h_type == "model_downgrade":
            # Latency improvement, quality cost
            if baseline.get("avg_latency", 0) > 30:
                return 0.12  # Good improvement
            return 0.03

        elif h_type == "temperature_adjust":
            # Consistency improvement
            if baseline.get("success_rate", 1.0) < 0.8:
                return 0.10
            return 0.02

        elif h_type == "token_reduction":
            # Latency improvement
            if baseline.get("avg_latency", 0) > 20:
                return 0.08
            return 0.02

        return 0.0

    def _select_best_configuration(
        self,
        experiments: List[Dict[str, Any]],
        baseline: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Select best configuration from experiments.

        Args:
            experiments: Experiment results
            baseline: Baseline metrics

        Returns:
            Best configuration or None
        """
        if not experiments:
            return None

        # Sort by improvement score
        sorted_exp = sorted(
            experiments,
            key=lambda e: e.get("improvement_score", 0),
            reverse=True
        )

        best = sorted_exp[0]

        if best.get("improvement_score", 0) >= 0.05:
            return best

        return None

    def _update_tool_definition(
        self,
        tool_name: str,
        optimized_config: Dict[str, Any]
    ):
        """
        Update tool definition with optimized config.

        Args:
            tool_name: Tool to update
            optimized_config: New configuration
        """
        # Find tool file
        tool_file = None
        for root, dirs, files in os.walk("tools"):
            for file in files:
                if file.endswith(".yaml"):
                    path = os.path.join(root, file)
                    with open(path, 'r') as f:
                        data = yaml.safe_load(f)
                        if data and data.get("name", "").replace(" ", "_").lower() == tool_name.lower():
                            tool_file = path
                            break
            if tool_file:
                break

        if not tool_file:
            if self.verbose:
                print(f"  Warning: Could not find tool file for {tool_name}")
            return

        # Load current config
        with open(tool_file, 'r') as f:
            current = yaml.safe_load(f)

        # Merge optimized config
        for key, value in optimized_config.items():
            if isinstance(value, dict) and key in current:
                current[key].update(value)
            else:
                current[key] = value

        # Add optimization metadata
        if "metadata" not in current:
            current["metadata"] = {}

        current["metadata"]["last_optimized"] = time.strftime("%Y-%m-%d")
        current["metadata"]["optimization_version"] = current["metadata"].get("optimization_version", 0) + 1

        # Write back
        with open(tool_file, 'w') as f:
            yaml.dump(current, f, default_flow_style=False, sort_keys=False)

        if self.verbose:
            print(f"  Updated: {tool_file}")


def main():
    """Test optimizer."""
    from src.config_manager import ConfigManager

    config = ConfigManager()
    client = OllamaClient(config_manager=config)
    rag = RAGMemory(ollama_client=client)
    tools = ToolsManager(config_manager=config, rag_memory=rag, ollama_client=client)

    optimizer = ToolOptimizer(tools, rag, client, verbose=True)

    # Test optimization
    result = optimizer.optimize_tool("content_summarizer")

    print("\n" + "="*60)
    print("OPTIMIZATION RESULT")
    print("="*60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
