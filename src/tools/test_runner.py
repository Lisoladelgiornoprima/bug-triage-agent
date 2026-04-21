"""Test runner tool for executing code in a sandboxed subprocess."""
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

from loguru import logger


class TestRunner:
    """Executes test code in a subprocess with timeout and resource limits."""

    def __init__(self, repo_path: str, python_path: Optional[str] = None):
        self.repo_path = Path(repo_path).resolve()
        self.python_path = python_path or "python"

    def run_test_code(
        self, code: str, timeout: int = 30, filename: str = "test_reproduce.py"
    ) -> Dict[str, any]:
        """Write test code to a temp file and execute it.

        Args:
            code: Python test code to execute
            timeout: Max execution time in seconds
            filename: Name for the temp test file

        Returns:
            Dict with {success, stdout, stderr, return_code, timed_out}
        """
        # Write code to a temp file inside the repo
        test_file = self.repo_path / filename
        try:
            test_file.write_text(code, encoding="utf-8")
            logger.info(f"Running test: {test_file}")

            result = subprocess.run(
                [self.python_path, str(test_file)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.repo_path),
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:5000],  # Limit output size
                "stderr": result.stderr[:5000],
                "return_code": result.returncode,
                "timed_out": False,
            }

        except subprocess.TimeoutExpired:
            logger.warning(f"Test timed out after {timeout}s")
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Test timed out after {timeout} seconds",
                "return_code": -1,
                "timed_out": True,
            }
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "timed_out": False,
            }
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()

    def run_pytest(self, test_path: str = "", timeout: int = 60) -> Dict[str, any]:
        """Run pytest on the repository or a specific test file.

        Args:
            test_path: Specific test file/dir (empty = run all)
            timeout: Max execution time in seconds

        Returns:
            Dict with {success, stdout, stderr, return_code, timed_out}
        """
        cmd = [self.python_path, "-m", "pytest", "-x", "-v", "--tb=short"]
        if test_path:
            cmd.append(test_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.repo_path),
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:5000],
                "return_code": result.returncode,
                "timed_out": False,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Pytest timed out after {timeout} seconds",
                "return_code": -1,
                "timed_out": True,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "timed_out": False,
            }
