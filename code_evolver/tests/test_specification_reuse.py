"""
Unit tests for specification storage and retrieval in RAG.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from src.qdrant_rag_memory import QdrantRAGMemory
from src.rag_memory import ArtifactType
from src.ollama_client import OllamaClient
from src.config_manager import ConfigManager


class TestSpecificationReuse:
    """Test specification storage and retrieval functionality."""

    def setup_method(self):
        """Set up test fixtures with temporary RAG storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ConfigManager()
        self.client = OllamaClient(config_manager=self.config)

        # Use NumPy-based RAG for testing (simpler than Qdrant for unit tests)
        from src.rag_memory import RAGMemory
        self.rag = RAGMemory(
            memory_path=self.temp_dir,
            ollama_client=self.client
        )

    def teardown_method(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_store_specification(self):
        """Test storing a specification in RAG."""
        spec_content = """
        ## Problem Definition
        Calculate the sum of two integers.

        ## Implementation Plan
        1. Read two integers from input
        2. Add them together
        3. Return the result

        ## Test Cases
        - Input: {a: 5, b: 3} -> Output: 8
        - Input: {a: 10, b: 20} -> Output: 30
        """

        self.rag.store_artifact(
            artifact_id="spec_test_add",
            artifact_type=ArtifactType.PLAN,
            name="Specification: add two numbers",
            description="Detailed specification for adding two integers",
            content=spec_content,
            tags=["specification", "plan", "overseer", "arithmetic"],
            metadata={
                "task_description": "add two numbers",
                "overseer_model": "llama3",
                "complexity": "SIMPLE"
            },
            auto_embed=False  # Skip embedding for speed in tests
        )

        # Verify it was stored
        artifact = self.rag.get_artifact("spec_test_add")
        assert artifact is not None, "specification should be stored"
        assert artifact.artifact_type == ArtifactType.PLAN
        assert "adding" in artifact.description.lower() or "add" in artifact.description.lower()
        assert artifact.metadata.get("complexity") == "SIMPLE"

    def test_retrieve_similar_specification(self):
        """Test retrieving a similar specification."""
        # Store a specification
        spec_content = """
        ## Problem Definition
        Multiply two integers together.

        ## Implementation Plan
        1. Read two integers from input
        2. Multiply them
        3. Return the result
        """

        self.rag.store_artifact(
            artifact_id="spec_multiply",
            artifact_type=ArtifactType.PLAN,
            name="Specification: multiply two numbers",
            description="Detailed specification for multiplying two integers",
            content=spec_content,
            tags=["specification", "plan", "arithmetic"],
            metadata={
                "task_description": "multiply two numbers",
                "complexity": "SIMPLE"
            },
            auto_embed=True
        )

        # Search for similar specification
        similar = self.rag.find_similar(
            "multiply 6 by 7",
            artifact_type=ArtifactType.PLAN,
            top_k=1
        )

        assert len(similar) > 0, "should find similar specification"
        spec_artifact, similarity = similar[0]
        assert spec_artifact.artifact_type == ArtifactType.PLAN
        assert "multiply" in spec_artifact.content.lower()

    def test_specification_has_complexity_metadata(self):
        """Test that stored specifications include complexity metadata."""
        self.rag.store_artifact(
            artifact_id="spec_fibonacci",
            artifact_type=ArtifactType.PLAN,
            name="Specification: fibonacci sequence",
            description="Specification for calculating fibonacci sequence",
            content="Detailed fibonacci implementation plan...",
            tags=["specification", "plan", "complex"],
            metadata={
                "task_description": "calculate fibonacci sequence",
                "overseer_model": "llama3",
                "complexity": "COMPLEX"
            },
            auto_embed=False
        )

        artifact = self.rag.get_artifact("spec_fibonacci")
        assert artifact.metadata.get("complexity") == "COMPLEX"
        assert artifact.metadata.get("task_description") == "calculate fibonacci sequence"

    def test_filter_specifications_by_complexity(self):
        """Test filtering specifications by complexity level."""
        # Store simple spec
        self.rag.store_artifact(
            artifact_id="spec_simple_1",
            artifact_type=ArtifactType.PLAN,
            name="Specification: simple task",
            description="Simple arithmetic operation",
            content="Simple plan...",
            tags=["specification", "simple"],
            metadata={"complexity": "SIMPLE"},
            auto_embed=False
        )

        # Store complex spec
        self.rag.store_artifact(
            artifact_id="spec_complex_1",
            artifact_type=ArtifactType.PLAN,
            name="Specification: complex task",
            description="Complex algorithm",
            content="Complex plan...",
            tags=["specification", "complex"],
            metadata={"complexity": "COMPLEX"},
            auto_embed=False
        )

        # Retrieve and check
        simple_spec = self.rag.get_artifact("spec_simple_1")
        complex_spec = self.rag.get_artifact("spec_complex_1")

        assert simple_spec.metadata.get("complexity") == "SIMPLE"
        assert complex_spec.metadata.get("complexity") == "COMPLEX"

    def test_specification_includes_task_description(self):
        """Test that specifications store the original task description."""
        task_desc = "create a function to validate email addresses"

        self.rag.store_artifact(
            artifact_id="spec_email_validation",
            artifact_type=ArtifactType.PLAN,
            name="Specification: email validation",
            description=f"Specification for: {task_desc}",
            content="Email validation specification...",
            tags=["specification", "validation"],
            metadata={
                "task_description": task_desc,
                "complexity": "COMPLEX"
            },
            auto_embed=False
        )

        artifact = self.rag.get_artifact("spec_email_validation")
        assert artifact.metadata.get("task_description") == task_desc
