"""Issue Analyzer Agent - analyzes GitHub issues to extract structured bug info."""
import json
from typing import Any, Dict, List

from loguru import logger

from src.core.agent_base import BaseAgent
from src.tools.github_client import GitHubClient


class IssueAnalyzer(BaseAgent):
    """Analyzes a GitHub issue and extracts structured bug information.

    Tools: get_issue, get_issue_comments, search_similar_issues
    Output: Structured analysis including bug type, severity, stack traces, etc.
    """

    def __init__(self, client, github_client: GitHubClient, model: str = "claude-sonnet-4-6"):
        self.github_client = github_client
        super().__init__(name="IssueAnalyzer", client=client, model=model)

    def _register_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "get_issue",
                "description": "Fetch the details of a GitHub issue given its URL. Returns title, body, labels, state, etc.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The full GitHub issue URL",
                        }
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "get_issue_comments",
                "description": "Fetch all comments on a GitHub issue. Useful for additional context and reproduction details.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The full GitHub issue URL",
                        }
                    },
                    "required": ["url"],
                },
            },
        ]

    def _build_system_prompt(self) -> str:
        return """You are an expert bug triage analyst. Your job is to analyze GitHub issues and extract structured information.

For each issue, you should:
1. Use get_issue to fetch the issue details
2. Use get_issue_comments if you need more context
3. Extract and structure the following information:
   - bug_type: "crash", "logic_error", "performance", "ui", or "unknown"
   - severity: "critical", "major", or "minor"
   - error_messages: List of error messages found
   - stack_trace: Full stack trace if present (null if not)
   - steps_to_reproduce: List of steps to reproduce the bug
   - affected_components: List of components/modules affected
   - environment: Dict of environment info (OS, version, etc.)
   - related_files_hint: List of file paths mentioned in the issue

Output your analysis as JSON in this format:
```json
{
  "title": "...",
  "bug_type": "...",
  "severity": "...",
  "error_messages": [...],
  "stack_trace": "..." or null,
  "steps_to_reproduce": [...],
  "affected_components": [...],
  "environment": {...},
  "related_files_hint": [...]
}
```

Be thorough but concise. If information is missing, use null or empty lists."""

    def _build_initial_messages(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build initial message with the issue URL."""
        issue_url = context.get("issue_url", "")
        return [
            {
                "role": "user",
                "content": f"Please analyze this GitHub issue and provide a structured analysis: {issue_url}",
            }
        ]

    def _handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute GitHub API calls."""
        try:
            if tool_name == "get_issue":
                result = self.github_client.get_issue(tool_input["url"])
                return json.dumps(result, indent=2)
            elif tool_name == "get_issue_comments":
                result = self.github_client.get_issue_comments(tool_input["url"])
                return json.dumps(result, indent=2)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return f"Error: {e}"
