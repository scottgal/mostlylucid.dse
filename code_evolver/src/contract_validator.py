"""
Contract Validator - Validates Code Against Contracts

This module provides validators for checking code against contract rules:
- AST-based validation for structural requirements
- Pattern matching for required/forbidden patterns
- Metric calculation for complexity, length, etc.
- Custom validators for specific requirements
"""

from __future__ import annotations

import ast
import re
import logging
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from .code_contract import (
    CodeContract,
    ContractRule,
    ContractViolation,
    ContractSeverity,
    ContractType,
    ComplianceReport
)

logger = logging.getLogger(__name__)


class ContractValidator:
    """Validates Python code against contract rules."""

    def __init__(self):
        """Initialize validator with custom validators registry."""
        self.custom_validators: Dict[str, Callable] = {}
        self._register_builtin_validators()

    def _register_builtin_validators(self):
        """Register built-in validators."""
        self.custom_validators['has_logging'] = self._validate_has_logging
        self.custom_validators['has_call_tool_wrapper'] = self._validate_has_call_tool_wrapper
        self.custom_validators['max_function_length'] = self._validate_max_function_length
        self.custom_validators['forbidden_library'] = self._validate_forbidden_library
        self.custom_validators['required_import'] = self._validate_required_import
        self.custom_validators['cyclomatic_complexity'] = self._validate_cyclomatic_complexity
        self.custom_validators['has_docstring'] = self._validate_has_docstring
        self.custom_validators['has_type_hints'] = self._validate_has_type_hints

    def register_validator(self, name: str, validator: Callable):
        """
        Register a custom validator function.

        Args:
            name: Validator name
            validator: Function(code: str, rule: ContractRule) -> List[ContractViolation]
        """
        self.custom_validators[name] = validator

    def validate(self, code: str, contract: CodeContract, code_path: str = "<string>") -> ComplianceReport:
        """
        Validate code against a contract.

        Args:
            code: Python source code to validate
            contract: Contract to validate against
            code_path: Path/identifier for the code

        Returns:
            ComplianceReport with violations and passed rules
        """
        violations: List[ContractViolation] = []
        passed_rules: List[ContractRule] = []

        for rule in contract.rules:
            rule_violations = self._validate_rule(code, rule, code_path)

            if rule_violations:
                violations.extend(rule_violations)
            else:
                passed_rules.append(rule)

        return ComplianceReport(
            contract=contract,
            code_path=code_path,
            violations=violations,
            passed_rules=passed_rules
        )

    def _validate_rule(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate a single rule against code."""
        # Check if custom validator exists
        if rule.validator and rule.validator in self.custom_validators:
            validator_func = self.custom_validators[rule.validator]
            return validator_func(code, rule, code_path)

        # Default validation based on rule type
        if rule.rule_type == ContractType.PATTERN:
            return self._validate_pattern_rule(code, rule, code_path)
        elif rule.rule_type == ContractType.METRIC:
            return self._validate_metric_rule(code, rule, code_path)
        elif rule.rule_type == ContractType.LIBRARY:
            return self._validate_library_rule(code, rule, code_path)
        elif rule.rule_type == ContractType.STRUCTURAL:
            return self._validate_structural_rule(code, rule, code_path)
        elif rule.rule_type == ContractType.DOCUMENTATION:
            return self._validate_documentation_rule(code, rule, code_path)
        else:
            logger.warning(f"No validator for rule type: {rule.rule_type}")
            return []

    def _validate_pattern_rule(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate pattern-based rules."""
        if not rule.pattern:
            return []

        violations = []
        pattern = re.compile(rule.pattern, re.MULTILINE)
        matches = list(pattern.finditer(code))

        if rule.required and not matches:
            # Pattern is required but not found
            violations.append(ContractViolation(
                rule=rule,
                location=code_path,
                message=f"Required pattern not found: {rule.pattern}",
                suggestion=f"Add code matching pattern: {rule.pattern}"
            ))
        elif not rule.required and matches:
            # Pattern is forbidden but found
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                violations.append(ContractViolation(
                    rule=rule,
                    location=code_path,
                    line_number=line_num,
                    message=f"Forbidden pattern found: {rule.pattern}",
                    code_snippet=match.group(0),
                    suggestion=f"Remove or refactor code matching: {rule.pattern}"
                ))

        return violations

    def _validate_metric_rule(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate metric-based rules (using validator config to specify metric)."""
        # This would call specific metric validators based on config
        return []

    def _validate_library_rule(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate library/import rules."""
        if not rule.pattern:
            return []

        violations = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            violations.append(ContractViolation(
                rule=rule,
                location=code_path,
                line_number=e.lineno,
                message=f"Syntax error in code: {e.msg}"
            ))
            return violations

        # Find all imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append((node.module, node.lineno))

        pattern = re.compile(rule.pattern)

        for import_name, line_num in imports:
            if pattern.search(import_name):
                if not rule.required:
                    # Forbidden import found
                    violations.append(ContractViolation(
                        rule=rule,
                        location=code_path,
                        line_number=line_num,
                        message=f"Forbidden library import: {import_name}",
                        suggestion=f"Remove import of {import_name} or use an alternative"
                    ))

        if rule.required and not any(pattern.search(imp[0]) for imp in imports):
            # Required import not found
            violations.append(ContractViolation(
                rule=rule,
                location=code_path,
                message=f"Required library import not found: {rule.pattern}",
                suggestion=f"Add import matching: {rule.pattern}"
            ))

        return violations

    def _validate_structural_rule(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate structural rules (AST-based)."""
        # Use custom validators for structural rules
        return []

    def _validate_documentation_rule(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate documentation rules."""
        # Use custom validators for documentation rules
        return []

    # Built-in custom validators

    def _validate_has_logging(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate that code has logging statements."""
        violations = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []  # Will be caught by other validators

        # Check for logging import
        has_logging_import = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'logging':
                        has_logging_import = True
                        break
            elif isinstance(node, ast.ImportFrom):
                if node.module == 'logging':
                    has_logging_import = True
                    break

        if not has_logging_import:
            violations.append(ContractViolation(
                rule=rule,
                location=code_path,
                message="Missing logging import",
                suggestion="Add: import logging"
            ))

        # Check for logger creation and usage
        has_logger = False
        has_log_calls = False

        for node in ast.walk(tree):
            # Check for logger = logging.getLogger(...)
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Attribute):
                        if (isinstance(node.value.func.value, ast.Name) and
                            node.value.func.value.id == 'logging' and
                            node.value.func.attr == 'getLogger'):
                            has_logger = True

            # Check for logger.debug/info/warning/error/critical calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['debug', 'info', 'warning', 'error', 'critical']:
                        has_log_calls = True

        min_log_calls = rule.validator_config.get('min_calls', 1)

        if not has_logger and min_log_calls > 0:
            violations.append(ContractViolation(
                rule=rule,
                location=code_path,
                message="No logger instance created",
                suggestion="Add: logger = logging.getLogger(__name__)"
            ))

        if not has_log_calls and min_log_calls > 0:
            violations.append(ContractViolation(
                rule=rule,
                location=code_path,
                message="No logging calls found",
                suggestion="Add logger calls (e.g., logger.info(), logger.error())"
            ))

        return violations

    def _validate_has_call_tool_wrapper(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate that functions have call_tool wrappers at start/end."""
        violations = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        # Find all function definitions
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for func in functions:
            # Skip private/magic methods if configured
            if rule.validator_config.get('skip_private', True):
                if func.name.startswith('_'):
                    continue

            # Check if function has call_tool at start and end
            if not func.body:
                continue

            has_start_call = False
            has_end_call = False

            # Check first statement
            first_stmt = func.body[0]
            if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Call):
                if isinstance(first_stmt.value.func, ast.Name) and 'call_tool' in first_stmt.value.func.id:
                    has_start_call = True

            # Check last statement(s) - could be before return
            for stmt in func.body[-3:]:  # Check last 3 statements
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    if isinstance(stmt.value.func, ast.Name) and 'call_tool' in stmt.value.func.id:
                        has_end_call = True
                        break

            if not has_start_call:
                violations.append(ContractViolation(
                    rule=rule,
                    location=code_path,
                    line_number=func.lineno,
                    message=f"Function '{func.name}' missing call_tool at start",
                    suggestion="Add call_tool() as first statement in function"
                ))

            if not has_end_call:
                violations.append(ContractViolation(
                    rule=rule,
                    location=code_path,
                    line_number=func.lineno,
                    message=f"Function '{func.name}' missing call_tool at end",
                    suggestion="Add call_tool() before return statement"
                ))

        return violations

    def _validate_max_function_length(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate that functions don't exceed max length."""
        violations = []
        max_lines = int(rule.max_value or rule.validator_config.get('max_lines', 50))

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for func in functions:
            # Calculate function length
            if not func.body:
                continue

            first_line = func.lineno
            last_line = max(
                getattr(node, 'lineno', func.lineno)
                for node in ast.walk(func)
                if hasattr(node, 'lineno')
            )
            func_length = last_line - first_line + 1

            if func_length > max_lines:
                violations.append(ContractViolation(
                    rule=rule,
                    location=code_path,
                    line_number=func.lineno,
                    message=f"Function '{func.name}' is {func_length} lines (max: {max_lines})",
                    suggestion=f"Refactor '{func.name}' into smaller functions or extract to a tool"
                ))

        return violations

    def _validate_forbidden_library(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate that forbidden libraries are not used."""
        # This is handled by _validate_library_rule
        return self._validate_library_rule(code, rule, code_path)

    def _validate_required_import(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate that required imports are present."""
        # This is handled by _validate_library_rule
        return self._validate_library_rule(code, rule, code_path)

    def _validate_cyclomatic_complexity(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate cyclomatic complexity of functions."""
        violations = []
        max_complexity = int(rule.max_value or rule.validator_config.get('max_complexity', 10))

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for func in functions:
            complexity = self._calculate_complexity(func)

            if complexity > max_complexity:
                violations.append(ContractViolation(
                    rule=rule,
                    location=code_path,
                    line_number=func.lineno,
                    message=f"Function '{func.name}' has complexity {complexity} (max: {max_complexity})",
                    suggestion=f"Simplify '{func.name}' by reducing branches and loops"
                ))

        return violations

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of an AST node."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Each decision point adds 1
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _validate_has_docstring(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate that functions/classes have docstrings."""
        violations = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        # Check module docstring
        if rule.validator_config.get('require_module_docstring', True):
            if not ast.get_docstring(tree):
                violations.append(ContractViolation(
                    rule=rule,
                    location=code_path,
                    line_number=1,
                    message="Module missing docstring",
                    suggestion="Add module-level docstring at the top of the file"
                ))

        # Check functions and classes
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                # Skip private if configured
                if rule.validator_config.get('skip_private', True):
                    if node.name.startswith('_') and not node.name.startswith('__'):
                        continue

                if not ast.get_docstring(node):
                    node_type = "Function" if isinstance(node, ast.FunctionDef) else "Class"
                    violations.append(ContractViolation(
                        rule=rule,
                        location=code_path,
                        line_number=node.lineno,
                        message=f"{node_type} '{node.name}' missing docstring",
                        suggestion=f"Add docstring to {node_type.lower()} '{node.name}'"
                    ))

        return violations

    def _validate_has_type_hints(self, code: str, rule: ContractRule, code_path: str) -> List[ContractViolation]:
        """Validate that functions have type hints."""
        violations = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for func in functions:
            # Skip private if configured
            if rule.validator_config.get('skip_private', True):
                if func.name.startswith('_') and not func.name.startswith('__'):
                    continue

            # Check return type hint
            if not func.returns and rule.validator_config.get('require_return_type', True):
                violations.append(ContractViolation(
                    rule=rule,
                    location=code_path,
                    line_number=func.lineno,
                    message=f"Function '{func.name}' missing return type hint",
                    suggestion=f"Add return type hint to function '{func.name}'"
                ))

            # Check parameter type hints
            if rule.validator_config.get('require_param_types', True):
                for arg in func.args.args:
                    if arg.arg != 'self' and not arg.annotation:
                        violations.append(ContractViolation(
                            rule=rule,
                            location=code_path,
                            line_number=func.lineno,
                            message=f"Function '{func.name}' parameter '{arg.arg}' missing type hint",
                            suggestion=f"Add type hint for parameter '{arg.arg}'"
                        ))

        return violations
