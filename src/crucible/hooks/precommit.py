"""Pre-commit hook implementation."""

import os
import re
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

import yaml

from crucible.errors import Result
from crucible.models import Domain, Severity, ToolFinding
from crucible.tools.delegation import (
    check_tool,
    delegate_bandit,
    delegate_gitleaks,
    delegate_ruff,
    delegate_semgrep,
    delegate_slither,
    get_semgrep_config,
)
from crucible.tools.git import (
    GitContext,
    get_changed_files,
    get_repo_root,
    get_staged_changes,
)

# Config locations (cascade: project > user)
CONFIG_PROJECT = Path(".crucible") / "precommit.yaml"
CONFIG_USER = Path.home() / ".claude" / "crucible" / "precommit.yaml"

# Default tool selection by domain
DEFAULT_TOOLS: dict[Domain, list[str]] = {
    Domain.SMART_CONTRACT: ["slither", "semgrep"],
    Domain.BACKEND: ["ruff", "bandit", "semgrep"],
    Domain.FRONTEND: ["semgrep"],
    Domain.INFRASTRUCTURE: ["semgrep"],
    Domain.UNKNOWN: ["semgrep"],
}

# Severity ordering for threshold comparison
SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}

# =============================================================================
# Secrets Detection (built-in, no external tool needed)
# =============================================================================

# Patterns for sensitive files that should never be committed
SENSITIVE_FILE_PATTERNS = [
    # Environment files
    (r"\.env$", "Environment file"),
    (r"\.env\.[^.]+$", "Environment file"),  # .env.local, .env.production
    (r"\.envrc$", "direnv file"),
    # Private keys and certificates
    (r"\.(pem|key|p12|pfx|jks)$", "Private key/certificate"),
    # SSH keys
    (r"(^|/)id_(rsa|ed25519|ecdsa|dsa)$", "SSH private key"),
    # Keystores (crypto wallets)
    (r"keystore", "Keystore file"),
    (r"\.keyfile$", "Key file"),
    # Credentials files
    (r"credentials.*\.json$", "Credentials file"),
    (r"secrets.*\.json$", "Secrets file"),
    (r"service.account.*\.json$", "Service account file"),
    # Generic secrets
    (r"\.(secret|secrets)$", "Secret file"),
]

# Compile patterns for performance
_SENSITIVE_PATTERNS = [(re.compile(p, re.IGNORECASE), desc) for p, desc in SENSITIVE_FILE_PATTERNS]


def check_sensitive_files(file_paths: list[str]) -> list[ToolFinding]:
    """Check for sensitive files that shouldn't be committed."""
    findings: list[ToolFinding] = []

    for file_path in file_paths:
        # Skip .example files
        if file_path.endswith(".example"):
            continue

        for pattern, description in _SENSITIVE_PATTERNS:
            if pattern.search(file_path):
                findings.append(
                    ToolFinding(
                        tool="crucible",
                        rule="sensitive-file",
                        severity=Severity.CRITICAL,
                        message=f"{description} should not be committed: {file_path}",
                        location=file_path,
                        suggestion="Add to .gitignore or use .example suffix",
                    )
                )
                break  # One match per file is enough

    return findings


# =============================================================================
# Configuration
# =============================================================================

@dataclass(frozen=True)
class PrecommitConfig:
    """Pre-commit hook configuration."""

    fail_on: Severity = Severity.HIGH
    timeout: int = 120
    exclude: tuple[str, ...] = ()
    include_context: bool = False
    # Per-domain tool overrides
    tools: dict[Domain, list[str]] = field(default_factory=dict)
    # Skip specific tools globally
    skip_tools: tuple[str, ...] = ()
    # Verbose output
    verbose: bool = False
    # Secrets detection: "auto" (gitleaks if available, else builtin), "gitleaks", "builtin", or "none"
    secrets_tool: str = "auto"


@dataclass(frozen=True)
class PrecommitResult:
    """Result of a pre-commit check."""

    passed: bool
    findings: tuple[ToolFinding, ...]
    blocked_files: tuple[str, ...]  # Files blocked by secrets check
    severity_counts: dict[str, int]
    files_checked: int
    error: str | None = None


