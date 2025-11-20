"""
Unit tests for the language converter module.
"""

import ast
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from language_converter import (
    Language,
    ConversionStrategy,
    ConversionContext,
    ConversionResult,
    PythonToJavaScriptConverter,
    PythonASTAnalyzer,
    PythonToJSASTConverter,
    create_converter
)


class TestLanguageEnum:
    """Test Language enum."""

    def test_language_values(self):
        """Test language enum values."""
        assert Language.PYTHON.value == "python"
        assert Language.JAVASCRIPT.value == "javascript"
        assert Language.TYPESCRIPT.value == "typescript"


class TestConversionStrategy:
    """Test ConversionStrategy enum."""

    def test_strategy_values(self):
        """Test conversion strategy values."""
        assert ConversionStrategy.AST_BASED.value == "ast"
        assert ConversionStrategy.LLM_BASED.value == "llm"
        assert ConversionStrategy.HYBRID.value == "hybrid"
        assert ConversionStrategy.TEMPLATE_BASED.value == "template"


class TestConversionContext:
    """Test ConversionContext dataclass."""

    def test_context_creation(self):
        """Test creating conversion context."""
        context = ConversionContext(
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            tool_definition={"name": "test"},
            source_code="def hello(): pass",
            strategy=ConversionStrategy.HYBRID
        )

        assert context.source_language == Language.PYTHON
        assert context.target_language == Language.JAVASCRIPT
        assert context.tool_definition["name"] == "test"
        assert context.source_code == "def hello(): pass"
        assert context.strategy == ConversionStrategy.HYBRID


class TestConversionResult:
    """Test ConversionResult dataclass."""

    def test_result_creation(self):
        """Test creating conversion result."""
        result = ConversionResult(
            success=True,
            target_code="function hello() {}",
            errors=[],
            warnings=[]
        )

        assert result.success is True
        assert result.target_code == "function hello() {}"
        assert result.errors == []
        assert result.warnings == []


class TestPythonASTAnalyzer:
    """Test Python AST analyzer."""

    def test_analyze_imports(self):
        """Test analyzing imports."""
        code = """
import os
from pathlib import Path
"""
        tree = ast.parse(code)
        analyzer = PythonASTAnalyzer()
        analysis = analyzer.analyze(tree)

        assert "os" in analysis["imports"]
        assert "pathlib.Path" in analysis["imports"]

    def test_analyze_functions(self):
        """Test analyzing function definitions."""
        code = """
def simple_func(x, y):
    return x + y

async def async_func(z):
    return z * 2
"""
        tree = ast.parse(code)
        analyzer = PythonASTAnalyzer()
        analysis = analyzer.analyze(tree)

        assert len(analysis["functions"]) == 2
        assert analysis["functions"][0]["name"] == "simple_func"
        assert analysis["functions"][0]["args"] == ["x", "y"]
        assert analysis["functions"][0]["is_async"] is False

        assert analysis["functions"][1]["name"] == "async_func"
        assert analysis["functions"][1]["is_async"] is True
        assert "async_func" in analysis["async_functions"]

    def test_analyze_classes(self):
        """Test analyzing class definitions."""
        code = """
class MyClass:
    def __init__(self):
        self.value = 0

    def method(self):
        pass
"""
        tree = ast.parse(code)
        analyzer = PythonASTAnalyzer()
        analysis = analyzer.analyze(tree)

        assert len(analysis["classes"]) == 1
        assert analysis["classes"][0]["name"] == "MyClass"
        assert "__init__" in analysis["classes"][0]["methods"]
        assert "method" in analysis["classes"][0]["methods"]

    def test_analyze_has_main(self):
        """Test detecting main function."""
        code = """
def main():
    print("Hello")

if __name__ == "__main__":
    main()
"""
        tree = ast.parse(code)
        analyzer = PythonASTAnalyzer()
        analysis = analyzer.analyze(tree)

        assert analysis["has_main"] is True


