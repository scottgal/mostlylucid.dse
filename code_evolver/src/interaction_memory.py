"""
Interaction Memory - Self-Aware Memory of All User Interactions

This module maintains a running memory of all interactions with the system,
stored in the conversation system with a 'default' conversation ID.

Enables self-awareness:
- "How did you do that?"
- "Show me the last thing you did"
- "What was the workflow you used?"
- "/memory contents" - Show recent memory
- "/memory flush" - Clear memory
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class InteractionMemory:
    """
    Tracks all user interactions and system actions in a persistent memory.

    Uses the conversation system with a special 'default' conversation to maintain
    context across sessions.
    """

    DEFAULT_CONVERSATION_ID = "system_default_memory"

    def __init__(self, rag_memory):
        """
        Initialize interaction memory.

        Args:
            rag_memory: RAGMemory instance (REQUIRED)
        """
        if not rag_memory:
            raise ValueError("RAG memory is required for interaction memory")

        self.rag = rag_memory
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"Interaction memory active (session: {self.current_session_id})")

    def record_user_input(self, user_input: str, metadata: Optional[Dict] = None):
        """
        Record user input to memory in RAG.

        Args:
            user_input: What the user said/typed
            metadata: Additional context (timestamp, command type, etc.)
        """
        entry = {
            "type": "user_input",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.current_session_id,
            **(metadata or {})
        }

        try:
            from src.rag_memory import ArtifactType
            self.rag.store_artifact(
                artifact_id=f"interaction_{datetime.now().timestamp()}",
                artifact_type=ArtifactType.PATTERN,
                name="User Input",
                description=user_input[:100],
                content=json.dumps(entry),
                tags=["memory", "interaction", "user_input", self.current_session_id],
                auto_embed=True  # Enable semantic search
            )
            logger.debug(f"Recorded user input: {user_input[:50]}...")
        except Exception as e:
            logger.warning(f"Could not store interaction in RAG: {e}")

    def record_system_action(
        self,
        action: str,
        details: str,
        result: Optional[Any] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Record system action to memory in RAG.

        Args:
            action: Action taken (e.g., "generated_code", "ran_workflow")
            details: Description of what was done
            result: Result of the action
            metadata: Additional context
        """
        entry = {
            "type": "system_action",
            "action": action,
            "details": details,
            "result": str(result)[:200] if result else None,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.current_session_id,
            **(metadata or {})
        }

        try:
            from src.rag_memory import ArtifactType
            self.rag.store_artifact(
                artifact_id=f"action_{datetime.now().timestamp()}",
                artifact_type=ArtifactType.PATTERN,
                name=f"Action: {action}",
                description=details[:100],
                content=json.dumps(entry),
                tags=["memory", "interaction", "system_action", action, self.current_session_id],
                auto_embed=True  # Enable semantic search
            )
            logger.debug(f"Recorded action: {action} - {details[:50]}...")
        except Exception as e:
            logger.warning(f"Could not store action in RAG: {e}")

    def record_workflow(
        self,
        workflow_name: str,
        steps: List[Dict[str, Any]],
        result: Optional[Any] = None
    ):
        """
        Record a workflow execution in RAG.

        Args:
            workflow_name: Name of the workflow
            steps: List of steps executed
            result: Final result
        """
        entry = {
            "type": "workflow",
            "workflow_name": workflow_name,
            "steps": steps,
            "result": str(result)[:200] if result else None,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.current_session_id
        }

        workflow_desc = f"Executed workflow '{workflow_name}' with {len(steps)} steps"

        try:
            from src.rag_memory import ArtifactType
            self.rag.store_artifact(
                artifact_id=f"workflow_{workflow_name}_{datetime.now().timestamp()}",
                artifact_type=ArtifactType.WORKFLOW,
                name=workflow_name,
                description=workflow_desc,
                content=json.dumps(entry),
                tags=["memory", "interaction", "workflow", workflow_name, self.current_session_id],
                auto_embed=True  # Enable semantic search
            )
            logger.debug(f"Recorded workflow: {workflow_name}")
        except Exception as e:
            logger.warning(f"Could not store workflow in RAG: {e}")

    def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent interactions from RAG memory.

        Args:
            limit: Number of recent interactions to retrieve

        Returns:
            List of interaction entries
        """
        interactions = []

        try:
            results = self.rag.find_by_tags(
                tags=["memory", "interaction"],
                limit=limit
            )

            for artifact in results:
                try:
                    entry = json.loads(artifact.content) if artifact.content else {}
                    interactions.append(entry)
                except:
                    pass

        except Exception as e:
            logger.warning(f"Could not get interactions from RAG: {e}")

        # Sort by timestamp (most recent first)
        interactions.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )

        return interactions[:limit]

    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search memory for specific interactions.

        Args:
            query: Search query (e.g., "workflow", "code generation")
            limit: Number of results

        Returns:
            List of matching interactions
        """
        results = []

        # Search in RAG
        if self.rag:
            try:
                from src.rag_memory import ArtifactType
                rag_results = self.rag.find_similar(
                    query=query,
                    artifact_type=ArtifactType.PATTERN,
                    top_k=limit
                )

                for artifact, similarity in rag_results:
                    if any(tag in artifact.tags for tag in ["interaction", "system_action", "workflow"]):
                        try:
                            entry = json.loads(artifact.content) if artifact.content else {}
                            entry["similarity"] = similarity
                            results.append(entry)
                        except:
                            pass
            except Exception as e:
                logger.debug(f"Could not search RAG: {e}")

        return results

    def get_last_action(self) -> Optional[Dict[str, Any]]:
        """
        Get the last system action.

        Returns:
            Dict with last action details, or None
        """
        interactions = self.get_recent_interactions(limit=20)

        # Find most recent system action
        for interaction in reversed(interactions):
            if isinstance(interaction, dict) and interaction.get("type") == "system_action":
                return interaction
            elif isinstance(interaction, dict) and interaction.get("role") == "assistant":
                # Parse from conversation message
                content = interaction.get("content", "")
                if content.startswith("[ACTION:"):
                    return {
                        "type": "system_action",
                        "details": content,
                        "timestamp": interaction.get("timestamp")
                    }

        return None

    def get_last_workflow(self) -> Optional[Dict[str, Any]]:
        """
        Get the last workflow execution.

        Returns:
            Dict with workflow details, or None
        """
        if self.rag:
            try:
                results = self.rag.find_by_tags(
                    tags=["interaction", "workflow"],
                    limit=1
                )
                if results:
                    return json.loads(results[0].content) if results[0].content else None
            except Exception as e:
                logger.debug(f"Could not get last workflow: {e}")

        return None

    def flush_memory(self, confirm: bool = False):
        """
        Clear interaction memory from RAG.

        Args:
            confirm: Must be True to actually flush

        Raises:
            ValueError: If confirm is False
        """
        if not confirm:
            raise ValueError("Memory flush requires confirmation. Set confirm=True")

        logger.warning("Flushing interaction memory from RAG...")

        try:
            # Find all memory artifacts
            artifacts = self.rag.find_by_tags(
                tags=["memory", "interaction"],
                limit=10000
            )

            # Delete them
            deleted_count = 0
            for artifact in artifacts:
                try:
                    self.rag.delete_artifact(artifact.artifact_id)
                    deleted_count += 1
                except:
                    pass

            logger.info(f"Flushed {deleted_count} interaction artifacts from RAG")

        except Exception as e:
            logger.warning(f"Could not clear RAG memory: {e}")

        # Start new session
        old_session = self.current_session_id
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Started new memory session: {old_session} -> {self.current_session_id}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about interaction memory from RAG.

        Returns:
            Dict with stats
        """
        stats = {
            "session_id": self.current_session_id,
            "total_interactions": 0,
            "user_inputs": 0,
            "system_actions": 0,
            "workflows": 0
        }

        try:
            artifacts = self.rag.find_by_tags(
                tags=["memory", "interaction"],
                limit=10000
            )

            stats["total_interactions"] = len(artifacts)

            for artifact in artifacts:
                try:
                    entry = json.loads(artifact.content) if artifact.content else {}
                    entry_type = entry.get("type", "")

                    if entry_type == "user_input":
                        stats["user_inputs"] += 1
                    elif entry_type == "system_action":
                        stats["system_actions"] += 1
                    elif entry_type == "workflow":
                        stats["workflows"] += 1
                except:
                    pass

        except Exception as e:
            logger.warning(f"Could not get memory stats from RAG: {e}")

        return stats
