"""
GitHub Tool for Code Evolver.
Provides GitHub API integration for PR management, issue tracking, and repository operations.
"""
import json
import logging
import os
import re
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)


class GitHubTool:
    """
    GitHub integration tool for PR management and repository operations.

    Features:
    - Pull Request management (status, list, comments, reviews, merge status)
    - Issue tracking
    - Repository information
    - Authentication from config.yaml
    - URL parsing (supports multiple formats)
    - Rate limit handling
    """

    GITHUB_API_BASE = "https://api.github.com"

    def __init__(
        self,
        api_version: str = "2022-11-28",
        max_results: int = 100,
        config_manager: Optional[Any] = None
    ):
        """
        Initialize GitHub tool.

        Args:
            api_version: GitHub API version
            max_results: Maximum results to return
            config_manager: ConfigManager for loading credentials
        """
        self.api_version = api_version
        self.max_results = max_results
        self.config_manager = config_manager

        # Load credentials
        self.token = self._load_token()

        # Prepare headers
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version
        }

        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
            logger.info("GitHub tool initialized with authentication")
        else:
            logger.warning("GitHub tool initialized WITHOUT authentication (rate limits apply)")

    def _load_token(self) -> Optional[str]:
        """Load GitHub token from config.yaml or environment."""
        # Try environment variable first
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token

        # Try config manager
        if self.config_manager:
            try:
                git_config = self.config_manager.get("git", {})
                github_config = git_config.get("github", {})
                token = github_config.get("token", "")
                if token:
                    return os.path.expandvars(token)
            except Exception as e:
                logger.error(f"Error loading GitHub token from config: {e}")

        return None

    def _parse_repo_url(self, repo_url: str) -> Tuple[str, str, Optional[int]]:
        """
        Parse repository URL to extract owner, repo, and optional PR/issue number.

        Supports formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo/pull/123
        - https://github.com/owner/repo/issues/456
        - owner/repo

        Args:
            repo_url: Repository URL or owner/repo string

        Returns:
            Tuple of (owner, repo, number)
        """
        # Handle full GitHub URLs
        if repo_url.startswith("http"):
            parsed = urlparse(repo_url)
            path_parts = parsed.path.strip("/").split("/")

            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo = path_parts[1]

                # Check for PR/issue number
                number = None
                if len(path_parts) >= 4 and path_parts[2] in ["pull", "issues"]:
                    try:
                        number = int(path_parts[3])
                    except ValueError:
                        pass

                return owner, repo, number

        # Handle owner/repo format
        elif "/" in repo_url:
            parts = repo_url.split("/")
            if len(parts) == 2:
                return parts[0], parts[1], None

        raise ValueError(f"Invalid repository URL format: {repo_url}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make a request to GitHub API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/repos/owner/repo/pulls')
            params: Query parameters
            data: Request body data

        Returns:
            Response dictionary
        """
        url = f"{self.GITHUB_API_BASE}{endpoint}"

        try:
            logger.debug(f"GitHub API request: {method} {endpoint}")

            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30
            )

            # Check rate limit
            if response.status_code == 403:
                if "rate limit" in response.text.lower():
                    return {
                        "success": False,
                        "error": "GitHub API rate limit exceeded. Use authentication for higher limits."
                    }

            # Check for errors
            if response.status_code >= 400:
                error_msg = f"GitHub API error {response.status_code}: {response.text}"
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
                "error": "GitHub API request timed out"
            }
        except Exception as e:
            logger.error(f"Error making GitHub API request: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def check_merged(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """
        Check if a pull request is merged.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Result with merge status
        """
        # Get PR details
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        result = self._make_request("GET", endpoint)

        if not result["success"]:
            return result

        pr_data = result["data"]

        return {
            "success": True,
            "data": {
                "pr_number": pr_number,
                "is_merged": pr_data.get("merged", False),
                "merged_at": pr_data.get("merged_at"),
                "merged_by": pr_data.get("merged_by", {}).get("login") if pr_data.get("merged_by") else None,
                "state": pr_data.get("state"),
                "title": pr_data.get("title")
            }
        }

    def pr_status(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Get pull request status and details."""
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        result = self._make_request("GET", endpoint)

        if not result["success"]:
            return result

        pr = result["data"]

        return {
            "success": True,
            "data": {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "body": pr.get("body"),
                "state": pr.get("state"),
                "merged": pr.get("merged", False),
                "mergeable": pr.get("mergeable"),
                "draft": pr.get("draft", False),
                "author": pr.get("user", {}).get("login"),
                "created_at": pr.get("created_at"),
                "updated_at": pr.get("updated_at"),
                "merged_at": pr.get("merged_at"),
                "head_ref": pr.get("head", {}).get("ref"),
                "base_ref": pr.get("base", {}).get("ref"),
                "commits": pr.get("commits"),
                "additions": pr.get("additions"),
                "deletions": pr.get("deletions"),
                "changed_files": pr.get("changed_files")
            }
        }

    def pr_list(
        self,
        owner: str,
        repo: str,
        state: str = "open"
    ) -> Dict[str, Any]:
        """List pull requests."""
        endpoint = f"/repos/{owner}/{repo}/pulls"
        params = {
            "state": state,
            "per_page": min(self.max_results, 100)
        }

        result = self._make_request("GET", endpoint, params=params)

        if not result["success"]:
            return result

        prs = result["data"]

        return {
            "success": True,
            "data": {
                "prs": [
                    {
                        "number": pr.get("number"),
                        "title": pr.get("title"),
                        "state": pr.get("state"),
                        "author": pr.get("user", {}).get("login"),
                        "created_at": pr.get("created_at"),
                        "updated_at": pr.get("updated_at")
                    }
                    for pr in prs
                ]
            }
        }

    def pr_comments(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Get pull request comments."""
        endpoint = f"/repos/{owner}/{repo}/issues/{pr_number}/comments"
        result = self._make_request("GET", endpoint)

        if not result["success"]:
            return result

        comments = result["data"]

        return {
            "success": True,
            "data": {
                "comments": [
                    {
                        "id": comment.get("id"),
                        "author": comment.get("user", {}).get("login"),
                        "body": comment.get("body"),
                        "created_at": comment.get("created_at")
                    }
                    for comment in comments
                ]
            }
        }

    def pr_reviews(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Get pull request reviews."""
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        result = self._make_request("GET", endpoint)

        if not result["success"]:
            return result

        reviews = result["data"]

        return {
            "success": True,
            "data": {
                "reviews": [
                    {
                        "id": review.get("id"),
                        "author": review.get("user", {}).get("login"),
                        "state": review.get("state"),
                        "body": review.get("body"),
                        "submitted_at": review.get("submitted_at")
                    }
                    for review in reviews
                ]
            }
        }

    def pr_files(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Get files changed in pull request."""
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
        result = self._make_request("GET", endpoint)

        if not result["success"]:
            return result

        files = result["data"]

        return {
            "success": True,
            "data": {
                "files": [
                    {
                        "filename": file.get("filename"),
                        "status": file.get("status"),
                        "additions": file.get("additions"),
                        "deletions": file.get("deletions"),
                        "changes": file.get("changes")
                    }
                    for file in files
                ]
            }
        }

    def issue_status(
        self,
        owner: str,
        repo: str,
        issue_number: int
    ) -> Dict[str, Any]:
        """Get issue status and details."""
        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}"
        result = self._make_request("GET", endpoint)

        if not result["success"]:
            return result

        issue = result["data"]

        return {
            "success": True,
            "data": {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "body": issue.get("body"),
                "state": issue.get("state"),
                "author": issue.get("user", {}).get("login"),
                "created_at": issue.get("created_at"),
                "updated_at": issue.get("updated_at"),
                "closed_at": issue.get("closed_at"),
                "labels": [label.get("name") for label in issue.get("labels", [])]
            }
        }

    def issue_list(
        self,
        owner: str,
        repo: str,
        state: str = "open"
    ) -> Dict[str, Any]:
        """List issues."""
        endpoint = f"/repos/{owner}/{repo}/issues"
        params = {
            "state": state,
            "per_page": min(self.max_results, 100)
        }

        result = self._make_request("GET", endpoint, params=params)

        if not result["success"]:
            return result

        issues = result["data"]

        # Filter out pull requests (they also appear in issues endpoint)
        issues = [issue for issue in issues if "pull_request" not in issue]

        return {
            "success": True,
            "data": {
                "issues": [
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "state": issue.get("state"),
                        "author": issue.get("user", {}).get("login"),
                        "created_at": issue.get("created_at")
                    }
                    for issue in issues
                ]
            }
        }

    def repo_info(
        self,
        owner: str,
        repo: str
    ) -> Dict[str, Any]:
        """Get repository information."""
        endpoint = f"/repos/{owner}/{repo}"
        result = self._make_request("GET", endpoint)

        if not result["success"]:
            return result

        repo_data = result["data"]

        return {
            "success": True,
            "data": {
                "name": repo_data.get("name"),
                "full_name": repo_data.get("full_name"),
                "description": repo_data.get("description"),
                "private": repo_data.get("private"),
                "owner": repo_data.get("owner", {}).get("login"),
                "default_branch": repo_data.get("default_branch"),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "language": repo_data.get("language"),
                "stargazers_count": repo_data.get("stargazers_count"),
                "forks_count": repo_data.get("forks_count"),
                "open_issues_count": repo_data.get("open_issues_count")
            }
        }

    def create_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        comment_body: str
    ) -> Dict[str, Any]:
        """Create a comment on an issue or PR."""
        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        data = {"body": comment_body}

        result = self._make_request("POST", endpoint, data=data)

        if not result["success"]:
            return result

        comment = result["data"]

        return {
            "success": True,
            "data": {
                "id": comment.get("id"),
                "author": comment.get("user", {}).get("login"),
                "body": comment.get("body"),
                "created_at": comment.get("created_at")
            }
        }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a GitHub action.

        Args:
            params: Action parameters

        Returns:
            Result dictionary
        """
        action = params.get("action")

        if not action:
            return {
                "success": False,
                "error": "No action specified"
            }

        try:
            # Parse repository identification
            owner = params.get("owner")
            repo = params.get("repo")
            repo_url = params.get("repo_url")

            # If repo_url is provided, parse it
            if repo_url and (not owner or not repo):
                parsed_owner, parsed_repo, parsed_number = self._parse_repo_url(repo_url)
                owner = owner or parsed_owner
                repo = repo or parsed_repo

                # Use parsed number if not explicitly provided
                if parsed_number:
                    if not params.get("pr_number") and not params.get("issue_number"):
                        # Determine if it's a PR or issue from the URL
                        if "/pull/" in repo_url:
                            params["pr_number"] = parsed_number
                        elif "/issues/" in repo_url:
                            params["issue_number"] = parsed_number

            # Validate owner and repo
            if not owner or not repo:
                return {
                    "success": False,
                    "error": "Repository owner and name are required (provide repo_url or owner+repo)"
                }

            # Route to appropriate method
            if action == "check_merged":
                pr_number = params.get("pr_number")
                if not pr_number:
                    return {
                        "success": False,
                        "error": "pr_number is required for check_merged action"
                    }
                result = self.check_merged(owner, repo, pr_number)

            elif action == "pr_status":
                pr_number = params.get("pr_number")
                if not pr_number:
                    return {
                        "success": False,
                        "error": "pr_number is required for pr_status action"
                    }
                result = self.pr_status(owner, repo, pr_number)

            elif action == "pr_list":
                state = params.get("state", "open")
                result = self.pr_list(owner, repo, state)

            elif action == "pr_comments":
                pr_number = params.get("pr_number")
                if not pr_number:
                    return {
                        "success": False,
                        "error": "pr_number is required for pr_comments action"
                    }
                result = self.pr_comments(owner, repo, pr_number)

            elif action == "pr_reviews":
                pr_number = params.get("pr_number")
                if not pr_number:
                    return {
                        "success": False,
                        "error": "pr_number is required for pr_reviews action"
                    }
                result = self.pr_reviews(owner, repo, pr_number)

            elif action == "pr_files":
                pr_number = params.get("pr_number")
                if not pr_number:
                    return {
                        "success": False,
                        "error": "pr_number is required for pr_files action"
                    }
                result = self.pr_files(owner, repo, pr_number)

            elif action == "issue_status":
                issue_number = params.get("issue_number")
                if not issue_number:
                    return {
                        "success": False,
                        "error": "issue_number is required for issue_status action"
                    }
                result = self.issue_status(owner, repo, issue_number)

            elif action == "issue_list":
                state = params.get("state", "open")
                result = self.issue_list(owner, repo, state)

            elif action == "repo_info":
                result = self.repo_info(owner, repo)

            elif action == "create_comment":
                issue_number = params.get("pr_number") or params.get("issue_number")
                comment_body = params.get("comment_body")
                if not issue_number or not comment_body:
                    return {
                        "success": False,
                        "error": "issue_number/pr_number and comment_body are required for create_comment"
                    }
                result = self.create_comment(owner, repo, issue_number, comment_body)

            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }

            result["action"] = action
            return result

        except Exception as e:
            logger.error(f"Error executing GitHub action '{action}': {e}")
            return {
                "success": False,
                "action": action,
                "error": str(e)
            }