class TestPythonToJSASTConverter:
    """Test Python to JavaScript AST converter."""

    def test_convert_simple_function(self):
        """Test converting a simple function."""
        code = """
def add(a, b):
    return a + b
"""
        tree = ast.parse(code)
        converter = PythonToJSASTConverter(type_mapping={"str": "string"})
        js_code = converter.convert(tree)

        assert "function add(a, b)" in js_code
        assert "return a + b;" in js_code

    def test_convert_async_function(self):
        """Test converting async function."""
        code = """
async def fetch_data(url):
    return await get(url)
"""
        tree = ast.parse(code)
        converter = PythonToJSASTConverter(type_mapping={})
        js_code = converter.convert(tree)

        assert "async function fetch_data(url)" in js_code

    def test_convert_if_statement(self):
        """Test converting if statement."""
        code = """
if x > 0:
    print("positive")
else:
    print("negative")
"""
        tree = ast.parse(code)
        converter = PythonToJSASTConverter(type_mapping={})
        js_code = converter.convert(tree)

        assert "if (x > 0)" in js_code
        assert "} else {" in js_code

    def test_convert_for_loop(self):
        """Test converting for loop."""
        code = """
for item in items:
    process(item)
"""
        tree = ast.parse(code)
        converter = PythonToJSASTConverter(type_mapping={})
        js_code = converter.convert(tree)

        assert "for (const item of items)" in js_code


class TestPythonToJavaScriptConverter:
    """Test Python to JavaScript converter."""

    def test_converter_initialization(self):
        """Test converter initialization."""
        converter = PythonToJavaScriptConverter()

        assert converter.llm_client is None
        assert "str" in converter.type_mapping
        assert converter.type_mapping["str"] == "string"
        assert converter.type_mapping["int"] == "number"

    def test_convert_simple_code(self):
        """Test converting simple Python code."""
        converter = PythonToJavaScriptConverter()

        context = ConversionContext(
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            tool_definition={"name": "test_tool"},
            source_code="""
def greet(name):
    return f"Hello, {name}!"
""",
            strategy=ConversionStrategy.AST_BASED
        )

        result = converter.convert_code(context)

        assert result.success is True
        assert "function greet(name)" in result.target_code
        assert result.errors == []

    def test_convert_with_syntax_error(self):
        """Test handling syntax errors."""
        converter = PythonToJavaScriptConverter()

        context = ConversionContext(
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            tool_definition={"name": "test_tool"},
            source_code="def invalid syntax here",
            strategy=ConversionStrategy.AST_BASED
        )

        result = converter.convert_code(context)

        assert result.success is False
        assert len(result.errors) > 0
        assert "syntax error" in result.errors[0].lower()

    def test_identify_complex_patterns(self):
        """Test identifying complex code patterns."""
        converter = PythonToJavaScriptConverter()

        code = """
result = [x*2 for x in range(10) if x % 2 == 0]

@decorator
def decorated_func():
    pass

with open("file.txt") as f:
    data = f.read()
"""
        tree = ast.parse(code)
        patterns = converter._identify_complex_patterns(tree)

        assert len(patterns) > 0
        pattern_types = [p["type"] for p in patterns]
        assert "decorated_function" in pattern_types
        assert "context_manager" in pattern_types

    def test_convert_tool_definition(self):
        """Test converting tool definition."""
        converter = PythonToJavaScriptConverter()

        tool_def = {
            "name": "Example Tool",
            "type": "executable",
            "executable": {
                "command": "python",
                "args": ["script.py", "--verbose"]
            }
        }

        converted = converter.convert_tool_definition(tool_def, Language.JAVASCRIPT)

        assert converted["executable"]["command"] == "node"
        assert converted["executable"]["args"][0] == "script.js"
        assert converted["metadata"]["converted_from"] == "python"

    def test_map_dependencies(self):
        """Test mapping Python dependencies to JavaScript."""
        converter = PythonToJavaScriptConverter()

        python_deps = [
            "requests>=2.28.0",
            "numpy",
            "pyyaml",
            "unknown-package"
        ]

        js_deps = converter._map_dependencies(python_deps)

        assert "axios" in js_deps
        assert "mathjs" in js_deps
        assert "js-yaml" in js_deps
        assert len(converter.warnings) > 0  # Warning for unknown package

    def test_convert_pytest_to_jest(self):
        """Test converting pytest tests to Jest."""
        converter = PythonToJavaScriptConverter()

        pytest_code = """
import pytest

def test_addition():
    assert 2 + 2 == 4

def test_string():
    assert "hello" == "hello"
"""

        jest_code = converter._convert_pytest_to_jest(pytest_code)

        assert "test(" in jest_code
        assert "expect(" in jest_code
        assert "toBe(" in jest_code

    def test_generate_package_json(self):
        """Test generating package.json."""
        converter = PythonToJavaScriptConverter()

        context = ConversionContext(
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            tool_definition={
                "name": "Unit Converter",
                "version": "1.0.0",
                "description": "Converts units",
                "tags": ["conversion", "utility"]
            },
            source_code="",
            dependencies=["requests", "pyyaml"]
        )

        analysis = {"imports": [], "functions": []}
        package_json = converter._generate_package_json(context, analysis)

        assert package_json["name"] == "unit-converter"
        assert package_json["version"] == "1.0.0"
        assert package_json["description"] == "Converts units"
        assert "axios" in package_json["dependencies"]
        assert "js-yaml" in package_json["dependencies"]
        assert "jest" in package_json["devDependencies"]
        assert "conversion" in package_json["keywords"]


