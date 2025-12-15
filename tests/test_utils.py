"""Tests for utility functions."""
import tempfile
from pathlib import Path

from vmcp.utils.aggregate_results import get_worst_severity
from vmcp.utils.detect_language import detect_languages, select_scanners


def test_get_worst_severity_empty():
    """Test get_worst_severity with empty list."""
    assert get_worst_severity([]) == 'NONE'


def test_get_worst_severity_single():
    """Test get_worst_severity with single vulnerability."""
    vulns = [{'severity': 'HIGH'}]
    assert get_worst_severity(vulns) == 'HIGH'


def test_get_worst_severity_multiple():
    """Test get_worst_severity with multiple vulnerabilities."""
    vulns = [
        {'severity': 'LOW'},
        {'severity': 'HIGH'},
        {'severity': 'MEDIUM'},
        {'severity': 'CRITICAL'},
    ]
    assert get_worst_severity(vulns) == 'CRITICAL'


def test_get_worst_severity_priority():
    """Test severity priority ordering."""
    # CRITICAL should beat HIGH
    assert get_worst_severity([
        {'severity': 'HIGH'},
        {'severity': 'CRITICAL'}
    ]) == 'CRITICAL'

    # HIGH should beat MEDIUM
    assert get_worst_severity([
        {'severity': 'MEDIUM'},
        {'severity': 'HIGH'}
    ]) == 'HIGH'

    # MEDIUM should beat LOW
    assert get_worst_severity([
        {'severity': 'LOW'},
        {'severity': 'MEDIUM'}
    ]) == 'MEDIUM'


def test_detect_languages_empty():
    """Test language detection on empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        languages = detect_languages(temp_dir)
        assert languages == {}


def test_detect_languages_python():
    """Test Python file detection."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create Python file
        py_file = Path(temp_dir) / 'test.py'
        py_file.write_text('print("hello")')

        languages = detect_languages(temp_dir)
        assert 'python' in languages
        assert languages['python'] == 1


def test_detect_languages_multiple():
    """Test detection of multiple languages."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create files
        (Path(temp_dir) / 'test.py').write_text('pass')
        (Path(temp_dir) / 'app.js').write_text('console.log()')
        (Path(temp_dir) / 'main.go').write_text('package main')

        languages = detect_languages(temp_dir)
        assert 'python' in languages
        assert 'javascript' in languages
        assert 'go' in languages


def test_select_scanners_python():
    """Test scanner selection for Python."""
    scanners = select_scanners({'python': 10})
    assert 'trivy' in scanners
    assert 'semgrep' in scanners
    assert 'osv-scanner' in scanners


def test_select_scanners_javascript():
    """Test scanner selection for JavaScript."""
    scanners = select_scanners({'javascript': 5})
    assert 'trivy' in scanners
    assert 'semgrep' in scanners
    assert 'osv-scanner' in scanners


def test_select_scanners_empty():
    """Test scanner selection with no languages."""
    scanners = select_scanners({})
    # Should still include general scanners
    assert 'trivy' in scanners
    assert 'osv-scanner' in scanners
