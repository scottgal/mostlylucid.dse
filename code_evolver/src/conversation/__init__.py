"""
Conversation Tool Module

A comprehensive conversation management system with:
- Multi-chat context memory
- Auto-summarization with context window awareness
- Volatile Qdrant storage for semantic search
- Performance tracking and context optimization
- Smart orchestration with dynamic tool calling
- Parallel task execution with CPU/GPU load awareness
"""

from .conversation_storage import ConversationStorage
from .context_manager import ContextMemoryManager
from .summarizer import ConversationSummarizer
from .intent_detector import ConversationIntentDetector
from .embedder import ConversationEmbedder
from .smart_orchestrator import SmartConversationOrchestrator
from .conversation_tool import ConversationTool

__all__ = [
    "ConversationStorage",
    "ContextMemoryManager",
    "ConversationSummarizer",
    "ConversationIntentDetector",
    "ConversationEmbedder",
    "SmartConversationOrchestrator",
    "ConversationTool",
]
