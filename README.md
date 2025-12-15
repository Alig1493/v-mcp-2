# VMCP - Vulnerability Management CI/CD Platform

Automated vulnerability scanning platform for GitHub repositories using multiple security scanners in parallel.

## 🎯 What This Does

**This repository triggers a GitHub Action that:**
1. ✅ Clones any public repository you specify
2. ✅ Runs recommended scanners (or your choice of scanners)
3. ✅ Publishes results to `results/<org>/<repo>/violations.json`
4. ✅ Aggregates findings and updates a summary table in README.md

**No installation needed on target repositories!** This scans external repos and stores results here.

## Features

- **Multi-Scanner Support**: Runs Trivy, OSV Scanner, and Semgrep in parallel
- **Language Detection**: Automatically detects repository languages and selects appropriate scanners
- **CVE Link Enhancement**: Validates and enhances CVE links to point to detailed vulnerability information
- **GitHub Actions Integration**: Ready-to-use workflow for automated scanning
- **Aggregated Reporting**: Generates comprehensive vulnerability reports with severity-based status indicators

## Installation

### Prerequisites

- Python 3.13+
- uv (Python package manager)
- Git

### Install from source

```bash
# Clone the repository
git clone <this-repo-url>
cd v-mcp-2

# Install with uv
uv sync

# Install the CLI tool
uv pip install -e .
```

## Usage

### CLI Usage

#### Scan a repository

```bash
# Auto-detect scanners based on repository language
vmcp scan https://github.com/org/repo

# Use specific scanners
vmcp scan https://github.com/org/repo --scanners trivy osv-scanner semgrep

# Specify output directory
vmcp scan https://github.com/org/repo --output-dir ./my-results
```

#### Aggregate results

```bash
# Aggregate all scan results and generate README
vmcp aggregate --results-dir results
```

### GitHub Actions Usage (Primary Method)

**🚀 Quick Start:**
1. Push this repository to GitHub
2. Go to **Actions** tab in your GitHub repository
3. Select **"Vulnerability Scan"** workflow
4. Click **"Run workflow"** button
5. Enter:
   - **Repository URL**: `https://github.com/org/target-repo` (the repo to scan)
   - **Scanners**: Leave empty for auto-detect, or specify: `trivy,semgrep,osv-scanner`
6. Click **"Run workflow"** to start

**📊 View Results:**
- Results are automatically committed to `results/<org>/<repo>/violations.json`
- Summary table is updated in `README.md`
- Download artifacts from the workflow run

**See [QUICK_START.md](QUICK_START.md) for detailed instructions.**

## Project Structure

```
v-mcp-2/
├── src/vmcp/
│   ├── __init__.py
│   ├── models.py              # Pydantic models for vulnerabilities
│   ├── cli.py                 # CLI entry point
│   ├── orchestrator.py        # Parallel scanner orchestration
│   ├── scanners/
│   │   ├── __init__.py
│   │   ├── base.py           # Base scanner interface
│   │   ├── trivy.py          # Trivy scanner implementation
│   │   ├── osv.py            # OSV scanner implementation
│   │   └── semgrep.py        # Semgrep scanner implementation
│   └── utils/
│       ├── detect_language.py    # Language detection
│       ├── enhance_cve_links.py  # CVE link enhancement
│       └── aggregate_results.py  # Results aggregation
├── .github/workflows/
│   └── scan-repo.yml         # GitHub Actions workflow
├── pyproject.toml
└── README.md
```

## Output Format

### Violations JSON

Results are saved to `results/<org>/<repo>/violations.json`:

```json
{
  "org/repo": {
    "trivy": [
      {
        "id": "CVE-2024-1234",
        "identifier_type": "cve",
        "severity": "HIGH",
        "summary": "Vulnerability description",
        "details": "Detailed information...",
        "affected_range": "1.0.0",
        "fixed_version": "1.0.1",
        "references": [
          {
            "type": "web",
            "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-1234"
          }
        ],
        "scores": [
          {
            "type": "cvss",
            "value": 7.5,
            "version": "3.0"
          }
        ]
      }
    ],
    "semgrep": [...],
    "osv-scanner": [...]
  }
}
```

### README Summary

Generated README includes:

| Project | Total Findings | Severity | Status |
|---------|----------------|----------|--------|
| org/repo | 42 | HIGH | 🔴 |

**Status Indicators**:
- 🔴 CRITICAL or HIGH severity
- 🟡 MEDIUM, LOW, or UNKNOWN severity
- 🟢 No vulnerabilities

## Supported Scanners

- **Trivy**: Container and filesystem vulnerability scanner
- **OSV Scanner**: Open Source Vulnerability scanner
- **Semgrep**: Static analysis security testing (SAST)

## CVE Link Enhancement

The platform automatically enhances CVE links:

1. Validates if `https://nvd.nist.gov/vuln/detail/<CVE-ID>` exists
2. Falls back to search URL if direct link unavailable
3. Ensures all CVE references point to useful information

## Development

### Running tests

```bash
# Install development dependencies
uv sync --dev

# Run tests (when implemented)
pytest
```

### Adding new scanners

1. Create a new scanner class in `src/vmcp/scanners/`
2. Inherit from `BaseScanner`
3. Implement `name` property and `scan()` method
4. Add to `SCANNER_MAP` in `orchestrator.py`
5. Update language detection mappings in `utils/detect_language.py`

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or PR.
