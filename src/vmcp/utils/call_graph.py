"""Call graph analysis for MCP tools.

Builds a dependency graph showing which files and functions each tool calls.
This enables accurate vulnerability-to-tool mapping based on actual code paths.
"""
import ast
from pathlib import Path
from typing import Any

from vmcp.utils.tool_detector import MCPTool


class CallGraphBuilder:
    """Builds call graphs for MCP tools to track dependencies."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.tool_graphs: dict[str, set[str]] = {}

    def build_graphs(self, tools: list[MCPTool]) -> dict[str, set[str]]:
        """
        Build call graphs for all tools.

        Returns:
            Map of tool_name -> set of file paths the tool depends on
        """
        for tool in tools:
            self.tool_graphs[tool.name] = self._build_tool_graph(tool)

        return self.tool_graphs

    def _build_tool_graph(self, tool: MCPTool) -> set[str]:
        """
        Build dependency graph for a single tool.

        Traces:
        1. Direct imports in the tool's file
        2. Function calls within the tool function
        3. Transitive imports (imports from imported files)

        Returns:
            Set of file paths (relative to repo root) that the tool depends on
        """
        dependencies = set()
        tool_file_path = self.repo_path / tool.file_path

        # Always include the tool's own file
        dependencies.add(tool.file_path)

        if not tool_file_path.exists():
            return dependencies

        # Language-specific graph building
        if tool.language == 'python':
            dependencies.update(self._build_python_graph(tool_file_path, tool.file_path))
        elif tool.language in ['typescript', 'javascript']:
            dependencies.update(self._build_javascript_graph(tool_file_path, tool.file_path))

        return dependencies

    def _build_python_graph(self, file_path: Path, relative_path: str, visited: set[str] | None = None) -> set[str]:
        """
        Build dependency graph for Python file.

        Args:
            file_path: Absolute path to Python file
            relative_path: Path relative to repo root
            visited: Set of already-visited files (to prevent cycles)

        Returns:
            Set of file paths this file depends on
        """
        if visited is None:
            visited = set()

        # Prevent circular imports
        if relative_path in visited:
            return set()
        visited.add(relative_path)

        dependencies = set()

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)

            # Extract imports
            for node in ast.walk(tree):
                imports = []

                # Handle: import foo, import foo.bar
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)

                # Handle: from foo import bar
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

                # Resolve imports to file paths
                for import_name in imports:
                    resolved_paths = self._resolve_python_import(import_name, file_path.parent)
                    for resolved_path in resolved_paths:
                        if resolved_path:
                            dependencies.add(resolved_path)

                            # Recursively analyze imported files (transitive dependencies)
                            absolute_resolved = self.repo_path / resolved_path
                            if absolute_resolved.exists() and absolute_resolved.suffix == '.py':
                                transitive_deps = self._build_python_graph(
                                    absolute_resolved,
                                    resolved_path,
                                    visited
                                )
                                dependencies.update(transitive_deps)

        except Exception as e:
            # If parsing fails, just return what we have
            pass

        return dependencies

    def _resolve_python_import(self, import_name: str, current_dir: Path) -> list[str]:
        """
        Resolve Python import to file paths.

        Args:
            import_name: e.g., "utils", "cyberchef_api_mcp_server.api_client"
            current_dir: Directory of the file doing the import

        Returns:
            List of possible file paths (relative to repo root)
        """
        paths = []

        # Convert import name to file path
        # e.g., "utils" -> "utils.py"
        # e.g., "cyberchef_api_mcp_server.api_client" -> "cyberchef_api_mcp_server/api_client.py"
        parts = import_name.split('.')

        # Try as direct module file
        module_path = Path(*parts).with_suffix('.py')
        module_file = self.repo_path / module_path
        if module_file.exists():
            paths.append(str(module_file.relative_to(self.repo_path)))

        # Try as package (__init__.py)
        package_path = Path(*parts) / '__init__.py'
        package_init = self.repo_path / package_path
        if package_init.exists():
            paths.append(str(package_init.relative_to(self.repo_path)))

        # Try relative to current directory
        relative_file = current_dir / f"{parts[-1]}.py"
        if relative_file.exists() and self.repo_path in relative_file.parents:
            paths.append(str(relative_file.relative_to(self.repo_path)))

        return paths

    def _build_javascript_graph(self, file_path: Path, relative_path: str, visited: set[str] | None = None) -> set[str]:
        """
        Build dependency graph for JavaScript/TypeScript file.

        Uses simple regex matching for imports (not full AST parsing).

        Args:
            file_path: Absolute path to JS/TS file
            relative_path: Path relative to repo root
            visited: Set of already-visited files

        Returns:
            Set of file paths this file depends on
        """
        if visited is None:
            visited = set()

        if relative_path in visited:
            return set()
        visited.add(relative_path)

        dependencies = set()

        try:
            import re

            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # Match: import ... from '...'
            # Match: require('...')
            import_patterns = [
                r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
                r"require\(['\"]([^'\"]+)['\"]\)",
            ]

            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    import_path = match.group(1)

                    # Resolve relative imports
                    if import_path.startswith('.'):
                        resolved_paths = self._resolve_javascript_import(import_path, file_path.parent)
                        for resolved_path in resolved_paths:
                            if resolved_path:
                                dependencies.add(resolved_path)

                                # Recursively analyze
                                absolute_resolved = self.repo_path / resolved_path
                                if absolute_resolved.exists() and absolute_resolved.suffix in ['.js', '.ts', '.jsx', '.tsx']:
                                    transitive_deps = self._build_javascript_graph(
                                        absolute_resolved,
                                        resolved_path,
                                        visited
                                    )
                                    dependencies.update(transitive_deps)

        except Exception:
            pass

        return dependencies

    def _resolve_javascript_import(self, import_path: str, current_dir: Path) -> list[str]:
        """
        Resolve JavaScript/TypeScript import to file paths.

        Args:
            import_path: e.g., "./utils", "../api/client"
            current_dir: Directory of the file doing the import

        Returns:
            List of possible file paths (relative to repo root)
        """
        paths = []

        # Resolve relative path
        resolved = (current_dir / import_path).resolve()

        # Try with common extensions
        extensions = ['.ts', '.tsx', '.js', '.jsx', '']
        for ext in extensions:
            file_with_ext = Path(str(resolved) + ext) if ext else resolved

            if file_with_ext.exists() and self.repo_path in file_with_ext.parents:
                paths.append(str(file_with_ext.relative_to(self.repo_path)))
                break

            # Try as index file
            index_file = file_with_ext / f'index{ext}' if not ext else file_with_ext.parent / file_with_ext.name / 'index' + ext
            if index_file.exists() and self.repo_path in index_file.parents:
                paths.append(str(index_file.relative_to(self.repo_path)))
                break

        return paths


def build_tool_call_graphs(tools: list[MCPTool], repo_path: str) -> dict[str, set[str]]:
    """
    Convenience function to build call graphs for all tools.

    Args:
        tools: List of detected MCP tools
        repo_path: Path to repository

    Returns:
        Map of tool_name -> set of file paths the tool depends on
    """
    builder = CallGraphBuilder(Path(repo_path))
    return builder.build_graphs(tools)
