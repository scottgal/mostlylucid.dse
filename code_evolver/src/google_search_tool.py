"""
Google Search Tool for mostlylucid DiSE.
Provides Google Custom Search API integration with RAG caching for search results.
"""
import json
import logging
import os
import re
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)


class GoogleSearchTool:
    """
    Google Custom Search integration tool with RAG caching.

    Features:
    - Web search via Google Custom Search API
    - Natural language query support
    - Advanced search filters (date, file type, site, etc.)
    - RAG caching to store and reuse search results
    - TTL-based cache invalidation
    - Pagination support
    """

    def __init__(
        self,
        api_base: str = "https://www.googleapis.com/customsearch/v1",
        max_results: int = 10,
        use_rag_cache: bool = True,
        rag_cache_ttl_hours: int = 24,
        config_manager: Optional[Any] = None,
        rag_memory: Optional[Any] = None
    ):
        """
        Initialize Google Search tool.

        Args:
            api_base: Google Custom Search API base URL
            max_results: Default maximum results to return
            use_rag_cache: Whether to use RAG caching
            rag_cache_ttl_hours: Cache TTL in hours
            config_manager: ConfigManager for loading credentials
            rag_memory: RAGMemory instance for caching
        """
        self.api_base = api_base
        self.max_results = max_results
        self.use_rag_cache = use_rag_cache
        self.rag_cache_ttl_hours = rag_cache_ttl_hours
        self.config_manager = config_manager
        self.rag_memory = rag_memory

        # Load credentials
        self.api_key = self._load_api_key()
        self.search_engine_id = self._load_search_engine_id()

        if self.api_key and self.search_engine_id:
            logger.info("Google Search tool initialized with API credentials")
        else:
            logger.warning("Google Search tool initialized WITHOUT complete credentials")
            if not self.api_key:
                logger.warning("Missing: API key")
            if not self.search_engine_id:
                logger.warning("Missing: Search Engine ID (CX)")

    def _load_api_key(self) -> Optional[str]:
        """Load Google Search API key from config.yaml or environment."""
        # Try specific Google Search API key
        api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        if api_key:
            return api_key

        # Try generic Google API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            return api_key

        # Try config manager
        if self.config_manager:
            try:
                google_config = self.config_manager.get("google", {})

                # Try search-specific API key
                search_config = google_config.get("search", {})
                api_key = search_config.get("api_key", "")
                if api_key:
                    return os.path.expandvars(api_key)

                # Try generic Google API key in config
                api_key = google_config.get("api_key", "")
                if api_key:
                    return os.path.expandvars(api_key)
            except Exception as e:
                logger.error(f"Error loading Google Search API key from config: {e}")

        return None

    def _load_search_engine_id(self) -> Optional[str]:
        """Load Google Search Engine ID (CX) from config.yaml or environment."""
        # Try environment variable
        cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        if cx:
            return cx

        # Try config manager
        if self.config_manager:
            try:
                google_config = self.config_manager.get("google", {})
                search_config = google_config.get("search", {})
                cx = search_config.get("search_engine_id", "")
                if cx:
                    return os.path.expandvars(cx)
            except Exception as e:
                logger.error(f"Error loading Google Search Engine ID from config: {e}")

        return None

    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """
        Generate a unique cache key for search parameters.

        Args:
            params: Search parameters

        Returns:
            Cache key (hash of normalized params)
        """
        # Normalize params (sort keys, convert to string)
        normalized = json.dumps(params, sort_keys=True)

        # Generate hash
        cache_key = hashlib.sha256(normalized.encode()).hexdigest()

        return f"search_{cache_key}"

    def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Check if cached results exist and are still valid.

        Args:
            cache_key: Cache key to check

        Returns:
            Cached data if valid, None otherwise
        """
        if not self.use_rag_cache or not self.rag_memory:
            return None

        try:
            # Import here to avoid circular dependency
            from rag_memory import ArtifactType

            # Search for cached results
            # Use find_by_tags instead of find_similar for exact match
            results = self.rag_memory.find_by_tags(
                tags=[cache_key, "search_result"],
                artifact_type=ArtifactType.PATTERN,  # Using PATTERN type for search results
                limit=1
            )

            if not results:
                return None

            artifact = results[0]

            # Check TTL
            cache_timestamp = artifact.metadata.get("cache_timestamp")
            if cache_timestamp:
                cache_time = datetime.fromisoformat(cache_timestamp)
                ttl = timedelta(hours=self.rag_cache_ttl_hours)

                if datetime.utcnow() - cache_time > ttl:
                    logger.info(f"Cache expired for key: {cache_key}")
                    return None

            # Parse cached content
            cached_data = json.loads(artifact.content)
            cached_data["cached"] = True
            cached_data["cache_timestamp"] = cache_timestamp

            logger.info(f"✓ Cache HIT for key: {cache_key}")
            return cached_data

        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None

    def _store_in_cache(
        self,
        cache_key: str,
        query: str,
        search_data: Dict[str, Any]
    ):
        """
        Store search results in RAG cache.

        Args:
            cache_key: Cache key
            query: Original search query
            search_data: Search results to cache
        """
        if not self.use_rag_cache or not self.rag_memory:
            return

        try:
            # Import here to avoid circular dependency
            from rag_memory import ArtifactType

            # Prepare cache content
            cache_content = {
                "items": search_data.get("items", []),
                "total_results": search_data.get("total_results", "0"),
                "search_time": search_data.get("search_time", 0)
            }

            # Store in RAG memory
            self.rag_memory.store_artifact(
                artifact_id=cache_key,
                artifact_type=ArtifactType.PATTERN,  # Using PATTERN type for search results
                name=f"Search: {query}",
                description=f"Cached search results for query: {query}",
                content=json.dumps(cache_content, indent=2),
                tags=[cache_key, "search_result", "google_search"],
                metadata={
                    "query": query,
                    "cache_timestamp": datetime.utcnow().isoformat(),
                    "ttl_hours": self.rag_cache_ttl_hours,
                    "total_results": search_data.get("total_results", "0")
                },
                auto_embed=True
            )

            logger.info(f"✓ Stored search results in cache: {cache_key}")

        except Exception as e:
            logger.error(f"Error storing in cache: {e}")

    def _extract_query_from_natural_language(self, query: str) -> tuple[str, Optional[int]]:
        """
        Extract the actual search query from natural language.

        Examples:
        - "search for python tutorials" -> ("python tutorials", None)
        - "find out how to deploy docker" -> ("how to deploy docker", None)
        - "top 10 javascript frameworks" -> ("javascript frameworks", 10)
        - "google best practices for REST API" -> ("best practices for REST API", None)

        Args:
            query: Natural language query

        Returns:
            Tuple of (extracted_query, num_results)
        """
        original_query = query
        num_results = None

        # Patterns to match natural language queries
        patterns = [
            r"^(?:search|find|look|google|lookup|find out|search for|look up)\s+(?:for\s+)?(?:the\s+)?(.+?)(?:\?)?$",
            r"^what is (.+?)(?:\?)?$",
            r"^how (?:to|do i|can i) (.+?)(?:\?)?$",
            r"^(?:top|best)\s+(\d+)\s+(.+?)(?:\?)?$",
        ]

        query_lower = query.lower().strip()

        # Check for "top N" pattern first
        top_match = re.match(r"^(?:top|best)\s+(\d+)\s+(.+?)(?:\?)?$", query_lower, re.IGNORECASE)
        if top_match:
            num_results = int(top_match.group(1))
            return top_match.group(2).strip(), num_results

        # Try other patterns
        for pattern in patterns:
            match = re.match(pattern, query_lower, re.IGNORECASE)
            if match:
                return match.group(1).strip(), num_results

        # If no pattern matches, return original query
        return query.strip(), num_results

    def _make_request(
        self,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make a request to Google Custom Search API.

        Args:
            params: Search parameters

        Returns:
            Response dictionary
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Google Search API key not configured. Set GOOGLE_SEARCH_API_KEY or GOOGLE_API_KEY environment variable."
            }

        if not self.search_engine_id:
            return {
                "success": False,
                "error": "Google Search Engine ID (CX) not configured. Set GOOGLE_SEARCH_ENGINE_ID environment variable."
            }

        # Add required parameters
        params["key"] = self.api_key
        params["cx"] = self.search_engine_id

        try:
            logger.debug(f"Google Search API request: {params.get('q')}")

            response = requests.get(
                url=self.api_base,
                params=params,
                timeout=30
            )

            # Check for errors
            if response.status_code == 403:
                return {
                    "success": False,
                    "error": "API key authentication failed or quota exceeded. Check your credentials and quota."
                }

            if response.status_code == 429:
                return {
                    "success": False,
                    "error": "Rate limit exceeded. Please wait before making more requests."
                }

            if response.status_code >= 400:
                error_msg = f"Google Search API error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

            # Parse response
            result = response.json() if response.text else {}

            return {
                "success": True,
                "data": result
            }

        except requests.Timeout:
            return {
                "success": False,
                "error": "Google Search API request timed out"
            }
        except Exception as e:
            logger.error(f"Error making Google Search API request: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _format_search_results(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format search results from API response.

        Args:
            api_response: Raw API response

        Returns:
            Formatted results dictionary
        """
        items = api_response.get("items", [])
        search_info = api_response.get("searchInformation", {})

        formatted_items = []
        for item in items:
            formatted_item = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "display_link": item.get("displayLink", ""),
                "formatted_url": item.get("formattedUrl", ""),
                "html_snippet": item.get("htmlSnippet", ""),
                "mime": item.get("mime", "text/html"),
                "file_format": item.get("fileFormat")
            }
            formatted_items.append(formatted_item)

        return {
            "items": formatted_items,
            "total_results": search_info.get("formattedTotalResults", "0"),
            "search_time": search_info.get("searchTime", 0)
        }

    def search(
        self,
        query: str,
        num_results: Optional[int] = None,
        start_index: int = 1,
        safe_search: str = "active",
        language: str = "en",
        country: Optional[str] = None,
        date_restrict: Optional[str] = None,
        file_type: Optional[str] = None,
        site_search: Optional[str] = None,
        exact_terms: Optional[str] = None,
        exclude_terms: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Perform a Google search.

        Args:
            query: Search query
            num_results: Number of results (max 10 per request)
            start_index: Starting index for pagination
            safe_search: Safe search level (active, moderate, off)
            language: Interface language
            country: Country code for geolocation
            date_restrict: Time period restriction
            file_type: Restrict to specific file type
            site_search: Restrict to specific site
            exact_terms: Exact phrase that must appear
            exclude_terms: Terms to exclude
            use_cache: Whether to use RAG cache

        Returns:
            Search results dictionary
        """
        # Extract query from natural language
        processed_query, extracted_num = self._extract_query_from_natural_language(query)

        # Use extracted num_results if found
        if extracted_num and not num_results:
            num_results = extracted_num

        # Build search parameters
        params = {
            "q": processed_query,
            "num": min(num_results or self.max_results, 10),
            "start": start_index,
            "safe": safe_search,
            "lr": f"lang_{language}"
        }

        # Add optional parameters
        if country:
            params["gl"] = country

        if date_restrict:
            params["dateRestrict"] = date_restrict

        if file_type:
            params["fileType"] = file_type

        if site_search:
            params["siteSearch"] = site_search

        if exact_terms:
            params["exactTerms"] = exact_terms

        if exclude_terms:
            params["excludeTerms"] = exclude_terms

        # Generate cache key
        cache_key = self._generate_cache_key(params)

        # Check cache if enabled
        if use_cache:
            cached_data = self._check_cache(cache_key)
            if cached_data:
                return {
                    "success": True,
                    "query": query,
                    "processed_query": processed_query,
                    "data": cached_data
                }

        # Make API request
        result = self._make_request(params)

        if not result["success"]:
            return {
                "success": False,
                "error": result["error"],
                "query": query
            }

        # Format results
        formatted_data = self._format_search_results(result["data"])
        formatted_data["cached"] = False
        formatted_data["cache_timestamp"] = None

        # Store in cache
        if use_cache:
            self._store_in_cache(cache_key, processed_query, formatted_data)

        return {
            "success": True,
            "query": query,
            "processed_query": processed_query,
            "data": formatted_data
        }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a search.

        Args:
            params: Search parameters

        Returns:
            Result dictionary
        """
        query = params.get("query")

        if not query:
            return {
                "success": False,
                "error": "No query specified. Provide a search query."
            }

        try:
            # Extract parameters
            num_results = params.get("num_results")
            start_index = params.get("start_index", 1)
            safe_search = params.get("safe_search", "active")
            language = params.get("language", "en")
            country = params.get("country")
            date_restrict = params.get("date_restrict")
            file_type = params.get("file_type")
            site_search = params.get("site_search")
            exact_terms = params.get("exact_terms")
            exclude_terms = params.get("exclude_terms")
            use_cache = params.get("use_cache", True)

            # Perform search
            result = self.search(
                query=query,
                num_results=num_results,
                start_index=start_index,
                safe_search=safe_search,
                language=language,
                country=country,
                date_restrict=date_restrict,
                file_type=file_type,
                site_search=site_search,
                exact_terms=exact_terms,
                exclude_terms=exclude_terms,
                use_cache=use_cache
            )

            return result

        except Exception as e:
            logger.error(f"Error executing Google Search: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
