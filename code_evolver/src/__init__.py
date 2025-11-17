"""
mostlylucid DiSE - A system for evolving code through AI-assisted generation and evaluation.
"""

__version__ = "0.2.0"

from .ollama_client import OllamaClient
from .registry import Registry
from .node_runner import NodeRunner
from .evaluator import Evaluator
from .config_manager import ConfigManager
from .solution_memory import SolutionMemory
from .auto_evolver import AutoEvolver
from .tools_manager import ToolsManager, Tool, ToolType
from .rag_memory import RAGMemory, Artifact, ArtifactType
from .qdrant_rag_memory import QdrantRAGMemory, QDRANT_AVAILABLE
from .openapi_tool import OpenAPITool

def create_rag_memory(config_manager, ollama_client):
    """
    Factory function to create appropriate RAG memory implementation.

    CRITICAL: RAG is required infrastructure. This function will retry with
    exponential backoff if initialization fails.

    Args:
        config_manager: ConfigManager instance
        ollama_client: OllamaClient instance

    Returns:
        RAGMemory or QdrantRAGMemory instance based on configuration

    Raises:
        RuntimeError: If RAG cannot be initialized after all retries
    """
    import logging
    import time

    logger = logging.getLogger(__name__)

    # Get embedding configuration (separate from LLM backend)
    # This allows using local Ollama for embeddings even when using cloud LLMs

    # Get embedding model key from config (e.g., "nomic_embed")
    embedding_model_key = config_manager.get("llm.embedding.default", "nomic_embed")

    # Get model metadata from registry
    embedding_metadata = config_manager.get_model_metadata(embedding_model_key)
    embedding_model_name = embedding_metadata.get("name", "nomic-embed-text")

    # Get Ollama backend URL (embeddings ALWAYS use Ollama)
    embedding_endpoint = config_manager.get("llm.backends.ollama.base_url", "http://localhost:11434")

    # Retry configuration
    max_retries = 3
    base_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            if config_manager.use_qdrant:
                if not QDRANT_AVAILABLE:
                    logger.error("CRITICAL: Qdrant requested but qdrant-client not installed!")
                    logger.error("Install with: pip install qdrant-client>=1.7.0")
                    raise RuntimeError("Qdrant client not available - RAG cannot initialize")

                logger.info(f"Initializing Qdrant RAG memory (attempt {attempt + 1}/{max_retries})...")
                rag = QdrantRAGMemory(
                    memory_path=config_manager.rag_memory_path,
                    ollama_client=ollama_client,
                    embedding_model=embedding_model_name,
                    embedding_endpoint=embedding_endpoint,  # ALWAYS Ollama for embeddings
                    qdrant_url=config_manager.qdrant_url,
                    collection_name=config_manager.get("rag_memory.collection_name", "code_evolver_artifacts"),
                    vector_size=config_manager.embedding_vector_size
                )
            else:
                logger.info(f"Initializing NumPy RAG memory (attempt {attempt + 1}/{max_retries})...")
                rag = RAGMemory(
                    memory_path=config_manager.rag_memory_path,
                    ollama_client=ollama_client,
                    embedding_model=embedding_model_name
                )

            # If we got here, initialization succeeded
            logger.info("RAG memory initialized successfully")
            return rag

        except Exception as e:
            if attempt < max_retries - 1:
                # Calculate exponential backoff delay
                delay = base_delay * (2 ** attempt)
                logger.warning(f"RAG initialization failed (attempt {attempt + 1}/{max_retries}): {e}")
                logger.warning(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                # Final attempt failed
                logger.error("CRITICAL: RAG memory initialization failed after all retries!")
                logger.error(f"Error: {e}")
                if config_manager.use_qdrant:
                    logger.error("Check that Qdrant is running: docker run -p 6333:6333 qdrant/qdrant")
                logger.error("RAG is critical infrastructure - cannot continue")
                raise RuntimeError(f"Failed to initialize RAG memory after {max_retries} attempts: {e}")


def create_loki_manager(config_manager, scope="global"):
    """
    Factory function to create LokiManager instance.

    This function creates a LokiManager instance configured from the
    config_manager settings. It checks for existing instances and reuses
    them if available.

    Args:
        config_manager: ConfigManager instance
        scope: Deployment scope ('global', 'tool', or custom name)

    Returns:
        LokiManager instance or None if Loki is disabled

    Example:
        >>> config = ConfigManager()
        >>> loki = create_loki_manager(config, scope='global')
        >>> if loki:
        ...     loki.start()
        ...     loki.push(logs=[{"message": "Hello"}])
    """
    if not config_manager.loki_enabled:
        return None

    try:
        # Import here to avoid circular dependency
        import sys
        from pathlib import Path

        # Add tools/executable to path if not already there
        tools_path = Path(__file__).parent.parent / 'tools' / 'executable'
        if str(tools_path) not in sys.path:
            sys.path.insert(0, str(tools_path))

        from loki_manager import LokiManager

        # Get or create instance for this scope
        loki = LokiManager.get_instance(
            scope=scope,
            url=config_manager.loki_url,
            data_path=config_manager.loki_data_path,
            docker_image=config_manager.loki_docker_image,
            container_name=config_manager.loki_container_name,
            port=config_manager.loki_port,
            config_file=config_manager.loki_config_file,
            default_labels=config_manager.loki_default_labels,
            batch_size=config_manager.loki_batch_size,
            timeout_seconds=config_manager.loki_batch_timeout
        )

        return loki

    except ImportError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Loki requested but loki_manager not available (optional): {e}")
        return None
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create LokiManager: {e}")
        return None


def create_filesystem_manager(config_manager):
    """
    Factory function to create FilesystemManager instance.

    This function creates a FilesystemManager instance configured from
    the config_manager settings.

    Args:
        config_manager: ConfigManager instance

    Returns:
        FilesystemManager instance or None if filesystem is disabled

    Example:
        >>> config = ConfigManager()
        >>> fs = create_filesystem_manager(config)
        >>> if fs:
        ...     fs.write("my_tool", "data.json", '{"key": "value"}')
        ...     content = fs.read("my_tool", "data.json")
    """
    if not config_manager.filesystem_enabled:
        return None

    try:
        # Import here to avoid circular dependency
        import sys
        from pathlib import Path

        # Add tools/executable to path if not already there
        tools_path = Path(__file__).parent.parent / 'tools' / 'executable'
        if str(tools_path) not in sys.path:
            sys.path.insert(0, str(tools_path))

        from filesystem_manager import FilesystemManager

        # Create instance
        fs = FilesystemManager(
            base_path=config_manager.filesystem_base_path,
            max_file_size_mb=config_manager.filesystem_max_file_size_mb,
            max_total_size_mb=config_manager.filesystem_max_total_size_mb,
            allowed_extensions=config_manager.filesystem_allowed_extensions,
            allow_absolute_paths=config_manager.filesystem_allow_absolute_paths,
            allow_parent_traversal=config_manager.filesystem_allow_parent_traversal
        )

        return fs

    except ImportError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Filesystem requested but filesystem_manager not available (optional): {e}")
        return None
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create FilesystemManager: {e}")
        return None


# New hierarchical evolution system
from .overseer_llm import OverseerLlm, ExecutionPlan
from .evaluator_llm import EvaluatorLlm, FitnessEvaluation
from .hierarchical_evolver import HierarchicalEvolver, SharedPlanContext, NodeMetrics, NodeLearning
from .rag_integrated_tools import RAGIntegratedTools, FunctionMetadata
from .progress_display import ProgressDisplay, Stage, get_progress_display
from .quality_evaluator import QualityEvaluator, EvaluationResult, EvaluationStep
from .workflow_tracker import WorkflowTracker, WorkflowStep as WorkflowTrackerStep, StepStatus
from .workflow_spec import (
    WorkflowSpec, WorkflowStep as WorkflowStepSpec, WorkflowInput, WorkflowOutput,
    ToolDefinition, StepType, OperationType,
    create_simple_workflow
)
from .workflow_builder import WorkflowBuilder
from .background_process import BackgroundProcess, ProcessStatus, StatusUpdate
from .background_process_manager import BackgroundProcessManager
from .optimized_perf_tracker import OptimizedPerfTracker, get_tracker as get_perf_tracker
from .tool_interceptors import (
    get_global_interceptor_chain,
    intercept_tool_call,
    BugCatcherInterceptor,
    PerfCatcherInterceptor,
    OptimizedPerfTrackerInterceptor
)
from .json_response_fixer import extract_json_from_response, safe_json_parse

__all__ = [
    "OllamaClient",
    "Registry",
    "NodeRunner",
    "Evaluator",
    "ConfigManager",
    "SolutionMemory",
    "AutoEvolver",
    "ToolsManager",
    "Tool",
    "ToolType",
    "RAGMemory",
    "QdrantRAGMemory",
    "Artifact",
    "ArtifactType",
    "OpenAPITool",
    "create_rag_memory",  # Factory function for RAG
    "create_loki_manager",  # Factory function for Loki
    "create_filesystem_manager",  # Factory function for Filesystem
    # New exports
    "OverseerLlm",
    "ExecutionPlan",
    "EvaluatorLlm",
    "FitnessEvaluation",
    "HierarchicalEvolver",
    "SharedPlanContext",
    "NodeMetrics",
    "NodeLearning",
    "RAGIntegratedTools",
    "FunctionMetadata",
    "ProgressDisplay",
    "Stage",
    "get_progress_display",
    # Quality evaluation
    "QualityEvaluator",
    "EvaluationResult",
    "EvaluationStep",
    # Workflow tracking (runtime)
    "WorkflowTracker",
    "WorkflowTrackerStep",
    "StepStatus",
    # Workflow specification
    "WorkflowSpec",
    "WorkflowStepSpec",
    "WorkflowInput",
    "WorkflowOutput",
    "ToolDefinition",
    "StepType",
    "OperationType",
    "create_simple_workflow",
    "WorkflowBuilder",
    # Background execution
    "BackgroundProcess",
    "BackgroundProcessManager",
    "ProcessStatus",
    "StatusUpdate",
    # Performance tracking & optimization
    "OptimizedPerfTracker",
    "get_perf_tracker",
    "get_global_interceptor_chain",
    "intercept_tool_call",
    "BugCatcherInterceptor",
    "PerfCatcherInterceptor",
    "OptimizedPerfTrackerInterceptor",
    # JSON response handling
    "extract_json_from_response",
    "safe_json_parse"
]
