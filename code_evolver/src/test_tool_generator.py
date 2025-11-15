"""
Test Tool Generator

Uses LLMs (like CodeLlama) to automatically generate test tools for any quality dimension.
This is a meta-testing tool - it generates tools that test code!

Usage:
    generator = TestToolGenerator(llm_client)

    # Generate a test tool for a specific dimension
    test_tool_code = generator.generate_test_tool(
        dimension="accuracy",
        tool_description="HTTP API fetcher",
        input_type="str (URL)",
        output_type="dict (JSON response)",
        quality_criteria="Must return valid JSON with status code 200"
    )

    # The generated test tool can then be used to test implementations
    exec(test_tool_code)  # Creates test_accuracy() function

    result = test_accuracy(input_data, output_data)
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import inspect
import ast
import json
from pathlib import Path


@dataclass
class TestToolSpec:
    """Specification for a test tool"""
    dimension: str
    description: str
    input_type: str
    output_type: str
    quality_criteria: str
    examples: Optional[List[Dict[str, Any]]] = None


class TestToolGenerator:
    """
    Generates test tools using LLMs for any quality dimension.

    This is a "testing tool generator" - it creates tools that test code!
    """

    def __init__(self, llm_client: Any, model: str = "codellama"):
        """
        Initialize test tool generator.

        Args:
            llm_client: LLM client (OllamaClient, OpenAI, etc.)
            model: Model to use for generation (default: codellama)
        """
        self.llm_client = llm_client
        self.model = model

        # Cache of generated test tools
        self.generated_tools: Dict[str, str] = {}

    def generate_test_tool(
        self,
        spec: TestToolSpec,
        return_as_function: bool = False
    ) -> str:
        """
        Generate a test tool for a specific quality dimension.

        Args:
            spec: TestToolSpec describing what to test
            return_as_function: If True, returns executable function instead of code string

        Returns:
            Python code for the test tool (or function if return_as_function=True)

        Example:
            spec = TestToolSpec(
                dimension="accuracy",
                description="Tests if HTTP fetcher returns correct status codes",
                input_type="str (URL)",
                output_type="dict with 'status' and 'data' keys",
                quality_criteria="Status code must match expected value",
                examples=[
                    {"input": "http://example.com", "expected_status": 200},
                    {"input": "http://notfound.com", "expected_status": 404}
                ]
            )

            code = generator.generate_test_tool(spec)
        """
        # Check cache
        cache_key = f"{spec.dimension}:{hash(str(spec))}"
        if cache_key in self.generated_tools:
            code = self.generated_tools[cache_key]
            if return_as_function:
                return self._code_to_function(code, spec.dimension)
            return code

        # Build prompt for LLM
        prompt = self._build_generation_prompt(spec)

        # Generate code
        try:
            response = self.llm_client.generate(
                model=self.model,
                prompt=prompt,
                temperature=0.2,  # Low temperature for code generation
                model_key="code_generator"
            )

            # Extract code from response
            code = self._extract_code(response)

            # Validate generated code
            if self._validate_code(code):
                self.generated_tools[cache_key] = code

                if return_as_function:
                    return self._code_to_function(code, spec.dimension)
                return code
            else:
                raise ValueError("Generated code failed validation")

        except Exception as e:
            print(f"Failed to generate test tool: {e}")
            # Fallback to template
            return self._generate_template_test_tool(spec)

    def _build_generation_prompt(self, spec: TestToolSpec) -> str:
        """Build prompt for LLM to generate test tool"""

        examples_str = ""
        if spec.examples:
            examples_str = "\n\nEXAMPLE TEST CASES:\n"
            for i, example in enumerate(spec.examples, 1):
                examples_str += f"{i}. {json.dumps(example, indent=2)}\n"

        prompt = f"""You are an expert at generating Python test code.

Generate a Python function that tests the '{spec.dimension}' quality dimension for a tool.

TOOL DESCRIPTION: {spec.description}

INPUT TYPE: {spec.input_type}
OUTPUT TYPE: {spec.output_type}

QUALITY CRITERIA: {spec.quality_criteria}
{examples_str}

Generate a Python function with this EXACT signature:

