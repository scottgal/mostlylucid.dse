import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from node_runtime import call_tool


def main():
    input_data = json.load(sys.stdin)

    # Extract user's request description
task_description = input_data.get('description', '')
# Build a detailed prompt for the LLM based on the task
# Example: If task is 'tell a joke about cats', prompt could be 'Write a funny joke about cats'
prompt = f'Generate content for: {task_description}'
# CRITICAL: Always use call_tool() for content generation - NEVER hardcode content
content = call_tool('content_generator', prompt)
print(json.dumps({'result': content}))
if __name__ == '__main__':
    main()
