"""
Quick script to copy the test story to the news_site for demonstration
"""

from pathlib import Path
import re
import shutil

def main():
    # Source and destination
    source_dir = Path("code_evolver/gradual_chaos_output")
    dest_dir = Path("news_site/stories")
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Find the test story markdown
    test_md = source_dir / "test_parking.md"

    if not test_md.exists():
        print(f"Test story not found at {test_md}")
        print("Run the generator first:")
        print("  python code_evolver/gradual_chaos_generator.py --iterations 4 --topic 'parking' --model gemma3:4b --name test_parking")
        return

    print(f"Reading {test_md}...")
    content = test_md.read_text(encoding='utf-8')

    # Extract each iteration
    iterations = content.split('## Iteration')

    print(f"Found {len(iterations) - 1} iterations")

    version = 0
    for iteration_text in iterations[1:]:  # Skip the header
        # Extract the story content
        lines = iteration_text.split('\n')

        # Find where the actual story starts
        story_lines = []
        in_story = False
        for line in lines:
            if line.strip().startswith('**') or (in_story and line.strip()):
                in_story = True
                story_lines.append(line)
            elif in_story and line.startswith('---'):
                break

        if story_lines:
            # Save as individual version file
            version_file = dest_dir / f"story_01_v{version:02d}.md"
            version_file.write_text('\n'.join(story_lines), encoding='utf-8')
            print(f"  [OK] Saved {version_file.name}")
            version += 1

    print(f"\n[OK] Copied {version} versions to {dest_dir}")
    print("\nNow run the website:")
    print("  cd news_site")
    print("  python app.py")
    print("  Open http://localhost:5000")

if __name__ == "__main__":
    main()
