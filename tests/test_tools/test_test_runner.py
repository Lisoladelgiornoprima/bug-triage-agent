"""Tests for TestRunner."""
from src.tools.test_runner import TestRunner


def test_run_test_code_success(sample_repo):
    """Test running a simple passing script."""
    runner = TestRunner(str(sample_repo))
    result = runner.run_test_code("print('hello')")

    assert result["success"] is True
    assert "hello" in result["stdout"]
    assert result["timed_out"] is False


def test_run_test_code_failure(sample_repo):
    """Test running a script that raises an error."""
    runner = TestRunner(str(sample_repo))
    result = runner.run_test_code("raise ValueError('test error')")

    assert result["success"] is False
    assert "ValueError" in result["stderr"]


def test_run_test_code_timeout(sample_repo):
    """Test that long-running scripts are killed."""
    runner = TestRunner(str(sample_repo))
    result = runner.run_test_code("import time; time.sleep(60)", timeout=2)

    assert result["success"] is False
    assert result["timed_out"] is True


def test_run_test_code_cleans_up(sample_repo):
    """Test that temp test file is cleaned up after execution."""
    runner = TestRunner(str(sample_repo))
    runner.run_test_code("print('cleanup test')")

    test_file = sample_repo / "test_reproduce.py"
    assert not test_file.exists()
