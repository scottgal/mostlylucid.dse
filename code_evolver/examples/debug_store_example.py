"""
Example: Using the Hybrid Debug Store for Request/Response Recording

This example demonstrates:
1. Basic debug recording
2. Workflow tracking integration
3. Code variant comparison
4. Analysis and LLM output generation
5. Optimization recommendations
"""

import time
import random
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from debug_store import DebugStore, DebugContext
from debug_analyzer import DebugAnalyzer
from debug_integration import DebugIntegration, init_debug_integration, debug_track
from workflow_tracker import WorkflowTracker, WorkflowStep


def example_1_basic_recording():
    """Example 1: Basic debug recording"""
    print("\n" + "="*60)
    print("Example 1: Basic Debug Recording")
    print("="*60)

    # Create a debug store
    with DebugStore(session_id="example_basic", base_path="debug_data") as store:

        # Record a simple operation
        record_id = store.write_record(
            context_type="tool",
            context_id="data_processor",
            context_name="Data Processor",
            request_data={"input": "hello world", "mode": "uppercase"},
            response_data={"output": "HELLO WORLD", "length": 11},
            duration_ms=45.2,
            memory_mb=5.3,
            cpu_percent=12.5,
            status="success"
        )

        print(f"✅ Recorded operation: {record_id}")

        # Record an error
        error_id = store.write_record(
            context_type="tool",
            context_id="data_processor",
            context_name="Data Processor",
            request_data={"input": None, "mode": "uppercase"},
            response_data={},
            duration_ms=1.2,
            status="error",
            error="TypeError: Cannot process None"
        )

        print(f"❌ Recorded error: {error_id}")

        # Sync to analytics layer
        synced = store.sync_to_duckdb()
        print(f"📊 Synced {synced} records to DuckDB")

        # Get stats
        stats = store.get_stats()
        print(f"\n📈 Store Stats:")
        print(f"   - Total records: {stats['duckdb_entries']}")
        print(f"   - LMDB size: {stats['lmdb_size_mb']:.2f} MB")
        print(f"   - DuckDB size: {stats['duckdb_size_mb']:.2f} MB")


def example_2_context_manager():
    """Example 2: Using context manager for automatic tracking"""
    print("\n" + "="*60)
    print("Example 2: Context Manager for Automatic Tracking")
    print("="*60)

    with DebugStore(session_id="example_context", base_path="debug_data") as store:

        # Success case
        with DebugContext(
            store,
            context_type="tool",
            context_id="api_fetch",
            context_name="API Data Fetch"
        ) as ctx:
            ctx.set_request({"url": "https://api.example.com/data", "timeout": 30})

            # Simulate API call
            time.sleep(0.1)
            result = {"status": 200, "data": {"count": 42}}

            ctx.set_response(result)

        print("✅ Tracked successful API call")

        # Error case
        try:
            with DebugContext(
                store,
                context_type="tool",
                context_id="api_fetch",
                context_name="API Data Fetch"
            ) as ctx:
                ctx.set_request({"url": "https://bad-url", "timeout": 30})
                raise ConnectionError("Failed to connect")
        except ConnectionError:
            print("❌ Tracked failed API call")

        store.sync_to_duckdb()
        summary = store.get_performance_summary()
        print(f"\n📊 Performance Summary:\n{summary}")


