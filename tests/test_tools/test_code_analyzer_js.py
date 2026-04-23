"""Tests for JSCodeAnalyzer."""
from src.tools.code_analyzer_js import JSCodeAnalyzer


def test_extract_classes(tmp_path):
    """Test extracting class definitions from JS."""
    js_file = tmp_path / "app.js"
    js_file.write_text(
        """
class UserService {
    constructor() {}

    async getUser(id) {
        return fetch(`/api/users/${id}`);
    }

    deleteUser(id) {
        return this.api.delete(id);
    }
}

class AdminService extends UserService {
    banUser(id) {
        console.log('banning', id);
    }
}
"""
    )

    analyzer = JSCodeAnalyzer(str(tmp_path))
    structure = analyzer.get_file_structure("app.js")

    assert structure is not None
    assert len(structure["classes"]) == 2
    assert structure["classes"][0]["name"] == "UserService"
    assert structure["classes"][1]["name"] == "AdminService"

    # Check methods
    user_methods = [m["name"] for m in structure["classes"][0]["methods"]]
    assert "getUser" in user_methods
    assert "deleteUser" in user_methods


def test_extract_functions(tmp_path):
    """Test extracting function definitions from JS."""
    js_file = tmp_path / "utils.js"
    js_file.write_text(
        """
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}

export function formatCurrency(amount) {
    return `$${amount.toFixed(2)}`;
}

const fetchData = async (url) => {
    const response = await fetch(url);
    return response.json();
};

const processItems = (items) => {
    return items.map(item => item.id);
};
"""
    )

    analyzer = JSCodeAnalyzer(str(tmp_path))
    structure = analyzer.get_file_structure("utils.js")

    assert structure is not None
    func_names = [f["name"] for f in structure["functions"]]
    assert "calculateTotal" in func_names
    assert "formatCurrency" in func_names
    assert "fetchData" in func_names
    assert "processItems" in func_names


def test_extract_imports(tmp_path):
    """Test extracting import statements."""
    ts_file = tmp_path / "app.ts"
    ts_file.write_text(
        """
import React from 'react';
import { useState, useEffect } from 'react';
import './styles.css';
const axios = require('axios');
"""
    )

    analyzer = JSCodeAnalyzer(str(tmp_path))
    structure = analyzer.get_file_structure("app.ts")

    assert structure is not None
    import_modules = [i["module"] for i in structure["imports"]]
    assert "react" in import_modules
    assert "./styles.css" in import_modules
    assert "axios" in import_modules


def test_find_symbol_in_js(tmp_path):
    """Test finding symbols across JS files."""
    (tmp_path / "service.js").write_text(
        """
class AuthService {
    login(user) {}
}
"""
    )
    (tmp_path / "utils.js").write_text(
        """
function login(credentials) {
    return AuthService.login(credentials);
}
"""
    )

    analyzer = JSCodeAnalyzer(str(tmp_path))
    results = analyzer.find_symbol("login")

    assert len(results) >= 2
    types = [r["type"] for r in results]
    assert "method" in types
    assert "function" in types


def test_typescript_support(tmp_path):
    """Test that TypeScript files are parsed."""
    ts_file = tmp_path / "types.ts"
    ts_file.write_text(
        """
interface User {
    id: number;
    name: string;
}

class UserRepository {
    async findById(id: number): Promise<User> {
        return fetch(`/users/${id}`).then(r => r.json());
    }
}

export function createUser(data: Partial<User>): User {
    return { id: Date.now(), ...data };
}
"""
    )

    analyzer = JSCodeAnalyzer(str(tmp_path))
    structure = analyzer.get_file_structure("types.ts")

    assert structure is not None
    assert len(structure["classes"]) == 1
    assert structure["classes"][0]["name"] == "UserRepository"
    func_names = [f["name"] for f in structure["functions"]]
    assert "createUser" in func_names
