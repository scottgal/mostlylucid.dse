#!/usr/bin/env python3
"""
Language Detection Tool - Detects the language of text content.

Supports two detection methods:
1. NMT API (if available at localhost:8000) - Fast and accurate
2. LLM Fallback - Uses a quick LLM call with a text chunk

Usage:
    python language_detector.py

Input (JSON via stdin):
    {
        "text": "Text to detect language for",
        "method": "auto|nmt|llm",  # optional, default: auto
        "max_chunk_size": 500      # optional, for LLM method
    }

Output (JSON):
    {
        "success": true,
        "language": "en",
        "language_name": "English",
        "confidence": 0.95,
        "method_used": "nmt|llm",
        "message": "Language detected successfully"
    }
"""

import sys
import json
import re
from typing import Dict, Any, Optional

# Try to import optional dependencies
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class LanguageDetector:
    """
    Detects the language of text content using multiple methods.
    """

    # ISO 639-1 language codes to names
    LANGUAGE_NAMES = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'nl': 'Dutch',
        'ru': 'Russian',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ko': 'Korean',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'pl': 'Polish',
        'tr': 'Turkish',
        'vi': 'Vietnamese',
        'th': 'Thai',
        'sv': 'Swedish',
        'da': 'Danish',
        'fi': 'Finnish',
        'no': 'Norwegian',
        'cs': 'Czech',
        'el': 'Greek',
        'he': 'Hebrew',
        'id': 'Indonesian',
        'ms': 'Malay',
        'ro': 'Romanian',
        'uk': 'Ukrainian',
    }

    # Simple language detection patterns (basic heuristics)
    LANGUAGE_PATTERNS = {
        'en': [r'\b(the|and|is|are|was|were|have|has|will|would|can|could)\b'],
        'es': [r'\b(el|la|los|las|de|que|en|es|por|para|con|una?)\b'],
        'fr': [r'\b(le|la|les|de|et|un|une|dans|pour|avec|est|sont)\b'],
        'de': [r'\b(der|die|das|und|ist|sind|von|zu|mit|den|dem)\b'],
        'it': [r'\b(il|la|lo|le|di|che|è|sono|da|per|con|un)\b'],
        'pt': [r'\b(o|a|os|as|de|que|em|é|para|com|um|uma)\b'],
        'ru': [r'[а-яА-Я]{3,}'],  # Cyrillic characters
        'zh': [r'[\u4e00-\u9fff]{2,}'],  # Chinese characters
        'ja': [r'[\u3040-\u309f\u30a0-\u30ff]{2,}'],  # Hiragana/Katakana
        'ko': [r'[\uac00-\ud7af]{2,}'],  # Hangul
        'ar': [r'[\u0600-\u06ff]{3,}'],  # Arabic
        'el': [r'[\u0370-\u03ff]{3,}'],  # Greek
        'he': [r'[\u0590-\u05ff]{3,}'],  # Hebrew
        'th': [r'[\u0e00-\u0e7f]{3,}'],  # Thai
    }

    def __init__(self, nmt_url: str = "http://localhost:8000"):
        """
        Initialize Language Detector.

        Args:
            nmt_url: Base URL for NMT service
        """
        self.nmt_url = nmt_url
        self.nmt_available = None  # Lazy check

    def detect(
        self,
        text: str,
        method: str = "auto",
        max_chunk_size: int = 500
    ) -> Dict[str, Any]:
        """
        Detect the language of text.

        Args:
            text: Text to detect language for
            method: Detection method ('auto', 'nmt', 'llm', 'heuristic')
            max_chunk_size: Maximum text chunk size for LLM method

        Returns:
            Result dictionary with detected language
        """
        try:
            if not text or not text.strip():
                return self._error("No text provided for language detection")

            # Truncate text to reasonable size for detection
            detection_text = text[:2000]  # First 2000 chars should be enough

            # Choose detection method
            if method == "auto":
                # Try NMT first, then heuristic, then LLM
                result = self._detect_with_nmt(detection_text)
                if result['success']:
                    return result

                result = self._detect_with_heuristics(detection_text)
                if result['success'] and result.get('confidence', 0) > 0.3:
                    return result

                # Fall back to LLM (if heuristics failed or low confidence)
                # For now, return heuristic result even with low confidence
                # since LLM detection is not implemented
                if result['success']:
                    result['message'] = 'Language detected using heuristics (LLM fallback not available)'
                    return result

                return self._detect_with_llm(detection_text, max_chunk_size)

            elif method == "nmt":
                return self._detect_with_nmt(detection_text)

            elif method == "llm":
                return self._detect_with_llm(detection_text, max_chunk_size)

            elif method == "heuristic":
                return self._detect_with_heuristics(detection_text)

            else:
                return self._error(f"Unknown detection method: {method}")

        except Exception as e:
            return self._error(f"Language detection failed: {str(e)}")

    def _detect_with_nmt(self, text: str) -> Dict[str, Any]:
        """
        Detect language using NMT service.

        The NMT API might have a /detect endpoint, or we can use
        the /languages endpoint to get supported languages and
        try translations to detect the source language.
        """
        if not HAS_REQUESTS:
            return self._error("NMT detection requires 'requests' library")

        try:
            # Check if NMT service is available (lazy check)
            if self.nmt_available is None:
                self.nmt_available = self._check_nmt_service()

            if not self.nmt_available:
                return self._error("NMT service not available at " + self.nmt_url)

            # Try to use detect endpoint if it exists
            detect_url = f"{self.nmt_url}/detect"

            try:
                response = requests.get(
                    detect_url,
                    params={"text": text[:500]},  # Use first 500 chars
                    timeout=5
                )

                if response.status_code == 200:
                    result = response.json()

                    # Extract language from response
                    # The exact format depends on the API
                    detected_lang = result.get('language') or result.get('detected_language')

                    if detected_lang:
                        return {
                            'success': True,
                            'language': detected_lang,
                            'language_name': self.LANGUAGE_NAMES.get(detected_lang, detected_lang),
                            'confidence': result.get('confidence', 0.9),
                            'method_used': 'nmt',
                            'message': 'Language detected using NMT service'
                        }

            except requests.exceptions.RequestException:
                pass  # /detect endpoint doesn't exist, fall through

            # Fallback: The NMT service may not have a detect endpoint
            # We could try other methods here
            return self._error("NMT service doesn't support language detection")

        except Exception as e:
            return self._error(f"NMT detection error: {str(e)}")

    def _detect_with_heuristics(self, text: str) -> Dict[str, Any]:
        """
        Detect language using simple heuristic patterns.

        This is fast but less accurate than NMT or LLM methods.
        """
        text_lower = text.lower()
        word_count = len(text.split())
        scores = {}

        # Check each language pattern
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches

            if score > 0:
                scores[lang] = score

        if not scores:
            return self._error("Could not detect language using heuristics", success=False)

        # Find language with highest score
        detected_lang = max(scores, key=scores.get)
        max_score = scores[detected_lang]
        total_matches = sum(scores.values())

        # Calculate confidence based on:
        # 1. Ratio of top language to total matches
        # 2. Absolute number of matches relative to text length
        confidence_ratio = max_score / total_matches if total_matches > 0 else 0
        match_density = max_score / max(word_count, 1)

        # Combine both factors
        confidence = min(confidence_ratio * 0.6 + match_density * 0.4, 0.95)

        # Boost confidence if there's a clear winner
        if total_matches > 1:
            second_best = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
            if max_score > second_best * 2:  # Clear winner
                confidence = min(confidence * 1.3, 0.95)

        return {
            'success': True,
            'language': detected_lang,
            'language_name': self.LANGUAGE_NAMES.get(detected_lang, detected_lang),
            'confidence': round(confidence, 2),
            'method_used': 'heuristic',
            'message': 'Language detected using pattern matching',
            'scores': scores  # Include all scores for debugging
        }

    def _detect_with_llm(self, text: str, max_chunk_size: int = 500) -> Dict[str, Any]:
        """
        Detect language using a quick LLM call.

        This uses a small text chunk and asks the LLM to identify the language.
        """
        try:
            # Truncate text to max chunk size
            chunk = text[:max_chunk_size]

            # Create a simple prompt for language detection
            prompt = f"""Identify the language of the following text. Respond with ONLY the ISO 639-1 two-letter language code (e.g., 'en', 'es', 'fr', 'de').

Text:
{chunk}

Language code:"""

            # For now, we'll return a structured response indicating that
            # LLM integration is needed. In a full implementation, this would
            # call the LLM service.
            #
            # Example integration (pseudocode):
            # response = call_llm(prompt, model="fast", max_tokens=10)
            # detected_lang = response.strip().lower()

            return {
                'success': False,
                'error': 'LLM detection requires LLM service integration',
                'message': 'LLM language detection not yet implemented',
                'method_used': 'llm',
                'hint': 'Consider using method="auto" to try NMT or heuristic detection first'
            }

        except Exception as e:
            return self._error(f"LLM detection error: {str(e)}")

    def _check_nmt_service(self) -> bool:
        """
        Check if NMT service is available.

        Returns:
            True if service is reachable, False otherwise
        """
        if not HAS_REQUESTS:
            return False

        try:
            response = requests.get(
                f"{self.nmt_url}/languages",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False

    def _error(self, message: str, success: bool = False) -> Dict[str, Any]:
        """Return error result."""
        return {
            'success': success,
            'error': message,
            'message': message,
            'language': None,
            'language_name': None,
            'confidence': 0.0,
            'method_used': None
        }


def main():
    """
    Main entry point for language detection tool.

    Reads JSON input from stdin and outputs JSON result.
    """
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract parameters
        text = input_data.get('text')
        method = input_data.get('method', 'auto')
        max_chunk_size = input_data.get('max_chunk_size', 500)
        nmt_url = input_data.get('nmt_url', 'http://localhost:8000')

        if not text:
            print(json.dumps({
                'success': False,
                'error': 'Missing required parameter: text'
            }))
            sys.exit(1)

        # Create detector
        detector = LanguageDetector(nmt_url=nmt_url)

        # Detect language
        result = detector.detect(
            text=text,
            method=method,
            max_chunk_size=max_chunk_size
        )

        # Output result
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'message': 'An unexpected error occurred during language detection'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
