"""
Code Evolver - A system for evolving code through AI-assisted generation and evaluation.
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

    Args:
        config_manager: ConfigManager instance
        ollama_client: OllamaClient instance

    Returns:
        RAGMemory or QdrantRAGMemory instance based on configuration
    """
    # Get embedding configuration (separate from LLM backend)
    # This allows using local Ollama for embeddings even when using cloud LLMs

    # Get embedding model key from config (e.g., "nomic_embed")
    embedding_model_key = config_manager.get("llm.embedding.default", "nomic_embed")

    # Get model metadata from registry
    embedding_metadata = config_manager.get_model_metadata(embedding_model_key)
    embedding_model_name = embedding_metadata.get("name", "nomic-embed-text")

    # Get Ollama backend URL (embeddings ALWAYS use Ollama)
    embedding_endpoint = config_manager.get("llm.backends.ollama.base_url", "http://localhost:11434")

    if config_manager.use_qdrant:
        if not QDRANT_AVAILABLE:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Qdrant requested but qdrant-client not installed. Falling back to NumPy-based RAG.")
            return RAGMemory(
                memory_path=config_manager.rag_memory_path,
                ollama_client=ollama_client,
                embedding_model=embedding_model_name
            )

        return QdrantRAGMemory(
            memory_path=config_manager.rag_memory_path,
            ollama_client=ollama_client,
            embedding_model=embedding_model_name,
            embedding_endpoint=embedding_endpoint,  # ALWAYS Ollama for embeddings
            qdrant_url=config_manager.qdrant_url,
            collection_name=config_manager.get("rag_memory.collection_name", "code_evolver_artifacts"),
            vector_size=config_manager.embedding_vector_size
        )
    else:
        return RAGMemory(
            memory_path=config_manager.rag_memory_path,
            ollama_client=ollama_client,
            embedding_model=embedding_model_name
        )

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
    "WorkflowBuilder"
]
