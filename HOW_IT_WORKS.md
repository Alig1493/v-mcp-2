# How VMCP Works

## Workflow Overview

This repository contains a GitHub Action that scans external repositories for vulnerabilities. Here's exactly what happens:

## Step-by-Step Process

### 1. Trigger the Action
- Go to your GitHub repository → **Actions** tab
- Select **"Vulnerability Scan"** workflow
- Click **"Run workflow"**
- Enter inputs:
  - **repo_url**: `https://github.com/org/target-repo` (required)
  - **scanners**: `trivy,semgrep,osv-scanner` (optional - leave empty for auto-detect)

### 2. Clone Target Repository
```bash
git clone --depth 1 https://github.com/org/target-repo
```
The CLI ([cli.py:32-36](src/vmcp/cli.py:32-36)) clones the target repo to a temporary directory.

### 3. Select Scanners
**Option A - Auto-detect** (if no scanners specified):
- Scans repository for file extensions ([detect_language.py:9-42](src/vmcp/utils/detect_language.py:9-42))
- Detects languages (Python, JavaScript, Go, etc.)
- Selects appropriate scanners ([detect_language.py:45-73](src/vmcp/utils/detect_language.py:45-73))

**Option B - Manual** (if scanners specified):
- Uses your provided comma-separated list
- Example: `trivy,semgrep`

### 4. Run Scanners in Parallel
The orchestrator ([orchestrator.py:29-41](src/vmcp/orchestrator.py:29-41)) runs all scanners concurrently:
- **Trivy**: Container and filesystem vulnerabilities
- **OSV Scanner**: Open source vulnerabilities
- **Semgrep**: Static analysis (SAST)

Each scanner:
1. Executes its scan
2. Parses output to standard format
3. Returns list of `VulnerabilityModel` objects

### 5. Publish Results
Results are saved to:
```
results/
└── <org>/
    └── <repo>/
        └── violations.json
```

Format:
```json
{
  "org/repo": {
    "trivy": [
      {
        "id": "CVE-2024-1234",
        "severity": "HIGH",
        "summary": "...",
        "references": [...],
        "scores": [...]
      }
    ],
    "semgrep": [...],
    "osv-scanner": [...]
  }
}
```

### 6. Enhance CVE Links
The system ([enhance_cve_links.py:10-71](src/vmcp/utils/enhance_cve_links.py:10-71)):
- Validates CVE detail URLs: `https://nvd.nist.gov/vuln/detail/CVE-XXXX-XXXXX`
- Falls back to search if detail page doesn't exist
- Updates all references with working URLs

### 7. Aggregate & Update Table
The aggregator ([aggregate_results.py:49-121](src/vmcp/utils/aggregate_results.py:49-121)):
- Scans all `violations.json` files in `results/`
- Determines worst severity for each project
- Generates/updates `README.md` with table:

```markdown
| Project | Total Findings | Severity | Status |
|---------|----------------|----------|--------|
| org/repo | 42 | HIGH | 🔴 |
```

Status indicators:
- 🔴 CRITICAL or HIGH
- 🟡 MEDIUM, LOW, or UNKNOWN
- 🟢 No vulnerabilities

### 8. Commit Results
The workflow commits back to **this repository**:
```bash
git add results/ README.md
git commit -m "Add scan results for {repo_url}"
git push
```

## Example Usage

### Scan a Single Repository
```yaml
# Manual trigger via GitHub UI
Inputs:
  repo_url: https://github.com/facebook/react
  scanners: (leave empty for auto-detect)
```

Result:
- Clones React repository
- Detects JavaScript/TypeScript
- Runs Trivy + Semgrep + OSV Scanner
- Saves to `results/facebook/react/violations.json`
- Updates README.md table

### Scan Multiple Repositories
Run the workflow multiple times with different URLs:
1. `https://github.com/django/django` → `results/django/django/`
2. `https://github.com/golang/go` → `results/golang/go/`
3. `https://github.com/rust-lang/rust` → `results/rust-lang/rust/`

The aggregator combines all results into one table.

### Use Specific Scanners
```yaml
Inputs:
  repo_url: https://github.com/user/my-app
  scanners: trivy,semgrep
```

Only runs Trivy and Semgrep (skips OSV Scanner).

## File Locations

After scanning 3 repos, your repository structure looks like:

```
v-mcp-2/
├── results/
│   ├── facebook/
│   │   └── react/
│   │       └── violations.json
│   ├── django/
│   │   └── django/
│   │       └── violations.json
│   └── golang/
│       └── go/
│           └── violations.json
└── README.md  (auto-generated table)
```

## Key Features

✅ **Clones target repo** - No need for target to have the action
✅ **Auto-detects languages** - Recommends best scanners
✅ **Runs scanners in parallel** - Fast execution
✅ **Publishes to violations.json** - Standard format
✅ **Aggregates results** - Single table view
✅ **Commits automatically** - Results stored in this repo

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Actions (This Repo)                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. User triggers workflow                              │
│     ↓                                                    │
│  2. Clone target repo (https://github.com/org/repo)     │
│     ↓                                                    │
│  3. Detect languages → Select scanners                  │
│     ↓                                                    │
│  4. Run scanners in parallel:                           │
│     • Trivy                                             │
│     • OSV Scanner                                       │
│     • Semgrep                                           │
│     ↓                                                    │
│  5. Parse results → VulnerabilityModel                  │
│     ↓                                                    │
│  6. Enhance CVE links (validate URLs)                   │
│     ↓                                                    │
│  7. Save to results/org/repo/violations.json            │
│     ↓                                                    │
│  8. Aggregate all results → Update README.md            │
│     ↓                                                    │
│  9. Commit results/ and README.md to this repo          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## What Gets Stored in This Repo

- **results/**: All vulnerability scan results
- **README.md**: Auto-generated summary table
- **.github/workflows/**: The action itself
- **src/vmcp/**: Scanner implementations

## What Doesn't Change

- **Target repository**: Remains untouched
- **External scanners**: Installed in CI environment, not committed

## Next Steps

1. **Enable the workflow**: Push this repo to GitHub
2. **Run your first scan**: Actions tab → Vulnerability Scan → Run workflow
3. **View results**: Check `results/` folder and README.md
4. **Scan more repos**: Run the workflow again with different URLs

---

**Summary**: This action runs IN your repo, scans EXTERNAL repos, and stores results BACK in your repo.
