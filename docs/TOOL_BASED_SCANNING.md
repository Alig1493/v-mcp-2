# Tool-Based Vulnerability Scanning

This feature allows you to scan MCP (Model Context Protocol) servers and group vulnerabilities by the individual tools they expose, rather than just by scanner type.

## Overview

Traditional vulnerability scanning groups results by scanner (Trivy, OSV-Scanner, Semgrep, YARA). Tool-based scanning adds an additional dimension: it identifies the MCP tools in a repository and maps vulnerabilities to specific tools.

### Why Tool-Based Scanning?

- **Tool-Level Risk Assessment**: Understand which specific MCP tools have vulnerabilities
- **Targeted Remediation**: Fix vulnerabilities in high-risk tools first
- **Better Context**: See how vulnerabilities relate to actual functionality
- **Dependency Tracking**: Separate dependency vulnerabilities from tool-specific issues

## File Format

### Tools File (One Per Repository)

`<org>-<repo>-tools.json`:
```json
[
  {
    "name": "get_temporal_context",
    "file_path": "vuln_nist_mcp_server.py",
    "description": "Retrieve a CVE by its CVE-ID",
    "line_number": 75,
    "language": "python",
    "trivy": [
      {
        "id": "CVE-2024-1234",
        "severity": "HIGH",
        "file_location": "vuln_nist_mcp_server.py",
        ...
      }
    ],
    "semgrep": [
      {
        "id": "python.lang.security.sql-injection",
        "severity": "HIGH",
        ...
      }
    ]
  },
  {
    "name": "dependencies",
    "file_path": "",
    "description": "Project dependencies",
    "line_number": null,
    "language": "N/A",
    "trivy": [...],
    "osv-scanner": [...]
  }
]
```

**Key Features:**
- One file per repository
- Tool metadata (name, file_path, description, etc.)
- Scanner results nested under scanner names
- Special categories: `dependencies`, `unknown`

## Usage

### Scanning with Tool Grouping

#### Using Makefile (GitHub Actions)

```bash
# Scan a repository and group by tools using all scanners
make scan-tool REPO_URL=https://github.com/org/mcp-server

# Scan with specific scanners
make scan-tool REPO_URL=https://github.com/org/mcp-server SCANNERS=trivy,semgrep

# Scan with YARA only
make scan-tool REPO_URL=https://github.com/org/mcp-server SCANNERS=yara
```

#### Using CLI Directly

```bash
# Scan a repository and group by tools (defaults to results_tools/ directory)
uv run python -m vmcp.cli scan-tool https://github.com/org/mcp-server

# Scan with specific scanners
uv run python -m vmcp.cli scan-tool https://github.com/org/mcp-server --scanners trivy semgrep

# Custom output directory
uv run python -m vmcp.cli scan-tool https://github.com/org/mcp-server --output-dir custom_dir
```

### Aggregating Tool-Based Results

```bash
# Aggregate tool-based results and generate SCAN_RESULTS_TOOLS.md (defaults to results_tools/)
uv run python -m vmcp.cli aggregate-tool https://github.com/org/mcp-server

# Specify custom results directory
uv run python -m vmcp.cli aggregate-tool https://github.com/org/mcp-server --results-dir custom_dir
```

## Tool Detection

The system automatically detects MCP tools by analyzing code patterns:

### Python (FastMCP / Official SDK)

```python
from fastmcp import FastMCP

mcp = FastMCP("Server Name")

@mcp.tool()
def my_tool(param: str) -> str:
    """Tool description"""
    return result
```

Detected as: `my_tool`

### TypeScript

```typescript
import { Tool } from "@modelcontextprotocol/sdk";

@Tool({ description: 'Lookup IP address' })
async function ip_lookup(args: IPInput): Promise<IPOutput> {
    // implementation
}
```

Detected as: `ip_lookup`

## Vulnerability Grouping Logic

