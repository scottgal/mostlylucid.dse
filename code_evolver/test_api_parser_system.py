#!/usr/bin/env python3
"""
Test the Smart API Parser System
Demonstrates all three tools working together
"""
import json
import sys
from pathlib import Path

# Add code_evolver to path
sys.path.insert(0, str(Path(__file__).parent))

from node_runtime import call_tool


def test_fake_data_generator():
    """Test the Faker-based data generator"""
    print("\n" + "="*80)
    print("TEST 1: Fake Data Generator (Faker-based)")
    print("="*80)

    # Test 1: Generate a single email
    print("\n1. Generating fake email:")
    result = call_tool('fake_data_generator', json.dumps({
        'schema': {
            'type': 'string',
            'format': 'email'
        }
    }))
    print(result)

    # Test 2: Generate a user object
    print("\n2. Generating fake user object:")
    result = call_tool('fake_data_generator', json.dumps({
        'schema': {
            'type': 'object',
            'required': ['name', 'email', 'age'],
            'properties': {
                'name': {'type': 'string'},
                'email': {'type': 'string', 'format': 'email'},
                'age': {'type': 'integer', 'minimum': 18, 'maximum': 80},
                'address': {'type': 'string', 'description': 'full address'}
            }
        }
    }))
    print(result)

    # Test 3: Generate array of phone numbers
    print("\n3. Generating array of 3 fake phone numbers:")
    result = call_tool('fake_data_generator', json.dumps({
        'schema': {
            'type': 'string',
            'description': 'phone number'
        },
        'count': 3
    }))
    print(result)


def test_llm_fake_data_generator():
    """Test the LLM-based data generator"""
    print("\n" + "="*80)
    print("TEST 2: LLM Fake Data Generator (Context-aware)")
    print("="*80)

    # Test 1: Generate contextual user data
    print("\n1. Generating contextual e-commerce order:")
    schema = {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "customer_name": {"type": "string"},
            "total_amount": {"type": "number"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_name": {"type": "string"},
                        "quantity": {"type": "integer"},
                        "price": {"type": "number"}
                    }
                }
            }
        }
    }

    result = call_tool('llm_fake_data_generator', json.dumps({
        'schema_json': json.dumps(schema),
        'additional_context': 'E-commerce order for tech products'
    }))
    print(result)


def test_smart_api_parser_dry_run():
    """Test Smart API Parser in dry-run mode"""
    print("\n" + "="*80)
    print("TEST 3: Smart API Parser (Dry Run)")
    print("="*80)

    # Create a sample OpenAPI spec
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "User Management API",
            "version": "1.0.0",
            "description": "API for managing users"
        },
        "servers": [
            {"url": "https://api.example.com/v1"}
        ],
        "paths": {
            "/users": {
                "post": {
                    "operationId": "createUser",
                    "summary": "Create a new user",
                    "description": "Creates a new user account",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["email", "name"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string", "format": "email"},
                                        "age": {"type": "integer", "minimum": 18},
                                        "role": {
                                            "type": "string",
                                            "enum": ["user", "admin", "moderator"]
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "User created"}
                    }
                },
                "get": {
                    "operationId": "listUsers",
                    "summary": "List all users",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer"}
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "200": {"description": "List of users"}
                    }
                }
            },
            "/users/{id}": {
                "get": {
                    "operationId": "getUser",
                    "summary": "Get user by ID",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {"description": "User details"}
                    }
                }
            }
        }
    }

    print("\n1. Dry run with Faker (shows generated test data):")
    result = call_tool('smart_api_parser', json.dumps({
        'openapi_spec': openapi_spec,
        'use_llm_generator': False,
        'make_requests': False
    }))

    result_data = json.loads(result)
    print(f"\nAPI: {result_data['api_info']['title']}")
    print(f"Base URL: {result_data['base_url']}")
    print(f"Total Endpoints: {result_data['total_endpoints']}")
    print(f"Tested: {result_data['tested_endpoints']}")

    print("\nGenerated Test Data per Endpoint:")
    for endpoint_result in result_data['results']:
        print(f"\n  {endpoint_result['method']} {endpoint_result['url']}")
        if endpoint_result.get('request_body'):
            print(f"  Request Body: {json.dumps(endpoint_result['request_body'], indent=4)}")
        if endpoint_result.get('query_params'):
            print(f"  Query Params: {endpoint_result['query_params']}")


def main():
    """Run all tests"""
    print("\n" + "#"*80)
    print("# Smart API Parser System - Comprehensive Test Suite")
    print("#"*80)

    try:
        # Test 1: Fake Data Generator
        test_fake_data_generator()

        # Test 2: LLM Fake Data Generator
        print("\n[Skipping LLM test - requires LLM to be running]")
        # test_llm_fake_data_generator()

        # Test 3: Smart API Parser
        test_smart_api_parser_dry_run()

        print("\n" + "#"*80)
        print("# All Tests Completed!")
        print("#"*80)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
