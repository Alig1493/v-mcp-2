"""Example script to test vulnerability scanning."""
import asyncio
from pathlib import Path

from vmcp.models import VulnerabilityModel
from vmcp.orchestrator import ScanOrchestrator


async def test_local_scan():
    """Test scanning a local directory."""
    # For testing, scan this project itself
    repo_path = Path(__file__).parent.parent
    org_name = "test-org"
    repo_name = "test-repo"

    print(f"Scanning {repo_path}...")

    orchestrator = ScanOrchestrator(str(repo_path), org_name, repo_name)

    # Run only Trivy for quick test
    results = await orchestrator.run_all_scanners(['trivy'])

    # Display results
    for scanner, vulnerabilities in results.items():
        print(f"\n{scanner}: Found {len(vulnerabilities)} vulnerabilities")
        if vulnerabilities:
            print(f"  First vulnerability: {vulnerabilities[0].id}")

    # Save results
    output_dir = Path(__file__).parent / 'test_results'
    output_dir.mkdir(exist_ok=True)
    orchestrator.save_results(results, str(output_dir))

    print(f"\nResults saved to {output_dir}/{org_name}/{repo_name}/violations.json")


if __name__ == '__main__':
    asyncio.run(test_local_scan())
