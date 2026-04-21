"""File system tools for code search and navigation."""
import fnmatch
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


class FileSystemTools:
    """Provides file search, read, and grep operations on a local repository."""

    # Directories to always skip
    SKIP_DIRS = {
        ".git", "__pycache__", "node_modules", ".tox", ".mypy_cache",
        ".pytest_cache", "venv", ".venv", "env", ".env", "dist", "build",
        ".eggs", "*.egg-info",
    }

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.is_dir():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")
        logger.info(f"FileSystemTools initialized at: {self.repo_path}")

    def _should_skip(self, dir_name: str) -> bool:
        """Check if a directory should be skipped."""
        return dir_name in self.SKIP_DIRS or dir_name.startswith(".")

    def search_files(self, pattern: str, max_results: int = 50) -> List[str]:
        """Search for files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g. "*.py", "**/*test*.py")
            max_results: Maximum number of results

        Returns:
            List of relative file paths
        """
        results = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not self._should_skip(d)]
            for f in files:
                full_path = Path(root) / f
                rel_path = str(full_path.relative_to(self.repo_path))
                if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(f, pattern):
                    results.append(rel_path)
                    if len(results) >= max_results:
                        return results
        return results

    def read_file(self, file_path: str, max_lines: int = 500) -> Optional[str]:
        """Read file contents.

        Args:
            file_path: Relative path from repo root
            max_lines: Max lines to read (prevent huge files)

        Returns:
            File contents or None if error
        """
        full_path = self.repo_path / file_path
        if not full_path.is_file():
            logger.warning(f"File not found: {file_path}")
            return None

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"\n... (truncated at {max_lines} lines)")
                        break
                    lines.append(line)
                return "".join(lines)
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return None

    def grep_content(
        self, pattern: str, file_pattern: str = "*.py", max_results: int = 20
    ) -> List[Dict[str, any]]:
        """Search for regex pattern in file contents.

        Args:
            pattern: Regex pattern to search
            file_pattern: Glob pattern for files to search in
            max_results: Max matches to return

        Returns:
            List of {file, line_number, line_content}
        """
        results = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            files = self.search_files(file_pattern, max_results=100)

            for file_path in files:
                if len(results) >= max_results:
                    break

                content = self.read_file(file_path, max_lines=1000)
                if not content:
                    continue

                for line_num, line in enumerate(content.split("\n"), 1):
                    if regex.search(line):
                        results.append({
                            "file": file_path,
                            "line_number": line_num,
                            "line_content": line.strip(),
                        })
                        if len(results) >= max_results:
                            break

            logger.debug(f"Grep found {len(results)} matches for '{pattern}'")
            return results
        except Exception as e:
            logger.error(f"Grep failed: {e}")
            return []
