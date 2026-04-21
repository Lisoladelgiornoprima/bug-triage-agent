"""Code Locator Agent - locates bug-related code files in a repository."""
import json
from typing import Any

from loguru import logger

from src.core.agent_base import BaseAgent
from src.tools.code_analyzer import CodeAnalyzer
from src.tools.file_system import FileSystemTools


class CodeLocator(BaseAgent):
    """Locates code files related to a bug report.

    Uses multiple strategies:
    - Stack trace extraction (direct file paths)
    - Keyword search (grep for error messages, function names)
    - AST analysis (find symbol definitions)

    Tools: search_files, read_file, grep_content, get_file_structure, find_symbol
    Output: List of relevant files with confidence scores
    """

    def __init__(self, client, repo_path: str, model: str = "claude-sonnet-4-6"):
        self.repo_path = repo_path
        self.fs = FileSystemTools(repo_path)
        self.analyzer = CodeAnalyzer(repo_path)
        super().__init__(name="CodeLocator", client=client, model=model)

    def _register_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "search_files",
                "description": "Search for files matching a glob pattern in the repository. Use patterns like '*.py', '*test*.py', 'src/**/*.py'.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern to match files",
                        },
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "read_file",
                "description": "Read the contents of a file. Use this to examine code in detail.",
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
                "name": "grep_content",
                "description": "Search for a regex pattern in file contents. Returns matching lines with file path and line number.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for",
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Glob pattern for files to search in (default: *.py)",
                        },
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "get_file_structure",
                "description": "Get the structure of a Python file: classes, functions, imports, and their line numbers.",
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
                "name": "find_symbol",
                "description": "Find where a function or class is defined across the repository.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol_name": {
                            "type": "string",
                            "description": "Name (or partial name) of the function or class to find",
                        },
                    },
                    "required": ["symbol_name"],
                },
            },
        ]

    def _build_system_prompt(self) -> str:
        return """You are an expert code investigator. Given a bug report analysis, your job is to locate the most relevant source code files in the repository.

Strategy:
1. Start by searching for files related to the affected components
2. If there are error messages or stack traces, grep for those specific strings
3. Use find_symbol to locate function/class definitions mentioned in the bug
4. Read the most promising files to confirm relevance
5. Identify the key lines of code that are likely involved

Output your findings as JSON:
```json
{
  "relevant_files": [
    {
      "path": "path/to/file.py",
      "confidence": 0.9,
      "reason": "Contains the connection pool logic mentioned in the bug",
      "key_lines": [42, 55, 78]
    }
  ],
  "code_context": "Brief summary of what the relevant code does"
}
```

Order files by confidence (highest first). Include 3-7 most relevant files."""

    def _build_initial_messages(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Present the issue analysis to the code locator."""
        issue_data = context.get("issue_data", {})
        issue_summary = json.dumps(issue_data, indent=2, default=str)
        return [
            {
                "role": "user",
                "content": f"Here is the bug report analysis. Please locate the relevant source code files in the repository.\n\nBug Report Analysis:\n{issue_summary}",
            }
        ]

    def _handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute file system and code analysis tool calls."""
        try:
            if tool_name == "search_files":
                result = self.fs.search_files(tool_input["pattern"])
                return json.dumps(result, indent=2)

            elif tool_name == "read_file":
                content = self.fs.read_file(tool_input["file_path"])
                if content is None:
                    return "File not found or unreadable"
                return content

            elif tool_name == "grep_content":
                result = self.fs.grep_content(
                    pattern=tool_input["pattern"],
                    file_pattern=tool_input.get("file_pattern", "*.py"),
                )
                return json.dumps(result, indent=2)

            elif tool_name == "get_file_structure":
                result = self.analyzer.get_file_structure(tool_input["file_path"])
                if result is None:
                    return "Failed to parse file (not a Python file or syntax error)"
                return json.dumps(result, indent=2)

            elif tool_name == "find_symbol":
                result = self.analyzer.find_symbol(tool_input["symbol_name"])
                return json.dumps(result, indent=2)

            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return f"Error: {e}"
