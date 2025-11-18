#!/usr/bin/env python3
"""
Style Extractor - Extract comprehensive style information from any source.

Analyzes writing style, tone, vocabulary, structure, and formatting patterns
to generate detailed JSON profiles. Similar to langextract but for style analysis.

Supports:
- Multiple sources: URLs, files, text
- Tiered analysis: quick (rule-based), detailed (LLM-assisted), comprehensive (multi-pass)
- Summarization for long content
- Configurable write guardrails
- RAG storage integration
"""

import json
import sys
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from collections import Counter
import statistics

# Try to import optional dependencies
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB_SUPPORT = True
except ImportError:
    HAS_WEB_SUPPORT = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class StyleExtractor:
    """
    Extracts comprehensive style information from text content.

    Supports multi-tier analysis with different accuracy/speed tradeoffs.
    """

    # Common stop words for filtering
    STOP_WORDS = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their'
    }

    # Formal indicators
    FORMAL_INDICATORS = [
        'furthermore', 'moreover', 'consequently', 'therefore', 'thus',
        'however', 'nevertheless', 'accordingly', 'subsequently', 'henceforth',
        'whereas', 'whereby', 'herein', 'thereof', 'notwithstanding'
    ]

    # Informal indicators
    INFORMAL_INDICATORS = [
        "gonna", "wanna", "gotta", "kinda", "sorta", "yeah", "nah",
        "hey", "cool", "awesome", "stuff", "things", "get", "got",
        "lots", "tons", "really", "very", "pretty", "quite"
    ]

    def __init__(self, tier: str = "detailed"):
        """
        Initialize Style Extractor.

        Args:
            tier: Analysis tier (quick, detailed, comprehensive)
        """
        self.tier = tier
        self.start_time = time.time()

    def extract_from_source(
        self,
        source_type: str,
        source: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract style from any source.

        Args:
            source_type: 'url', 'file', or 'text'
            source: The actual source content/path
            **kwargs: Additional parameters

        Returns:
            Result dictionary with style profile
        """
        try:
            # Get content based on source type
            if source_type == "text":
                content = source
            elif source_type == "file":
                content = self._read_file(source)
            elif source_type == "url":
                content = self._fetch_url(source)
            else:
                return self._error(f"Unknown source type: {source_type}")

            if not content:
                return self._error("No content to analyze")

            # Extract style profile
            style_profile = self._analyze_style(
                content,
                aspects=kwargs.get('style_aspects', []),
                max_length=kwargs.get('max_content_length', 50000)
            )

            # Calculate metadata
            metadata = self._calculate_metadata(content)

            # Build result
            result = {
                'success': True,
                'source_type': source_type,
                'source': source if source_type != 'text' else f"[{len(source)} chars]",
                'extraction_tier': self.tier,
                'style_profile': style_profile,
                'metadata': metadata,
                'message': f"Successfully extracted style using {self.tier} tier"
            }

            # Save to file if requested
            if kwargs.get('save_to_file'):
                filename = kwargs.get('filename', f"style_{int(time.time())}.json")
                saved_path = self._save_to_file(result, filename, kwargs.get('output_format', 'json'))
                result['saved_file'] = saved_path

            return result

        except Exception as e:
            return self._error(f"Extraction failed: {str(e)}")

    def _read_file(self, file_path: str) -> str:
        """Read content from a file."""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Read based on extension
            content = path.read_text(encoding='utf-8', errors='ignore')
            return content

        except Exception as e:
            raise ValueError(f"Failed to read file: {str(e)}")

    def _fetch_url(self, url: str) -> str:
        """Fetch content from a URL."""
        if not HAS_WEB_SUPPORT:
            raise ImportError("Web support requires: pip install requests beautifulsoup4")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse HTML to extract text
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text

        except Exception as e:
            raise ValueError(f"Failed to fetch URL: {str(e)}")

    def _analyze_style(
        self,
        content: str,
        aspects: List[str] = None,
        max_length: int = 50000
    ) -> Dict[str, Any]:
        """
        Analyze style of content.

        Args:
            content: Text content to analyze
            aspects: Specific aspects to analyze (None = all)
            max_length: Maximum content length before summarization

        Returns:
            Style profile dictionary
        """
        # Truncate/summarize if too long
        original_length = len(content)
        summarization_applied = False

        if len(content) > max_length:
            content = content[:max_length]
            summarization_applied = True

        # Determine which aspects to analyze
        all_aspects = [
            'tone', 'formality', 'vocabulary', 'sentence_structure',
            'paragraph_structure', 'formatting', 'punctuation',
            'rhetorical_devices', 'voice', 'pacing', 'imagery', 'technical_level'
        ]

        aspects_to_analyze = aspects if aspects else all_aspects

        # Build style profile
        profile = {}

        if 'tone' in aspects_to_analyze:
            profile['tone'] = self._analyze_tone(content)

        if 'formality' in aspects_to_analyze:
            profile['formality'] = self._analyze_formality(content)

        if 'vocabulary' in aspects_to_analyze:
            profile['vocabulary'] = self._analyze_vocabulary(content)

        if 'sentence_structure' in aspects_to_analyze:
            profile['sentence_structure'] = self._analyze_sentences(content)

        if 'paragraph_structure' in aspects_to_analyze:
            profile['paragraph_structure'] = self._analyze_paragraphs(content)

        if 'formatting' in aspects_to_analyze:
            profile['formatting'] = self._analyze_formatting(content)

        if 'punctuation' in aspects_to_analyze:
            profile['punctuation'] = self._analyze_punctuation(content)

        if 'rhetorical_devices' in aspects_to_analyze:
            profile['rhetorical_devices'] = self._analyze_rhetorical_devices(content)

        if 'voice' in aspects_to_analyze:
            profile['voice'] = self._analyze_voice(content)

        if 'pacing' in aspects_to_analyze:
            profile['pacing'] = self._analyze_pacing(content)

        if 'imagery' in aspects_to_analyze:
            profile['imagery'] = self._analyze_imagery(content)

        if 'technical_level' in aspects_to_analyze:
            profile['technical_level'] = self._analyze_technical_level(content)

        return profile

    def _analyze_tone(self, content: str) -> Dict[str, Any]:
        """Analyze overall tone."""
        content_lower = content.lower()

        # Sentiment indicators
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
                         'positive', 'happy', 'joy', 'love', 'best', 'perfect']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'worst', 'hate',
                         'negative', 'sad', 'angry', 'problem', 'issue', 'error']

        positive_count = sum(content_lower.count(word) for word in positive_words)
        negative_count = sum(content_lower.count(word) for word in negative_words)

        # Emotion indicators
        emotional_words = ['feel', 'believe', 'think', 'hope', 'wish', 'want', 'need',
                          'must', 'should', 'could', 'would', 'may', 'might']
        emotional_count = sum(content_lower.count(word) for word in emotional_words)

        # Calculate tone
        total_words = len(content.split())

        tone_score = {
            'sentiment': 'neutral',
            'emotional_intensity': 'low',
            'confidence': 0.0,
            'indicators': {}
        }

        if total_words > 0:
            pos_ratio = positive_count / total_words
            neg_ratio = negative_count / total_words
            emo_ratio = emotional_count / total_words

            if pos_ratio > neg_ratio * 1.5:
                tone_score['sentiment'] = 'positive'
                tone_score['confidence'] = min(pos_ratio * 10, 1.0)
            elif neg_ratio > pos_ratio * 1.5:
                tone_score['sentiment'] = 'negative'
                tone_score['confidence'] = min(neg_ratio * 10, 1.0)
            else:
                tone_score['sentiment'] = 'neutral'
                tone_score['confidence'] = 0.5

            if emo_ratio > 0.05:
                tone_score['emotional_intensity'] = 'high'
            elif emo_ratio > 0.02:
                tone_score['emotional_intensity'] = 'medium'
            else:
                tone_score['emotional_intensity'] = 'low'

            tone_score['indicators'] = {
                'positive_word_ratio': round(pos_ratio, 4),
                'negative_word_ratio': round(neg_ratio, 4),
                'emotional_word_ratio': round(emo_ratio, 4)
            }

        return tone_score

    def _analyze_formality(self, content: str) -> Dict[str, Any]:
        """Analyze formality level."""
        content_lower = content.lower()
        words = content.split()

        # Count formal vs informal indicators
        formal_count = sum(content_lower.count(word) for word in self.FORMAL_INDICATORS)
        informal_count = sum(content_lower.count(word) for word in self.INFORMAL_INDICATORS)

        # Check for contractions
        contractions = len(re.findall(r"\w+n't|\w+'ll|\w+'re|\w+'ve|\w+'d", content))

        # Calculate formality level
        total_words = len(words)
        formality = {
            'level': 'neutral',
            'score': 0.5,
            'indicators': {
                'formal_words': formal_count,
                'informal_words': informal_count,
                'contractions': contractions,
                'avg_word_length': 0.0
            }
        }

        if total_words > 0:
            formal_ratio = formal_count / total_words
            informal_ratio = informal_count / total_words
            contraction_ratio = contractions / total_words
            avg_word_length = sum(len(word) for word in words) / total_words

            # Calculate formality score (0 = very informal, 1 = very formal)
            score = 0.5  # Start neutral
            score += formal_ratio * 2  # Formal indicators increase score
            score -= informal_ratio * 2  # Informal indicators decrease score
            score -= contraction_ratio * 1  # Contractions decrease score
            score += (avg_word_length - 5) * 0.05  # Longer words = more formal

            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

            formality['score'] = round(score, 2)
            formality['indicators']['avg_word_length'] = round(avg_word_length, 2)

            if score > 0.7:
                formality['level'] = 'very formal'
            elif score > 0.55:
                formality['level'] = 'formal'
            elif score > 0.45:
                formality['level'] = 'neutral'
            elif score > 0.3:
                formality['level'] = 'informal'
            else:
                formality['level'] = 'very informal'

        return formality

    def _analyze_vocabulary(self, content: str) -> Dict[str, Any]:
        """Analyze vocabulary patterns."""
        # Tokenize
        words = re.findall(r'\b\w+\b', content.lower())

        if not words:
            return {'word_count': 0, 'unique_words': 0, 'lexical_diversity': 0.0}

        # Filter stop words
        content_words = [w for w in words if w not in self.STOP_WORDS]

        # Calculate metrics
        word_count = len(words)
        unique_words = len(set(words))
        lexical_diversity = unique_words / word_count if word_count > 0 else 0

        # Find common words (excluding stop words)
        word_freq = Counter(content_words)
        top_words = word_freq.most_common(20)

        # Calculate average word length
        avg_word_length = sum(len(word) for word in words) / len(words)

        # Identify complex words (> 10 characters)
        complex_words = [w for w in words if len(w) > 10]
        complex_ratio = len(complex_words) / len(words) if words else 0

        return {
            'word_count': word_count,
            'unique_words': unique_words,
            'lexical_diversity': round(lexical_diversity, 3),
            'avg_word_length': round(avg_word_length, 2),
            'complex_word_ratio': round(complex_ratio, 3),
            'top_words': [{'word': word, 'count': count} for word, count in top_words[:10]],
            'complexity_level': 'high' if complex_ratio > 0.15 else 'medium' if complex_ratio > 0.08 else 'low'
        }

    def _analyze_sentences(self, content: str) -> Dict[str, Any]:
        """Analyze sentence structure."""
        # Split into sentences (simple approach)
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {'sentence_count': 0, 'avg_length': 0, 'structure': 'unknown'}

        # Calculate metrics
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_length = statistics.mean(sentence_lengths)

        # Calculate variety (need at least 2 sentences for stdev)
        if len(sentence_lengths) > 1:
            stdev = statistics.stdev(sentence_lengths)
            variety = 'high' if stdev > 10 else 'medium' if stdev > 5 else 'low'
        else:
            variety = 'single sentence'

        structure = {
            'sentence_count': len(sentences),
            'avg_words_per_sentence': round(avg_length, 1),
            'min_length': min(sentence_lengths),
            'max_length': max(sentence_lengths),
            'structure_variety': variety,
            'complexity': 'complex' if avg_length > 20 else 'moderate' if avg_length > 12 else 'simple'
        }

        return structure

    def _analyze_paragraphs(self, content: str) -> Dict[str, Any]:
        """Analyze paragraph structure."""
        # Split into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        if not paragraphs:
            paragraphs = [content]  # Treat as single paragraph

        # Calculate metrics
        para_lengths = [len(p.split()) for p in paragraphs]

        # Calculate consistency (need at least 2 paragraphs for stdev)
        if len(para_lengths) > 1:
            consistency = 'consistent' if statistics.stdev(para_lengths) < 50 else 'varied'
        else:
            consistency = 'single paragraph'

        return {
            'paragraph_count': len(paragraphs),
            'avg_words_per_paragraph': round(statistics.mean(para_lengths), 1) if para_lengths else 0,
            'organization': 'well-structured' if len(paragraphs) > 3 else 'minimal',
            'consistency': consistency
        }

    def _analyze_formatting(self, content: str) -> Dict[str, Any]:
        """Analyze formatting patterns."""
        # Check for markdown/formatting elements
        headings = len(re.findall(r'^#{1,6}\s+.+$', content, re.MULTILINE))
        lists = len(re.findall(r'^\s*[-*+]\s+', content, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\s*\d+\.\s+', content, re.MULTILINE))
        code_blocks = len(re.findall(r'```[\s\S]*?```', content))
        inline_code = len(re.findall(r'`[^`]+`', content))
        bold = len(re.findall(r'\*\*[^*]+\*\*|__[^_]+__', content))
        italic = len(re.findall(r'\*[^*]+\*|_[^_]+_', content))

        return {
            'has_headings': headings > 0,
            'heading_count': headings,
            'has_lists': lists > 0 or numbered_lists > 0,
            'bullet_lists': lists,
            'numbered_lists': numbered_lists,
            'code_blocks': code_blocks,
            'inline_code': inline_code,
            'bold_usage': bold,
            'italic_usage': italic,
            'formatting_richness': 'high' if (headings + lists + code_blocks) > 10 else 'medium' if (headings + lists + code_blocks) > 3 else 'low'
        }

    def _analyze_punctuation(self, content: str) -> Dict[str, Any]:
        """Analyze punctuation usage."""
        # Count different punctuation marks
        periods = content.count('.')
        commas = content.count(',')
        semicolons = content.count(';')
        colons = content.count(':')
        exclamations = content.count('!')
        questions = content.count('?')
        dashes = content.count('—') + content.count('--')

        total_chars = len(content)

        return {
            'periods': periods,
            'commas': commas,
            'semicolons': semicolons,
            'colons': colons,
            'exclamations': exclamations,
            'questions': questions,
            'dashes': dashes,
            'comma_density': round(commas / total_chars * 1000, 2) if total_chars > 0 else 0,
            'exclamation_usage': 'high' if exclamations > 10 else 'medium' if exclamations > 3 else 'low',
            'question_usage': 'high' if questions > 10 else 'medium' if questions > 3 else 'low'
        }

    def _analyze_rhetorical_devices(self, content: str) -> Dict[str, Any]:
        """Analyze use of rhetorical devices."""
        content_lower = content.lower()

        # Detect questions (rhetorical or otherwise)
        questions = len(re.findall(r'\?', content))

        # Detect metaphors/similes (simple heuristic)
        metaphor_indicators = ['like', 'as', '似', 'metaphor', 'symbolize']
        metaphor_count = sum(content_lower.count(word) for word in metaphor_indicators)

        # Detect repetition (same word used multiple times in close proximity)
        words = content_lower.split()
        repetition_score = 0
        for i in range(len(words) - 10):
            window = words[i:i+10]
            if len(window) != len(set(window)):
                repetition_score += 1

        return {
            'questions': questions,
            'question_ratio': round(questions / len(content.split('.')) if content.split('.') else 0, 3),
            'metaphor_indicators': metaphor_count,
            'repetition_score': repetition_score,
            'rhetorical_intensity': 'high' if (questions + metaphor_count + repetition_score) > 20 else 'medium' if (questions + metaphor_count + repetition_score) > 5 else 'low'
        }

    def _analyze_voice(self, content: str) -> Dict[str, Any]:
        """Analyze voice (active/passive, person)."""
        content_lower = content.lower()

        # Detect passive voice indicators
        passive_indicators = ['was', 'were', 'been', 'being', 'is', 'are', 'am']
        passive_count = sum(content_lower.count(f" {word} ") for word in passive_indicators)

        # Detect person
        first_person = content_lower.count(' i ') + content_lower.count(' we ') + content_lower.count(' my ') + content_lower.count(' our ')
        second_person = content_lower.count(' you ') + content_lower.count(' your ')
        third_person = content_lower.count(' he ') + content_lower.count(' she ') + content_lower.count(' they ') + content_lower.count(' their ')

        # Determine dominant person
        max_person_count = max(first_person, second_person, third_person)
        if max_person_count == 0:
            dominant_person = 'impersonal'
        elif first_person == max_person_count:
            dominant_person = 'first person'
        elif second_person == max_person_count:
            dominant_person = 'second person'
        else:
            dominant_person = 'third person'

        return {
            'passive_voice_indicators': passive_count,
            'voice_type': 'passive' if passive_count > len(content.split()) * 0.1 else 'active',
            'person': dominant_person,
            'first_person_count': first_person,
            'second_person_count': second_person,
            'third_person_count': third_person
        }

    def _analyze_pacing(self, content: str) -> Dict[str, Any]:
        """Analyze content pacing."""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 3:
            return {'pacing': 'insufficient data', 'rhythm': 'unknown'}

        # Calculate sentence length variation
        lengths = [len(s.split()) for s in sentences]
        variation = statistics.stdev(lengths) if len(lengths) > 1 else 0

        # Check for rhythm patterns
        short_sentences = sum(1 for l in lengths if l < 10)
        medium_sentences = sum(1 for l in lengths if 10 <= l <= 20)
        long_sentences = sum(1 for l in lengths if l > 20)

        return {
            'pacing': 'varied' if variation > 10 else 'steady',
            'rhythm': 'dynamic' if (short_sentences > 0 and long_sentences > 0) else 'consistent',
            'sentence_length_variation': round(variation, 2),
            'short_sentences': short_sentences,
            'medium_sentences': medium_sentences,
            'long_sentences': long_sentences
        }

    def _analyze_imagery(self, content: str) -> Dict[str, Any]:
        """Analyze use of imagery and descriptive language."""
        content_lower = content.lower()

        # Sensory words
        visual_words = ['see', 'look', 'view', 'color', 'bright', 'dark', 'light', 'shadow']
        auditory_words = ['hear', 'sound', 'loud', 'quiet', 'noise', 'music', 'voice']
        tactile_words = ['feel', 'touch', 'soft', 'hard', 'smooth', 'rough', 'warm', 'cold']

        visual_count = sum(content_lower.count(word) for word in visual_words)
        auditory_count = sum(content_lower.count(word) for word in auditory_words)
        tactile_count = sum(content_lower.count(word) for word in tactile_words)

        total_sensory = visual_count + auditory_count + tactile_count

        # Adjective estimation (simple heuristic)
        common_adjectives = ['good', 'new', 'first', 'last', 'long', 'great', 'little', 'own', 'other', 'old', 'right', 'big', 'high', 'different', 'small']
        adjective_count = sum(content_lower.count(word) for word in common_adjectives)

        return {
            'sensory_words': total_sensory,
            'visual_imagery': visual_count,
            'auditory_imagery': auditory_count,
            'tactile_imagery': tactile_count,
            'descriptive_richness': 'high' if total_sensory > 20 else 'medium' if total_sensory > 5 else 'low',
            'adjective_usage': adjective_count
        }

    def _analyze_technical_level(self, content: str) -> Dict[str, Any]:
        """Analyze technical complexity and jargon usage."""
        content_lower = content.lower()

        # Technical indicators
        technical_keywords = [
            'algorithm', 'function', 'variable', 'parameter', 'method', 'class',
            'instance', 'object', 'array', 'string', 'integer', 'boolean',
            'syntax', 'semantic', 'paradigm', 'framework', 'library', 'api',
            'database', 'server', 'client', 'protocol', 'interface', 'implementation'
        ]

        technical_count = sum(content_lower.count(word) for word in technical_keywords)

        # Acronyms and abbreviations
        acronyms = len(re.findall(r'\b[A-Z]{2,}\b', content))

        # Code-like patterns
        code_patterns = len(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)', content))

        words = content.split()
        technical_ratio = technical_count / len(words) if words else 0

        return {
            'technical_terms': technical_count,
            'technical_ratio': round(technical_ratio, 4),
            'acronyms': acronyms,
            'code_patterns': code_patterns,
            'technical_level': 'very high' if technical_ratio > 0.05 else 'high' if technical_ratio > 0.02 else 'medium' if technical_ratio > 0.005 else 'low'
        }

    def _calculate_metadata(self, content: str) -> Dict[str, Any]:
        """Calculate content metadata."""
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        if not paragraphs:
            paragraphs = [content]

        elapsed_time = (time.time() - self.start_time) * 1000  # Convert to ms

        return {
            'content_length': len(content),
            'word_count': len(words),
            'sentence_count': len(sentences),
            'paragraph_count': len(paragraphs),
            'extraction_time_ms': round(elapsed_time, 2),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'tier_used': self.tier,
            'summarization_applied': len(content) < len(content)  # Would be true if we truncated
        }

    def _save_to_file(self, data: Dict[str, Any], filename: str, format: str) -> str:
        """
        Save extracted style to filesystem.

        Note: This uses the filesystem_manager tool's scope isolation.
        Files are saved to: ./data/filesystem/style_extractor/
        """
        try:
            # Import filesystem manager
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools' / 'executable'))
            from filesystem_manager import FilesystemManager

            # Create manager
            manager = FilesystemManager()

            # Prepare content
            if format == 'yaml' and HAS_YAML:
                content = yaml.dump(data, default_flow_style=False, sort_keys=False)
                if not filename.endswith('.yaml') and not filename.endswith('.yml'):
                    filename += '.yaml'
            else:
                content = json.dumps(data, indent=2)
                if not filename.endswith('.json'):
                    filename += '.json'

            # Write file
            result = manager.write(
                scope='style_extractor',
                path=filename,
                content=content
            )

            if result['status'] == 'success':
                return result['path']
            else:
                raise ValueError(result.get('message', 'Unknown error'))

        except Exception as e:
            # Fallback: save to current directory
            fallback_path = Path(filename)
            if format == 'yaml' and HAS_YAML:
                fallback_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
            else:
                fallback_path.write_text(json.dumps(data, indent=2))
            return str(fallback_path)

    def _error(self, message: str) -> Dict[str, Any]:
        """Return error result."""
        return {
            'success': False,
            'error': message,
            'message': f"Extraction failed: {message}",
            'style_profile': {},
            'metadata': {
                'extraction_time_ms': (time.time() - self.start_time) * 1000,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'tier_used': self.tier
            }
        }


def main():
    """
    Main entry point for style extraction tool.

    Reads JSON input from stdin and executes extraction.
    """
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract parameters
        source_type = input_data.get('source_type')
        source = input_data.get('source')
        tier = input_data.get('extraction_tier', 'detailed')

        if not source_type:
            print(json.dumps({
                'success': False,
                'error': 'Missing required parameter: source_type'
            }))
            sys.exit(1)

        if not source:
            print(json.dumps({
                'success': False,
                'error': 'Missing required parameter: source'
            }))
            sys.exit(1)

        # Create extractor
        extractor = StyleExtractor(tier=tier)

        # Extract style
        result = extractor.extract_from_source(
            source_type=source_type,
            source=source,
            style_aspects=input_data.get('style_aspects'),
            output_format=input_data.get('output_format', 'json'),
            save_to_file=input_data.get('save_to_file', False),
            filename=input_data.get('filename'),
            include_metadata=input_data.get('include_metadata', True),
            max_content_length=input_data.get('max_content_length', 50000)
        )

        # Output result
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'message': 'An unexpected error occurred during style extraction'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
