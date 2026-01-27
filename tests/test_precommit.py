"""Tests for pre-commit hook functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from crucible.hooks.precommit import (
    PrecommitConfig,
    PrecommitResult,
    _detect_domain_from_path,
    _filter_findings_to_staged,
    _get_tools_for_file,
    _parse_severity,
    _severity_meets_threshold,
    _should_exclude,
    check_sensitive_files,
    format_precommit_output,
    load_precommit_config,
)
from crucible.models import Domain, Severity, ToolFinding
from crucible.tools.git import GitChange, GitContext, LineRange


class TestSensitiveFileDetection:
    """Test built-in secrets/sensitive file detection."""

    def test_detects_env_file(self) -> None:
        findings = check_sensitive_files([".env"])
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL
        assert findings[0].rule == "sensitive-file"

    def test_detects_env_local(self) -> None:
        findings = check_sensitive_files([".env.local"])
        assert len(findings) == 1
        assert "Environment file" in findings[0].message

    def test_detects_env_production(self) -> None:
        findings = check_sensitive_files([".env.production"])
        assert len(findings) == 1

    def test_skips_env_example(self) -> None:
        findings = check_sensitive_files([".env.example"])
        assert len(findings) == 0

    def test_detects_pem_file(self) -> None:
        findings = check_sensitive_files(["server.pem", "cert.key"])
        assert len(findings) == 2

    def test_detects_ssh_keys(self) -> None:
        findings = check_sensitive_files(["id_rsa", "id_ed25519", ".ssh/id_ecdsa"])
        assert len(findings) == 3

    def test_detects_keystore(self) -> None:
        findings = check_sensitive_files(["wallet.keystore", "my.keyfile"])
        assert len(findings) == 2

    def test_detects_credentials_json(self) -> None:
        findings = check_sensitive_files([
            "credentials.json",
            "secrets.json",
            "service-account.json",
        ])
        assert len(findings) == 3

    def test_detects_secret_files(self) -> None:
        findings = check_sensitive_files(["app.secret", "config.secrets"])
        assert len(findings) == 2

    def test_ignores_safe_files(self) -> None:
        findings = check_sensitive_files([
            "main.py",
            "config.json",
            "README.md",
            "package.json",
        ])
        assert len(findings) == 0

    def test_case_insensitive_keystore(self) -> None:
        findings = check_sensitive_files(["MyKeyStore.json", "KEYSTORE"])
        assert len(findings) == 2


class TestPrecommitConfig:
    """Test configuration loading and parsing."""

    def test_default_config(self) -> None:
        config = PrecommitConfig()
        assert config.fail_on == Severity.HIGH
        assert config.timeout == 120
        assert config.exclude == ()
        assert config.secrets_tool == "auto"

    def test_parse_severity(self) -> None:
        assert _parse_severity("critical") == Severity.CRITICAL
        assert _parse_severity("HIGH") == Severity.HIGH
        assert _parse_severity("Medium") == Severity.MEDIUM
        assert _parse_severity("low") == Severity.LOW
        assert _parse_severity("info") == Severity.INFO
        assert _parse_severity("unknown") == Severity.HIGH  # default

    def test_load_config_defaults_when_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_precommit_config(tmpdir)
            assert config.fail_on == Severity.HIGH
            assert config.timeout == 120

    def test_load_config_from_project_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".crucible"
            config_dir.mkdir()
            config_file = config_dir / "precommit.yaml"
            config_file.write_text("""
fail_on: medium
timeout: 60
exclude:
  - "*.md"
  - "tests/**"
