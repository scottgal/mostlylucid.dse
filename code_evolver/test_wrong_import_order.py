# Test file with WRONG import order
import json
import sys
from pathlib import Path

# Path setup comes too late!
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool  # ❌ This comes BEFORE path setup

def main():
    result = call_tool('content_generator', 'test')
    print(json.dumps({'result': result}))

if __name__ == '__main__':
    main()
