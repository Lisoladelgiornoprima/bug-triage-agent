"""Code analysis tools using Python AST for structure extraction."""
import ast
from pathlib import Path
from typing import Any

from loguru import logger

from src.tools.code_analyzer_js import JSCodeAnalyzer


class CodeAnalyzer:
    """Analyzes source code using language-specific parsers.

    Supports:
    - Python: AST-based analysis
    - JavaScript/TypeScript: Regex-based analysis
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.js_analyzer = JSCodeAnalyzer(repo_path)

    def _parse_python_file(self, file_path: str) -> ast.Module | None:
        """Parse a Python file into an AST."""
        full_path = self.repo_path / file_path
        if not full_path.exists() or not full_path.suffix == ".py":
            return None
        try:
            source = full_path.read_text(encoding="utf-8", errors="ignore")
            return ast.parse(source, filename=file_path)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return None

    def get_file_structure(self, file_path: str) -> dict[str, Any] | None:
        """Extract the structure of a source file.

        Automatically detects language and uses appropriate parser.

        Returns:
            Dict with classes, functions, imports, and their line numbers
        """
        full_path = self.repo_path / file_path
        if not full_path.exists():
            return None

        # Route to appropriate analyzer
        suffix = full_path.suffix
        if suffix == ".py":
            return self._get_python_structure(file_path)
        elif suffix in {".js", ".ts", ".jsx", ".tsx"}:
            return self.js_analyzer.get_file_structure(file_path)
        else:
            logger.warning(f"Unsupported file type: {suffix}")
            return None

    def _get_python_structure(self, file_path: str) -> dict[str, Any] | None:
        """Extract structure from a Python file using AST."""
        tree = self._parse_python_file(file_path)
        if tree is None:
            return None

        structure = {
            "file": file_path,
            "classes": [],
            "functions": [],
            "imports": [],
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    {"name": n.name, "line": n.lineno}
                    for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                structure["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                })

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not methods inside classes)
                if not any(
                    isinstance(parent, ast.ClassDef)
                    for parent in ast.walk(tree)
                    if hasattr(parent, 'body') and node in getattr(parent, 'body', [])
                ):
                    structure["functions"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                    })

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    structure["imports"].append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    structure["imports"].append({
                        "module": f"{module}.{alias.name}",
                        "alias": alias.asname,
                        "line": node.lineno,
                    })

        return structure

    def find_symbol(self, symbol_name: str, file_pattern: str = "*.py") -> list[dict[str, Any]]:
        """Find where a symbol (function/class) is defined across the repo.

        Searches Python, JavaScript, and TypeScript files.

        Args:
            symbol_name: Name of the function or class to find
            file_pattern: Glob pattern for files to search

        Returns:
            List of {file, name, type, line}
        """
        from src.tools.file_system import FileSystemTools

        fs = FileSystemTools(str(self.repo_path))

        # Search Python files
        py_files = fs.search_files(file_pattern, max_results=200)
        results = []

        for fp in py_files:
            structure = self.get_file_structure(fp)
            if not structure:
                continue
            results.extend(self._match_symbol(structure, symbol_name, fp))

        # Also search JS/TS files
        for ext in ["*.js", "*.ts", "*.jsx", "*.tsx"]:
            for fp in fs.search_files(ext, max_results=100):
                structure = self.js_analyzer.get_file_structure(fp)
                if not structure:
                    continue
                results.extend(self._match_symbol(structure, symbol_name, fp))

        logger.debug(f"Found {len(results)} definitions for '{symbol_name}'")
        return results

    @staticmethod
    def _match_symbol(structure: dict, symbol_name: str, file_path: str) -> list[dict[str, Any]]:
        """Match a symbol name against a file structure."""
        results = []
        for cls in structure.get("classes", []):
            if symbol_name.lower() in cls["name"].lower():
                results.append({
                    "file": file_path,
                    "name": cls["name"],
                    "type": "class",
                    "line": cls["line"],
                })
            for method in cls.get("methods", []):
                if symbol_name.lower() in method["name"].lower():
                    results.append({
                        "file": file_path,
                        "name": f"{cls['name']}.{method['name']}",
                        "type": "method",
                        "line": method["line"],
                    })

        for func in structure.get("functions", []):
            if symbol_name.lower() in func["name"].lower():
                results.append({
                    "file": file_path,
                    "name": func["name"],
                    "type": "function",
                    "line": func["line"],
                })
        return results
