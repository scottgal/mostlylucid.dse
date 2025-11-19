"""
Task Type Evaluator - Uses tinyllama to classify tasks and determine routing.

Prevents over-optimization by ensuring creative/content tasks use appropriate LLMs.
"""
import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks for routing decisions."""
    CREATIVE_CONTENT = "creative_content"      # Stories, jokes, poems, articles → needs LLM
    ARITHMETIC = "arithmetic"                  # Math calculations → can use tools
    DATA_PROCESSING = "data_processing"        # Transform, filter, sort → can use tools
    CODE_GENERATION = "code_generation"        # Write functions → needs LLM
    TRANSLATION = "translation"                # Language translation → can use tools for simple, LLM for complex
    QUESTION_ANSWERING = "question_answering"  # Answer questions → needs LLM
    FORMATTING = "formatting"                  # Text formatting → can use tools
    CONVERSION = "conversion"                  # Unit/format conversion → can use tools
    SYSTEM_INFO = "system_info"                # System/machine info queries → use platform_info tool
    ACCIDENTAL = "accidental"                  # Nonsense/accidental input → ask for clarification
    UNKNOWN = "unknown"                        # Needs LLM analysis


class TaskEvaluator:
    """Evaluates task type and routing requirements."""

    # Max tokens for tinyllama context (conservative estimate)
    TINYLLAMA_MAX_TOKENS = 500  # ~2000 chars

    # Input length thresholds
    SHORT_INPUT = 200    # < 200 chars → use tinyllama
    MEDIUM_INPUT = 1000  # < 1000 chars → use phi3 or gemma
    LONG_INPUT = 5000    # < 5000 chars → use llama3

    def __init__(self, ollama_client, rag_memory=None):
        """
        Initialize task evaluator.

        Args:
            ollama_client: OllamaClient for LLM inference
            rag_memory: Optional RAGMemory for querying available tools
        """
        self.client = ollama_client
        self.rag_memory = rag_memory
        self._api_tools_cache = None  # Cache of available API tools

    def _get_relevant_api_tools(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Query RAG to find relevant API tools based on query.

        Args:
            query: User's query
            limit: Maximum number of tools to return

        Returns:
            List of relevant API tool metadata
        """
        if not self.rag_memory:
            return []

        try:
            # Search for tools with API-related tags
            from .rag_memory import ArtifactType

            # Query RAG for similar tools
            results = self.rag_memory.find_similar(
                query=query,
                artifact_type=ArtifactType.TOOL,
                top_k=limit
            )

            # Filter to only API tools (openapi, custom API tools)
            api_tools = []
            for artifact, similarity in results:
                # Check if this is an API tool based on tags or metadata
                if artifact.tags:
                    api_tags = {'api', 'openapi', 'rest', 'geolocation', 'ip', 'weather',
                               'currency', 'translation', 'dictionary', 'jokes', 'quotes'}
                    if any(tag in api_tags for tag in artifact.tags):
                        api_tools.append({
                            'name': artifact.name,
                            'description': artifact.description[:200],
                            'tags': artifact.tags[:5],  # Limit tags for smaller context
                            'similarity': similarity
                        })

            return api_tools[:limit]
        except Exception as e:
            logger.warning(f"Failed to query RAG for API tools: {e}")
            return []

    def evaluate_task_type(self, description: str) -> Dict[str, Any]:
        """
        Classify task type and determine routing.

        Args:
            description: Task description from user

        Returns:
            Dict with:
                - task_type: TaskType enum
                - requires_llm: bool
                - requires_content_llm: bool (medium+ tier for creative tasks)
                - can_use_tools: bool
                - recommended_tier: str
                - reason: str
                - is_accidental: bool
                - suggestions: list (if accidental)
        """
        input_length = len(description)

        # Quick check for obviously accidental input
        accidental_check = self._check_if_accidental(description)
        if accidental_check['is_accidental']:
            return {
                "task_type": TaskType.ACCIDENTAL,
                "understanding": accidental_check['understanding'],
                "key_aspects": "unclear, needs clarification",
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "none",
                "reason": "Input appears accidental or unclear",
                "is_accidental": True,
                "suggestions": accidental_check['suggestions'],
                "input_length": input_length,
                "evaluation_model": "rule-based"
            }

        # CRITICAL: Fast RAG lookup for exact tool matches FIRST
        # If we have a 100% match with an existing tool, use it directly
        desc_lower = description.lower()

        # FIRST: Query RAG to find relevant tools (not just APIs, ALL tools)
        relevant_tools = []
        if self.rag_memory:
            try:
                from .rag_memory import ArtifactType

                # Fast semantic search for ANY tool matching the query
                results = self.rag_memory.find_similar(
                    query=description,
                    artifact_type=ArtifactType.TOOL,
                    top_k=3
                )

                if results:
                    top_match = results[0]
                    artifact, similarity = top_match

                    # If we have a very high similarity match (>95%), this is likely an exact tool match
                    if similarity > 0.95:
                        logger.info(f"100% RAG tool match: {artifact.name} (similarity: {similarity:.0%})")

                        # Verify with sentinel LLM (fast check)
                        verification_prompt = f"""Does this query exactly match this tool?

Query: "{description}"
Tool: {artifact.name}
Description: {artifact.description[:200]}

Answer ONLY 'yes' or 'no':"""

                        verification = self.client.generate(
                            model="gemma3:1b",
                            prompt=verification_prompt,
                            max_tokens=5,
                            temperature=0.0
                        )

                        if 'yes' in verification.lower().strip():
                            logger.info(f"Sentinel confirmed 100% match - routing directly to {artifact.name}")

                            # Return with direct tool routing (NO code generation needed)
                            return {
                                "task_type": TaskType.CODE_GENERATION,
                                "complexity": "simple",
                                "understanding": f"Direct tool execution: {artifact.name}",
                                "key_aspects": "100% RAG match, exact tool found",
                                "requires_llm": False,
                                "requires_content_llm": False,
                                "can_use_tools": True,
                                "recommended_tier": "executable",
                                "recommended_tool": artifact.name,
                                "exact_match": True,
                                "reason": f"100% RAG match with existing tool (no code generation needed)",
                                "input_length": input_length,
                                "evaluation_model": "rag-exact-match"
                            }

                    # Store relevant tools for later API routing
                    relevant_tools = [(artifact, similarity) for artifact, similarity in results[:5]]

            except Exception as e:
                logger.warning(f"RAG exact match lookup failed: {e}")

        # SECOND: If no exact match, check for API tools specifically
        relevant_apis = self._get_relevant_api_tools(description, limit=5)

        if relevant_apis:
            logger.info(f"Found {len(relevant_apis)} relevant API tools in RAG")

            try:
                # Build a tight, focused prompt with ONLY relevant APIs from RAG
                import json

                # Create minimal API context from RAG results
                api_context = []
                for api in relevant_apis:
                    api_context.append({
                        'name': api['name'],
                        'desc': api['description'][:100],
                        'tags': api['tags'][:3]
                    })

                # Use the 1B LLM to route with tight context
                routing_prompt = f"""Task: "{description}"

Available APIs (from RAG search):
{json.dumps(api_context, indent=2)}

If this task needs an API, respond with JSON:
{{"api": "api_name", "confidence": 0.95}}

If NOT an API task, respond:
{{"api": null, "confidence": 0}}"""

                route_response = self.client.generate(
                    model="gemma3:1b",
                    prompt=routing_prompt,
                    max_tokens=100,
                    temperature=0.1
                )

                # Parse response
                import re
                json_match = re.search(r'\{[^}]+\}', route_response)
                if json_match:
                    route_data = json.loads(json_match.group(0))

                    # If the LLM has high confidence, this is an API call
                    if route_data.get('api') and route_data.get('confidence', 0) > 0.7:
                        logger.info(f"RAG+LLM routing: {route_data['api']} (confidence: {route_data['confidence']:.0%})")

                        # Return early with API routing
                        return {
                            "task_type": TaskType.CODE_GENERATION,
                            "complexity": "simple",
                            "understanding": f"API call to {route_data['api']}",
                            "key_aspects": f"Routed via RAG semantic search",
                            "requires_llm": False,
                            "requires_content_llm": False,
                            "can_use_tools": True,
                            "recommended_tier": "executable",
                            "recommended_api": route_data['api'],
                            "reason": f"API request routed to {route_data['api']} via RAG",
                            "input_length": input_length,
                            "evaluation_model": "rag+gemma3:1b"
                        }
                    else:
                        logger.info(f"LLM rejected API routing: confidence too low ({route_data.get('confidence', 0):.0%})")
            except Exception as e:
                logger.warning(f"RAG-based API routing failed: {e}, continuing with standard classification")

        # NOW check for system info queries
        # Only after we've ruled out API calls

        # CRITICAL: Exclude IP/geolocation queries from system_info
        # These should ALWAYS go to API, never to platform_info
        ip_exclusions = ['my ip', 'external ip', 'public ip', 'ip address',
                        'where am i', 'my geolocation', 'my location',
                        'geolocation', 'geolocate', 'find the geolocation',
                        'get the geolocation', 'location of this machine',
                        'what country', 'what city']

        # Also check for explicit API usage requests
        api_usage_indicators = ['use the api', 'call the api', 'use api to', 'call api to']

        is_ip_query = any(exclusion in desc_lower for exclusion in ip_exclusions)
        is_explicit_api = any(indicator in desc_lower for indicator in api_usage_indicators)

        if is_ip_query or is_explicit_api:
            # This is an IP/geolocation query OR explicit API request - force API routing
            reason = "IP/geolocation query" if is_ip_query else "Explicit API usage request"
            logger.info(f"{reason} detected - forcing API routing")
            return {
                "task_type": TaskType.CODE_GENERATION,
                "complexity": "simple",
                "understanding": "IP address or geolocation lookup via API",
                "key_aspects": "external IP, geolocation, API call",
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "executable",
                "recommended_api": "ip_geolocation_api",
                "reason": f"{reason} requires external API call (never use platform_info for IP)",
                "input_length": input_length,
                "evaluation_model": "keyword-based-api-detection"
            }

        is_real_question = any(desc_lower.startswith(q) for q in ['what', 'which', 'how much', 'how many', 'tell me', 'show me'])

        # VERY RESTRICTIVE: Only these EXACT phrases indicate system info queries
        system_info_keywords = [
            'my ram', 'my memory', 'my cpu', 'my gpu',
            'my os', 'my operating system', 'my platform',
            'this machine', 'this computer', 'this system',
            'system specs', 'hardware specs', 'machine specs',
            'available memory', 'available ram', 'total memory', 'total ram',
            'gpu memory', 'gpu usage', 'cpu usage', 'disk space',
            'what os', 'which os', 'what cpu', 'what gpu',
            'how much ram', 'how much memory', 'how much disk'
        ]

        # Only match if it STARTS with question word AND contains EXACT system keyword phrase
        if is_real_question and any(keyword in desc_lower for keyword in system_info_keywords):
            # Use sentinel to confirm this is REALLY a system info question
            logger.info(f"Potential system info query detected, verifying with sentinel LLM...")

            verification_prompt = f"""Is this task asking for information ABOUT THIS COMPUTER/MACHINE's hardware (RAM, CPU, GPU, OS, disk space)?

Task: "{description}"

Answer ONLY 'yes' if asking about THIS MACHINE'S hardware/system specs (examples: 'what is my RAM', 'show me CPU specs', 'how much memory do I have').
Answer 'no' for EVERYTHING ELSE including:
- Business data ('inventory', 'demand', 'sales', 'orders')
- External data ('get data from URL', 'fetch from API')
- File operations ('read file', 'save to disk')
- ANY task that is NOT about this computer's hardware specs

Answer (yes/no):"""

            try:
                verification = self.client.generate(
                    model="gemma3:1b",  # Fast verification
                    prompt=verification_prompt,
                    max_tokens=10,
                    temperature=0.0  # Deterministic
                )

                if 'yes' in verification.lower().strip():
                    logger.info(f"Sentinel confirmed: system info query")
                    routing = self._determine_routing(TaskType.SYSTEM_INFO, description, "simple")
                    return {
                        "task_type": TaskType.SYSTEM_INFO,
                        "complexity": "simple",
                        "understanding": "System information query",
                        "key_aspects": "hardware, specs, platform",
                        "input_length": input_length,
                        "evaluation_model": "sentinel-verified",
                        **routing
                    }
                else:
                    logger.info(f"Sentinel rejected: not a system info query - '{verification.strip()}'")
            except Exception as e:
                logger.warning(f"Sentinel verification failed: {e}, skipping system_info classification")

        # Choose model based on input length
        if input_length < self.SHORT_INPUT:
            model = "gemma3:1b"
            tier = "very-fast"
        elif input_length < self.MEDIUM_INPUT:
            model = "gemma3:4b"  # Changed from phi3:mini which doesn't exist
            tier = "fast"
        elif input_length < self.LONG_INPUT:
            model = "gemma3:4b"
            tier = "fast"
        else:
            model = "llama3"
            tier = "medium"

        logger.info(f"Evaluating task type with {model} (input length: {input_length} chars)")

        prompt = f"""Task: "{description}"

Classify as ONE:
- creative_content: stories, jokes, articles, poems, OR GENERATING SAMPLE/TEST/RANDOM DATA
- arithmetic: math calculations, number operations
- data_processing: filtering, sorting, transforming EXISTING data (NOT generating new data)
- code_generation: writing functions, programs, OR fetching/downloading/saving data
- translation: language translation
- question_answering: answering questions, explaining concepts
- formatting: changing text format/case
- conversion: converting between formats
- system_info: queries about machine specs, hardware, OS, memory, CPU, GPU (use Questions About Me tool)
- unknown: unclear tasks

IMPORTANT:
- "generate data", "create sample data", "random data" → creative_content (needs LLM)
- "filter data", "sort data" → data_processing (can use code)
- "fetch", "download", "get from URL", "save to disk" → code_generation (needs code to fetch/save)
- "what memory", "what OS", "CPU info", "how much RAM", "system specs", "is GPU busy" → system_info (use Questions About Me tool)

EXAMPLES:
- "how much memory does this machine have?" → system_info
- "what OS am I running?" → system_info
- "show me system specs" → system_info
- "what CPU does this have?" → system_info

Also rate COMPLEXITY:
simple, moderate, complex

CATEGORY: [pick one]
COMPLEXITY: [pick one]"""

        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                model_key="triage"
            )

            # Parse structured response - extract category and complexity
            lines = response.strip().split('\n')
            category_line = next((l for l in lines if l.startswith('CATEGORY:')), '')
            complexity_line = next((l for l in lines if l.startswith('COMPLEXITY:')), '')

            category = category_line.replace('CATEGORY:', '').strip().lower().replace("-", "_")
            complexity = complexity_line.replace('COMPLEXITY:', '').strip().lower()

            # CRITICAL: Override category for data GENERATION requests
            # (even if tinyllama classified it as data_processing)
            desc_lower = description.lower()
            if any(keyword in desc_lower for keyword in ["generate data", "create data", "sample data",
                                                         "random data", "fake data", "mock data",
                                                         "test data", "dummy data", "synthetic data",
                                                         "generate sample", "create sample", "make up data"]):
                # Data generation needs LLM, not code loops
                logger.info(f"Detected data generation request - overriding to creative_content")
                category = 'creative_content'

            # CRITICAL: Override system_info for API/ACTION tasks
            # Use RAG to check if this is actually an API call
            if category == 'system_info':
                # Check if RAG found relevant APIs (reuse the earlier check)
                relevant_apis = self._get_relevant_api_tools(description, limit=3)

                if relevant_apis:
                    logger.info(f"Overriding system_info - found {len(relevant_apis)} relevant APIs in RAG")
                    category = 'code_generation'  # API calls need code execution

            # Don't try to parse understanding or key_aspects - tinyllama is too unreliable
            understanding = ""
            key_aspects = ""

            # Fallback: Try to extract from unstructured response
            if not category or not complexity:
                # Try to infer from response content
                response_lower = response.lower()

                # Extract category from keywords
                if not category:
                    if any(word in response_lower for word in ['joke', 'story', 'poem', 'creative', 'article', 'content']):
                        category = 'creative_content'
                    elif any(word in response_lower for word in ['math', 'calculate', 'arithmetic', 'number']):
                        category = 'arithmetic'
                    elif any(word in response_lower for word in ['code', 'function', 'program', 'fetch', 'download', 'save', 'file']):
                        category = 'code_generation'
                    elif any(word in response_lower for word in ['question', 'answer', 'explain']):
                        category = 'question_answering'
                    elif any(word in response_lower for word in ['system', 'machine', 'hardware', 'memory', 'ram', 'cpu', 'platform', 'os', 'operating']):
                        category = 'system_info'
                    # Removed aggressive 'accidental' keyword check - let unknown tasks route to LLM
                    # Don't reject tasks just because tinyllama is confused
                    else:
                        category = 'unknown'

                # Extract complexity from keywords if not found
                if not complexity:
                    desc_lower = description.lower()
                    # Keyword-based complexity detection
                    if any(word in desc_lower for word in ['simple', 'basic', 'quick', 'small', 'easy']):
                        complexity = 'simple'
                    elif any(word in desc_lower for word in ['complex', 'advanced', 'system', 'architecture', 'multi', 'design']):
                        complexity = 'complex'
                    else:
                        complexity = 'moderate'

            # Map to TaskType
            task_type = self._parse_task_type(category)

            # Determine requirements (pass complexity for better routing)
            routing = self._determine_routing(task_type, description, complexity)

            logger.info(f"Task classified as: {task_type.value} (complexity: {complexity}) → {routing['recommended_tier']}")

            return {
                "task_type": task_type,
                "complexity": complexity,
                "understanding": understanding,
                "key_aspects": key_aspects,
                "input_length": input_length,
                "evaluation_model": model,
                **routing
            }

        except Exception as e:
            logger.error(f"Error evaluating task type: {e}")
            # Safe default: assume needs LLM
            return {
                "task_type": TaskType.UNKNOWN,
                "complexity": "moderate",
                "understanding": "Unable to evaluate task due to an error",
                "key_aspects": "error, unknown",
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "code.general",  # Updated from coding.tier_2
                "reason": f"Error during evaluation: {e}",
                "input_length": input_length,
                "evaluation_model": "none"
            }

    def _check_if_accidental(self, description: str) -> Dict[str, Any]:
        """
        Check if input appears to be accidental or nonsense.

        Returns:
            Dict with is_accidental, understanding, suggestions
        """
        desc_lower = description.lower().strip()
        desc_clean = ''.join(c for c in desc_lower if c.isalnum() or c.isspace())
        words = desc_lower.split()

        # Patterns that suggest accidental input
        accidental_patterns = [
            # Very short nonsense (but allow short math tasks like "add 10 and 20")
            len(description) <= 2,
            # Common test inputs (single word only)
            len(words) == 1 and desc_lower in ['test', 'testing', 'asdf', 'qwerty', 'hello', 'hi', 'abc'],
            # Just numbers with no context (but allow "add 10 and 20")
            len(words) == 1 and desc_clean.isdigit(),
            # Random keypresses (4+ consecutive same char, not 3 to avoid false positives like "www")
            any(description.count(c * 4) > 0 for c in set(description) if c.isalpha()),
            # Just punctuation
            desc_clean == '',
            # Mostly consonants with no real words (unlikely to be real)
            len(desc_clean) > 3 and len(words) == 1 and sum(1 for c in desc_clean if c in 'aeiou') < len(desc_clean) * 0.2,
        ]

        is_accidental = any(accidental_patterns)

        if is_accidental:
            # Generate helpful suggestions based on what we detected
            suggestions = []

            # Single punctuation character
            if len(description) == 1 and not description.isalnum():
                suggestions = [
                    "Describe what you want to create in words",
                    "Example: 'write a function to calculate fibonacci'",
                    "Example: 'create a program to sort a list'"
                ]
                understanding = "Input is just a punctuation character - needs a description in words"

            elif desc_lower in ['test', 'testing']:
                suggestions = [
                    "Try: 'write a function to add two numbers'",
                    "Try: 'create a fibonacci sequence generator'",
                    "Try: 'write a joke about programming'"
                ]
                understanding = "This looks like a test input"
            elif len(description) <= 2:
                suggestions = [
                    "Describe what you want to create",
                    "Try: 'sort a list of numbers'",
                    "Try: 'translate text to french'"
                ]
                understanding = "Input is too short to understand"
            elif desc_clean == '':
                suggestions = [
                    "Please enter a task description",
                    "Example: 'write a story about a robot'",
                    "Example: 'calculate prime numbers'"
                ]
                understanding = "No meaningful text detected"
            else:
                suggestions = [
                    "Please rephrase your request more clearly",
                    "Example: 'write a function that...'",
                    "Example: 'create a program to...'"
                ]
                understanding = "Input is unclear or may be accidental"

            return {
                'is_accidental': True,
                'understanding': understanding,
                'suggestions': suggestions
            }

        return {'is_accidental': False}

    def _parse_task_type(self, category: str) -> TaskType:
        """Parse category string to TaskType enum."""
        try:
            # Try direct match
            return TaskType(category)
        except ValueError:
            # Try fuzzy matching
            # IMPORTANT: Check for data GENERATION first (needs LLM)
            # before generic data processing (can use code)
            if any(keyword in category for keyword in ["generate data", "create data", "sample data",
                                                       "random data", "fake data", "mock data",
                                                       "test data", "dummy data", "synthetic data"]):
                # Data generation needs LLM for realistic results
                return TaskType.CREATIVE_CONTENT
            elif "creative" in category or "content" in category or "story" in category or "joke" in category:
                return TaskType.CREATIVE_CONTENT
            elif "math" in category or "arithmetic" in category or "calculate" in category:
                return TaskType.ARITHMETIC
            elif "data" in category or "process" in category:
                # Generic data processing (filter, sort, transform) can use code
                return TaskType.DATA_PROCESSING
            elif "code" in category or "function" in category or "program" in category:
                return TaskType.CODE_GENERATION
            elif "translate" in category or "translation" in category:
                return TaskType.TRANSLATION
            elif "question" in category or "answer" in category or "explain" in category:
                return TaskType.QUESTION_ANSWERING
            elif "format" in category or "case" in category:
                return TaskType.FORMATTING
            elif "convert" in category or "conversion" in category:
                return TaskType.CONVERSION
            elif "system_info" in category:  # Must be exact match, not just "info"
                return TaskType.SYSTEM_INFO
            else:
                return TaskType.UNKNOWN

    def _determine_routing(self, task_type: TaskType, description: str, complexity: str = "moderate") -> Dict[str, Any]:
        """
        Determine routing requirements based on task type and complexity.

        Args:
            task_type: The type of task
            description: Task description
            complexity: Task complexity (simple, moderate, complex)

        Returns:
            Dict with requires_llm, requires_content_llm, can_use_tools, recommended_tier, reason
        """
        # Accidental input - should not proceed
        if task_type == TaskType.ACCIDENTAL:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "none",
                "reason": "Input appears accidental or unclear - needs clarification"
            }

        # CRITICAL: Creative content ALWAYS needs LLM (medium+ tier)
        if task_type == TaskType.CREATIVE_CONTENT:
            return {
                "requires_llm": True,
                "requires_content_llm": True,
                "can_use_tools": False,
                "recommended_tier": "content.general",  # Updated from content.tier_2
                "reason": "Creative content requires LLM generation (stories, jokes, poems, articles)"
            }

        # Question answering needs LLM
        elif task_type == TaskType.QUESTION_ANSWERING:
            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "content.general",  # Updated from content.tier_2
                "reason": "Question answering requires LLM knowledge"
            }

        # Code generation needs coding LLM - tier based on complexity
        elif task_type == TaskType.CODE_GENERATION:
            # Select tier based on complexity assessment
            if complexity == "simple":
                tier = "code.fast"  # Updated from coding.tier_1
                reason = "Simple code generation (basic functions, straightforward logic)"
            elif complexity == "complex":
                tier = "code.escalation"  # Updated from coding.tier_3
                reason = "Complex code generation (advanced algorithms, system design)"
            else:  # moderate
                tier = "code.general"  # Updated from coding.tier_2
                reason = "Standard code generation (multi-step workflows, moderate complexity)"

            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": tier,
                "reason": reason
            }

        # Arithmetic can use calculator tools
        elif task_type == TaskType.ARITHMETIC:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "executable",
                "reason": "Arithmetic can use calculator tool (zero-cost)"
            }

        # Formatting can use text formatter tools
        elif task_type == TaskType.FORMATTING:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "executable",
                "reason": "Text formatting can use formatter tool (zero-cost)"
            }

        # Conversion can use converter tools
        elif task_type == TaskType.CONVERSION:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "executable",
                "reason": "Unit conversion can use converter tool (zero-cost)"
            }

        # Translation - simple can use tool, complex needs LLM
        elif task_type == TaskType.TRANSLATION:
            # Check if it's a simple word/phrase translation
            words = description.split()
            if len(words) <= 10:  # Simple translation
                return {
                    "requires_llm": False,
                    "requires_content_llm": False,
                    "can_use_tools": True,
                    "recommended_tier": "llm.quick_translator",
                    "reason": "Simple translation can use quick_translator tool"
                }
            else:  # Complex translation
                return {
                    "requires_llm": True,
                    "requires_content_llm": True,
                    "can_use_tools": False,
                    "recommended_tier": "content.general",  # Updated from content.tier_2
                    "reason": "Complex translation requires LLM for context/nuance"
                }

        # Data processing can use code
        elif task_type == TaskType.DATA_PROCESSING:
            return {
                "requires_llm": False,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "code.fast",  # Updated from coding.tier_1
                "reason": "Data processing can use generated code"
            }

        # System info queries use Questions About Me LLM tool
        # which internally calls platform_info but provides conversational responses
        elif task_type == TaskType.SYSTEM_INFO:
            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": True,
                "recommended_tier": "llm.questions_about_me",
                "reason": "System information queries use Questions About Me tool (calls platform_info, provides natural language response)"
            }

        # Unknown - safe default to LLM
        else:
            return {
                "requires_llm": True,
                "requires_content_llm": False,
                "can_use_tools": False,
                "recommended_tier": "content.general",  # Updated from content.tier_2
                "reason": "Unknown task type, defaulting to LLM for safety"
            }
