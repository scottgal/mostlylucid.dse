"""
Comprehensive tests for RAG Memory System.
Tests artifact storage, retrieval, embedding generation, and similarity search.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag_memory import RAGMemory, Artifact, ArtifactType


class TestRAGMemory(unittest.TestCase):
    """Test suite for RAG Memory system."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.rag = RAGMemory(memory_path=self.test_dir, ollama_client=None)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initialization(self):
        """Test RAG memory initialization."""
        self.assertTrue(Path(self.test_dir).exists())
        self.assertTrue((Path(self.test_dir) / "artifacts").exists())
        self.assertEqual(len(self.rag.artifacts), 0)

    def test_store_plan_artifact(self):
        """Test storing a plan artifact."""
        artifact = self.rag.store_artifact(
            artifact_id="test_plan_001",
            artifact_type=ArtifactType.PLAN,
            name="Text Processing Strategy",
            description="Strategy for processing large text files efficiently",
            content="1. Read in chunks\n2. Process incrementally\n3. Stream output",
            tags=["text-processing", "streaming", "efficiency"],
            metadata={"author": "overseer", "complexity": "medium"},
            auto_embed=False  # Skip embedding for this test
        )

        self.assertEqual(artifact.artifact_id, "test_plan_001")
        self.assertEqual(artifact.artifact_type, ArtifactType.PLAN)
        self.assertEqual(len(artifact.tags), 3)
        self.assertIn("test_plan_001", self.rag.artifacts)

    def test_store_function_artifact(self):
        """Test storing a function artifact."""
        code = """
def validate_email(email: str) -> bool:
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
"""
        artifact = self.rag.store_artifact(
            artifact_id="func_validate_email",
            artifact_type=ArtifactType.FUNCTION,
            name="Email Validator",
            description="Validates email addresses using regex",
            content=code,
            tags=["validation", "email", "regex", "utility"],
            auto_embed=False
        )

        self.assertEqual(artifact.artifact_type, ArtifactType.FUNCTION)
        self.assertIn("validation", artifact.tags)

    def test_store_workflow_artifact(self):
        """Test storing a workflow artifact."""
        workflow = {
            "steps": [
                {"action": "generate_code", "model": "codellama"},
                {"action": "run_tests", "framework": "pytest"},
                {"action": "evaluate", "model": "llama3"}
            ]
        }

        import json
        artifact = self.rag.store_artifact(
            artifact_id="workflow_code_gen",
            artifact_type=ArtifactType.WORKFLOW,
            name="Code Generation Workflow",
            description="Complete workflow for generating and testing code",
            content=json.dumps(workflow, indent=2),
            tags=["workflow", "code-generation", "testing"],
            auto_embed=False
        )

        self.assertEqual(artifact.artifact_type, ArtifactType.WORKFLOW)

    def test_find_by_tags(self):
        """Test finding artifacts by tags."""
        # Store multiple artifacts
        for i in range(5):
            self.rag.store_artifact(
                artifact_id=f"artifact_{i}",
                artifact_type=ArtifactType.FUNCTION,
                name=f"Function {i}",
                description=f"Test function {i}",
                content=f"def func_{i}(): pass",
                tags=["utility", f"group{i % 2}"],
                auto_embed=False
            )

        # Find by single tag
        results = self.rag.find_by_tags(["utility"])
        self.assertEqual(len(results), 5)

        # Find by specific tag
        results = self.rag.find_by_tags(["group0"])
        self.assertEqual(len(results), 3)  # artifacts 0, 2, 4

    def test_find_by_tags_match_all(self):
        """Test finding artifacts requiring all tags."""
        self.rag.store_artifact(
            artifact_id="art1",
            artifact_type=ArtifactType.FUNCTION,
            name="Art 1",
            description="Test",
            content="code",
            tags=["python", "utility", "validation"],
            auto_embed=False
        )

        self.rag.store_artifact(
            artifact_id="art2",
            artifact_type=ArtifactType.FUNCTION,
            name="Art 2",
            description="Test",
            content="code",
            tags=["python", "utility"],
            auto_embed=False
        )

        # Match all tags
        results = self.rag.find_by_tags(["python", "utility", "validation"], match_all=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].artifact_id, "art1")

        # Match any tag
        results = self.rag.find_by_tags(["python", "utility"], match_all=False)
        self.assertEqual(len(results), 2)

    def test_keyword_search(self):
        """Test keyword-based search."""
        self.rag.store_artifact(
            artifact_id="test_email",
            artifact_type=ArtifactType.FUNCTION,
            name="Email Validator",
            description="Validates email addresses",
            content="def validate_email(): pass",
            tags=["email", "validation"],
            auto_embed=False
        )

        self.rag.store_artifact(
            artifact_id="test_phone",
            artifact_type=ArtifactType.FUNCTION,
            name="Phone Validator",
            description="Validates phone numbers",
            content="def validate_phone(): pass",
            tags=["phone", "validation"],
            auto_embed=False
        )

        # Search for email
        results = self.rag.search_by_keywords("email validator")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0][0].artifact_id, "test_email")

    def test_filter_by_type(self):
        """Test filtering by artifact type."""
        # Store different types
        self.rag.store_artifact(
            artifact_id="plan1",
            artifact_type=ArtifactType.PLAN,
            name="Plan 1",
            description="Test plan",
            content="strategy",
            tags=["test"],
            auto_embed=False
        )

        self.rag.store_artifact(
            artifact_id="func1",
            artifact_type=ArtifactType.FUNCTION,
            name="Func 1",
            description="Test function",
            content="def func(): pass",
            tags=["test"],
            auto_embed=False
        )

        # List only plans
        plans = self.rag.list_all(artifact_type=ArtifactType.PLAN)
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].artifact_type, ArtifactType.PLAN)

        # List only functions
        functions = self.rag.list_all(artifact_type=ArtifactType.FUNCTION)
        self.assertEqual(len(functions), 1)
        self.assertEqual(functions[0].artifact_type, ArtifactType.FUNCTION)

    def test_usage_tracking(self):
        """Test usage count tracking."""
        artifact_id = "test_usage"
        self.rag.store_artifact(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.FUNCTION,
            name="Test Usage",
            description="Test",
            content="code",
            tags=["test"],
            auto_embed=False
        )

        # Initial usage count
        artifact = self.rag.get_artifact(artifact_id)
        self.assertEqual(artifact.usage_count, 0)

        # Increment usage
        self.rag.increment_usage(artifact_id)
        self.rag.increment_usage(artifact_id)
        self.rag.increment_usage(artifact_id)

        artifact = self.rag.get_artifact(artifact_id)
        self.assertEqual(artifact.usage_count, 3)

    def test_quality_score(self):
        """Test quality score management."""
        artifact_id = "test_quality"
        self.rag.store_artifact(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.FUNCTION,
            name="Test Quality",
            description="Test",
            content="code",
            tags=["test"],
            auto_embed=False
        )

        # Initial quality score
        artifact = self.rag.get_artifact(artifact_id)
        self.assertEqual(artifact.quality_score, 0.0)

        # Update quality score
        self.rag.update_quality_score(artifact_id, 0.85)

        artifact = self.rag.get_artifact(artifact_id)
        self.assertEqual(artifact.quality_score, 0.85)

        # Test clamping (should clamp to 0-1 range)
        self.rag.update_quality_score(artifact_id, 1.5)
        artifact = self.rag.get_artifact(artifact_id)
        self.assertEqual(artifact.quality_score, 1.0)

        self.rag.update_quality_score(artifact_id, -0.5)
        artifact = self.rag.get_artifact(artifact_id)
        self.assertEqual(artifact.quality_score, 0.0)

    def test_persistence(self):
        """Test saving and loading from disk."""
        # Store artifact
        self.rag.store_artifact(
            artifact_id="persist_test",
            artifact_type=ArtifactType.PLAN,
            name="Persistence Test",
            description="Testing persistence",
            content="This should persist",
            tags=["test", "persistence"],
            auto_embed=False
        )

        # Create new RAG instance pointing to same directory
        rag2 = RAGMemory(memory_path=self.test_dir, ollama_client=None)

        # Check artifact was loaded
        self.assertIn("persist_test", rag2.artifacts)
        artifact = rag2.get_artifact("persist_test")
        self.assertEqual(artifact.name, "Persistence Test")
        self.assertEqual(len(artifact.tags), 2)

    def test_delete_artifact(self):
        """Test deleting artifacts."""
        artifact_id = "delete_test"
        self.rag.store_artifact(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.FUNCTION,
            name="Delete Test",
            description="To be deleted",
            content="code",
            tags=["test", "delete"],
            auto_embed=False
        )

        # Verify it exists
        self.assertIsNotNone(self.rag.get_artifact(artifact_id))

        # Delete it
        result = self.rag.delete_artifact(artifact_id)
        self.assertTrue(result)

        # Verify it's gone
        self.assertIsNone(self.rag.get_artifact(artifact_id))

        # Try deleting again (should return False)
        result = self.rag.delete_artifact(artifact_id)
        self.assertFalse(result)

    def test_tags_index(self):
        """Test tags index functionality."""
        self.rag.store_artifact(
            artifact_id="tag_test_1",
            artifact_type=ArtifactType.FUNCTION,
            name="Tag Test 1",
            description="Test",
            content="code",
            tags=["python", "utility"],
            auto_embed=False
        )

        self.rag.store_artifact(
            artifact_id="tag_test_2",
            artifact_type=ArtifactType.FUNCTION,
            name="Tag Test 2",
            description="Test",
            content="code",
            tags=["python", "validation"],
            auto_embed=False
        )

        # Check tags index
        self.assertIn("python", self.rag.tags_index)
        self.assertIn("utility", self.rag.tags_index)
        self.assertIn("validation", self.rag.tags_index)

        # Python tag should have 2 artifacts
        self.assertEqual(len(self.rag.tags_index["python"]), 2)

    def test_statistics(self):
        """Test statistics generation."""
        # Store various artifacts
        self.rag.store_artifact(
            artifact_id="stats_1",
            artifact_type=ArtifactType.PLAN,
            name="Stats 1",
            description="Test",
            content="content",
            tags=["test"],
            auto_embed=False
        )

        self.rag.store_artifact(
            artifact_id="stats_2",
            artifact_type=ArtifactType.FUNCTION,
            name="Stats 2",
            description="Test",
            content="content",
            tags=["test"],
            auto_embed=False
        )

        # Increment usage and set quality
        self.rag.increment_usage("stats_2")
        self.rag.update_quality_score("stats_2", 0.9)

        # Get statistics
        stats = self.rag.get_statistics()

        self.assertEqual(stats["total_artifacts"], 2)
        self.assertEqual(stats["by_type"]["plan"], 1)
        self.assertEqual(stats["by_type"]["function"], 1)
        self.assertGreater(stats["total_tags"], 0)

        # Check most used
        self.assertEqual(len(stats["most_used"]), 2)
        self.assertEqual(stats["most_used"][0]["id"], "stats_2")

        # Check highest quality
        self.assertEqual(len(stats["highest_quality"]), 2)
        self.assertEqual(stats["highest_quality"][0]["id"], "stats_2")


