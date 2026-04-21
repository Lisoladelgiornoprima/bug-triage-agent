"""Fix Generator Agent - analyzes root cause and generates code fixes."""
import json
from typing import Any

from loguru import logger

from src.core.agent_base import BaseAgent
from src.tools.code_analyzer import CodeAnalyzer
from src.tools.file_system import FileSystemTools


class FixGenerator(BaseAgent):
    """Generates fix suggestions based on all prior analysis.

    Takes issue analysis + code locations + reproduction results as input.
    Reads relevant code, performs root cause analysis, and proposes fixes.

    Tools: read_file, get_file_structure, grep_content
    Output: Root cause analysis + code change diffs + test suggestions
    """

    def __init__(self, client, repo_path: str, model: str = "claude-sonnet-4-6"):
        self.repo_path = repo_path
        self.fs = FileSystemTools(repo_path)
        self.analyzer = CodeAnalyzer(repo_path)
        super().__init__(name="FixGenerator", client=client, model=model)

    def _register_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "read_file",
                "description": "Read a source file to understand the code before proposing a fix.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "File path relative to repo root",
                        },
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "get_file_structure",
                "description": "Get the structure (classes, functions, imports) of a Python file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Python file path relative to repo root",
                        },
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "grep_content",
                "description": "Search for a pattern in file contents across the repository.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for",
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Glob pattern for files to search (default: *.py)",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        ]

    def _build_system_prompt(self) -> str:
        return """You are a senior software engineer specialized in debugging and fixing bugs. Given a complete bug analysis (issue, code locations, reproduction results), your job is to:

1. Read the relevant source files carefully
2. Identify the exact root cause of the bug
3. Propose a concrete code fix
4. Suggest tests to verify the fix

Guidelines:
- Read all relevant files before proposing changes
- Make minimal, targeted changes (don't refactor unrelated code)
- Explain WHY the fix works, not just WHAT it changes
- Consider edge cases and potential regressions
- If you need to understand more code (e.g., callers, related functions), use grep_content

Output your analysis as JSON:
```json
{
  "root_cause": "Clear explanation of why the bug occurs",
  "fix_description": "High-level description of the fix approach",
  "code_changes": [
    {
      "file": "path/to/file.py",
      "description": "What this change does and why",
      "original_code": "the exact code to be replaced (enough lines for context)",
      "fixed_code": "the corrected code"
    }
  ],
  "test_suggestions": [
    "Description of test case 1",
    "Description of test case 2"
  ],
  "confidence": 0.85,
  "risk_assessment": "Low/Medium/High - potential side effects of this fix"
}
```"""

    def _build_initial_messages(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Present all prior analysis results."""
        issue_data = context.get("issue_data", {})
        code_locations = context.get("code_locations", {})
        reproduction = context.get("reproduction", {})

        return [
            {
                "role": "user",
                "content": (
                    "Please analyze this bug and propose a fix.\n\n"
                    f"## Bug Report Analysis\n{json.dumps(issue_data, indent=2, default=str)}\n\n"
                    f"## Code Locations\n{json.dumps(code_locations, indent=2, default=str)}\n\n"
                    f"## Reproduction Results\n{json.dumps(reproduction, indent=2, default=str)}"
                ),
            }
        ]

    def _handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute file system and code analysis tool calls."""
        try:
            if tool_name == "read_file":
                content = self.fs.read_file(tool_input["file_path"])
                if content is None:
                    return "File not found or unreadable"
                return content

            elif tool_name == "get_file_structure":
                result = self.analyzer.get_file_structure(tool_input["file_path"])
                if result is None:
                    return "Failed to parse file"
                return json.dumps(result, indent=2)

            elif tool_name == "grep_content":
                result = self.fs.grep_content(
                    pattern=tool_input["pattern"],
                    file_pattern=tool_input.get("file_pattern", "*.py"),
                )
                return json.dumps(result, indent=2)

            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return f"Error: {e}"
