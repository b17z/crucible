"""Tool delegation - shell out to static analysis tools."""

import json
import subprocess
from pathlib import Path

from crucible.errors import Result, err, ok
from crucible.models import Severity, ToolFinding


def _severity_from_semgrep(level: str) -> Severity:
    """Map semgrep severity to our Severity enum."""
    mapping = {
        "ERROR": Severity.HIGH,
        "WARNING": Severity.MEDIUM,
        "INFO": Severity.INFO,
    }
    return mapping.get(level.upper(), Severity.INFO)


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
    if not Path(path).exists():
        return err(f"Path does not exist: {path}")

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
    if not Path(path).exists():
        return err(f"Path does not exist: {path}")

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
            severity=Severity.LOW,  # Ruff is mostly style/lint
            message=r.get("message", ""),
            location=f"{r.get('filename', '?')}:{r.get('location', {}).get('row', '?')}",
            suggestion=r.get("fix", {}).get("message") if r.get("fix") else None,
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
    if not Path(path).exists():
        return err(f"Path does not exist: {path}")

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