def test_{spec.dimension}(input_data: dict, output_data: dict, criteria: dict = None) -> float:
    \"\"\"
    Test {spec.dimension} quality dimension.

    Args:
        input_data: Input to the tool (dict with 'value' or specific keys)
        output_data: Output from the tool (dict with 'result' or specific keys)
        criteria: Optional additional test criteria

    Returns:
        Score from 0.0 (worst) to 1.0 (best)
    \"\"\"
    # Your test logic here
    pass

Requirements:
1. Must return a float between 0.0 and 1.0
2. Must handle edge cases gracefully (return 0.0 on error)
3. Must be well-documented with comments
4. Must extract actual values from dicts properly
5. Should use the quality criteria to determine pass/fail

Return ONLY the Python function code. No explanations, no markdown fences.
"""

        return prompt

    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response"""
        import re

        # Remove markdown code fences
        code = response.strip()

        if '```python' in code:
            code = code.split('```python')[1].split('```')[0].strip()
        elif '```' in code:
            code = code.split('```')[1].split('```')[0].strip()

        # Remove any explanation text before the function
        lines = code.split('\n')
        code_start = 0

        for i, line in enumerate(lines):
            if line.strip().startswith('def test_'):
                code_start = i
                break

        code = '\n'.join(lines[code_start:])

        return code

    def _validate_code(self, code: str) -> bool:
        """Validate generated code"""
        try:
            # Parse as AST
            tree = ast.parse(code)

            # Check for function definition
            has_function = any(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))

            # Check for return statement
            has_return = any(isinstance(node, ast.Return) for node in ast.walk(tree))

            return has_function and has_return

        except SyntaxError:
            return False

    def _code_to_function(self, code: str, dimension: str) -> Callable:
        """Convert code string to executable function"""
        namespace = {}
        exec(code, namespace)

        func_name = f"test_{dimension}"
        if func_name in namespace:
            return namespace[func_name]

        # Fallback: find any test_ function
        for name, obj in namespace.items():
            if name.startswith('test_') and callable(obj):
                return obj

        raise ValueError(f"No function found in generated code")

    def _generate_template_test_tool(self, spec: TestToolSpec) -> str:
        """Generate a template test tool if LLM generation fails"""

        template = f'''def test_{spec.dimension}(input_data: dict, output_data: dict, criteria: dict = None) -> float:
    """
    Test {spec.dimension} for: {spec.description}

    Input: {spec.input_type}
    Output: {spec.output_type}
    Criteria: {spec.quality_criteria}
    """
    try:
        # Extract actual values
        actual_output = output_data.get('result', output_data)

        # Check if output exists
        if actual_output is None:
            return 0.0

        # Basic validation based on type
        expected_type = criteria.get('expected_type') if criteria else None

        if expected_type and not isinstance(actual_output, expected_type):
            return 0.5  # Type mismatch, but not complete failure

        # Check for expected value if provided
        expected_value = criteria.get('expected_value') if criteria else None

        if expected_value is not None:
            return 1.0 if actual_output == expected_value else 0.0

        # Default: non-empty output is success
        if isinstance(actual_output, (str, list, dict)):
            return 1.0 if len(actual_output) > 0 else 0.0

        return 1.0  # Any other non-None value

    except Exception as e:
        # Error in test tool itself
        return 0.0
'''

        return template

    def generate_test_suite(
        self,
        tool_name: str,
        tool_description: str,
        dimensions: List[str],
        input_type: str,
        output_type: str,
        quality_criteria: Dict[str, str]
    ) -> str:
        """
        Generate a complete test suite for multiple quality dimensions.

        Args:
            tool_name: Name of the tool to test
            tool_description: Description of what the tool does
            dimensions: List of quality dimensions to test
            input_type: Description of input type
            output_type: Description of output type
            quality_criteria: Dict mapping dimension -> criteria

        Returns:
            Python code for complete test suite

        Example:
            test_suite = generator.generate_test_suite(
                tool_name="http_fetcher",
                tool_description="Fetches data from HTTP APIs",
                dimensions=["accuracy", "reliability", "performance"],
                input_type="str (URL)",
                output_type="dict (JSON response)",
                quality_criteria={
                    "accuracy": "Returns valid JSON with correct schema",
                    "reliability": "Handles errors gracefully",
                    "performance": "Completes within 5 seconds"
                }
            )
        """
        suite_code = []

        # Header
        suite_code.append(f'"""Test suite for {tool_name}\n\nGenerated by TestToolGenerator\n"""')
        suite_code.append("\nfrom typing import Dict, Any\n\n")

        # Generate each test function
        for dimension in dimensions:
            spec = TestToolSpec(
                dimension=dimension,
                description=tool_description,
                input_type=input_type,
                output_type=output_type,
                quality_criteria=quality_criteria.get(dimension, f"Test {dimension}")
            )

            test_code = self.generate_test_tool(spec)
            suite_code.append(test_code)
            suite_code.append("\n\n")

        # Add runner function
        runner = f'''def run_all_tests(input_data: Dict[str, Any], output_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Run all quality dimension tests.

    Returns:
        Dict mapping dimension -> score
    """
    results = {{}}

    dimensions = {dimensions}

    for dimension in dimensions:
        test_func = globals()[f"test_{{dimension}}"]
        try:
            score = test_func(input_data, output_data)
            results[dimension] = float(score)
        except Exception as e:
            print(f"Test {{dimension}} failed: {{e}}")
            results[dimension] = 0.0

    return results
'''

        suite_code.append(runner)

        return "\n".join(suite_code)

    def save_test_suite(self, test_suite_code: str, output_path: str):
        """Save generated test suite to file"""
        Path(output_path).write_text(test_suite_code)

    def load_test_suite(self, test_suite_path: str) -> Dict[str, Callable]:
        """
        Load a test suite from file and return test functions.

        Args:
            test_suite_path: Path to test suite file

        Returns:
            Dict mapping dimension -> test_function
        """
        code = Path(test_suite_path).read_text()

        namespace = {}
        exec(code, namespace)

        # Extract test functions
        test_functions = {}
        for name, obj in namespace.items():
            if name.startswith('test_') and callable(obj):
                dimension = name.replace('test_', '')
                test_functions[dimension] = obj

        return test_functions


