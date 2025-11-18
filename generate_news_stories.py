"""
Generate multiple story sequences for the Oldest Dailly Gazette
Each story gets 10 iterations of increasing weirdness
"""

import sys
import os
import subprocess
from pathlib import Path
import shutil

# Topics for different stories
STORY_TOPICS = [
    "parish council debates new parking restrictions",
    "annual village fete raises funds for church roof",
    "local WI group holds jam making competition",
    "roadworks announced for high street next week",
    "new postman starts rounds in village",
    "library book club discusses latest bestseller",
    "planning permission sought for garden shed extension",
    "village cricket team loses to neighboring town",
    "residents complain about bins collection changes",
    "community garden produces record-breaking marrow",
]

def generate_story(story_num: int, topic: str, output_dir: Path):
    """Generate one story sequence with 10 versions."""
    print(f"\n{'='*70}")
    print(f"GENERATING STORY {story_num}: {topic}")
    print(f"{'='*70}")

    # Run the generator
    cmd = [
        "python",
        "code_evolver/gradual_chaos_generator.py",
        "--iterations", "9",  # 0-9 = 10 versions total
        "--topic", topic,
        "--temperature", "0.93",  # High temperature for creativity
        "--model", "gemma3:4b",
        "--name", f"temp_story_{story_num}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR generating story {story_num}:")
        print(result.stderr)
        return False

    # Move generated files to correct naming scheme
    temp_output_dir = Path("code_evolver/gradual_chaos_output")

    # The generator creates markdown with session name
    generated_md = temp_output_dir / f"temp_story_{story_num}.md"

    if generated_md.exists():
        # Parse the markdown to extract individual versions
        content = generated_md.read_text(encoding='utf-8')

        # Extract each iteration
        iterations = content.split('## Iteration')

        version = 0
        for iteration_text in iterations[1:]:  # Skip the header
            # Extract the story content
            lines = iteration_text.split('\n')

            # Find where the actual story starts (after metadata)
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
                version_file = output_dir / f"story_{story_num:02d}_v{version:02d}.md"
                version_file.write_text('\n'.join(story_lines), encoding='utf-8')
                print(f"  ✓ Saved version {version}")
                version += 1

        # Clean up temp files
        generated_md.unlink()
        temp_json = temp_output_dir / f"temp_story_{story_num}.json"
        if temp_json.exists():
            temp_json.unlink()

        print(f"✓ Story {story_num} complete ({version} versions)")
        return True
    else:
        print(f"✗ Failed to generate story {story_num}")
        return False


def main():
    """Generate all stories for the news site."""
    print("="*70)
    print("OLDER DAILLY - STORY GENERATOR")
    print("="*70)

    # Create output directory
    output_dir = Path("news_site/stories")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clear existing stories
    for old_file in output_dir.glob("*.md"):
        old_file.unlink()
    print(f"\nOutput directory: {output_dir.absolute()}")
    print(f"Generating {len(STORY_TOPICS)} stories with 10 versions each...")

    # Generate each story
    success_count = 0
    for i, topic in enumerate(STORY_TOPICS, 1):
        if generate_story(i, topic, output_dir):
            success_count += 1

    print("\n" + "="*70)
    print("GENERATION COMPLETE")
    print("="*70)
    print(f"Successfully generated: {success_count}/{len(STORY_TOPICS)} stories")
    print(f"Total versions: {success_count * 10}")
    print(f"Output location: {output_dir.absolute()}")
    print("\nTo start the website:")
    print("  cd news_site")
    print("  python app.py")
    print("  Open http://localhost:5000")


if __name__ == "__main__":
    main()
