"""
Language Converter Module

Converts tools and workflows between programming languages.
Supports Python → JavaScript conversion with extensibility for other languages.
"""

import ast
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


class ConversionStrategy(Enum):
    """Conversion strategy for code transformation."""
    AST_BASED = "ast"  # Abstract Syntax Tree parsing
    LLM_BASED = "llm"  # LLM-guided conversion
    HYBRID = "hybrid"  # AST + LLM for complex cases
    TEMPLATE_BASED = "template"  # Template-based generation


@dataclass
class ConversionContext:
    """Context information for code conversion."""
    source_language: Language
    target_language: Language
    tool_definition: Dict[str, Any]
    source_code: str
    tests: Optional[str] = None
    dependencies: Optional[List[str]] = None
    strategy: ConversionStrategy = ConversionStrategy.HYBRID


@dataclass
class ConversionResult:
    """Result of a language conversion."""
    success: bool
    target_code: str
    target_tests: Optional[str] = None
    target_definition: Optional[Dict[str, Any]] = None
    package_config: Optional[Dict[str, Any]] = None
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class LanguageConverter(ABC):
    """Base class for language converters."""

    def __init__(self, llm_client=None):
        """
        Initialize converter.

        Args:
            llm_client: Optional LLM client for intelligent conversion
        """
        self.llm_client = llm_client
        self.errors = []
        self.warnings = []

    @abstractmethod
    def convert_code(self, context: ConversionContext) -> ConversionResult:
        """
        Convert source code to target language.

        Args:
            context: Conversion context with source and target info

        Returns:
            ConversionResult with converted code and metadata
        """
        pass

    @abstractmethod
    def convert_tests(self, context: ConversionContext) -> str:
        """
        Convert test code to target language.

        Args:
            context: Conversion context

        Returns:
            Converted test code
        """
        pass

    def convert_tool_definition(self, tool_def: Dict[str, Any],
                                target_lang: Language) -> Dict[str, Any]:
        """
        Convert tool YAML definition for target language.

        Args:
            tool_def: Original tool definition
            target_lang: Target language

        Returns:
            Modified tool definition
        """
        converted = tool_def.copy()

        # Update executable section based on target language
        if "executable" in converted:
            if target_lang == Language.JAVASCRIPT:
                converted["executable"]["command"] = "node"
                # Update file extension in args
                if "args" in converted["executable"]:
                    converted["executable"]["args"] = [
                        arg.replace(".py", ".js")
                        for arg in converted["executable"]["args"]
                    ]
            elif target_lang == Language.TYPESCRIPT:
                converted["executable"]["command"] = "ts-node"
                if "args" in converted["executable"]:
                    converted["executable"]["args"] = [
                        arg.replace(".py", ".ts")
                        for arg in converted["executable"]["args"]
                    ]

        # Add conversion metadata
        converted["metadata"] = converted.get("metadata", {})
        converted["metadata"]["converted_from"] = "python"
        converted["metadata"]["conversion_tool"] = "language_converter"

        return converted