def example_3_code_variants():
    """Example 3: Tracking code variants for comparison"""
    print("\n" + "="*60)
    print("Example 3: Code Variant Tracking and Comparison")
    print("="*60)

    with DebugStore(session_id="example_variants", base_path="debug_data") as store:

        # Variant 1: Simple implementation
        code_v1 = """
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total
        """.strip()

        # Variant 2: Built-in sum
        code_v2 = """
def calculate_sum(numbers):
    return sum(numbers)
        """.strip()

        # Simulate multiple executions of variant 1
        print("\n🔬 Testing Variant 1 (loop-based)...")
        for i in range(20):
            numbers = list(range(1000))
            start = time.time()
            # Simulate variant 1 execution
            total = sum(range(len(numbers)))  # Dummy work
            duration = (time.time() - start) * 1000

            store.write_record(
                context_type="function",
                context_id="calculate_sum",
                context_name="calculate_sum",
                request_data={"numbers_length": len(numbers)},
                response_data={"result": total},
                duration_ms=duration + random.uniform(10, 20),  # Slightly slower
                status="success",
                code_snapshot=code_v1,
                code_hash="v1_hash",
                variant_id="variant_1"
            )

        # Simulate multiple executions of variant 2
        print("🔬 Testing Variant 2 (built-in sum)...")
        for i in range(20):
            numbers = list(range(1000))
            start = time.time()
            # Simulate variant 2 execution (faster)
            total = sum(range(len(numbers)))
            duration = (time.time() - start) * 1000

            store.write_record(
                context_type="function",
                context_id="calculate_sum",
                context_name="calculate_sum",
                request_data={"numbers_length": len(numbers)},
                response_data={"result": total},
                duration_ms=duration + random.uniform(1, 5),  # Faster
                status="success",
                code_snapshot=code_v2,
                code_hash="v2_hash",
                variant_id="variant_2"
            )

        store.sync_to_duckdb()

        # Analyze variants
        analyzer = DebugAnalyzer(store)
        package = analyzer.analyze_context(
            context_type="function",
            context_id="calculate_sum",
            include_variants=True
        )

        print(f"\n📊 Variant Analysis:")
        for variant in package.code_variants:
            print(f"\n   {variant.description}:")
            print(f"   - Executions: {variant.execution_count}")
            print(f"   - Avg Duration: {variant.avg_duration_ms:.2f}ms")
            print(f"   - Success Rate: {variant.success_rate:.1%}")

        print(f"\n💡 Recommendations:")
        for rec in package.recommendations:
            print(f"   {rec}")


def example_4_workflow_integration():
    """Example 4: Integration with WorkflowTracker"""
    print("\n" + "="*60)
    print("Example 4: Workflow Integration")
    print("="*60)

    integration = DebugIntegration(
        session_id="example_workflow",
        base_path="debug_data"
    )

    # Create a workflow
    tracker = WorkflowTracker(
        workflow_id="data_pipeline",
        description="Multi-step data processing pipeline"
    )

    # Track the entire workflow
    with integration.track_workflow(tracker):
        # Step 1: Fetch data
        step1 = WorkflowStep("step_1", "http_fetch", "Fetch raw data")
        tracker.steps.append(step1)

        with integration.track_step(step1, parent_workflow_id="data_pipeline"):
            step1.start()
            time.sleep(0.05)
            step1.complete("Fetched 100 records")

        print("✅ Step 1: Fetched data")

        # Step 2: Transform data
        step2 = WorkflowStep("step_2", "transformer", "Transform data")
        tracker.steps.append(step2)

        with integration.track_step(step2, parent_workflow_id="data_pipeline"):
            step2.start()
            time.sleep(0.03)
            step2.complete("Transformed 100 records")

        print("✅ Step 2: Transformed data")

        # Step 3: Save data (with error)
        step3 = WorkflowStep("step_3", "database", "Save to database")
        tracker.steps.append(step3)

        try:
            with integration.track_step(step3, parent_workflow_id="data_pipeline"):
                step3.start()
                time.sleep(0.02)
                # Simulate error
                raise IOError("Database connection failed")
        except IOError:
            step3.fail("Database connection failed")
            print("❌ Step 3: Database error")

    # Analyze the workflow
    print("\n📊 Analyzing workflow...")
    markdown = integration.analyze(
        context_type="workflow",
        context_id="data_pipeline",
        max_tokens=5000
    )

    print("\n📄 Analysis Preview:")
    print(markdown[:500] + "...\n")

    # Find optimization candidates
    candidates = integration.get_optimization_candidates()
    if candidates:
        print("🎯 Optimization Candidates:")
        for i, candidate in enumerate(candidates[:3], 1):
            print(f"   {i}. {candidate['context_name']}")
            print(f"      - Avg Duration: {candidate['avg_duration_ms']:.2f}ms")
            print(f"      - Total Time: {candidate['total_duration_ms']:.2f}ms")
            print(f"      - Score: {candidate['optimization_score']:.2f}")

    integration.close()


