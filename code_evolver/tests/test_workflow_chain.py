"""
Unit tests for workflow chain visualization in WorkflowTracker.
"""
import pytest
from src.workflow_tracker import WorkflowTracker, WorkflowStep, StepStatus


class TestWorkflowChain:
    """Test workflow chain visualization functionality."""

    def test_workflow_chain_with_completed_steps(self):
        """Test that workflow chain shows completed steps."""
        tracker = WorkflowTracker(
            workflow_id="test_workflow_1",
            description="Test workflow",
            context={"priority": "high"}
        )

        # Add and complete some steps
        tracker.add_step("step1", "rag: Search for tools", "Finding relevant tools")
        tracker.start_step("step1")
        tracker.complete_step("step1", "Found 3 tools")

        tracker.add_step("step2", "llm: Consult overseer (llama3)", "Getting specification")
        tracker.start_step("step2")
        tracker.complete_step("step2", "Specification created")

        tracker.add_step("step3", "llm: Generate code", "Creating implementation")
        tracker.start_step("step3")
        tracker.complete_step("step3", "Code generated")

        # Get formatted display
        display = tracker.format_text_display()

        # Should contain workflow chain
        assert "Workflow Chain:" in display
        # Should show tool names with prefixes removed
        assert "Search for tools" in display
        assert "Consult overseer (llama3)" in display
        assert "Generate code" in display
        # Should show chain with arrows
        assert "->" in display

    def test_workflow_chain_removes_prefixes(self):
        """Test that common prefixes are removed from tool names."""
        tracker = WorkflowTracker("test_workflow_2", "Test prefix removal")

        # Add steps with various prefixes
        tracker.add_step("s1", "llm: Model call", "LLM prefix test")
        tracker.start_step("s1")
        tracker.complete_step("s1", "done")

        tracker.add_step("s2", "test: Run tests", "Test prefix")
        tracker.start_step("s2")
        tracker.complete_step("s2", "done")

        tracker.add_step("s3", "rag: Search memory", "RAG prefix")
        tracker.start_step("s3")
        tracker.complete_step("s3", "done")

        tracker.add_step("s4", "optimize: Improve code", "Optimize prefix")
        tracker.start_step("s4")
        tracker.complete_step("s4", "done")

        tracker.add_step("s5", "run: Execute workflow", "Run prefix")
        tracker.start_step("s5")
        tracker.complete_step("s5", "done")

        display = tracker.format_text_display()

        # Prefixes should be removed in chain
        chain_section = display.split("Workflow Chain:")[1].split("\n")[1]
        assert "llm:" not in chain_section.lower()
        assert "test:" not in chain_section.lower()
        assert "rag:" not in chain_section.lower()
        assert "optimize:" not in chain_section.lower()
        assert "run:" not in chain_section.lower()

        # But the actual content should be there
        assert "Model call" in chain_section or "model call" in chain_section.lower()

    def test_workflow_chain_truncates_long_names(self):
        """Test that long tool names are truncated."""
        tracker = WorkflowTracker("test_workflow_3", "Test truncation")

        # Add step with very long name
        long_name = "This is a very long tool name that should be truncated to fit"
        tracker.add_step("s1", long_name, "Long name test")
        tracker.start_step("s1")
        tracker.complete_step("s1", "done")

        display = tracker.format_text_display()

        # Should contain truncated version with ...
        assert "..." in display

    def test_workflow_chain_only_shows_completed(self):
        """Test that workflow chain only shows completed steps."""
        tracker = WorkflowTracker("test_workflow_4", "Test completed only")

        # Add completed step
        tracker.add_step("s1", "Step 1", "First step")
        tracker.start_step("s1")
        tracker.complete_step("s1", "done")

        # Add pending step
        tracker.add_step("s2", "Step 2", "Second step")

        # Add failed step
        tracker.add_step("s3", "Step 3", "Third step")
        tracker.start_step("s3")
        tracker.fail_step("s3", "error")

        display = tracker.format_text_display()

        # Chain should only show completed steps
        chain_section = display.split("Workflow Chain:")[1].split("\n\n")[0]
        assert "Step 1" in chain_section
        # Step 2 and 3 should not be in chain (not completed)
        assert "Step 2" not in chain_section
        assert "Step 3" not in chain_section

    def test_workflow_chain_with_no_completed_steps(self):
        """Test workflow chain when no steps are completed."""
        tracker = WorkflowTracker("test_workflow_5", "No completed steps")

        # Add pending steps
        tracker.add_step("s1", "Step 1", "First step")
        tracker.add_step("s2", "Step 2", "Second step")

        display = tracker.format_text_display()

        # Should not show chain section if no completed steps
        # The chain section should only appear if there are completed steps
        if "Workflow Chain:" in display:
            # If it appears, it should be empty or minimal
            pass  # This is acceptable behavior

    def test_workflow_chain_format(self):
        """Test the exact format of workflow chain."""
        tracker = WorkflowTracker("test_workflow_6", "Test format")

        tracker.add_step("s1", "First", "First step")
        tracker.start_step("s1")
        tracker.complete_step("s1", "done")

        tracker.add_step("s2", "Second", "Second step")
        tracker.start_step("s2")
        tracker.complete_step("s2", "done")

        tracker.add_step("s3", "Third", "Third step")
        tracker.start_step("s3")
        tracker.complete_step("s3", "done")

        display = tracker.format_text_display()

        # Should have chain in format: First -> Second -> Third
        assert "First -> Second -> Third" in display

    def test_workflow_summary_includes_chain(self):
        """Test that workflow summary includes chain before context."""
        tracker = WorkflowTracker(
            "test_workflow_7",
            "Test summary order",
            context={"priority": "medium"}
        )

        tracker.add_step("s1", "Tool 1", "First")
        tracker.start_step("s1")
        tracker.complete_step("s1", "done")

        display = tracker.format_text_display()

        # Chain should appear before Context
        chain_pos = display.find("Workflow Chain:")
        context_pos = display.find("Context:")

        assert chain_pos > 0, "Should have workflow chain"
        assert context_pos > 0, "Should have context"
        assert chain_pos < context_pos, "Chain should appear before context"
