"""
Google Fact Check Tool for mostlylucid DiSE.
Provides Google Fact Check Tools API integration for verifying claims and checking facts.
"""
import json
import logging
import os
import re
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger(__name__)


class GoogleFactCheckTool:
    """
    Google Fact Check integration tool for claim verification and fact-checking.

    Features:
    - Search fact-checks for claims and statements
    - Filter by language, age, and publisher
    - Pagination support
    - Natural language query support
    - Authentication from config.yaml or environment
    - Multiple fact-checking sources
    """

    def __init__(
        self,
        api_base: str = "https://factchecktools.googleapis.com/v1alpha1",
        max_results: int = 10,
        config_manager: Optional[Any] = None
    ):
        """
        Initialize Google Fact Check tool.

        Args:
            api_base: Google Fact Check API base URL
            max_results: Default maximum results to return
            config_manager: ConfigManager for loading credentials
        """
        self.api_base = api_base
        self.max_results = max_results
        self.config_manager = config_manager

        # Load API key
        self.api_key = self._load_api_key()

        if self.api_key:
            logger.info("Google Fact Check tool initialized with API key")
        else:
            logger.warning("Google Fact Check tool initialized WITHOUT API key")

    def _load_api_key(self) -> Optional[str]:
        """Load Google Fact Check API key from config.yaml or environment."""
        # Try environment variable first
        api_key = os.getenv("GOOGLE_FACTCHECK_API_KEY")
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
                factcheck_config = google_config.get("factcheck", {})
                api_key = factcheck_config.get("api_key", "")
                if api_key:
                    return os.path.expandvars(api_key)

                # Try generic Google API key in config
                api_key = google_config.get("api_key", "")
                if api_key:
                    return os.path.expandvars(api_key)
            except Exception as e:
                logger.error(f"Error loading Google Fact Check API key from config: {e}")

        return None

    def _extract_claim_from_natural_language(self, query: str) -> str:
        """
        Extract the actual claim from natural language questions.

        Examples:
        - "Can you check if vaccines cause autism?" -> "vaccines cause autism"
        - "Is it true that the earth is flat?" -> "the earth is flat"
        - "Fact-check: climate change is real" -> "climate change is real"

        Args:
            query: Natural language query

        Returns:
            Extracted claim text
        """
        # Patterns to match natural language queries
        patterns = [
            r"^can you (?:check|verify|fact-?check) (?:if |whether |that )?(.+?)(?:\?)?$",
            r"^is it true (?:that )?(.+?)(?:\?)?$",
            r"^fact-?check:?\s*(.+?)(?:\?)?$",
            r"^verify:?\s*(.+?)(?:\?)?$",
            r"^check:?\s*(.+?)(?:\?)?$",
            r"^(.+?)(?: true or false| real or fake)(?:\?)?$",
        ]

        query_lower = query.lower().strip()

        for pattern in patterns:
            match = re.match(pattern, query_lower, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # If no pattern matches, return original query
        return query.strip()

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make a request to Google Fact Check API.

        Args:
            endpoint: API endpoint (e.g., '/claims:search')
            params: Query parameters

        Returns:
            Response dictionary
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Google Fact Check API key not configured. Set GOOGLE_FACTCHECK_API_KEY environment variable or add to config.yaml"
            }

        url = f"{self.api_base}{endpoint}"

        # Add API key to params
        params = params or {}
        params["key"] = self.api_key

        try:
            logger.debug(f"Google Fact Check API request: GET {endpoint}")
            logger.debug(f"Query params: {params}")

            response = requests.get(
                url=url,
                params=params,
                timeout=30
            )

            # Check for errors
            if response.status_code == 403:
                return {
                    "success": False,
                    "error": "API key authentication failed. Check your GOOGLE_FACTCHECK_API_KEY"
                }

            if response.status_code == 429:
                return {
                    "success": False,
                    "error": "Rate limit exceeded. Please wait before making more requests."
                }

            if response.status_code >= 400:
                error_msg = f"Google Fact Check API error {response.status_code}: {response.text}"
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
                "error": "Google Fact Check API request timed out"
            }
        except Exception as e:
            logger.error(f"Error making Google Fact Check API request: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _format_claim_data(self, claim_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a claim object from API response.

        Args:
            claim_obj: Raw claim object from API

        Returns:
            Formatted claim dictionary
        """
        # Extract main claim text
        claim_text = claim_obj.get("text", "")

        # Extract claimant
        claimant = claim_obj.get("claimant", "Unknown")

        # Extract claim date
        claim_date = claim_obj.get("claimDate", None)

        # Extract claim review (the fact-check)
        claim_reviews = claim_obj.get("claimReview", [])

        formatted_reviews = []
        for review in claim_reviews:
            formatted_review = {
                "publisher": {
                    "name": review.get("publisher", {}).get("name", "Unknown"),
                    "site": review.get("publisher", {}).get("site", "")
                },
                "url": review.get("url", ""),
                "title": review.get("title", ""),
                "review_date": review.get("reviewDate", None),
                "textual_rating": review.get("textualRating", "Not Rated"),
                "language_code": review.get("languageCode", "en")
            }
            formatted_reviews.append(formatted_review)

        # Return formatted claim with the first review (primary)
        return {
            "claim_text": claim_text,
            "claimant": claimant,
            "claim_date": claim_date,
            "claim_review": formatted_reviews[0] if formatted_reviews else {},
            "all_reviews": formatted_reviews
        }

    def search_claims(
        self,
        query: str,
        language_code: Optional[str] = None,
        max_age_days: Optional[int] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        review_publisher_site_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for fact-checks on claims.

        Args:
            query: The claim or statement to fact-check
            language_code: BCP-47 language code (e.g., 'en', 'en-US')
            max_age_days: Maximum age of fact-checks in days
            page_size: Number of results to return (max 100)
            page_token: Token for pagination
            review_publisher_site_filter: Filter by publisher site

        Returns:
            Result dictionary with claims and fact-checks
        """
        # Extract claim from natural language if needed
        processed_query = self._extract_claim_from_natural_language(query)

        # Build request parameters
        params = {
            "query": processed_query
        }

        if language_code:
            params["languageCode"] = language_code

        if max_age_days is not None:
            params["maxAgeDays"] = max_age_days

        if page_size is not None:
            params["pageSize"] = min(page_size, 100)
        else:
            params["pageSize"] = self.max_results

        if page_token:
            params["pageToken"] = page_token

        if review_publisher_site_filter:
            params["reviewPublisherSiteFilter"] = review_publisher_site_filter

        # Make API request
        result = self._make_request("/claims:search", params)

        if not result["success"]:
            return {
                "success": False,
                "error": result["error"],
                "query": query
            }

        # Parse claims from response
        api_data = result["data"]
        claims = api_data.get("claims", [])

        # Format claims
        formatted_claims = [self._format_claim_data(claim) for claim in claims]

        # Get next page token if available
        next_page_token = api_data.get("nextPageToken")

        return {
            "success": True,
            "query": query,
            "processed_query": processed_query,
            "data": {
                "claims": formatted_claims,
                "next_page_token": next_page_token,
                "total_results": len(formatted_claims)
            }
        }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a fact-check search.

        Args:
            params: Search parameters

        Returns:
            Result dictionary
        """
        query = params.get("query")

        if not query:
            return {
                "success": False,
                "error": "No query specified. Provide a claim or statement to fact-check."
            }

        try:
            # Extract optional parameters
            language_code = params.get("language_code", "en")
            max_age_days = params.get("max_age_days")
            page_size = params.get("page_size")
            page_token = params.get("page_token")
            review_publisher_site_filter = params.get("review_publisher_site_filter")

            # Perform search
            result = self.search_claims(
                query=query,
                language_code=language_code,
                max_age_days=max_age_days,
                page_size=page_size,
                page_token=page_token,
                review_publisher_site_filter=review_publisher_site_filter
            )

            return result

        except Exception as e:
            logger.error(f"Error executing Google Fact Check search: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
