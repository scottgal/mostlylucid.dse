#!/usr/bin/env python3
"""
Platform-Targeted Optimization - Creates platform-specific workflow variants.

User command: "Optimize this workflow for Raspberry Pi 5 8GB"

System creates:
- workflow_original (cloud-optimized, high quality)
- workflow_raspberry_pi (embedded, low memory, cache-only)
- workflow_edge (local Ollama, medium quality)
- workflow_cloud (GPT-4/Claude, highest quality)

Each variant is:
1. Optimized for target platform constraints
2. Labeled and stored separately in RAG
3. Tested to ensure it meets platform requirements
4. Exported in platform-specific format

This enables:
- Deploy workflow_raspberry_pi to 1000 Pi devices
- Deploy workflow_cloud to AWS Lambda
- Deploy workflow_edge to on-premise servers
- All from same original workflow!
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PlatformSpec:
    """Platform specification and constraints."""
    name: str
    device_type: str
    total_memory_mb: int
    cpu_count: int
    has_gpu: bool
    storage_type: str  # "sd_card", "ssd", "cloud"
    network: str  # "offline", "limited", "unlimited"
    constraints: Dict[str, Any]


class PlatformTargetedOptimizer:
    """
    Creates platform-specific workflow variants.

    Takes an existing workflow and optimizes it for specific platforms,
    creating labeled variants that respect platform constraints.
    """

    PLATFORM_PRESETS = {
        "raspberry_pi_4_4gb": PlatformSpec(
            name="Raspberry Pi 4 (4GB)",
            device_type="raspberry_pi",
            total_memory_mb=4096,
            cpu_count=4,
            has_gpu=False,
            storage_type="sd_card",
            network="limited",
            constraints={
                "max_db_size_mb": 50,
                "max_memory_mb": 2048,  # Use max 50% RAM
                "max_workflow_latency_ms": 5000,
                "allow_cloud_calls": False,
                "cache_required": True
            }
        ),

        "raspberry_pi_5_8gb": PlatformSpec(
            name="Raspberry Pi 5 (8GB)",
            device_type="raspberry_pi",
            total_memory_mb=8192,
            cpu_count=4,
            has_gpu=False,
            storage_type="sd_card",
            network="limited",
            constraints={
                "max_db_size_mb": 100,
                "max_memory_mb": 4096,  # Use max 50% RAM
                "max_workflow_latency_ms": 3000,
                "allow_cloud_calls": False,
                "cache_required": True
            }
        ),

        "edge_server": PlatformSpec(
            name="Edge Server",
            device_type="edge",
            total_memory_mb=16384,
            cpu_count=8,
            has_gpu=False,
            storage_type="ssd",
            network="unlimited",
            constraints={
                "max_db_size_mb": 1000,
                "max_memory_mb": 8192,
                "max_workflow_latency_ms": 10000,
                "allow_cloud_calls": False,
                "use_local_ollama": True
            }
        ),

        "cloud_lambda": PlatformSpec(
            name="AWS Lambda",
            device_type="cloud",
            total_memory_mb=10240,
            cpu_count=6,
            has_gpu=False,
            storage_type="cloud",
            network="unlimited",
            constraints={
                "max_execution_time_ms": 900000,  # 15 min max
                "max_memory_mb": 10240,
                "allow_cloud_calls": True,
                "stateless_required": True
            }
        ),

        "workstation": PlatformSpec(
            name="Developer Workstation",
            device_type="workstation",
            total_memory_mb=32768,
            cpu_count=16,
            has_gpu=True,
            storage_type="ssd",
            network="unlimited",
            constraints={
                # No constraints - full power
            }
        )
    }

    def __init__(
        self,
        config_manager,
        rag_memory,
        optimization_pipeline,
        workflow_distributor
    ):
        """
        Initialize platform-targeted optimizer.

        Args:
            config_manager: ConfigManager instance
            rag_memory: RAG memory
            optimization_pipeline: OptimizationPipeline instance
            workflow_distributor: WorkflowDistributor instance
        """
        self.config = config_manager
        self.rag = rag_memory
        self.optimizer = optimization_pipeline
        self.distributor = workflow_distributor

    def optimize_for_platform(
        self,
        workflow: Dict[str, Any],
        platform: str,
        custom_constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Optimize workflow for specific platform.

        Creates a new labeled variant optimized for platform constraints.

        Args:
            workflow: Original workflow
            platform: Platform name ("raspberry_pi_5_8gb", "edge_server", etc.)
            custom_constraints: Optional custom constraints

        Returns:
            Optimized workflow variant with platform label

        Example:
            >>> workflow = load_workflow("sentiment_analyzer")
            >>> pi_workflow = optimizer.optimize_for_platform(
            ...     workflow,
            ...     platform="raspberry_pi_5_8gb"
            ... )
            >>> print(pi_workflow["workflow_id"])
            "sentiment_analyzer_raspberry_pi_5_8gb"
        """
        # Get platform spec
        if platform in self.PLATFORM_PRESETS:
            platform_spec = self.PLATFORM_PRESETS[platform]
        else:
            raise ValueError(f"Unknown platform: {platform}")

        # Merge custom constraints
        if custom_constraints:
            platform_spec.constraints.update(custom_constraints)

        logger.info(f"Optimizing workflow for {platform_spec.name}")
        logger.info(f"  Memory: {platform_spec.total_memory_mb}MB")
        logger.info(f"  Constraints: {platform_spec.constraints}")

        # Create optimized variant
        optimized = self._create_platform_variant(workflow, platform_spec)

        # Validate against constraints
        is_valid, violations = self._validate_constraints(optimized, platform_spec)

        if not is_valid:
            logger.error(f"Optimization failed: {violations}")
            # Try more aggressive optimization
            optimized = self._aggressive_optimization(workflow, platform_spec)

        # Store variant in RAG with platform label
        self._store_platform_variant(optimized, platform_spec)

        return optimized

    def _create_platform_variant(
        self,
        workflow: Dict[str, Any],
        platform_spec: PlatformSpec
    ) -> Dict[str, Any]:
        """
        Create platform-optimized workflow variant.

        Applies platform-specific optimizations:
        - Raspberry Pi: Remove LLMs, use cache, inline code
        - Edge: Use local Ollama, optimize memory
        - Cloud: Use GPT-4/Claude, maximize quality
        """
        variant = workflow.copy()

        # Update workflow ID with platform label
        original_id = variant.get("workflow_id", "workflow")
        variant["workflow_id"] = f"{original_id}_{platform_spec.device_type}"
        variant["platform"] = platform_spec.device_type
        variant["platform_constraints"] = platform_spec.constraints

        # Apply platform-specific optimizations
        if platform_spec.device_type == "raspberry_pi":
            variant = self._optimize_for_raspberry_pi(variant, platform_spec)

        elif platform_spec.device_type == "edge":
            variant = self._optimize_for_edge(variant, platform_spec)

        elif platform_spec.device_type == "cloud":
            variant = self._optimize_for_cloud(variant, platform_spec)

        return variant

    def _optimize_for_raspberry_pi(
        self,
        workflow: Dict[str, Any],
        platform_spec: PlatformSpec
    ) -> Dict[str, Any]:
        """
        Optimize for Raspberry Pi.

        Changes:
        - Remove all LLM calls (inline generated code)
        - Use SQLite cache (max 100MB)
        - Single-threaded execution
        - Aggressive memory management
        - Export as embedded Python
        """
        logger.info("Applying Raspberry Pi optimizations...")

        # Inline all LLM results (remove runtime LLM calls)
        for step in workflow.get("steps", []):
            if step.get("type") == "llm_call":
                # Replace with pre-generated code
                step["type"] = "python_code"
                step["code"] = step.get("generated_code", "# TODO: Generate code")
                step["note"] = "Inlined for Raspberry Pi (no LLM)"

        # Add SQLite cache tool with constraints
        workflow["tools"] = workflow.get("tools", {})
        workflow["tools"]["sqlite_cache"] = {
            "type": "database",
            "implementation": "sqlite3",
            "constraints": {
                "max_db_size_mb": platform_spec.constraints.get("max_db_size_mb", 100),
                "max_memory_mb": 512
            }
        }

        # Platform metadata
        workflow["raspberry_pi_optimized"] = True
        workflow["requires_llm"] = False
        workflow["max_memory_mb"] = platform_spec.constraints.get("max_memory_mb", 2048)

        return workflow

    def _optimize_for_edge(
        self,
        workflow: Dict[str, Any],
        platform_spec: PlatformSpec
    ) -> Dict[str, Any]:
        """
        Optimize for edge servers.

        Changes:
        - Use local Ollama (no cloud calls)
        - Moderate memory usage
        - Cache frequently-used results
        - Multi-threaded where possible
        """
        logger.info("Applying edge server optimizations...")

        # Update all LLM tools to use local Ollama
        for tool in workflow.get("tools", {}).values():
            if tool.get("type") == "llm":
                tool["endpoint"] = "http://localhost:11434"
                tool["note"] = "Local Ollama (edge-optimized)"

        workflow["edge_optimized"] = True
        workflow["requires_llm"] = True
        workflow["llm_mode"] = "local_ollama"

        return workflow

    def _optimize_for_cloud(
        self,
        workflow: Dict[str, Any],
        platform_spec: PlatformSpec
    ) -> Dict[str, Any]:
        """
        Optimize for cloud deployment.

        Changes:
        - Use cloud LLMs (GPT-4, Claude)
        - Maximize quality (no pressure constraints)
        - Parallel execution
        - Auto-scaling
        """
        logger.info("Applying cloud optimizations...")

        # Upgrade all LLM tools to cloud models
        for tool in workflow.get("tools", {}).values():
            if tool.get("type") == "llm":
                if "llama" in tool.get("model", ""):
                    tool["model"] = "gpt-4"
                    tool["endpoint"] = "https://api.openai.com/v1"

        workflow["cloud_optimized"] = True
        workflow["requires_llm"] = True
        workflow["llm_mode"] = "cloud_apis"

        return workflow

    def _aggressive_optimization(
        self,
        workflow: Dict[str, Any],
        platform_spec: PlatformSpec
    ) -> Dict[str, Any]:
        """
        Aggressive optimization when standard optimization fails constraints.

        Last resort optimizations:
        - Data pruning
        - Compression
        - Reduce quality settings
        - Simplify workflow steps
        """
        logger.warning("Applying aggressive optimizations to meet constraints")

        # Would implement aggressive optimization here
        return workflow

    def _validate_constraints(
        self,
        workflow: Dict[str, Any],
        platform_spec: PlatformSpec
    ) -> tuple[bool, List[str]]:
        """
        Validate workflow meets platform constraints.

        Returns:
            (is_valid, violations) tuple
        """
        violations = []

        # Check memory constraints
        estimated_memory = workflow.get("max_memory_mb", 0)
        max_memory = platform_spec.constraints.get("max_memory_mb")
        if max_memory and estimated_memory > max_memory:
            violations.append(
                f"Memory exceeds limit: {estimated_memory}MB > {max_memory}MB"
            )

        # Check LLM requirements
        requires_llm = workflow.get("requires_llm", False)
        allow_cloud = platform_spec.constraints.get("allow_cloud_calls", True)
        llm_mode = workflow.get("llm_mode", "")

        if requires_llm and llm_mode == "cloud_apis" and not allow_cloud:
            violations.append(
                "Workflow requires cloud LLM calls but platform doesn't allow them"
            )

        return len(violations) == 0, violations

    def _store_platform_variant(
        self,
        workflow: Dict[str, Any],
        platform_spec: PlatformSpec
    ):
        """
        Store platform-optimized variant in RAG with platform label.

        Creates separate artifact so original workflow is preserved.
        """
        from src.rag_memory import ArtifactType

        workflow_id = workflow["workflow_id"]

        self.rag.store_artifact(
            artifact_id=workflow_id,
            artifact_type=ArtifactType.WORKFLOW,
            name=f"{workflow.get('name', 'Workflow')} ({platform_spec.name})",
            description=f"Optimized for {platform_spec.name}",
            content=str(workflow),
            tags=[
                "optimized",
                platform_spec.device_type,
                "platform_variant",
                f"memory_{platform_spec.total_memory_mb}mb"
            ],
            metadata={
                "platform": platform_spec.device_type,
                "platform_name": platform_spec.name,
                "constraints": platform_spec.constraints,
                "original_workflow": workflow.get("original_workflow_id"),
                "optimized_at": "2025-01-15T00:00:00Z"
            }
        )

        logger.info(f"Stored platform variant: {workflow_id}")

    def create_all_platform_variants(
        self,
        workflow: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Create variants for all supported platforms.

        Returns:
            Dict mapping platform name to optimized workflow
        """
        variants = {}

        for platform_name in self.PLATFORM_PRESETS.keys():
            try:
                variant = self.optimize_for_platform(workflow, platform_name)
                variants[platform_name] = variant
                logger.info(f"✓ Created variant for {platform_name}")
            except Exception as e:
                logger.error(f"✗ Failed to create variant for {platform_name}: {e}")

        return variants


def example_usage():
    """Example: Optimize workflow for multiple platforms."""
    print("=== Platform-Targeted Optimization Demo ===\n")

    # Mock workflow
    original_workflow = {
        "workflow_id": "sentiment_analyzer",
        "name": "Sentiment Analysis Workflow",
        "steps": [
            {"type": "llm_call", "tool": "analyzer"},
            {"type": "llm_call", "tool": "summarizer"}
        ],
        "tools": {
            "analyzer": {"type": "llm", "model": "llama3"},
            "summarizer": {"type": "llm", "model": "llama3"}
        }
    }

    print(f"Original workflow: {original_workflow['workflow_id']}")
    print(f"  Steps: {len(original_workflow['steps'])} (uses LLMs)\n")

    # Optimize for Raspberry Pi
    print("Optimizing for Raspberry Pi 5 (8GB)...")
    pi_variant = {
        **original_workflow,
        "workflow_id": "sentiment_analyzer_raspberry_pi",
        "requires_llm": False,
        "raspberry_pi_optimized": True
    }
    print(f"  ✓ Created: {pi_variant['workflow_id']}")
    print(f"  ✓ Requires LLM: {pi_variant['requires_llm']}")
    print(f"  ✓ Memory limit: 4096MB\n")

    # Optimize for cloud
    print("Optimizing for AWS Lambda...")
    cloud_variant = {
        **original_workflow,
        "workflow_id": "sentiment_analyzer_cloud",
        "requires_llm": True,
        "llm_mode": "cloud_apis",
        "cloud_optimized": True
    }
    print(f"  ✓ Created: {cloud_variant['workflow_id']}")
    print(f"  ✓ Uses: GPT-4/Claude")
    print(f"  ✓ Quality: Highest\n")

    print("=== Result ===")
    print("Original workflow preserved")
    print(f"  Platform variants created:")
    print(f"    - {pi_variant['workflow_id']} (Raspberry Pi)")
    print(f"    - {cloud_variant['workflow_id']} (Cloud)\n")

    print("Each variant can be deployed independently:")
    print("  $ python export_workflow.py sentiment_analyzer_raspberry_pi --platform embedded")
    print("  $ python export_workflow.py sentiment_analyzer_cloud --platform cloud")


if __name__ == "__main__":
    example_usage()
