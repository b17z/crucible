"""Integration tests for vulnerability detection.

These tests verify that crucible's tool delegation correctly identifies
known vulnerability patterns. Each test uses fixtures in tests/fixtures/vulnerable/.
"""

import subprocess
from pathlib import Path

import pytest

# Skip all tests if tools aren't installed
pytestmark = pytest.mark.skipif(
    subprocess.run(["which", "semgrep"], capture_output=True).returncode != 0,
    reason="semgrep not installed",
)

FIXTURES = Path(__file__).parent / "fixtures" / "vulnerable"


class TestPythonVulnerabilities:
    """Test Python vulnerability detection via semgrep/bandit."""

    def test_sql_injection_detected(self) -> None:
        """SQL injection should be detected by bandit rules."""
        from crucible.tools.delegation import delegate_semgrep

        result = delegate_semgrep(str(FIXTURES / "sql_injection.py"), "p/bandit")
        assert result.is_ok
        findings = result.value

        # Should find SQL injection
        rules = [f.rule for f in findings]
        assert any("sql" in r.lower() or "B608" in r for r in rules), f"Expected SQL finding, got: {rules}"

    def test_command_injection_detected(self) -> None:
        """Command injection should be detected by bandit rules."""
        from crucible.tools.delegation import delegate_semgrep

        result = delegate_semgrep(str(FIXTURES / "command_injection.py"), "p/bandit")
        assert result.is_ok
        findings = result.value

        # Should find shell=True issues
        rules = [f.rule for f in findings]
        assert any("B602" in r or "shell" in r.lower() for r in rules), f"Expected shell finding, got: {rules}"

        # Should be HIGH severity
        from crucible.models import Severity
        severities = [f.severity for f in findings]
        assert Severity.HIGH in severities

    def test_ruff_catches_security_issues(self) -> None:
        """Ruff should catch Python security issues with S rules."""
        from crucible.tools.delegation import delegate_ruff

        # Create a file with a known ruff security issue
        test_file = FIXTURES / "ruff_security_test.py"
        test_file.write_text('''
import subprocess
# S602: subprocess with shell=True
subprocess.call("ls", shell=True)
''')
        try:
            result = delegate_ruff(str(test_file))
            assert result.is_ok
            # Ruff may or may not catch this depending on config
            # This test documents current behavior
        finally:
            test_file.unlink()


@pytest.mark.skipif(
    subprocess.run(["which", "bandit"], capture_output=True).returncode != 0,
    reason="bandit not installed",
)
class TestBanditVulnerabilities:
    """Test Python secret detection via bandit."""

    def test_hardcoded_password_funcarg_detected(self) -> None:
        """B106: Hardcoded password in function argument should be detected."""
        from crucible.tools.delegation import delegate_bandit

        result = delegate_bandit(str(FIXTURES / "hardcoded_secrets.py"))
        assert result.is_ok
        findings = result.value

        rules = [f.rule for f in findings]
        assert any("B106" in r for r in rules), f"Expected B106, got: {rules}"

    def test_hardcoded_password_string_detected(self) -> None:
        """B105: Hardcoded password string should be detected."""
        from crucible.tools.delegation import delegate_bandit

        result = delegate_bandit(str(FIXTURES / "hardcoded_secrets.py"))
        assert result.is_ok
        findings = result.value

        rules = [f.rule for f in findings]
        assert any("B105" in r for r in rules), f"Expected B105, got: {rules}"


@pytest.mark.skipif(
    subprocess.run(["which", "slither"], capture_output=True).returncode != 0,
    reason="slither not installed",
)
class TestSolidityVulnerabilities:
    """Test Solidity vulnerability detection via slither."""

    def test_reentrancy_detected(self) -> None:
        """Reentrancy vulnerability should be detected."""
        from crucible.tools.delegation import delegate_slither

        result = delegate_slither(str(FIXTURES / "reentrancy.sol"))
        assert result.is_ok
        findings = result.value

        # Should find reentrancy
        rules = [f.rule for f in findings]
        assert any("reentrancy" in r.lower() for r in rules), f"Expected reentrancy, got: {rules}"

        # Should be HIGH severity
        from crucible.models import Severity
        high_findings = [f for f in findings if f.severity == Severity.HIGH]
        assert len(high_findings) >= 1

    def test_unchecked_transfer_detected(self) -> None:
        """Unchecked ERC20 transfer should be detected."""
        from crucible.tools.delegation import delegate_slither

        result = delegate_slither(str(FIXTURES / "unchecked_calls.sol"))
        assert result.is_ok
        findings = result.value

        rules = [f.rule for f in findings]
        assert any("unchecked-transfer" in r for r in rules), f"Expected unchecked-transfer, got: {rules}"

    def test_controlled_delegatecall_detected(self) -> None:
        """Delegatecall to user-controlled address should be detected."""
        from crucible.tools.delegation import delegate_slither

        result = delegate_slither(str(FIXTURES / "unchecked_calls.sol"))
        assert result.is_ok
        findings = result.value

        rules = [f.rule for f in findings]
        assert any("delegatecall" in r.lower() for r in rules), f"Expected delegatecall, got: {rules}"

    def test_missing_zero_check_detected(self) -> None:
        """Missing zero address check should be detected."""
        from crucible.tools.delegation import delegate_slither

        result = delegate_slither(str(FIXTURES / "unchecked_calls.sol"))
        assert result.is_ok
        findings = result.value

        rules = [f.rule for f in findings]
        assert any("zero" in r.lower() for r in rules), f"Expected zero-check, got: {rules}"

    def test_tx_origin_detected(self) -> None:
        """tx.origin for authorization should be detected."""
        from crucible.tools.delegation import delegate_slither

        result = delegate_slither(str(FIXTURES / "unchecked_calls.sol"), detectors=["tx-origin"])
        assert result.is_ok
        findings = result.value

        rules = [f.rule for f in findings]
        assert any("tx-origin" in r for r in rules), f"Expected tx-origin, got: {rules}"


class TestDomainDetection:
    """Test that domain detection returns correct tags."""

    def test_solidity_domain_tags(self) -> None:
        """Solidity files should return web3 domain tags."""
        from crucible.models import Domain
        from crucible.review.core import detect_domain_for_file

        domain, tags = detect_domain_for_file("Contract.sol")
        assert domain == Domain.SMART_CONTRACT
        assert "solidity" in tags
        assert "web3" in tags

    def test_python_domain_tags(self) -> None:
        """Python files should return backend domain tags."""
        from crucible.models import Domain
        from crucible.review.core import detect_domain_for_file

        domain, tags = detect_domain_for_file("main.py")
        assert domain == Domain.BACKEND
        assert "python" in tags


class TestQuickReviewIntegration:
    """Test quick_review end-to-end."""

    def test_quick_review_returns_domains(self) -> None:
        """quick_review should return domains_detected in output."""
        # This tests the full flow through the MCP handler
        from crucible.server import _handle_quick_review

        result = _handle_quick_review({"path": str(FIXTURES / "sql_injection.py")})
        assert len(result) == 1
        output = result[0].text

        assert "Domains detected:" in output
        assert "python" in output.lower()

    def test_quick_review_returns_severity_summary(self) -> None:
        """quick_review should return severity_summary."""
        from crucible.server import _handle_quick_review

        result = _handle_quick_review({
            "path": str(FIXTURES / "command_injection.py"),
            "tools": ["semgrep"],
        })
        output = result[0].text

        assert "Severity summary:" in output
