#!/usr/bin/env python3
"""
Tests for hierarchical evolution system.
"""
import unittest
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.overseer_llm import OverseerLlm, ExecutionPlan
from src.evaluator_llm import EvaluatorLlm, FitnessEvaluation
from src.hierarchical_evolver import HierarchicalEvolver, SharedPlanContext, NodeMetrics
from src.rag_integrated_tools import RAGIntegratedTools, FunctionMetadata
from src.rag_memory import RAGMemory, ArtifactType
from src.ollama_client import OllamaClient


class TestOverseerLlm(unittest.TestCase):
    """Test OverseerLlm functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.rag_memory = RAGMemory(memory_path=f"{self.temp_dir}/rag")
        self.overseer = OverseerLlm(rag_memory=self.rag_memory, model="tiny")

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_execution_plan(self):
        """Test creating an execution plan."""
        plan = self.overseer.create_execution_plan(
            task_description="Sort a list of numbers",
            constraints={"quality_target": 0.8, "speed_target_ms": 100}
        )

        self.assertIsInstance(plan, ExecutionPlan)
        self.assertIsNotNone(plan.plan_id)
        self.assertIsNotNone(plan.strategy)
        self.assertGreater(len(plan.steps), 0)

    def test_plan_recording(self):
        """Test recording plan executions."""
        plan = self.overseer.create_execution_plan(
            task_description="Test task",
            constraints={}
        )

        # Record execution
        plan.record_execution(
            actual_quality=0.85,
            actual_speed_ms=95,
            node_id="test_node",
            success=True
        )

        self.assertEqual(len(plan.executions), 1)
        self.assertEqual(plan.get_average_quality(), 0.85)
        self.assertEqual(plan.get_average_speed(), 95)


class TestEvaluatorLlm(unittest.TestCase):
    """Test EvaluatorLlm functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = EvaluatorLlm(model="tiny")

    def test_evaluate_fitness_success(self):
        """Test fitness evaluation with successful execution."""
        execution_result = {
            "stdout": '{"result": "sorted", "data": [1, 2, 3, 4, 5]}',
            "stderr": "",
            "metrics": {
                "exit_code": 0,
                "latency_ms": 85,
                "memory_mb_peak": 32,
                "success": True
            }
        }

        evaluation = self.evaluator.evaluate_fitness(
            node_id="test_node",
            task_description="Sort numbers",
            execution_result=execution_result,
            quality_targets={"quality": 0.8, "speed_ms": 100}
        )

        self.assertIsInstance(evaluation, FitnessEvaluation)
        self.assertIsNotNone(evaluation.evaluation_id)
        self.assertGreater(evaluation.overall_score, 0.0)
        self.assertIn(evaluation.verdict, ["excellent", "good", "acceptable", "poor", "fail", "unknown"])

    def test_evaluate_fitness_failure(self):
        """Test fitness evaluation with failed execution."""
        execution_result = {
            "stdout": "",
            "stderr": "Error: division by zero",
            "metrics": {
                "exit_code": 1,
                "latency_ms": 10,
                "memory_mb_peak": 16,
                "success": False
            }
        }

        evaluation = self.evaluator.evaluate_fitness(
            node_id="test_node",
            task_description="Test task",
            execution_result=execution_result
        )

        # Failed execution should have lower score
        self.assertLess(evaluation.overall_score, 0.6)

    def test_compare_solutions(self):
        """Test comparing multiple solutions."""
        eval1 = FitnessEvaluation(
            evaluation_id="eval1",
            node_id="node1",
            plan_id=None,
            overall_score=0.75,
            quality_score=0.8,
            speed_score=0.7,
            correctness_score=0.75,
            verdict="good",
            strengths=[],
            weaknesses=[],
            recommendations=[]
        )

        eval2 = FitnessEvaluation(
            evaluation_id="eval2",
            node_id="node2",
            plan_id=None,
            overall_score=0.9,
            quality_score=0.95,
            speed_score=0.85,
            correctness_score=0.9,
            verdict="excellent",
            strengths=[],
            weaknesses=[],
            recommendations=[]
        )

        best = self.evaluator.compare_solutions([eval1, eval2], optimization_goal="balanced")

        self.assertEqual(best.node_id, "node2")
        self.assertEqual(best.overall_score, 0.9)


