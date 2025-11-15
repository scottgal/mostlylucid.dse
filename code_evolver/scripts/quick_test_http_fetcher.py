"""
Quick verification test for HTTP Content Fetcher.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from http_content_fetcher import create_http_fetcher


def quick_test():
    """Run a quick verification test."""
    print("HTTP Content Fetcher - Quick Verification Test")
    print("=" * 60)

    fetcher = create_http_fetcher()

    # Test 1: Basic GET
    print("\n[1/5] Testing basic GET request...")
    result1 = fetcher.get('https://jsonplaceholder.typicode.com/posts/1')
    if result1['success'] and result1['status_code'] == 200:
        print(f"  ✓ GET request successful (status {result1['status_code']})")
    else:
        print(f"  ✗ GET request failed: {result1.get('error', 'Unknown error')}")
        return False

    # Test 2: POST with JSON
    print("\n[2/5] Testing POST with JSON body...")
    result2 = fetcher.post(
        'https://jsonplaceholder.typicode.com/posts',
        body={'title': 'Test', 'body': 'Test body', 'userId': 1},
        body_type='json'
    )
    if result2['success'] and result2['status_code'] == 201:
        print(f"  ✓ POST request successful (created ID: {result2['data'].get('id', 'N/A')})")
    else:
        print(f"  ✗ POST request failed: {result2.get('error', 'Unknown error')}")
        return False

    # Test 3: Authentication headers
    print("\n[3/5] Testing authentication...")
    result3 = fetcher.get(
        'https://httpbin.org/headers',
        auth={'type': 'bearer', 'token': 'test_token'}
    )
    if result3['success'] and 'Authorization' in result3['data']['headers']:
        print(f"  ✓ Authentication header sent successfully")
    else:
        print(f"  ✗ Authentication test failed")
        return False

    # Test 4: Query parameters
    print("\n[4/5] Testing query parameters...")
    result4 = fetcher.get(
        'https://httpbin.org/get',
        params={'test': 'value', 'page': 1}
    )
    if result4['success'] and result4['data']['args'].get('test') == 'value':
        print(f"  ✓ Query parameters sent successfully")
    else:
        print(f"  ✗ Query parameters test failed")
        return False

    # Test 5: Error handling
    print("\n[5/5] Testing error handling...")
    result5 = fetcher.get('https://httpbin.org/status/404')
    if not result5['success'] and result5['status_code'] == 404:
        print(f"  ✓ Error handling works correctly (404 detected)")
    else:
        print(f"  ✗ Error handling test failed")
        return False

    print("\n" + "=" * 60)
    print("✓ All verification tests passed!")
    print("=" * 60)
    return True


if __name__ == '__main__':
    try:
        success = quick_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
