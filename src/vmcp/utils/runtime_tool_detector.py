"""Runtime MCP Tool Detection using stdio transport.

Discovers tools by actually running the MCP server and querying tools/list.
More accurate than static analysis, but requires code execution.
"""
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from vmcp.utils.tool_detector import MCPTool


class RuntimeToolDetector:
    """Detects MCP tools by running the server and querying tools/list."""

    def __init__(self, repo_path: str, timeout: int = 30):
        self.repo_path = Path(repo_path)
        self.timeout = timeout
        self.tools: list[MCPTool] = []

    async def detect_tools(self) -> list[MCPTool]:
        """
        Detect tools by running the MCP server with stdio transport.

        Returns:
            List of MCPTool objects discovered from runtime
        """
        # Find server entry point
        entry_point = self._find_entry_point()
        if not entry_point:
            print("⚠️  Could not find MCP server entry point")
            return []

        # Determine command to run server
        command = self._get_server_command(entry_point)
        if not command:
            print("⚠️  Could not determine server command")
            return []

        print(f"🔍 Running MCP server: {' '.join(command)}")

        try:
            # Run server and query tools
            tools_list = await self._query_tools(command)

            if not tools_list:
                print("⚠️  No tools returned from server")
                return []

            # Convert to MCPTool objects
            self.tools = self._parse_tools_response(tools_list, entry_point)
            print(f"✅ Discovered {len(self.tools)} tools via runtime detection")

            return self.tools

        except asyncio.TimeoutError:
            print(f"⏱️  Server startup timed out after {self.timeout}s")
            return []
        except Exception as e:
            print(f"❌ Runtime detection failed: {e}")
            return []

    def _find_entry_point(self) -> Path | None:
        """Find the main MCP server entry point."""
        # Common patterns for MCP server entry points
        candidates = [
            # Python FastMCP patterns
            'server.py',
            'main.py',
            '__main__.py',
            'src/server.py',
            'src/main.py',
            'src/__main__.py',
            'src/**/server.py',
            'src/**/main.py',
            '**/server.py',
            '**/main.py',
            '**/__main__.py',
            # TypeScript patterns
            'index.ts',
            'server.ts',
            'src/index.ts',
            'src/server.ts',
            # Package.json bin entries
            'package.json',
        ]

        for pattern in candidates:
            matches = list(self.repo_path.glob(pattern))
            if matches:
                # Check if file contains MCP server initialization
                for match in matches:
                    if self._is_mcp_entry_point(match):
                        return match

        return None

    def _is_mcp_entry_point(self, file_path: Path) -> bool:
        """Check if file is likely an MCP server entry point."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # Python patterns
            if file_path.suffix == '.py':
                if any(pattern in content for pattern in [
                    'mcp.run()',
                    'FastMCP(',
                    'Server(',
                    'from mcp import',
                    'from fastmcp import',
                    'import mcp',
                    'import fastmcp',
                ]):
                    return True

            # TypeScript patterns
            elif file_path.suffix in ['.ts', '.js']:
                if any(pattern in content for pattern in [
                    '@modelcontextprotocol/sdk',
                    'new Server(',
                    'StdioServerTransport',
                ]):
                    return True

            # package.json
            elif file_path.name == 'package.json':
                try:
                    data = json.loads(content)
                    # Check for bin entry or start script
                    if 'bin' in data or ('scripts' in data and 'start' in data.get('scripts', {})):
                        return True
                except json.JSONDecodeError:
                    pass

        except Exception:
            pass

        return False

    def _get_server_command(self, entry_point: Path) -> list[str] | None:
        """Determine command to run the MCP server."""
        # Python servers
        if entry_point.suffix == '.py':
            # Check for pyproject.toml with script entry point
            pyproject_file = self.repo_path / 'pyproject.toml'
            if pyproject_file.exists():
                try:
                    import tomllib
                    content = pyproject_file.read_text()
                    config = tomllib.loads(content)

                    # Check for [project.scripts] entry point
                    scripts = config.get('project', {}).get('scripts', {})
                    if scripts:
                        # Use first script entry point
                        script_name = next(iter(scripts.keys()))
                        print(f"  Found script entry: {script_name}")
                        # Install package first, then run script
                        return ['sh', '-c', f'cd {self.repo_path} && uv pip install -e . --quiet && uv run {script_name}']
                except Exception:
                    pass

                # Fall back to direct python execution with uv
                return ['uv', 'run', 'python', str(entry_point)]

            # Fall back to python
            return ['python', str(entry_point)]

        # TypeScript/JavaScript servers
        elif entry_point.suffix in ['.ts', '.js']:
            # Check package.json for start command
            package_json = self.repo_path / 'package.json'
            if package_json.exists():
                try:
                    data = json.loads(package_json.read_text())
                    # Use npm start if available
                    if 'scripts' in data and 'start' in data['scripts']:
                        return ['npm', 'start']
                    # Use bin entry if available
                    if 'bin' in data:
                        bin_entry = data['bin']
                        if isinstance(bin_entry, str):
                            return ['node', bin_entry]
                        elif isinstance(bin_entry, dict):
                            # Use first bin entry
                            first_bin = next(iter(bin_entry.values()))
                            return ['node', first_bin]
                except Exception:
                    pass

            # Fall back to direct execution
            if entry_point.suffix == '.ts':
                return ['npx', 'tsx', str(entry_point)]
            else:
                return ['node', str(entry_point)]

        return None

    async def _query_tools(self, command: list[str]) -> list[dict[str, Any]] | None:
        """
        Run MCP server and query tools/list via stdio transport.

        Returns:
            List of tool definitions from server
        """
        try:
            # Start server process
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.repo_path),
            )

            # MCP protocol requires initialization handshake first
            # 1. Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "vmcp-tool-detector",
                        "version": "1.0.0"
                    }
                }
            }

            # 2. Send tools/list request
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            # Send both requests
            requests = json.dumps(init_request) + '\n' + json.dumps(tools_request) + '\n'

            # Send requests and wait for responses
            try:
                process.stdin.write(requests.encode())
                await process.stdin.drain()

                # Read responses with timeout
                stdout_data = await asyncio.wait_for(
                    process.stdout.read(1024 * 100),  # Read up to 100KB
                    timeout=self.timeout
                )

                # Close process
                process.stdin.close()
                try:
                    await asyncio.wait_for(process.wait(), timeout=2)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise

            # Parse responses
            if stdout_data:
                # MCP servers send JSON-RPC responses line by line
                for line in stdout_data.decode('utf-8', errors='ignore').strip().split('\n'):
                    if not line:
                        continue
                    try:
                        response = json.loads(line)
                        # Check if this is the tools/list response
                        if response.get('id') == 2 and 'result' in response:
                            tools = response['result'].get('tools', [])
                            if tools:
                                return tools
                    except json.JSONDecodeError:
                        continue

            return None

        except Exception as e:
            print(f"  Error querying server: {e}")
            return None

    def _parse_tools_response(self, tools_list: list[dict[str, Any]], entry_point: Path) -> list[MCPTool]:
        """Convert MCP tools/list response to MCPTool objects."""
        parsed_tools = []

        for tool_def in tools_list:
            name = tool_def.get('name', 'unknown')
            description = tool_def.get('description', '')

            # Try to find the function definition in source code
            file_path, line_number = self._find_tool_in_source(name, entry_point)

            # Detect language from entry point
            language = 'unknown'
            if entry_point.suffix == '.py':
                language = 'python'
            elif entry_point.suffix in ['.ts', '.tsx']:
                language = 'typescript'
            elif entry_point.suffix in ['.js', '.jsx']:
                language = 'javascript'

            parsed_tools.append(MCPTool(
                name=name,
                file_path=file_path,
                description=description,
                line_number=line_number,
                language=language
            ))

        return parsed_tools

    def _find_tool_in_source(self, tool_name: str, entry_point: Path) -> tuple[str, int]:
        """
        Find where a tool is defined in source code.

        Returns:
            (relative_file_path, line_number)
        """
        # Search in entry point and nearby files
        search_files = [entry_point]

        # Add files in same directory
        if entry_point.parent != self.repo_path:
            search_files.extend(entry_point.parent.glob(f'*{entry_point.suffix}'))

        for file_path in search_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                # Look for function definition
                for i, line in enumerate(lines, 1):
                    if f'def {tool_name}(' in line or f'async def {tool_name}(' in line:
                        relative_path = str(file_path.relative_to(self.repo_path))
                        return relative_path, i
                    elif f'function {tool_name}(' in line or f'async function {tool_name}(' in line:
                        relative_path = str(file_path.relative_to(self.repo_path))
                        return relative_path, i

            except Exception:
                continue

        # Default to entry point if not found
        relative_path = str(entry_point.relative_to(self.repo_path))
        return relative_path, 0


async def detect_tools_runtime(repo_path: str, timeout: int = 30) -> list[MCPTool]:
    """
    Convenience function to detect tools via runtime discovery.

    Args:
        repo_path: Path to repository
        timeout: Timeout in seconds for server startup

    Returns:
        List of detected MCPTool objects
    """
    detector = RuntimeToolDetector(repo_path, timeout)
    return await detector.detect_tools()
