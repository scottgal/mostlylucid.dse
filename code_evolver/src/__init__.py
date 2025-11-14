"""
Code Evolver - A system for evolving code through AI-assisted generation and evaluation.
"""

__version__ = "0.1.0"

from .ollama_client import OllamaClient
from .registry import Registry
from .node_runner import NodeRunner
from .evaluator import Evaluator
from .config_manager import ConfigManager
from .solution_memory import SolutionMemory
from .auto_evolver import AutoEvolver
from .tools_manager import ToolsManager, Tool, ToolType
from .rag_memory import RAGMemory, Artifact, ArtifactType

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
    "ArtifactType"
]
