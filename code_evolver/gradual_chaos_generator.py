"""
Gradual Chaos News Generator

Starts with MUNDANE village news, then progressively adds ONE odd thing at a time.
Each story is written by a different persona for variety.
Temperature is high to encourage creativity while maintaining coherence.
"""

import json
import os
import random
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import requests

# Different writer personas for variety
WRITER_PERSONAS = [
    "a retired local journalist who loves community events",
    "an enthusiastic young reporter fresh out of journalism school",
    "a cynical veteran correspondent who's seen it all",
    "a poetic writer who finds beauty in everyday moments",
    "a practical, no-nonsense news writer who sticks to facts",
    "an eccentric columnist with a quirky writing style",
    "a former tabloid writer trying to write serious news",
    "a philosophical observer who sees deeper meaning in small events"
]

# Mundane starting topics for Older Dailly
MUNDANE_STARTERS = [
    "village council meeting about parking regulations",
    "local bus route to Girvan schedule changes",
    "community garden produces record harvest",
    "library announces extended opening hours",
    "post office queues during pension day",
    "parish newsletter discusses church roof repairs",
    "village shop introduces new opening times",
    "residents debate location of new bench near the stile",
    "local school holds bake sale fundraiser",
    "community centre tea morning well attended"
]

# Progressive oddification prompts - absurdist UK comedy style
ODDIFICATION_LEVELS = [
    "Add ONE slightly unusual but plausible detail that makes people do a double-take",
    "Add ONE peculiar detail - something odd that's mentioned completely matter-of-factly",
    "Introduce ONE genuinely weird element as if it's perfectly normal village news",
    "Add ONE surreal detail that escalates the absurdity (inspired by British sketch comedy)",
    "Escalate with ONE more bizarre element - things are getting properly strange now",
    "Add ONE completely absurd detail while maintaining the formal news tone",
    "Introduce ONE final level of chaos - full absurdist territory",
    "Maximum weirdness: throw in something utterly nonsensical as the cherry on top"
]


def call_ollama(prompt: str, model: str = "gemma2:9b", temperature: float = 0.88, max_tokens: int = 800) -> str:
    """Call Ollama API for text generation with configurable temperature."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
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


class GradualChaosGenerator:
    def __init__(self, model: str = "gemma2:9b"):
        self.model = model
        self.output_dir = Path("code_evolver/gradual_chaos_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_initial_story(self, topic: str, writer_persona: str, temperature: float = 0.85) -> str:
        """Generate the initial MUNDANE story."""
        prompt = f"""You are {writer_persona}.

Write a short (150-200 word), completely MUNDANE local news article about:
"{topic}"

Make it ordinary, everyday, unremarkable village news. Nothing exciting happens.
Just regular people doing regular things in a regular way.

Write in proper news article format with a headline."""

        return call_ollama(prompt, model=self.model, temperature=temperature, max_tokens=400)

    def oddify_story(self, current_story: str, oddification_prompt: str,
                     writer_persona: str, iteration: int, temperature: float = 0.9) -> str:
        """Add ONE odd thing to the existing story."""
        prompt = f"""You are {writer_persona}.

Here's a news story so far:

{current_story}

Task: {oddification_prompt}

Important:
- Add ONLY ONE new odd element
- Keep everything from the previous story
- Maintain the news article format
- The new odd thing should feel like a natural (if weird) progression
- Rewrite the article incorporating this new element seamlessly
- Update the headline if needed to reflect the growing strangeness

