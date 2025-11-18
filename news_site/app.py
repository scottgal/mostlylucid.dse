"""
Old Dailly Gazette - A plausible-looking local news site
with a 'Fit My Likes' feature that makes stories progressively weirder
"""

from flask import Flask, render_template, jsonify, send_from_directory
from pathlib import Path
import json
import re
from datetime import datetime, timedelta
import random
import markdown

app = Flask(__name__)

# Configure markdown with extensions
md = markdown.Markdown(extensions=['extra', 'nl2br'])

# Path to stories
STORIES_DIR = Path(__file__).parent / "stories"

def parse_story_markdown(md_content: str) -> dict:
    """Parse markdown story file to extract headline, lure, and full content."""
    lines = md_content.split('\n')

    # Strip metadata lines and dividers
    cleaned_lines = []
    headline = ""

    for line in lines:
        # Skip metadata lines (Writer:, Temperature:, etc.)
        if line.startswith('**Writer:') or line.startswith('Writer:') or \
           line.startswith('**Temperature:') or line.startswith('Temperature:') or \
           line.startswith('**Iteration:') or line.startswith('Iteration:') or \
           line.startswith('**Model:') or line.startswith('Model:') or \
           line.strip() == '---':
            continue

        # Extract headline (bold text that looks like a headline)
        if line.startswith('**') and line.endswith('**') and len(line) > 10:
            potential_headline = line.strip('*').strip()
            # Check if it's not a metadata field
            if ':' not in potential_headline[:20]:  # Headline shouldn't have : near start
                headline = potential_headline
                continue

        cleaned_lines.append(line)

    # Rejoin cleaned content
    clean_content = '\n'.join(cleaned_lines).strip()

    # Extract lure (first paragraph)
    lure = ""
    paragraphs = []
    for line in cleaned_lines:
        if line.strip() and len(line.strip()) > 50:
            paragraphs.append(line.strip())
            if len(paragraphs) >= 1:
                break

    if paragraphs:
        lure = paragraphs[0]
        if len(lure) > 150:
            lure = lure[:147] + '...'

    # Convert cleaned markdown to HTML for display
    html_content = md.convert(clean_content)

    return {
        "headline": headline or "Local News Update",
        "lure": lure or "Read the full story inside.",
        "content": html_content,
        "raw_content": clean_content
    }

def get_all_stories() -> list:
    """Load all story sequences from the stories directory."""
    stories = []

    if not STORIES_DIR.exists():
        return stories

    # Group stories by base name (story_01, story_02, etc)
    story_groups = {}

    for md_file in STORIES_DIR.glob("*.md"):
        # Parse filename: story_01_v00.md -> story_01, version 00
        match = re.match(r'story_(\d+)_v(\d+)\.md', md_file.name)
        if match:
            story_num = match.group(1)
            version = int(match.group(2))

            if story_num not in story_groups:
                story_groups[story_num] = {}

            # Read and parse the story
            content = md_file.read_text(encoding='utf-8')
            parsed = parse_story_markdown(content)

            story_groups[story_num][version] = {
                "filename": md_file.name,
                "version": version,
                **parsed
            }

    # Convert to list format
    for story_num, versions in sorted(story_groups.items()):
        if versions:  # Only include if has versions
            # Get version 0 for the list view
            base_story = versions.get(0, list(versions.values())[0])

            # Generate random recent date
            days_ago = random.randint(0, 14)
            pub_date = (datetime.now() - timedelta(days=days_ago)).strftime("%d %B %Y")

            # Random byline
            bylines = [
                "Emily Weatherby, Community Correspondent",
                "James Thornton, Local Affairs",
                "Margaret Fletcher, Senior Reporter",
                "Oliver Pritchard, Village News",
                "Sarah Montague, Chief Reporter",
                "Henry Blackwell, Rural Correspondent"
            ]

            stories.append({
                "id": f"story_{story_num}",
                "story_num": story_num,
                "headline": base_story["headline"],
                "lure": base_story["lure"],
                "byline": random.choice(bylines),
                "date": pub_date,
                "max_version": max(versions.keys()),
                "versions": versions
            })

    return stories

@app.route('/')
def index():
    """Homepage with list of stories."""
    stories = get_all_stories()
    return render_template('index.html', stories=stories)

@app.route('/story/<story_id>')
def story(story_id):
    """View a single story."""
    stories = get_all_stories()

    # Find the story
    story_data = None
    for s in stories:
        if s['id'] == story_id:
            story_data = s
            break

    if not story_data:
        return "Story not found", 404

    return render_template('story.html', story=story_data)

@app.route('/api/story/<story_num>/version/<int:version>')
def get_story_version(story_num, version):
    """API endpoint to get a specific version of a story."""
    stories = get_all_stories()

    for s in stories:
        if s['story_num'] == story_num:
            if version in s['versions']:
                return jsonify({
                    "success": True,
                    "version": version,
                    "max_version": s['max_version'],
                    "headline": s['versions'][version]['headline'],
                    "content": s['versions'][version]['content']
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Version not found"
                }), 404

    return jsonify({
        "success": False,
        "error": "Story not found"
    }), 404

if __name__ == '__main__':
    app.run(debug=True, port=5050)
