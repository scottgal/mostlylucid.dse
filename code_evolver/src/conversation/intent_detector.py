"""
Conversation Intent Detector

Detects when user wants to start a conversation vs. asking to generate dialogue.
Uses fast LLM (gemma3:1b) for intent classification.
"""
import logging
from typing import Dict, Any, Optional
import requests
import re

logger = logging.getLogger(__name__)


class ConversationIntentDetector:
    """
    Detects user intent to start a conversation.

    Distinguishes between:
    - User wants to have a conversation ("let's chat", "up for a chat")
    - User wants to generate a conversation ("write a conversation between X and Y")
    - Regular task/question (no conversation intent)
    """

    # Patterns that strongly suggest wanting to have a conversation
    # Comprehensive list of synonyms and variations
    CONVERSATION_PATTERNS = [
        # Chat variations
        r"let'?s (have a |)chat",
        r"up for a chat",
        r"wanna (chat|have a chat)",
        r"want to (chat|have a chat)",
        r"can we (chat|have a chat)",
        r"shall we (chat|have a chat)",
        r"could we (chat|have a chat)",
        r"would you (chat|like to chat)",
        r"how about (a |)chat",
        r"fancy (a |)chat",
        r"down for (a |)chat",
        r"ready (for a |to) chat",

        # Conversation variations
        r"let'?s (have a |)conversation",
        r"up for a conversation",
        r"wanna (have a |)conversation",
        r"want to (have a |)conversation",
        r"can we (have a |)conversation",
        r"shall we (have a |)conversation",
        r"could we (have a |)conversation",
        r"would you (like to have a |have a |)conversation",
        r"start( a|) conversation",
        r"begin( a|) conversation",
        r"initiate( a|) conversation",
        r"open( a|) conversation",
        r"how about (a |)conversation",
        r"fancy (a |)conversation",
        r"down for (a |)conversation",

        # Talk/speak variations
        r"let'?s talk",
        r"wanna talk",
        r"want to talk",
        r"can we talk",
        r"shall we talk",
        r"could we talk",
        r"need to talk",
        r"let'?s speak",
        r"can we speak",

        # Discuss variations
        r"let'?s discuss",
        r"wanna discuss",
        r"want to discuss",
        r"can we discuss",
        r"shall we discuss",
        r"could we discuss",
        r"let'?s have (a |)discussion",
        r"up for (a |)discussion",

        # Dialogue variations
        r"let'?s (have a |)dialogue",
        r"can we (have a |)dialogue",
        r"open (a |)dialogue",
        r"start (a |)dialogue",

        # Informal/casual
        r"let'?s shoot the breeze",
        r"let'?s chit.?chat",
        r"let'?s have a chinwag",
        r"let'?s jaw",
        r"let'?s gab",
        r"let'?s rap",
        r"let'?s converse",
        r"let'?s exchange (ideas|thoughts|views)",

        # Direct asks
        r"talk (to|with) me",
        r"chat (to|with) me",
        r"converse with me",
        r"speak (to|with) me",
        r"engage (in conversation|with me)",
        r"communicate with me",

        # Interrogative forms
        r"can you (chat|talk|converse|speak)",
        r"will you (chat|talk|converse|speak)",
        r"would you (chat|talk|converse|speak)",
        r"could you (chat|talk|converse|speak)",
        r"may (I|we) (chat|talk|converse|speak)",
        r"might (I|we) (chat|talk|converse|speak)",

        # Present continuous
        r"(I'?m|we'?re) (here to|ready to|wanting to) (chat|talk|converse|speak)",
        r"looking (for a|to have a|to) (chat|talk|conversation|discussion)",
        r"seeking (a |)conversation",
        r"interested in (a |)(chat|conversation|discussion|dialogue)",
    ]

    # Patterns that suggest generating dialogue (NOT starting a conversation)
    # These take priority over conversation patterns
    GENERATION_PATTERNS = [
        # "between" patterns (strong indicator of generation)
        r"write (a|an|) (conversation|dialogue|discussion|exchange) between",
        r"create (a|an|) (conversation|dialogue|discussion|exchange) between",
        r"generate (a|an|) (conversation|dialogue|discussion|exchange) between",
        r"compose (a|an|) (conversation|dialogue|discussion|exchange) between",
        r"draft (a|an|) (conversation|dialogue|discussion|exchange) between",
        r"simulate (a|an|) (conversation|dialogue|discussion|exchange) between",
        r"produce (a|an|) (conversation|dialogue|discussion|exchange) between",
        r"develop (a|an|) (conversation|dialogue|discussion|exchange) between",
        r"make (a|an|) (conversation|dialogue|discussion|exchange) between",
        r"script (a|an|) (conversation|dialogue|discussion|exchange) between",

        # "for" patterns (e.g., "write a conversation for my story")
        r"write (a|an) (conversation|dialogue) for",
        r"create (a|an) (conversation|dialogue) for",
        r"generate (a|an) (conversation|dialogue) for",
        r"compose (a|an) (conversation|dialogue) for",
        r"draft (a|an) (conversation|dialogue) for",

        # "of" patterns (e.g., "write a conversation of two people")
        r"write (a|an) (conversation|dialogue) of",
        r"create (a|an) (conversation|dialogue) of",

        # "where" patterns (e.g., "write a conversation where...")
        r"write (a|an) (conversation|dialogue) where",
        r"create (a|an) (conversation|dialogue) where",
        r"generate (a|an) (conversation|dialogue) where",

        # "with" patterns when followed by character indicators
        r"write (a|an) (conversation|dialogue) with (characters|people|persons|two|three|someone)",
        r"create (a|an) (conversation|dialogue) with (characters|people|persons|two|three|someone)",

        # Script/screenplay related
        r"script (a|an) (conversation|dialogue|scene)",
        r"write (a|an) script",
        r"create (a|an) script",
        r"screenplay (with|containing)",
        r"scene (with|containing|where)",

        # Example conversation patterns
        r"(write|create|generate|show|give|provide) (an |)example (conversation|dialogue)",
        r"(write|create|generate|show|give|provide) (a |)sample (conversation|dialogue)",

        # Fictional conversation indicators
        r"fictional (conversation|dialogue)",
        r"imaginary (conversation|dialogue)",
        r"hypothetical (conversation|dialogue)",
        r"pretend (conversation|dialogue)",
        r"mock (conversation|dialogue)",
    ]

    def __init__(
        self,
        model_name: str = "gemma3:1b",
        ollama_endpoint: str = "http://localhost:11434",
        use_llm_fallback: bool = True
    ):
        """
        Initialize intent detector.

        Args:
            model_name: Fast LLM for intent classification
            ollama_endpoint: Ollama API endpoint
            use_llm_fallback: Use LLM when patterns don't match
        """
        self.model_name = model_name
        self.ollama_endpoint = ollama_endpoint
        self.use_llm_fallback = use_llm_fallback

        logger.info(f"Intent detector initialized with model: {model_name}")

    def detect_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Detect if user wants to start a conversation.

        Args:
            user_input: User's input text

        Returns:
            Dict with:
            - intent: 'start_conversation', 'generate_dialogue', or 'task'
            - confidence: Confidence score (0.0-1.0)
            - method: Detection method used ('pattern' or 'llm')
            - topic: Extracted topic (if any)
        """
        user_input_lower = user_input.lower()

        # First check generation patterns (these take priority)
        for pattern in self.GENERATION_PATTERNS:
            if re.search(pattern, user_input_lower):
                logger.debug(f"Detected 'generate_dialogue' intent via pattern: {pattern}")
                return {
                    "intent": "generate_dialogue",
                    "confidence": 0.95,
                    "method": "pattern",
                    "topic": None
                }

        # Then check conversation patterns
        for pattern in self.CONVERSATION_PATTERNS:
            if re.search(pattern, user_input_lower):
                logger.debug(f"Detected 'start_conversation' intent via pattern: {pattern}")

                # Extract topic if mentioned
                topic = self._extract_topic(user_input)

                return {
                    "intent": "start_conversation",
                    "confidence": 0.9,
                    "method": "pattern",
                    "topic": topic
                }

        # No pattern match - use LLM fallback if enabled
        if self.use_llm_fallback:
            return self._detect_with_llm(user_input)

        # Default to task intent
        return {
            "intent": "task",
            "confidence": 0.5,
            "method": "default",
            "topic": None
        }

    def _extract_topic(self, user_input: str) -> Optional[str]:
        """
        Extract conversation topic from user input.

        Args:
            user_input: User input

        Returns:
            Extracted topic or None
        """
        # Look for "about X" patterns
        about_match = re.search(r"about (.+?)(?:\.|$|,)", user_input, re.IGNORECASE)
        if about_match:
            return about_match.group(1).strip()

        # Look for "on X" patterns
        on_match = re.search(r"on (.+?)(?:\.|$|,)", user_input, re.IGNORECASE)
        if on_match:
            return on_match.group(1).strip()

        return None

    def _detect_with_llm(self, user_input: str) -> Dict[str, Any]:
        """
        Use LLM to detect intent.

        Args:
            user_input: User input

        Returns:
            Intent detection result
        """
        prompt = f"""Analyze this user input and determine the intent.

