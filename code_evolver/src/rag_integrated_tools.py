"""
RAG-Integrated Tools Manager
Self-optimizing system that uses RAG at every level (workflow → function).
Functions have metadata tags linking to RAG for tool discovery.
"""
import json
import logging
import ast
import inspect
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .rag_memory import RAGMemory, ArtifactType, Artifact
from .tools_manager import ToolsManager, Tool, ToolType
from .ollama_client import OllamaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FunctionMetadata:
    """Metadata for a function extracted from comments and docstrings."""

    def __init__(
        self,
        function_name: str,
        description: str,
        parameters: Dict[str, Any],
        returns: str,
        tags: List[str],
        use_cases: List[str],
        complexity: str = "O(n)",
        quality_score: float = 0.0,
        token_count: int = 0
    ):
        """
        Initialize function metadata.

        Args:
            function_name: Name of the function
            description: What the function does
            parameters: Parameter definitions
            returns: Return type and description
            tags: Tags describing the function (e.g., "sort", "search", "data-processing")
            use_cases: Specific use cases this function solves
            complexity: Time/space complexity
            quality_score: Quality score from evaluations
            token_count: Approximate token count
        """
        self.function_name = function_name
        self.description = description
        self.parameters = parameters
        self.returns = returns
        self.tags = tags
        self.use_cases = use_cases
        self.complexity = complexity
        self.quality_score = quality_score
        self.token_count = token_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "function_name": self.function_name,
            "description": self.description,
            "parameters": self.parameters,
            "returns": self.returns,
            "tags": self.tags,
            "use_cases": self.use_cases,
            "complexity": self.complexity,
            "quality_score": self.quality_score,
            "token_count": self.token_count
        }


