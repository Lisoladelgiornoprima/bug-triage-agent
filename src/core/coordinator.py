"""Coordinator for orchestrating multiple agents."""
from typing import Dict, Any

from anthropic import Anthropic
from loguru import logger

from src.agents.issue_analyzer import IssueAnalyzer
from src.core.state import WorkflowState, WorkflowStatus
from src.tools.github_client import GitHubClient


class Coordinator:
    """Orchestrates the bug triage workflow across multiple agents.

    Currently implements a simple sequential pipeline:
    1. Issue Analysis
    (Future: 2. Code Location, 3. Bug Reproduction, 4. Fix Generation)
    """

    def __init__(self, anthropic_client: Anthropic, github_client: GitHubClient):
        self.anthropic_client = anthropic_client
        self.github_client = github_client
        self.state = WorkflowState()
        self.agents = self._init_agents()

    def _init_agents(self) -> Dict[str, Any]:
        """Initialize all agents."""
        return {
            "issue_analyzer": IssueAnalyzer(
                client=self.anthropic_client,
                github_client=self.github_client,
            ),
        }

    def run(self, issue_url: str) -> WorkflowState:
        """Execute the bug triage workflow.

        Args:
            issue_url: GitHub issue URL to analyze

        Returns:
            WorkflowState with results from each phase
        """
        self.state.status = WorkflowStatus.IN_PROGRESS
        logger.info(f"Starting bug triage for: {issue_url}")

        # Phase 1: Issue Analysis
        self.state.current_phase = "issue_analysis"
        try:
            logger.info("Phase 1: Analyzing issue...")
            result = self.agents["issue_analyzer"].process({"issue_url": issue_url})
            self.state.update("issue_analysis", result)
            logger.info("Phase 1 completed successfully")
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            self.state.add_error("issue_analysis", str(e))
            self.state.status = WorkflowStatus.FAILED
            return self.state

        # Future phases will be added here
        # Phase 2: Code Location
        # Phase 3: Bug Reproduction
        # Phase 4: Fix Generation

        self.state.status = WorkflowStatus.COMPLETED
        logger.info("Bug triage workflow completed")
        return self.state