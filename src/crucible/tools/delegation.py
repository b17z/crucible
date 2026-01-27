"""Tool delegation - shell out to static analysis tools."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from crucible.errors import Result, err, ok
from crucible.models import Domain, Severity, ToolFinding

# Semgrep configs by domain
SEMGREP_CONFIGS: dict[Domain, list[str]] = {
    Domain.SMART_CONTRACT: ["p/smart-contracts", "p/solidity"],
    Domain.FRONTEND: ["p/javascript", "p/typescript", "p/react"],
    Domain.BACKEND: ["p/python", "p/golang", "p/rust"],
    Domain.INFRASTRUCTURE: ["p/terraform", "p/dockerfile", "p/kubernetes"],
    Domain.UNKNOWN: ["auto"],
}


@dataclass(frozen=True)
class ToolStatus:
    """Status of an external tool."""

    name: str
    installed: bool
    path: str | None
    version: str | None


def check_tool(name: str) -> ToolStatus:
    """Check if a tool is installed and get its version."""
    path = shutil.which(name)
    if not path:
        return ToolStatus(name=name, installed=False, path=None, version=None)

    # Try to get version
    version = None
    try:
        if name == "semgrep":
            result = subprocess.run([name, "--version"], capture_output=True, text=True, timeout=5)
            version = result.stdout.strip().split("\n")[0] if result.returncode == 0 else None
        elif name in ("ruff", "slither", "gitleaks"):
            result = subprocess.run([name, "--version"], capture_output=True, text=True, timeout=5)
            version = result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return ToolStatus(name=name, installed=True, path=path, version=version)


def check_all_tools() -> dict[str, ToolStatus]:
    """Check status of all supported tools."""
    tools = ["semgrep", "ruff", "slither", "bandit", "gitleaks"]
    return {name: check_tool(name) for name in tools}


def get_semgrep_config(domain: Domain) -> str:
    """Get the appropriate semgrep config for a domain."""
    configs = SEMGREP_CONFIGS.get(domain, SEMGREP_CONFIGS[Domain.UNKNOWN])
    # Join multiple configs with --config flags handled by semgrep
    return configs[0] if configs else "auto"


def _severity_from_semgrep(level: str) -> Severity:
    """Map semgrep severity to our Severity enum."""
    mapping = {
        "ERROR": Severity.HIGH,
        "WARNING": Severity.MEDIUM,
        "INFO": Severity.INFO,
    }
    return mapping.get(level.upper(), Severity.INFO)


def _validate_path(path: str) -> Result[None, str]:
    """Validate path argument to prevent argument injection.

    Args:
        path: Path to validate

    Returns:
        Result with None on success, error message on failure
    """
    if not path:
        return err("Path cannot be empty")
    if path.startswith("-"):
        return err(f"Path cannot start with '-': {path}")
    if not Path(path).exists():
        return err(f"Path does not exist: {path}")
    return ok(None)


def delegate_semgrep(
    path: str,
    config: str = "auto",
    timeout: int = 120,
) -> Result[list[ToolFinding], str]:
    """
    Run semgrep on a file or directory.

    Args:
        path: File or directory to scan
        config: Semgrep config (auto, p/python, p/javascript, etc.)
        timeout: Timeout in seconds

    Returns:
        Result containing list of findings or error message
    """
    validation = _validate_path(path)
    if validation.is_err:
        return err(validation.error)

    try:
        result = subprocess.run(
            ["semgrep", "--config", config, "--json", "--quiet", path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return err("semgrep not found. Install with: pip install semgrep")
    except subprocess.TimeoutExpired:
        return err(f"semgrep timed out after {timeout}s")

    if result.returncode not in (0, 1):  # 1 means findings found
        return err(f"semgrep failed: {result.stderr}")

    try:
        output = json.loads(result.stdout) if result.stdout else {"results": []}
    except json.JSONDecodeError as e:
        return err(f"Failed to parse semgrep output: {e}")

    findings: list[ToolFinding] = []
    for r in output.get("results", []):
        finding = ToolFinding(
            tool="semgrep",
            rule=r.get("check_id", "unknown"),
            severity=_severity_from_semgrep(r.get("extra", {}).get("severity", "INFO")),
            message=r.get("extra", {}).get("message", r.get("check_id", "")),
            location=f"{r.get('path', '?')}:{r.get('start', {}).get('line', '?')}",
            suggestion=r.get("extra", {}).get("fix", None),
        )
        findings.append(finding)

    return ok(findings)


def delegate_ruff(
    path: str,
    timeout: int = 60,
) -> Result[list[ToolFinding], str]:
    """
    Run ruff on a Python file or directory.

    Args:
        path: File or directory to scan
        timeout: Timeout in seconds

    Returns:
        Result containing list of findings or error message
    """
    validation = _validate_path(path)
    if validation.is_err:
        return err(validation.error)

    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return err("ruff not found. Install with: pip install ruff")
    except subprocess.TimeoutExpired:
        return err(f"ruff timed out after {timeout}s")

    try:
        output = json.loads(result.stdout) if result.stdout else []
    except json.JSONDecodeError as e:
        return err(f"Failed to parse ruff output: {e}")

    findings: list[ToolFinding] = []
    for r in output:
        finding = ToolFinding(
            tool="ruff",
            rule=r.get("code", "unknown"),
            severity=_severity_from_ruff(r.get("code", "")),
            message=r.get("message", ""),
            location=f"{r.get('filename', '?')}:{r.get('location', {}).get('row', '?')}",
            suggestion=r.get("fix", {}).get("message") if r.get("fix") else None,
        )
        findings.append(finding)

    return ok(findings)


def _severity_from_ruff(code: str) -> Severity:
    """Map ruff rule codes to severity based on category."""
    if not code:
        return Severity.LOW

    # Security-related rules are higher severity
    # S = bandit (security), T = flake8-print (debug code)
    if code.startswith("S"):
        # S1xx = security issues
        if code.startswith("S1"):
            return Severity.HIGH
        return Severity.MEDIUM

    # Error-prone patterns
    # B = bugbear, E9xx = syntax errors, F = pyflakes
    if code.startswith("B") or code.startswith("E9") or code.startswith("F"):
        return Severity.MEDIUM

    # Everything else is low (style, formatting)
    return Severity.LOW


def delegate_bandit(
    path: str,
    timeout: int = 60,
) -> Result[list[ToolFinding], str]:
    """
    Run bandit on a Python file or directory.

    Bandit catches hardcoded secrets (B105, B106, B107) that semgrep's
    p/bandit config doesn't include.

    Args:
        path: File or directory to scan
        timeout: Timeout in seconds

    Returns:
        Result containing list of findings or error message
    """
    validation = _validate_path(path)
    if validation.is_err:
        return err(validation.error)

    try:
        result = subprocess.run(
            ["bandit", "-f", "json", "-r", path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return err("bandit not found. Install with: pip install bandit")
    except subprocess.TimeoutExpired:
        return err(f"bandit timed out after {timeout}s")

    try:
        output = json.loads(result.stdout) if result.stdout else {"results": []}
    except json.JSONDecodeError as e:
        return err(f"Failed to parse bandit output: {e}")

    # Map bandit severity to our Severity
    severity_map = {
        "HIGH": Severity.HIGH,
        "MEDIUM": Severity.MEDIUM,
        "LOW": Severity.LOW,
    }

    findings: list[ToolFinding] = []
    for r in output.get("results", []):
        finding = ToolFinding(
            tool="bandit",
            rule=r.get("test_id", "unknown"),
            severity=severity_map.get(r.get("issue_severity", ""), Severity.INFO),
            message=r.get("issue_text", ""),
            location=f"{r.get('filename', '?')}:{r.get('line_number', '?')}",
            suggestion=None,
        )
        findings.append(finding)

    return ok(findings)


def delegate_slither(
    path: str,
    detectors: list[str] | None = None,
    timeout: int = 300,
) -> Result[list[ToolFinding], str]:
    """
    Run slither on a Solidity file or project.

    Args:
        path: File or directory to scan
        detectors: Specific detectors to run (None = all)
        timeout: Timeout in seconds

    Returns:
        Result containing list of findings or error message
    """
    validation = _validate_path(path)
    if validation.is_err:
        return err(validation.error)

    cmd = ["slither", path, "--json", "-"]
    if detectors:
        cmd.extend(["--detect", ",".join(detectors)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return err("slither not found. Install with: pip install slither-analyzer")
    except subprocess.TimeoutExpired:
        return err(f"slither timed out after {timeout}s")

    try:
        output = json.loads(result.stdout) if result.stdout else {"results": {"detectors": []}}
    except json.JSONDecodeError as e:
        return err(f"Failed to parse slither output: {e}")

    # Map slither impact to severity
    impact_map = {
        "High": Severity.HIGH,
        "Medium": Severity.MEDIUM,
        "Low": Severity.LOW,
        "Informational": Severity.INFO,
    }

    findings: list[ToolFinding] = []
    for d in output.get("results", {}).get("detectors", []):
        elements = d.get("elements", [])
        location = "unknown"
        if elements:
            first = elements[0]
            location = f"{first.get('source_mapping', {}).get('filename_relative', '?')}"

        finding = ToolFinding(
            tool="slither",
            rule=d.get("check", "unknown"),
            severity=impact_map.get(d.get("impact", ""), Severity.INFO),
            message=d.get("description", ""),
            location=location,
            suggestion=None,
        )
        findings.append(finding)

    return ok(findings)


def delegate_gitleaks(
    path: str,
    staged_only: bool = False,
    timeout: int = 60,
) -> Result[list[ToolFinding], str]:
    """
    Run gitleaks to detect secrets in code.

    Args:
        path: Repository path to scan
        staged_only: Only scan staged changes (for pre-commit)
        timeout: Timeout in seconds

    Returns:
        Result containing list of findings or error message
    """
    validation = _validate_path(path)
    if validation.is_err:
        return err(validation.error)

    # Build command
    if staged_only:
        cmd = ["gitleaks", "protect", "--staged", "--report-format", "json", "--report-path", "/dev/stdout"]
    else:
        cmd = ["gitleaks", "detect", "--source", path, "--report-format", "json", "--report-path", "/dev/stdout"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=path if staged_only else None,
        )
    except FileNotFoundError:
        return err("gitleaks not found. Install from: https://github.com/gitleaks/gitleaks")
    except subprocess.TimeoutExpired:
        return err(f"gitleaks timed out after {timeout}s")

    # Exit code 1 means leaks found, 0 means clean
    if result.returncode not in (0, 1):
        return err(f"gitleaks failed: {result.stderr}")

    try:
        output = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError as e:
        return err(f"Failed to parse gitleaks output: {e}")

    findings: list[ToolFinding] = []
    for leak in output:
        # Gitleaks output format
        finding = ToolFinding(
            tool="gitleaks",
            rule=leak.get("RuleID", "unknown"),
            severity=Severity.CRITICAL,  # All secrets are critical
            message=f"Secret detected: {leak.get('Description', 'potential secret')}",
            location=f"{leak.get('File', '?')}:{leak.get('StartLine', '?')}",
            suggestion="Remove secret and rotate credentials",
        )
        findings.append(finding)

    return ok(findings)
