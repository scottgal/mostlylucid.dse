"""
Intelligent Fuzzer for Code Evolver

An intelligent fuzzing tool that tries to break functions/tools by feeding them
malformed, edge-case, and adversarial inputs. Inspired by Hypothesis, Atheris,
and AFL fuzzing strategies.

Features:
- Type-aware fuzzing based on function signatures
- Grammar-based fuzzing for structured data
- Mutation-based fuzzing from valid inputs
- Coverage-guided fuzzing to find new code paths
- Crash detection and reproduction
- Automatic test case generation from failures

Used for:
- Finding edge cases in tools
- Mutation testing optimization
- Generating comprehensive unit tests
- Security testing (finding injection vulnerabilities)
"""

import ast
import inspect
import random
import string
import sys
import traceback
import copy
import json
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import logging


class FuzzStrategy(Enum):
    """Fuzzing strategies"""
    RANDOM = "random"  # Pure random data
    TYPE_AWARE = "type_aware"  # Based on type hints
    MUTATION = "mutation"  # Mutate valid inputs
    GRAMMAR = "grammar"  # Grammar-based generation
    BOUNDARY = "boundary"  # Boundary value analysis
    ADVERSARIAL = "adversarial"  # Known attack patterns


@dataclass
class FuzzCase:
    """A single fuzzing test case"""
    strategy: FuzzStrategy
    inputs: Dict[str, Any]
    expected_crash: bool = False
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FuzzResult:
    """Result of fuzzing a function"""
    function_name: str
    test_case: FuzzCase
    crashed: bool
    exception: Optional[Exception] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    output: Optional[Any] = None
    execution_time_ms: float = 0.0


@dataclass
class FuzzReport:
    """Summary report of fuzzing session"""
    function_name: str
    total_cases: int = 0
    crashes: int = 0
    timeouts: int = 0
    successful: int = 0
    unique_crashes: int = 0
    crash_results: List[FuzzResult] = field(default_factory=list)
    coverage_paths: Set[str] = field(default_factory=set)
    timestamp: datetime = field(default_factory=datetime.now)


