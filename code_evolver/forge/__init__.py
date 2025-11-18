"""
Tool Forge - Integration-optimized, consensus-hardened tool generation system.

This module provides a comprehensive system for generating, validating, optimizing,
and serving MCP tools via a central RAG-backed registry.

Key Features:
- Multi-LLM adversarial hardening
- Integration testing as an optimization loop
- Lineage tracking and trust weighting
- Automatic tool selection and optimization
- Provenance and auditability
"""

from .core.director import ForgeDirector
from .core.registry import ForgeRegistry
from .core.runtime import ForgeRuntime
from .core.consensus import ConsensusEngine
from .core.validator import ValidationCouncil
from .core.optimizer import IntegrationOptimizer

__all__ = [
    'ForgeDirector',
    'ForgeRegistry',
    'ForgeRuntime',
    'ConsensusEngine',
    'ValidationCouncil',
    'IntegrationOptimizer'
]

__version__ = '1.0.0'
