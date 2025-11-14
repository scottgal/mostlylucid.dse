#!/usr/bin/env python3
"""
Demo script showing the progress display system.
This demonstrates what users will see when running the code evolver.
"""
import time
from src import ProgressDisplay, Stage, ConfigManager

def demo_progress_display():
    """
    Demonstrate the progress display with simulated code evolution.
    """
    progress = ProgressDisplay(use_rich=True)
    config = ConfigManager()

    # Start the task
    progress.start("Generate Email Validator Function")

    try:
        # Stage 1: Initialization
        progress.enter_stage(Stage.INITIALIZATION, "Loading configuration and models")
        time.sleep(0.5)  # Simulate work
        progress.log_message("Configuration loaded successfully", "success")
        progress.log_message(f"Embedding model: {config.embedding_model}", "info")
        progress.exit_stage(success=True)

        # Stage 2: Overseer Planning
        progress.enter_stage(
            Stage.OVERSEER_PLANNING,
            "Consulting overseer LLM for strategy"
        )
        time.sleep(0.3)

        # Show token estimation
        planning_prompt = """Analyze this request and plan the best approach:
        Write a Python function that validates email addresses using regex.
        Include error handling and comprehensive tests."""
        estimated_tokens = progress.estimate_tokens(planning_prompt)
        progress.update_token_estimate("planning", estimated_tokens, "llama3")

        # Show context usage
        context_window = config.get_context_window("llama3")
        progress.show_context_info("llama3", context_window, estimated_tokens)

        time.sleep(0.5)
        progress.log_message("Strategy: Use regex pattern with RFC 5322 compliance", "info")
        progress.update_speed(tokens_per_second=35.2, chars_per_second=140.8)
        progress.exit_stage(success=True)

        # Stage 3: Code Generation
        progress.enter_stage(
            Stage.CODE_GENERATION,
            "Generating code with codellama"
        )
        time.sleep(0.3)

        code_prompt = f"{planning_prompt}\n\nImplement the following...\n(previous code)..."
        estimated_tokens = progress.estimate_tokens(code_prompt)
        progress.update_token_estimate("generation", estimated_tokens, "codellama")

        context_window = config.get_context_window("codellama")
        progress.show_context_info("codellama", context_window, estimated_tokens)

        time.sleep(1.0)  # Simulate code generation
        progress.log_message("Generated 45 lines of code", "success")
        progress.update_speed(tokens_per_second=28.5, chars_per_second=114.0)
        progress.exit_stage(success=True)

        # Stage 4: Testing
        progress.enter_stage(Stage.TESTING, "Running unit tests")
        time.sleep(0.4)
        progress.log_message("Test 1: Valid email formats - PASSED", "success")
        progress.log_message("Test 2: Invalid formats - PASSED", "success")
        progress.log_message("Test 3: Edge cases - PASSED", "success")
        progress.log_message("Test 4: Special characters - PASSED", "success")
        progress.exit_stage(success=True)

        # Stage 5: Evaluation
        progress.enter_stage(Stage.EVALUATION, "Evaluating code quality")
        time.sleep(0.5)

        eval_metrics = {
            "correctness": 0.95,
            "efficiency": 0.88,
            "readability": 0.92,
            "test_coverage": 0.90
        }
        progress.show_metrics_table(eval_metrics)
        progress.exit_stage(success=True)

        # Stage 6: RAG Storage
        progress.enter_stage(Stage.RAG_STORAGE, "Storing in RAG memory for future reuse")
        time.sleep(0.3)
        progress.log_message(f"Stored with embedding model: {config.embedding_model}", "info")
        progress.log_message("Added tags: validation, email, regex, utility", "info")
        progress.exit_stage(success=True)

        # Stage 7: Evolution (simulated)
        progress.enter_stage(Stage.EVOLUTION, "Checking optimization opportunities")
        time.sleep(0.2)

        # Show optimization progress
        scores = [0.85, 0.87, 0.89, 0.91, 0.92]
        for i, score in enumerate(scores, 1):
            improvement = score - scores[i-2] if i > 1 else 0
            progress.show_optimization_progress(i, score, improvement)
            time.sleep(0.2)

        progress.log_message("Optimization complete - improved by 8.2%", "success")
        progress.exit_stage(success=True)

        # Stage 8: Complete
        progress.enter_stage(Stage.COMPLETE, "Finalizing")
        time.sleep(0.2)
        progress.exit_stage(success=True)

        # Final summary
        final_metrics = {
            "total_tokens_processed": 1247,
            "average_speed_tokens_per_sec": 31.8,
            "total_stages": 8,
            "quality_score": 0.92,
            "test_pass_rate": 1.0,
            "lines_of_code": 45,
            "optimization_improvement": 0.082
        }

        progress.show_summary(success=True, final_metrics=final_metrics)

    except Exception as e:
        progress.log_message(f"Error: {str(e)}", "error")
        progress.show_summary(success=False, final_metrics={})


if __name__ == "__main__":
    print("\n" + "="*70)
    print("CODE EVOLVER - Progress Display Demo")
    print("This shows what you'll see during code evolution")
    print("="*70 + "\n")

    demo_progress_display()

    print("\n" + "="*70)
    print("Demo complete! This is what the exe will show during operation.")
    print("="*70 + "\n")