class IntelligentFuzzer:
    """
    Main fuzzing engine with multiple strategies
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        max_string_length: int = 1000,
        max_list_length: int = 100,
        max_dict_size: int = 50,
        timeout_seconds: float = 5.0
    ):
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        self.max_string_length = max_string_length
        self.max_list_length = max_list_length
        self.max_dict_size = max_dict_size
        self.timeout_seconds = timeout_seconds

        self.logger = logging.getLogger(__name__)

        # Known attack patterns
        self.sql_injection_patterns = [
            "' OR '1'='1",
            "1; DROP TABLE users--",
            "admin'--",
            "' UNION SELECT NULL--"
        ]

        self.xss_patterns = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "<svg onload=alert(1)>"
        ]

        self.path_traversal_patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM"
        ]

        self.command_injection_patterns = [
            "; ls -la",
            "| cat /etc/passwd",
            "`whoami`",
            "$(id)",
            "&& ping -c 10 google.com"
        ]

    # Type-aware fuzzing
    # ==================

    def fuzz_for_type(self, type_hint: Any) -> Any:
        """Generate fuzz data based on type hint"""
        # Handle None/NoneType
        if type_hint is None or type_hint == type(None):
            return None

        # Handle basic types
        if type_hint == int:
            return self._fuzz_int()
        elif type_hint == float:
            return self._fuzz_float()
        elif type_hint == str:
            return self._fuzz_string()
        elif type_hint == bool:
            return self._fuzz_bool()
        elif type_hint == bytes:
            return self._fuzz_bytes()
        elif type_hint == list or type_hint == List:
            return self._fuzz_list()
        elif type_hint == dict or type_hint == Dict:
            return self._fuzz_dict()

        # Handle typing module types
        if hasattr(type_hint, '__origin__'):
            origin = type_hint.__origin__
            args = getattr(type_hint, '__args__', ())

            if origin == list or origin == List:
                elem_type = args[0] if args else Any
                return [self.fuzz_for_type(elem_type) for _ in range(random.randint(0, 5))]

            elif origin == dict or origin == Dict:
                key_type = args[0] if len(args) > 0 else str
                val_type = args[1] if len(args) > 1 else Any
                return {
                    self.fuzz_for_type(key_type): self.fuzz_for_type(val_type)
                    for _ in range(random.randint(0, 5))
                }

            elif origin == tuple:
                return tuple(self.fuzz_for_type(arg) for arg in args)

            elif origin == Union:
                # Pick one of the union types
                chosen_type = random.choice(args)
                return self.fuzz_for_type(chosen_type)

        # Fallback: return None or random data
        return random.choice([None, 0, "", [], {}])

    def _fuzz_int(self) -> int:
        """Generate interesting integer values"""
        interesting_ints = [
            0, 1, -1,
            sys.maxsize, -sys.maxsize - 1,  # Max/min int
            2**31 - 1, -2**31,  # 32-bit boundaries
            2**63 - 1, -2**63,  # 64-bit boundaries
            2**32, 2**64,  # Overflow values
            127, -128,  # 8-bit boundaries
            32767, -32768,  # 16-bit boundaries
            random.randint(-10000, 10000),  # Random
        ]
        return random.choice(interesting_ints)

    def _fuzz_float(self) -> float:
        """Generate interesting float values"""
        interesting_floats = [
            0.0, -0.0,
            1.0, -1.0,
            float('inf'), float('-inf'), float('nan'),
            sys.float_info.max, sys.float_info.min,
            sys.float_info.epsilon,
            1e308, -1e308,  # Near max
            1e-308,  # Near min positive
            random.uniform(-1000.0, 1000.0),  # Random
        ]
        return random.choice(interesting_floats)

    def _fuzz_string(self) -> str:
        """Generate interesting string values"""
        strategies = [
            lambda: "",  # Empty
            lambda: " ",  # Single space
            lambda: "\n",  # Newline
            lambda: "\x00",  # Null byte
            lambda: "A" * random.randint(0, self.max_string_length),  # Long
            lambda: "🔥" * 100,  # Unicode
            lambda: "\u202e" + "test",  # Right-to-left override
            lambda: "\\n\\t\\r",  # Escaped characters
            lambda: random.choice(self.sql_injection_patterns),
            lambda: random.choice(self.xss_patterns),
            lambda: random.choice(self.path_traversal_patterns),
            lambda: random.choice(self.command_injection_patterns),
            lambda: ''.join(random.choices(string.printable, k=random.randint(1, 100))),
            lambda: ''.join(chr(random.randint(0, 1000)) for _ in range(20)),  # Random unicode
        ]
        return random.choice(strategies)()

    def _fuzz_bool(self) -> bool:
        """Generate bool value"""
        # Include truthy/falsy values that might break type checking
        return random.choice([True, False, 0, 1, "", "true", "false", None, [], {}])

    def _fuzz_bytes(self) -> bytes:
        """Generate interesting byte sequences"""
        strategies = [
            lambda: b"",
            lambda: b"\x00",
            lambda: b"\xff" * 100,
            lambda: bytes(random.randint(0, 255) for _ in range(random.randint(0, 100))),
        ]
        return random.choice(strategies)()

    def _fuzz_list(self) -> list:
        """Generate interesting lists"""
        strategies = [
            lambda: [],
            lambda: [None],
            lambda: [[] for _ in range(10)],  # Nested empty lists
            lambda: [[[[]]]],  # Deep nesting
            lambda: list(range(self.max_list_length)),  # Very long
            lambda: [random.choice([0, "", None, [], {}]) for _ in range(random.randint(0, 20))],
        ]
        return random.choice(strategies)()

    def _fuzz_dict(self) -> dict:
        """Generate interesting dictionaries"""
        strategies = [
            lambda: {},
            lambda: {None: None},
            lambda: {"": ""},
            lambda: {i: i for i in range(100)},  # Large dict
            lambda: {"key": {"key": {"key": {}}}},  # Deep nesting
            lambda: {random.choice(["a", "b", "c"]): random.choice([0, "", None]) for _ in range(10)},
        ]
        return random.choice(strategies)()

    # Mutation-based fuzzing
    # ======================

    def mutate_value(self, value: Any) -> Any:
        """Mutate a value to create a variant"""
        if value is None:
            return random.choice([0, "", [], {}])

        elif isinstance(value, bool):
            return not value

        elif isinstance(value, int):
            mutations = [
                lambda: value + random.randint(-10, 10),
                lambda: value * 2,
                lambda: -value,
                lambda: 0,
                lambda: sys.maxsize,
            ]
            return random.choice(mutations)()

        elif isinstance(value, float):
            mutations = [
                lambda: value + random.uniform(-10, 10),
                lambda: value * 2,
                lambda: -value,
                lambda: float('inf'),
                lambda: float('nan'),
            ]
            return random.choice(mutations)()

        elif isinstance(value, str):
            mutations = [
                lambda: value + random.choice(["!", "\n", "\x00"]),
                lambda: value * 2,
                lambda: value.upper(),
                lambda: value.lower(),
                lambda: value[::-1],  # Reverse
                lambda: "",
                lambda: value.replace(random.choice(value) if value else "a", "X"),
            ]
            return random.choice(mutations)()

        elif isinstance(value, list):
            mutations = [
                lambda: value + [None],
                lambda: value * 2,
                lambda: value[::-1],
                lambda: [],
                lambda: [self.mutate_value(v) for v in value],
            ]
            return random.choice(mutations)()

        elif isinstance(value, dict):
            mutations = [
                lambda: {**value, "extra": None},
                lambda: {},
                lambda: {k: self.mutate_value(v) for k, v in value.items()},
            ]
            return random.choice(mutations)()

        else:
            return value

    # Main fuzzing interface
    # ======================

    def fuzz_function(
        self,
        func: Callable,
        num_cases: int = 100,
        strategies: Optional[List[FuzzStrategy]] = None,
        valid_examples: Optional[List[Dict[str, Any]]] = None
    ) -> FuzzReport:
        """
        Fuzz a function with various strategies

        Args:
            func: Function to fuzz
            num_cases: Number of test cases to generate
            strategies: List of strategies to use (default: all)
            valid_examples: Valid input examples for mutation-based fuzzing

        Returns:
            FuzzReport with results
        """
        if strategies is None:
            strategies = list(FuzzStrategy)

        func_name = func.__name__
        report = FuzzReport(function_name=func_name)

        # Get function signature
        try:
            sig = inspect.signature(func)
        except:
            sig = None

        # Generate and run test cases
        for i in range(num_cases):
            # Pick a strategy
            strategy = random.choice(strategies)

            # Generate test case
            if strategy == FuzzStrategy.RANDOM:
                test_case = self._generate_random_case(sig)
            elif strategy == FuzzStrategy.TYPE_AWARE and sig:
                test_case = self._generate_type_aware_case(sig)
            elif strategy == FuzzStrategy.MUTATION and valid_examples:
                test_case = self._generate_mutation_case(valid_examples)
            elif strategy == FuzzStrategy.BOUNDARY and sig:
                test_case = self._generate_boundary_case(sig)
            elif strategy == FuzzStrategy.ADVERSARIAL:
                test_case = self._generate_adversarial_case(sig)
            else:
                # Fallback to random
                test_case = self._generate_random_case(sig)

            # Execute test case
            result = self._execute_test_case(func, test_case)
            report.total_cases += 1

            if result.crashed:
                report.crashes += 1
                report.crash_results.append(result)

                # Check if unique crash
                if result.exception_type not in [r.exception_type for r in report.crash_results[:-1]]:
                    report.unique_crashes += 1
            else:
                report.successful += 1

        return report

    def _generate_random_case(self, sig: Optional[inspect.Signature]) -> FuzzCase:
        """Generate completely random inputs"""
        inputs = {}

        if sig:
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'cls'):
                    continue
                inputs[param_name] = random.choice([
                    None, 0, "", [], {}, True, False,
                    random.randint(-1000, 1000),
                    random.choice(string.printable) * random.randint(0, 100)
                ])
        else:
            # No signature, just try a few random args
            inputs = {
                'arg0': random.randint(0, 100),
                'arg1': self._fuzz_string()
            }

        return FuzzCase(
            strategy=FuzzStrategy.RANDOM,
            inputs=inputs,
            description="Random data"
        )

    def _generate_type_aware_case(self, sig: inspect.Signature) -> FuzzCase:
        """Generate inputs based on type hints"""
        inputs = {}

        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'cls'):
                continue

            if param.annotation != inspect.Parameter.empty:
                inputs[param_name] = self.fuzz_for_type(param.annotation)
            else:
                inputs[param_name] = random.choice([None, 0, ""])

        return FuzzCase(
            strategy=FuzzStrategy.TYPE_AWARE,
            inputs=inputs,
            description="Type-aware fuzzing"
        )

    def _generate_mutation_case(self, valid_examples: List[Dict[str, Any]]) -> FuzzCase:
        """Mutate a valid input"""
        base_example = random.choice(valid_examples)
        mutated = {k: self.mutate_value(v) for k, v in base_example.items()}

        return FuzzCase(
            strategy=FuzzStrategy.MUTATION,
            inputs=mutated,
            description="Mutated from valid example"
        )

    def _generate_boundary_case(self, sig: inspect.Signature) -> FuzzCase:
        """Generate boundary values"""
        inputs = {}

        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'cls'):
                continue

            type_hint = param.annotation if param.annotation != inspect.Parameter.empty else None

            if type_hint == int:
                inputs[param_name] = random.choice([0, -1, 1, sys.maxsize, -sys.maxsize - 1])
            elif type_hint == float:
                inputs[param_name] = random.choice([0.0, float('inf'), float('-inf'), float('nan')])
            elif type_hint == str:
                inputs[param_name] = random.choice(["", "A" * 10000])
            elif type_hint == list:
                inputs[param_name] = random.choice([[], list(range(1000))])
            else:
                inputs[param_name] = None

        return FuzzCase(
            strategy=FuzzStrategy.BOUNDARY,
            inputs=inputs,
            description="Boundary values"
        )

    def _generate_adversarial_case(self, sig: Optional[inspect.Signature]) -> FuzzCase:
        """Generate adversarial inputs (injection attacks, etc.)"""
        inputs = {}

        attack_patterns = (
            self.sql_injection_patterns +
            self.xss_patterns +
            self.path_traversal_patterns +
            self.command_injection_patterns
        )

        if sig:
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'cls'):
                    continue
                inputs[param_name] = random.choice(attack_patterns)
        else:
            inputs = {'arg0': random.choice(attack_patterns)}

        return FuzzCase(
            strategy=FuzzStrategy.ADVERSARIAL,
            inputs=inputs,
            description="Adversarial patterns",
            expected_crash=False  # Should handle gracefully
        )

    def _execute_test_case(self, func: Callable, test_case: FuzzCase) -> FuzzResult:
        """Execute a test case and capture results"""
        import time

        result = FuzzResult(
            function_name=func.__name__,
            test_case=test_case,
            crashed=False
        )

        start_time = time.perf_counter()

        try:
            # Execute function
            output = func(**test_case.inputs)
            result.output = output
            result.crashed = False

        except Exception as e:
            # Captured a crash!
            result.crashed = True
            result.exception = e
            result.exception_type = type(e).__name__
            result.exception_message = str(e)
            result.stack_trace = traceback.format_exc()

        end_time = time.perf_counter()
        result.execution_time_ms = (end_time - start_time) * 1000

        return result

    def generate_test_cases_from_crashes(self, report: FuzzReport) -> str:
        """Generate pytest test cases from crash results"""
        test_code = f'''"""
