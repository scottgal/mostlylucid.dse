#!/usr/bin/env python3
"""
Random Test Data Generator - Creates test data for workflows.

Usage:
    python random_data_generator.py <schema_or_description>

The input can be:
    - A JSON schema describing the expected input format
    - A natural language description of what data is needed
    - A workflow name or ID to analyze

Examples:
    python random_data_generator.py '{"name": "string", "age": "number", "email": "string"}'
    python random_data_generator.py "Generate data for a user profile with name, age, and email"
    python random_data_generator.py "I need test data for translating text"
"""

import sys
import json
import random
import string
from typing import Any, Dict, List, Union


class RandomDataGenerator:
    """Generates random test data based on schemas or descriptions."""

    def __init__(self):
        self.first_names = [
            "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
            "Iris", "Jack", "Kate", "Liam", "Mary", "Nathan", "Olivia", "Peter"
        ]
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
            "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez"
        ]
        self.domains = [
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "example.com"
        ]
        self.words = [
            "hello", "world", "test", "data", "sample", "example", "random",
            "quick", "brown", "fox", "jumps", "over", "lazy", "dog"
        ]
        self.languages = ["en", "es", "fr", "de", "it", "pt", "nl", "ru", "zh", "ja"]
        self.language_names = ["English", "Spanish", "French", "German", "Italian", "Portuguese"]

    def generate_string(self, field_name: str = "", min_length: int = 5, max_length: int = 20) -> str:
        """Generate a random string, context-aware based on field name."""
        field_lower = field_name.lower()

        # Email
        if "email" in field_lower or "mail" in field_lower:
            first = random.choice(self.first_names).lower()
            last = random.choice(self.last_names).lower()
            domain = random.choice(self.domains)
            return f"{first}.{last}@{domain}"

        # Name
        if "name" in field_lower or "title" in field_lower:
            if "first" in field_lower:
                return random.choice(self.first_names)
            elif "last" in field_lower:
                return random.choice(self.last_names)
            else:
                return f"{random.choice(self.first_names)} {random.choice(self.last_names)}"

        # Text/Content
        if "text" in field_lower or "content" in field_lower or "message" in field_lower or "description" in field_lower:
            num_words = random.randint(5, 15)
            return " ".join(random.choices(self.words, k=num_words)).capitalize() + "."

        # Language code
        if "lang" in field_lower or "language" in field_lower:
            if "source" in field_lower or "src" in field_lower or "from" in field_lower:
                return random.choice(self.languages)
            elif "target" in field_lower or "tgt" in field_lower or "to" in field_lower or "dest" in field_lower:
                return random.choice([lang for lang in self.languages if lang != "en"])
            else:
                # If language name expected
                if "name" in field_lower:
                    return random.choice(self.language_names)
                return random.choice(self.languages)

        # URL
        if "url" in field_lower or "link" in field_lower or "href" in field_lower:
            return f"https://example.com/{random.choice(self.words)}"

        # Phone
        if "phone" in field_lower or "tel" in field_lower:
            return f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}"

        # Address
        if "address" in field_lower or "street" in field_lower:
            num = random.randint(1, 9999)
            street = random.choice(["Main St", "Oak Ave", "Park Rd", "Washington Blvd"])
            return f"{num} {street}"

        # City
        if "city" in field_lower:
            return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia"])

        # Country
        if "country" in field_lower:
            return random.choice(["USA", "UK", "Canada", "Australia", "Germany", "France"])

        # Default: random alphanumeric string
        length = random.randint(min_length, max_length)
        return ''.join(random.choices(string.ascii_lowercase, k=length))

    def generate_number(self, field_name: str = "", min_val: int = 0, max_val: int = 100) -> Union[int, float]:
        """Generate a random number, context-aware based on field name."""
        field_lower = field_name.lower()

        # Age
        if "age" in field_lower:
            return random.randint(18, 80)

        # Price/Cost
        if "price" in field_lower or "cost" in field_lower or "amount" in field_lower:
            return round(random.uniform(9.99, 999.99), 2)

        # Year
        if "year" in field_lower:
            return random.randint(1900, 2024)

        # Temperature
        if "temp" in field_lower:
            return round(random.uniform(0.0, 1.0), 2)

        # Beam size (for translation)
        if "beam" in field_lower:
            return random.randint(1, 10)

        # Default
        if any(word in field_lower for word in ["float", "decimal", "rate", "ratio"]):
            return round(random.uniform(min_val, max_val), 2)
        else:
            return random.randint(min_val, max_val)

    def generate_boolean(self, field_name: str = "") -> bool:
        """Generate a random boolean."""
        # For splitting/processing flags, default to True
        if "split" in field_name.lower() or "perform" in field_name.lower():
            return random.choice([True, True, False])  # 66% chance of True
        return random.choice([True, False])

    def generate_array(self, field_name: str = "", item_type: str = "string", min_items: int = 1, max_items: int = 5) -> List[Any]:
        """Generate a random array."""
        num_items = random.randint(min_items, max_items)
        items = []

        for _ in range(num_items):
            if item_type == "string":
                items.append(self.generate_string(field_name))
            elif item_type == "number":
                items.append(self.generate_number(field_name))
            elif item_type == "boolean":
                items.append(self.generate_boolean(field_name))
            else:
                items.append(self.generate_string())

        return items

    def generate_from_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate random data from a JSON schema."""
        result = {}

        for field, field_type in schema.items():
            if isinstance(field_type, dict):
                # Nested object
                result[field] = self.generate_from_schema(field_type)
            elif field_type in ["string", "str", "text"]:
                result[field] = self.generate_string(field)
            elif field_type in ["number", "int", "integer", "float"]:
                result[field] = self.generate_number(field)
            elif field_type in ["boolean", "bool"]:
                result[field] = self.generate_boolean(field)
            elif field_type in ["array", "list"]:
                result[field] = self.generate_array(field)
            else:
                # Unknown type, use string
                result[field] = self.generate_string(field)

        return result

    def parse_natural_language(self, description: str) -> Dict[str, Any]:
        """Parse natural language description to generate test data."""
        result = {}
        desc_lower = description.lower()

        # Translation workflow
        if "translat" in desc_lower:
            result["text"] = self.generate_string("text")
            if "source" in desc_lower or "from" in desc_lower:
                result["source_lang"] = "en"
            if "target" in desc_lower or "to" in desc_lower:
                result["target_lang"] = random.choice(["es", "fr", "de"])
            if "beam" in desc_lower:
                result["beam_size"] = 5
            return result

        # User profile
        if "profile" in desc_lower or "user" in desc_lower:
            result["name"] = self.generate_string("name")
            result["email"] = self.generate_string("email")
            if "age" in desc_lower:
                result["age"] = self.generate_number("age")
            return result

        # Article/Content
        if "article" in desc_lower or "content" in desc_lower or "story" in desc_lower:
            if "title" in desc_lower:
                result["title"] = self.generate_string("title")
            result["content"] = self.generate_string("content")
            if "author" in desc_lower:
                result["author"] = self.generate_string("name")
            return result

        # Generic fallback
        if "name" in desc_lower:
            result["name"] = self.generate_string("name")
        if "text" in desc_lower or "input" in desc_lower:
            result["text"] = self.generate_string("text")
        if "description" in desc_lower:
            result["description"] = self.generate_string("description")

        # If no fields identified, create a generic input
        if not result:
            result["input"] = self.generate_string("text")

        return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Missing argument. Usage: random_data_generator.py <schema_or_description>"
        }))
        sys.exit(1)

    input_arg = " ".join(sys.argv[1:])
    generator = RandomDataGenerator()

    try:
        # Try to parse as JSON schema
        schema = json.loads(input_arg)
        result = generator.generate_from_schema(schema)
    except json.JSONDecodeError:
        # Treat as natural language description
        result = generator.parse_natural_language(input_arg)

    # Output the generated data
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
