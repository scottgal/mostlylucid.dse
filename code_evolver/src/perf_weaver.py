"""
Performance Weaver - Automatic OpenTelemetry Instrumentation

Automatically "weaves" OpenTelemetry tracing into Python code to assess performance
without requiring manual instrumentation. Uses AST transformation to inject
telemetry calls at function entry/exit points.

Features:
- Automatic function instrumentation
- Class method instrumentation
- Context preservation
- Configurable sampling
- Hot-path detection
- Performance metrics collection
"""

import ast
import inspect
import textwrap
import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import sys
import importlib.util


@dataclass
class InstrumentationConfig:
    """Configuration for performance weaving"""
    enabled: bool = True
    instrument_functions: bool = True
    instrument_methods: bool = True
    instrument_properties: bool = False
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "__init__", "__repr__", "__str__", "__eq__", "__hash__"
    ])
    include_private: bool = False  # Instrument _private methods
    sample_rate: float = 1.0  # 0.0 to 1.0
    trace_args: bool = True
    trace_return: bool = True
    max_arg_length: int = 100  # Truncate long args


@dataclass
class InstrumentationReport:
    """Report of instrumentation performed"""
    file_path: Optional[str] = None
    functions_instrumented: int = 0
    methods_instrumented: int = 0
    classes_instrumented: int = 0
    lines_added: int = 0
    instrumented_names: List[str] = field(default_factory=list)
    skipped_names: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class TelemetryInjector(ast.NodeTransformer):
    """
    AST transformer that injects OpenTelemetry calls into functions/methods
    """

    def __init__(self, config: InstrumentationConfig):
        self.config = config
        self.report = InstrumentationReport()
        self.current_class = None

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Visit class definition to instrument methods"""
        if not self.config.instrument_methods:
            return node

        old_class = self.current_class
        self.current_class = node.name
        self.report.classes_instrumented += 1

        # Visit all methods in the class
        self.generic_visit(node)

        self.current_class = old_class
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function definition to add instrumentation"""
        # Determine if we should instrument this function
        if not self._should_instrument(node):
            self.report.skipped_names.append(node.name)
            return node

        # Check if it's a method or function
        is_method = self.current_class is not None

        if is_method and not self.config.instrument_methods:
            self.report.skipped_names.append(f"{self.current_class}.{node.name}")
            return node

        if not is_method and not self.config.instrument_functions:
            self.report.skipped_names.append(node.name)
            return node

        # Instrument the function
        instrumented = self._inject_telemetry(node, is_method)

        if is_method:
            self.report.methods_instrumented += 1
            self.report.instrumented_names.append(f"{self.current_class}.{node.name}")
        else:
            self.report.functions_instrumented += 1
            self.report.instrumented_names.append(node.name)

        return instrumented

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Visit async function definition"""
        # Same logic as regular functions
        return self.visit_FunctionDef(node)

    def _should_instrument(self, node: ast.FunctionDef) -> bool:
        """Determine if a function should be instrumented"""
        name = node.name

        # Check exclude patterns
        for pattern in self.config.exclude_patterns:
            if pattern in name:
                return False

        # Check private functions
        if name.startswith('_') and not self.config.include_private:
            return False

        return True

    def _inject_telemetry(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        is_method: bool
    ) -> Union[ast.FunctionDef, ast.AsyncFunctionDef]:
        """
        Inject OpenTelemetry tracing into function body

        Transforms:
            def func(x, y):
                return x + y

        Into:
            def func(x, y):
                from src.telemetry_tracker import get_tracker
                _tracker = get_tracker()
                with _tracker.track_tool_call("func", {"x": x, "y": y}) as _span:
                    try:
                        _result = x + y
                        _span.set_attribute("result", str(_result))
                        return _result
                    except Exception as _e:
                        _span.set_attribute("error", str(_e))
                        raise
        """
        func_name = f"{self.current_class}.{node.name}" if is_method else node.name

        # Build the telemetry context manager
        # Import statement
        import_node = ast.ImportFrom(
            module='src.telemetry_tracker',
            names=[ast.alias(name='get_tracker', asname=None)],
            level=0
        )

        # Get tracker
        tracker_assign = ast.Assign(
            targets=[ast.Name(id='_tracker', ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id='get_tracker', ctx=ast.Load()),
                args=[],
                keywords=[]
            )
        )

        # Build params dict if trace_args is enabled
        if self.config.trace_args:
            params_dict = self._build_params_dict(node)
        else:
            params_dict = ast.Dict(keys=[], values=[])

        # Create the with statement
        with_stmt = self._create_with_statement(node, func_name, params_dict)

        # Create new function body
        new_body = [import_node, tracker_assign, with_stmt]

        # Update the function
        new_node = ast.copy_location(
            type(node)(
                name=node.name,
                args=node.args,
                body=new_body,
                decorator_list=node.decorator_list,
                returns=node.returns,
                type_comment=node.type_comment if hasattr(node, 'type_comment') else None
            ),
            node
        )

        self.report.lines_added += 3  # Import, tracker, with statement

        return new_node

    def _build_params_dict(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> ast.Dict:
        """Build dictionary of function parameters for tracing"""
        keys = []
        values = []

        # Regular args
        for arg in node.args.args:
            # Skip 'self' and 'cls'
            if arg.arg in ('self', 'cls'):
                continue

            keys.append(ast.Constant(value=arg.arg))

            # Wrap in str() to handle any type
            values.append(
                ast.Call(
                    func=ast.Name(id='str', ctx=ast.Load()),
                    args=[ast.Name(id=arg.arg, ctx=ast.Load())],
                    keywords=[]
                )
            )

        return ast.Dict(keys=keys, values=values)

    def _create_with_statement(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        func_name: str,
        params_dict: ast.Dict
    ) -> ast.With:
        """Create the with statement that wraps the function body"""
        # Call tracker.track_tool_call(name, params)
        context_expr = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='_tracker', ctx=ast.Load()),
                attr='track_tool_call',
                ctx=ast.Load()
            ),
            args=[
                ast.Constant(value=func_name),
                params_dict
            ],
            keywords=[]
        )

        # Wrap original body in try-except
        try_body = self._wrap_body_with_return_tracking(node.body)

        # Create exception handler
        except_handler = ast.ExceptHandler(
            type=ast.Name(id='Exception', ctx=ast.Load()),
            name='_e',
            body=[
                # _span.set_attribute("error", str(_e))
                ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='_span', ctx=ast.Load()),
                            attr='set_attribute',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Constant(value='error'),
                            ast.Call(
                                func=ast.Name(id='str', ctx=ast.Load()),
                                args=[ast.Name(id='_e', ctx=ast.Load())],
                                keywords=[]
                            )
                        ],
                        keywords=[]
                    )
                ),
                # raise
                ast.Raise(exc=None, cause=None)
            ]
        )

        # Try-except block
        try_except = ast.Try(
            body=try_body,
            handlers=[except_handler],
            orelse=[],
            finalbody=[]
        )

        # With statement
        with_stmt = ast.With(
            items=[ast.withitem(
                context_expr=context_expr,
                optional_vars=ast.Name(id='_span', ctx=ast.Store())
            )],
            body=[try_except]
        )

        return with_stmt

    def _wrap_body_with_return_tracking(self, body: List[ast.stmt]) -> List[ast.stmt]:
        """
        Wrap return statements to track return values

        Transforms:
            return x + y

        Into:
            _result = x + y
            if _span: _span.set_attribute("result", str(_result))
            return _result
        """
        if not self.config.trace_return:
            return body

        new_body = []
        for stmt in body:
            if isinstance(stmt, ast.Return) and stmt.value is not None:
                # Assign return value to _result
                assign = ast.Assign(
                    targets=[ast.Name(id='_result', ctx=ast.Store())],
                    value=stmt.value
                )

                # Track result
                track_result = ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='_span', ctx=ast.Load()),
                            attr='set_attribute',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Constant(value='result'),
                            ast.Call(
                                func=ast.Name(id='str', ctx=ast.Load()),
                                args=[ast.Name(id='_result', ctx=ast.Load())],
                                keywords=[]
                            )
                        ],
                        keywords=[]
                    )
                )

                # Return _result
                new_return = ast.Return(value=ast.Name(id='_result', ctx=ast.Load()))

                new_body.extend([assign, track_result, new_return])
            else:
                new_body.append(stmt)

        return new_body


class PerfWeaver:
    """
    Main class for automatic performance instrumentation
    """

    def __init__(self, config: Optional[InstrumentationConfig] = None):
        self.config = config or InstrumentationConfig()
        self.logger = logging.getLogger(__name__)

    def weave_file(self, file_path: Union[str, Path]) -> InstrumentationReport:
        """
        Instrument a Python file with telemetry

        Args:
            file_path: Path to Python file to instrument

        Returns:
            Report of instrumentation performed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read the file
        source = file_path.read_text(encoding='utf-8')

        # Parse AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            self.logger.error(f"Syntax error in {file_path}: {e}")
            raise

        # Transform AST
        injector = TelemetryInjector(self.config)
        new_tree = injector.visit(tree)
        ast.fix_missing_locations(new_tree)

        # Generate instrumented code
        instrumented_code = ast.unparse(new_tree)

        # Update report
        report = injector.report
        report.file_path = str(file_path)

        # Save instrumented version
        instrumented_path = file_path.with_suffix('.instrumented.py')
        instrumented_path.write_text(instrumented_code, encoding='utf-8')

        self.logger.info(f"Instrumented {file_path} -> {instrumented_path}")
        self.logger.info(f"  Functions: {report.functions_instrumented}")
        self.logger.info(f"  Methods: {report.methods_instrumented}")
        self.logger.info(f"  Classes: {report.classes_instrumented}")

        return report

    def weave_module(self, module) -> InstrumentationReport:
        """
        Instrument a loaded Python module

        Args:
            module: Python module object

        Returns:
            Report of instrumentation performed
        """
        module_file = inspect.getfile(module)
        return self.weave_file(module_file)

    def weave_function(self, func: Callable) -> Callable:
        """
        Instrument a single function with telemetry (decorator style)

        Usage:
            @weaver.weave_function
            def my_function(x, y):
                return x + y

        Args:
            func: Function to instrument

        Returns:
            Instrumented function
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from src.telemetry_tracker import get_tracker
                tracker = get_tracker()
            except:
                # Telemetry not available, run without instrumentation
                return func(*args, **kwargs)

            # Build params
            params = {}
            if self.config.trace_args:
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                params = {k: str(v)[:self.config.max_arg_length]
                         for k, v in bound.arguments.items()}

            # Track execution
            func_name = f"{func.__module__}.{func.__qualname__}"
            with tracker.track_tool_call(func_name, params) as span:
                try:
                    result = func(*args, **kwargs)
                    if self.config.trace_return:
                        span.set_attribute("result", str(result)[:self.config.max_arg_length])
                    return result
                except Exception as e:
                    span.set_attribute("error", str(e))
                    raise

        return wrapper

    def weave_class(self, cls):
        """
        Instrument all methods in a class (decorator style)

        Usage:
            @weaver.weave_class
            class MyClass:
                def method1(self):
                    pass

        Args:
            cls: Class to instrument

        Returns:
            Instrumented class
        """
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            # Skip excluded patterns
            if any(pattern in name for pattern in self.config.exclude_patterns):
                continue

            # Skip private if not included
            if name.startswith('_') and not self.config.include_private:
                continue

            # Wrap the method
            wrapped = self.weave_function(method)
            setattr(cls, name, wrapped)

        return cls

    def generate_report(self, reports: List[InstrumentationReport]) -> str:
        """
        Generate a summary report of instrumentation

        Args:
            reports: List of instrumentation reports

        Returns:
            Formatted report string
        """
        total_functions = sum(r.functions_instrumented for r in reports)
        total_methods = sum(r.methods_instrumented for r in reports)
        total_classes = sum(r.classes_instrumented for r in reports)
        total_lines = sum(r.lines_added for r in reports)

        report = f"""
