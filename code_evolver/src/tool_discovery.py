"""
Tool Discovery - Self-Awareness for Tool Management

This module enables the system to search and discover existing tools before
creating new ones, preventing duplication and encouraging reuse.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolDiscovery:
    """
    Tool discovery and self-awareness system.

    Enables the system to:
    - Search for existing tools matching a need
    - Identify tools that can be adapted/reused
    - Prevent creation of duplicate tools
    - Suggest similar existing tools
    """

    def __init__(self, tools_manager, rag_memory):
        """
        Initialize tool discovery.

        Args:
            tools_manager: ToolsManager instance
            rag_memory: RAGMemory instance for semantic search
        """
        self.tools_manager = tools_manager
        self.rag = rag_memory

    def find_tools_for_task(
        self,
        task_description: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find existing tools that could help with a task.

        Args:
            task_description: What the user wants to do
            top_k: Number of top matches to return

        Returns:
            List of tool matches with similarity scores

        Example:
            >>> discovery.find_tools_for_task("generate fake data for testing")
            [
                {
                    "tool_id": "faker_tool",
                    "name": "Smart Faker",
                    "description": "Generate realistic fake data...",
                    "similarity": 0.92,
                    "can_reuse": True,
                    "adaptation_needed": "minimal"
                },
                ...
            ]
        """
        logger.info(f"Searching for tools matching: {task_description}")

        # Search tools by description using RAG
        results = []

        # 1. Semantic search in RAG memory
        if self.rag:
            try:
                from src.rag_memory import ArtifactType

                rag_results = self.rag.find_similar(
                    query=task_description,
                    artifact_type=ArtifactType.TOOL,
                    top_k=top_k
                )

                for artifact, similarity in rag_results:
                    results.append({
                        "tool_id": artifact.artifact_id,
                        "name": artifact.name,
                        "description": artifact.description,
                        "similarity": similarity,
                        "can_reuse": similarity > 0.85,
                        "adaptation_needed": self._assess_adaptation(similarity),
                        "tags": artifact.tags
                    })

            except Exception as e:
                logger.warning(f"RAG search failed: {e}")

        # 2. Direct search in tools manager
        if self.tools_manager:
            for tool_id, tool in self.tools_manager.tools.items():
                # Skip if already found via RAG
                if any(r["tool_id"] == tool_id for r in results):
                    continue

                # Simple keyword matching
                keywords = task_description.lower().split()
                tool_text = f"{tool.name} {tool.description}".lower()

                matches = sum(1 for kw in keywords if kw in tool_text)
                if matches > 0:
                    similarity = matches / len(keywords)
                    results.append({
                        "tool_id": tool_id,
                        "name": tool.name,
                        "description": tool.description,
                        "similarity": similarity,
                        "can_reuse": similarity > 0.6,
                        "adaptation_needed": self._assess_adaptation(similarity),
                        "tags": tool.tags
                    })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(f"Found {len(results)} matching tools")
        return results[:top_k]

    def _assess_adaptation(self, similarity: float) -> str:
        """Assess how much adaptation is needed based on similarity."""
        if similarity > 0.95:
            return "none"
        elif similarity > 0.85:
            return "minimal"
        elif similarity > 0.70:
            return "moderate"
        elif similarity > 0.50:
            return "significant"
        else:
            return "complete_rewrite"

    def check_duplicate(self, tool_name: str, tool_description: str) -> Optional[Dict[str, Any]]:
        """
        Check if a tool with similar name/description already exists.

        Args:
            tool_name: Proposed tool name
            tool_description: Proposed tool description

        Returns:
            Dict with duplicate info if found, None otherwise
        """
        # Check exact name match
        if self.tools_manager:
            for tool_id, tool in self.tools_manager.tools.items():
                if tool.name.lower() == tool_name.lower():
                    return {
                        "exists": True,
                        "tool_id": tool_id,
                        "match_type": "exact_name",
                        "existing_tool": {
                            "name": tool.name,
                            "description": tool.description
                        }
                    }

        # Check semantic similarity
        matches = self.find_tools_for_task(tool_description, top_k=1)
        if matches and matches[0]["similarity"] > 0.90:
            return {
                "exists": True,
                "tool_id": matches[0]["tool_id"],
                "match_type": "semantic_duplicate",
                "similarity": matches[0]["similarity"],
                "existing_tool": {
                    "name": matches[0]["name"],
                    "description": matches[0]["description"]
                }
            }

        return None

    def suggest_tool_improvements(self, tool_id: str) -> List[str]:
        """
        Suggest improvements for an existing tool based on similar tools.

        Args:
            tool_id: Tool to analyze

        Returns:
            List of improvement suggestions
        """
        if not self.tools_manager or tool_id not in self.tools_manager.tools:
            return []

        tool = self.tools_manager.tools[tool_id]
        suggestions = []

        # Find similar tools
        similar = self.find_tools_for_task(tool.description, top_k=5)

        for match in similar:
            if match["tool_id"] == tool_id:
                continue

            # Check for features the current tool might be missing
            match_tags = set(match.get("tags", []))
            current_tags = set(tool.tags)

            missing_features = match_tags - current_tags
            if missing_features:
                suggestions.append(
                    f"Consider adding features from '{match['name']}': {', '.join(missing_features)}"
                )

        return suggestions

    def get_tool_usage_stats(self, tool_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a tool from RAG memory.

        Args:
            tool_id: Tool identifier

        Returns:
            Dict with usage stats
        """
        if not self.rag:
            return {"usage_count": 0, "available": False}

        try:
            # Get artifact from RAG
            artifact = self.rag.get_artifact(tool_id)
            if artifact:
                return {
                    "usage_count": artifact.usage_count,
                    "quality_score": artifact.quality_score,
                    "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
                    "available": True
                }
        except Exception as e:
            logger.debug(f"Could not get usage stats: {e}")

        return {"usage_count": 0, "available": False}

    def recommend_tool_composition(
        self,
        task_description: str
    ) -> Dict[str, Any]:
        """
        Recommend how to compose existing tools to solve a task.

        Args:
            task_description: Task to accomplish

        Returns:
            Recommendation with tool composition strategy
        """
        # Find relevant tools
        tools = self.find_tools_for_task(task_description, top_k=10)

        if not tools:
            return {
                "strategy": "create_new",
                "reason": "No existing tools found",
                "tools": []
            }

        # Check if single tool is sufficient
        if tools and tools[0]["similarity"] > 0.90:
            return {
                "strategy": "use_existing",
                "reason": f"Existing tool '{tools[0]['name']}' matches closely",
                "tools": [tools[0]],
                "recommended_action": "reuse"
            }

        # Check if tools can be composed
        if len(tools) >= 2 and all(t["similarity"] > 0.60 for t in tools[:3]):
            return {
                "strategy": "compose",
                "reason": "Multiple tools can be combined",
                "tools": tools[:3],
                "recommended_action": "create_workflow_combining_tools"
            }

        # Suggest adaptation
        if tools and tools[0]["similarity"] > 0.70:
            return {
                "strategy": "adapt_existing",
                "reason": f"Tool '{tools[0]['name']}' can be adapted",
                "tools": [tools[0]],
                "recommended_action": "fork_and_modify"
            }

        return {
            "strategy": "create_new",
            "reason": "No suitable existing tools found",
            "tools": tools[:3] if tools else [],
            "recommended_action": "create_from_scratch"
        }