def load_precommit_config(repo_path: str | None = None) -> PrecommitConfig:
    """Load pre-commit config with cascade priority."""
    config_data: dict = {}

    # Try project-level first
    project_config = Path(repo_path) / CONFIG_PROJECT if repo_path else CONFIG_PROJECT

    if project_config.exists():
        try:
            with open(project_config) as f:
                config_data = yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError):
            pass

    # Fall back to user-level
    if not config_data and CONFIG_USER.exists():
        try:
            with open(CONFIG_USER) as f:
                config_data = yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError):
            pass

    # Parse config
    fail_on_str = config_data.get("fail_on", "high").lower()
    fail_on = _parse_severity(fail_on_str)

    timeout = config_data.get("timeout", 120)
    exclude = tuple(config_data.get("exclude", []))
    include_context = config_data.get("include_context", False)
    skip_tools = tuple(config_data.get("skip_tools", []))
    verbose = config_data.get("verbose", False)

    # Handle secrets_tool config (supports old skip_secrets_check for backwards compat)
    if config_data.get("skip_secrets_check", False):
        secrets_tool = "none"
    else:
        secrets_tool = config_data.get("secrets_tool", "auto")

    # Parse per-domain tools
    tools: dict[Domain, list[str]] = {}
    tools_config = config_data.get("tools", {})
    for domain_str, tool_list in tools_config.items():
        try:
            domain = Domain(domain_str)
            tools[domain] = list(tool_list)
        except ValueError:
            domain = _domain_from_string(domain_str)
            if domain:
                tools[domain] = list(tool_list)

    return PrecommitConfig(
        fail_on=fail_on,
        timeout=timeout,
        exclude=exclude,
        include_context=include_context,
        tools=tools,
        skip_tools=skip_tools,
        verbose=verbose,
        secrets_tool=secrets_tool,
    )


def _parse_severity(s: str) -> Severity:
    """Parse severity string to Severity enum."""
    mapping = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }
    return mapping.get(s.lower(), Severity.HIGH)


def _domain_from_string(s: str) -> Domain | None:
    """Map common strings to Domain enum."""
    mapping = {
        "solidity": Domain.SMART_CONTRACT,
        "smart_contract": Domain.SMART_CONTRACT,
        "python": Domain.BACKEND,
        "backend": Domain.BACKEND,
        "frontend": Domain.FRONTEND,
        "react": Domain.FRONTEND,
        "typescript": Domain.FRONTEND,
        "infrastructure": Domain.INFRASTRUCTURE,
        "terraform": Domain.INFRASTRUCTURE,
    }
    return mapping.get(s.lower())


# =============================================================================
# Domain Detection & Tool Selection
# =============================================================================

def _detect_domain_from_path(path: str) -> tuple[Domain, list[str]]:
    """Detect domain from file path extension."""
    if path.endswith(".sol"):
        return Domain.SMART_CONTRACT, ["solidity", "smart_contract", "web3"]
    elif path.endswith(".vy"):
        return Domain.SMART_CONTRACT, ["vyper", "smart_contract", "web3"]
    elif path.endswith(".py"):
        return Domain.BACKEND, ["python", "backend"]
    elif path.endswith((".ts", ".tsx")):
        return Domain.FRONTEND, ["typescript", "frontend"]
    elif path.endswith((".js", ".jsx")):
        return Domain.FRONTEND, ["javascript", "frontend"]
    elif path.endswith(".go"):
        return Domain.BACKEND, ["go", "backend"]
    elif path.endswith(".rs"):
        return Domain.BACKEND, ["rust", "backend"]
    elif path.endswith((".tf", ".yaml", ".yml")):
        return Domain.INFRASTRUCTURE, ["infrastructure", "devops"]
    else:
        return Domain.UNKNOWN, []


def _get_tools_for_file(file_path: str, config: PrecommitConfig) -> list[str]:
    """Get the tools to run for a file based on its domain."""
    domain, _ = _detect_domain_from_path(file_path)

    if domain in config.tools:
        tools = config.tools[domain]
    else:
        tools = DEFAULT_TOOLS.get(domain, DEFAULT_TOOLS[Domain.UNKNOWN])

    return [t for t in tools if t not in config.skip_tools]


def _should_exclude(file_path: str, exclude_patterns: tuple[str, ...]) -> bool:
    """Check if a file should be excluded based on patterns."""
    return any(fnmatch(file_path, pattern) for pattern in exclude_patterns)


def _severity_meets_threshold(severity: Severity, threshold: Severity) -> bool:
    """Check if a severity meets or exceeds the threshold."""
    return SEVERITY_ORDER[severity] <= SEVERITY_ORDER[threshold]


# =============================================================================
# Finding Filtering
# =============================================================================