1. **Direct File Match**: If a vulnerability is in the same file as a tool definition, it's assigned to that tool
2. **Directory Match**: If a vulnerability is in the same directory as a tool file, it's assigned to that tool
3. **Dependencies**: Trivy and OSV-Scanner findings are assigned to `dependencies` category
4. **Unknown**: Other vulnerabilities are assigned to `unknown` category

## Output Reports

### SCAN_RESULTS_TOOLS.md

Tool-based scanning generates a separate markdown report showing vulnerabilities per tool:

| Project | Tool | Description | Results | Total | Critical | High | Medium | Low | Fixable | Scanners | Status |
|---------|------|-------------|---------|-------|----------|------|--------|-----|---------|----------|--------|
| org/repo | ip_lookup | Lookup IP info | 📋 | 5 | 1 | 2 | 2 | 0 | 3 | semgrep, trivy | 🔴 |
| org/repo | 📦 dependencies | | 📋 | 10 | 0 | 5 | 5 | 0 | 8 | osv-scanner, trivy | 🔴 |

### Special Tool Categories

- **📦 dependencies**: Vulnerabilities in project dependencies (npm, pip, etc.)
- **❓ unknown**: Vulnerabilities not mapped to specific tools

## Example Workflow

```bash
# 1. Scan multiple MCP repositories with tool grouping (uses results_tools/ by default)
for repo in repo1 repo2 repo3; do
    uv run python -m vmcp.cli scan-tool https://github.com/org/$repo
done

# 2. Aggregate results for each repository
for repo in repo1 repo2 repo3; do
    uv run python -m vmcp.cli aggregate-tool https://github.com/org/$repo
done

# 3. View the tool-based summary
cat SCAN_RESULTS_TOOLS.md
```

## Directory Structure

Tool-based scanning uses a separate directory structure to keep results organized:

```
project/
├── results/                    # Regular scan results
│   ├── org-repo-violations.json
│   └── SCAN_RESULTS.md
│
└── results_tools/              # Tool-based scan results (default)
    ├── org-repo-tools.json      # Single file per repo
    └── SCAN_RESULTS_TOOLS.md    # Summary table (one row per repo)
```

**Why separate directories?**
- Prevents confusion between regular and tool-based results
- Different file formats and naming conventions
- Different report outputs (SCAN_RESULTS.md vs SCAN_RESULTS_TOOLS.md)
- Easier to manage and clean up

**Temporary Files (Deleted After Aggregation):**
- `{scanner}-tool-violations.json` - Scanner-specific results (parallel scan)
- `{org}-{repo}-tools-metadata.json` - Tool metadata (parallel scan)

## Comparison: Regular vs Tool-Based Scanning

### Regular Scanning
- **Format**: `{"scanner": [vulns]}`
- **Output**: One file per repo (`org-repo-violations.json`)
- **Report**: `SCAN_RESULTS.md` - One row per repo
- **Directory**: `results/`
- **Grouping**: By scanner type
- **Use Case**: General vulnerability assessment

### Tool-Based Scanning
- **Format**: `[{"name": "tool", "scanner1": [vulns], "scanner2": [vulns]}]`
- **Output**: One file per repo (`org-repo-tools.json`)
- **Report**: `SCAN_RESULTS_TOOLS.md` - One row per repo with tool list
- **Directory**: `results_tools/`
- **Grouping**: By tool with scanner results nested
- **Use Case**: MCP-specific risk assessment per tool

## Limitations

1. **Tool Detection Accuracy**: Relies on code pattern matching; may miss dynamic tool registration
2. **Mapping Heuristics**: Uses file/directory proximity; may not be 100% accurate for complex codebases
3. **Performance**: Slightly slower than regular scanning due to tool detection step

## Supported MCP Frameworks

- **Python**: FastMCP, official `mcp` SDK
- **TypeScript**: `@modelcontextprotocol/sdk`
- **Detection**: Automatic via decorator/annotation patterns

## Future Enhancements

- Runtime tool discovery via MCP protocol (`tools/list` JSON-RPC)
- Support for HTTP-deployed MCP servers
- Per-tool risk scoring
- Tool dependency graphs
