"""Tests for tool delegation."""

from crucible.models import Domain, Severity
from crucible.tools.delegation import (
    _severity_from_ruff,
    _severity_from_semgrep,
    check_tool,
    get_semgrep_config,
)


class TestSemgrepConfig:
    """Test domain-aware semgrep config selection."""

    def test_smart_contract_config(self) -> None:
        config = get_semgrep_config(Domain.SMART_CONTRACT)
        assert "smart-contracts" in config or "solidity" in config

    def test_frontend_config(self) -> None:
        config = get_semgrep_config(Domain.FRONTEND)
        assert "javascript" in config or "react" in config

    def test_backend_config(self) -> None:
        config = get_semgrep_config(Domain.BACKEND)
        assert "python" in config or "golang" in config

    def test_unknown_config(self) -> None:
        config = get_semgrep_config(Domain.UNKNOWN)
        assert config == "auto"


class TestToolCheck:
    """Test tool availability checking."""

    def test_check_installed_tool(self) -> None:
        # Python is always available
        status = check_tool("python")
        assert status.installed is True
        assert status.path is not None

    def test_check_missing_tool(self) -> None:
        status = check_tool("definitely-not-a-real-tool-12345")
        assert status.installed is False
        assert status.path is None


class TestSeverityMapping:
    """Test severity normalization across tools."""

    def test_semgrep_error_is_high(self) -> None:
        assert _severity_from_semgrep("ERROR") == Severity.HIGH

    def test_semgrep_warning_is_medium(self) -> None:
        assert _severity_from_semgrep("WARNING") == Severity.MEDIUM

    def test_semgrep_info_is_info(self) -> None:
        assert _severity_from_semgrep("INFO") == Severity.INFO

    def test_semgrep_unknown_defaults_to_info(self) -> None:
        assert _severity_from_semgrep("UNKNOWN") == Severity.INFO

    def test_ruff_security_is_high(self) -> None:
        # S1xx = high security issues
        assert _severity_from_ruff("S101") == Severity.HIGH

    def test_ruff_security_other_is_medium(self) -> None:
        # S2xx, S3xx, etc = medium security
        assert _severity_from_ruff("S201") == Severity.MEDIUM

    def test_ruff_bugbear_is_medium(self) -> None:
        assert _severity_from_ruff("B001") == Severity.MEDIUM

    def test_ruff_style_is_low(self) -> None:
        # E, W, I = style/formatting
        assert _severity_from_ruff("E501") == Severity.LOW
        assert _severity_from_ruff("W291") == Severity.LOW
        assert _severity_from_ruff("I001") == Severity.LOW