User input: "{user_input}"

Classify the intent as ONE of:
1. START_CONVERSATION - User wants to have a conversation with you
2. GENERATE_DIALOGUE - User wants you to write/create a conversation between characters
3. TASK - User has a regular task or question

Also extract the topic if mentioned.

Respond in this exact format:
INTENT: [START_CONVERSATION|GENERATE_DIALOGUE|TASK]
CONFIDENCE: [0.0-1.0]
TOPIC: [topic or NONE]

Your response:"""

        try:
            response = requests.post(
                f"{self.ollama_endpoint}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for classification
                        "num_predict": 100
                    }
                },
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            text = result.get("response", "").strip()

            # Parse response
            intent_match = re.search(r"INTENT:\s*(\w+)", text, re.IGNORECASE)
            confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", text, re.IGNORECASE)
            topic_match = re.search(r"TOPIC:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)

            intent_str = intent_match.group(1).upper() if intent_match else "TASK"
            confidence = float(confidence_match.group(1)) if confidence_match else 0.6
            topic = topic_match.group(1).strip() if topic_match else None

            # Normalize topic
            if topic and topic.upper() in ["NONE", "N/A", "NULL"]:
                topic = None

            # Map intent string to our format
            intent_map = {
                "START_CONVERSATION": "start_conversation",
                "GENERATE_DIALOGUE": "generate_dialogue",
                "TASK": "task"
            }
            intent = intent_map.get(intent_str, "task")

            logger.debug(f"LLM detected intent: {intent} (confidence: {confidence})")

            return {
                "intent": intent,
                "confidence": confidence,
                "method": "llm",
                "topic": topic
            }

        except Exception as e:
            logger.error(f"LLM intent detection failed: {e}")
            return {
                "intent": "task",
                "confidence": 0.5,
                "method": "error",
                "topic": None
            }

    def should_start_conversation(
        self,
        user_input: str,
        confidence_threshold: float = 0.7
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if conversation should be started.

        Args:
            user_input: User input
            confidence_threshold: Minimum confidence to start conversation

        Returns:
            Tuple of (should_start, topic)
        """
        result = self.detect_intent(user_input)

        should_start = (
            result["intent"] == "start_conversation" and
            result["confidence"] >= confidence_threshold
        )

        return should_start, result.get("topic")
