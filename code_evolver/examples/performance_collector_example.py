"""
Example: Using Performance Collector for System-Wide Optimization

This demonstrates using the PerformanceCollector to track performance
across all layers of the system for optimization purposes.

Shows:
1. Instrumenting tools at different layers
2. Collecting entry/exit data and performance metrics
3. Generating optimization reports
4. Identifying bottlenecks
"""

import time
import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from performance_collector import PerformanceCollector


def example_1_basic_instrumentation():
    """Example 1: Basic tool instrumentation"""
    print("\n" + "="*60)
    print("Example 1: Basic Tool Instrumentation")
    print("="*60)

    collector = PerformanceCollector(session_id="perf_basic")

    # Instrument a tool function
    @collector.instrument(layer="tool", tool_name="data_fetcher")
    def fetch_data(url: str, timeout: int = 30):
        """Simulate data fetching"""
        time.sleep(random.uniform(0.05, 0.15))
        return {"data": [1, 2, 3], "status": 200}

    # Instrument another tool
    @collector.instrument(layer="tool", tool_name="data_processor")
    def process_data(data: dict):
        """Simulate data processing"""
        time.sleep(random.uniform(0.02, 0.08))
        return {"processed": len(data.get("data", [])), "success": True}

    print("\n🔄 Executing instrumented tools...")

    # Execute tools - performance is tracked automatically
    for i in range(10):
        raw_data = fetch_data(f"https://api.example.com/data/{i}")
        result = process_data(raw_data)
        print(f"   Processed request {i+1}: {result['processed']} items")

    # Generate report
    print("\n📊 Generating performance report...")
    report = collector.generate_optimization_report(min_executions=1)

    print("\n" + "="*60)
    print("PERFORMANCE REPORT PREVIEW")
    print("="*60)
    print(report[:800] + "...\n")

    collector.close()


def example_2_layered_instrumentation():
    """Example 2: Multi-layer instrumentation"""
    print("\n" + "="*60)
    print("Example 2: Multi-Layer System Instrumentation")
    print("="*60)

    collector = PerformanceCollector(
        session_id="perf_multilayer",
        enable_io_tracking=True,
        enable_memory_profiling=True
    )

    # Layer 1: Node level
    @collector.instrument(layer="node", tool_name="llm_node")
    def llm_call(prompt: str, model: str):
        """Simulate LLM call"""
        time.sleep(random.uniform(0.1, 0.3))
        return f"Response to: {prompt[:20]}..."

    # Layer 2: Tool level
    @collector.instrument(layer="tool", tool_name="workflow_executor")
    def execute_workflow(workflow_id: str, steps: list):
        """Simulate workflow execution"""
        results = []
        for step in steps:
            time.sleep(random.uniform(0.01, 0.05))
            if step == "llm_call":
                result = llm_call(f"Process step {step}", "gpt-4")
            else:
                result = f"Executed {step}"
            results.append(result)
        return results

    # Layer 3: Function level
    @collector.instrument(layer="function", tool_name="validation")
    def validate_input(data: dict):
        """Input validation"""
        time.sleep(0.005)
        return "schema" in data and "content" in data

    print("\n🔄 Executing multi-layer workflow...")

    # Execute workflow with multiple layers
    for i in range(5):
        # Validate input (function layer)
        is_valid = validate_input({"schema": "v1", "content": f"data_{i}"})

        if is_valid:
            # Execute workflow (tool layer, which calls node layer)
            results = execute_workflow(
                f"workflow_{i}",
                ["fetch", "llm_call", "process", "llm_call", "save"]
            )
            print(f"   Workflow {i+1}: {len(results)} steps completed")

    # Generate comprehensive report
    print("\n📊 Generating multi-layer performance report...")
    report = collector.generate_optimization_report(
        output_path="debug_data/multilayer_performance.md",
        min_executions=1
    )

    print("\n✅ Report saved to: debug_data/multilayer_performance.md")

    # Show layer breakdown
    print("\n📈 Performance by Layer:")
    print(report[report.find("## Performance by Layer"):report.find("## Top Time-Consuming Tools")])

    collector.close()


