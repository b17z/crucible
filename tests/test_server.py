"""Tests for server internals."""

from pathlib import Path

from crucible.models import Domain, Severity, ToolFinding
from crucible.review.core import (
    deduplicate_findings,
    detect_domain,
    detect_domain_for_file,
)


class TestDetectDomainForFile:
    """Test single file domain detection."""

    def test_solidity(self) -> None:
        domain, tags = detect_domain_for_file("contract.sol")
        assert domain == Domain.SMART_CONTRACT
        assert "solidity" in tags
        assert "web3" in tags

    def test_vyper(self) -> None:
        domain, tags = detect_domain_for_file("contract.vy")
        assert domain == Domain.SMART_CONTRACT
        assert "vyper" in tags
        assert "web3" in tags

    def test_python(self) -> None:
        domain, tags = detect_domain_for_file("main.py")
        assert domain == Domain.BACKEND
        assert "python" in tags

    def test_typescript(self) -> None:
        domain, tags = detect_domain_for_file("App.tsx")
        assert domain == Domain.FRONTEND
        assert "typescript" in tags

    def test_javascript(self) -> None:
        domain, tags = detect_domain_for_file("index.js")
        assert domain == Domain.FRONTEND
        assert "javascript" in tags

    def test_go(self) -> None:
        domain, tags = detect_domain_for_file("main.go")
        assert domain == Domain.BACKEND
        assert "go" in tags

    def test_rust(self) -> None:
        domain, tags = detect_domain_for_file("lib.rs")
        assert domain == Domain.BACKEND
        assert "rust" in tags

    def test_terraform(self) -> None:
        domain, tags = detect_domain_for_file("main.tf")
        assert domain == Domain.INFRASTRUCTURE
        assert "infrastructure" in tags
        assert "devops" in tags

    def test_yaml(self) -> None:
        domain, tags = detect_domain_for_file("deploy.yaml")
        assert domain == Domain.INFRASTRUCTURE

    def test_unknown(self) -> None:
        domain, tags = detect_domain_for_file("README.md")
        assert domain == Domain.UNKNOWN
        assert tags == []


class TestDetectDomain:
    """Test domain detection for files and directories."""

    def test_single_file(self, tmp_path: Path) -> None:
        """Single file should use file detection."""
        test_file = tmp_path / "main.py"
        test_file.write_text("x = 1")

        domain, tags = detect_domain(str(test_file))
        assert domain == Domain.BACKEND
        assert "python" in tags

    def test_directory_with_python_files(self, tmp_path: Path) -> None:
        """Directory with Python files should detect backend domain."""
        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "utils.py").write_text("y = 2")
        (tmp_path / "README.md").write_text("# Readme")

        domain, tags = detect_domain(str(tmp_path))
        assert domain == Domain.BACKEND
        assert "python" in tags
        assert "backend" in tags

    def test_directory_with_mixed_files(self, tmp_path: Path) -> None:
        """Directory with mixed files should return most common domain."""
        # 3 Python files
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("x = 2")
        (tmp_path / "c.py").write_text("x = 3")
        # 1 TypeScript file
        (tmp_path / "app.tsx").write_text("export default () => null")

        domain, tags = detect_domain(str(tmp_path))
        assert domain == Domain.BACKEND  # Python is more common
        # Tags should include both
        assert "python" in tags
        assert "typescript" in tags

    def test_directory_with_solidity(self, tmp_path: Path) -> None:
        """Directory with Solidity files should detect smart_contract domain."""
        contracts = tmp_path / "contracts"
        contracts.mkdir()
        (contracts / "Token.sol").write_text("pragma solidity ^0.8.0;")
        (contracts / "Vault.sol").write_text("pragma solidity ^0.8.0;")

        domain, tags = detect_domain(str(tmp_path))
        assert domain == Domain.SMART_CONTRACT
        assert "solidity" in tags
        assert "web3" in tags

    def test_directory_skips_node_modules(self, tmp_path: Path) -> None:
        """Should skip node_modules directory."""
        (tmp_path / "app.py").write_text("x = 1")
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        # Add many JS files in node_modules (should be ignored)
        for i in range(10):
            (node_modules / f"lib{i}.js").write_text("module.exports = {}")

        domain, tags = detect_domain(str(tmp_path))
        assert domain == Domain.BACKEND  # Python wins, node_modules ignored
        assert "python" in tags

    def test_directory_skips_hidden(self, tmp_path: Path) -> None:
        """Should skip hidden directories."""
        (tmp_path / "main.py").write_text("x = 1")
        hidden = tmp_path / ".git"
        hidden.mkdir()
        (hidden / "config").write_text("stuff")

        domain, tags = detect_domain(str(tmp_path))
        assert domain == Domain.BACKEND

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory should return unknown."""
        domain, tags = detect_domain(str(tmp_path))
        assert domain == Domain.UNKNOWN
        assert "unknown" in tags

    def test_nonexistent_path(self) -> None:
        """Non-existent path should return unknown."""
        domain, tags = detect_domain("/nonexistent/path/xyz")
        assert domain == Domain.UNKNOWN
        assert "unknown" in tags


class TestDeduplicateFindings:
    """Test finding deduplication logic."""

    def test_no_duplicates_unchanged(self) -> None:
        """Unique findings should pass through unchanged."""
        findings = [
            ToolFinding(tool="ruff", rule="E501", severity=Severity.LOW, message="Line too long", location="file.py:10"),
            ToolFinding(tool="bandit", rule="B101", severity=Severity.MEDIUM, message="Use of assert", location="file.py:20"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 2

    def test_exact_duplicates_removed(self) -> None:
        """Exact duplicates should be removed."""
        findings = [
            ToolFinding(tool="ruff", rule="E501", severity=Severity.LOW, message="Line too long", location="file.py:10"),
            ToolFinding(tool="ruff", rule="E501", severity=Severity.LOW, message="Line too long", location="file.py:10"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1

    def test_same_location_same_message_keeps_higher_severity(self) -> None:
        """When same location and message, keep higher severity."""
        findings = [
            ToolFinding(tool="ruff", rule="E501", severity=Severity.LOW, message="Issue found", location="file.py:10"),
            ToolFinding(tool="bandit", rule="B101", severity=Severity.HIGH, message="Issue found", location="file.py:10"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert result[0].severity == Severity.HIGH

    def test_different_locations_not_deduplicated(self) -> None:
        """Same message at different locations should not be deduplicated."""
        findings = [
            ToolFinding(tool="ruff", rule="E501", severity=Severity.LOW, message="Line too long", location="file.py:10"),
            ToolFinding(tool="ruff", rule="E501", severity=Severity.LOW, message="Line too long", location="file.py:20"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 2

    def test_message_normalization(self) -> None:
        """Messages should be normalized (case-insensitive, stripped)."""
        findings = [
            ToolFinding(tool="ruff", rule="E501", severity=Severity.LOW, message="Line Too Long", location="file.py:10"),
            ToolFinding(tool="bandit", rule="B101", severity=Severity.MEDIUM, message="line too long  ", location="file.py:10"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        # Higher severity (MEDIUM) should be kept
        assert result[0].severity == Severity.MEDIUM

    def test_empty_list(self) -> None:
        """Empty list should return empty list."""
        result = deduplicate_findings([])
        assert result == []
