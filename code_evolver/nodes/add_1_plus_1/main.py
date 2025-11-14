Here's the fixed code:

```python
import json
import sys

def add(a: int, b: int) -> int:
    """
    Adds two integers and returns the result.
    """
    return a + b

if __name__ == "__main__":
    try:
        input_json = json.load(sys.stdin)
        if not isinstance(input_json, dict):
            raise ValueError("Invalid JSON")
        if "a" not in input_json or "b" not in input_json:
            raise ValueError("JSON missing 'a' and/or 'b'")
        a = int(input_json["a"])
        b = int(input_json["b"])
        result = add(a, b)
        output_json = {"result": result}
        print(json.dumps(output_json))
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    except ValueError as e:
        print(f"Invalid input: {e}")
```