"""
Auto-Evolution Engine - Monitors performance and triggers improvements.
Automatically evolves nodes when performance degrades or opportunities arise.
"""
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .ollama_client import OllamaClient
from .registry import Registry
from .node_runner import NodeRunner
from .evaluator import Evaluator
from .config_manager import ConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoEvolver:
    """Automatic code evolution based on performance monitoring."""

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        client: Optional[OllamaClient] = None,
        registry: Optional[Registry] = None,
        runner: Optional[NodeRunner] = None,
        evaluator: Optional[Evaluator] = None
    ):
        """
        Initialize auto-evolver.

        Args:
            config: Configuration manager
            client: Ollama client
            registry: Registry
            runner: Node runner
            evaluator: Evaluator
        """
        self.config = config or ConfigManager()
        self.client = client or OllamaClient(self.config.ollama_url)
        self.registry = registry or Registry(self.config.registry_path)
        self.runner = runner or NodeRunner(self.config.nodes_path)
        self.evaluator = evaluator or Evaluator(self.client)

        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.last_check: Dict[str, datetime] = {}

    def should_evolve(self, node_id: str) -> bool:
        """
        Determine if a node should be evolved based on performance history.

        Args:
            node_id: Node identifier

        Returns:
            True if evolution should be triggered
        """
        if not self.config.auto_evolution_enabled:
            return False

        # Check minimum runs requirement
        min_runs = self.config.get("auto_evolution.min_runs_before_evolution", 3)
        history = self.performance_history.get(node_id, [])

        if len(history) < min_runs:
            logger.debug(f"Not enough runs for {node_id}: {len(history)}/{min_runs}")
            return False

        # Check if enough time has passed since last check
        check_interval = self.config.get("auto_evolution.check_interval_minutes", 60)
        last_check = self.last_check.get(node_id)

        if last_check:
            elapsed = datetime.utcnow() - last_check
            if elapsed < timedelta(minutes=check_interval):
                return False

        # Update last check time
        self.last_check[node_id] = datetime.utcnow()

        # Analyze performance trend
        recent_scores = [h.get("score", 0) for h in history[-min_runs:]]
        avg_recent = sum(recent_scores) / len(recent_scores)

        # Get historical average (if more data available)
        if len(history) > min_runs:
            older_scores = [h.get("score", 0) for h in history[:-min_runs]]
            avg_older = sum(older_scores) / len(older_scores)

            # Calculate performance change
            threshold = self.config.get("auto_evolution.performance_threshold", 0.15)
            change = (avg_recent - avg_older) / avg_older if avg_older > 0 else 0

            # Trigger if performance degraded significantly
            if change < -threshold:
                logger.info(f"Performance degraded for {node_id}: {change:.2%}")
                return True

            # Also trigger if there's room for improvement (low score)
            if avg_recent < 0.7:
                logger.info(f"Low score for {node_id}: {avg_recent:.2f}")
                return True

        return False

    def record_performance(self, node_id: str, metrics: Dict[str, Any], score: float):
        """
        Record performance for a node.

        Args:
            node_id: Node identifier
            metrics: Execution metrics
            score: Evaluation score
        """
        if node_id not in self.performance_history:
            self.performance_history[node_id] = []

        self.performance_history[node_id].append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": metrics,
            "score": score
        })

        # Keep only recent history
        max_history = 100
        if len(self.performance_history[node_id]) > max_history:
            self.performance_history[node_id] = self.performance_history[node_id][-max_history:]

    def evolve_node(self, node_id: str) -> Optional[str]:
        """
        Evolve a node to improve its performance.

        Args:
            node_id: Node identifier to evolve

        Returns:
            New node ID if successful, None otherwise
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Evolving node: {node_id}")
        logger.info(f"{'='*60}")

        # Load node definition and code
        node_def = self.registry.get_node(node_id)
        if not node_def:
            logger.error(f"Node {node_id} not found")
            return None

        code_path = self.runner.get_node_path(node_id)
        if not code_path.exists():
            logger.error(f"Code not found for {node_id}")
            return None

        with open(code_path, 'r', encoding='utf-8') as f:
            current_code = f.read()

        # Get performance history
        history = self.performance_history.get(node_id, [])
        recent_metrics = [h["metrics"] for h in history[-3:]]
        recent_scores = [h["score"] for h in history[-3:]]

        # Generate improvement prompt using overseer
        logger.info(f"Consulting overseer ({self.config.overseer_model}) for improvement strategy...")

        overseer_prompt = f"""Analyze this code and suggest improvements:

Current Implementation:
```python
{current_code}
```

Performance History:
- Average Score: {sum(recent_scores)/len(recent_scores) if recent_scores else 0:.2f}
- Recent Metrics: {recent_metrics}

Goals:
{node_def.get('goals', {})}

Provide:
1. Performance bottlenecks or issues
2. Specific optimization strategies
3. Alternative algorithms or approaches
4. Expected improvement areas

Be specific and actionable."""

        strategy = self.client.generate(
            model=self.config.overseer_model,
            prompt=overseer_prompt,
            temperature=0.7
        )

        logger.info("✓ Strategy generated")

        # Generate improved code
        logger.info(f"Generating improved code with {self.config.generator_model}...")

        improvement_prompt = f"""Improve this code based on the following strategy:

Strategy:
{strategy}

