"""Coordinator for orchestrating multiple agents."""
from typing import Any, Dict, Optional

from anthropic import Anthropic
from loguru import logger

from src.agents.bug_reproducer import BugReproducer
from src.agents.code_locator import CodeLocator
from src.agents.issue_analyzer import IssueAnalyzer
from src.core.state import WorkflowState, WorkflowStatus
from src.tools.github_client import GitHubClient


class Coordinator:
    """Orchestrates the bug triage workflow across multiple agents.

    Pipeline:
    1. Issue Analysis   (required)
    2. Code Location    (requires repo_path, skipped otherwise)
    3. Bug Reproduction (requires repo_path, skipped otherwise)
    """

    def __init__(
        self,
        anthropic_client: Anthropic,
        github_client: GitHubClient,
        repo_path: Optional[str] = None,
    ):
        self.anthropic_client = anthropic_client
        self.github_client = github_client
        self.repo_path = repo_path
        self.state = WorkflowState()

    def run(self, issue_url: str) -> WorkflowState:
        """Execute the bug triage workflow.

        Args:
            issue_url: GitHub issue URL to analyze

        Returns:
            WorkflowState with results from each phase
        """
        self.state.status = WorkflowStatus.IN_PROGRESS
        logger.info(f"Starting bug triage for: {issue_url}")

        # Phase 1: Issue Analysis (always runs)
        self.state.current_phase = "issue_analysis"
        try:
            logger.info("Phase 1: Analyzing issue...")
            analyzer = IssueAnalyzer(
                client=self.anthropic_client,
                github_client=self.github_client,
            )
            result = analyzer.process({"issue_url": issue_url})
            self.state.update("issue_analysis", result)
            logger.info("Phase 1 completed")
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            self.state.add_error("issue_analysis", str(e))
            self.state.status = WorkflowStatus.FAILED
            return self.state

        # Phase 2 & 3 require a local repo
        if not self.repo_path:
            logger.info("No repo_path provided, skipping code location and reproduction")
            self.state.status = WorkflowStatus.COMPLETED
            return self.state

        # Phase 2: Code Location
        self.state.current_phase = "code_location"
        try:
            logger.info("Phase 2: Locating relevant code...")
            locator = CodeLocator(
                client=self.anthropic_client,
                repo_path=self.repo_path,
            )
            result = locator.process({
                "issue_data": self.state.get("issue_analysis"),
            })
            self.state.update("code_location", result)
            logger.info("Phase 2 completed")
        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            self.state.add_error("code_location", str(e))
            # Non-fatal: continue with empty code locations

        # Phase 3: Bug Reproduction
        self.state.current_phase = "bug_reproduction"
        try:
            logger.info("Phase 3: Attempting to reproduce bug...")
            reproducer = BugReproducer(
                client=self.anthropic_client,
                repo_path=self.repo_path,
            )
            result = reproducer.process({
                "issue_data": self.state.get("issue_analysis"),
                "code_locations": self.state.get("code_location", {}),
            })
            self.state.update("bug_reproduction", result)
            logger.info("Phase 3 completed")
        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            self.state.add_error("bug_reproduction", str(e))

        self.state.status = WorkflowStatus.COMPLETED
        logger.info("Bug triage workflow completed")
        return self.state