class PythonToJavaScriptConverter(LanguageConverter):
    """Converts Python code to JavaScript."""

    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.type_mapping = {
            "str": "string",
            "int": "number",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
            "None": "null",
            "Any": "any"
        }

    def convert_code(self, context: ConversionContext) -> ConversionResult:
        """
        Convert Python code to JavaScript.

        Uses hybrid approach:
        1. AST parsing for structure
        2. Pattern-based conversion for common constructs
        3. LLM fallback for complex logic
        """
        self.errors = []
        self.warnings = []

        try:
            # Parse Python AST
            tree = ast.parse(context.source_code)

            # Analyze code structure
            analyzer = PythonASTAnalyzer()
            analysis = analyzer.analyze(tree)

            # Convert based on strategy
            if context.strategy == ConversionStrategy.AST_BASED:
                js_code = self._convert_ast_based(tree, analysis)
            elif context.strategy == ConversionStrategy.LLM_BASED and self.llm_client:
                js_code = self._convert_llm_based(context)
            else:
                # Hybrid: AST for structure, LLM for complex parts
                js_code = self._convert_hybrid(tree, analysis, context)

            # Convert tests if provided
            js_tests = None
            if context.tests:
                js_tests = self.convert_tests(context)

            # Convert tool definition
            js_definition = None
            if context.tool_definition:
                js_definition = self.convert_tool_definition(
                    context.tool_definition,
                    Language.JAVASCRIPT
                )

            # Generate package.json
            package_config = self._generate_package_json(context, analysis)

            return ConversionResult(
                success=len(self.errors) == 0,
                target_code=js_code,
                target_tests=js_tests,
                target_definition=js_definition,
                package_config=package_config,
                errors=self.errors,
                warnings=self.warnings,
                metadata={
                    "imports": analysis.get("imports", []),
                    "functions": analysis.get("functions", []),
                    "classes": analysis.get("classes", [])
                }
            )

        except SyntaxError as e:
            self.errors.append(f"Python syntax error: {e}")
            return ConversionResult(
                success=False,
                target_code="",
                errors=self.errors
            )
        except Exception as e:
            self.errors.append(f"Conversion error: {e}")
            return ConversionResult(
                success=False,
                target_code="",
                errors=self.errors
            )

    def _convert_ast_based(self, tree: ast.AST, analysis: Dict) -> str:
        """Convert Python AST to JavaScript using pattern matching."""
        converter = PythonToJSASTConverter(self.type_mapping)
        js_code = converter.convert(tree)
        self.warnings.extend(converter.warnings)
        return js_code

    def _convert_llm_based(self, context: ConversionContext) -> str:
        """Use LLM to convert complex Python code to JavaScript."""
        if not self.llm_client:
            raise ValueError("LLM client required for LLM-based conversion")

        prompt = self._build_conversion_prompt(context)
        response = self.llm_client.generate(prompt)

        # Extract JavaScript code from response
        js_code = self._extract_code_from_llm_response(response)
        return js_code

    def _convert_hybrid(self, tree: ast.AST, analysis: Dict,
                       context: ConversionContext) -> str:
        """
        Hybrid conversion: AST for structure, LLM for complex parts.
        """
        # Start with AST-based conversion
        base_code = self._convert_ast_based(tree, analysis)

        # Identify complex patterns that need LLM assistance
        complex_patterns = self._identify_complex_patterns(tree)

        if complex_patterns and self.llm_client:
            # Use LLM to refine complex sections
            refined_code = self._refine_with_llm(base_code, complex_patterns, context)
            return refined_code

        return base_code

    def _identify_complex_patterns(self, tree: ast.AST) -> List[Dict]:
        """Identify code patterns that need LLM assistance."""
        complex_patterns = []

        for node in ast.walk(tree):
            # List comprehensions with multiple conditions
            if isinstance(node, ast.ListComp) and len(node.generators) > 1:
                complex_patterns.append({
                    "type": "complex_comprehension",
                    "node": node
                })

            # Complex lambda functions
            if isinstance(node, ast.Lambda):
                # Check if lambda body is complex
                if not isinstance(node.body, (ast.Name, ast.Constant)):
                    complex_patterns.append({
                        "type": "complex_lambda",
                        "node": node
                    })

            # Decorators
            if isinstance(node, ast.FunctionDef) and node.decorator_list:
                complex_patterns.append({
                    "type": "decorated_function",
                    "node": node
                })

            # Context managers
            if isinstance(node, ast.With):
                complex_patterns.append({
                    "type": "context_manager",
                    "node": node
                })

        return complex_patterns

    def _refine_with_llm(self, base_code: str, complex_patterns: List[Dict],
                        context: ConversionContext) -> str:
        """Use LLM to refine complex code sections."""
        if not self.llm_client:
            return base_code

        prompt = f"""
Refine this JavaScript code converted from Python. Pay special attention to these complex patterns:
{json.dumps([p["type"] for p in complex_patterns], indent=2)}

Original Python:
```python
{context.source_code}
```

Initial JavaScript conversion:
```javascript
{base_code}
```

Please provide an improved JavaScript version that:
1. Handles the complex patterns correctly
2. Maintains the original functionality
3. Follows JavaScript best practices
4. Preserves error handling
5. Maintains the same input/output contract
"""

        response = self.llm_client.generate(prompt)
        refined_code = self._extract_code_from_llm_response(response)
        return refined_code

    def _build_conversion_prompt(self, context: ConversionContext) -> str:
        """Build LLM prompt for code conversion."""
        prompt = f"""
Convert this Python code to JavaScript while maintaining functionality and contracts.

Tool: {context.tool_definition.get('name', 'Unknown')}
Description: {context.tool_definition.get('description', '')}

Python Code:
```python
{context.source_code}
```
"""

        if context.tests:
            prompt += f"""
Existing Tests:
```python
{context.tests}
```
"""

        prompt += """
Requirements:
1. Convert to modern JavaScript (ES6+)
2. Maintain the same input/output contract
3. Preserve error handling and validation
4. Use async/await for asynchronous operations
5. Include proper type hints in JSDoc comments
6. Follow JavaScript best practices

Provide the converted JavaScript code.
"""
        return prompt

    def _extract_code_from_llm_response(self, response: str) -> str:
        """Extract code block from LLM response."""
        # Look for ```javascript or ```js code blocks
        pattern = r"```(?:javascript|js)\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Fallback: return the whole response if no code block found
        return response.strip()

    def convert_tests(self, context: ConversionContext) -> str:
        """
        Convert Python pytest tests to JavaScript Jest tests.
        """
        if not context.tests:
            return ""

        # Use pattern-based conversion for common pytest patterns
        js_tests = self._convert_pytest_to_jest(context.tests)

        # If LLM available, refine the conversion
        if self.llm_client:
            js_tests = self._refine_tests_with_llm(context.tests, js_tests)

        return js_tests

    def _convert_pytest_to_jest(self, pytest_code: str) -> str:
        """Convert pytest code to Jest using pattern matching."""
        js_test = pytest_code

        # Convert imports
        js_test = re.sub(r"import pytest", "// Jest testing framework", js_test)
        js_test = re.sub(r"from .* import .*", "// Converted imports", js_test)

        # Convert test functions
        js_test = re.sub(r"def (test_\w+)\((.*?)\):",
                        r"test('\1', () => {", js_test)

        # Convert assertions
        js_test = re.sub(r"assert (.*) == (.*)",
                        r"expect(\1).toBe(\2);", js_test)
        js_test = re.sub(r"assert (.*)",
                        r"expect(\1).toBeTruthy();", js_test)

        # Convert fixtures to beforeEach
        js_test = re.sub(r"@pytest\.fixture", "beforeEach(() => {", js_test)

        return js_test

    def _refine_tests_with_llm(self, pytest_code: str, jest_code: str) -> str:
        """Use LLM to refine test conversion."""
        if not self.llm_client:
            return jest_code

        prompt = f"""
Convert these Python pytest tests to JavaScript Jest tests.

Original pytest code:
```python
{pytest_code}
```

Initial conversion:
```javascript
{jest_code}
```

Provide improved Jest tests that:
1. Properly handle async operations
2. Use Jest matchers correctly
3. Set up and tear down test fixtures
4. Maintain test coverage
"""

        response = self.llm_client.generate(prompt)
        refined_tests = self._extract_code_from_llm_response(response)
        return refined_tests

    def _generate_package_json(self, context: ConversionContext,
                               analysis: Dict) -> Dict[str, Any]:
        """Generate package.json for the converted JavaScript tool."""
        tool_def = context.tool_definition

        # Map Python dependencies to JavaScript equivalents
        js_dependencies = self._map_dependencies(
            context.dependencies or []
        )

        package_json = {
            "name": tool_def.get("name", "converted-tool").lower().replace(" ", "-"),
            "version": tool_def.get("version", "1.0.0"),
            "description": tool_def.get("description", ""),
            "main": "index.js",
            "scripts": {
                "start": "node index.js",
                "test": "jest"
            },
            "dependencies": js_dependencies,
            "devDependencies": {
                "jest": "^29.0.0"
            },
            "keywords": tool_def.get("tags", []),
            "metadata": {
                "converted_from": "python",
                "original_tool_id": tool_def.get("tool_id"),
                "conversion_date": ""  # Will be filled at runtime
            }
        }

        return package_json

    def _map_dependencies(self, python_deps: List[str]) -> Dict[str, str]:
        """Map Python dependencies to JavaScript equivalents."""
        # Common Python → JavaScript dependency mappings
        dep_mapping = {
            "requests": "axios",
            "numpy": "mathjs",
            "pandas": "danfojs",
            "beautifulsoup4": "cheerio",
            "pytest": "jest",
            "pyyaml": "js-yaml",
            "python-dotenv": "dotenv",
            "aiohttp": "axios",
            "fastapi": "express",
            "pydantic": "joi",
            "sqlalchemy": "sequelize",
            "redis": "redis",
            "pillow": "sharp"
        }

        js_deps = {}

        for dep in python_deps:
            # Parse dependency (handle version specifiers)
            dep_name = re.split(r"[><=!]", dep)[0].strip().lower()

            if dep_name in dep_mapping:
                js_deps[dep_mapping[dep_name]] = "latest"
            else:
                self.warnings.append(
                    f"No JavaScript equivalent found for Python package: {dep_name}"
                )

        return js_deps


