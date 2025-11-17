# Python Best Practices

Python is a versatile programming language that emphasizes code readability and simplicity. When writing Python code, it's essential to follow established best practices to ensure your code is maintainable and efficient.

## Code Style

Always follow PEP 8 guidelines for code formatting. This includes:

- Use 4 spaces for indentation (never tabs)
- Limit lines to 79 characters
- Use snake_case for function names
- Use CamelCase for class names

## Documentation

Every function should have a docstring that explains its purpose, parameters, and return values. Use the following format:

```python
def calculate_sum(a: int, b: int) -> int:
    """
    Calculate the sum of two integers.

    Args:
        a: First integer
        b: Second integer

    Returns:
        Sum of a and b
    """
    return a + b
```

## Error Handling

Use specific exceptions rather than generic ones. Always catch the most specific exception possible:

```python
try:
    result = divide(10, 0)
except ZeroDivisionError:
    logger.error("Cannot divide by zero")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

Remember: clean code is better than clever code.
