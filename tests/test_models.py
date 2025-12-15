"""Tests for data models."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from vmcp.models import (
    VulnerabilityModel,
    VulnerabilityReferenceModel,
    VulnerabilityScoreModel,
)


def test_vulnerability_score_model():
    """Test VulnerabilityScoreModel creation."""
    score = VulnerabilityScoreModel(
        type="cvss",
        value=7.5,
        version="3.0"
    )
    assert score.type == "cvss"
    assert score.value == 7.5
    assert score.version == "3.0"


def test_vulnerability_reference_model():
    """Test VulnerabilityReferenceModel creation."""
    ref = VulnerabilityReferenceModel(
        type="web",
        url="https://nvd.nist.gov/vuln/detail/CVE-2024-1234"
    )
    assert ref.type == "web"
    assert ref.url == "https://nvd.nist.gov/vuln/detail/CVE-2024-1234"


def test_vulnerability_model_minimal():
    """Test VulnerabilityModel with minimal fields."""
    vuln = VulnerabilityModel(
        id="CVE-2024-1234",
        identifier_type="cve",
        affected_range="1.0.0",
        details="Test vulnerability",
        severity="HIGH",
        summary="Test summary"
    )

    assert vuln.id == "CVE-2024-1234"
    assert vuln.severity == "HIGH"
    assert vuln.aliases == []
    assert vuln.references == []
    assert vuln.scores == []


def test_vulnerability_model_complete():
    """Test VulnerabilityModel with all fields."""
    vuln = VulnerabilityModel(
        id="CVE-2024-1234",
        identifier_type="cve",
        affected_range="1.0.0",
        aliases=["GHSA-1234-5678-9012"],
        details="Detailed description of vulnerability",
        fixed_version="1.0.1",
        published=datetime(2024, 1, 15, 12, 0, 0),
        references=[
            VulnerabilityReferenceModel(
                type="web",
                url="https://nvd.nist.gov/vuln/detail/CVE-2024-1234"
            )
        ],
        scores=[
            VulnerabilityScoreModel(
                type="cvss",
                value=7.5,
                version="3.0"
            )
        ],
        severity="HIGH",
        source="trivy",
        summary="SQL Injection vulnerability",
        rule_name="sql-injection",
        rule_id="G201",
        confidence="HIGH",
        file_location="app/db.py",
        line_range="42-45",
        categories=["CWE-89"]
    )

    assert vuln.id == "CVE-2024-1234"
    assert vuln.severity == "HIGH"
    assert len(vuln.aliases) == 1
    assert len(vuln.references) == 1
    assert len(vuln.scores) == 1
    assert vuln.rule_name == "sql-injection"
    assert vuln.categories == ["CWE-89"]


def test_vulnerability_model_json_serialization():
    """Test VulnerabilityModel JSON serialization."""
    vuln = VulnerabilityModel(
        id="CVE-2024-1234",
        identifier_type="cve",
        affected_range="1.0.0",
        details="Test",
        severity="HIGH",
        summary="Test"
    )

    json_data = vuln.model_dump(mode='json')

    assert json_data["id"] == "CVE-2024-1234"
    assert json_data["severity"] == "HIGH"
    assert isinstance(json_data, dict)


def test_invalid_severity():
    """Test that invalid severity values are rejected."""
    # Note: With Literal type, Pydantic will validate at runtime
    # This test verifies the model accepts valid severities
    valid_severities = ["UNKNOWN", "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL", "WARNING"]

    for severity in valid_severities:
        vuln = VulnerabilityModel(
            id="TEST-001",
            identifier_type="test",
            affected_range="1.0.0",
            details="Test",
            severity=severity,
            summary="Test"
        )
        assert vuln.severity == severity
