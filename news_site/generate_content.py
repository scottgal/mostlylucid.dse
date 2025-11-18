"""
Continuous content generator for Older Dailly Gazette
Leave this running to continuously generate new stories in the background
"""

import sys
import os
import subprocess
import time
import random
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Extended topics for Older Dailly
STORY_TOPICS = [
    # Council & Planning
    "parish council debates new parking restrictions near the stile",
    "planning permission sought for garden shed extension on Dailly Road",
    "village council discusses streetlight replacement program",
    "residents petition for new litter bins on the high street",
    "council considers extending library opening hours",

    # Community Events
    "annual village fete raises funds for church roof repairs",
    "local WI group holds jam making competition",
    "community centre tea morning well attended",
    "village choir rehearses for Christmas concert",
    "gardening club plans spring flower show",

    # Transport & Infrastructure
    "local bus route to Girvan schedule changes announced",
    "roadworks planned for high street next week",
    "new footpath proposed near the old stile",
    "pothole repairs scheduled for Station Road",
    "bus shelter vandalism reported to police",

    # Local Business
    "village shop introduces new opening times",
    "post office queues during pension day",
    "local bakery wins South Ayrshire award",
    "butcher shop celebrates 50 years in village",
    "new owner takes over newsagent shop",

    # Schools & Youth
    "local school holds bake sale fundraiser",
    "primary school pupils visit Culzean Castle",
    "school football team loses to Crosshill",
    "parent teacher association plans fundraiser",
    "school library receives book donation",

    # Nature & Environment
    "community garden produces record-breaking marrow",
    "rare bird spotted near Dailly Water",
    "litter pick volunteers clear village green",
    "resident complains about overflowing bins",
    "wildflower meadow planted at cemetery",

    # Crime & Safety (mild)
    "bicycle reported stolen from outside shop",
    "speeding concerns raised on Girvan Road",
    "neighborhood watch meeting scheduled",
    "dog fouling fines to be enforced",
    "village bobby retires after 30 years",

    # Heritage & History
    "local historian gives talk on village history",
    "old photographs discovered in church attic",
    "memorial bench dedicated to former councillor",
    "historical society seeks volunteers",
    "restoration planned for old milestone",

    # Weather & Seasons
    "heavy rain causes flooding on Main Street",
    "first frost of winter arrives early",
    "snowdrop walk scheduled for February",
    "village prepares for annual summer gala",
    "autumn leaves block drainage gullies",

    # Miscellaneous
    "library announces new book club dates",
    "residents debate location of new bench",
    "village newsletter goes digital",
    "lost cat reunited with owner",
    "church bell restoration fund launched",
    "Old Bob Galloway stealing apples / doing other rapscalion stuff"
]

def generate_story(story_num: int, topic: str, stories_dir: Path, model: str = "gemma3:4b"):
    """Generate one story sequence with 10 versions."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Generating story {story_num}: {topic[:50]}...")

    # Get absolute paths
    project_root = Path(__file__).parent.parent
    generator_script = project_root / "code_evolver" / "gradual_chaos_generator.py"

    # Run the generator from project root
    cmd = [
        "python",
        str(generator_script),
        "--iterations", "9",
        "--topic", topic,
        "--temperature", str(random.uniform(0.90, 0.95)),  # Random high temp
        "--model", model,
        "--name", f"temp_story_{story_num}"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                               cwd=str(project_root))  # Run from project root

        if result.returncode != 0:
            print(f"[{timestamp}] ERROR: {result.stderr[:200]}")
            return False

        # Process generated markdown
        temp_output_dir = Path(__file__).parent.parent / "code_evolver" / "gradual_chaos_output"
        generated_md = temp_output_dir / f"temp_story_{story_num}.md"

        if generated_md.exists():
            content = generated_md.read_text(encoding='utf-8')
            iterations = content.split('## Iteration')

            version = 0
            for iteration_text in iterations[1:]:
                lines = iteration_text.split('\n')
                story_lines = []
                in_story = False

                for line in lines:
                    if line.strip().startswith('**') or (in_story and line.strip()):
                        in_story = True
                        story_lines.append(line)
                    elif in_story and line.startswith('---'):
                        break

                if story_lines:
                    version_file = stories_dir / f"story_{story_num:02d}_v{version:02d}.md"
                    version_file.write_text('\n'.join(story_lines), encoding='utf-8')
                    version += 1

            # Clean up temp files
            generated_md.unlink()
            temp_json = temp_output_dir / f"temp_story_{story_num}.json"
            if temp_json.exists():
                temp_json.unlink()

            print(f"[{timestamp}] ✓ Story {story_num} complete ({version} versions)")
            return True
        else:
            print(f"[{timestamp}] ✗ Failed - no output file")
            return False

    except subprocess.TimeoutExpired:
        print(f"[{timestamp}] ✗ Timeout after 5 minutes")
        return False
    except Exception as e:
        print(f"[{timestamp}] ✗ Error: {str(e)[:100]}")
        return False


def main():
    """Continuously generate stories."""
    print("="*70)
    print("OLDER DAILLY GAZETTE - CONTINUOUS CONTENT GENERATOR")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Available topics: {len(STORY_TOPICS)}")
    print("Press Ctrl+C to stop")
    print("="*70)
    print()

    # Setup
    stories_dir = Path(__file__).parent / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)

    # Check which model to use
    model = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
    print(f"Using model: {model}")
    print()

    # Track statistics
    story_num = 1
    success_count = 0
    fail_count = 0

    # Shuffle topics for variety
    topics = STORY_TOPICS.copy()
    random.shuffle(topics)

    try:
        while True:
            # Pick next topic (cycle through all topics)
            topic = topics[(story_num - 1) % len(topics)]

            # Generate story
            if generate_story(story_num, topic, stories_dir, model):
                success_count += 1
            else:
                fail_count += 1

            # Statistics
            total = success_count + fail_count
            success_rate = (success_count / total * 100) if total > 0 else 0

            print(f"Stats: {success_count} success, {fail_count} failed ({success_rate:.1f}% success rate)")
            print()

            story_num += 1

            # Small delay between stories (to avoid overwhelming the system)
            time.sleep(2)

    except KeyboardInterrupt:
        print()
        print("="*70)
        print("GENERATOR STOPPED")
        print("="*70)
        print(f"Total stories generated: {success_count}")
        print(f"Failed attempts: {fail_count}")
        print(f"Final count: {success_count} stories with 10 versions each")
        print(f"Location: {stories_dir.absolute()}")
        print()


if __name__ == "__main__":
    main()