def example_3_context_manager_tracking():
    """Example 3: Manual tracking with context manager"""
    print("\n" + "="*60)
    print("Example 3: Manual Tracking with Context Manager")
    print("="*60)

    collector = PerformanceCollector(session_id="perf_manual")

    print("\n🔄 Tracking custom operations...")

    # Track a complex operation with custom entry/exit data
    for i in range(5):
        with collector.track_execution("tool", "image_processor") as tracker:
            # Set entry data
            tracker.set_entry({
                "image_path": f"/images/photo_{i}.jpg",
                "filters": ["resize", "sharpen", "compress"],
                "target_size": (800, 600)
            })

            # Simulate processing
            time.sleep(random.uniform(0.1, 0.3))

            # Simulate memory-intensive operation
            _ = [0] * (1024 * 1024)  # Allocate some memory

            # Set exit data
            tracker.set_exit({
                "output_path": f"/processed/photo_{i}.jpg",
                "original_size_kb": random.randint(1000, 5000),
                "compressed_size_kb": random.randint(300, 1500),
                "processing_time_ms": random.uniform(100, 300)
            })

        print(f"   Processed image {i+1}")

    # Generate report
    report = collector.generate_optimization_report(min_executions=1)

    print("\n📊 Top Time-Consuming Tools:")
    start = report.find("## Top Time-Consuming Tools")
    end = report.find("## Memory Hotspots")
    print(report[start:end])

    collector.close()


def example_4_error_tracking():
    """Example 4: Tracking errors and failures"""
    print("\n" + "="*60)
    print("Example 4: Error Tracking and Analysis")
    print("="*60)

    collector = PerformanceCollector(session_id="perf_errors")

    @collector.instrument(layer="tool", tool_name="unreliable_api")
    def call_unreliable_api(endpoint: str):
        """Simulate unreliable API"""
        time.sleep(random.uniform(0.05, 0.15))

        # Fail randomly
        if random.random() < 0.3:
            raise ConnectionError(f"Failed to connect to {endpoint}")

        return {"status": "success", "data": [1, 2, 3]}

    print("\n🔄 Executing unreliable operations...")

    success_count = 0
    error_count = 0

    for i in range(20):
        try:
            result = call_unreliable_api(f"/api/endpoint_{i}")
            success_count += 1
            print(f"   ✅ Request {i+1}: Success")
        except ConnectionError as e:
            error_count += 1
            print(f"   ❌ Request {i+1}: Error")

    print(f"\n📊 Results: {success_count} succeeded, {error_count} failed")

    # Generate report with error analysis
    report = collector.generate_optimization_report(min_executions=1)

    if "## Error-Prone Tools" in report:
        print("\n⚠️  Error Analysis:")
        start = report.find("## Error-Prone Tools")
        end = report.find("## Optimization Recommendations")
        print(report[start:end])

    collector.close()


