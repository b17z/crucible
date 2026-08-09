"""Tests for tool delegation."""

import subprocess

from crucible.models import Domain, Severity
from crucible.tools.delegation import (
    _check_tool_run,
    _severity_from_ruff,
    _severity_from_semgrep,
    _validate_path,
    check_all_tools,
    check_tool,
    delegate_semgrep,
    get_semgrep_config,
)


def _make_result(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    """Build a synthetic CompletedProcess for _check_tool_run tests."""
    return subprocess.CompletedProcess(
        args=["fake-tool"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
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


class TestToolRunCheck:
    """Distinguish a successful no-findings run from a pre-arg-parse crash."""

    def test_exit_zero_with_json_is_ok(self) -> None:
        """Successful scan with no findings — exit 0, JSON body present."""
        result = _make_result(0, stdout='{"results": []}\n')
        check = _check_tool_run("semgrep", result, success_codes=(0, 1))
        assert check.is_ok

    def test_exit_one_with_json_is_ok(self) -> None:
        """Scan with findings — exit 1 is a success code for many tools."""
        result = _make_result(1, stdout='{"results": [{"check_id": "x"}]}\n')
        check = _check_tool_run("semgrep", result, success_codes=(0, 1))
        assert check.is_ok

    def test_exit_one_with_empty_stdout_is_err(self) -> None:
        """Regression: pre-arg-parse crash (exit 1, empty stdout) is failure.

        This is the silent-crash bug that hid an opentelemetry ImportError in
        semgrep behind a fake 'no findings' result.
        """
        result = _make_result(1, stdout="", stderr="ImportError: cannot import name 'LogData'")
        check = _check_tool_run("semgrep", result, success_codes=(0, 1))
        assert check.is_err
        assert "no output" in check.error.lower() or "crash" in check.error.lower()
        assert "ImportError" in check.error  # stderr must surface

    def test_exit_two_is_err(self) -> None:
        """Exit code outside success_codes is failure regardless of stdout."""
        result = _make_result(2, stdout='{"results": []}', stderr="parse error")
        check = _check_tool_run("bandit", result, success_codes=(0, 1))
        assert check.is_err
        assert "bandit failed" in check.error
        assert "parse error" in check.error

    def test_slither_tight_predicate(self) -> None:
        """Slither uses success_codes=(0,) — exit 1 should error."""
        result = _make_result(1, stdout="", stderr="solc not found")
        check = _check_tool_run("slither", result, success_codes=(0,))
        assert check.is_err

    def test_zero_with_empty_stdout_is_ok(self) -> None:
        """Exit 0 with empty stdout shouldn't error — some tools emit nothing
        on a clean run. Only non-zero + empty triggers the crash heuristic."""
        result = _make_result(0, stdout="", stderr="")
        check = _check_tool_run("ruff", result, success_codes=(0, 1))
        assert check.is_ok

    def test_stderr_truncation(self) -> None:
        """Long stderr is truncated to keep error messages manageable."""
        long_stderr = "X" * 2000
        result = _make_result(99, stdout="", stderr=long_stderr)
        check = _check_tool_run("tool", result, success_codes=(0,))
        assert check.is_err
        # Truncation cap is 500 chars; the error message has surrounding text
        # but the stderr portion must be bounded.
        assert len(check.error) < 800


class TestToolFindingSuppression:
    def test_defaults_unsuppressed(self) -> None:
        from crucible.models import Severity, ToolFinding

        f = ToolFinding(tool="bandit", rule="B101", severity=Severity.LOW,
                        message="assert used", location="tests/test_x.py:3")
        assert f.suppressed is False
        assert f.suppression_reason is None

    def test_replace_marks_suppressed(self) -> None:
        import dataclasses

        from crucible.models import Severity, ToolFinding

        f = ToolFinding(tool="bandit", rule="B101", severity=Severity.LOW,
                        message="assert used", location="tests/test_x.py:3")
        marked = dataclasses.replace(f, suppressed=True,
                                     suppression_reason="verifier:is_test_file — pytest asserts")
        assert marked.suppressed is True
        assert "is_test_file" in marked.suppression_reason
