# Contributing to VMCP

Thank you for your interest in contributing to VMCP!

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd v-mcp-2
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   uv pip install -e .
   ```

3. **Verify installation**:
   ```bash
   uv run vmcp --help
   ```

## Project Structure

```
src/vmcp/
├── models.py              # Data models for vulnerabilities
├── cli.py                 # CLI entry point
├── orchestrator.py        # Scanner orchestration
├── scanners/              # Scanner implementations
│   ├── base.py           # Base scanner class
│   ├── trivy.py          # Trivy scanner
│   ├── osv.py            # OSV scanner
│   └── semgrep.py        # Semgrep scanner
└── utils/                 # Utility modules
    ├── detect_language.py    # Language detection
    ├── enhance_cve_links.py  # CVE link enhancement
    └── aggregate_results.py  # Results aggregation
```

## Adding a New Scanner

1. **Create scanner class** in `src/vmcp/scanners/`:
   ```python
   from vmcp.scanners.base import BaseScanner
   from vmcp.models import VulnerabilityModel

   class MyScanner(BaseScanner):
       @property
       def name(self) -> str:
           return "my-scanner"

       async def scan(self) -> list[VulnerabilityModel]:
           # Implementation here
           pass
   ```

2. **Register scanner** in `src/vmcp/orchestrator.py`:
   ```python
   SCANNER_MAP = {
       'my-scanner': MyScanner,
       # ... other scanners
   }
   ```

3. **Update language detection** in `src/vmcp/utils/detect_language.py`:
   ```python
   language_scanners = {
       'python': ['trivy', 'semgrep', 'my-scanner'],
       # ... other languages
   }
   ```

## Code Style

- Use Python 3.13 features
- Follow PEP 8 style guidelines
- Use type hints for all functions
- Keep functions focused and modular

## Testing

```bash
# Test scanning a local directory
python examples/test_scan.py

# Test CLI
uv run vmcp scan https://github.com/user/repo --scanners trivy
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test your changes
5. Commit with clear messages
6. Push to your fork
7. Open a pull request

## Questions?

Open an issue for any questions or concerns.