verbose: true
secrets_tool: gitleaks
""")
            config = load_precommit_config(tmpdir)
            assert config.fail_on == Severity.MEDIUM
            assert config.timeout == 60
            assert "*.md" in config.exclude
            assert "tests/**" in config.exclude
            assert config.verbose is True
            assert config.secrets_tool == "gitleaks"

    def test_load_config_backwards_compat_skip_secrets(self) -> None:
        """Test that old skip_secrets_check config still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".crucible"
            config_dir.mkdir()
            config_file = config_dir / "precommit.yaml"
            config_file.write_text("""
skip_secrets_check: true
""")
            config = load_precommit_config(tmpdir)
            assert config.secrets_tool == "none"

    def test_load_config_secrets_tool_options(self) -> None:
        """Test all secrets_tool options."""
        for tool_option in ["auto", "gitleaks", "builtin", "none"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                config_dir = Path(tmpdir) / ".crucible"
                config_dir.mkdir()
                config_file = config_dir / "precommit.yaml"
                config_file.write_text(f"secrets_tool: {tool_option}")
                config = load_precommit_config(tmpdir)
                assert config.secrets_tool == tool_option

    def test_load_config_with_tools_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".crucible"
            config_dir.mkdir()
            config_file = config_dir / "precommit.yaml"
            config_file.write_text("""
tools:
  solidity: [semgrep]
  python: [ruff]
""")
            config = load_precommit_config(tmpdir)
            assert Domain.SMART_CONTRACT in config.tools
            assert config.tools[Domain.SMART_CONTRACT] == ["semgrep"]
            assert Domain.BACKEND in config.tools
            assert config.tools[Domain.BACKEND] == ["ruff"]


class TestDomainDetection:
    """Test domain detection from file paths."""

    def test_solidity_detection(self) -> None:
        domain, tags = _detect_domain_from_path("Contract.sol")
        assert domain == Domain.SMART_CONTRACT
        assert "solidity" in tags

    def test_vyper_detection(self) -> None:
        domain, tags = _detect_domain_from_path("contract.vy")
        assert domain == Domain.SMART_CONTRACT
        assert "vyper" in tags

    def test_python_detection(self) -> None:
        domain, tags = _detect_domain_from_path("main.py")
        assert domain == Domain.BACKEND
        assert "python" in tags

    def test_typescript_detection(self) -> None:
        domain, tags = _detect_domain_from_path("App.tsx")
        assert domain == Domain.FRONTEND
        assert "typescript" in tags

    def test_javascript_detection(self) -> None:
        domain, tags = _detect_domain_from_path("index.js")
        assert domain == Domain.FRONTEND
        assert "javascript" in tags

    def test_go_detection(self) -> None:
        domain, tags = _detect_domain_from_path("main.go")
        assert domain == Domain.BACKEND
        assert "go" in tags

    def test_rust_detection(self) -> None:
        domain, tags = _detect_domain_from_path("lib.rs")
        assert domain == Domain.BACKEND
        assert "rust" in tags

    def test_terraform_detection(self) -> None:
        domain, tags = _detect_domain_from_path("main.tf")
        assert domain == Domain.INFRASTRUCTURE

    def test_yaml_detection(self) -> None:
        domain, tags = _detect_domain_from_path("config.yaml")
        assert domain == Domain.INFRASTRUCTURE

    def test_unknown_extension(self) -> None:
        domain, tags = _detect_domain_from_path("README.md")
        assert domain == Domain.UNKNOWN
        assert tags == []


class TestToolSelection:
    """Test tool selection based on domain and config."""

    def test_default_tools_for_solidity(self) -> None:
        config = PrecommitConfig()
        tools = _get_tools_for_file("Contract.sol", config)
        assert "slither" in tools
        assert "semgrep" in tools

    def test_default_tools_for_python(self) -> None:
        config = PrecommitConfig()
        tools = _get_tools_for_file("main.py", config)
        assert "ruff" in tools
        assert "bandit" in tools
        assert "semgrep" in tools

    def test_default_tools_for_frontend(self) -> None:
        config = PrecommitConfig()
        tools = _get_tools_for_file("App.tsx", config)
        assert "semgrep" in tools
        assert "slither" not in tools

    def test_config_override_tools(self) -> None:
        config = PrecommitConfig(
            tools={Domain.SMART_CONTRACT: ["semgrep"]}
        )
        tools = _get_tools_for_file("Contract.sol", config)
        assert tools == ["semgrep"]
        assert "slither" not in tools

    def test_skip_tools(self) -> None:
        config = PrecommitConfig(skip_tools=("slither",))
        tools = _get_tools_for_file("Contract.sol", config)
        assert "slither" not in tools
        assert "semgrep" in tools


class TestExcludePatterns:
    """Test file exclusion patterns."""

    def test_exclude_markdown(self) -> None:
        assert _should_exclude("README.md", ("*.md",)) is True
        assert _should_exclude("docs/guide.md", ("*.md",)) is True

    def test_exclude_directory_pattern(self) -> None:
        assert _should_exclude("tests/test_foo.py", ("tests/**",)) is True
        assert _should_exclude("src/main.py", ("tests/**",)) is False

    def test_no_exclusions(self) -> None:
        assert _should_exclude("main.py", ()) is False

    def test_multiple_patterns(self) -> None:
        patterns = ("*.md", "*.json", "tests/**")
        assert _should_exclude("README.md", patterns) is True
        assert _should_exclude("package.json", patterns) is True
        assert _should_exclude("tests/test.py", patterns) is True
        assert _should_exclude("src/main.py", patterns) is False


class TestSeverityThreshold:
    """Test severity threshold comparison."""

    def test_critical_meets_all(self) -> None:
        assert _severity_meets_threshold(Severity.CRITICAL, Severity.CRITICAL) is True
        assert _severity_meets_threshold(Severity.CRITICAL, Severity.HIGH) is True
        assert _severity_meets_threshold(Severity.CRITICAL, Severity.INFO) is True

    def test_high_meets_high_and_below(self) -> None:
        assert _severity_meets_threshold(Severity.HIGH, Severity.CRITICAL) is False
        assert _severity_meets_threshold(Severity.HIGH, Severity.HIGH) is True
        assert _severity_meets_threshold(Severity.HIGH, Severity.MEDIUM) is True

    def test_info_only_meets_info(self) -> None:
        assert _severity_meets_threshold(Severity.INFO, Severity.CRITICAL) is False
        assert _severity_meets_threshold(Severity.INFO, Severity.HIGH) is False
        assert _severity_meets_threshold(Severity.INFO, Severity.INFO) is True


class TestFilterFindingsToStaged:
    """Test filtering findings to staged line ranges."""

    def test_includes_findings_in_range(self) -> None:
        findings = [
            ToolFinding(
                tool="test",
                rule="R001",
                severity=Severity.HIGH,
                message="Issue",
                location="test.py:5",
            ),
        ]
        context = GitContext(
            mode="staged",
            base_ref=None,
            changes=(
                GitChange(
                    path="test.py",
                    status="M",
                    added_lines=(LineRange(1, 10),),
                ),
            ),
        )
        filtered = _filter_findings_to_staged(findings, context)
        assert len(filtered) == 1

    def test_excludes_findings_outside_range(self) -> None:
        findings = [
            ToolFinding(
                tool="test",
                rule="R001",
                severity=Severity.HIGH,
                message="Issue",
                location="test.py:100",
            ),
        ]
        context = GitContext(
            mode="staged",
            base_ref=None,
            changes=(
                GitChange(
                    path="test.py",
                    status="M",
                    added_lines=(LineRange(1, 10),),
                ),
            ),
        )
        filtered = _filter_findings_to_staged(findings, context)
        assert len(filtered) == 0

    def test_handles_no_line_number(self) -> None:
        """Findings without line numbers should match by file."""
        findings = [
            ToolFinding(
                tool="crucible",
                rule="sensitive-file",
                severity=Severity.CRITICAL,
                message="Bad file",
                location="secrets.json",  # No line number
            ),
        ]
        context = GitContext(
            mode="staged",
            base_ref=None,
            changes=(
                GitChange(
                    path="secrets.json",
                    status="A",
                    added_lines=(LineRange(1, 10),),
                ),
            ),
        )
        filtered = _filter_findings_to_staged(findings, context)
        assert len(filtered) == 1

    def test_handles_context_lines(self) -> None:
        findings = [
            ToolFinding(
                tool="test",
                rule="R001",
                severity=Severity.HIGH,
                message="Issue",
                location="test.py:15",  # Within 5 lines of range end
            ),
        ]
        context = GitContext(
            mode="staged",
            base_ref=None,
            changes=(
                GitChange(
                    path="test.py",
                    status="M",
                    added_lines=(LineRange(10, 10),),
                ),
            ),
        )
        # Without context
        filtered = _filter_findings_to_staged(findings, context, include_context=False)
        assert len(filtered) == 0

        # With context (5 lines)
        filtered = _filter_findings_to_staged(findings, context, include_context=True)
        assert len(filtered) == 1


class TestPrecommitResult:
    """Test PrecommitResult formatting."""

    def test_format_no_findings(self) -> None:
        result = PrecommitResult(
            passed=True,
            findings=(),
            blocked_files=(),
            severity_counts={},
            files_checked=5,
        )
        output = format_precommit_output(result)
        assert "5 file(s)" in output
        assert "no issues found" in output

    def test_format_blocked_files(self) -> None:
        result = PrecommitResult(
            passed=False,
            findings=(
                ToolFinding(
                    tool="crucible",
                    rule="sensitive-file",
                    severity=Severity.CRITICAL,
                    message="Bad file",
                    location=".env",
                ),
            ),
            blocked_files=(".env",),
            severity_counts={"critical": 1},
            files_checked=1,
        )
        output = format_precommit_output(result)
        assert "BLOCKED" in output
        assert ".env" in output
        assert "FAILED" in output

    def test_format_findings_compact(self) -> None:
        result = PrecommitResult(
            passed=False,
            findings=(
                ToolFinding(
                    tool="bandit",
                    rule="B602",
                    severity=Severity.HIGH,
                    message="shell=True is dangerous",
                    location="test.py:10",
                ),
            ),
            blocked_files=(),
            severity_counts={"high": 1},
            files_checked=1,
        )
        output = format_precommit_output(result, verbose=False)
        assert "[HIGH]" in output
        assert "B602" in output

    def test_format_findings_verbose(self) -> None:
        result = PrecommitResult(
            passed=False,
            findings=(
                ToolFinding(
                    tool="bandit",
                    rule="B602",
                    severity=Severity.HIGH,
                    message="shell=True is dangerous",
                    location="test.py:10",
                    suggestion="Use shell=False",
                ),
                ToolFinding(
                    tool="ruff",
                    rule="E501",
                    severity=Severity.LOW,
                    message="Line too long",
                    location="test.py:20",
                ),
            ),
            blocked_files=(),
            severity_counts={"high": 1, "low": 1},
            files_checked=1,
        )
        output = format_precommit_output(result, verbose=True)
        assert "[HIGH]" in output
        assert "[LOW]" in output
        assert "Fix: Use shell=False" in output

    def test_format_passed_below_threshold(self) -> None:
        result = PrecommitResult(
            passed=True,
            findings=(
                ToolFinding(
                    tool="ruff",
                    rule="E501",
                    severity=Severity.LOW,
                    message="Line too long",
                    location="test.py:10",
                ),
            ),
            blocked_files=(),
            severity_counts={"low": 1},
            files_checked=1,
        )
        output = format_precommit_output(result)
        assert "PASSED" in output
        assert "below threshold" in output

    def test_format_error(self) -> None:
        result = PrecommitResult(
            passed=False,
            findings=(),
            blocked_files=(),
            severity_counts={},
            files_checked=0,
            error="Git command failed",
        )
        output = format_precommit_output(result)
        assert "Error:" in output
        assert "Git command failed" in output


class TestSensitivePatternCoverage:
    """Ensure all sensitive file patterns work correctly."""

    @pytest.mark.parametrize("filename,should_block", [
        # Environment files
        (".env", True),
        (".env.local", True),
        (".env.development", True),
        (".env.production", True),
        (".envrc", True),
        (".env.example", False),  # Examples are OK
        ("env.local.example", False),
        # Private keys
        ("server.pem", True),
        ("private.key", True),
        ("cert.p12", True),
        ("keystore.pfx", True),
        ("java.jks", True),
        ("public.pem", True),  # Still blocked (could be private)
        # SSH keys
        ("id_rsa", True),
        ("id_ed25519", True),
        ("id_ecdsa", True),
        ("id_dsa", True),
        (".ssh/id_rsa", True),
        ("home/user/.ssh/id_ed25519", True),
        ("id_rsa.pub", False),  # Public key is OK
        # Keystores
        ("keystore.json", True),
        ("my.keyfile", True),
        ("wallet-keystore", True),
        # Credentials
        ("credentials.json", True),
        ("google-credentials.json", True),
        ("secrets.json", True),
        ("service-account.json", True),
        ("service-account-prod.json", True),
        # Generic secrets
        ("app.secret", True),
        ("config.secrets", True),
        (".secret", True),
        # Safe files
        ("main.py", False),
        ("package.json", False),
        ("config.yaml", False),
        ("README.md", False),
    ])
    def test_sensitive_file_pattern(self, filename: str, should_block: bool) -> None:
        findings = check_sensitive_files([filename])
        if should_block:
            assert len(findings) == 1, f"Expected {filename} to be blocked"
        else:
            assert len(findings) == 0, f"Expected {filename} to be allowed"