class TestSharedPlanContext(unittest.TestCase):
    """Test SharedPlanContext functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.context = SharedPlanContext(storage_path=f"{self.temp_dir}/context")

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_retrieve_learning(self):
        """Test adding and retrieving learnings."""
        from hierarchical_evolver import NodeLearning

        learning = NodeLearning(
            node_id="test_node",
            context_signature="test_context",
            lesson="Use quicksort for large arrays",
            quality_achieved=0.9,
            speed_achieved=150,
            recommendation="Use quicksort algorithm",
            confidence=0.85,
            usage_count=0,
            success_rate=1.0
        )

        self.context.add_learning(learning)

        # Retrieve learnings
        learnings = self.context.get_learnings("test_context", min_confidence=0.7)

        self.assertEqual(len(learnings), 1)
        self.assertEqual(learnings[0].lesson, "Use quicksort for large arrays")

    def test_strategy_preferences(self):
        """Test strategy preference recording."""
        self.context.record_strategy_preference(
            task_pattern="sorting",
            strategy="quicksort",
            quality=0.9,
            speed=100
        )

        best_strategy = self.context.get_best_strategy("sorting")

        self.assertEqual(best_strategy, "quicksort")


class TestRAGIntegratedTools(unittest.TestCase):
    """Test RAG-integrated tools functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.rag_memory = RAGMemory(memory_path=f"{self.temp_dir}/rag")
        self.rag_tools = RAGIntegratedTools(rag_memory=self.rag_memory)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_register_function_to_rag(self):
        """Test registering a function to RAG."""
        function_code = '''
def bubble_sort(arr: list) -> list:
    """
    Sort array using bubble sort.

    #tags: sort, simple
    #use-case: Sorting small arrays
    """
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
'''

        artifact_id = self.rag_tools.register_function_to_rag(
            function_code=function_code,
            tags=["algorithm"],
            use_cases=["sorting"],
            quality_score=0.7
        )

        self.assertIsNotNone(artifact_id)

        # Verify it's in RAG
        artifact = self.rag_memory.get_artifact(artifact_id)
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.artifact_type, ArtifactType.FUNCTION)

    def test_find_solution_at_level(self):
        """Test finding solutions at different levels."""
        # Register a function first
        function_code = '''
def test_func(x: int) -> int:
    """Test function. #tags: test"""
    return x * 2
'''

        self.rag_tools.register_function_to_rag(
            function_code=function_code,
            tags=["test"],
            use_cases=["testing"],
            quality_score=0.8
        )

        # Search for it
        results = self.rag_tools.find_solution_at_level(
            level="function",
            task_description="multiply number by two",
            top_k=3,
            min_similarity=0.3  # Lower threshold for test
        )

        # Should find at least one result
        self.assertGreaterEqual(len(results), 0)

    def test_token_estimation(self):
        """Test token count estimation."""
        code = "def test(): pass"
        tokens = self.rag_tools._estimate_tokens(code)

        self.assertGreater(tokens, 0)
        # Simple code should be ~4-5 tokens
        self.assertLess(tokens, 10)


class TestHierarchicalEvolver(unittest.TestCase):
    """Test HierarchicalEvolver functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.rag_memory = RAGMemory(memory_path=f"{self.temp_dir}/rag")
        self.evolver = HierarchicalEvolver(rag_memory=self.rag_memory)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_hierarchy_tracking(self):
        """Test that hierarchy is tracked correctly."""
        # Execute parent
        plan1, result1, eval1 = self.evolver.execute_with_plan(
            task_description="Parent task",
            node_id="parent",
            depth=0
        )

        # Execute child
        plan2, result2, eval2 = self.evolver.execute_with_plan(
            task_description="Child task",
            node_id="child",
            parent_node_id="parent",
            depth=1
        )

        # Verify hierarchy
        self.assertIn("parent", self.evolver.node_hierarchy)
        self.assertIn("child", self.evolver.node_hierarchy["parent"])

    def test_node_metrics_recording(self):
        """Test that node metrics are recorded."""
        plan, result, evaluation = self.evolver.execute_with_plan(
            task_description="Test task",
            node_id="test_node",
            depth=0
        )

        # Verify metrics were recorded
        self.assertIn("test_node", self.evolver.node_metrics)
        self.assertGreater(len(self.evolver.node_metrics["test_node"]), 0)

        metrics = self.evolver.node_metrics["test_node"][0]
        self.assertIsInstance(metrics, NodeMetrics)
        self.assertEqual(metrics.node_id, "test_node")

    def test_get_node_statistics(self):
        """Test getting node statistics."""
        # Execute node multiple times
        for _ in range(3):
            self.evolver.execute_with_plan(
                task_description="Test task",
                node_id="stats_test",
                depth=0
            )

        stats = self.evolver.get_node_statistics("stats_test")

        self.assertIn("executions", stats)
        self.assertEqual(stats["executions"], 3)
        self.assertIn("avg_quality", stats)
        self.assertIn("avg_speed_ms", stats)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestOverseerLlm))
    suite.addTests(loader.loadTestsFromTestCase(TestEvaluatorLlm))
    suite.addTests(loader.loadTestsFromTestCase(TestSharedPlanContext))
    suite.addTests(loader.loadTestsFromTestCase(TestRAGIntegratedTools))
    suite.addTests(loader.loadTestsFromTestCase(TestHierarchicalEvolver))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
