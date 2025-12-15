"""Tests for scanner orchestration."""
import tempfile
from pathlib import Path

import pytest

from vmcp.orchestrator import ScanOrchestrator


def test_orchestrator_initialization():
    """Test ScanOrchestrator initialization."""
    orchestrator = ScanOrchestrator("/tmp/test", "org", "repo")
    assert orchestrator.repo_path == "/tmp/test"
    assert orchestrator.org_name == "org"
    assert orchestrator.repo_name == "repo"


def test_scanner_map_exists():
    """Test that scanner map is defined."""
    assert len(ScanOrchestrator.SCANNER_MAP) > 0
    assert 'trivy' in ScanOrchestrator.SCANNER_MAP
    assert 'osv-scanner' in ScanOrchestrator.SCANNER_MAP
    assert 'semgrep' in ScanOrchestrator.SCANNER_MAP


def test_save_results():
    """Test saving results to JSON file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        orchestrator = ScanOrchestrator("/tmp/test", "testorg", "testrepo")

        # Create fake results
        results = {
            'trivy': [],
            'osv-scanner': []
        }

        orchestrator.save_results(results, temp_dir)

        # Check file was created
        output_file = Path(temp_dir) / 'testorg' / 'testrepo' / 'violations.json'
        assert output_file.exists()

        # Check content
        import json
        with open(output_file) as f:
            data = json.load(f)

        assert 'testorg/testrepo' in data
        assert 'trivy' in data['testorg/testrepo']
        assert 'osv-scanner' in data['testorg/testrepo']
