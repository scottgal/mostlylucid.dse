"""
Example: Quality Dimension Testing with Test Tool Generator

Demonstrates:
1. Using TestToolGenerator to create custom test tools
2. Integrating quality testing with performance benchmarking
3. Testing any quality dimension (accuracy, reliability, etc.)
4. LLM-generated test tools for custom quality metrics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Mock LLM client for demonstration
class MockLLMClient:
    """Mock LLM client for example"""
    def generate(self, model, prompt, temperature=0.7, model_key=None):
        # Return a simple generated test function
        return """
def test_accuracy(input_data: dict, output_data: dict, criteria: dict = None) -> float:
    \"\"\"Test accuracy dimension\"\"\"
    expected = input_data.get('expected')
    actual = output_data.get('result')

    if expected is None or actual is None:
        return 0.0

    return 1.0 if expected == actual else 0.0
"""


def example_1_generate_test_tool():
    """Example 1: Generate a test tool for a custom quality dimension"""
    print("\n" + "="*60)
    print("Example 1: Generate Test Tool for Custom Dimension")
    print("="*60)

    from test_tool_generator import TestToolGenerator, TestToolSpec

    generator = TestToolGenerator(MockLLMClient(), model="codellama")

    # Define what we want to test
    spec = TestToolSpec(
        dimension="api_correctness",
        description="HTTP API that fetches user data",
        input_type="str (user_id)",
        output_type="dict with 'user_id', 'name', and 'email' keys",
        quality_criteria="Response must contain all required fields",
        examples=[
            {"input": "user123", "expected_fields": ["user_id", "name", "email"]},
            {"input": "user456", "expected_fields": ["user_id", "name", "email"]}
        ]
    )

    # Generate test tool
    print("\n📝 Generating test tool for 'api_correctness' dimension...")
    test_code = generator.generate_test_tool(spec)

    print("\n✅ Generated test tool:")
    print(test_code)

    # Use the generated test tool
    exec(test_code)
    test_func = locals()['test_api_correctness']

    # Test it
    test_input = {"user_id": "user123", "expected_fields": ["user_id", "name", "email"]}
    test_output = {"result": {"user_id": "user123", "name": "John", "email": "john@example.com"}}

    score = test_func(test_input, test_output)
    print(f"\n📊 Test Score: {score:.2f}")


def example_2_complete_test_suite():
    """Example 2: Generate complete test suite for a tool"""
    print("\n" + "="*60)
    print("Example 2: Generate Complete Test Suite")
    print("="*60)

    from test_tool_generator import TestToolGenerator

    generator = TestToolGenerator(MockLLMClient())

    # Generate suite for multiple dimensions
    print("\n📝 Generating test suite for HTTP fetcher tool...")

    suite_code = generator.generate_test_suite(
        tool_name="http_fetcher",
        tool_description="Fetches data from HTTP APIs and returns JSON",
        dimensions=["accuracy", "reliability", "completeness"],
        input_type="str (URL)",
        output_type="dict (JSON response)",
        quality_criteria={
            "accuracy": "Returns valid JSON with correct schema",
            "reliability": "Handles errors and timeouts gracefully",
            "completeness": "Response contains all expected fields"
        }
    )

    print("\n✅ Generated test suite:")
    print(suite_code[:500] + "...\n")

    # Save to file
    output_path = Path("debug_data") / "http_fetcher_test_suite.py"
    output_path.parent.mkdir(exist_ok=True)
    generator.save_test_suite(suite_code, str(output_path))

    print(f"💾 Saved to: {output_path}")


def example_3_quality_and_performance():
    """Example 3: Test both quality AND performance together"""
    print("\n" + "="*60)
    print("Example 3: Combined Quality + Performance Testing")
    print("="*60)

    from test_tool_generator import GeneratedQualityEvaluator, TestToolSpec
    from performance_collector import PerformanceCollector
    import time

    # Setup
    evaluator = GeneratedQualityEvaluator(MockLLMClient())
    collector = PerformanceCollector(session_id="quality_perf_test")

    # Register quality dimensions
    print("\n📝 Registering quality dimensions...")

    spec = TestToolSpec(
        dimension="output_validity",
        description="Validates output format and content",
        input_type="dict",
        output_type="dict",
        quality_criteria="Output must be valid dict with 'status' key"
    )

    evaluator.register_generated_dimension(spec, threshold=0.8)

    # Define tool to test
    @collector.instrument(layer="tool", tool_name="data_processor")
    def process_data(data):
        """Sample data processor"""
        time.sleep(0.05)  # Simulate work
        return {"status": "success", "processed": len(data)}

    # Run tests with quality + performance tracking
    print("\n🔄 Running tests with quality + performance tracking...")

    test_cases = [
        ({"records": [1, 2, 3]}, {"status": "success"}),
        ({"records": [4, 5, 6, 7]}, {"status": "success"}),
        ({"records": []}, {"status": "success"}),
    ]

    for i, (input_data, expected_output) in enumerate(test_cases, 1):
        # Execute with performance tracking
        result = process_data(input_data)

        # Evaluate quality
        output_data = {"result": result}
        quality_scores = evaluator.evaluate_all(
            input_data={"value": input_data, "expected": expected_output},
            output_data=output_data
        )

        print(f"\n   Test {i}:")
        print(f"      Quality Scores: {quality_scores}")
        print(f"      Output: {result}")

    # Get performance report
    collector.store.sync_to_duckdb()
    print("\n📊 Performance Summary:")
    perf_summary = collector.store.get_performance_summary()
    print(perf_summary)

    collector.close()


def example_4_benchmark_with_quality():
    """Example 4: Use benchmark fixture with quality testing"""
    print("\n" + "="*60)
    print("Example 4: Benchmark Fixture with Quality Metrics")
    print("="*60)

    from benchmark_fixture import BenchmarkFixture
    from test_tool_generator import GeneratedQualityEvaluator, TestToolSpec

    fixture = BenchmarkFixture(session_id="quality_benchmark")
    evaluator = GeneratedQualityEvaluator(MockLLMClient())

    # Register quality dimension
    spec = TestToolSpec(
        dimension="correctness",
        description="Checks if output is correct",
        input_type="int",
        output_type="int",
        quality_criteria="Output must equal input * 2"
    )

    evaluator.register_generated_dimension(spec, threshold=1.0)

    # Define implementations to compare
    def multiply_v1(x):
        """Version 1: Simple multiplication"""
        return x * 2

    def multiply_v2(x):
        """Version 2: Addition loop"""
        result = 0
        for _ in range(2):
            result += x
        return result

    # Create scenarios
    scenarios = fixture.create_standard_scenarios("numeric_computation")

    # Benchmark performance
    print("\n🏁 Benchmarking implementations...")

    perf_results = fixture.benchmark(
        implementations={"v1": multiply_v1, "v2": multiply_v2},
        scenarios=[scenarios[0]],  # Use first scenario
        layer="function"
    )

    # Test quality
    print("\n📊 Testing quality...")

    for impl_name, impl_func in [("v1", multiply_v1), ("v2", multiply_v2)]:
        test_input = {"value": 5, "expected": 10}
        test_output = {"result": impl_func(5)}

        quality_score = evaluator.evaluate("correctness", test_input, test_output)

        print(f"\n   {impl_name}:")
        print(f"      Quality: {quality_score:.2f}")
        if perf_results:
            scenario_results = list(perf_results.values())[0]
            impl_result = next(r for r in scenario_results if r.implementation_name == impl_name)
            print(f"      Avg Duration: {impl_result.avg_duration_ms:.2f}ms")

    # Generate comparison report
    report = fixture.generate_comparison_report(perf_results)
    print("\n📄 Performance Report Preview:")
    print(report[:400] + "...\n")

    fixture.close()


def example_5_meta_testing():
    """Example 5: Meta-testing - test the test tool generator itself!"""
    print("\n" + "="*60)
    print("Example 5: Meta-Testing the Test Tool Generator")
    print("="*60)

    from test_tool_generator import TestToolGenerator, TestToolSpec

    generator = TestToolGenerator(MockLLMClient())

    # Generate a test tool
    spec = TestToolSpec(
        dimension="test_tool_quality",
        description="Tests if generated test tools work correctly",
        input_type="str (test function code)",
        output_type="bool (test passed)",
        quality_criteria="Test tool must correctly identify good and bad outputs"
    )

    print("\n🧪 Generating test tool for testing test tools (meta!)...")

    test_code = generator.generate_test_tool(spec)

    print(f"\n✅ Generated {len(test_code)} characters of test code")

    # Validate the generated code
    try:
        compile(test_code, '<string>', 'exec')
        print("✅ Generated code compiles successfully")

        # Execute it
        exec(test_code)
        print("✅ Generated code executes successfully")

        # Try to use it
        test_func = locals()['test_test_tool_quality']
        score = test_func(
            {"value": "test code"},
            {"result": True}
        )
        print(f"✅ Generated test tool returns score: {score}")

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("🧪 Quality Dimension Testing Examples")
    print("="*60)

    examples = [
        example_1_generate_test_tool,
        example_2_complete_test_suite,
        example_3_quality_and_performance,
        example_4_benchmark_with_quality,
        example_5_meta_testing
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n❌ Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("✅ All examples completed!")
    print("="*60)

    print("\n💡 Key Takeaways:")
    print("   1. Test tools can be generated for ANY quality dimension")
    print("   2. LLMs (like CodeLlama) generate the test code automatically")
    print("   3. Quality testing integrates with performance benchmarking")
    print("   4. Test tool generator is itself a meta-testing tool")
    print("   5. Quality + performance gives complete optimization picture")


if __name__ == "__main__":
    main()
