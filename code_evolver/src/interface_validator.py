"""
Static Interface Validator
Validates Python code interfaces without executing the code.
"""
import ast
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InterfaceValidator:
    """Validates code interfaces using static analysis."""

    @staticmethod
    def validate_file(file_path: Path, check_imports: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate a Python file for basic interface requirements.

        Args:
            file_path: Path to the Python file to validate
            check_imports: Whether to validate imports can be resolved

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            # Parse the code into an AST
            try:
                tree = ast.parse(code, filename=str(file_path))
            except SyntaxError as e:
                issues.append(f"Syntax error: {e}")
                return False, issues

            # Check for main() function
            has_main = InterfaceValidator._has_function(tree, 'main')
            if not has_main:
                issues.append("Missing main() function")

            # Check for proper JSON handling
            imports = InterfaceValidator._get_imports(tree)
            if 'json' not in imports and 'sys' not in imports:
                issues.append("Missing 'import json' or 'import sys'")

            # Check if __name__ == '__main__' block exists
            has_main_block = InterfaceValidator._has_main_block(tree)
            if not has_main_block:
                issues.append("Missing if __name__ == '__main__': block")

            # Check for phantom imports (imports that don't exist)
            if check_imports:
                phantom_imports = InterfaceValidator._check_phantom_imports(tree, file_path)
                if phantom_imports:
                    issues.extend(phantom_imports)

            is_valid = len(issues) == 0
            return is_valid, issues

        except Exception as e:
            logger.error(f"Error validating {file_path}: {e}")
            issues.append(f"Validation error: {e}")
            return False, issues

    @staticmethod
    def _has_function(tree: ast.AST, function_name: str) -> bool:
        """Check if a function with the given name exists in the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return True
        return False

    @staticmethod
    def _get_imports(tree: ast.AST) -> set:
        """Get all imported module names from the AST."""
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        return imports

    @staticmethod
    def _has_main_block(tree: ast.AST) -> bool:
        """Check if the code has a if __name__ == '__main__': block."""
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if this is the __name__ == '__main__' pattern
                test = node.test
                if isinstance(test, ast.Compare):
                    if (isinstance(test.left, ast.Name) and test.left.id == '__name__' and
                        any(isinstance(comp, ast.Str) and comp.s == '__main__' or
                            isinstance(comp, ast.Constant) and comp.value == '__main__'
                            for comp in test.comparators)):
                        return True
        return False

    @staticmethod
    def _check_phantom_imports(tree: ast.AST, file_path: Path) -> List[str]:
        """
        Check for imports that can't be resolved (phantom imports).
        Returns list of issues for imports that don't exist.
        """
        import importlib.util
        import sys

        issues = []

        # Known stdlib modules (partial list of common ones)
        stdlib_modules = {
            'abc', 'ast', 'asyncio', 'base64', 'collections', 'copy', 'csv',
            'datetime', 'decimal', 'enum', 'functools', 'hashlib', 'io',
            'itertools', 'json', 'logging', 'math', 'os', 'pathlib', 'random',
            're', 'shutil', 'sqlite3', 'string', 'subprocess', 'sys', 'tempfile',
            'threading', 'time', 'typing', 'unittest', 'urllib', 'uuid', 'warnings'
        }

        # Get directory of the file being validated
        file_dir = file_path.parent

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]

                    # Skip stdlib modules
                    if module_name in stdlib_modules:
                        continue

                    # Check if it's a local file
                    local_file = file_dir / f"{module_name}.py"
                    if local_file.exists():
                        continue

                    # Check if it's in parent directory (common for node_runtime)
                    parent_file = file_dir.parent / f"{module_name}.py"
                    if parent_file.exists():
                        # This exists but won't be importable without path setup
                        issues.append(
                            f"Import '{module_name}' exists in parent directory but is not in import path. "
                            f"Add 'sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))' before import."
                        )
                        continue

                    # Try to import it (this checks if it's installed via pip)
                    spec = importlib.util.find_spec(module_name)
                    if spec is None:
                        issues.append(
                            f"Phantom import: '{module_name}' cannot be found. "
                            f"Not in stdlib, not a local file, not installed via pip."
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]

                    # Skip stdlib modules
                    if module_name in stdlib_modules:
                        continue

                    # Check if it's a local file
                    local_file = file_dir / f"{module_name}.py"
                    if local_file.exists():
                        continue

                    # Check if it's in parent directory
                    parent_file = file_dir.parent / f"{module_name}.py"
                    if parent_file.exists():
                        issues.append(
                            f"Import 'from {module_name} ...' exists in parent directory but is not in import path. "
                            f"Add 'sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))' before import."
                        )
                        continue

                    # Try to import it
                    spec = importlib.util.find_spec(module_name)
                    if spec is None:
                        issues.append(
                            f"Phantom import: 'from {module_name} ...' cannot be found. "
                            f"Not in stdlib, not a local file, not installed via pip."
                        )

        return issues

    @staticmethod
    def validate_function_signature(file_path: Path, function_name: str,
                                  expected_params: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        """
        Validate a specific function signature.

        Args:
            file_path: Path to the Python file
            function_name: Name of the function to check
            expected_params: Expected parameter names (optional)

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            tree = ast.parse(code, filename=str(file_path))

            # Find the function
            func_node = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    func_node = node
                    break

            if not func_node:
                issues.append(f"Function '{function_name}' not found")
                return False, issues

            # Check parameters if specified
            if expected_params is not None:
                actual_params = [arg.arg for arg in func_node.args.args]
                if actual_params != expected_params:
                    issues.append(
                        f"Function signature mismatch. Expected params: {expected_params}, "
                        f"got: {actual_params}"
                    )

            is_valid = len(issues) == 0
            return is_valid, issues

        except Exception as e:
            logger.error(f"Error validating function signature in {file_path}: {e}")
            issues.append(f"Validation error: {e}")
            return False, issues

    @staticmethod
    def quick_validate_node(node_path: Path) -> bool:
        """
        Quick validation for a node directory.
        Checks main.py for basic interface requirements.

        Args:
            node_path: Path to the node directory

        Returns:
            True if validation passes, False otherwise
        """
        main_file = node_path / "main.py"

        if not main_file.exists():
            logger.error(f"main.py not found in {node_path}")
            return False

        is_valid, issues = InterfaceValidator.validate_file(main_file)

        if not is_valid:
            logger.warning(f"Interface validation failed for {node_path}:")
            for issue in issues:
                logger.warning(f"  - {issue}")

        return is_valid


def main():
    """CLI interface for the validator."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python interface_validator.py <path_to_python_file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    is_valid, issues = InterfaceValidator.validate_file(file_path)

    if is_valid:
        print(f"[PASS] {file_path} passed interface validation")
        sys.exit(0)
    else:
        print(f"[FAIL] {file_path} failed interface validation:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)


if __name__ == "__main__":
    main()
