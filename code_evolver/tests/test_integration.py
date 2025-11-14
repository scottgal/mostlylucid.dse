#!/usr/bin/env python3
"""
Integration tests for Code Evolver system.
Tests the full end-to-end workflow with progress display.
"""
import unittest
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import (
    ConfigManager, OllamaClient, RAGMemory,
    ProgressDisplay, Stage, get_progress_display
)


class TestProgressDisplay(unittest.TestCase):
    """Test progress display functionality."""

    def test_progress_display_basic(self):
        """Test basic progress display functionality."""
        progress = ProgressDisplay(use_rich=False)  # Use simple display for testing

        progress.start("Test Task")
        progress.enter_stage(Stage.INITIALIZATION, "Setting up test environment")
        progress.exit_stage(success=True)

        progress.enter_stage(Stage.OVERSEER_PLANNING, "Planning approach")
        progress.update_token_estimate("planning", 150, "llama3")
        progress.update_speed(tokens_per_second=25.0, chars_per_second=100.0)
        progress.exit_stage(success=True)

        progress.show_metrics_table({
            "latency_ms": 1250,
            "tokens": 150,
            "quality_score": 0.85
        })

        progress.show_summary(success=True, final_metrics={
            "total_tokens": 500,
            "average_speed": 23.5,
            "quality": 0.87
        })

        self.assertIsNotNone(progress)

    def test_token_estimation(self):
        """Test token estimation."""
        progress = ProgressDisplay()
        text = "This is a test string for token estimation"
        tokens = progress.estimate_tokens(text)

        # Rough approximation: should be around len(text) / 4
        expected = len(text) // 4
        self.assertAlmostEqual(tokens, expected, delta=5)

    def test_context_info_display(self):
        """Test context window info display."""
        progress = ProgressDisplay(use_rich=False)
        progress.show_context_info(
            model="llama3",
            context_window=8192,
            prompt_length=2048
        )
        # Should not raise any exceptions

    def test_optimization_progress(self):
        """Test optimization progress display."""
        progress = ProgressDisplay(use_rich=False)
        progress.enter_stage(Stage.EVOLUTION, "Optimizing code")

        # Simulate optimization iterations
        scores = [0.70, 0.75, 0.78, 0.82, 0.85]
        for i, score in enumerate(scores, 1):
            improvement = score - scores[i-2] if i > 1 else 0
            progress.show_optimization_progress(i, score, improvement)

        progress.exit_stage(success=True)


class TestConfigManagerIntegration(unittest.TestCase):
    """Test configuration manager with new features."""

    def test_embedding_model_config(self):
        """Test embedding model configuration."""
        config = ConfigManager()

        # Test new embedding model property
        embedding_model = config.embedding_model
        self.assertIsNotNone(embedding_model)
        self.assertIn("embed", embedding_model.lower())  # Should contain "embed"

    def test_context_window_config(self):
        """Test context window configuration."""
        config = ConfigManager()

        # Test context window for known models
        llama3_context = config.get_context_window("llama3")
        self.assertGreater(llama3_context, 0)

        codellama_context = config.get_context_window("codellama")
        self.assertGreater(codellama_context, 0)

        # Test default for unknown model
        unknown_context = config.get_context_window("unknown_model_xyz")
        self.assertGreater(unknown_context, 0)

    def test_rag_memory_config(self):
        """Test RAG memory configuration."""
        config = ConfigManager()

        rag_path = config.rag_memory_path
        self.assertIsNotNone(rag_path)

        max_length = config.max_embedding_content_length
        self.assertGreater(max_length, 0)


class TestRAGMemoryIntegration(unittest.TestCase):
    """Test RAG memory with new configuration."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rag_memory_with_config(self):
        """Test RAG memory with configurable parameters."""
        rag = RAGMemory(
            memory_path=self.test_dir,
            embedding_model="nomic-embed-text",
            max_content_length=500
        )

        # Verify configuration was applied
        self.assertEqual(rag.embedding_model, "nomic-embed-text")
        self.assertEqual(rag.max_content_length, 500)

    def test_content_truncation(self):
        """Test content truncation in embeddings."""
        rag = RAGMemory(
            memory_path=self.test_dir,
            embedding_model="nomic-embed-text",
            max_content_length=100
        )

        # Store artifact with long content
        long_content = "x" * 500
        from src.rag_memory import ArtifactType

        artifact = rag.store_artifact(
            artifact_id="test_long",
            artifact_type=ArtifactType.FUNCTION,
            name="Test Function",
            description="Test description",
            content=long_content,
            tags=["test"],
            auto_embed=False  # Don't try to actually generate embeddings
        )

        # Verify artifact was stored with full content
        self.assertEqual(artifact.content, long_content)


class TestOllamaClientIntegration(unittest.TestCase):
    """Test Ollama client with new features."""

    def test_truncate_prompt(self):
        """Test prompt truncation based on context window."""
        config = ConfigManager()
        client = OllamaClient(config_manager=config)

        # Test with short prompt (should not truncate)
        short_prompt = "This is a short prompt"
        truncated = client.truncate_prompt(short_prompt, "llama3")
        self.assertEqual(short_prompt, truncated)

        # Test with very long prompt (should truncate)
        long_prompt = "x" * 100000  # Very long prompt
        truncated = client.truncate_prompt(long_prompt, "llama3")
        self.assertLess(len(truncated), len(long_prompt))
        self.assertIn("truncated", truncated.lower())


class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete end-to-end workflow with progress display."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config = ConfigManager()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_workflow_with_progress(self):
        """Test complete workflow with progress display."""
        progress = ProgressDisplay(use_rich=False)

        # Start task
        progress.start("Code Generation Workflow Test")

        # Stage 1: Initialization
        progress.enter_stage(Stage.INITIALIZATION, "Loading configuration")
        config = ConfigManager()
        self.assertIsNotNone(config)
        progress.exit_stage(success=True)

        # Stage 2: Overseer Planning
        progress.enter_stage(Stage.OVERSEER_PLANNING, "Planning code generation strategy")
        planning_prompt = "Write a function to calculate fibonacci numbers"
        estimated_tokens = progress.estimate_tokens(planning_prompt)
        progress.update_token_estimate("planning", estimated_tokens, "llama3")

        # Show context usage
        context_window = config.get_context_window("llama3")
        progress.show_context_info("llama3", context_window, estimated_tokens)
        progress.exit_stage(success=True)

        # Stage 3: Code Generation
        progress.enter_stage(Stage.CODE_GENERATION, "Generating code with codellama")
        code_prompt = "Based on the plan, write Python code for fibonacci"
        estimated_tokens = progress.estimate_tokens(code_prompt)
        progress.update_token_estimate("generation", estimated_tokens, "codellama")

        context_window = config.get_context_window("codellama")
        progress.show_context_info("codellama", context_window, estimated_tokens)
        progress.exit_stage(success=True)

        # Stage 4: RAG Storage
        progress.enter_stage(Stage.RAG_STORAGE, "Storing results in RAG memory")
        rag = RAGMemory(
            memory_path=self.test_dir,
            embedding_model=config.embedding_model,
            max_content_length=config.max_embedding_content_length
        )
        self.assertIsNotNone(rag)
        progress.exit_stage(success=True)

        # Final summary
        progress.show_summary(success=True, final_metrics={
            "total_stages": 4,
            "estimated_tokens": 200,
            "quality_score": 0.85
        })


if __name__ == "__main__":
    unittest.main()
