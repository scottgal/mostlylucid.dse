#!/usr/bin/env python3
"""
Fake Data Generator using Faker library
Generates realistic fake data for testing APIs
"""
import json
import sys
from typing import Dict, Any, List, Optional


def generate_fake_data(schema: Dict[str, Any]) -> Any:
    """
    Generate fake data based on a schema

    Args:
        schema: JSON schema or simple type description

    Returns:
        Generated fake data matching the schema
    """
    try:
        from faker import Faker
        fake = Faker()
    except ImportError:
        # Fallback to basic generation without faker
        return generate_basic_fake_data(schema)

    # Handle schema type
    schema_type = schema.get('type', 'string')
    schema_format = schema.get('format', '')

    # String types with formats
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
        elif 'name' in schema.get('description', '').lower():
            return fake.name()
        elif 'address' in schema.get('description', '').lower():
            return fake.address()
        elif 'phone' in schema.get('description', '').lower():
            return fake.phone_number()
        elif 'company' in schema.get('description', '').lower():
            return fake.company()
        else:
            # Check if there's an enum
            if 'enum' in schema:
                return fake.random_element(schema['enum'])
            # Check max length
            max_length = schema.get('maxLength', 50)
            return fake.text(max_nb_chars=min(max_length, 100))

    # Integer/number types
    elif schema_type == 'integer':
        minimum = schema.get('minimum', 0)
        maximum = schema.get('maximum', 1000)
        return fake.random_int(min=minimum, max=maximum)

    elif schema_type == 'number':
        minimum = schema.get('minimum', 0.0)
        maximum = schema.get('maximum', 1000.0)
        return round(fake.pyfloat(min_value=minimum, max_value=maximum), 2)

    # Boolean type
    elif schema_type == 'boolean':
        return fake.boolean()

    # Array type
    elif schema_type == 'array':
        items_schema = schema.get('items', {'type': 'string'})
        min_items = schema.get('minItems', 1)
        max_items = schema.get('maxItems', 5)
        count = fake.random_int(min=min_items, max=max_items)
        return [generate_fake_data(items_schema) for _ in range(count)]

    # Object type
    elif schema_type == 'object':
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        result = {}

        # Generate all required fields
        for prop_name in required:
            if prop_name in properties:
                result[prop_name] = generate_fake_data(properties[prop_name])

        # Generate some optional fields (50% chance for each)
        for prop_name, prop_schema in properties.items():
            if prop_name not in required and fake.boolean():
                result[prop_name] = generate_fake_data(prop_schema)

        return result

    # Null type
    elif schema_type == 'null':
        return None

    # Default fallback
    else:
        return fake.word()


def generate_basic_fake_data(schema: Dict[str, Any]) -> Any:
    """
    Fallback generator without Faker library

    Args:
        schema: JSON schema

    Returns:
        Basic fake data
    """
    import random
    import string

    schema_type = schema.get('type', 'string')

    if schema_type == 'string':
        if 'enum' in schema:
            return random.choice(schema['enum'])
        max_length = schema.get('maxLength', 20)
        length = min(max_length, random.randint(5, 20))
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

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
        return [generate_basic_fake_data(items_schema) for _ in range(count)]

    elif schema_type == 'object':
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        result = {}
        for prop_name in required:
            if prop_name in properties:
                result[prop_name] = generate_basic_fake_data(properties[prop_name])

        return result

    elif schema_type == 'null':
        return None

    else:
        return "test_value"


def main():
    """Main entry point"""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Get schema from input
        schema = input_data.get('schema', {'type': 'string'})
        count = input_data.get('count', 1)

        # Generate fake data
        if count == 1:
            result = generate_fake_data(schema)
        else:
            result = [generate_fake_data(schema) for _ in range(count)]

        # Output result
        print(json.dumps({
            'success': True,
            'data': result,
            'schema': schema
        }, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
