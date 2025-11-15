"""
Tool for installing Python packages via pip.
Reads package name from stdin as JSON, installs it, and returns status.
"""
import json
import sys
import subprocess


def main():
    """Install Python package via pip."""
    try:
        # Read input
        input_data = json.load(sys.stdin)
        package = input_data.get('package', '')

        if not package:
            print(json.dumps({
                'status': 'failed',
                'error': 'No package specified'
            }))
            return

        # Install package using pip
        # Use --quiet to reduce output, --no-input to avoid prompts
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--quiet', '--no-input', package],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout for installation
        )

        if result.returncode == 0:
            print(json.dumps({
                'status': 'installed',
                'package': package
            }))
        else:
            print(json.dumps({
                'status': 'failed',
                'package': package,
                'error': result.stderr.strip() or result.stdout.strip()
            }))

    except subprocess.TimeoutExpired:
        print(json.dumps({
            'status': 'failed',
            'package': package,
            'error': 'Installation timeout after 120 seconds'
        }))
    except Exception as e:
        print(json.dumps({
            'status': 'failed',
            'error': str(e)
        }))


if __name__ == '__main__':
    main()