class PythonASTAnalyzer:
    """Analyzes Python AST to extract structural information."""

    def analyze(self, tree: ast.AST) -> Dict[str, Any]:
        """
        Analyze Python AST and extract key information.

        Returns:
            Dictionary with imports, functions, classes, etc.
        """
        analysis = {
            "imports": [],
            "functions": [],
            "classes": [],
            "global_vars": [],
            "async_functions": [],
            "has_main": False
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    analysis["imports"].append(f"{module}.{alias.name}")

            elif isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "returns": ast.unparse(node.returns) if node.returns else None,
                    "is_async": False,
                    "decorators": [ast.unparse(d) for d in node.decorator_list]
                }
                analysis["functions"].append(func_info)

                if node.name == "main":
                    analysis["has_main"] = True

            elif isinstance(node, ast.AsyncFunctionDef):
                func_info = {
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "returns": ast.unparse(node.returns) if node.returns else None,
                    "is_async": True,
                    "decorators": [ast.unparse(d) for d in node.decorator_list]
                }
                analysis["functions"].append(func_info)
                analysis["async_functions"].append(node.name)

            elif isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "bases": [ast.unparse(base) for base in node.bases],
                    "methods": []
                }

                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        class_info["methods"].append(item.name)

                analysis["classes"].append(class_info)

            elif isinstance(node, ast.Assign):
                # Global variable assignments
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        analysis["global_vars"].append(target.id)

        return analysis


