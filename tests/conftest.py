"""Shared test fixtures."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def sample_repo(tmp_path):
    """Create a minimal sample Python repo for testing."""
    # Create a simple Python project structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text("")

    # A sample Python file with classes and functions
    (src_dir / "calculator.py").write_text(
        '''"""A simple calculator module."""
import math


class Calculator:
    """Basic calculator class."""

    def add(self, a: int, b: int) -> int:
        return a + b

    def divide(self, a: int, b: int) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b


def factorial(n: int) -> int:
    """Calculate factorial."""
    if n < 0:
        raise ValueError("Negative numbers not allowed")
    return math.factorial(n)
'''
    )

    # A file with a known bug
    (src_dir / "buggy.py").write_text(
        '''"""Module with a known bug for testing."""


def process_items(items):
    """Process a list of items. Bug: crashes on empty list."""
    total = sum(items) / len(items)  # ZeroDivisionError on empty list
    return total
'''
    )

    # A test file
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_calculator.py").write_text(
        '''from src.calculator import Calculator

def test_add():
    calc = Calculator()
    assert calc.add(1, 2) == 3
'''
    )

    # A JavaScript file for multi-language testing
    (src_dir / "helpers.js").write_text(
        '''import { format } from 'date-fns';

class Formatter {
    formatDate(date) {
        return format(date, 'yyyy-MM-dd');
    }
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

module.exports = { Formatter, capitalize };
'''
    )

    return tmp_path


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_issue_data():
    """Sample issue analysis result for testing."""
    return {
        "title": "ZeroDivisionError in process_items",
        "bug_type": "crash",
        "severity": "major",
        "error_messages": ["ZeroDivisionError: division by zero"],
        "stack_trace": "File 'src/buggy.py', line 6, in process_items\n    total = sum(items) / len(items)",
        "steps_to_reproduce": ["Call process_items with an empty list"],
        "affected_components": ["process_items"],
        "environment": {},
        "related_files_hint": ["src/buggy.py"],
    }
