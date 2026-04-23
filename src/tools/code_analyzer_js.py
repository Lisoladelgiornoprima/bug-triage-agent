"""JavaScript/TypeScript code analyzer using regex patterns."""
import re
from pathlib import Path
from typing import Any

from loguru import logger


class JSCodeAnalyzer:
    """Analyzes JavaScript/TypeScript code using regex patterns.

    Provides basic structure extraction without external dependencies.
    For production use, consider using esprima or @babel/parser.
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()

    def get_file_structure(self, file_path: str) -> dict[str, Any] | None:
        """Extract structure from a JS/TS file.

        Returns:
            Dict with classes, functions, imports
        """
        full_path = self.repo_path / file_path
        if not full_path.exists() or full_path.suffix not in {".js", ".ts", ".jsx", ".tsx"}:
            return None

        try:
            source = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return None

        structure = {
            "file": file_path,
            "classes": self._extract_classes(source),
            "functions": self._extract_functions(source),
            "imports": self._extract_imports(source),
        }

        return structure

    def _extract_classes(self, source: str) -> list[dict[str, Any]]:
        """Extract class definitions."""
        classes = []
        # Match: class ClassName { ... }
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{"
        for match in re.finditer(class_pattern, source):
            line_num = source[:match.start()].count("\n") + 1
            class_name = match.group(1)

            # Extract methods within this class (simplified)
            methods = self._extract_methods_in_class(source, match.start())

            classes.append({
                "name": class_name,
                "line": line_num,
                "methods": methods,
            })

        return classes

    def _extract_methods_in_class(self, source: str, class_start: int) -> list[dict[str, Any]]:
        """Extract methods from a class body."""
        methods = []
        # Find the class body (simplified: find matching braces)
        brace_count = 0
        class_body_start = source.find("{", class_start)
        if class_body_start == -1:
            return methods

        class_body_end = class_body_start
        for i in range(class_body_start, len(source)):
            if source[i] == "{":
                brace_count += 1
            elif source[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    class_body_end = i
                    break

        class_body = source[class_body_start:class_body_end]

        # Match method definitions: methodName(...) { or async methodName(...) {
        method_pattern = r"(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{"
        for match in re.finditer(method_pattern, class_body):
            method_name = match.group(1)
            # Skip constructor and common keywords
            if method_name in {"if", "for", "while", "switch", "catch"}:
                continue
            line_num = source[:class_body_start + match.start()].count("\n") + 1
            methods.append({"name": method_name, "line": line_num})

        return methods

    def _extract_functions(self, source: str) -> list[dict[str, Any]]:
        """Extract top-level function definitions."""
        functions = []

        # Match function declarations (including TS return type annotations)
        patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)[^{]*\{",  # function declarations
            r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)[^=]*=>\s*\{",  # arrow functions
            r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*function\s*\([^)]*\)[^{]*\{",  # function expressions
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, source):
                func_name = match.group(1)
                line_num = source[:match.start()].count("\n") + 1
                functions.append({"name": func_name, "line": line_num})

        return functions

    def _extract_imports(self, source: str) -> list[dict[str, Any]]:
        """Extract import statements."""
        imports = []

        # Match: import ... from 'module' or import 'module' or require('module')
        import_patterns = [
            r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",  # ES6 imports
            r"import\s+['\"]([^'\"]+)['\"]",  # Side-effect imports
            r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",  # CommonJS require
        ]

        for pattern in import_patterns:
            for match in re.finditer(pattern, source):
                module = match.group(1)
                line_num = source[:match.start()].count("\n") + 1
                imports.append({
                    "module": module,
                    "line": line_num,
                })

        return imports

    def find_symbol(self, symbol_name: str, file_pattern: str = "*.{js,ts,jsx,tsx}") -> list[dict[str, Any]]:
        """Find where a symbol is defined across JS/TS files.

        Args:
            symbol_name: Name of the function or class to find
            file_pattern: Glob pattern for files to search

        Returns:
            List of {file, name, type, line}
        """
        from src.tools.file_system import FileSystemTools

        fs = FileSystemTools(str(self.repo_path))
        # Expand pattern to match multiple extensions
        patterns = ["*.js", "*.ts", "*.jsx", "*.tsx"]
        files = []
        for pat in patterns:
            files.extend(fs.search_files(pat, max_results=200))

        results = []
        for file_path in files:
            structure = self.get_file_structure(file_path)
            if not structure:
                continue

            # Search in classes
            for cls in structure["classes"]:
                if symbol_name.lower() in cls["name"].lower():
                    results.append({
                        "file": file_path,
                        "name": cls["name"],
                        "type": "class",
                        "line": cls["line"],
                    })
                # Search in methods
                for method in cls["methods"]:
                    if symbol_name.lower() in method["name"].lower():
                        results.append({
                            "file": file_path,
                            "name": f"{cls['name']}.{method['name']}",
                            "type": "method",
                            "line": method["line"],
                        })

            # Search in functions
            for func in structure["functions"]:
                if symbol_name.lower() in func["name"].lower():
                    results.append({
                        "file": file_path,
                        "name": func["name"],
                        "type": "function",
                        "line": func["line"],
                    })

        logger.debug(f"Found {len(results)} JS/TS definitions for '{symbol_name}'")
        return results