def _filter_findings_to_staged(
    findings: list[ToolFinding],
    context: GitContext,
    include_context: bool = False,
) -> list[ToolFinding]:
    """Filter findings to only those in staged lines."""
    changed_ranges: dict[str, list[tuple[int, int]]] = {}
    for change in context.changes:
        if change.status == "D":
            continue
        ranges = [(r.start, r.end) for r in change.added_lines]
        changed_ranges[change.path] = ranges

    context_lines = 5 if include_context else 0
    filtered: list[ToolFinding] = []

    for finding in findings:
        parts = finding.location.split(":")
        if len(parts) < 2:
            # No line number - include if file matches (e.g., sensitive file check)
            file_path = parts[0]
            for changed_file in changed_ranges:
                if file_path.endswith(changed_file) or changed_file.endswith(file_path):
                    filtered.append(finding)
                    break
            continue

        file_path = parts[0]
        try:
            line_num = int(parts[1])
        except ValueError:
            continue

        matching_file = None
        for changed_file in changed_ranges:
            if file_path.endswith(changed_file) or changed_file.endswith(file_path):
                matching_file = changed_file
                break

        if not matching_file:
            continue

        ranges = changed_ranges[matching_file]
        for start, end in ranges:
            if start - context_lines <= line_num <= end + context_lines:
                filtered.append(finding)
                break

    return filtered


# =============================================================================
# Main Entry Point
# =============================================================================

def run_precommit(
    repo_path: str | None = None,
    config: PrecommitConfig | None = None,
) -> PrecommitResult:
    """
    Run pre-commit checks on staged changes.

    Checks performed:
    1. Secrets/sensitive file detection (built-in, always runs first)
    2. Static analysis via delegated tools (semgrep, ruff, bandit, slither)

    Args:
        repo_path: Repository path (defaults to cwd)
        config: Pre-commit config (loads from file if not provided)

    Returns:
        PrecommitResult with pass/fail status and findings
    """
    # Get repo root
    path = repo_path or os.getcwd()
    root_result = get_repo_root(path)
    if root_result.is_err:
        return PrecommitResult(
            passed=False,
            findings=(),
            blocked_files=(),
            severity_counts={},
            files_checked=0,
            error=root_result.error,
        )
    repo_root = root_result.value

    # Load config if not provided
    if config is None:
        config = load_precommit_config(repo_root)

    # Get staged changes
    context_result = get_staged_changes(repo_root)
    if context_result.is_err:
        return PrecommitResult(
            passed=False,
            findings=(),
            blocked_files=(),
            severity_counts={},
            files_checked=0,
            error=context_result.error,
        )
    context = context_result.value

    # Get changed files (excluding deleted)
    changed_files = get_changed_files(context)
    if not changed_files:
        return PrecommitResult(
            passed=True,
            findings=(),
            blocked_files=(),
            severity_counts={},
            files_checked=0,
        )

    all_findings: list[ToolFinding] = []
    blocked_files: list[str] = []

    # Step 1: Secrets detection (configurable tool)
    secrets_findings: list[ToolFinding] = []

    if config.secrets_tool != "none":
        use_gitleaks = False

        if config.secrets_tool == "gitleaks":
            use_gitleaks = True
        elif config.secrets_tool == "auto":
            # Use gitleaks if available, otherwise builtin
            gitleaks_status = check_tool("gitleaks")
            use_gitleaks = gitleaks_status.installed

        if use_gitleaks:
            # Delegate to gitleaks
            gitleaks_result = delegate_gitleaks(repo_root, staged_only=True, timeout=config.timeout)
            if gitleaks_result.is_ok:
                secrets_findings = gitleaks_result.value
            # If gitleaks fails, fall back to builtin (unless explicitly configured)
            elif config.secrets_tool == "auto":
                secrets_findings = check_sensitive_files(changed_files)
        else:
            # Use built-in detection
            secrets_findings = check_sensitive_files(changed_files)

        if secrets_findings:
            blocked_files = [f.location for f in secrets_findings]
            all_findings.extend(secrets_findings)
            # Fail fast on secrets - don't run other tools
            return PrecommitResult(
                passed=False,
                findings=tuple(all_findings),
                blocked_files=tuple(blocked_files),
                severity_counts={"critical": len(secrets_findings)},
                files_checked=len(changed_files),
            )

    # Step 2: Filter excluded files for static analysis
    files_to_check = [
        f for f in changed_files if not _should_exclude(f, config.exclude)
    ]

    if not files_to_check:
        return PrecommitResult(
            passed=True,
            findings=(),
            blocked_files=(),
            severity_counts={},
            files_checked=0,
        )

    # Step 3: Run static analysis on each file
    for file_path in files_to_check:
        full_path = f"{repo_root}/{file_path}"
        tools = _get_tools_for_file(file_path, config)
        domain, _ = _detect_domain_from_path(file_path)

        for tool in tools:
            result: Result[list[ToolFinding], str]

            if tool == "semgrep":
                semgrep_config = get_semgrep_config(domain)
                result = delegate_semgrep(full_path, semgrep_config, config.timeout)
            elif tool == "ruff":
                result = delegate_ruff(full_path, config.timeout)
            elif tool == "bandit":
                result = delegate_bandit(full_path, config.timeout)
            elif tool == "slither":
                result = delegate_slither(full_path, timeout=config.timeout)
            else:
                continue

            if result.is_ok:
                all_findings.extend(result.value)

    # Step 4: Filter to staged lines only
    filtered_findings = _filter_findings_to_staged(
        all_findings, context, config.include_context
    )

    # Count severities
    severity_counts: dict[str, int] = {}
    for f in filtered_findings:
        sev = f.severity.value
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Check if any finding meets threshold
    passed = True
    for finding in filtered_findings:
        if _severity_meets_threshold(finding.severity, config.fail_on):
            passed = False
            break

    return PrecommitResult(
        passed=passed,
        findings=tuple(filtered_findings),
        blocked_files=(),
        severity_counts=severity_counts,
        files_checked=len(files_to_check),
    )


