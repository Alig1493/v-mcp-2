"""Aggregate vulnerability scan results and generate README."""
import json
import os
from pathlib import Path
from typing import Any


SEVERITY_ORDER = {
    'CRITICAL': 0,
    'HIGH': 1,
    'MEDIUM': 2,
    'LOW': 3,
    'UNKNOWN': 4,
    'WARNING': 5,
    'NONE': 6,
}

SEVERITY_EMOJI = {
    'CRITICAL': '🔴',
    'HIGH': '🔴',
    'MEDIUM': '🟡',
    'LOW': '🟡',
    'UNKNOWN': '🟡',
    'WARNING': '🟡',
    'NONE': '🟢',
}


def get_worst_severity(vulnerabilities: list[dict[str, Any]]) -> str:
    """Get the worst (highest priority) severity from a list of findings."""
    if not vulnerabilities:
        return 'NONE'

    worst_severity = 'NONE'
    worst_priority = SEVERITY_ORDER.get(worst_severity, 999)

    for vuln in vulnerabilities:
        severity = vuln.get('severity', 'UNKNOWN')
        priority = SEVERITY_ORDER.get(severity, 999)

        if priority < worst_priority:
            worst_severity = severity
            worst_priority = priority

    return worst_severity


def aggregate_results(results_dir: str) -> dict[str, Any]:
    """Aggregate all vulnerability results from scanner-specific files and single violations.json."""
    aggregated = {}
    results_path = Path(results_dir)

    # First, load existing violations.json if it exists (single source of truth)
    violations_file = results_path / 'violations.json'
    if violations_file.exists():
        with open(violations_file, 'r') as f:
            content = f.read().strip()
            if content:  # Only load if not empty
                aggregated = json.loads(content)

    # Find old per-repo violations.json files (for migration)
    per_repo_files = []
    for item in results_path.iterdir():
        if item.is_dir():
            repo_violations = item / 'violations.json'
            if repo_violations.exists():
                per_repo_files.append(repo_violations)
            # Also check nested org/repo structure
            for subitem in item.iterdir():
                if subitem.is_dir():
                    nested_violations = subitem / 'violations.json'
                    if nested_violations.exists():
                        per_repo_files.append(nested_violations)

    # Merge old per-repo files
    for per_repo_file in per_repo_files:
        with open(per_repo_file, 'r') as f:
            data = json.load(f)
            for org_repo, scanner_results in data.items():
                if org_repo not in aggregated:
                    aggregated[org_repo] = {}
                for scanner_name, vulnerabilities in scanner_results.items():
                    aggregated[org_repo][scanner_name] = vulnerabilities

    # Find scanner-specific files (e.g., trivy-violations.json from new scans)
    scanner_files = list(results_path.glob('**/*-violations.json'))

    for scanner_file in scanner_files:
        with open(scanner_file, 'r') as f:
            data = json.load(f)

            # Merge scanner results for each repo
            for org_repo, scanner_results in data.items():
                if org_repo not in aggregated:
                    aggregated[org_repo] = {}

                # Merge scanner findings
                for scanner_name, vulnerabilities in scanner_results.items():
                    # Update with latest scanner data
                    aggregated[org_repo][scanner_name] = vulnerabilities

    return aggregated


def save_aggregated_results(results: dict[str, Any], results_dir: str) -> None:
    """Save aggregated results to a single violations.json file."""
    results_path = Path(results_dir)
    results_path.mkdir(parents=True, exist_ok=True)

    # Save all results to single violations.json file
    violations_file = results_path / 'violations.json'

    with open(violations_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Aggregated results saved to {violations_file}")

    # Remove scanner-specific files after aggregation
    scanner_files = list(results_path.glob('**/*-violations.json'))
    for scanner_file in scanner_files:
        scanner_file.unlink()
        print(f"Removed scanner-specific file: {scanner_file}")

    # Remove old per-repo violations.json files
    old_violations_files = list(results_path.glob('**/violations.json'))
    for old_file in old_violations_files:
        if old_file != violations_file:  # Don't remove the new single file
            old_file.unlink()
            print(f"Removed old per-repo file: {old_file}")


def count_by_severity(vulnerabilities: list[dict[str, Any]]) -> dict[str, int]:
    """Count vulnerabilities by severity."""
    counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for vuln in vulnerabilities:
        severity = vuln.get('severity', 'UNKNOWN')
        if severity in counts:
            counts[severity] += 1
    return counts


def count_fixable(vulnerabilities: list[dict[str, Any]]) -> int:
    """Count vulnerabilities with available fixes."""
    return sum(1 for vuln in vulnerabilities if vuln.get('fixed_version'))


def get_scanners_used(scanners: dict[str, list]) -> str:
    """Get list of scanners that were used."""
    scanner_names = []
    for scanner_name, vulns in scanners.items():
        # Only include scanners that actually ran (even if no vulns found)
        scanner_names.append(scanner_name)
    return ', '.join(sorted(scanner_names)) if scanner_names else 'None'


def generate_summary_table(results: dict[str, Any]) -> str:
    """Generate summary table for README."""
    # Prepare all row data first
    rows = []

    for org_repo, scanners in results.items():
        # Collect all vulnerabilities across scanners (done once)
        all_vulnerabilities = []
        for scanner, vulnerabilities in scanners.items():
            all_vulnerabilities.extend(vulnerabilities)

        total_findings = len(all_vulnerabilities)
        worst_severity = get_worst_severity(all_vulnerabilities)
        severity_priority = SEVERITY_ORDER.get(worst_severity, 999)
        status_emoji = SEVERITY_EMOJI.get(worst_severity, '⚪')

        # Get severity breakdown
        severity_counts = count_by_severity(all_vulnerabilities)

        # Count fixable vulnerabilities
        fixable_count = count_fixable(all_vulnerabilities)

        # Get scanners used
        scanners_used = get_scanners_used(scanners)

        # Store row data with sort key
        rows.append({
            'org_repo': org_repo,
            'total': total_findings,
            'severity_counts': severity_counts,
            'fixable': fixable_count,
            'scanners': scanners_used,
            'status': status_emoji,
            'sort_key': (-severity_priority, org_repo)  # Best first, then alphabetical
        })

    # Sort rows by severity (best first), then by name
    rows.sort(key=lambda r: r['sort_key'])

    # Generate table lines
    lines = [
        "# Vulnerability Scan Results",
        "",
        "| Project | Total | Critical | High | Medium | Low | Fixable | Scanners | Status |",
        "|---------|-------|----------|------|--------|-----|---------|----------|--------|",
    ]

    for row in rows:
        results_link = f"[{row['org_repo']}](results/violations.json)"
        lines.append(
            f"| {results_link} | {row['total']} | "
            f"{row['severity_counts']['CRITICAL']} | {row['severity_counts']['HIGH']} | "
            f"{row['severity_counts']['MEDIUM']} | {row['severity_counts']['LOW']} | "
            f"{row['fixable']} | {row['scanners']} | {row['status']} |"
        )

    return "\n".join(lines)


def main():
    import sys

    if len(sys.argv) < 2:
        results_dir = 'results'
    else:
        results_dir = sys.argv[1]

    # Aggregate results
    results = aggregate_results(results_dir)

    # Save aggregated results to violations.json
    save_aggregated_results(results, results_dir)

    # Generate report (summary only, no details)
    summary = generate_summary_table(results)

    # Write to SCAN_RESULTS.md (not README.md)
    with open('SCAN_RESULTS.md', 'w') as f:
        f.write(summary)

    print("Generated SCAN_RESULTS.md with vulnerability summary")


if __name__ == '__main__':
    main()
