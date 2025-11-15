"""
HTTP Content Fetcher - Example Usage

This script demonstrates the comprehensive capabilities of the HTTPContentFetcher tool,
showing how it can be used standalone or integrated with the DSE workflow system.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from http_content_fetcher import create_http_fetcher


def example_basic_get():
    """Example: Basic GET request."""
    print("\n" + "="*60)
    print("Example 1: Basic GET Request")
    print("="*60)

    fetcher = create_http_fetcher()
    result = fetcher.get('https://jsonplaceholder.typicode.com/posts/1')

    print(f"Status: {result['status_code']}")
    print(f"Success: {result['success']}")
    print(f"Data: {json.dumps(result['data'], indent=2)}")


def example_post_json():
    """Example: POST request with JSON body."""
    print("\n" + "="*60)
    print("Example 2: POST Request with JSON Body")
    print("="*60)

    fetcher = create_http_fetcher()

    payload = {
        'title': 'My New Post',
        'body': 'This is the content of my post',
        'userId': 1
    }

    result = fetcher.post(
        'https://jsonplaceholder.typicode.com/posts',
        body=payload,
        body_type='json'
    )

    print(f"Status: {result['status_code']}")
    print(f"Created ID: {result['data'].get('id')}")
    print(f"Title: {result['data'].get('title')}")


def example_authentication():
    """Example: Using different authentication methods."""
    print("\n" + "="*60)
    print("Example 3: Authentication Methods")
    print("="*60)

    fetcher = create_http_fetcher()

    # Bearer token
    result1 = fetcher.get(
        'https://httpbin.org/headers',
        auth={'type': 'bearer', 'token': 'my_secret_token'}
    )
    print(f"Bearer Token: {'Authorization' in result1['data']['headers']}")

    # API Key
    result2 = fetcher.get(
        'https://httpbin.org/headers',
        auth={'type': 'api_key', 'key': 'my_api_key', 'header': 'X-API-Key'}
    )
    print(f"API Key: {'X-Api-Key' in result2['data']['headers']}")


def example_all_http_methods():
    """Example: All HTTP methods."""
    print("\n" + "="*60)
    print("Example 4: All HTTP Methods")
    print("="*60)

    fetcher = create_http_fetcher()

    methods = {
        'GET': lambda: fetcher.get('https://httpbin.org/get'),
        'POST': lambda: fetcher.post('https://httpbin.org/post', body={'test': 'data'}),
        'PUT': lambda: fetcher.put('https://httpbin.org/put', body={'test': 'data'}),
        'DELETE': lambda: fetcher.delete('https://httpbin.org/delete'),
        'PATCH': lambda: fetcher.patch('https://httpbin.org/patch', body={'test': 'data'}),
        'HEAD': lambda: fetcher.head('https://httpbin.org/get'),
    }

    for method_name, method_func in methods.items():
        result = method_func()
        print(f"{method_name}: Status {result['status_code']} - {'✓' if result['success'] else '✗'}")


def example_different_body_types():
    """Example: Different request body types."""
    print("\n" + "="*60)
    print("Example 5: Different Body Types")
    print("="*60)

    fetcher = create_http_fetcher()

    # JSON
    json_result = fetcher.post(
        'https://httpbin.org/post',
        body={'key': 'value'},
        body_type='json'
    )
    print(f"JSON Body: {json_result['success']}")

    # Form-encoded
    form_result = fetcher.post(
        'https://httpbin.org/post',
        body={'field1': 'value1', 'field2': 'value2'},
        body_type='form'
    )
    print(f"Form Body: {form_result['success']}")

    # XML
    xml_data = '<?xml version="1.0"?><root><item>test</item></root>'
    xml_result = fetcher.post(
        'https://httpbin.org/post',
        body=xml_data,
        body_type='xml'
    )
    print(f"XML Body: {xml_result['success']}")

    # Plain text
    text_result = fetcher.post(
        'https://httpbin.org/post',
        body='This is plain text',
        body_type='text'
    )
    print(f"Text Body: {text_result['success']}")


def example_custom_headers():
    """Example: Custom headers."""
    print("\n" + "="*60)
    print("Example 6: Custom Headers")
    print("="*60)

    fetcher = create_http_fetcher()

    result = fetcher.get(
        'https://httpbin.org/headers',
        headers={
            'X-Custom-Header': 'MyValue',
            'User-Agent': 'MyApp/1.0',
            'Accept': 'application/json'
        }
    )

    print(f"Custom headers sent: {result['success']}")
    print(f"Headers received: {list(result['data']['headers'].keys())[:5]}...")


def example_query_parameters():
    """Example: Query parameters."""
    print("\n" + "="*60)
    print("Example 7: Query Parameters")
    print("="*60)

    fetcher = create_http_fetcher()

    result = fetcher.get(
        'https://httpbin.org/get',
        params={
            'search': 'python',
            'page': 1,
            'limit': 10
        }
    )

    print(f"Query params sent: {result['data']['args']}")


def example_error_handling():
    """Example: Error handling."""
    print("\n" + "="*60)
    print("Example 8: Error Handling")
    print("="*60)

    fetcher = create_http_fetcher()

    # 404 error
    result1 = fetcher.get('https://httpbin.org/status/404')
    print(f"404 Error: Status {result1['status_code']}, Error: {result1['error']}")

    # Invalid URL
    result2 = fetcher.get('not_a_valid_url')
    print(f"Invalid URL: {result2['error']}")

    # Connection error
    result3 = fetcher.get('https://this-does-not-exist-12345.com', timeout=5)
    print(f"Connection Error: {result3['error'][:50]}...")


def example_response_formats():
    """Example: Different response formats."""
    print("\n" + "="*60)
    print("Example 9: Response Formats")
    print("="*60)

    fetcher = create_http_fetcher()

    # Auto-detect (JSON)
    json_result = fetcher.get('https://httpbin.org/json', response_format='auto')
    print(f"Auto-detect JSON: {type(json_result['data']).__name__}")

    # Explicit text
    text_result = fetcher.get('https://httpbin.org/html', response_format='text')
    print(f"Explicit text: {len(text_result['data'])} characters")

    # Binary (base64 encoded)
    binary_result = fetcher.get('https://httpbin.org/bytes/100', response_format='binary')
    print(f"Binary (base64): {len(binary_result['data'])} encoded chars")


def example_timeout_and_retries():
    """Example: Timeout and retry configuration."""
    print("\n" + "="*60)
    print("Example 10: Timeout and Retries")
    print("="*60)

    # Create fetcher with custom timeout and retries
    fetcher = create_http_fetcher(
        default_timeout=10,
        max_retries=5,
        retry_backoff_factor=0.5
    )

    result = fetcher.get('https://httpbin.org/delay/2')
    print(f"Request with 2s delay: {result['success']}")
    print(f"Elapsed time: {result['elapsed_ms']:.2f}ms")


def example_cookies():
    """Example: Cookie handling."""
    print("\n" + "="*60)
    print("Example 11: Cookies")
    print("="*60)

    fetcher = create_http_fetcher()

    result = fetcher.get(
        'https://httpbin.org/cookies',
        cookies={
            'session_id': 'abc123',
            'user_pref': 'dark_mode'
        }
    )

    print(f"Cookies sent: {result['data']['cookies']}")


def example_workflow_integration():
    """Example: Integration with DSE workflow system."""
    print("\n" + "="*60)
    print("Example 12: Workflow Integration")
    print("="*60)

    fetcher = create_http_fetcher(tool_id="api_fetcher", name="API Data Fetcher")

    # Simulate a workflow step that fetches data
    print("Simulating workflow step...")

    # Step 1: Fetch user data
    user_result = fetcher.get('https://jsonplaceholder.typicode.com/users/1')

    if user_result['success']:
        user_data = user_result['data']
        print(f"✓ Step 1: Fetched user '{user_data['name']}'")

        # Step 2: Fetch user's posts using data from Step 1
        posts_result = fetcher.get(
            'https://jsonplaceholder.typicode.com/posts',
            params={'userId': user_data['id']}
        )

        if posts_result['success']:
            posts_data = posts_result['data']
            print(f"✓ Step 2: Fetched {len(posts_data)} posts for user")

            # Step 3: Create a new post
            new_post = fetcher.post(
                'https://jsonplaceholder.typicode.com/posts',
                body={
                    'title': f"New post by {user_data['name']}",
                    'body': 'This post was created by the workflow',
                    'userId': user_data['id']
                }
            )

            if new_post['success']:
                print(f"✓ Step 3: Created new post with ID {new_post['data']['id']}")
                print(f"\n✓ Workflow completed successfully!")
            else:
                print(f"✗ Step 3 failed: {new_post['error']}")
        else:
            print(f"✗ Step 2 failed: {posts_result['error']}")
    else:
        print(f"✗ Step 1 failed: {user_result['error']}")


def example_advanced_features():
    """Example: Advanced features."""
    print("\n" + "="*60)
    print("Example 13: Advanced Features")
    print("="*60)

    fetcher = create_http_fetcher()

    # Disable redirects
    result1 = fetcher.get('https://httpbin.org/redirect/1', allow_redirects=False)
    print(f"Redirect disabled: Status {result1['status_code']} (should be 302)")

    # Response timing
    result2 = fetcher.get('https://httpbin.org/delay/1')
    print(f"Response timing: {result2['elapsed_ms']:.2f}ms")

    # Response headers inspection
    result3 = fetcher.get('https://httpbin.org/response-headers?X-Test=Value')
    print(f"Response headers: {len(result3['headers'])} headers received")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print(" HTTP CONTENT FETCHER - COMPREHENSIVE EXAMPLES")
    print("="*70)

    examples = [
        example_basic_get,
        example_post_json,
        example_authentication,
        example_all_http_methods,
        example_different_body_types,
        example_custom_headers,
        example_query_parameters,
        example_error_handling,
        example_response_formats,
        example_timeout_and_retries,
        example_cookies,
        example_workflow_integration,
        example_advanced_features,
    ]

    for i, example in enumerate(examples, 1):
        try:
            example()
        except Exception as e:
            print(f"\n✗ Example {i} failed: {e}")

    print("\n" + "="*70)
    print(" ALL EXAMPLES COMPLETED")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
