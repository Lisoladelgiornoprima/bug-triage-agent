"""Bug Reproducer Agent - generates and runs test code to reproduce bugs."""
import json
from typing import Any, Dict, List

from loguru import logger

from src.core.agent_base import BaseAgent
from src.tools.file_system import FileSystemTools
from src.tools.test_runner import TestRunner


class BugReproducer(BaseAgent):
    """Attempts to reproduce a bug by generating and running test code.

    Takes issue analysis + code locations as input.
    Generates minimal reproduction scripts and executes them.

    Tools: read_file, run_test_code, run_pytest
    Output: Reproduction result with test code and output
    """

    def __init__(self, client, repo_path: str, model: str = "claude-sonnet-4-6"):
        self.repo_path = repo_path
        self.fs = FileSystemTools(repo_path)
        self.runner = TestRunner(repo_path)
        super().__init__(name="BugReproducer", client=client, model=model)

    def _register_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "read_file",
                "description": "Read a file from the repository to understand the code before writing reproduction tests.",
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
                "name": "run_test_code",
                "description": "Execute a Python script to try reproducing the bug. The code will be run in a subprocess with a 30-second timeout. Write self-contained scripts that print results clearly.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute as a reproduction test",
                        },
                    },
                    "required": ["code"],
                },
            },
            {
                "name": "run_pytest",
                "description": "Run existing pytest tests. Optionally specify a test file or directory.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "test_path": {
                            "type": "string",
                            "description": "Specific test file/dir to run (empty for all tests)",
                        },
                    },
                    "required": [],
                },
            },
        ]

    def _build_system_prompt(self) -> str:
        return """You are an expert at reproducing software bugs. Given a bug analysis and relevant code locations, your job is to:

1. Read the relevant source files to understand the code
2. Write a minimal Python script that reproduces the bug
3. Run the script and observe the output
4. If the first attempt fails, iterate: adjust the script and try again (up to 3 attempts)

Guidelines for writing reproduction scripts:
- Keep scripts self-contained and minimal
- Add clear print statements showing expected vs actual behavior
- Use try/except to catch and display errors
- Include assertions where appropriate
- Handle imports properly (add sys.path if needed)

Output your findings as JSON:
```json
{
  "reproduced": true/false,
  "test_code": "the final reproduction script",
  "output": "stdout/stderr from running the script",
  "reproduction_steps": ["step 1", "step 2"],
  "notes": "any additional observations"
}
```

If you cannot reproduce the bug, explain why and still provide your best attempt."""

    def _build_initial_messages(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Present the issue analysis and code locations."""
        issue_data = context.get("issue_data", {})
        code_locations = context.get("code_locations", {})

        return [
            {
                "role": "user",
                "content": (
                    "Please try to reproduce this bug.\n\n"
                    f"Bug Analysis:\n{json.dumps(issue_data, indent=2, default=str)}\n\n"
                    f"Code Locations:\n{json.dumps(code_locations, indent=2, default=str)}"
                ),
            }
        ]

    def _handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute test runner and file system tool calls."""
        try:
            if tool_name == "read_file":
                content = self.fs.read_file(tool_input["file_path"])
                if content is None:
                    return "File not found or unreadable"
                return content

            elif tool_name == "run_test_code":
                result = self.runner.run_test_code(tool_input["code"])
                return json.dumps(result, indent=2)

            elif tool_name == "run_pytest":
                result = self.runner.run_pytest(
                    test_path=tool_input.get("test_path", "")
                )
                return json.dumps(result, indent=2)

            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return f"Error: {e}"
