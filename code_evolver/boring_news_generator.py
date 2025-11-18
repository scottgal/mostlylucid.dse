#!/usr/bin/env python3
"""
Boring UK Local News Generator with Progressive Monty Python Weirdness
Generates mundane local news stories that gradually become absurd.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import requests

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def call_ollama(prompt: str, model: str = "gemma3:4b", max_tokens: int = 1000) -> str:
    """Call Ollama API for text generation."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.8,
                }
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return ""


def generate_base_story(story_num: int) -> dict:
    """Generate a boring baseline UK local news story."""

    prompt = f"""Generate a VERY boring UK (Scotland) local news story (story #{story_num}).
The story should be mundane, dry, and typical of small-town Scottish local village news.

Format as:
# [Headline]

## [Subheading]

[3-4 paragraphs of boring local news content]

Topics could include: gardening clubs, mens shed meetings, allotments, 'troubled teens', 'buskers', the welsh, parish council meetings, roadworks, charity bake sales,
planning applications, local sports results, school fetes, recycling changes, etc.

Keep it dry, factual, and incredibly dull. Use British spelling and place names.
Maximum 300 words total."""

    content = call_ollama(prompt, max_tokens=800)

    # Parse the content to extract headline
    lines = content.split('\n')
    headline = "Local News Update"
    for line in lines:
        if line.startswith('# '):
            headline = line.replace('# ', '').strip()
            break

    return {
        "story_num": story_num,
        "headline": headline,
        "content": content,
        "weirdness_level": 0
    }


def add_weirdness(base_story: dict, iteration: int) -> dict:
    """Add progressive Monty Python-style weirdness to a story."""

    weirdness_percent = iteration * 10  # 10%, 20%, 30%... up to 100%

    prompt = f"""Take this boring UK local news story and add {weirdness_percent}% weirdness.

Original story:
{base_story['content']}

Instructions:
- Keep the overall story structure and main facts
- Add {iteration} subtle absurdist (uk comedy) references
- Make them casual passing mentions, not the main focus
- Examples: dragons running for mayor, unexpected Spanish Inquisitions,
  knights who say "Ni" at council meetings, blood skies, exploding frogs, dead parrots in pet shops,
   etc. (be creative)
- Slip in as if normal mentions of a sentient Raven named Corvus (who may or may not own this newspaper) in a conspiratorial tone
- The weirder elements should seem almost normal in context
- Keep British tone and local news style
- Maximum 350 words total

Return the FULL modified story in the same markdown format."""

    content = call_ollama(prompt, max_tokens=1000)

    # Parse headline
    lines = content.split('\n')
    headline = base_story['headline']
    for line in lines:
        if line.startswith('# '):
            headline = line.replace('# ', '').strip()
            break

    return {
        "story_num": base_story['story_num'],
        "headline": headline,
        "content": content,
        "weirdness_level": weirdness_percent,
        "iteration": iteration
    }


def save_story(story: dict, output_dir: Path):
    """Save a story to a markdown file."""

    # Create filename: story_01_v00.md, story_01_v01.md, etc.
    story_num = story['story_num']
    iteration = story.get('iteration', 0)
    filename = f"story_{story_num:02d}_v{iteration:02d}.md"

    filepath = output_dir / filename

    # Add metadata header
    metadata = f"""---
story_number: {story_num}
iteration: {iteration}
weirdness_level: {story.get('weirdness_level', 0)}%
generated: {datetime.now().isoformat()}
---

"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(metadata)
        f.write(story['content'])
        f.write('\n')

    print(f"[OK] Saved: {filename} (weirdness: {story.get('weirdness_level', 0)}%)")


def main():
    """Main execution function."""
    print("=" * 70)
    print("UK Local News Generator with Progressive Monty Python Weirdness")
    print("=" * 70)
    print()

    # Create output directory
    output_dir = Path(__file__).parent / "boring_news_output"
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}")
    print()

    num_stories = 20
    num_iterations = 10

    for story_num in range(1, num_stories + 1):
        print(f"\n{'='*70}")
        print(f"Story {story_num}/{num_stories}")
        print(f"{'='*70}")

        # Generate base boring story
        print(f"Generating baseline story {story_num}...")
        base_story = generate_base_story(story_num)
        save_story(base_story, output_dir)

        # Generate 10 progressively weirder variations
        for iteration in range(1, num_iterations + 1):
            print(f"  Generating iteration {iteration}/10 ({iteration * 10}% weird)...")
            weird_story = add_weirdness(base_story, iteration)
            save_story(weird_story, output_dir)

        print(f"[OK] Completed story {story_num} with {num_iterations} variations")

    print()
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"Total stories generated: {num_stories}")
    print(f"Variations per story: {num_iterations + 1} (baseline + 10 iterations)")
    print(f"Total files: {num_stories * (num_iterations + 1)}")
    print(f"Output location: {output_dir.absolute()}")
    print()


if __name__ == "__main__":
    main()
