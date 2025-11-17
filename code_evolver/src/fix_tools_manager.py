"""
Fix Tools Manager - Self-Learning Error Fix Library

This module manages a library of error-fixing tools stored in RAG.
When code generation encounters errors, the system:

1. Searches RAG for similar error patterns (semantic search)
2. Uses a fast LLM to validate fix applicability
3. Auto-applies the fix
4. Re-tests and only escalates if fix didn't work

This creates a LEARNING system that accumulates fixes over time.
"""

import logging
import json
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FixToolsManager:
    """
    Manages error-fixing tools stored in RAG.

    Fix tools are executable tools tagged with ["fix", "error_handler"] that:
    - Detect specific error patterns
    - Apply automated fixes to code
    - Return fixed code and metadata

    Benefits:
    - Self-learning: Accumulates fixes over time
    - Reusable: Any workflow can use the fix library
    - Intelligent: LLM validates fix applicability before applying
    """

    def __init__(self, rag_memory, tools_manager, ollama_client):
        """
        Initialize fix tools manager.

        Args:
            rag_memory: RAGMemory instance for storing/searching fixes
            tools_manager: ToolsManager instance for executing fix tools
            ollama_client: OllamaClient for LLM validation
        """
        self.rag = rag_memory
        self.tools = tools_manager
        self.client = ollama_client

        # Load fix tools into RAG on initialization
        self._index_fix_tools()

    def _index_fix_tools(self):
        """
        Index all fix tools from tools/executable/ into RAG.

        Fix tools are identified by:
        - Type: "executable"
        - Tags: ["fix", "error_handler"]
        - Metadata: error_pattern field
        """
        logger.info("Indexing fix tools in RAG...")

        if not self.tools:
            logger.warning("Tools manager not available - cannot index fix tools")
            return

        fix_count = 0

        for tool_id, tool in self.tools.tools.items():
            # Check if this is a fix tool
            if tool.type == "executable" and "fix" in tool.tags:
                try:
                    from src.rag_memory import ArtifactType

                    # Store in RAG with error pattern as description
                    error_pattern = tool.metadata.get("error_pattern", "")

                    self.rag.store_artifact(
                        artifact_id=f"fix_tool_{tool_id}",
                        artifact_type=ArtifactType.TOOL,
                        name=tool.name,
                        description=f"{tool.description}\n\nError Pattern: {error_pattern}",
                        content=json.dumps({
                            "tool_id": tool_id,
                            "command": tool.command,
                            "args": tool.args,
                            "error_pattern": error_pattern,
                            "applies_to": tool.metadata.get("applies_to", ""),
                            "category": tool.metadata.get("category", "code_fixer"),
                            "priority": tool.metadata.get("priority", "medium"),
                            "auto_apply": tool.metadata.get("auto_apply", False)
                        }),
                        tags=["fix_tool", "error_handler"] + tool.tags,
                        auto_embed=True  # Enable semantic search
                    )

                    fix_count += 1
                    logger.debug(f"Indexed fix tool: {tool_id}")

                except Exception as e:
                    logger.warning(f"Could not index fix tool {tool_id}: {e}")

        logger.info(f"Indexed {fix_count} fix tools in RAG")

    def find_applicable_fixes(
        self,
        error_message: str,
        error_type: str,
        code: str,
        filename: str = "main.py",
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find fix tools that might solve this error.

        Args:
            error_message: The error message from test failure
            error_type: Type of error (ImportError, SyntaxError, etc.)
            code: The code that failed
            filename: Name of the file with the error
            top_k: Number of top matches to return

        Returns:
            List of applicable fix tools with similarity scores
        """
        logger.info(f"Searching for fixes for: {error_type}")

        # Search RAG for similar error patterns
        query = f"{error_type}: {error_message}"

        try:
            from src.rag_memory import ArtifactType

            results = self.rag.find_similar(
                query=query,
                artifact_type=ArtifactType.TOOL,
                top_k=top_k * 2  # Get more candidates for LLM filtering
            )

            applicable_fixes = []

            for artifact, similarity in results:
                # Only consider fix tools
                if "fix_tool" not in artifact.tags:
                    continue

                try:
                    fix_data = json.loads(artifact.content)

                    # Check if this fix applies to the current file
                    applies_to = fix_data.get("applies_to", "")
                    if applies_to and filename not in applies_to:
                        logger.debug(f"Skipping {fix_data['tool_id']} - doesn't apply to {filename}")
                        continue

                    applicable_fixes.append({
                        "tool_id": fix_data["tool_id"],
                        "name": artifact.name,
                        "description": artifact.description,
                        "similarity": similarity,
                        "priority": fix_data.get("priority", "medium"),
                        "auto_apply": fix_data.get("auto_apply", False),
                        "fix_data": fix_data
                    })

                except Exception as e:
                    logger.debug(f"Could not parse fix tool artifact: {e}")

            # Sort by similarity and priority
            priority_weights = {"high": 3, "medium": 2, "low": 1}
            applicable_fixes.sort(
                key=lambda x: (
                    priority_weights.get(x["priority"], 2),
                    x["similarity"]
                ),
                reverse=True
            )

            logger.info(f"Found {len(applicable_fixes)} potentially applicable fixes")
            return applicable_fixes[:top_k]

        except Exception as e:
            logger.warning(f"Error searching for fixes: {e}")
            return []

    def validate_fix_with_llm(
        self,
        fix_tool: Dict[str, Any],
        error_message: str,
        code: str
    ) -> Dict[str, Any]:
        """
        Use a fast LLM to validate if this fix is actually applicable.

        Args:
            fix_tool: Fix tool metadata
            error_message: The error message
            code: The failing code

        Returns:
            Dict with validation results:
            - applicable: bool
            - confidence: float (0-1)
            - reasoning: str
        """
        validation_prompt = f"""You are an error analysis expert. Determine if this fix tool is applicable to the given error.

ERROR:
{error_message}

CODE (first 500 chars):
{code[:500]}

FIX TOOL:
Name: {fix_tool['name']}
Description: {fix_tool['description']}

QUESTION: Should this fix tool be applied to solve this error?

Respond with ONLY a JSON object:
{{
    "applicable": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Why this fix is/isn't applicable"
}}
"""

        try:
            # Use fast model (veryfast tier) for quick validation
            response = self.client.generate(
                role="veryfast",  # tinyllama or similar
                prompt=validation_prompt,
                temperature=0.1  # Low temperature for consistent decisions
            )

            # Parse JSON response
            import re
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "applicable": result.get("applicable", False),
                    "confidence": result.get("confidence", 0.0),
                    "reasoning": result.get("reasoning", "")
                }

        except Exception as e:
            logger.warning(f"LLM validation failed: {e}")

        # Default: not applicable if validation fails
        return {
            "applicable": False,
            "confidence": 0.0,
            "reasoning": "Validation failed"
        }

    def apply_fix(
        self,
        fix_tool_id: str,
        code: str,
        filename: str = "main.py",
        error_message: str = ""
    ) -> Dict[str, Any]:
        """
        Apply a fix tool to code.

        Args:
            fix_tool_id: ID of the fix tool to apply
            code: Code to fix
            filename: Name of the file being fixed
            error_message: The error message being fixed

        Returns:
            Dict with fix results:
            - success: bool
            - fixed_code: str (if successful)
            - message: str
            - details: Dict (tool-specific output)
            - validated: bool (if tool has validation)
            - validation_result: Dict (if validated)
        """
        logger.info(f"Applying fix tool: {fix_tool_id}")

        if not self.tools or fix_tool_id not in self.tools.tools:
            return {
                "success": False,
                "message": f"Fix tool '{fix_tool_id}' not found"
            }

        try:
            from node_runtime import call_tool

            # Prepare input for fix tool
            fix_input = json.dumps({
                "command": "fix",
                "code": code,
                "filename": filename,
                "error_message": error_message
            })

            # Call the fix tool
            result = call_tool(fix_tool_id, fix_input)

            # Parse result
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    pass

            if isinstance(result, dict) and result.get("fixed"):
                fixed_code = result.get("fixed_code", code)

                # Check if this tool has built-in validation
                tool = self.tools.tools.get(fix_tool_id)
                has_validation = tool.metadata.get("has_validation", False) if tool else False

                validation_result = None
                if has_validation:
                    # Call the tool's validate() method
                    logger.info(f"Validating fix with built-in validator")
                    validation_result = self._validate_fix_with_tool(
                        fix_tool_id=fix_tool_id,
                        original_code=code,
                        fixed_code=fixed_code,
                        fix_result=result,
                        error_message=error_message
                    )

                    if not validation_result.get("valid"):
                        logger.warning(f"Fix validation failed: {validation_result.get('reason')}")
                        return {
                            "success": False,
                            "message": f"Fix validation failed: {validation_result.get('reason')}",
                            "details": result,
                            "validated": True,
                            "validation_result": validation_result
                        }

                return {
                    "success": True,
                    "fixed_code": fixed_code,
                    "message": result.get("message", "Fix applied"),
                    "details": result,
                    "validated": has_validation,
                    "validation_result": validation_result
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message", "Fix tool reported no changes"),
                    "details": result
                }

        except Exception as e:
            logger.error(f"Error applying fix tool: {e}")
            return {
                "success": False,
                "message": f"Fix failed: {e}"
            }

    def _validate_fix_with_tool(
        self,
        fix_tool_id: str,
        original_code: str,
        fixed_code: str,
        fix_result: Dict[str, Any],
        error_message: str
    ) -> Dict[str, Any]:
        """
        Call a fix tool's validate() method.

        Args:
            fix_tool_id: ID of the fix tool
            original_code: Code before fix
            fixed_code: Code after fix
            fix_result: Result from the fix() call
            error_message: The error being fixed

        Returns:
            {
                "valid": bool,
                "confidence": float,
                "reason": str
            }
        """
        try:
            from node_runtime import call_tool

            validate_input = json.dumps({
                "command": "validate",
                "original_code": original_code,
                "fixed_code": fixed_code,
                "fix_result": fix_result,
                "error_message": error_message
            })

            result = call_tool(fix_tool_id, validate_input)

            if isinstance(result, str):
                result = json.loads(result)

            return result

        except Exception as e:
            logger.error(f"Error validating fix: {e}")
            # Default to valid if validation fails
            return {
                "valid": True,
                "confidence": 0.0,
                "reason": f"Validation error: {e}"
            }

    def auto_fix_code(
        self,
        error_message: str,
        error_type: str,
        code: str,
        filename: str = "main.py"
    ) -> Dict[str, Any]:
        """
        Automatically find and apply the best fix for an error.

        This is the main entry point for the auto-fix system.

        Args:
            error_message: Error message from test failure
            error_type: Type of error (ImportError, SyntaxError, etc.)
            code: The failing code
            filename: Name of the file with error

        Returns:
            Dict with fix results:
            - fixed: bool
            - fixed_code: str (if successful)
            - fix_applied: str (name of fix tool used)
            - message: str
        """
        logger.info(f"Auto-fixing {error_type}...")

        # 1. Search for applicable fixes
        fixes = self.find_applicable_fixes(
            error_message=error_message,
            error_type=error_type,
            code=code,
            filename=filename
        )

        if not fixes:
            return {
                "fixed": False,
                "message": "No applicable fixes found in library"
            }

        # 2. Validate and apply fixes in order of priority
        for fix in fixes:
            logger.info(f"Considering fix: {fix['name']} (similarity: {fix['similarity']:.2f})")

            # Auto-apply high-priority fixes without LLM validation
            if fix["auto_apply"] and fix["similarity"] > 0.8:
                logger.info(f"Auto-applying {fix['name']} (high confidence)")
                validation = {"applicable": True, "confidence": fix["similarity"]}
            else:
                # Validate with LLM
                validation = self.validate_fix_with_llm(fix, error_message, code)

            if validation["applicable"] and validation["confidence"] > 0.6:
                logger.info(f"Applying {fix['name']} (confidence: {validation['confidence']:.2f})")

                # Apply the fix
                result = self.apply_fix(fix["tool_id"], code, filename)

                if result["success"]:
                    return {
                        "fixed": True,
                        "fixed_code": result["fixed_code"],
                        "fix_applied": fix["name"],
                        "tool_id": fix["tool_id"],
                        "message": result["message"],
                        "confidence": validation["confidence"]
                    }

        # No fixes worked
        return {
            "fixed": False,
            "message": f"Tried {len(fixes)} fixes, none were successful"
        }

    def register_new_fix_tool(
        self,
        tool_id: str,
        error_pattern: str,
        description: str
    ):
        """
        Register a new fix tool in the library.

        Args:
            tool_id: ID of the tool to register
            error_pattern: Regex or description of error this fixes
            description: What the fix does
        """
        logger.info(f"Registering new fix tool: {tool_id}")

        # Re-index fix tools to pick up the new one
        self._index_fix_tools()
