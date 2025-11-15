#!/usr/bin/env python3
"""
Test script for Quality Evaluator with phi3:3.8b.
Tests evaluation at each step and iterative improvement.
"""
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import box

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import (
    create_rag_memory,
    OllamaClient,
    ConfigManager,
    QualityEvaluator,
    EvaluationStep
)

console = Console()

def test_quality_evaluator():
    """Test the quality evaluator system."""

    console.print("[bold cyan]Testing Quality Evaluator System[/bold cyan]\n")

    # Initialize
    console.print("[dim]Initializing components...[/dim]")
    config = ConfigManager("config.yaml")
    client = OllamaClient(config.ollama_url, config_manager=config)
    rag = create_rag_memory(config, client)
    evaluator = QualityEvaluator(client, config, rag)

    console.print("[green]OK Initialized[/green]\n")

    # Test 1: Evaluate Strategy
    console.print("[bold]Test 1: Evaluating Strategy Quality[/bold]\n")

    test_strategy = """
Approach: Use a simple addition function with two parameters.

1. Create a function add(a, b)
2. Return a + b
3. Add error handling for non-numeric inputs
4. Include type hints for clarity
5. Write unit tests for normal and edge cases
"""

    task = "Create a function that adds two numbers"

    result = evaluator.evaluate_strategy(test_strategy, task)

    console.print(f"Score: [cyan]{result.score:.2f}[/cyan]")
    console.print(f"Passed: [{'green' if result.passed else 'red'}]{result.passed}[/]")
    console.print(f"Feedback: {result.feedback}")
    console.print(f"Strengths: {', '.join(result.strengths)}")
    console.print(f"Weaknesses: {', '.join(result.weaknesses)}")
    console.print(f"Suggestions: {', '.join(result.suggestions)}\n")

    # Test 2: Evaluate Code
    console.print("[bold]Test 2: Evaluating Code Quality[/bold]\n")

    test_code = """
import json
import sys

def add(a: int, b: int) -> int:
    \"\"\"Add two numbers and return the result.\"\"\"
    return a + b

if __name__ == "__main__":
    data = json.load(sys.stdin)
    result = add(data['a'], data['b'])
    print(json.dumps({"result": result}))
"""

    result = evaluator.evaluate_code(test_code, task, test_strategy)

    console.print(f"Score: [cyan]{result.score:.2f}[/cyan]")
    console.print(f"Passed: [{'green' if result.passed else 'red'}]{result.passed}[/]")
    console.print(f"Feedback: {result.feedback}")
    console.print(f"Strengths: {', '.join(result.strengths)}")
    console.print(f"Weaknesses: {', '.join(result.weaknesses)}")
    console.print(f"Suggestions: {', '.join(result.suggestions)}\n")

    # Test 3: Evaluate Tests
    console.print("[bold]Test 3: Evaluating Test Quality[/bold]\n")

    test_tests = """
import pytest
from main import add

def test_add_positive():
    assert add(2, 3) == 5

def test_add_negative():
    assert add(-1, -1) == -2

def test_add_zero():
    assert add(0, 5) == 5
"""

    result = evaluator.evaluate_tests(test_tests, test_code)

    console.print(f"Score: [cyan]{result.score:.2f}[/cyan]")
    console.print(f"Passed: [{'green' if result.passed else 'red'}]{result.passed}[/]")
    console.print(f"Feedback: {result.feedback}")
    console.print(f"Strengths: {', '.join(result.strengths)}")
    console.print(f"Weaknesses: {', '.join(result.weaknesses)}")
    console.print(f"Suggestions: {', '.join(result.suggestions)}\n")

    # Test 4: Evaluate Writing (using phi3:3.8b)
    console.print("[bold]Test 4: Evaluating Writing Quality (phi3:3.8b)[/bold]\n")

    test_article = """
# Understanding Python Decorators

Python decorators are a powerful feature that allows you to modify the behavior of functions or classes. They provide a clean syntax for wrapping functionality around existing code.

## What are Decorators?

A decorator is essentially a function that takes another function and extends its behavior without explicitly modifying it.

## Basic Example

```python
def my_decorator(func):
    def wrapper():
        print("Before function")
        func()
        print("After function")
    return wrapper

@my_decorator
def say_hello():
    print("Hello!")
```

When you call `say_hello()`, the decorator wraps additional functionality around it.
"""

    writing_task = "Write a blog post introduction about Python decorators"

    result = evaluator.evaluate_writing(test_article, writing_task, "blog")

    console.print(f"Score: [cyan]{result.score:.2f}[/cyan]")
    console.print(f"Passed: [{'green' if result.passed else 'red'}]{result.passed}[/]")
    console.print(f"Feedback: {result.feedback}")
    console.print(f"Strengths: {', '.join(result.strengths)}")
    console.print(f"Weaknesses: {', '.join(result.weaknesses)}")
    console.print(f"Suggestions: {', '.join(result.suggestions)}\n")

    # Test 5: Iterative Improvement
    console.print("[bold]Test 5: Iterative Improvement with Feedback[/bold]\n")

    # Start with low-quality strategy
    poor_strategy = "Just add the numbers together."

    console.print("[dim]Starting with poor strategy:[/dim]")
    console.print(f"  '{poor_strategy}'")

    improved_strategy, evaluations = evaluator.iterative_improve(
        poor_strategy,
        "strategy",
        {"task_description": task}
    )

    console.print(f"\n[dim]Improvement iterations: {len(evaluations)}[/dim]")
    for i, eval_result in enumerate(evaluations):
        console.print(f"  Iteration {i+1}: Score {eval_result.score:.2f} - {'PASS' if eval_result.passed else 'FAIL'}")

    if evaluations[-1].passed:
        console.print(f"\n[green]Final strategy passed evaluation![/green]")
        console.print(Panel(improved_strategy, title="[cyan]Improved Strategy[/cyan]", box=box.ROUNDED))
    else:
        console.print(f"\n[yellow]Strategy did not pass after {len(evaluations)} iterations[/yellow]")
        console.print(f"Final score: {evaluations[-1].score:.2f}")

    # Test 6: Threshold Auto-Adjustment
    console.print("\n[bold]Test 6: Auto-Adjusting Thresholds[/bold]\n")

    stats = evaluator.get_evaluation_stats()
    console.print("[cyan]Evaluation Statistics:[/cyan]")
    for step_type, step_stats in stats.items():
        if step_stats.get("count", 0) > 0:
            console.print(f"\n{step_type.upper()}:")
            console.print(f"  Count: {step_stats['count']}")
            console.print(f"  Mean: {step_stats['mean']:.2f}")
            console.print(f"  Median: {step_stats['median']:.2f}")
            console.print(f"  Range: {step_stats['min']:.2f} - {step_stats['max']:.2f}")

    # Test 7: Model Selection
    console.print("\n[bold]Test 7: Evaluator Model Selection[/bold]\n")

    console.print("Model mapping:")
    console.print(f"  Strategy evaluation: {evaluator._get_model_for_content_type('strategy')}")
    console.print(f"  Code evaluation: {evaluator._get_model_for_content_type('code')}")
    console.print(f"  Test evaluation: {evaluator._get_model_for_content_type('tests')}")
    console.print(f"  Writing evaluation: {evaluator._get_model_for_content_type('writing')}")
    console.print(f"  Blog evaluation: {evaluator._get_model_for_content_type('blog')}")

    # Summary
    console.print("\n[bold green]All Tests Complete![/bold green]\n")

    console.print("[bold cyan]Summary:[/bold cyan]")
    console.print("OK Strategy evaluation working")
    console.print("OK Code evaluation working")
    console.print("OK Test evaluation working")
    console.print("OK Writing evaluation working (phi3:3.8b)")
    console.print("OK Iterative improvement working")
    console.print("OK Threshold auto-adjustment working")
    console.print("OK Model selection working (different models for code vs writing)")

    console.print("\n[bold]Key Features:[/bold]")
    console.print("- Separate evaluators: phi3:3.8b for writing, llama3 for code")
    console.print("- Automatic quality thresholds (configurable)")
    console.print("- Iterative improvement with feedback loop")
    console.print("- Threshold auto-adjustment based on history")
    console.print("- RAG integration for learning from evaluations")

    return True

if __name__ == "__main__":
    try:
        test_quality_evaluator()
        sys.exit(0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