Write the complete updated article (200-250 words)."""

        return call_ollama(prompt, model=self.model, temperature=temperature, max_tokens=500)

    def generate_chaos_sequence(self, iterations: int = 5,
                                starting_topic: str = None,
                                temperature: float = 0.88) -> List[Dict[str, Any]]:
        """Generate a sequence of progressively weirder stories."""

        # Pick random mundane starter if not provided
        if starting_topic is None:
            starting_topic = random.choice(MUNDANE_STARTERS)

        stories = []

        # Generate initial mundane story
        print(f"\n{'='*60}")
        print(f"ITERATION 0: MUNDANE START")
        print(f"Topic: {starting_topic}")
        print(f"{'='*60}\n")

        writer_persona = random.choice(WRITER_PERSONAS)
        print(f"Writer: {writer_persona}\n")

        current_story = self.generate_initial_story(starting_topic, writer_persona, temperature)
        print(current_story)
        print(f"\n{'='*60}\n")

        stories.append({
            "iteration": 0,
            "description": "MUNDANE START",
            "writer": writer_persona,
            "story": current_story,
            "temperature": temperature
        })

        # Progressive oddification
        for i in range(iterations):
            # New writer for each iteration
            writer_persona = random.choice(WRITER_PERSONAS)

            # Get appropriate oddification level
            oddification_idx = min(i, len(ODDIFICATION_LEVELS) - 1)
            oddification_prompt = ODDIFICATION_LEVELS[oddification_idx]

            print(f"{'='*60}")
            print(f"ITERATION {i+1}: ADDING ODDNESS")
            print(f"Instruction: {oddification_prompt}")
            print(f"Writer: {writer_persona}")
            print(f"{'='*60}\n")

            # Slightly increase temperature as chaos grows
            iteration_temp = min(temperature + (i * 0.02), 1.0)

            current_story = self.oddify_story(
                current_story,
                oddification_prompt,
                writer_persona,
                i + 1,
                iteration_temp
            )

            print(current_story)
            print(f"\n{'='*60}\n")

            stories.append({
                "iteration": i + 1,
                "description": oddification_prompt,
                "writer": writer_persona,
                "story": current_story,
                "temperature": iteration_temp
            })

        return stories

    def save_sequence(self, stories: List[Dict[str, Any]], session_name: str = None):
        """Save the story sequence to a file."""
        if session_name is None:
            session_name = f"chaos_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Save as JSON
        json_path = self.output_dir / f"{session_name}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(stories, f, indent=2, ensure_ascii=False)

        # Save as readable markdown
        md_path = self.output_dir / f"{session_name}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Gradual Chaos News Sequence\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"---\n\n")

            for story in stories:
                f.write(f"## Iteration {story['iteration']}: {story['description']}\n\n")
                f.write(f"**Writer:** {story['writer']}\n\n")
                f.write(f"**Temperature:** {story['temperature']:.3f}\n\n")
                f.write(f"{story['story']}\n\n")
                f.write(f"---\n\n")

        print(f"\nSaved to:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")

        return json_path, md_path


def main():
    """Run the gradual chaos generator."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate progressively weirder news stories")
    parser.add_argument("--iterations", type=int, default=5,
                       help="Number of oddification iterations (default: 5)")
    parser.add_argument("--topic", type=str, default=None,
                       help="Starting mundane topic (random if not specified)")
    parser.add_argument("--temperature", type=float, default=0.88,
                       help="Base temperature for generation (default: 0.88)")
    parser.add_argument("--model", type=str, default="gemma2:9b",
                       help="Ollama model to use (default: gemma2:9b)")
    parser.add_argument("--name", type=str, default=None,
                       help="Session name for output files")

    args = parser.parse_args()

    print("GRADUAL CHAOS NEWS GENERATOR")
    print("============================")
    print(f"Starting with: {args.topic or 'random mundane topic'}")
    print(f"Iterations: {args.iterations}")
    print(f"Base temperature: {args.temperature}")
    print(f"Model: {args.model}")
    print()

    generator = GradualChaosGenerator(model=args.model)

    stories = generator.generate_chaos_sequence(
        iterations=args.iterations,
        starting_topic=args.topic,
        temperature=args.temperature
    )

    generator.save_sequence(stories, session_name=args.name)

    print("\nChaos generation complete!")


if __name__ == "__main__":
    main()