class PythonToJSASTConverter:
    """Converts Python AST nodes to JavaScript code."""

    def __init__(self, type_mapping: Dict[str, str]):
        self.type_mapping = type_mapping
        self.warnings = []
        self.indent_level = 0

    def convert(self, tree: ast.AST) -> str:
        """Convert Python AST to JavaScript code."""
        js_lines = []

        # Add header comment
        js_lines.append("// Converted from Python by DiSE Language Converter")
        js_lines.append("")

        # Process top-level nodes
        for node in ast.iter_child_nodes(tree):
            js_code = self._convert_node(node)
            if js_code:
                js_lines.append(js_code)
                js_lines.append("")

        return "\n".join(js_lines)

    def _convert_node(self, node: ast.AST) -> str:
        """Convert a single AST node to JavaScript."""
        if isinstance(node, ast.Import):
            return self._convert_import(node)
        elif isinstance(node, ast.ImportFrom):
            return self._convert_import_from(node)
        elif isinstance(node, ast.FunctionDef):
            return self._convert_function(node)
        elif isinstance(node, ast.AsyncFunctionDef):
            return self._convert_async_function(node)
        elif isinstance(node, ast.ClassDef):
            return self._convert_class(node)
        elif isinstance(node, ast.Assign):
            return self._convert_assignment(node)
        elif isinstance(node, ast.If):
            return self._convert_if(node)
        elif isinstance(node, ast.For):
            return self._convert_for(node)
        elif isinstance(node, ast.While):
            return self._convert_while(node)
        elif isinstance(node, ast.Return):
            return self._convert_return(node)
        elif isinstance(node, ast.Expr):
            return self._convert_expr(node)
        else:
            self.warnings.append(f"Unsupported node type: {type(node).__name__}")
            return f"// TODO: Convert {type(node).__name__}"

    def _convert_import(self, node: ast.Import) -> str:
        """Convert import statement."""
        imports = []
        for alias in node.names:
            name = alias.name
            as_name = alias.asname or alias.name
            imports.append(f"// import {name} as {as_name}")
        return "\n".join(imports)

    def _convert_import_from(self, node: ast.ImportFrom) -> str:
        """Convert from...import statement."""
        module = node.module or ""
        names = [alias.name for alias in node.names]
        return f"// from {module} import {', '.join(names)}"

    def _convert_function(self, node: ast.FunctionDef) -> str:
        """Convert function definition."""
        # Function signature
        args = [arg.arg for arg in node.args.args]
        signature = f"function {node.name}({', '.join(args)}) {{"

        # Function body
        body_lines = [signature]
        for stmt in node.body:
            stmt_code = self._convert_node(stmt)
            if stmt_code:
                body_lines.append(f"  {stmt_code}")

        body_lines.append("}")

        return "\n".join(body_lines)

    def _convert_async_function(self, node: ast.AsyncFunctionDef) -> str:
        """Convert async function definition."""
        args = [arg.arg for arg in node.args.args]
        signature = f"async function {node.name}({', '.join(args)}) {{"

        body_lines = [signature]
        for stmt in node.body:
            stmt_code = self._convert_node(stmt)
            if stmt_code:
                body_lines.append(f"  {stmt_code}")

        body_lines.append("}")

        return "\n".join(body_lines)

    def _convert_class(self, node: ast.ClassDef) -> str:
        """Convert class definition."""
        class_lines = [f"class {node.name} {{"]

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_code = self._convert_method(item)
                class_lines.append(f"  {method_code}")

        class_lines.append("}")

        return "\n".join(class_lines)

    def _convert_method(self, node: ast.FunctionDef) -> str:
        """Convert class method."""
        args = [arg.arg for arg in node.args.args if arg.arg != "self"]
        signature = f"{node.name}({', '.join(args)}) {{"

        body_lines = [signature]
        for stmt in node.body:
            stmt_code = self._convert_node(stmt)
            if stmt_code:
                body_lines.append(f"  {stmt_code}")

        body_lines.append("}")

        return "\n".join(body_lines)

    def _convert_assignment(self, node: ast.Assign) -> str:
        """Convert assignment statement."""
        targets = [ast.unparse(t) for t in node.targets]
        value = ast.unparse(node.value)

        # Simple conversion
        return f"let {targets[0]} = {value};"

    def _convert_if(self, node: ast.If) -> str:
        """Convert if statement."""
        test = ast.unparse(node.test)
        if_lines = [f"if ({test}) {{"]

        for stmt in node.body:
            stmt_code = self._convert_node(stmt)
            if stmt_code:
                if_lines.append(f"  {stmt_code}")

        if node.orelse:
            if_lines.append("} else {")
            for stmt in node.orelse:
                stmt_code = self._convert_node(stmt)
                if stmt_code:
                    if_lines.append(f"  {stmt_code}")

        if_lines.append("}")

        return "\n".join(if_lines)

    def _convert_for(self, node: ast.For) -> str:
        """Convert for loop."""
        target = ast.unparse(node.target)
        iter_expr = ast.unparse(node.iter)

        for_lines = [f"for (const {target} of {iter_expr}) {{"]

        for stmt in node.body:
            stmt_code = self._convert_node(stmt)
            if stmt_code:
                for_lines.append(f"  {stmt_code}")

        for_lines.append("}")

        return "\n".join(for_lines)

    def _convert_while(self, node: ast.While) -> str:
        """Convert while loop."""
        test = ast.unparse(node.test)
        while_lines = [f"while ({test}) {{"]

        for stmt in node.body:
            stmt_code = self._convert_node(stmt)
            if stmt_code:
                while_lines.append(f"  {stmt_code}")

        while_lines.append("}")

        return "\n".join(while_lines)

    def _convert_return(self, node: ast.Return) -> str:
        """Convert return statement."""
        if node.value:
            value = ast.unparse(node.value)
            return f"return {value};"
        return "return;"

    def _convert_expr(self, node: ast.Expr) -> str:
        """Convert expression statement."""
        return ast.unparse(node.value) + ";"


def create_converter(source_lang: Language, target_lang: Language,
                     llm_client=None) -> LanguageConverter:
    """
    Factory function to create appropriate language converter.

    Args:
        source_lang: Source programming language
        target_lang: Target programming language
        llm_client: Optional LLM client for intelligent conversion

    Returns:
        LanguageConverter instance
    """
    if source_lang == Language.PYTHON and target_lang == Language.JAVASCRIPT:
        return PythonToJavaScriptConverter(llm_client)
    elif source_lang == Language.PYTHON and target_lang == Language.TYPESCRIPT:
        # TODO: Implement TypeScript converter
        raise NotImplementedError("Python to TypeScript conversion not yet implemented")
    else:
        raise ValueError(f"Conversion from {source_lang} to {target_lang} not supported")
