#!/usr/bin/env python3
"""
Example: Generate and test a text compression node using RLE (Run-Length Encoding).

This example demonstrates the full workflow:
1. Generate code from a prompt using codellama
2. Execute the code with test inputs
3. Evaluate performance using llama3 and tiny
4. Store results in the registry
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import OllamaClient, Registry, NodeRunner, Evaluator


def main():
    print("="*80)
    print("Text Compressor Example - Code Evolution System")
    print("="*80)

    # Initialize components
    print("\n1. Initializing components...")
    client = OllamaClient()
    registry = Registry("./registry")
    runner = NodeRunner("./nodes")
    evaluator = Evaluator(client)

    # Check Ollama connection
    print("\n2. Checking Ollama connection...")
    if not client.check_connection():
        print("ERROR: Cannot connect to Ollama. Please ensure:")
        print("  1. Ollama is installed")
        print("  2. Ollama server is running (ollama serve)")
        return 1

    # Check required models
    models = client.list_models()
    required = ["codellama", "llama3"]
    missing = [m for m in required if m not in models]

    if missing:
        print(f"WARNING: Missing models: {', '.join(missing)}")
        print("Install with:")
        for model in missing:
            print(f"  ollama pull {model}")
        print("\nContinuing anyway (may fail)...")

    # Define the node
    node_id = "compress_text_v1"
    title = "Text compressor using RLE (Run-Length Encoding)"

    print(f"\n3. Creating node '{node_id}'...")

    # Create node in registry
    node_def = registry.create_node(
        node_id=node_id,
        title=title,
        version="1.0.0",
        node_type="processor",
        tags=["compression", "text", "rle", "baseline"],
        goals={
            "primary": ["correctness", "determinism"],
            "secondary": ["latency<200ms", "memory<64MB"]
        },
        inputs={"text": "string"},
        outputs={"compressed": "bytes", "ratio": "float"},
        constraints={
            "timeout_ms": 5000,
            "max_memory_mb": 256
        }
    )

    # Generate code prompt
    print("\n4. Generating code with codellama...")
    prompt = """Write a Python module with:
- def compress(text: str) -> bytes: Compress text using Run-Length Encoding (RLE)
- def decompress(data: bytes) -> str: Decompress RLE-encoded data back to text

Constraints:
- Pure Python, no external dependencies
- Deterministic output
- Handle ASCII text only
- Performance: target latency <200ms on 100KB text; memory <64MB

Include __main__ section that:
1. Reads JSON from stdin with format: {"text": "..."}
2. Compresses the text
3. Decompresses it back
4. Verifies round-trip (original == decompressed)
5. Prints JSON result with format:
   {
     "original_len": <int>,
     "compressed_len": <int>,
     "ratio": <float>,
     "roundtrip_ok": <bool>
   }

Return only code, no explanations."""

    code = client.generate_code(prompt)

    if not code or len(code) < 50:
        print("ERROR: Failed to generate code")
        return 1

    print(f"✓ Generated {len(code)} characters of code")

    # Save the code
    print("\n5. Saving code...")
    code_path = runner.save_code(node_id, code)
    print(f"✓ Code saved to: {code_path}")

    # Test with sample inputs
    print("\n6. Testing with sample inputs...")

    test_cases = [
        {"text": "AAAABBBCCDAA"},
        {"text": "AAAAAA"},
        {"text": "ABCDEFG"},
        {"text": "A" * 100}
    ]

    all_passed = True

    for i, test_input in enumerate(test_cases, 1):
        print(f"\n   Test case {i}: {test_input['text'][:30]}...")

        # Run the node
        stdout, stderr, metrics = runner.run_node(
            node_id=node_id,
            input_payload=test_input,
            timeout_ms=node_def["constraints"]["timeout_ms"]
        )

        # Save metrics
        registry.save_metrics(node_id, metrics)

        # Print results
        if metrics["success"]:
            print(f"   ✓ Success: {metrics['latency_ms']}ms, {metrics['memory_mb_peak']:.2f}MB")
            if stdout:
                print(f"   Output: {stdout[:100]}")
        else:
            print(f"   ✗ Failed: exit_code={metrics['exit_code']}")
            if stderr:
                print(f"   Error: {stderr[:200]}")
            all_passed = False

    # Evaluate the last run
    print("\n7. Evaluating performance...")

    result = evaluator.evaluate_full(
        stdout=stdout,
        stderr=stderr,
        metrics=metrics,
        code_summary=f"Text compressor using RLE. Last test: {test_input}",
        goals=node_def["goals"],
        targets={
            "latency_ms": 200,
            "memory_mb": 64,
            "exit_code": 0
        }
    )

    # Save evaluation
    eval_data = {
        "score_overall": result["final_score"],
        "verdict": result["final_verdict"],
        "triage": result.get("triage"),
        "evaluation": result.get("evaluation")
    }
    registry.save_evaluation(node_id, eval_data)

    # Update index
    registry.update_index(
        node_id=node_id,
        version=node_def["version"],
        tags=node_def["tags"],
        score_overall=result["final_score"]
    )

    # Print evaluation results
    print(f"\n{'='*80}")
    print("EVALUATION RESULTS")
    print(f"{'='*80}")
    print(f"Overall Score: {result['final_score']:.2f}")
    print(f"Verdict: {result['final_verdict']}")

    if result.get("evaluation"):
        eval_data = result["evaluation"]
        if "scores" in eval_data:
            print(f"\nDetailed Scores:")
            for key, value in eval_data["scores"].items():
                print(f"  {key.capitalize()}: {value:.2f}")

        if "notes" in eval_data:
            print(f"\nNotes:\n{eval_data['notes'][:300]}")

    # Print registry location
    print(f"\n{'='*80}")
    print("Registry saved to:")
    print(f"  Node definition: {registry.get_node_dir(node_id) / 'node.json'}")
    print(f"  Metrics: {registry.get_node_dir(node_id) / 'metrics.json'}")
    print(f"  Evaluation: {registry.get_node_dir(node_id) / 'evaluation.json'}")
    print(f"  Code: {code_path}")
    print(f"{'='*80}")

    return 0 if all_passed and result["final_verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
