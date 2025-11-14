#!/usr/bin/env python3
"""
Orchestrator CLI - Main entry point for code evolution system.
Manages workflows for generating, executing, and evaluating code nodes.
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from src import OllamaClient, Registry, NodeRunner, Evaluator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator for code evolution workflows."""

    def __init__(
        self,
        registry_path: str = "./registry",
        nodes_path: str = "./nodes"
    ):
        """
        Initialize orchestrator.

        Args:
            registry_path: Path to registry directory
            nodes_path: Path to nodes directory
        """
        self.client = OllamaClient()
        self.registry = Registry(registry_path)
        self.runner = NodeRunner(nodes_path)
        self.evaluator = Evaluator(self.client)

    def check_setup(self) -> bool:
        """
        Check if Ollama is running and required models are available.

        Returns:
            True if setup is valid
        """
        logger.info("Checking Ollama setup...")

        if not self.client.check_connection():
            logger.error("Cannot connect to Ollama. Is it running?")
            logger.error("Start Ollama with: ollama serve")
            return False

        models = self.client.list_models()
        logger.info(f"Available models: {', '.join(models) if models else 'none'}")

        required_models = ["codellama", "llama3", "tiny"]
        missing_models = [m for m in required_models if m not in models]

        if missing_models:
            logger.warning(f"Missing models: {', '.join(missing_models)}")
            logger.warning("Install with:")
            for model in missing_models:
                logger.warning(f"  ollama pull {model}")
            return False

        logger.info("✓ Setup OK")
        return True

    def generate_node(
        self,
        node_id: str,
        title: str,
        prompt: str,
        node_type: str = "processor",
        tags: list = None,
        goals: dict = None
    ) -> bool:
        """
        Generate a new node from a prompt.

        Args:
            node_id: Unique identifier
            title: Human-readable title
            prompt: Code generation prompt
            node_type: Type of node
            tags: List of tags
            goals: Goal definitions

        Returns:
            True if successful
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Generating node: {node_id}")
        logger.info(f"{'='*60}")

        # Create node definition in registry
        node_def = self.registry.create_node(
            node_id=node_id,
            title=title,
            node_type=node_type,
            tags=tags or ["generated"],
            goals=goals
        )

        # Generate code
        logger.info("Generating code with codellama...")
        code = self.client.generate_code(prompt)

        if not code or len(code) < 10:
            logger.error("Failed to generate valid code")
            return False

        # Save code
        self.runner.save_code(node_id, code)

        logger.info(f"✓ Node '{node_id}' generated successfully")
        return True

    def run_node(
        self,
        node_id: str,
        input_data: dict = None,
        evaluate: bool = True
    ) -> bool:
        """
        Run an existing node with input data.

        Args:
            node_id: Node identifier
            input_data: Input data dictionary
            evaluate: Whether to run evaluation (default: True)

        Returns:
            True if successful
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Running node: {node_id}")
        logger.info(f"{'='*60}")

        # Get node definition
        node_def = self.registry.get_node(node_id)
        if not node_def:
            logger.error(f"Node '{node_id}' not found in registry")
            return False

        # Check if code exists
        if not self.runner.node_exists(node_id):
            logger.error(f"No code found for node '{node_id}'")
            return False

        # Use default test input if none provided
        if input_data is None:
            node_type = node_def.get("type", "processor")
            input_data = self.runner.create_test_input(node_type)
            logger.info(f"Using default test input: {input_data}")

        # Get constraints
        constraints = node_def.get("constraints", {})
        timeout_ms = constraints.get("timeout_ms", 5000)

        # Run the node
        stdout, stderr, metrics = self.runner.run_node(
            node_id=node_id,
            input_payload=input_data,
            timeout_ms=timeout_ms
        )

        # Save metrics and log
        self.registry.save_metrics(node_id, metrics)
        log_content = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}\n\nMETRICS:\n{json.dumps(metrics, indent=2)}"
        self.registry.save_run_log(node_id, log_content)

        # Print results
        logger.info(f"\nResults:")
        logger.info(f"  Exit code: {metrics['exit_code']}")
        logger.info(f"  Latency: {metrics['latency_ms']}ms")
        logger.info(f"  Memory: {metrics['memory_mb_peak']}MB")

        if stdout:
            logger.info(f"\nOutput:\n{stdout[:500]}")

        if stderr:
            logger.warning(f"\nErrors:\n{stderr[:500]}")

        # Evaluate if requested
        if evaluate:
            return self.evaluate_node(node_id, stdout, stderr, metrics, node_def)

        return metrics["success"]

    def evaluate_node(
        self,
        node_id: str,
        stdout: str = None,
        stderr: str = None,
        metrics: dict = None,
        node_def: dict = None
    ) -> bool:
        """
        Evaluate a node's execution results.

        Args:
            node_id: Node identifier
            stdout: Standard output (loads from registry if None)
            stderr: Standard error (loads from registry if None)
            metrics: Metrics (loads from registry if None)
            node_def: Node definition (loads from registry if None)

        Returns:
            True if evaluation passes
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Evaluating node: {node_id}")
        logger.info(f"{'='*60}")

        # Load data from registry if not provided
        if metrics is None:
            metrics = self.registry.get_metrics(node_id)
            if not metrics:
                logger.error("No metrics found")
                return False

        if node_def is None:
            node_def = self.registry.get_node(node_id)

        # Get goals and targets
        goals = node_def.get("goals") if node_def else None

        # Run evaluation
        result = self.evaluator.evaluate_full(
            stdout=stdout or "",
            stderr=stderr or "",
            metrics=metrics,
            goals=goals
        )

        # Save evaluation
        eval_data = {
            "score_overall": result["final_score"],
            "verdict": result["final_verdict"],
            "triage": result.get("triage"),
            "evaluation": result.get("evaluation")
        }
        self.registry.save_evaluation(node_id, eval_data)

        # Update index
        tags = node_def.get("tags", []) if node_def else []
        version = node_def.get("version", "1.0.0") if node_def else "1.0.0"
        self.registry.update_index(
            node_id=node_id,
            version=version,
            tags=tags,
            score_overall=result["final_score"]
        )

        # Print results
        logger.info(f"\nEvaluation Results:")
        logger.info(f"  Verdict: {result['final_verdict']}")
        logger.info(f"  Score: {result['final_score']:.2f}")

        if result.get("evaluation"):
            scores = result["evaluation"].get("scores", {})
            logger.info(f"  Detailed scores:")
            for key, value in scores.items():
                logger.info(f"    {key}: {value:.2f}")

        return result["final_verdict"] == "pass"

    def list_nodes(self):
        """List all nodes in the registry."""
        nodes = self.registry.list_nodes()

        if not nodes:
            logger.info("No nodes in registry")
            return

        logger.info(f"\nRegistry contains {len(nodes)} node(s):")
        logger.info(f"{'='*80}")

        for node in nodes:
            node_id = node.get("node_id", "unknown")
            version = node.get("version", "?")
            score = node.get("score_overall", 0.0)
            tags = ", ".join(node.get("tags", []))

            logger.info(f"  {node_id} (v{version})")
            logger.info(f"    Score: {score:.2f}")
            logger.info(f"    Tags: {tags}")
            logger.info(f"")

    def generate_and_run(
        self,
        node_id: str,
        title: str,
        prompt: str,
        input_data: dict = None,
        **kwargs
    ) -> bool:
        """
        Full workflow: generate, run, and evaluate a node.

        Args:
            node_id: Node identifier
            title: Node title
            prompt: Code generation prompt
            input_data: Input data for execution
            **kwargs: Additional node creation parameters

        Returns:
            True if all steps succeed
        """
        # Generate
        if not self.generate_node(node_id, title, prompt, **kwargs):
            return False

        # Run and evaluate
        return self.run_node(node_id, input_data, evaluate=True)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Code Evolution Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Check command
    subparsers.add_parser("check", help="Check Ollama setup")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate a new node")
    gen_parser.add_argument("node_id", help="Unique node identifier")
    gen_parser.add_argument("title", help="Node title")
    gen_parser.add_argument("prompt", help="Code generation prompt")
    gen_parser.add_argument("--type", default="processor", help="Node type")
    gen_parser.add_argument("--tags", nargs="+", help="Tags")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run an existing node")
    run_parser.add_argument("node_id", help="Node identifier")
    run_parser.add_argument("--input", help="Input JSON file or string")
    run_parser.add_argument("--no-eval", action="store_true", help="Skip evaluation")

    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate a node")
    eval_parser.add_argument("node_id", help="Node identifier")

    # List command
    subparsers.add_parser("list", help="List all nodes")

    # Full workflow command
    full_parser = subparsers.add_parser("full", help="Generate, run, and evaluate")
    full_parser.add_argument("node_id", help="Node identifier")
    full_parser.add_argument("title", help="Node title")
    full_parser.add_argument("prompt", help="Code generation prompt")
    full_parser.add_argument("--input", help="Input JSON file or string")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize orchestrator
    orch = Orchestrator()

    # Execute command
    if args.command == "check":
        return 0 if orch.check_setup() else 1

    elif args.command == "generate":
        success = orch.generate_node(
            node_id=args.node_id,
            title=args.title,
            prompt=args.prompt,
            node_type=args.type,
            tags=args.tags
        )
        return 0 if success else 1

    elif args.command == "run":
        input_data = None
        if args.input:
            try:
                # Try as JSON string first
                input_data = json.loads(args.input)
            except json.JSONDecodeError:
                # Try as file path
                with open(args.input) as f:
                    input_data = json.load(f)

        success = orch.run_node(
            node_id=args.node_id,
            input_data=input_data,
            evaluate=not args.no_eval
        )
        return 0 if success else 1

    elif args.command == "evaluate":
        success = orch.evaluate_node(node_id=args.node_id)
        return 0 if success else 1

    elif args.command == "list":
        orch.list_nodes()
        return 0

    elif args.command == "full":
        input_data = None
        if args.input:
            try:
                input_data = json.loads(args.input)
            except json.JSONDecodeError:
                with open(args.input) as f:
                    input_data = json.load(f)

        success = orch.generate_and_run(
            node_id=args.node_id,
            title=args.title,
            prompt=args.prompt,
            input_data=input_data
        )
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
