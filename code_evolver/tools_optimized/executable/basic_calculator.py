#!/usr/bin/env python3
"""
Basic Calculator - Fast arithmetic operations.

Optimizations:
- Extracted from inline Python to separate file
- Uses BaseTool for consistent error handling
- Better input validation
- Clearer error messages
- Maintains exact same behavior as original
"""

import sys
import os

# Add lib to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from base_tool import BaseCalculatorTool


class BasicCalculator(BaseCalculatorTool):
    """Fast arithmetic operations without LLM overhead."""

    OPERATIONS = {
        'add': lambda a, b: a + b,
        'subtract': lambda a, b: a - b,
        'multiply': lambda a, b: a * b,
        'divide': lambda a, b: a / b if b != 0 else float('inf'),
        'power': lambda a, b: a ** b,
        'modulo': lambda a, b: a % b if b != 0 else 0
    }

    def execute(self, input_data):
        """
        Perform arithmetic operation.

        Args:
            input_data: Dict with 'operation', 'a', 'b'

        Returns:
            Result dictionary
        """
        # Get parameters with defaults (same as original)
        operation = input_data.get('operation', 'add')
        a = input_data.get('a', 0)
        b = input_data.get('b', 0)

        # Validate operation
        if operation not in self.OPERATIONS:
            return self.error(
                f"Unknown operation: {operation}",
                valid_operations=list(self.OPERATIONS.keys())
            )

        # Validate numeric inputs
        is_valid_a, error_a = self.validate_numeric(a, 'a')
        if not is_valid_a:
            return self.error(error_a)

        is_valid_b, error_b = self.validate_numeric(b, 'b')
        if not is_valid_b:
            return self.error(error_b)

        # Perform calculation
        try:
            result = self.OPERATIONS[operation](a, b)

            return self.success({
                'result': result,
                'operation': operation
            })

        except Exception as e:
            return self.error(f"Calculation failed: {str(e)}")


if __name__ == "__main__":
    BasicCalculator().run()