def example_5_decorator_tracking():
    """Example 5: Using decorators for automatic tracking"""
    print("\n" + "="*60)
    print("Example 5: Decorator-based Tracking")
    print("="*60)

    # Initialize global integration
    init_debug_integration("example_decorator", base_path="debug_data")

    # Define functions with tracking
    @debug_track(context_type="tool")
    def fetch_user_data(user_id: int):
        """Fetch user data from API"""
        time.sleep(0.02)  # Simulate API call
        return {"user_id": user_id, "name": f"User {user_id}", "active": True}

    @debug_track(context_type="tool")
    def process_user_data(user_data: dict):
        """Process user data"""
        time.sleep(0.01)
        return {
            "processed": True,
            "user_name": user_data["name"],
            "status": "active" if user_data["active"] else "inactive"
        }

    # Execute functions - tracking happens automatically
    print("🔄 Executing tracked functions...")
    for user_id in range(1, 6):
        user_data = fetch_user_data(user_id)
        result = process_user_data(user_data)
        print(f"   Processed user {user_id}: {result['status']}")

    # Analyze
    from debug_integration import get_debug_integration
    integration = get_debug_integration()

    integration.store.sync_to_duckdb()
    summary = integration.store.get_performance_summary()

    print(f"\n📊 Function Performance:")
    for _, row in summary.iterrows():
        print(f"   {row['context_name']}: {row['avg_duration']:.2f}ms avg")

    integration.close()


def example_6_llm_export():
    """Example 6: Export for LLM consumption"""
    print("\n" + "="*60)
    print("Example 6: Export for LLM Consumption")
    print("="*60)

    with DebugStore(session_id="example_llm_export", base_path="debug_data") as store:

        # Create sample data
        for i in range(30):
            is_error = i % 10 == 0
            store.write_record(
                context_type="tool",
                context_id="image_processor",
                context_name="Image Processor",
                request_data={
                    "image_path": f"/images/photo_{i}.jpg",
                    "filters": ["resize", "sharpen"]
                },
                response_data={
                    "output_path": f"/processed/photo_{i}.jpg",
                    "size_kb": random.randint(100, 500)
                } if not is_error else {},
                duration_ms=random.uniform(200, 800),
                memory_mb=random.uniform(50, 150),
                status="error" if is_error else "success",
                error="OutOfMemoryError" if is_error else None
            )

        store.sync_to_duckdb()

        # Generate analysis for LLM
        analyzer = DebugAnalyzer(store)
        package = analyzer.analyze_context(
            context_type="tool",
            context_id="image_processor",
            max_samples=5
        )

        # Export as markdown (optimized for LLM context)
        output_path = Path("debug_data") / "image_processor_analysis.md"
        analyzer.export_to_file(
            package,
            str(output_path),
            format="markdown",
            max_tokens=10000  # Fit within typical context window
        )

        print(f"✅ Exported analysis to: {output_path}")
        print(f"   - Total records: {package.metadata['total_records']}")
        print(f"   - Unique variants: {package.metadata['unique_variants']}")

        # Show preview
        print("\n📄 Preview (first 500 chars):")
        markdown = package.to_markdown(max_tokens=10000)
        print(markdown[:500] + "...\n")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("🚀 Debug Store Examples")
    print("="*60)

    examples = [
        example_1_basic_recording,
        example_2_context_manager,
        example_3_code_variants,
        example_4_workflow_integration,
        example_5_decorator_tracking,
        example_6_llm_export
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
    print("\n💡 Next steps:")
    print("   1. Check debug_data/ directory for stored data")
    print("   2. Explore .lmdb and .duckdb files")
    print("   3. Review generated analysis markdown files")
    print("   4. Integrate with your own code using decorators or context managers")


if __name__ == "__main__":
    main()