class RAGIntegratedTools:
    """
    RAG-integrated tools manager with self-optimization.

    Features:
    1. RAG search at every level (workflow → sub-workflow → function)
    2. Tools retrieved from RAG and passed to overseer
    3. Token optimization: code LLM manipulates, optimizes, saves back to RAG
    4. Function-level granularity with metadata tagging
    5. Functions become tools themselves
    """

    def __init__(
        self,
        rag_memory: Optional[RAGMemory] = None,
        tools_manager: Optional[ToolsManager] = None,
        ollama_client: Optional[OllamaClient] = None
    ):
        """
        Initialize RAG-integrated tools.

        Args:
            rag_memory: RAG memory system
            tools_manager: Traditional tools manager
            ollama_client: Ollama client for code LLM
        """
        self.rag_memory = rag_memory or RAGMemory()
        self.tools_manager = tools_manager or ToolsManager()
        self.client = ollama_client or OllamaClient()

        # Function registry: function_name -> (code, metadata, artifact_id)
        self.function_registry: Dict[str, Tuple[str, FunctionMetadata, str]] = {}

        # Load existing functions from RAG
        self._load_functions_from_rag()

    def _load_functions_from_rag(self):
        """Load existing functions from RAG memory."""
        functions = self.rag_memory.list_all(artifact_type=ArtifactType.FUNCTION)

        for artifact in functions:
            try:
                metadata_dict = artifact.metadata.get("function_metadata", {})
                metadata = FunctionMetadata(
                    function_name=metadata_dict.get("function_name", "unknown"),
                    description=metadata_dict.get("description", ""),
                    parameters=metadata_dict.get("parameters", {}),
                    returns=metadata_dict.get("returns", ""),
                    tags=metadata_dict.get("tags", []),
                    use_cases=metadata_dict.get("use_cases", []),
                    complexity=metadata_dict.get("complexity", "O(n)"),
                    quality_score=metadata_dict.get("quality_score", 0.0),
                    token_count=metadata_dict.get("token_count", 0)
                )

                self.function_registry[metadata.function_name] = (
                    artifact.content,  # code
                    metadata,
                    artifact.artifact_id
                )

            except Exception as e:
                logger.warning(f"Failed to load function {artifact.artifact_id}: {e}")

        logger.info(f"✓ Loaded {len(self.function_registry)} functions from RAG")

    def find_solution_at_level(
        self,
        level: str,  # "workflow", "sub_workflow", "function"
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 3,
        min_similarity: float = 0.6
    ) -> List[Tuple[Artifact, float]]:
        """
        Find closest solution from RAG at specified level.

        Args:
            level: Level to search (workflow/sub_workflow/function)
            task_description: What needs to be done
            context: Additional context for matching
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (Artifact, similarity_score) tuples
        """
        logger.info(f"Searching RAG at {level} level for: {task_description[:50]}...")

        # Map level to artifact type
        level_to_type = {
            "workflow": ArtifactType.WORKFLOW,
            "nodeplan": ArtifactType.PLAN,  # Node plan is the actual script
            "function": ArtifactType.FUNCTION
        }

        artifact_type = level_to_type.get(level)

        if not artifact_type:
            logger.warning(f"Unknown level: {level}")
            return []

        # Search RAG
        results = self.rag_memory.find_similar(
            query=task_description,
            artifact_type=artifact_type,
            top_k=top_k,
            min_similarity=min_similarity
        )

        logger.info(f"✓ Found {len(results)} similar {level}(s)")

        return results

    def get_tools_for_overseer(
        self,
        task_description: str,
        level: str = "workflow",
        max_tools: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get relevant tools from RAG to pass to overseer for evaluation.

        Args:
            task_description: Task to solve
            level: Level of operation
            max_tools: Maximum tools to return

        Returns:
            List of tool definitions
        """
        logger.info(f"Fetching tools for overseer at {level} level...")

        # Get tools from multiple sources
        all_tools = []

        # 1. Get functions from RAG
        functions = self.find_solution_at_level("function", task_description, top_k=max_tools)

        for artifact, similarity in functions:
            all_tools.append({
                "type": "function",
                "name": artifact.name,
                "description": artifact.description,
                "code": artifact.content,
                "similarity": similarity,
                "quality": artifact.quality_score,
                "tags": artifact.tags,
                "artifact_id": artifact.artifact_id
            })

        # 2. Get nodeplans if applicable
        if level != "function":
            nodeplans = self.find_solution_at_level("nodeplan", task_description, top_k=3)

            for artifact, similarity in nodeplans:
                all_tools.append({
                    "type": "nodeplan",
                    "name": artifact.name,
                    "description": artifact.description,
                    "plan": json.loads(artifact.content) if artifact.content.startswith("{") else artifact.content,
                    "similarity": similarity,
                    "quality": artifact.quality_score,
                    "artifact_id": artifact.artifact_id
                })

        # 3. Get workflows if at top level
        if level == "workflow":
            workflows = self.find_solution_at_level("workflow", task_description, top_k=2)

            for artifact, similarity in workflows:
                all_tools.append({
                    "type": "workflow",
                    "name": artifact.name,
                    "description": artifact.description,
                    "workflow": json.loads(artifact.content) if artifact.content.startswith("{") else artifact.content,
                    "similarity": similarity,
                    "quality": artifact.quality_score,
                    "artifact_id": artifact.artifact_id
                })

        # Sort by similarity and quality
        all_tools.sort(key=lambda t: (t["similarity"], t.get("quality", 0)), reverse=True)

        return all_tools[:max_tools]

    def optimize_and_save(
        self,
        code: str,
        task_description: str,
        level: str,
        quality_score: float,
        existing_artifact_id: Optional[str] = None
    ) -> str:
        """
        Token optimization: Code LLM optimizes code and saves to RAG.

        Args:
            code: Code to optimize
            task_description: What the code does
            level: Level (workflow/sub_workflow/function)
            quality_score: Quality score of this implementation
            existing_artifact_id: If optimizing existing artifact

        Returns:
            New artifact ID
        """
        logger.info(f"Optimizing {level} code...")

        # Extract function metadata if it's a function
        if level == "function":
            metadata = self._extract_function_metadata(code)
        else:
            metadata = None

        # Check if code is different from existing
        is_different = True
        if existing_artifact_id:
            existing = self.rag_memory.get_artifact(existing_artifact_id)
            if existing and existing.content == code:
                is_different = False
                logger.info("Code is identical to existing, skipping optimization")

        # If different, optimize with code LLM
        optimized_code = code
        if is_different:
            optimized_code = self._optimize_with_code_llm(code, task_description, level, metadata)

        # Calculate token count
        token_count = self._estimate_tokens(optimized_code)

        # Save to RAG
        artifact_id = self._save_to_rag(
            code=optimized_code,
            task_description=task_description,
            level=level,
            metadata=metadata,
            quality_score=quality_score,
            token_count=token_count
        )

        logger.info(f"✓ Optimized and saved to RAG: {artifact_id} ({token_count} tokens)")

        return artifact_id

    def _optimize_with_code_llm(
        self,
        code: str,
        task_description: str,
        level: str,
        metadata: Optional[FunctionMetadata]
    ) -> str:
        """Use code LLM to optimize code (reduce tokens, improve efficiency)."""
        logger.info("Running code optimization with LLM...")

        prompt = f"""Optimize this {level} code for:
1. Reduced token count (make it more concise)
2. Improved efficiency
3. Better readability
4. Maintained correctness

Task: {task_description}

Current Code:
```python
{code}
```

{"Function Metadata: " + json.dumps(metadata.to_dict(), indent=2) if metadata else ""}

Return ONLY the optimized Python code. Maintain functionality but reduce tokens and improve performance.
"""

        optimized = self.client.generate(
            model="codellama",
            prompt=prompt,
            temperature=0.3  # Lower temperature for consistent optimization
        )

        # Extract code from response
        code_match = None
        import re
        code_patterns = [
            r'```python\n(.*?)\n```',
            r'```\n(.*?)\n```',
        ]

        for pattern in code_patterns:
            match = re.search(pattern, optimized, re.DOTALL)
            if match:
                code_match = match.group(1)
                break

        if code_match:
            optimized = code_match.strip()
        else:
            # If no code block found, use the whole response
            optimized = optimized.strip()

        # Verify optimization actually reduced tokens
        original_tokens = self._estimate_tokens(code)
        optimized_tokens = self._estimate_tokens(optimized)

        if optimized_tokens < original_tokens:
            logger.info(f"✓ Optimized: {original_tokens} → {optimized_tokens} tokens ({((original_tokens - optimized_tokens) / original_tokens * 100):.1f}% reduction)")
            return optimized
        else:
            logger.info("Optimization didn't reduce tokens, keeping original")
            return code

    def _extract_function_metadata(self, code: str) -> Optional[FunctionMetadata]:
        """Extract metadata from function code (docstring, comments, tags)."""
        try:
            # Parse code to extract function information
            tree = ast.parse(code)

            # Find function definition
            func_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_def = node
                    break

            if not func_def:
                return None

            # Extract docstring
            docstring = ast.get_docstring(func_def) or ""

            # Extract tags from comments
            tags = []
            use_cases = []

            # Parse docstring for tags and use cases
            for line in docstring.split('\n'):
                line = line.strip()
                if line.startswith('#tags:'):
                    tags = [t.strip() for t in line.replace('#tags:', '').split(',')]
                elif line.startswith('#use-case:'):
                    use_cases.append(line.replace('#use-case:', '').strip())

            # Extract parameters
            parameters = {}
            for arg in func_def.args.args:
                parameters[arg.arg] = {"type": "any", "description": ""}

            # Extract return annotation
            returns = "any"
            if func_def.returns:
                returns = ast.unparse(func_def.returns)

            metadata = FunctionMetadata(
                function_name=func_def.name,
                description=docstring.split('\n')[0] if docstring else "",
                parameters=parameters,
                returns=returns,
                tags=tags or ["function"],
                use_cases=use_cases,
                complexity="O(n)",  # Default, could be extracted from comments
                quality_score=0.0,
                token_count=self._estimate_tokens(code)
            )

            return metadata

        except Exception as e:
            logger.warning(f"Failed to extract function metadata: {e}")
            return None

    def _save_to_rag(
        self,
        code: str,
        task_description: str,
        level: str,
        metadata: Optional[FunctionMetadata],
        quality_score: float,
        token_count: int
    ) -> str:
        """Save code to RAG with appropriate metadata."""
        level_to_type = {
            "workflow": ArtifactType.WORKFLOW,
            "sub_workflow": ArtifactType.SUB_WORKFLOW,
            "function": ArtifactType.FUNCTION
        }

        artifact_type = level_to_type.get(level, ArtifactType.FUNCTION)

        # Generate unique ID
        code_hash = hashlib.md5(code.encode()).hexdigest()[:8]
        artifact_id = f"{level}_{code_hash}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Prepare tags
        tags = [level]
        if metadata:
            tags.extend(metadata.tags)
            name = metadata.function_name
            description = metadata.description
        else:
            name = task_description[:50]
            description = task_description

        # Save to RAG
        artifact = self.rag_memory.store_artifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            name=name,
            description=description,
            content=code,
            tags=tags,
            metadata={
                "function_metadata": metadata.to_dict() if metadata else {},
                "quality_score": quality_score,
                "token_count": token_count,
                "level": level
            },
            auto_embed=True
        )

        # Update quality score in RAG
        self.rag_memory.update_quality_score(artifact_id, quality_score)

        # If function, add to registry
        if level == "function" and metadata:
            self.function_registry[metadata.function_name] = (code, metadata, artifact_id)

        return artifact_id

    def _estimate_tokens(self, code: str) -> int:
        """Estimate token count for code."""
        # Simple estimation: ~4 characters per token on average
        return len(code) // 4

    def register_function_to_rag(
        self,
        function_code: str,
        tags: List[str],
        use_cases: List[str],
        quality_score: float = 0.0
    ) -> str:
        """
        Register a function to RAG with full metadata.

        Args:
            function_code: Complete function code with docstring
            tags: Tags describing the function
            use_cases: Specific use cases
            quality_score: Initial quality score

        Returns:
            Artifact ID
        """
        # Extract metadata
        metadata = self._extract_function_metadata(function_code)

        if not metadata:
            raise ValueError("Could not extract metadata from function code")

        # Update metadata with provided info
        metadata.tags.extend(tags)
        metadata.use_cases.extend(use_cases)
        metadata.quality_score = quality_score

        # Save to RAG
        artifact_id = self._save_to_rag(
            code=function_code,
            task_description=metadata.description,
            level="function",
            metadata=metadata,
            quality_score=quality_score,
            token_count=metadata.token_count
        )

        logger.info(f"✓ Registered function '{metadata.function_name}' to RAG: {artifact_id}")

        return artifact_id

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about RAG-integrated tools."""
        rag_stats = self.rag_memory.get_statistics()

        return {
            "rag_memory": rag_stats,
            "function_registry_size": len(self.function_registry),
            "avg_function_quality": sum(m[1].quality_score for m in self.function_registry.values()) / len(self.function_registry) if self.function_registry else 0.0
        }