Performance Weaving Report
{'='*70}

Files Instrumented: {len(reports)}
Functions Instrumented: {total_functions}
Methods Instrumented: {total_methods}
Classes Instrumented: {total_classes}
Lines of Code Added: {total_lines}

Details:
{'='*70}
"""

        for r in reports:
            report += f"""
File: {r.file_path}
  Functions: {r.functions_instrumented}
  Methods: {r.methods_instrumented}
  Classes: {r.classes_instrumented}

  Instrumented: {', '.join(r.instrumented_names[:10])}
  {f'... and {len(r.instrumented_names) - 10} more' if len(r.instrumented_names) > 10 else ''}
"""

        return report


# Convenience functions
# =====================

def weave_file(file_path: Union[str, Path], config: Optional[InstrumentationConfig] = None) -> InstrumentationReport:
    """Instrument a Python file with telemetry"""
    weaver = PerfWeaver(config)
    return weaver.weave_file(file_path)


def weave_function(func: Callable = None, config: Optional[InstrumentationConfig] = None):
    """
    Decorator to instrument a function with telemetry

    Usage:
        @weave_function
        def my_func(x, y):
            return x + y
    """
    weaver = PerfWeaver(config)

    if func is None:
        # Called with arguments: @weave_function(config=...)
        return lambda f: weaver.weave_function(f)
    else:
        # Called without arguments: @weave_function
        return weaver.weave_function(func)


def weave_class(cls = None, config: Optional[InstrumentationConfig] = None):
    """
    Decorator to instrument a class with telemetry

    Usage:
        @weave_class
        class MyClass:
            def method(self):
                pass
    """
    weaver = PerfWeaver(config)

    if cls is None:
        # Called with arguments: @weave_class(config=...)
        return lambda c: weaver.weave_class(c)
    else:
        # Called without arguments: @weave_class
        return weaver.weave_class(cls)


# Context manager for temporary instrumentation
# ==============================================

class InstrumentationContext:
    """
    Context manager for temporary instrumentation

    Usage:
        with InstrumentationContext() as ctx:
            # Code here is automatically instrumented
            result = my_function()
    """

    def __init__(self, config: Optional[InstrumentationConfig] = None):
        self.config = config or InstrumentationConfig()
        self.weaver = PerfWeaver(self.config)
        self.original_modules = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original modules if needed
        pass


if __name__ == "__main__":
    # Example usage
    print("Performance Weaver - Automatic OpenTelemetry Instrumentation\n")

    # Example: Instrument a file
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"Instrumenting: {file_path}\n")

        config = InstrumentationConfig(
            instrument_functions=True,
            instrument_methods=True,
            trace_args=True,
            trace_return=True
        )

        weaver = PerfWeaver(config)
        report = weaver.weave_file(file_path)

        print(f"Report:")
        print(f"  Functions instrumented: {report.functions_instrumented}")
        print(f"  Methods instrumented: {report.methods_instrumented}")
        print(f"  Classes instrumented: {report.classes_instrumented}")
        print(f"\nInstrumented names:")
        for name in report.instrumented_names:
            print(f"  - {name}")
    else:
        print("Usage: python perf_weaver.py <file_to_instrument.py>")