Current Code:
```python
{current_code}
```

Requirements:
1. Maintain the same interface (inputs/outputs)
2. Fix identified issues
3. Implement suggested optimizations
4. Preserve correctness
5. Keep dependencies minimal

Return ONLY the improved Python code."""

        improved_code = self.client.generate(
            model=self.config.generator_model,
            prompt=improvement_prompt,
            temperature=self.config.get("auto_evolution.mutation_temperature", 0.7)
        )

        if not improved_code or len(improved_code) < 50:
            logger.error("Failed to generate improved code")
            return None

        # Create new version
        current_version = node_def.get("version", "1.0.0")
        major, minor, patch = map(int, current_version.split('.'))
        new_version = f"{major}.{minor+1}.{patch}"

        new_node_id = f"{node_id}_v{minor+1}"

        # Create new node in registry
        new_node_def = node_def.copy()
        new_node_def.update({
            "node_id": new_node_id,
            "version": new_version,
            "lineage": {
                "parent": node_id,
                "derived_from": [node_id],
                "notes": f"Auto-evolved from {node_id} - performance improvement attempt"
            }
        })

        self.registry.create_node(**new_node_def)
        self.runner.save_code(new_node_id, improved_code)

        logger.info(f"✓ Created evolved version: {new_node_id}")

        # Test the new version
        logger.info("Testing evolved version...")

        # Use same test input as original
        test_input = self.runner.create_test_input(node_def.get("type", "processor"))

        stdout, stderr, metrics = self.runner.run_node(new_node_id, test_input)
        self.registry.save_metrics(new_node_id, metrics)

        # Evaluate
        result = self.evaluator.evaluate_full(
            stdout=stdout,
            stderr=stderr,
            metrics=metrics,
            goals=new_node_def.get("goals")
        )

        eval_data = {
            "score_overall": result["final_score"],
            "verdict": result["final_verdict"],
            "evaluation": result.get("evaluation")
        }
        self.registry.save_evaluation(new_node_id, eval_data)

        # Update index
        self.registry.update_index(
            node_id=new_node_id,
            version=new_version,
            tags=new_node_def.get("tags", []),
            score_overall=result["final_score"]
        )

        # Compare performance
        old_score = sum(recent_scores) / len(recent_scores) if recent_scores else 0
        new_score = result["final_score"]

        logger.info(f"\n{'='*60}")
        logger.info(f"Evolution Results:")
        logger.info(f"  Old Score: {old_score:.2f}")
        logger.info(f"  New Score: {new_score:.2f}")
        logger.info(f"  Improvement: {((new_score - old_score) / old_score * 100) if old_score > 0 else 0:.1f}%")
        logger.info(f"{'='*60}")

        # Keep best version
        if new_score > old_score:
            logger.info(f"✓ New version is better! Keeping {new_node_id}")
            return new_node_id
        else:
            logger.info(f"New version didn't improve. Keeping original {node_id}")
            # Could delete new version here, but keeping for analysis
            return None

    def monitor_and_evolve(self, interval_minutes: int = 60, max_iterations: int = 10):
        """
        Continuously monitor nodes and trigger evolution as needed.

        Args:
            interval_minutes: Check interval in minutes
            max_iterations: Maximum monitoring iterations (0 = infinite)
        """
        logger.info(f"Starting auto-evolution monitor (interval: {interval_minutes}min)")

        iteration = 0

        while max_iterations == 0 or iteration < max_iterations:
            try:
                # Get all nodes
                nodes = self.registry.list_nodes()

                for node_entry in nodes:
                    node_id = node_entry.get("node_id")

                    if self.should_evolve(node_id):
                        logger.info(f"\nTriggering evolution for {node_id}")
                        new_node_id = self.evolve_node(node_id)

                        if new_node_id:
                            logger.info(f"✓ Evolution successful: {new_node_id}")

                # Sleep until next check
                logger.info(f"\nSleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)

                iteration += 1

            except KeyboardInterrupt:
                logger.info("\n✓ Auto-evolution monitor stopped")
                break

            except Exception as e:
                logger.error(f"Error in auto-evolution monitor: {e}")
                time.sleep(60)  # Sleep 1 minute on error

    def prune_old_versions(self, node_id_prefix: str):
        """
        Remove old versions of a node, keeping only the best ones.

        Args:
            node_id_prefix: Node ID prefix (e.g., "compress_text")
        """
        max_versions = self.config.get("auto_evolution.max_versions_per_node", 10)
        keep_best = self.config.get("auto_evolution.keep_best_n_versions", 3)

        nodes = self.registry.list_nodes()

        # Find all versions of this node
        versions = [n for n in nodes if n.get("node_id", "").startswith(node_id_prefix)]

        if len(versions) <= max_versions:
            return

        # Sort by score
        versions.sort(key=lambda x: x.get("score_overall", 0), reverse=True)

        # Keep best N and most recent
        to_keep = set([v["node_id"] for v in versions[:keep_best]])

        # Also keep most recent
        versions_by_date = sorted(versions, key=lambda x: x.get("updated_at", ""), reverse=True)
        to_keep.add(versions_by_date[0]["node_id"])

        # Remove others
        for version in versions:
            if version["node_id"] not in to_keep:
                logger.info(f"Pruning old version: {version['node_id']}")
                # Note: Would implement actual deletion here
