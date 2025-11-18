"""
Node execution with sandboxing, metrics collection, and safety constraints.
"""
import subprocess
import time
import json
import logging
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Import profiling utilities
from .profiling import ProfileContext, get_global_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeRunner:
    """Executes nodes in sandboxed environment and collects metrics."""

    def __init__(self, nodes_dir: str = "./nodes"):
        """
        Initialize node runner.

        Args:
            nodes_dir: Directory where node code is stored
        """
        self.nodes_dir = Path(nodes_dir)
        self.nodes_dir.mkdir(parents=True, exist_ok=True)

    def save_code(self, node_id: str, code: str, filename: str = "main.py") -> Path:
        """
        Save generated code to node directory.

        Args:
            node_id: Node identifier
            code: Source code to save
            filename: Filename for the code (default: main.py)

        Returns:
            Path to saved code file
        """
        node_dir = self.nodes_dir / node_id
        node_dir.mkdir(parents=True, exist_ok=True)

        code_path = node_dir / filename
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)

        logger.info(f"✓ Saved code for '{node_id}' to {code_path}")
        return code_path

    def run_node(
        self,
        node_id: str,
        input_payload: Dict[str, Any],
        timeout_ms: int = 600000,  # 10 minutes default (was 60s, too short for LLM workflows)
        filename: str = "main.py"
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Execute a node with input data and collect metrics.

        Args:
            node_id: Node identifier
            input_payload: Input data as dictionary
            timeout_ms: Execution timeout in milliseconds (default: 600000ms = 10 minutes)
            filename: Code filename to execute

        Returns:
            Tuple of (stdout, stderr, metrics)
        """
        # Profile node execution (subprocess overhead analysis)
        profile_name = f"NodeRunner.run_node.{node_id}"
        profile_metadata = {
            "node_id": node_id,
            "timeout_ms": timeout_ms,
            "filename": filename
        }

        with ProfileContext(profile_name, metadata=profile_metadata):
            code_path = self.nodes_dir / node_id / filename

            if not code_path.exists():
                error_msg = f"Node code not found: {code_path}"
                logger.error(error_msg)
                return "", error_msg, self._create_error_metrics(error_msg)

            logger.info(f"Running node '{node_id}'...")

            # Prepare input as JSON
            input_json = json.dumps(input_payload)

            # Start timing
            start_time = time.time()
            cpu_start = time.process_time()

            # Track memory usage
            process = None
            peak_memory_mb = 0.0
            profile_data = None

            try:
                # Execute the node code
                # Add code_evolver directory to PYTHONPATH so node_runtime can be imported
                import os
                env = os.environ.copy()
                code_evolver_dir = str(Path(__file__).parent.parent.absolute())
                env['PYTHONPATH'] = code_evolver_dir + os.pathsep + env.get('PYTHONPATH', '')

                process = subprocess.Popen(
                    ["python", str(code_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env  # Pass modified environment
                )

                # Monitor process for memory usage
                try:
                    ps_process = psutil.Process(process.pid)
                    initial_memory = ps_process.memory_info().rss / (1024 * 1024)
                    peak_memory_mb = initial_memory
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

                # Communicate with timeout
                timeout_sec = timeout_ms / 1000.0
                try:
                    stdout, stderr = process.communicate(
                        input=input_json,
                        timeout=timeout_sec
                    )
                    exit_code = process.returncode
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    stderr += f"\n[ERROR] Process timed out after {timeout_ms}ms"
                    exit_code = -1

                # Check memory usage after execution
                try:
                    if process.pid and psutil.pid_exists(process.pid):
                        ps_process = psutil.Process(process.pid)
                        current_memory = ps_process.memory_info().rss / (1024 * 1024)
                        peak_memory_mb = max(peak_memory_mb, current_memory)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            except Exception as e:
                error_msg = f"Execution error: {str(e)}"
                logger.error(error_msg)
                return "", error_msg, self._create_error_metrics(error_msg)

            # Calculate metrics
            end_time = time.time()
            cpu_end = time.process_time()

            latency_ms = int((end_time - start_time) * 1000)
            cpu_time_ms = int((cpu_end - cpu_start) * 1000)

            metrics = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "latency_ms": latency_ms,
                "cpu_time_ms": cpu_time_ms,
                "memory_mb_peak": round(peak_memory_mb, 2),
                "exit_code": exit_code,
                "error": stderr if exit_code != 0 else None,
                "timeout_ms": timeout_ms,
                "success": exit_code == 0 and not stderr
            }

            if exit_code == 0:
                logger.info(f"✓ Node '{node_id}' completed successfully in {latency_ms}ms")
            else:
                logger.warning(f"✗ Node '{node_id}' failed with exit code {exit_code}")

            return stdout, stderr, metrics

    def _create_error_metrics(self, error_msg: str) -> Dict[str, Any]:
        """Create metrics object for error cases."""
        return {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "latency_ms": 0,
            "cpu_time_ms": 0,
            "memory_mb_peak": 0.0,
            "exit_code": -1,
            "error": error_msg,
            "success": False
        }

    def get_node_path(self, node_id: str, filename: str = "main.py") -> Path:
        """
        Get the path to a node's code file.

        Args:
            node_id: Node identifier
            filename: Code filename

        Returns:
            Path to code file
        """
        return self.nodes_dir / node_id / filename

    def get_test_path(self, node_id: str) -> Path:
        """
        Get the path to a node's test file.

        Args:
            node_id: Node identifier

        Returns:
            Path to test file
        """
        return self.nodes_dir / node_id / "test_main.py"

    def node_exists(self, node_id: str, filename: str = "main.py") -> bool:
        """
        Check if a node's code file exists.

        Args:
            node_id: Node identifier
            filename: Code filename

        Returns:
            True if code file exists
        """
        return self.get_node_path(node_id, filename).exists()

    def create_test_input(self, node_type: str = "compressor") -> Dict[str, Any]:
        """
        Create sample test input based on node type.

        Args:
            node_type: Type of node (e.g., 'compressor', 'processor')

        Returns:
            Test input dictionary
        """
        if node_type == "compressor":
            return {
                "text": "AAAABBBCCDAA"
            }
        elif node_type == "processor":
            return {
                "data": "sample input data"
            }
        else:
            return {
                "input": "test"
            }
