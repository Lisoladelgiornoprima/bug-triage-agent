"""GitHub API client for fetching issues and repository data."""
import re
from typing import Any

from github import Github, GithubException
from loguru import logger


class GitHubClient:
    """Wraps PyGithub to provide issue-related operations."""

    def __init__(self, token: str):
        self.gh = Github(token)

    @staticmethod
    def parse_issue_url(url: str) -> tuple[str, int]:
        """Extract owner/repo and issue number from a GitHub issue URL.

        Args:
            url: e.g. "https://github.com/psf/requests/issues/6234"

        Returns:
            Tuple of (owner/repo, issue_number)
        """
        pattern = r"github\.com/([^/]+/[^/]+)/issues/(\d+)"
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Invalid GitHub issue URL: {url}")
        return match.group(1), int(match.group(2))

    def get_issue(self, url: str) -> dict[str, Any]:
        """Fetch issue details from a GitHub URL."""
        repo_name, issue_number = self.parse_issue_url(url)
        logger.info(f"Fetching issue #{issue_number} from {repo_name}")

        try:
            repo = self.gh.get_repo(repo_name)
            issue = repo.get_issue(issue_number)
        except GithubException as e:
            raise RuntimeError(f"Failed to fetch issue: {e}") from e

        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "state": issue.state,
            "labels": [label.name for label in issue.labels],
            "created_at": issue.created_at.isoformat(),
            "updated_at": issue.updated_at.isoformat(),
            "user": issue.user.login if issue.user else "unknown",
            "url": issue.html_url,
            "comments_count": issue.comments,
        }

    def get_issue_comments(self, url: str) -> list[dict[str, Any]]:
        """Fetch all comments for an issue."""
        repo_name, issue_number = self.parse_issue_url(url)
        logger.info(f"Fetching comments for issue #{issue_number}")

        try:
            repo = self.gh.get_repo(repo_name)
            issue = repo.get_issue(issue_number)
            comments = issue.get_comments()
        except GithubException as e:
            raise RuntimeError(f"Failed to fetch comments: {e}") from e

        return [
            {
                "user": comment.user.login if comment.user else "unknown",
                "body": comment.body,
                "created_at": comment.created_at.isoformat(),
            }
            for comment in comments
        ]

    def search_similar_issues(
        self, repo_name: str, keywords: list[str], limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search for similar issues in a repository."""
        query = f"repo:{repo_name} is:issue {' '.join(keywords)}"
        logger.info(f"Searching issues with query: {query}")

        try:
            results = self.gh.search_issues(query=query)
            issues = []
            for issue in results[:limit]:
                issues.append(
                    {
                        "number": issue.number,
                        "title": issue.title,
                        "url": issue.html_url,
                        "state": issue.state,
                    }
                )
            return issues
        except GithubException as e:
            logger.warning(f"Failed to search issues: {e}")
            return []