def example_5_real_world_pipeline():
    """Example 5: Real-world data pipeline simulation"""
    print("\n" + "="*60)
    print("Example 5: Real-World Data Pipeline")
    print("="*60)

    collector = PerformanceCollector(
        session_id="perf_pipeline",
        enable_io_tracking=True,
        enable_memory_profiling=True
    )

    # Define pipeline stages
    @collector.instrument(layer="step", tool_name="extract")
    def extract_data(source: str):
        """Extract data from source"""
        time.sleep(random.uniform(0.05, 0.15))
        return {"records": list(range(100)), "source": source}

    @collector.instrument(layer="step", tool_name="transform")
    def transform_data(data: dict):
        """Transform extracted data"""
        time.sleep(random.uniform(0.08, 0.12))
        records = data.get("records", [])
        return {"records": [r * 2 for r in records], "count": len(records)}

    @collector.instrument(layer="step", tool_name="validate")
    def validate_data(data: dict):
        """Validate transformed data"""
        time.sleep(random.uniform(0.02, 0.05))
        return {"valid": True, "count": data.get("count", 0)}

    @collector.instrument(layer="step", tool_name="load")
    def load_data(data: dict):
        """Load data to destination"""
        time.sleep(random.uniform(0.1, 0.2))
        return {"loaded": data.get("count", 0), "status": "success"}

    @collector.instrument(layer="workflow", tool_name="etl_pipeline")
    def run_etl_pipeline(pipeline_id: str, source: str):
        """Run complete ETL pipeline"""
        # Extract
        raw_data = extract_data(source)

        # Transform
        transformed = transform_data(raw_data)

        # Validate
        validated = validate_data(transformed)

        # Load
        result = load_data(transformed)

        return result

    print("\n🔄 Running ETL pipelines...")

    # Run multiple pipeline executions
    sources = ["database", "api", "file", "stream"]
    for i in range(10):
        source = sources[i % len(sources)]
        result = run_etl_pipeline(f"pipeline_{i}", source)
        print(f"   Pipeline {i+1} ({source}): Loaded {result['loaded']} records")

    # Generate comprehensive report
    print("\n📊 Generating comprehensive pipeline report...")
    report = collector.generate_optimization_report(
        output_path="debug_data/pipeline_performance.md",
        min_executions=1,
        max_tokens=100000
    )

    print("\n✅ Full report saved to: debug_data/pipeline_performance.md")

    # Show key metrics
    print("\n📈 Key Performance Metrics:")
    print(report[report.find("## Overall System Performance"):report.find("## Performance by Layer")])

    print("\n🎯 Optimization Recommendations:")
    start = report.find("## Optimization Recommendations")
    end = report.find("## Detailed Layer Analysis") if "## Detailed Layer Analysis" in report else len(report)
    print(report[start:end][:500] + "...")

    collector.close()


def example_6_code_variant_comparison():
    """Example 6: Comparing code variants for optimization"""
    print("\n" + "="*60)
    print("Example 6: Code Variant Comparison")
    print("="*60)

    collector = PerformanceCollector(session_id="perf_variants")

    # Variant 1: Simple loop
    def sum_variant_1(numbers: list):
        """Sum using loop"""
        total = 0
        for num in numbers:
            total += num
        return total

    # Variant 2: Built-in sum
    def sum_variant_2(numbers: list):
        """Sum using built-in"""
        return sum(numbers)

    # Variant 3: NumPy (simulated)
    def sum_variant_3(numbers: list):
        """Sum using numpy-like approach"""
        # Simulate numpy overhead
        time.sleep(0.001)
        return sum(numbers)

    # Instrument variants
    v1 = collector.instrument(layer="function", tool_name="sum_v1", track_code_changes=True)(sum_variant_1)
    v2 = collector.instrument(layer="function", tool_name="sum_v2", track_code_changes=True)(sum_variant_2)
    v3 = collector.instrument(layer="function", tool_name="sum_v3", track_code_changes=True)(sum_variant_3)

    print("\n🔄 Testing code variants...")

    # Test each variant
    numbers = list(range(1000))

    print("   Testing variant 1 (loop)...")
    for _ in range(20):
        v1(numbers)

    print("   Testing variant 2 (built-in)...")
    for _ in range(20):
        v2(numbers)

    print("   Testing variant 3 (numpy-like)...")
    for _ in range(20):
        v3(numbers)

    # Generate comparison report
    print("\n📊 Generating variant comparison report...")
    report = collector.generate_optimization_report(min_executions=1)

    print("\n🏆 Variant Performance Comparison:")
    print(report[report.find("## Top Time-Consuming Tools"):report.find("## Memory Hotspots")])

    collector.close()


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("🚀 Performance Collector Examples")
    print("="*60)

    examples = [
        example_1_basic_instrumentation,
        example_2_layered_instrumentation,
        example_3_context_manager_tracking,
        example_4_error_tracking,
        example_5_real_world_pipeline,
        example_6_code_variant_comparison
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n❌ Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("✅ All performance collection examples completed!")
    print("="*60)
    print("\n💡 Next steps:")
    print("   1. Review generated reports in debug_data/")
    print("   2. Identify optimization candidates")
    print("   3. Instrument your own code at all layers")
    print("   4. Use reports to guide optimization efforts")
    print("   5. Compare code variants to find fastest implementation")


if __name__ == "__main__":
    main()
