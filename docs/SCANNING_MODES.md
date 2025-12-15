# Scanning Modes: Sequential vs Parallel

VMCP supports two scanning modes for different use cases.

## Mode 1: Sequential (Default)

**When to Use**: General purpose, moderate repositories

**How it works**:
```
Single Runner
├─ Clone repository
├─ Run Trivy      → 1-2 min
├─ Run OSV        → 1-2 min  (waits for Trivy)
├─ Run Semgrep    → 2-3 min  (waits for OSV)
├─ Aggregate
└─ Create PR
```

**Characteristics**:
- ✅ Uses only 1 GitHub Actions runner
- ✅ Lower resource usage
- ✅ Good for most repositories
- ⏱️ Total time: ~4-6 minutes
- 💰 Cost: 1 runner × 6 minutes = 6 runner-minutes

**Usage**:
```yaml
Inputs:
  repo_url: https://github.com/org/repo
  scanners: (empty for auto-detect)
  parallel_mode: false  # or unchecked
```

## Mode 2: Parallel

**When to Use**: Large repositories, need fast results

**How it works**:
```
Runner 1 (Trivy)    → 1-2 min ┐
Runner 2 (OSV)      → 1-2 min ├─ All run simultaneously
Runner 3 (Semgrep)  → 2-3 min ┘
                                ↓
          Aggregator Runner
          ├─ Download all results
          ├─ Merge into single violations.json
          ├─ Aggregate
          └─ Create PR
```

**Characteristics**:
- ✅ 3x faster (scanners run simultaneously)
- ✅ Best for large codebases
- ⚠️ Uses 4 GitHub Actions runners (3 scanners + 1 aggregator)
- ⏱️ Total time: ~2-3 minutes
- 💰 Cost: 3 runners × 3 minutes + 1 runner × 1 minute = 10 runner-minutes

**Usage**:
```yaml
Inputs:
  repo_url: https://github.com/org/repo
  scanners: (leave empty - parallel mode uses all scanners)
  parallel_mode: true  # or checked
```

## Comparison Table

| Feature | Sequential | Parallel |
|---------|-----------|----------|
| **Speed** | 4-6 minutes | 2-3 minutes |
| **Runners Used** | 1 | 4 (3 scanners + 1 aggregator) |
| **Cost** | ~6 runner-minutes | ~10 runner-minutes |
| **Best For** | Small-medium repos | Large repos, urgent scans |
| **Customizable Scanners** | Yes | No (uses all 3) |
| **Resource Usage** | Low | Higher |

## When to Use Each Mode

### Use Sequential Mode When:
- ✅ Repository is small-medium size (<100K LOC)
- ✅ No rush for results
- ✅ Want to minimize GitHub Actions usage
- ✅ Want to select specific scanners
- ✅ Free tier GitHub Actions (2000 minutes/month)

### Use Parallel Mode When:
- ✅ Repository is large (>100K LOC)
- ✅ Need results quickly (security incident, PR checks)
- ✅ Have plenty of GitHub Actions minutes
- ✅ Want all scanners to run
- ✅ Scanning multiple large repos in succession

## Technical Details

### Sequential Mode Implementation

**Job Flow**:
```yaml
jobs:
  scan:
    if: !inputs.parallel_mode
    steps:
      - Checkout
      - Install all scanners
      - Run scanners sequentially (in same runner)
      - Aggregate
      - Create PR
```

**Scanners run one after another**:
```python
# In orchestrator.py
results = await orchestrator.run_all_scanners(['trivy', 'osv-scanner', 'semgrep'])
# Uses asyncio.gather() but still in same runner
```

### Parallel Mode Implementation

**Job Flow**:
```yaml
jobs:
  parallel-scan:
    if: inputs.parallel_mode
    strategy:
      matrix:
        scanner: [trivy, osv-scanner, semgrep]  # 3 runners
    steps:
      - Checkout
      - Install ONE scanner
      - Run ONE scanner
      - Upload artifact

  aggregate-parallel-results:
    needs: parallel-scan  # waits for all 3
    steps:
      - Download all artifacts (merge)
      - Aggregate
      - Create PR
```

**3 Separate Runners**:
- Runner 1: Only installs & runs Trivy
- Runner 2: Only installs & runs OSV Scanner  
- Runner 3: Only installs & runs Semgrep

**Artifact Merging**:
```yaml
- name: Download all scanner results
  uses: actions/download-artifact@v4
  with:
    pattern: scan-results-*     # Gets all 3 artifacts
    merge-multiple: true         # Merges into results/
    path: results/
```

## Cost Analysis

### GitHub Actions Free Tier
- 2000 minutes/month for free accounts
- 3000 minutes/month for Pro accounts

### Sequential Mode Usage
```
10 scans/month × 6 minutes = 60 minutes/month
= 3% of free tier
```

### Parallel Mode Usage
```
10 scans/month × 10 minutes = 100 minutes/month
= 5% of free tier
```

### Break-even Analysis
For repositories where Semgrep takes >3 minutes:
- **Sequential**: 1 + 1 + 4 = 6 minutes total
- **Parallel**: max(1, 1, 4) + 1 = 5 minutes total
- **Savings**: Parallel is faster despite using more runners

## Examples

### Example 1: Small Python Project

**Repository**: Flask (small web framework)

**Sequential Mode**:
```
Trivy:    45 seconds
OSV:      30 seconds
Semgrep:  90 seconds
Total:    165 seconds = 2.75 minutes
```

**Parallel Mode**:
```
All scanners: 90 seconds (limited by slowest)
Aggregate:    15 seconds
Total:        105 seconds = 1.75 minutes
Speedup:      1.6x faster
```

### Example 2: Large JavaScript Project

**Repository**: React (large codebase)

**Sequential Mode**:
```
Trivy:    2 minutes
OSV:      2 minutes
Semgrep:  5 minutes
Total:    9 minutes
```

**Parallel Mode**:
```
All scanners: 5 minutes (limited by Semgrep)
Aggregate:    30 seconds
Total:        5.5 minutes
Speedup:      1.6x faster
```

## Limitations

### Sequential Mode
- ❌ Slower for large repositories
- ✅ Can customize scanner selection

### Parallel Mode
- ❌ Cannot customize scanners (always runs all 3)
- ❌ Uses more runner minutes
- ✅ Faster results
- ✅ Better for CI/CD pipelines

## Recommendations

| Repository Size | Lines of Code | Recommended Mode |
|----------------|---------------|------------------|
| Tiny | <1K | Sequential |
| Small | 1K-10K | Sequential |
| Medium | 10K-50K | Sequential |
| Large | 50K-100K | Parallel |
| Very Large | 100K-500K | Parallel |
| Huge | >500K | Parallel |

## Future Enhancements

Potential improvements:
- [ ] Smart mode selection based on repo size
- [ ] Configurable scanner matrix for parallel mode
- [ ] Conditional scanner execution (skip if no files match)
- [ ] Result caching to avoid re-scanning unchanged code

## FAQ

**Q: Can I use parallel mode with specific scanners?**
A: Not currently. Parallel mode runs all 3 scanners. Use sequential mode for custom selection.

**Q: Why not always use parallel mode?**
A: For small repos, setup overhead negates speed benefits. Sequential is more efficient.

**Q: Can I run parallel scans on multiple repos?**
A: Yes, trigger the workflow multiple times. Each invocation is independent.

**Q: Does parallel mode affect result quality?**
A: No, results are identical. Only execution time differs.

**Q: What if one scanner fails in parallel mode?**
A: Other scanners continue. Aggregator merges available results.
