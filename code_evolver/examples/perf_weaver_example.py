"""
Performance Weaver Examples

Demonstrates automatic OpenTelemetry instrumentation using the Perf Weaver tool.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.perf_weaver import (
    PerfWeaver,
    InstrumentationConfig,
    weave_function,
    weave_class
)


# Example 1: Decorator-based Function Instrumentation
# ====================================================

print("="*70)
print("EXAMPLE 1: Decorator-based Function Instrumentation")
print("="*70)

@weave_function
def calculate_fibonacci(n: int) -> int:
    """Calculate fibonacci number (recursive, slow)"""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)

print("\nCalling instrumented function: calculate_fibonacci(10)")
result = calculate_fibonacci(10)
print(f"Result: {result}")
print("(Check OpenTelemetry traces for performance data)")


# Example 2: Decorator-based Class Instrumentation
# =================================================

print("\n" + "="*70)
print("EXAMPLE 2: Decorator-based Class Instrumentation")
print("="*70)

@weave_class
class DataProcessor:
    """Example class with instrumented methods"""

    def __init__(self, name: str):
        self.name = name
        self.data = []

    def add_data(self, item):
        """Add item to dataset"""
        self.data.append(item)

    def process(self):
        """Process the dataset"""
        total = sum(self.data)
        average = total / len(self.data) if self.data else 0
        return {"total": total, "average": average, "count": len(self.data)}

    def _internal_method(self):
        """Private method (not instrumented by default)"""
        pass

print("\nUsing instrumented class:")
processor = DataProcessor("test")
processor.add_data(10)
processor.add_data(20)
processor.add_data(30)
result = processor.process()
print(f"Result: {result}")
print("(Check OpenTelemetry traces for method calls)")


# Example 3: File-based Instrumentation
# ======================================

print("\n" + "="*70)
print("EXAMPLE 3: File-based Instrumentation")
print("="*70)

# Create a sample file to instrument
sample_code = '''
def add(x, y):
    """Add two numbers"""
    return x + y

def multiply(x, y):
    """Multiply two numbers"""
    return x * y

class Calculator:
    """Simple calculator class"""

    def divide(self, x, y):
        """Divide x by y"""
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y

    def power(self, x, y):
        """Raise x to power y"""
        return x ** y
'''

sample_file = Path(__file__).parent / "sample_code.py"
sample_file.write_text(sample_code)

print(f"\nCreated sample file: {sample_file}")
print("\nOriginal code:")
print("-" * 70)
print(sample_code)
print("-" * 70)

# Instrument the file
config = InstrumentationConfig(
    instrument_functions=True,
    instrument_methods=True,
    trace_args=True,
    trace_return=True,
    include_private=False
)

weaver = PerfWeaver(config)
report = weaver.weave_file(sample_file)

print(f"\nInstrumentation Report:")
print(f"  Functions instrumented: {report.functions_instrumented}")
print(f"  Methods instrumented: {report.methods_instrumented}")
print(f"  Classes instrumented: {report.classes_instrumented}")
print(f"  Lines added: {report.lines_added}")

print(f"\nInstrumented names:")
for name in report.instrumented_names:
    print(f"  - {name}")

# Show instrumented code
instrumented_file = sample_file.with_suffix('.instrumented.py')
print(f"\nInstrumented code saved to: {instrumented_file}")
print("\nInstrumented code preview (first 30 lines):")
print("-" * 70)
instrumented_code = instrumented_file.read_text()
lines = instrumented_code.split('\n')
for i, line in enumerate(lines[:30], 1):
    print(f"{i:3d} | {line}")
if len(lines) > 30:
    print(f"... and {len(lines) - 30} more lines")
print("-" * 70)


# Example 4: Custom Configuration
# ================================

print("\n" + "="*70)
print("EXAMPLE 4: Custom Configuration")
print("="*70)

# Create config that includes private methods
custom_config = InstrumentationConfig(
    instrument_functions=True,
    instrument_methods=True,
    include_private=True,  # Include _private methods
    trace_args=True,
    trace_return=True,
    exclude_patterns=['__init__', '__repr__'],  # Still exclude these
    max_arg_length=50  # Truncate long arguments
)

print("\nConfiguration:")
print(f"  Include private methods: {custom_config.include_private}")
print(f"  Trace arguments: {custom_config.trace_args}")
print(f"  Trace returns: {custom_config.trace_return}")
print(f"  Max arg length: {custom_config.max_arg_length}")
print(f"  Exclude patterns: {custom_config.exclude_patterns}")


# Example 5: Selective Instrumentation
# =====================================

print("\n" + "="*70)
print("EXAMPLE 5: Selective Instrumentation")
print("="*70)

# Only instrument functions, not methods
functions_only_config = InstrumentationConfig(
    instrument_functions=True,
    instrument_methods=False,  # Skip methods
    trace_args=True,
    trace_return=False  # Don't track return values
)

print("\nConfiguration:")
print(f"  Instrument functions: {functions_only_config.instrument_functions}")
print(f"  Instrument methods: {functions_only_config.instrument_methods}")
print(f"  Trace args: {functions_only_config.trace_args}")
print(f"  Trace return: {functions_only_config.trace_return}")


# Example 6: Batch Processing
# ============================

print("\n" + "="*70)
print("EXAMPLE 6: Batch File Processing")
print("="*70)

# Create multiple sample files
sample_files = []
for i in range(3):
    code = f'''
def function_{i}_a(x):
    """Function {i}a"""
    return x * {i}

def function_{i}_b(x):
    """Function {i}b"""
    return x + {i}

class Class_{i}:
    """Class {i}"""
    def method(self, x):
        return x ** {i}
'''
    file_path = Path(__file__).parent / f"sample_{i}.py"
    file_path.write_text(code)
    sample_files.append(file_path)
    print(f"Created: {file_path.name}")

# Instrument all files
weaver = PerfWeaver(InstrumentationConfig())
reports = []

print("\nInstrumenting files...")
for file_path in sample_files:
    report = weaver.weave_file(file_path)
    reports.append(report)
    print(f"  {file_path.name}: {report.functions_instrumented} functions, {report.methods_instrumented} methods")

# Generate summary report
summary = weaver.generate_report(reports)
print("\n" + summary)


# Cleanup
# =======

print("\n" + "="*70)
print("Cleanup")
print("="*70)

cleanup_files = [
    sample_file,
    sample_file.with_suffix('.instrumented.py'),
]
cleanup_files.extend(sample_files)
cleanup_files.extend([f.with_suffix('.instrumented.py') for f in sample_files])

print("\nRemoving temporary files...")
for file_path in cleanup_files:
    if file_path.exists():
        file_path.unlink()
        print(f"  Removed: {file_path.name}")

print("\n" + "="*70)
print("Examples completed!")
print("="*70)
print("\nTo see actual telemetry data:")
print("1. Ensure OpenTelemetry collector is running")
print("2. Check Grafana/Jaeger for traces")
print("3. Look for spans with names like 'tool.<function_name>'")
