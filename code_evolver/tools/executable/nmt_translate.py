#!/usr/bin/env python3
"""
NMT Translation Tool - Wrapper for the Neural Machine Translation API.

Usage:
    python nmt_translate.py <prompt>

The prompt should be in one of these formats:
    "Translate to <lang>: <text>"
    "Translate from <src_lang> to <tgt_lang>: <text>"
    "Translate '<text>' to <lang>"

Examples:
    python nmt_translate.py "Translate to German: Hello"
    python nmt_translate.py "Translate from English to French: Hello, world!"
    python nmt_translate.py "Translate 'Goodbye' to Spanish"
"""

import sys
import json
import re
import requests


def parse_translation_prompt(prompt):
    """
    Parse a natural language translation prompt.

    Supported formats:
        - "Translate to <lang>: <text>"
        - "Translate from <src_lang> to <tgt_lang>: <text>"
        - "Translate '<text>' to <lang>"

    Returns:
        dict with keys: text, source_lang, target_lang
    """
    prompt = prompt.strip()

    # Pattern 1: "Translate from <src> to <tgt>: <text>"
    pattern1 = r"translate\s+from\s+(\w+)\s+to\s+(\w+)\s*:\s*(.+)"
    match = re.match(pattern1, prompt, re.IGNORECASE)
    if match:
        src_lang, tgt_lang, text = match.groups()
        return {
            "text": text.strip(),
            "source_lang": normalize_lang_code(src_lang),
            "target_lang": normalize_lang_code(tgt_lang)
        }

    # Pattern 2: "Translate to <tgt>: <text>" (assume English source)
    pattern2 = r"translate\s+to\s+(\w+)\s*:\s*(.+)"
    match = re.match(pattern2, prompt, re.IGNORECASE)
    if match:
        tgt_lang, text = match.groups()
        return {
            "text": text.strip(),
            "source_lang": "en",
            "target_lang": normalize_lang_code(tgt_lang)
        }

    # Pattern 3: "Translate '<text>' to <lang>"
    pattern3 = r"translate\s+['\"](.+?)['\"]\s+to\s+(\w+)"
    match = re.match(pattern3, prompt, re.IGNORECASE)
    if match:
        text, tgt_lang = match.groups()
        return {
            "text": text.strip(),
            "source_lang": "en",
            "target_lang": normalize_lang_code(tgt_lang)
        }

    # Default: treat entire prompt as text, translate from English to German
    return {
        "text": prompt,
        "source_lang": "en",
        "target_lang": "de"
    }


def normalize_lang_code(lang):
    """
    Convert language name to ISO 639-1 two-letter code.

    Examples:
        "English" -> "en"
        "German" -> "de"
        "en" -> "en" (already normalized)
    """
    lang_map = {
        "english": "en",
        "spanish": "es",
        "french": "fr",
        "german": "de",
        "italian": "it",
        "portuguese": "pt",
        "dutch": "nl",
        "russian": "ru",
        "chinese": "zh",
        "japanese": "ja",
        "korean": "ko",
        "arabic": "ar",
        "hindi": "hi"
    }

    lang_lower = lang.lower().strip()

    # If already a 2-letter code, return as-is
    if len(lang_lower) == 2 and lang_lower.isalpha():
        return lang_lower

    # Look up in map
    return lang_map.get(lang_lower, lang_lower)


def translate(text, source_lang="en", target_lang="de", beam_size=5):
    """
    Call the NMT API to translate text.

    Args:
        text: Text to translate (string)
        source_lang: ISO 639-1 source language code
        target_lang: ISO 639-1 target language code
        beam_size: Beam search size (default: 5)

    Returns:
        Translated text (string)
    """
    url = "http://localhost:8000/translate"

    params = {
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "beam_size": beam_size,
        "perform_sentence_splitting": "true"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        result = response.json()

        # Check for errors
        if result.get("error"):
            return json.dumps({"error": f"Translation failed: {result['error']}"})

        # Extract translation
        translations = result.get("translations", [])
        if translations:
            return translations[0] if isinstance(translations, list) else translations

        return json.dumps({"error": "No translation returned"})

    except requests.exceptions.ConnectionError:
        return json.dumps({"error": "NMT service not available at http://localhost:8000"})
    except requests.exceptions.Timeout:
        return json.dumps({"error": "Translation request timed out"})
    except Exception as e:
        return json.dumps({"error": f"Translation error: {str(e)}"})


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing prompt. Usage: nmt_translate.py <prompt>"}))
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])

    # Parse the prompt
    params = parse_translation_prompt(prompt)

    # Translate
    result = translate(
        text=params["text"],
        source_lang=params["source_lang"],
        target_lang=params["target_lang"]
    )

    # Output result
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
