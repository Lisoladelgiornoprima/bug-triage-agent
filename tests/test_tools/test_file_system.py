"""Tests for FileSystemTools."""
from src.tools.file_system import FileSystemTools


def test_search_files_finds_python_files(sample_repo):
    """Test that search_files finds Python files."""
    fs = FileSystemTools(str(sample_repo))
    results = fs.search_files("*.py")

    assert len(results) > 0
    assert any("calculator.py" in r for r in results)
    assert any("buggy.py" in r for r in results)


def test_search_files_with_pattern(sample_repo):
    """Test search with specific pattern."""
    fs = FileSystemTools(str(sample_repo))
    results = fs.search_files("**/test_*.py")

    assert len(results) >= 1
    assert any("test_calculator.py" in r for r in results)


def test_read_file_returns_content(sample_repo):
    """Test that read_file returns file contents."""
    fs = FileSystemTools(str(sample_repo))
    content = fs.read_file("src/calculator.py")

    assert content is not None
    assert "class Calculator" in content
    assert "def add" in content


def test_read_file_nonexistent_returns_none(sample_repo):
    """Test that reading nonexistent file returns None."""
    fs = FileSystemTools(str(sample_repo))
    content = fs.read_file("nonexistent.py")

    assert content is None


def test_grep_content_finds_matches(sample_repo):
    """Test that grep finds pattern matches."""
    fs = FileSystemTools(str(sample_repo))
    results = fs.grep_content("Calculator", file_pattern="*.py")

    assert len(results) > 0
    assert any("calculator.py" in r["file"] for r in results)


def test_grep_content_with_regex(sample_repo):
    """Test grep with regex pattern."""
    fs = FileSystemTools(str(sample_repo))
    results = fs.grep_content(r"def \w+\(", file_pattern="*.py")

    assert len(results) > 0
    # Should find function definitions
    assert any("def add" in r["line_content"] or "def divide" in r["line_content"] for r in results)
