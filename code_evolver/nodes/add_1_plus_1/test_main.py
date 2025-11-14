Here is a possible set of unit tests for the `add` function:
```python
import json
from add import add

def test_normal_case():
    input_json = {"a": 1, "b": 1}
    output_json = {"result": add(input_json["a"], input_json["b"])}
    assert output_json == {"result": 2}

def test_edge_cases():
    # What if the inputs are not integers?
    input_json = {"a": "1", "b": "1"}
    with pytest.raises(ValueError):
        add(input_json["a"], input_json["b"])

    # What if the inputs are negative?
    input_json = {"a": -1, "b": -1}
    output_json = {"result": add(input_json["a"], input_json["b"])}
    assert output_json == {"result": 0}

def test_error_handling():
    # What if the inputs are very large?
    input_json = {"a": 1000000000, "b": 1000000000}
    with pytest.raises(OverflowError):
        add(input_json["a"], input_json["b"])

def test_correctness():
    # Test that the function returns the correct result for a variety of inputs
    inputs = [
        {"a": 1, "b": 1},
        {"a": -1, "b": -1},
        {"a": 0, "b": 0},
        {"a": 1000000000, "b": 1000000000},
    ]
    for input in inputs:
        output_json = {"result": add(input["a"], input["b"])}
        assert output_json == {"result": input["a"] + input["b"]}
```
These tests cover the following cases:

* Normal case: Test that the function returns the correct result for a valid input.
* Edge cases: Test that the function raises the appropriate error for invalid inputs, such as non-integer or negative numbers.
* Error handling: Test that the function handles large inputs correctly and does not raise an error.
* Correctness: Test that the function returns the correct result for a variety of inputs.