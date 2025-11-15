"""
Quality Evaluator using phi3:3.8b for comprehensive quality assessment.
Evaluates strategy, code, tests, and provides feedback for iterative improvement.
"""
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EvaluationStep(Enum):
    """Steps in the workflow that can be evaluated."""
    STRATEGY = "strategy"
    CODE = "code"
    TESTS = "tests"
    FINAL = "final"


@dataclass
class EvaluationResult:
    """Result of a quality evaluation."""
    step: EvaluationStep
    score: float  # 0.0-1.0
    passed: bool
    feedback: str
    suggestions: List[str]
    strengths: List[str]
    weaknesses: List[str]
    examples: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class QualityEvaluator:
    """
    Evaluates quality at each workflow step using phi3:3.8b.
    Provides feedback for iterative improvement and auto-adjusts thresholds.
    """

    def __init__(self, ollama_client, config_manager, rag_memory=None):
        """
        Initialize quality evaluator.

        Args:
            ollama_client: OllamaClient instance
            config_manager: ConfigManager instance
            rag_memory: Optional RAG memory for storing feedback patterns
        """
        self.client = ollama_client
        self.config = config_manager
        self.rag = rag_memory

        # Load evaluation settings
        self.enabled = config_manager.get("quality_evaluation.enabled", True)
        self.evaluate_steps = config_manager.get("quality_evaluation.evaluate_steps", {})
        self.thresholds = config_manager.get("quality_evaluation.thresholds", {})
        self.max_iterations = config_manager.get("quality_evaluation.max_iterations", 3)
        self.improvement_threshold = config_manager.get("quality_evaluation.improvement_threshold", 0.05)
        self.feedback_config = config_manager.get("quality_evaluation.feedback", {})

        # Get evaluator models for different types
        self._evaluator_models = {
            "writing": self._get_evaluator_model("writing"),
            "code": self._get_evaluator_model("code"),
            "default": self._get_evaluator_model("default")
        }

        # Historical evaluation scores for threshold adjustment
        self.evaluation_history: Dict[str, List[float]] = {
            "strategy": [],
            "code": [],
            "tests": [],
            "final": [],
            "writing": []
        }

    def _get_evaluator_model(self, eval_type: str) -> str:
        """Get the appropriate evaluator model for a given type."""
        evaluator_config = self.config.get("ollama.models.evaluator", {})

        if isinstance(evaluator_config, dict):
            # New multi-model format
            type_config = evaluator_config.get(eval_type, evaluator_config.get("default", {}))
            if isinstance(type_config, dict):
                return type_config.get("model", "llama3")
            return str(type_config) if type_config else "llama3"
        else:
            # Old single-model format
            return str(evaluator_config) if evaluator_config else "llama3"

    def _get_model_for_content_type(self, content_type: str) -> str:
        """Get the appropriate model for evaluating a content type."""
        # Map content types to evaluator types
        type_mapping = {
            "strategy": "default",
            "code": "code",
            "tests": "code",
            "writing": "writing",
            "article": "writing",
            "blog": "writing",
            "documentation": "writing"
        }

        eval_type = type_mapping.get(content_type.lower(), "default")
        return self._evaluator_models.get(eval_type, self._evaluator_models["default"])

    def evaluate_strategy(self, strategy: str, task_description: str) -> EvaluationResult:
        """
        Evaluate the quality of overseer's strategy.

        Args:
            strategy: The strategy text from overseer
            task_description: Original task description

        Returns:
            EvaluationResult with score and feedback
        """
        if not self.enabled or not self.evaluate_steps.get("strategy", True):
            return EvaluationResult(
                step=EvaluationStep.STRATEGY,
                score=1.0,
                passed=True,
                feedback="Evaluation disabled",
                suggestions=[],
                strengths=[],
                weaknesses=[]
            )

        eval_model = self._get_model_for_content_type("strategy")
        logger.info(f"Evaluating strategy quality with {eval_model}...")

        prompt = f"""You are an expert software architect evaluating a strategic plan.

TASK: {task_description}

STRATEGY:
{strategy}

Evaluate this strategy on:
1. **Clarity**: Is the approach clearly explained?
2. **Completeness**: Does it address all aspects of the task?
3. **Feasibility**: Is the approach practically implementable?
4. **Best Practices**: Does it follow software engineering best practices?
5. **Edge Cases**: Does it consider potential edge cases?

Provide your evaluation in JSON format:
{{
  "score": 0.85,  // 0.0-1.0
  "strengths": ["clear explanation", "considers edge cases"],
  "weaknesses": ["missing error handling strategy", "no performance considerations"],
  "suggestions": ["add error handling approach", "consider performance implications"],
  "feedback": "Overall assessment in 2-3 sentences"
}}

Return ONLY the JSON object."""

        try:
            response = self.client.generate(
                model=eval_model,
                prompt=prompt,
                temperature=0.3,
                model_key="evaluator"
            )

            # Parse JSON response
            response = response.strip()
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0].strip()
            elif response.startswith('```'):
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            score = float(result.get("score", 0.5))
            min_threshold = self._get_adjusted_threshold("strategy_min", 0.70)
            passed = score >= min_threshold

            eval_result = EvaluationResult(
                step=EvaluationStep.STRATEGY,
                score=score,
                passed=passed,
                feedback=result.get("feedback", ""),
                suggestions=result.get("suggestions", []),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                metadata={"task": task_description, "threshold": min_threshold}
            )

            # Store in history
            self.evaluation_history["strategy"].append(score)
            self._store_evaluation_in_rag(eval_result, strategy)

            logger.info(f"Strategy evaluation: {score:.2f} (threshold: {min_threshold:.2f}) - {'PASS' if passed else 'FAIL'}")
            return eval_result

        except Exception as e:
            logger.error(f"Strategy evaluation failed: {e}")
            return EvaluationResult(
                step=EvaluationStep.STRATEGY,
                score=0.5,
                passed=False,
                feedback=f"Evaluation error: {e}",
                suggestions=["Manual review required"],
                strengths=[],
                weaknesses=[f"Evaluation failed: {e}"]
            )

    def evaluate_code(self, code: str, task_description: str, strategy: str) -> EvaluationResult:
        """
        Evaluate the quality of generated code.

        Args:
            code: The generated code
            task_description: Original task description
            strategy: The strategy used

        Returns:
            EvaluationResult with score and feedback
        """
        if not self.enabled or not self.evaluate_steps.get("code", True):
            return EvaluationResult(
                step=EvaluationStep.CODE,
                score=1.0,
                passed=True,
                feedback="Evaluation disabled",
                suggestions=[],
                strengths=[],
                weaknesses=[]
            )

        eval_model = self._get_model_for_content_type("code")
        logger.info(f"Evaluating code quality with {eval_model}...")

        prompt = f"""You are an expert code reviewer. Evaluate this Python code.

TASK: {task_description}

STRATEGY USED:
{strategy[:300]}...

CODE:
```python
{code}
```

Evaluate on:
1. **Correctness**: Does it solve the task?
2. **Code Quality**: Clean, readable, well-structured?
3. **Error Handling**: Proper error handling?
4. **Best Practices**: Follows Python best practices?
5. **Documentation**: Well-documented with docstrings?
6. **Testing**: Includes proper __main__ section for I/O?

Provide evaluation in JSON format:
{{
  "score": 0.80,
  "strengths": ["clean code", "good error handling"],
  "weaknesses": ["missing type hints", "no docstring"],
  "suggestions": ["add type hints", "add module docstring"],
  "feedback": "Overall code quality assessment",
  "examples": {{
    "improvement": "def process(data: dict) -> dict: ..."
  }}
}}

Return ONLY the JSON object."""

        try:
            response = self.client.generate(
                model=eval_model,
                prompt=prompt,
                temperature=0.3,
                model_key="evaluator"
            )

            response = response.strip()
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0].strip()
            elif response.startswith('```'):
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            score = float(result.get("score", 0.5))
            min_threshold = self._get_adjusted_threshold("code_quality_min", 0.75)
            passed = score >= min_threshold

            eval_result = EvaluationResult(
                step=EvaluationStep.CODE,
                score=score,
                passed=passed,
                feedback=result.get("feedback", ""),
                suggestions=result.get("suggestions", []),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                examples=result.get("examples"),
                metadata={"task": task_description, "threshold": min_threshold}
            )

            self.evaluation_history["code"].append(score)
            self._store_evaluation_in_rag(eval_result, code)

            logger.info(f"Code evaluation: {score:.2f} (threshold: {min_threshold:.2f}) - {'PASS' if passed else 'FAIL'}")
            return eval_result

        except Exception as e:
            logger.error(f"Code evaluation failed: {e}")
            return EvaluationResult(
                step=EvaluationStep.CODE,
                score=0.5,
                passed=False,
                feedback=f"Evaluation error: {e}",
                suggestions=["Manual review required"],
                strengths=[],
                weaknesses=[f"Evaluation failed: {e}"]
            )

    def evaluate_tests(self, test_code: str, main_code: str) -> EvaluationResult:
        """
        Evaluate the quality of generated tests.

        Args:
            test_code: The test code
            main_code: The main code being tested

        Returns:
            EvaluationResult with score and feedback
        """
        if not self.enabled or not self.evaluate_steps.get("tests", True):
            return EvaluationResult(
                step=EvaluationStep.TESTS,
                score=1.0,
                passed=True,
                feedback="Evaluation disabled",
                suggestions=[],
                strengths=[],
                weaknesses=[]
            )

        eval_model = self._get_model_for_content_type("tests")
        logger.info(f"Evaluating test quality with {eval_model}...")

        prompt = f"""You are an expert in software testing. Evaluate these unit tests.

MAIN CODE:
```python
{main_code[:500]}...
```

TEST CODE:
```python
{test_code}
```

Evaluate on:
1. **Coverage**: Do tests cover normal cases, edge cases, errors?
2. **Quality**: Well-structured, clear assertions?
3. **Independence**: Tests are independent and isolated?
4. **Best Practices**: Follows testing best practices?

Provide evaluation in JSON format:
{{
  "score": 0.85,
  "strengths": ["good coverage", "tests edge cases"],
  "weaknesses": ["missing error case tests"],
  "suggestions": ["add test for invalid input", "test boundary conditions"],
  "feedback": "Overall test quality assessment"
}}

Return ONLY the JSON object."""

        try:
            response = self.client.generate(
                model=eval_model,
                prompt=prompt,
                temperature=0.3,
                model_key="evaluator"
            )

            response = response.strip()
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0].strip()
            elif response.startswith('```'):
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            score = float(result.get("score", 0.5))
            min_threshold = self._get_adjusted_threshold("test_coverage_min", 0.80)
            passed = score >= min_threshold

            eval_result = EvaluationResult(
                step=EvaluationStep.TESTS,
                score=score,
                passed=passed,
                feedback=result.get("feedback", ""),
                suggestions=result.get("suggestions", []),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                metadata={"threshold": min_threshold}
            )

            self.evaluation_history["tests"].append(score)
            self._store_evaluation_in_rag(eval_result, test_code)

            logger.info(f"Test evaluation: {score:.2f} (threshold: {min_threshold:.2f}) - {'PASS' if passed else 'FAIL'}")
            return eval_result

        except Exception as e:
            logger.error(f"Test evaluation failed: {e}")
            return EvaluationResult(
                step=EvaluationStep.TESTS,
                score=0.5,
                passed=False,
                feedback=f"Evaluation error: {e}",
                suggestions=["Manual review required"],
                strengths=[],
                weaknesses=[f"Evaluation failed: {e}"]
            )

    def evaluate_writing(
        self,
        content: str,
        task_description: str,
        content_type: str = "article"
    ) -> EvaluationResult:
        """
        Evaluate the quality of technical writing (blog posts, articles, documentation).
        Uses phi3:3.8b specifically for writing evaluation.

        Args:
            content: The written content to evaluate
            task_description: Original writing task/goal
            content_type: Type of writing ("article", "blog", "documentation")

        Returns:
            EvaluationResult with score and feedback
        """
        if not self.enabled:
            return EvaluationResult(
                step=EvaluationStep.FINAL,
                score=1.0,
                passed=True,
                feedback="Evaluation disabled",
                suggestions=[],
                strengths=[],
                weaknesses=[]
            )

        eval_model = self._get_model_for_content_type("writing")
        logger.info(f"Evaluating writing quality with {eval_model}...")

        prompt = f"""You are an expert technical writing editor. Evaluate this {content_type}.

TASK: {task_description}

CONTENT:
{content[:2000]}{"..." if len(content) > 2000 else ""}

Evaluate on:
1. **Clarity**: Is the content clear and easy to understand?
2. **Technical Accuracy**: Is the technical information correct?
3. **Structure**: Is the content well-organized with logical flow?
4. **Readability**: Is it readable for the target audience?
5. **Completeness**: Does it cover the topic adequately?
6. **Engagement**: Is it engaging and interesting?
7. **SEO**: Does it have good keywords and structure for search?

Provide evaluation in JSON format:
{{
  "score": 0.85,
  "strengths": ["clear explanations", "good examples", "well-structured"],
  "weaknesses": ["missing code examples", "no SEO optimization"],
  "suggestions": [
    "add more code examples",
    "optimize headings for SEO",
    "include practical use cases"
  ],
  "feedback": "Overall quality assessment in 2-3 sentences",
  "examples": {{
    "improvement": "Consider adding: ## Practical Use Cases..."
  }}
}}

Return ONLY the JSON object."""

        try:
            response = self.client.generate(
                model=eval_model,
                prompt=prompt,
                temperature=0.3,
                model_key="evaluator"
            )

            response = response.strip()
            if response.startswith('```json'):
                response = response.split('```json')[1].split('```')[0].strip()
            elif response.startswith('```'):
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            score = float(result.get("score", 0.5))
            min_threshold = self._get_adjusted_threshold("final_min", 0.80)
            passed = score >= min_threshold

            eval_result = EvaluationResult(
                step=EvaluationStep.FINAL,
                score=score,
                passed=passed,
                feedback=result.get("feedback", ""),
                suggestions=result.get("suggestions", []),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                examples=result.get("examples"),
                metadata={
                    "task": task_description,
                    "content_type": content_type,
                    "threshold": min_threshold
                }
            )

            self.evaluation_history["writing"].append(score)
            self._store_evaluation_in_rag(eval_result, content)

            logger.info(f"Writing evaluation: {score:.2f} (threshold: {min_threshold:.2f}) - {'PASS' if passed else 'FAIL'}")
            return eval_result

        except Exception as e:
            logger.error(f"Writing evaluation failed: {e}")
            return EvaluationResult(
                step=EvaluationStep.FINAL,
                score=0.5,
                passed=False,
                feedback=f"Evaluation error: {e}",
                suggestions=["Manual review required"],
                strengths=[],
                weaknesses=[f"Evaluation failed: {e}"]
            )

    def improve_with_feedback(
        self,
        content: str,
        evaluation: EvaluationResult,
        content_type: str,
        context: Dict[str, str]
    ) -> Tuple[str, EvaluationResult]:
        """
        Improve content based on evaluator feedback.

        Args:
            content: The content to improve (strategy, code, or tests)
            evaluation: The evaluation result with feedback
            content_type: Type of content ("strategy", "code", "tests")
            context: Additional context (task_description, etc.)

        Returns:
            Tuple of (improved_content, new_evaluation)
        """
        if evaluation.passed:
            logger.info(f"{content_type} already passed evaluation")
            return content, evaluation

        logger.info(f"Attempting to improve {content_type} based on feedback...")

        # Build improvement prompt
        improvement_prompt = f"""You are an expert improving {content_type}.

ORIGINAL {content_type.upper()}:
{content}

EVALUATION FEEDBACK:
Score: {evaluation.score:.2f}
Strengths: {', '.join(evaluation.strengths)}
Weaknesses: {', '.join(evaluation.weaknesses)}
Suggestions: {', '.join(evaluation.suggestions)}

{evaluation.feedback}

Task: {context.get('task_description', 'N/A')}

Improve the {content_type} to address ALL weaknesses and suggestions.
Return the improved version ONLY (no explanations).
"""

        if content_type == "code":
            improvement_prompt += """
Return valid Python code with improvements applied.
DO NOT include markdown fences.
"""

        try:
            improved = self.client.generate(
                model=self.config.escalation_model if content_type == "code" else self.config.overseer_model,
                prompt=improvement_prompt,
                temperature=0.4,
                model_key="escalation" if content_type == "code" else "overseer"
            )

            # Clean code if needed
            if content_type == "code":
                import re
                improved = re.sub(r'^```python\s*\n', '', improved, flags=re.MULTILINE)
                improved = re.sub(r'^```\s*\n', '', improved, flags=re.MULTILINE)
                improved = re.sub(r'\n```\s*$', '', improved, flags=re.MULTILINE)
                improved = improved.strip()

            # Re-evaluate
            if content_type == "strategy":
                new_eval = self.evaluate_strategy(improved, context.get('task_description', ''))
            elif content_type == "code":
                new_eval = self.evaluate_code(
                    improved,
                    context.get('task_description', ''),
                    context.get('strategy', '')
                )
            elif content_type == "tests":
                new_eval = self.evaluate_tests(improved, context.get('main_code', ''))
            elif content_type in ["writing", "article", "blog", "documentation"]:
                new_eval = self.evaluate_writing(
                    improved,
                    context.get('task_description', ''),
                    content_type
                )
            else:
                raise ValueError(f"Unknown content type: {content_type}")

            improvement = new_eval.score - evaluation.score
            logger.info(f"Improvement iteration: score {evaluation.score:.2f} -> {new_eval.score:.2f} (Δ{improvement:+.2f})")

            return improved, new_eval

        except Exception as e:
            logger.error(f"Improvement failed: {e}")
            return content, evaluation

    def iterative_improve(
        self,
        content: str,
        content_type: str,
        context: Dict[str, str]
    ) -> Tuple[str, List[EvaluationResult]]:
        """
        Iteratively improve content until it passes or max iterations reached.

        Args:
            content: Initial content
            content_type: Type ("strategy", "code", "tests")
            context: Context dict with task_description, strategy, etc.

        Returns:
            Tuple of (final_content, list_of_evaluations)
        """
        evaluations = []
        current_content = content

        # Initial evaluation
        if content_type == "strategy":
            eval_result = self.evaluate_strategy(current_content, context.get('task_description', ''))
        elif content_type == "code":
            eval_result = self.evaluate_code(
                current_content,
                context.get('task_description', ''),
                context.get('strategy', '')
            )
        elif content_type == "tests":
            eval_result = self.evaluate_tests(current_content, context.get('main_code', ''))
        elif content_type in ["writing", "article", "blog", "documentation"]:
            eval_result = self.evaluate_writing(
                current_content,
                context.get('task_description', ''),
                content_type
            )
        else:
            raise ValueError(f"Unknown content type: {content_type}")

        evaluations.append(eval_result)

        # Iterative improvement
        iteration = 0
        while not eval_result.passed and iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Improvement iteration {iteration}/{self.max_iterations} for {content_type}")

            # Improve
            improved_content, new_eval = self.improve_with_feedback(
                current_content,
                eval_result,
                content_type,
                context
            )

            evaluations.append(new_eval)

            # Check if improvement is significant
            improvement = new_eval.score - eval_result.score
            if improvement < self.improvement_threshold and not new_eval.passed:
                logger.info(f"Improvement < {self.improvement_threshold:.2%}, stopping iterations")
                break

            current_content = improved_content
            eval_result = new_eval

        final_status = "PASSED" if eval_result.passed else f"FAILED (score: {eval_result.score:.2f})"
        logger.info(f"{content_type} final status after {iteration} iterations: {final_status}")

        return current_content, evaluations

    def _get_adjusted_threshold(self, threshold_key: str, default: float) -> float:
        """
        Get threshold, potentially auto-adjusted based on historical performance.

        Args:
            threshold_key: Key in thresholds config
            default: Default threshold value

        Returns:
            Adjusted threshold value
        """
        base_threshold = self.thresholds.get(threshold_key, default)

        if not self.thresholds.get("auto_adjust", False):
            return base_threshold

        # Get relevant history
        step_type = threshold_key.split('_')[0]  # e.g., "strategy", "code"
        history = self.evaluation_history.get(step_type, [])

        if len(history) < 10:  # Need minimum history
            return base_threshold

        # Use recent history window
        window = self.thresholds.get("adjustment_window", 100)
        recent_history = history[-window:]

        # Calculate percentile (e.g., 25th percentile as adjusted threshold)
        import statistics
        if len(recent_history) >= 10:
            median_score = statistics.median(recent_history)
            # Adjust threshold to be slightly below median (80% of median)
            adjusted = min(base_threshold, median_score * 0.8)
            logger.debug(f"Adjusted {threshold_key}: {base_threshold:.2f} -> {adjusted:.2f} (median: {median_score:.2f})")
            return adjusted

        return base_threshold

    def _store_evaluation_in_rag(self, evaluation: EvaluationResult, content: str):
        """Store evaluation feedback in RAG for learning."""
        if not self.rag or not self.feedback_config.get("store_in_rag", False):
            return

        try:
            from .rag_memory import ArtifactType

            # Store high-quality examples for learning
            if self.feedback_config.get("learn_from_success", True) and evaluation.score >= 0.85:
                self.rag.store_artifact(
                    artifact_id=f"eval_success_{evaluation.step.value}_{hash(content)}",
                    artifact_type=ArtifactType.PATTERN,
                    name=f"High-Quality {evaluation.step.value} Example",
                    description=f"Score: {evaluation.score:.2f} - {evaluation.feedback}",
                    content=content[:1000],
                    tags=["evaluation", "success", evaluation.step.value, "quality"],
                    metadata={
                        "score": evaluation.score,
                        "strengths": evaluation.strengths,
                        "step": evaluation.step.value
                    },
                    auto_embed=True
                )

            # Store feedback patterns
            if evaluation.suggestions:
                feedback_content = {
                    "score": evaluation.score,
                    "suggestions": evaluation.suggestions,
                    "weaknesses": evaluation.weaknesses,
                    "feedback": evaluation.feedback
                }

                self.rag.store_artifact(
                    artifact_id=f"eval_feedback_{evaluation.step.value}_{hash(str(feedback_content))}",
                    artifact_type=ArtifactType.PATTERN,
                    name=f"{evaluation.step.value} Improvement Pattern",
                    description=evaluation.feedback,
                    content=json.dumps(feedback_content, indent=2),
                    tags=["evaluation", "feedback", evaluation.step.value, "improvement"],
                    metadata={"step": evaluation.step.value, "score": evaluation.score},
                    auto_embed=True
                )

        except Exception as e:
            logger.warning(f"Failed to store evaluation in RAG: {e}")

    def get_evaluation_stats(self) -> Dict[str, Any]:
        """Get statistics about historical evaluations."""
        import statistics

        stats = {}
        for step_type, scores in self.evaluation_history.items():
            if scores:
                stats[step_type] = {
                    "count": len(scores),
                    "mean": statistics.mean(scores),
                    "median": statistics.median(scores),
                    "stdev": statistics.stdev(scores) if len(scores) > 1 else 0,
                    "min": min(scores),
                    "max": max(scores)
                }
            else:
                stats[step_type] = {"count": 0}

        return stats
