# VMCP Output Files Guide

## Where Scan Results Go

After running a vulnerability scan, you'll have these files:

### 1. violations.json (Detailed Results)

**Location:** `results/<org>/<repo>/violations.json`

**Purpose:** Complete vulnerability data from all scanners

**Example:** `results/django/django/violations.json`

**Format:**
```json
{
  "django/django": {
    "trivy": [
      {
        "id": "CVE-2024-1234",
        "severity": "HIGH",
        "summary": "SQL Injection vulnerability",
        "details": "Detailed description...",
        "affected_range": "4.2.0",
        "fixed_version": "4.2.1",
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
        ],
        "published": "2024-01-15T12:00:00Z"
      }
    ],
    "semgrep": [ /* ... */ ],
    "osv-scanner": [ /* ... */ ]
  }
}
```

**Use this for:**
- Detailed vulnerability analysis
- Integration with other tools
- Programmatic processing
- Historical tracking

---

### 2. SCAN_RESULTS.md (Summary Table)

**Location:** `SCAN_RESULTS.md` (root of repository)

**Purpose:** Human-readable summary of all scans

**Auto-generated:** Yes (overwrites on each aggregate)

**Format:**
```markdown
# Vulnerability Scan Results

| Project | Total Findings | Severity | Status |
|---------|----------------|----------|--------|
| django/django | 42 | HIGH | 🔴 |
| facebook/react | 15 | MEDIUM | 🟡 |
| golang/go | 3 | LOW | 🟡 |

## Detailed Findings

### django/django

#### Scanner: trivy
Found 20 vulnerabilities

**CRITICAL**: 2
**HIGH**: 8
**MEDIUM**: 10

#### Scanner: semgrep
Found 15 vulnerabilities

**HIGH**: 5
**MEDIUM**: 10

#### Scanner: osv-scanner
Found 7 vulnerabilities

**HIGH**: 3
**MEDIUM**: 4
```

**Use this for:**
- Quick overview of all scans
- At-a-glance severity assessment
- Management reporting
- Prioritizing work

---

### 3. README.md (Project Documentation)

**Location:** `README.md` (root of repository)

**Purpose:** Project documentation and usage guide

**Auto-generated:** NO - This is YOUR documentation file

**Status:** PRESERVED (not overwritten by scans)

**Contains:**
- Project overview
- Installation instructions
- Usage examples
- Feature list
- Documentation links

**Important:** The aggregator now writes to `SCAN_RESULTS.md` instead of `README.md` to preserve your project documentation!

---

## File Comparison

| File | Location | Purpose | Auto-Generated | Committed to Git |
|------|----------|---------|----------------|------------------|
| `violations.json` | `results/<org>/<repo>/` | Detailed scan data | Yes | Yes |
| `SCAN_RESULTS.md` | Root | Summary table | Yes | Yes |
| `README.md` | Root | Project docs | No | Yes |

## Git Behavior

**What gets committed after a scan:**
```bash
git add results/ SCAN_RESULTS.md
git commit -m "Add scan results for {repo_url}"
git push
```

**NOT committed:**
- Temporary clone of target repo (deleted after scan)
- Scanner binaries (installed in CI, not committed)
- Virtual environment

## Example Workflow Output

**Before scan:**
```
v-mcp-2/
├── README.md
├── src/
└── .github/
```

**After scanning django/django:**
```
v-mcp-2/
├── README.md              ← UNCHANGED
├── SCAN_RESULTS.md        ← NEW (or updated)
├── results/
│   └── django/
│       └── django/
│           └── violations.json  ← NEW
├── src/
└── .github/
```

**After scanning multiple repos:**
```
v-mcp-2/
├── README.md              ← UNCHANGED
├── SCAN_RESULTS.md        ← UPDATED (aggregates all)
├── results/
│   ├── django/
│   │   └── django/
│   │       └── violations.json
│   ├── facebook/
│   │   └── react/
│   │       └── violations.json
│   └── golang/
│       └── go/
│           └── violations.json
├── src/
└── .github/
```

## How to Use the Results

### View Summary
```bash
cat SCAN_RESULTS.md
```

### View Detailed Results for One Repo
```bash
cat results/django/django/violations.json | jq
```

### Extract High Severity Issues
```bash
cat results/django/django/violations.json | jq '.["django/django"]["trivy"][] | select(.severity == "HIGH")'
```

### Count Total Vulnerabilities
```bash
cat results/django/django/violations.json | jq '.["django/django"]["trivy"] | length'
```

## Important Notes

1. **README.md is safe** - Your project documentation won't be overwritten
2. **SCAN_RESULTS.md is auto-generated** - Don't edit manually, it will be overwritten
3. **violations.json is append-only** - Each scan creates a new file, old scans remain
4. **results/ is committed** - All scan data is version controlled

## Questions?

- **Q: Can I edit SCAN_RESULTS.md?**
  - A: You can, but it will be overwritten on next aggregate

- **Q: Where is the raw scanner output?**
  - A: It's parsed and stored in violations.json

- **Q: Can I change the output format?**
  - A: Yes! Edit `src/vmcp/utils/aggregate_results.py`

- **Q: How do I exclude results from git?**
  - A: Add to `.gitignore`, but note that defeats the purpose of centralized storage
