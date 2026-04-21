"""Tests for CodeAnalyzer."""
from src.tools.code_analyzer import CodeAnalyzer


def test_get_file_structure_extracts_classes(sample_repo):
    """Test that file structure extraction finds classes."""
    analyzer = CodeAnalyzer(str(sample_repo))
    structure = analyzer.get_file_structure("src/calculator.py")

    assert structure is not None
    assert len(structure["classes"]) == 1
    assert structure["classes"][0]["name"] == "Calculator"


def test_get_file_structure_extracts_methods(sample_repo):
    """Test that methods within classes are found."""
    analyzer = CodeAnalyzer(str(sample_repo))
    structure = analyzer.get_file_structure("src/calculator.py")

    methods = structure["classes"][0]["methods"]
    method_names = [m["name"] for m in methods]
    assert "add" in method_names
    assert "divide" in method_names


def test_get_file_structure_extracts_functions(sample_repo):
    """Test that top-level functions are found."""
    analyzer = CodeAnalyzer(str(sample_repo))
    structure = analyzer.get_file_structure("src/calculator.py")

    func_names = [f["name"] for f in structure["functions"]]
    assert "factorial" in func_names


def test_get_file_structure_extracts_imports(sample_repo):
    """Test that imports are found."""
    analyzer = CodeAnalyzer(str(sample_repo))
    structure = analyzer.get_file_structure("src/calculator.py")

    import_modules = [i["module"] for i in structure["imports"]]
    assert "math" in import_modules


def test_get_file_structure_nonexistent_returns_none(sample_repo):
    """Test that nonexistent file returns None."""
    analyzer = CodeAnalyzer(str(sample_repo))
    result = analyzer.get_file_structure("nonexistent.py")

    assert result is None


def test_find_symbol_finds_class(sample_repo):
    """Test that find_symbol locates a class definition."""
    analyzer = CodeAnalyzer(str(sample_repo))
    results = analyzer.find_symbol("Calculator")

    assert len(results) > 0
    assert any(r["name"] == "Calculator" and r["type"] == "class" for r in results)


def test_find_symbol_finds_function(sample_repo):
    """Test that find_symbol locates a function definition."""
    analyzer = CodeAnalyzer(str(sample_repo))
    results = analyzer.find_symbol("factorial")

    assert len(results) > 0
    assert any(r["name"] == "factorial" and r["type"] == "function" for r in results)


def test_find_symbol_finds_method(sample_repo):
    """Test that find_symbol locates a method definition."""
    analyzer = CodeAnalyzer(str(sample_repo))
    results = analyzer.find_symbol("divide")

    assert len(results) > 0
    assert any(r["type"] == "method" for r in results)