class TestConverterFactory:
    """Test converter factory function."""

    def test_create_python_to_js_converter(self):
        """Test creating Python to JavaScript converter."""
        converter = create_converter(
            Language.PYTHON,
            Language.JAVASCRIPT
        )

        assert isinstance(converter, PythonToJavaScriptConverter)

    def test_create_unsupported_converter(self):
        """Test creating unsupported converter raises error."""
        with pytest.raises(ValueError, match="not supported"):
            create_converter(
                Language.JAVASCRIPT,
                Language.PYTHON
            )

    def test_create_typescript_converter_not_implemented(self):
        """Test TypeScript converter is not yet implemented."""
        with pytest.raises(NotImplementedError):
            create_converter(
                Language.PYTHON,
                Language.TYPESCRIPT
            )


class TestIntegration:
    """Integration tests for language converter."""

    def test_full_conversion_workflow(self):
        """Test complete conversion workflow."""
        converter = PythonToJavaScriptConverter()

        # Simple Python tool
        source_code = """
import json
import sys

def process_data(data):
    \"\"\"Process input data.\"\"\"
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result

def main():
    input_data = [1, -2, 3, -4, 5]
    output = process_data(input_data)
    print(json.dumps(output))

if __name__ == "__main__":
    main()
"""

        tool_def = {
            "name": "Data Processor",
            "type": "executable",
            "version": "1.0.0",
            "description": "Processes data arrays",
            "executable": {
                "command": "python",
                "args": ["processor.py"]
            }
        }

        context = ConversionContext(
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            tool_definition=tool_def,
            source_code=source_code,
            dependencies=["json"],
            strategy=ConversionStrategy.HYBRID
        )

        result = converter.convert_code(context)

        # Verify conversion succeeded
        assert result.success is True

        # Verify JavaScript code structure
        assert "function process_data" in result.target_code or "function processData" in result.target_code
        assert "function main" in result.target_code

        # Verify tool definition converted
        assert result.target_definition is not None
        assert result.target_definition["executable"]["command"] == "node"

        # Verify package.json generated
        assert result.package_config is not None
        assert result.package_config["name"] == "data-processor"
        assert "jest" in result.package_config["devDependencies"]

    def test_conversion_with_tests(self):
        """Test conversion with test code."""
        converter = PythonToJavaScriptConverter()

        source_code = """
def add(a, b):
    return a + b
"""

        test_code = """
def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
"""

        context = ConversionContext(
            source_language=Language.PYTHON,
            target_language=Language.JAVASCRIPT,
            tool_definition={"name": "adder"},
            source_code=source_code,
            tests=test_code,
            strategy=ConversionStrategy.AST_BASED
        )

        result = converter.convert_code(context)

        assert result.success is True
        assert result.target_tests is not None
        assert "test(" in result.target_tests
        assert "expect(" in result.target_tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
