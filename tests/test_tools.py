"""Tests for tool delegation."""

from crucible.models import Domain, Severity
from crucible.tools.delegation import (
    _severity_from_ruff,
    _severity_from_semgrep,
    _validate_path,
    check_all_tools,
    check_tool,
    delegate_semgrep,
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


class TestCheckAllTools:
    """Test checking all supported tools."""

    def test_returns_all_tools(self) -> None:
        statuses = check_all_tools()
        assert "semgrep" in statuses
        assert "ruff" in statuses
        assert "slither" in statuses
        assert "bandit" in statuses
        assert "gitleaks" in statuses

    def test_each_status_has_name(self) -> None:
        statuses = check_all_tools()
        for name, status in statuses.items():
            assert status.name == name


class TestPathValidation:
    """Test path validation to prevent argument injection."""

    def test_valid_path(self, tmp_path) -> None:
        """Valid existing path should pass."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")
        result = _validate_path(str(test_file))
        assert result.is_ok

    def test_empty_path_rejected(self) -> None:
        """Empty path should be rejected."""
        result = _validate_path("")
        assert result.is_err
        assert "empty" in result.error.lower()

    def test_dash_prefix_rejected(self) -> None:
        """Path starting with '-' should be rejected (argument injection)."""
        result = _validate_path("-rf")
        assert result.is_err
        assert "cannot start with '-'" in result.error

        result = _validate_path("--help")
        assert result.is_err
        assert "cannot start with '-'" in result.error

    def test_nonexistent_path_rejected(self) -> None:
        """Non-existent path should be rejected."""
        result = _validate_path("/nonexistent/path/xyz123")
        assert result.is_err
        assert "does not exist" in result.error

    def test_delegate_rejects_bad_path(self) -> None:
        """Delegation functions should reject invalid paths."""
        result = delegate_semgrep("--help")
        assert result.is_err
        assert "cannot start with '-'" in result.error
