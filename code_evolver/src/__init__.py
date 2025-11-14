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

# New hierarchical evolution system
from .overseer_llm import OverseerLlm, ExecutionPlan
from .evaluator_llm import EvaluatorLlm, FitnessEvaluation
from .hierarchical_evolver import HierarchicalEvolver, SharedPlanContext, NodeMetrics, NodeLearning
from .rag_integrated_tools import RAGIntegratedTools, FunctionMetadata

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
    "Artifact",
    "ArtifactType",
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
    "FunctionMetadata"
]