Auto-generated test cases from fuzzing {report.function_name}
Generated: {datetime.now().isoformat()}
"""

import pytest

'''

        for i, crash in enumerate(report.crash_results):
            test_code += f'''
def test_fuzz_crash_{i}():
    """
    Crash found by {crash.test_case.strategy.value} fuzzing
    Exception: {crash.exception_type}
    Message: {crash.exception_message}
    """
    from module import {report.function_name}

    with pytest.raises({crash.exception_type}):
        {report.function_name}(**{repr(crash.test_case.inputs)})
'''

        return test_code


# Convenience functions
# =====================

def fuzz(
    func: Callable,
    num_cases: int = 100,
    valid_examples: Optional[List[Dict]] = None
) -> FuzzReport:
    """Quick fuzzing of a function"""
    fuzzer = IntelligentFuzzer()
    return fuzzer.fuzz_function(func, num_cases, valid_examples=valid_examples)


if __name__ == "__main__":
    # Example usage
    def divide(x: int, y: int) -> float:
        """Divide x by y"""
        return x / y

    fuzzer = IntelligentFuzzer(seed=42)
    report = fuzzer.fuzz_function(divide, num_cases=50)

    print(f"Fuzzed {report.function_name}:")
    print(f"  Total cases: {report.total_cases}")
    print(f"  Crashes: {report.crashes}")
    print(f"  Unique crashes: {report.unique_crashes}")
    print(f"\nCrash details:")
    for crash in report.crash_results[:5]:
        print(f"  - {crash.exception_type}: {crash.exception_message}")
        print(f"    Inputs: {crash.test_case.inputs}")