class TestArtifact(unittest.TestCase):
    """Test Artifact class."""

    def test_artifact_creation(self):
        """Test creating an artifact."""
        artifact = Artifact(
            artifact_id="test_001",
            artifact_type=ArtifactType.PLAN,
            name="Test Plan",
            description="A test plan",
            content="Plan content",
            tags=["test", "plan"]
        )

        self.assertEqual(artifact.artifact_id, "test_001")
        self.assertEqual(artifact.artifact_type, ArtifactType.PLAN)
        self.assertEqual(len(artifact.tags), 2)
        self.assertEqual(artifact.usage_count, 0)
        self.assertEqual(artifact.quality_score, 0.0)

    def test_artifact_serialization(self):
        """Test artifact to_dict and from_dict."""
        artifact = Artifact(
            artifact_id="ser_test",
            artifact_type=ArtifactType.FUNCTION,
            name="Serialization Test",
            description="Testing serialization",
            content="def test(): pass",
            tags=["test"],
            metadata={"key": "value"}
        )

        # Convert to dict
        data = artifact.to_dict()

        # Verify dict structure
        self.assertEqual(data["artifact_id"], "ser_test")
        self.assertEqual(data["artifact_type"], "function")
        self.assertEqual(data["metadata"]["key"], "value")

        # Convert back to artifact
        artifact2 = Artifact.from_dict(data)

        self.assertEqual(artifact2.artifact_id, artifact.artifact_id)
        self.assertEqual(artifact2.artifact_type, artifact.artifact_type)
        self.assertEqual(artifact2.name, artifact.name)
        self.assertEqual(artifact2.metadata, artifact.metadata)


if __name__ == "__main__":
    unittest.main()
