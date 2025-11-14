"""
File-based registry for storing node definitions, metrics, and evaluations.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Registry:
    """File-based registry for managing code evolution nodes."""

    def __init__(self, registry_path: str = "./registry"):
        """
        Initialize registry.

        Args:
            registry_path: Path to registry directory
        """
        self.registry_path = Path(registry_path)
        self.index_path = self.registry_path / "index.json"
        self._ensure_registry_exists()

    def _ensure_registry_exists(self):
        """Create registry directory structure if it doesn't exist."""
        self.registry_path.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._save_json(self.index_path, {"nodes": []})
            logger.info(f"Created new registry at {self.registry_path}")

    def _save_json(self, path: Path, data: Dict[str, Any]):
        """Save data as JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON file."""
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_node(
        self,
        node_id: str,
        title: str,
        version: str = "1.0.0",
        node_type: str = "processor",
        language: str = "python",
        tags: Optional[List[str]] = None,
        goals: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, str]] = None,
        outputs: Optional[Dict[str, str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new node definition in the registry.

        Args:
            node_id: Unique identifier for the node
            title: Human-readable title
            version: Version string (default: "1.0.0")
            node_type: Type of node (default: "processor")
            language: Programming language (default: "python")
            tags: List of tags
            goals: Goal definitions
            inputs: Input schema
            outputs: Output schema
            constraints: Execution constraints
            **kwargs: Additional fields

        Returns:
            Node definition dictionary
        """
        node_dir = self.registry_path / node_id
        node_dir.mkdir(parents=True, exist_ok=True)

        node_def = {
            "node_id": node_id,
            "title": title,
            "version": version,
            "type": node_type,
            "language": language,
            "tags": tags or [],
            "goals": goals or {
                "primary": ["correctness", "determinism"],
                "secondary": ["latency<200ms", "memory<64MB"]
            },
            "inputs": inputs or {},
            "outputs": outputs or {},
            "constraints": constraints or {
                "timeout_ms": 5000,
                "max_memory_mb": 256
            },
            "lineage": {
                "parent": None,
                "derived_from": [],
                "notes": "Initial version"
            },
            "fit": {
                "domain": kwargs.get("domain", "general"),
                "scale": kwargs.get("scale", "small"),
                "risk": kwargs.get("risk", "low")
            },
            "model_prompts": {
                "generator": "codellama",
                "evaluator": "llama3",
                "triage": "tiny"
            },
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        # Add any additional kwargs
        for key, value in kwargs.items():
            if key not in node_def:
                node_def[key] = value

        node_path = node_dir / "node.json"
        self._save_json(node_path, node_def)
        logger.info(f"✓ Created node '{node_id}' v{version}")

        return node_def

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get node definition by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node definition or None if not found
        """
        node_path = self.registry_path / node_id / "node.json"
        if not node_path.exists():
            logger.warning(f"Node '{node_id}' not found")
            return None
        return self._load_json(node_path)

    def save_metrics(self, node_id: str, metrics: Dict[str, Any]):
        """
        Save execution metrics for a node.

        Args:
            node_id: Node identifier
            metrics: Metrics dictionary
        """
        metrics_path = self.registry_path / node_id / "metrics.json"
        self._save_json(metrics_path, metrics)
        logger.info(f"✓ Saved metrics for '{node_id}'")

    def get_metrics(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a node."""
        metrics_path = self.registry_path / node_id / "metrics.json"
        if not metrics_path.exists():
            return None
        return self._load_json(metrics_path)

    def save_evaluation(self, node_id: str, evaluation: Dict[str, Any]):
        """
        Save evaluation results for a node.

        Args:
            node_id: Node identifier
            evaluation: Evaluation dictionary
        """
        eval_path = self.registry_path / node_id / "evaluation.json"
        self._save_json(eval_path, evaluation)
        logger.info(f"✓ Saved evaluation for '{node_id}'")

    def get_evaluation(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get evaluation for a node."""
        eval_path = self.registry_path / node_id / "evaluation.json"
        if not eval_path.exists():
            return None
        return self._load_json(eval_path)

    def save_run_log(self, node_id: str, log_content: str):
        """
        Save execution log for a node.

        Args:
            node_id: Node identifier
            log_content: Log text content
        """
        log_path = self.registry_path / node_id / "run.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            timestamp = datetime.utcnow().isoformat()
            f.write(f"\n--- {timestamp} ---\n")
            f.write(log_content)
            f.write("\n")
        logger.info(f"✓ Saved run log for '{node_id}'")

    def update_index(self, node_id: str, version: str, tags: List[str], score_overall: float):
        """
        Update the registry index with node information.

        Args:
            node_id: Node identifier
            version: Node version
            tags: List of tags
            score_overall: Overall evaluation score
        """
        index = self._load_json(self.index_path)
        if "nodes" not in index:
            index["nodes"] = []

        # Remove existing entry for this node
        index["nodes"] = [n for n in index["nodes"] if n.get("node_id") != node_id]

        # Add updated entry
        index["nodes"].append({
            "node_id": node_id,
            "version": version,
            "tags": tags,
            "score_overall": score_overall,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })

        # Sort by score descending
        index["nodes"].sort(key=lambda x: x.get("score_overall", 0), reverse=True)

        self._save_json(self.index_path, index)
        logger.info(f"✓ Updated index for '{node_id}' (score: {score_overall:.2f})")

    def list_nodes(self) -> List[Dict[str, Any]]:
        """
        List all nodes in the registry.

        Returns:
            List of node entries from index
        """
        index = self._load_json(self.index_path)
        return index.get("nodes", [])

    def get_node_dir(self, node_id: str) -> Path:
        """
        Get the directory path for a node.

        Args:
            node_id: Node identifier

        Returns:
            Path to node directory
        """
        return self.registry_path / node_id

    def get_artifacts_dir(self, node_id: str) -> Path:
        """
        Get or create artifacts directory for a node.

        Args:
            node_id: Node identifier

        Returns:
            Path to artifacts directory
        """
        artifacts_dir = self.registry_path / node_id / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        return artifacts_dir