# Integration with QualityEvaluator from existing codebase
class GeneratedQualityEvaluator:
    """
    Extends the existing QualityEvaluator with LLM-generated test tools.

    Combines hand-written evaluators with LLM-generated ones.
    """

    def __init__(self, llm_client: Any, code_generator_model: str = "codellama"):
        """
        Initialize evaluator with test tool generation capability.

        Args:
            llm_client: LLM client for generation
            code_generator_model: Model to use for code generation
        """
        self.generator = TestToolGenerator(llm_client, code_generator_model)
        self.evaluators: Dict[str, Callable] = {}
        self.thresholds: Dict[str, float] = {}

    def register_generated_dimension(
        self,
        spec: TestToolSpec,
        threshold: float = 0.7
    ):
        """
        Generate and register a test tool for a quality dimension.

        Args:
            spec: Specification for the test tool
            threshold: Minimum score to pass

        Example:
            spec = TestToolSpec(
                dimension="api_correctness",
                description="API returns correct HTTP status codes",
                input_type="str",
                output_type="dict",
                quality_criteria="Status code matches expected value"
            )

            evaluator.register_generated_dimension(spec, threshold=0.9)
        """
        # Generate test function
        test_func = self.generator.generate_test_tool(spec, return_as_function=True)

        # Register it
        self.evaluators[spec.dimension] = test_func
        self.thresholds[spec.dimension] = threshold

        print(f"✅ Registered generated test tool for '{spec.dimension}'")

    def evaluate(
        self,
        dimension: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        criteria: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Evaluate a quality dimension using generated or registered test tool.

        Args:
            dimension: Quality dimension to test
            input_data: Input to the tool
            output_data: Output from the tool
            criteria: Optional additional test criteria

        Returns:
            Score from 0.0 to 1.0
        """
        if dimension not in self.evaluators:
            raise ValueError(f"No test tool registered for dimension: {dimension}")

        test_func = self.evaluators[dimension]

        try:
            score = test_func(input_data, output_data, criteria)
            return max(0.0, min(1.0, float(score)))  # Clamp to [0, 1]
        except Exception as e:
            print(f"Evaluation failed for {dimension}: {e}")
            return 0.0

    def evaluate_all(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        dimensions: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Evaluate multiple dimensions.

        Args:
            input_data: Input to the tool
            output_data: Output from the tool
            dimensions: List of dimensions to evaluate (all if None)

        Returns:
            Dict mapping dimension -> score
        """
        if dimensions is None:
            dimensions = list(self.evaluators.keys())

        results = {}
        for dimension in dimensions:
            results[dimension] = self.evaluate(dimension, input_data, output_data)

        return results
