#!/usr/bin/env python3
"""
Integration Tests for GitHub Tool

Tests GitHub API integration, URL parsing, authentication, and error handling.
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


@pytest.fixture
def github_tool():
    """Create GitHub tool instance."""
    from src.github_tool import GitHubTool
    return GitHubTool()


@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": 40,
            "title": "Test PR",
            "state": "closed",
            "merged": True,
            "user": {"login": "testuser"},
            "created_at": "2025-01-10T09:00:00Z"
        }
        mock_get.return_value = mock_response
        yield mock_get


def test_github_tool_initialization(github_tool):
    """Test GitHub tool can be initialized."""
    assert github_tool is not None
    assert hasattr(github_tool, 'execute')


def test_url_parsing_full_pr_url(github_tool):
    """Test parsing full GitHub PR URL."""
    url = "https://github.com/scottgal/mostlylucid.dse/pull/40"

    # Parse URL
    owner, repo, pr_number = github_tool._parse_pr_url(url)

    assert owner == "scottgal"
    assert repo == "mostlylucid.dse"
    assert pr_number == 40


def test_url_parsing_owner_repo_format(github_tool):
    """Test parsing owner/repo format."""
    url = "scottgal/mostlylucid.dse"

    owner, repo, pr_number = github_tool._parse_repo_url(url)

    assert owner == "scottgal"
    assert repo == "mostlylucid.dse"
    assert pr_number is None


def test_check_merged_action(github_tool, mock_github_api):
    """Test check_merged action."""
    input_data = {
        "action": "check_merged",
        "repo_url": "https://github.com/scottgal/mostlylucid.dse/pull/40"
    }

    result = github_tool.execute(input_data)

    assert result["success"] is True
    assert result["action"] == "check_merged"
    assert "data" in result
    assert result["data"]["pr_number"] == 40


def test_pr_status_action(github_tool, mock_github_api):
    """Test pr_status action."""
    input_data = {
        "action": "pr_status",
        "owner": "scottgal",
        "repo": "mostlylucid.dse",
        "pr_number": 40
    }

    result = github_tool.execute(input_data)

    assert result["success"] is True
    assert result["action"] == "pr_status"
    assert result["data"]["number"] == 40
    assert result["data"]["merged"] is True


def test_pr_list_action(github_tool):
    """Test pr_list action."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"number": 41, "title": "PR 1", "user": {"login": "user1"}},
            {"number": 42, "title": "PR 2", "user": {"login": "user2"}}
        ]
        mock_get.return_value = mock_response

        input_data = {
            "action": "pr_list",
            "repo_url": "scottgal/mostlylucid.dse",
            "state": "open"
        }

        result = github_tool.execute(input_data)

        assert result["success"] is True
        assert len(result["data"]["prs"]) == 2


def test_authentication_with_token(github_tool):
    """Test authentication uses token from config or environment."""
    with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token"}):
        headers = github_tool._get_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "token ghp_test_token"


def test_authentication_without_token(github_tool):
    """Test authentication without token."""
    with patch.dict(os.environ, {}, clear=True):
        headers = github_tool._get_auth_headers()

        # Should still work but without auth header
        assert "Accept" in headers


def test_error_handling_invalid_repo(github_tool):
    """Test error handling for invalid repository."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}
        mock_get.return_value = mock_response

        input_data = {
            "action": "pr_status",
            "owner": "invalid",
            "repo": "nonexistent",
            "pr_number": 999
        }

        result = github_tool.execute(input_data)

        assert result["success"] is False
        assert "error" in result


def test_error_handling_rate_limit(github_tool):
    """Test error handling for rate limit."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "API rate limit exceeded"
        }
        mock_get.return_value = mock_response

        input_data = {
            "action": "pr_status",
            "owner": "scottgal",
            "repo": "mostlylucid.dse",
            "pr_number": 40
        }

        result = github_tool.execute(input_data)

        assert result["success"] is False
        assert "rate limit" in result["error"].lower()


def test_pr_comments_action(github_tool):
    """Test getting PR comments."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "user": {"login": "reviewer1"},
                "body": "Looks good!",
                "created_at": "2025-01-11T10:00:00Z"
            },
            {
                "user": {"login": "reviewer2"},
                "body": "Minor changes needed",
                "created_at": "2025-01-11T11:00:00Z"
            }
        ]
        mock_get.return_value = mock_response

        input_data = {
            "action": "pr_comments",
            "owner": "scottgal",
            "repo": "mostlylucid.dse",
            "pr_number": 40
        }

        result = github_tool.execute(input_data)

        assert result["success"] is True
        assert len(result["data"]["comments"]) == 2
        assert result["data"]["comments"][0]["author"] == "reviewer1"


def test_integration_with_config(github_tool):
    """Test integration with config.yaml settings."""
    from src.config_manager import ConfigManager

    config = ConfigManager()

    # Check if GitHub config section exists
    github_config = config.get("git.github", {})

    if "token" in github_config:
        # If configured, test should use it
        headers = github_tool._get_auth_headers()
        assert "Authorization" in headers


def test_pr_merge_status(github_tool):
    """Test getting PR merge status."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mergeable": True,
            "mergeable_state": "clean"
        }
        mock_get.return_value = mock_response

        input_data = {
            "action": "pr_merge_status",
            "owner": "scottgal",
            "repo": "mostlylucid.dse",
            "pr_number": 40
        }

        result = github_tool.execute(input_data)

        assert result["success"] is True
        assert result["data"]["mergeable"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
