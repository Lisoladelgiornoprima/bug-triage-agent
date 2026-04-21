"""Tests for GitHubClient."""
import pytest

from src.tools.github_client import GitHubClient


class TestParseIssueUrl:
    """Test URL parsing (no API calls needed)."""

    def test_parse_standard_url(self):
        repo, number = GitHubClient.parse_issue_url(
            "https://github.com/psf/requests/issues/6655"
        )
        assert repo == "psf/requests"
        assert number == 6655

    def test_parse_url_with_trailing_slash(self):
        repo, number = GitHubClient.parse_issue_url(
            "https://github.com/owner/repo/issues/123/"
        )
        assert repo == "owner/repo"
        assert number == 123

    def test_parse_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Invalid GitHub issue URL"):
            GitHubClient.parse_issue_url("https://example.com/not-github")

    def test_parse_url_without_issue_number_raises(self):
        with pytest.raises(ValueError):
            GitHubClient.parse_issue_url("https://github.com/owner/repo/pulls/1")