# =============================================================================
# Output Formatting
# =============================================================================

def format_precommit_output(result: PrecommitResult, verbose: bool = False) -> str:
    """Format pre-commit result for terminal output."""
    lines: list[str] = []

    if result.error:
        lines.append(f"Error: {result.error}")
        return "\n".join(lines)

    # Blocked files (sensitive files detected)
    if result.blocked_files:
        lines.append("BLOCKED: Sensitive files detected in staged changes:")
        lines.append("")
        for f in result.blocked_files:
            lines.append(f"  - {f}")
        lines.append("")
        lines.append("Remove these files from staging or add to .gitignore")
        lines.append("")
        lines.append("Pre-commit: FAILED")
        return "\n".join(lines)

    if not result.findings:
        lines.append(f"Checked {result.files_checked} file(s) - no issues found")
        return "\n".join(lines)

    # Header
    total = len(result.findings)
    lines.append(f"Found {total} issue(s) in {result.files_checked} file(s):")
    lines.append("")

    # Severity summary
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = result.severity_counts.get(sev, 0)
        if count > 0:
            lines.append(f"  {sev.upper()}: {count}")

    lines.append("")

    # Findings
    if verbose:
        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            sev_findings = [f for f in result.findings if f.severity == sev]
            if not sev_findings:
                continue

            lines.append(f"[{sev.value.upper()}]")
            for f in sev_findings:
                lines.append(f"  {f.location}")
                lines.append(f"    {f.rule}: {f.message}")
                if f.suggestion:
                    lines.append(f"    Fix: {f.suggestion}")
            lines.append("")
    else:
        # Compact: just show high+ findings
        for f in result.findings:
            if f.severity in (Severity.CRITICAL, Severity.HIGH):
                lines.append(f"  [{f.severity.value.upper()}] {f.location}")
                lines.append(f"    {f.rule}: {f.message}")

    # Status
    lines.append("")
    if result.passed:
        lines.append("Pre-commit: PASSED (findings below threshold)")
    else:
        lines.append("Pre-commit: FAILED")

    return "\n".join(lines)


# Exit codes
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2


def main() -> int:
    """CLI entry point for pre-commit hook."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        prog="crucible-precommit",
        description="Run pre-commit checks on staged changes",
    )
    parser.add_argument(
        "--fail-on",
        choices=["critical", "high", "medium", "low", "info"],
        help="Fail on findings at or above this severity (default: high)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show all findings, not just high+",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository path (default: current directory)",
    )

    args = parser.parse_args()

    # Load config and apply CLI overrides
    config = load_precommit_config(args.path)

    if args.fail_on:
        config = PrecommitConfig(
            fail_on=_parse_severity(args.fail_on),
            timeout=config.timeout,
            exclude=config.exclude,
            include_context=config.include_context,
            tools=config.tools,
            skip_tools=config.skip_tools,
            verbose=args.verbose or config.verbose,
            skip_secrets_check=config.skip_secrets_check,
        )

    result = run_precommit(args.path, config)

    if args.json:
        output = {
            "passed": result.passed,
            "findings": [
                {
                    "tool": f.tool,
                    "rule": f.rule,
                    "severity": f.severity.value,
                    "message": f.message,
                    "location": f.location,
                    "suggestion": f.suggestion,
                }
                for f in result.findings
            ],
            "blocked_files": list(result.blocked_files),
            "severity_counts": result.severity_counts,
            "files_checked": result.files_checked,
            "error": result.error,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_precommit_output(result, args.verbose or config.verbose))

    if result.error:
        return EXIT_ERROR
    return EXIT_PASS if result.passed else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
