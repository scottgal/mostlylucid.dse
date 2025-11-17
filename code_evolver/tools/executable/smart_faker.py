#!/usr/bin/env python3
"""
Smart Faker - Intelligent Fake Data Generator
Accepts plain English, code, JSON schemas, or any interpretable input
Generates realistic fake data in multiple formats
"""
import json
import sys
import csv
import io
import os
from typing import Dict, Any, List, Optional, Union


def get_llm_client():
    """Get LLM client from the codebase"""
    try:
        # Add parent directories to path to import from src
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
        from src.llm_client import OllamaClient
        from src.config_manager import ConfigManager

        config = ConfigManager()
        client = OllamaClient(
            base_url=config.ollama_url,
            config_manager=config
        )
        return client
    except Exception as e:
        print(f"Warning: Could not initialize LLM client: {e}", file=sys.stderr)
        return None


def interpret_prompt_with_llm(prompt: str, llm_model: str, additional_context: str = "") -> Dict[str, Any]:
    """
    Use LLM to interpret the prompt and convert it to a structured schema

    Args:
        prompt: User's input (plain English, code, JSON, etc.)
        llm_model: Model to use for interpretation
        additional_context: Additional context for generation

    Returns:
        JSON schema for data generation
    """
    client = get_llm_client()

    if client is None:
        # Fallback: Try to parse prompt as JSON schema
        return parse_prompt_without_llm(prompt)

    system_prompt = """You are a data schema interpreter. Convert user descriptions into JSON schemas.

Rules:
1. Return ONLY valid JSON schema (RFC draft-07)
2. Infer appropriate types from descriptions
3. For code snippets, extract field names and types
4. For example JSON, create matching schema
5. For plain English, infer reasonable structure
6. Use realistic field names and types
7. NO explanations, ONLY the schema JSON

Schema format:
{
  "type": "object",
  "properties": {
    "field_name": {"type": "string|number|boolean|integer|array|object", "description": "..."},
    ...
  },
  "required": ["field1", "field2"]
}"""

    prompt_text = f"""Input to interpret:
{prompt}

{additional_context if additional_context else ''}

Generate JSON schema:"""

    try:
        response = client.generate(
            model=llm_model,
            prompt=prompt_text,
            system=system_prompt,
            temperature=0.3,  # Lower for more consistent schema generation
            max_tokens=1000
        )

        # Extract JSON from response
        schema = extract_json_from_text(response)
        return schema

    except Exception as e:
        print(f"Warning: LLM interpretation failed: {e}", file=sys.stderr)
        return parse_prompt_without_llm(prompt)


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract JSON object from text that may contain markdown or other content"""
    # Try to find JSON in the text
    import re

    # Remove markdown code blocks if present
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Find first { and last }
    start = text.find('{')
    end = text.rfind('}')

    if start != -1 and end != -1:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # If that didn't work, try parsing the whole thing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Return a simple string schema as fallback
        return {"type": "object", "properties": {"value": {"type": "string"}}}


def parse_prompt_without_llm(prompt: str) -> Dict[str, Any]:
    """
    Fallback parser when LLM is not available
    Tries to detect JSON schema, example JSON, or creates simple schema
    """
    prompt = prompt.strip()

    # Try to parse as JSON schema
    try:
        parsed = json.loads(prompt)

        # If it looks like a schema (has "type" or "properties")
        if "type" in parsed or "properties" in parsed:
            return parsed

        # Otherwise, it's example data - infer schema from it
        return infer_schema_from_example(parsed)

    except json.JSONDecodeError:
        pass

    # Try to extract fields from plain English or code
    return infer_schema_from_text(prompt)


def infer_schema_from_example(example: Union[Dict, List]) -> Dict[str, Any]:
    """Infer JSON schema from example data"""
    if isinstance(example, dict):
        properties = {}
        required = []

        for key, value in example.items():
            prop_schema = infer_type_from_value(value)
            properties[key] = prop_schema
            required.append(key)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    elif isinstance(example, list) and len(example) > 0:
        item_schema = infer_schema_from_example(example[0])
        return {
            "type": "array",
            "items": item_schema
        }
    else:
        return {"type": "string"}


def infer_type_from_value(value: Any) -> Dict[str, Any]:
    """Infer JSON schema type from a value"""
    if isinstance(value, bool):
        return {"type": "boolean"}
    elif isinstance(value, int):
        return {"type": "integer"}
    elif isinstance(value, float):
        return {"type": "number"}
    elif isinstance(value, str):
        # Try to detect formats
        if '@' in value:
            return {"type": "string", "format": "email"}
        elif value.startswith('http'):
            return {"type": "string", "format": "uri"}
        else:
            return {"type": "string"}
    elif isinstance(value, list):
        if len(value) > 0:
            item_schema = infer_type_from_value(value[0])
            return {"type": "array", "items": item_schema}
        return {"type": "array"}
    elif isinstance(value, dict):
        return infer_schema_from_example(value)
    else:
        return {"type": "string"}


def infer_schema_from_text(text: str) -> Dict[str, Any]:
    """
    Infer schema from plain English description or code
    Uses simple pattern matching
    """
    import re

    # Look for field-like patterns
    # Pattern: word followed by optional type hints
    patterns = [
        r'(\w+):\s*(\w+)',  # "name: string"
        r'(\w+)\s+(\w+)',   # "string name"
        r'["\'](\w+)["\']', # "name"
        r'self\.(\w+)',     # Python: self.name
        r'this\.(\w+)',     # JavaScript: this.name
    ]

    fields = {}

    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        for match in matches:
            if isinstance(match, tuple):
                field_name = match[0] if match[0] not in ['type', 'self', 'this'] else match[1]
                type_hint = match[1] if len(match) > 1 else None
            else:
                field_name = match
                type_hint = None

            # Skip common keywords
            if field_name in ['def', 'class', 'function', 'const', 'let', 'var', 'return', 'if', 'for']:
                continue

            # Infer type from name or hint
            field_type = infer_type_from_name(field_name, type_hint)
            fields[field_name] = field_type

    if not fields:
        # Default schema
        return {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "value": {"type": "string"}
            }
        }

    return {
        "type": "object",
        "properties": fields,
        "required": list(fields.keys())
    }


def infer_type_from_name(field_name: str, type_hint: Optional[str] = None) -> Dict[str, Any]:
    """Infer JSON schema type from field name and optional type hint"""
    field_name = field_name.lower()

    # Check type hint first
    if type_hint:
        type_hint = type_hint.lower()
        if 'int' in type_hint or 'number' in type_hint:
            return {"type": "integer"}
        elif 'float' in type_hint or 'double' in type_hint or 'decimal' in type_hint:
            return {"type": "number"}
        elif 'bool' in type_hint:
            return {"type": "boolean"}
        elif 'array' in type_hint or 'list' in type_hint:
            return {"type": "array", "items": {"type": "string"}}

    # Infer from name patterns
    if 'email' in field_name:
        return {"type": "string", "format": "email"}
    elif 'url' in field_name or 'link' in field_name:
        return {"type": "string", "format": "uri"}
    elif 'date' in field_name or 'time' in field_name or 'timestamp' in field_name:
        return {"type": "string", "format": "date-time"}
    elif 'phone' in field_name or 'tel' in field_name:
        return {"type": "string", "description": "phone number"}
    elif 'age' in field_name or 'count' in field_name or 'quantity' in field_name:
        return {"type": "integer"}
    elif 'price' in field_name or 'amount' in field_name or 'total' in field_name or 'cost' in field_name:
        return {"type": "number"}
    elif 'is_' in field_name or 'has_' in field_name or 'active' in field_name or 'enabled' in field_name:
        return {"type": "boolean"}
    elif 'address' in field_name:
        return {"type": "string", "description": "address"}
    elif 'name' in field_name:
        return {"type": "string", "description": "name"}
    elif 'id' in field_name:
        return {"type": "string"}
    else:
        return {"type": "string"}


def generate_fake_data(schema: Dict[str, Any], seed: Optional[int] = None) -> Any:
    """
    Generate fake data based on schema using Faker library

    Args:
        schema: JSON schema
        seed: Random seed for reproducibility

    Returns:
        Generated fake data
    """
    try:
        from faker import Faker
        fake = Faker()
        if seed is not None:
            Faker.seed(seed)
    except ImportError:
        fake = None

    return _generate_from_schema(schema, fake, seed)


def _generate_from_schema(schema: Dict[str, Any], fake: Any, seed: Optional[int]) -> Any:
    """Recursive schema-based data generation"""
    schema_type = schema.get('type', 'string')
    schema_format = schema.get('format', '')
    description = schema.get('description', '').lower()

    # Use faker if available, otherwise fallback
    if fake:
        # String types
        if schema_type == 'string':
            if schema_format == 'email':
                return fake.email()
            elif schema_format == 'uri' or schema_format == 'url':
                return fake.url()
            elif schema_format == 'date':
                return fake.date()
            elif schema_format == 'date-time':
                return fake.iso8601()
            elif schema_format == 'uuid':
                return fake.uuid4()
            elif schema_format == 'hostname':
                return fake.hostname()
            elif schema_format == 'ipv4':
                return fake.ipv4()
            elif schema_format == 'ipv6':
                return fake.ipv6()
            elif 'name' in description:
                return fake.name()
            elif 'address' in description:
                return fake.address()
            elif 'phone' in description:
                return fake.phone_number()
            elif 'company' in description:
                return fake.company()
            elif 'city' in description:
                return fake.city()
            elif 'country' in description:
                return fake.country()
            elif 'job' in description or 'title' in description:
                return fake.job()
            else:
                if 'enum' in schema:
                    return fake.random_element(schema['enum'])
                max_length = schema.get('maxLength', 50)
                return fake.text(max_nb_chars=min(max_length, 100))

        # Integer
        elif schema_type == 'integer':
            minimum = schema.get('minimum', 0)
            maximum = schema.get('maximum', 1000)
            return fake.random_int(min=minimum, max=maximum)

        # Number
        elif schema_type == 'number':
            minimum = schema.get('minimum', 0.0)
            maximum = schema.get('maximum', 1000.0)
            return round(fake.pyfloat(min_value=minimum, max_value=maximum), 2)

        # Boolean
        elif schema_type == 'boolean':
            return fake.boolean()

        # Array
        elif schema_type == 'array':
            items_schema = schema.get('items', {'type': 'string'})
            min_items = schema.get('minItems', 1)
            max_items = schema.get('maxItems', 5)
            count = fake.random_int(min=min_items, max=max_items)
            return [_generate_from_schema(items_schema, fake, seed) for _ in range(count)]

        # Object
        elif schema_type == 'object':
            properties = schema.get('properties', {})
            required = schema.get('required', [])

            result = {}

            # Generate required fields
            for prop_name in required:
                if prop_name in properties:
                    result[prop_name] = _generate_from_schema(properties[prop_name], fake, seed)

            # Generate optional fields (50% chance)
            for prop_name, prop_schema in properties.items():
                if prop_name not in required and fake.boolean():
                    result[prop_name] = _generate_from_schema(prop_schema, fake, seed)

            return result

        # Null
        elif schema_type == 'null':
            return None

        else:
            return fake.word()

    else:
        # Fallback without Faker
        return _generate_basic_data(schema, seed)


def _generate_basic_data(schema: Dict[str, Any], seed: Optional[int]) -> Any:
    """Fallback data generation without Faker"""
    import random
    import string

    if seed is not None:
        random.seed(seed)

    schema_type = schema.get('type', 'string')

    if schema_type == 'string':
        if 'enum' in schema:
            return random.choice(schema['enum'])
        length = min(schema.get('maxLength', 20), 20)
        return ''.join(random.choices(string.ascii_letters, k=length))

    elif schema_type == 'integer':
        minimum = schema.get('minimum', 0)
        maximum = schema.get('maximum', 100)
        return random.randint(minimum, maximum)

    elif schema_type == 'number':
        minimum = schema.get('minimum', 0.0)
        maximum = schema.get('maximum', 100.0)
        return round(random.uniform(minimum, maximum), 2)

    elif schema_type == 'boolean':
        return random.choice([True, False])

    elif schema_type == 'array':
        items_schema = schema.get('items', {'type': 'string'})
        count = random.randint(1, 3)
        return [_generate_basic_data(items_schema, seed) for _ in range(count)]

    elif schema_type == 'object':
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        result = {}
        for prop_name in required:
            if prop_name in properties:
                result[prop_name] = _generate_basic_data(properties[prop_name], seed)
        return result

    else:
        return "test_value"


def format_output(data: List[Any], output_format: str, stream: bool = False) -> str:
    """
    Format data in requested output format

    Args:
        data: List of generated items
        output_format: 'json', 'csv', 'jsonl', or 'array'
        stream: Whether to output one item per line

    Returns:
        Formatted string
    """
    if output_format == 'json':
        return json.dumps(data if len(data) > 1 else data[0], indent=2)

    elif output_format == 'jsonl':
        return '\n'.join(json.dumps(item) for item in data)

    elif output_format == 'csv':
        if not data:
            return ""

        # Flatten nested objects for CSV
        flattened = [flatten_dict(item) if isinstance(item, dict) else {'value': item} for item in data]

        # Get all unique keys
        all_keys = set()
        for item in flattened:
            all_keys.update(item.keys())

        # Write CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sorted(all_keys))
        writer.writeheader()
        writer.writerows(flattened)
        return output.getvalue()

    elif output_format == 'array':
        return str(data)

    else:
        return json.dumps(data, indent=2)


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Flatten nested dictionary for CSV output"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Convert list to comma-separated string
            items.append((new_key, ','.join(str(x) for x in v)))
        else:
            items.append((new_key, v))
    return dict(items)


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Extract parameters
        prompt = input_data.get('prompt', '')
        count = input_data.get('count', 1)
        output_format = input_data.get('output_format', 'json')
        stream = input_data.get('stream', False)
        seed = input_data.get('seed')
        llm_model = input_data.get('llm_model', 'gemma2:2b')
        additional_context = input_data.get('additional_context', '')

        if not prompt:
            raise ValueError("Prompt is required")

        # Step 1: Interpret prompt to get schema
        schema = interpret_prompt_with_llm(prompt, llm_model, additional_context)

        # Step 2: Generate data based on schema
        data = []
        for i in range(count):
            item_seed = seed + i if seed is not None else None
            item = generate_fake_data(schema, item_seed)
            data.append(item)

            # If streaming, output immediately
            if stream and output_format == 'jsonl':
                print(json.dumps(item), flush=True)

        # Step 3: Format output (unless already streamed)
        if not (stream and output_format == 'jsonl'):
            formatted_data = format_output(data, output_format, stream)

            # Output result
            result = {
                'success': True,
                'data': formatted_data if output_format == 'csv' else data if len(data) > 1 else data[0],
                'format': output_format,
                'count': count,
                'schema': schema
            }

            print(json.dumps(result, indent=2))
        else:
            # For streaming JSONL, output success message at the end
            print(json.dumps({
                'success': True,
                'format': 'jsonl',
                'count': count,
                'schema': schema,
                'streamed': True
            }), file=sys.stderr)

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
