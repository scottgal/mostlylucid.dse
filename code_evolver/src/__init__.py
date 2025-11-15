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
    if config_manager.use_qdrant:
        if not QDRANT_AVAILABLE:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Qdrant requested but qdrant-client not installed. Falling back to NumPy-based RAG.")
            return RAGMemory(
                memory_path=config_manager.rag_memory_path,
                ollama_client=ollama_client,
                embedding_model=config_manager.embedding_model
            )

        return QdrantRAGMemory(
            memory_path=config_manager.rag_memory_path,
            ollama_client=ollama_client,
            embedding_model=config_manager.embedding_model,
            qdrant_url=config_manager.qdrant_url,
            vector_size=config_manager.embedding_vector_size
        )
    else:
        return RAGMemory(
            memory_path=config_manager.rag_memory_path,
            ollama_client=ollama_client,
            embedding_model=config_manager.embedding_model
        )

# New hierarchical evolution system
from .overseer_llm import OverseerLlm, ExecutionPlan
from .evaluator_llm import EvaluatorLlm, FitnessEvaluation
from .hierarchical_evolver import HierarchicalEvolver, SharedPlanContext, NodeMetrics, NodeLearning
from .rag_integrated_tools import RAGIntegratedTools, FunctionMetadata
from .progress_display import ProgressDisplay, Stage, get_progress_display
from .quality_evaluator import QualityEvaluator, EvaluationResult, EvaluationStep
from .workflow_tracker import WorkflowTracker, WorkflowStep, StepStatus

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
    # Workflow tracking
    "WorkflowTracker",
    "WorkflowStep",
    "StepStatus"
]
