"""Core review functionality shared between CLI and MCP server."""

from collections import Counter
from pathlib import Path

from crucible.models import Domain, Severity, ToolFinding
from crucible.tools.delegation import (
    delegate_bandit,
    delegate_ruff,
    delegate_semgrep,
    delegate_slither,
    get_semgrep_config,
)
from crucible.tools.git import GitContext


def detect_domain_for_file(path: str) -> tuple[Domain, list[str]]:
    """Detect domain from a single file path.

    Returns (domain, list of domain tags for skill matching).
    """
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


def detect_domain(path: str) -> tuple[Domain, list[str]]:
    """Detect domain from file or directory path.

    For directories, scans contained files and aggregates domains.
    Returns (primary_domain, list of all domain tags).
    """
    p = Path(path)

    # Single file - use direct detection
    if p.is_file():
        return detect_domain_for_file(path)

    # Directory - scan and aggregate
    if not p.is_dir():
        return Domain.UNKNOWN, ["unknown"]

    domain_counts: Counter[Domain] = Counter()
    all_tags: set[str] = set()

    # Scan files in directory (up to 1000 to avoid huge repos)
    file_count = 0
    max_files = 1000
    skip_dirs = {"node_modules", "__pycache__", "venv", ".venv", "dist", "build"}

    for file_path in p.rglob("*"):
        if file_count >= max_files:
            break
        if not file_path.is_file():
            continue
        # Skip hidden files and common non-code directories
        if any(part.startswith(".") for part in file_path.parts):
            continue
        if any(part in skip_dirs for part in file_path.parts):
            continue

        domain, tags = detect_domain_for_file(str(file_path))
        if domain != Domain.UNKNOWN:
            domain_counts[domain] += 1
            all_tags.update(tags)
        file_count += 1

    # Return most common domain, or UNKNOWN if none found
    if not domain_counts:
        return Domain.UNKNOWN, ["unknown"]

    primary_domain = domain_counts.most_common(1)[0][0]
    return primary_domain, sorted(all_tags) if all_tags else ["unknown"]


def get_tools_for_domain(domain: Domain, domain_tags: list[str]) -> list[str]:
    """Select static analysis tools based on domain and tags."""
    if domain == Domain.SMART_CONTRACT:
        return ["slither", "semgrep"]
    elif domain == Domain.BACKEND and "python" in domain_tags:
        return ["ruff", "bandit", "semgrep"]
    elif domain == Domain.FRONTEND:
        return ["semgrep"]
    else:
        return ["semgrep"]


def run_static_analysis(
    path: str,
    domain: Domain,
    domain_tags: list[str],
    tools: list[str] | None = None,
) -> tuple[list[ToolFinding], list[str]]:
    """Run static analysis tools.

    Args:
        path: File or directory to analyze
        domain: Detected domain
        domain_tags: Domain tags for tool selection
        tools: Override tool selection (if None, auto-select based on domain)

    Returns:
        (findings, tool_errors)
    """
    if tools is None:
        tools = get_tools_for_domain(domain, domain_tags)

    all_findings: list[ToolFinding] = []
    tool_errors: list[str] = []

    if "semgrep" in tools:
        config = get_semgrep_config(domain)
        result = delegate_semgrep(path, config)
        if result.is_ok:
            all_findings.extend(result.value)
        elif result.is_err:
            tool_errors.append(f"semgrep: {result.error}")

    if "ruff" in tools:
        result = delegate_ruff(path)
        if result.is_ok:
            all_findings.extend(result.value)
        elif result.is_err:
            tool_errors.append(f"ruff: {result.error}")

    if "slither" in tools:
        result = delegate_slither(path)
        if result.is_ok:
            all_findings.extend(result.value)
        elif result.is_err:
            tool_errors.append(f"slither: {result.error}")

    if "bandit" in tools:
        result = delegate_bandit(path)
        if result.is_ok:
            all_findings.extend(result.value)
        elif result.is_err:
            tool_errors.append(f"bandit: {result.error}")

    return all_findings, tool_errors


def deduplicate_findings(findings: list[ToolFinding]) -> list[ToolFinding]:
    """Deduplicate findings by location and message.

    When multiple tools report the same issue at the same location,
    keep only the highest severity finding.
    """
    seen: dict[tuple[str, str], ToolFinding] = {}
    severity_order = [
        Severity.CRITICAL,
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
        Severity.INFO,
    ]

    for f in findings:
        # Normalize the message for comparison
        norm_msg = f.message.lower().strip()
        key = (f.location, norm_msg)

        if key not in seen:
            seen[key] = f
        else:
            # Keep the higher severity finding
            existing = seen[key]
            if severity_order.index(f.severity) < severity_order.index(existing.severity):
                seen[key] = f

    return list(seen.values())


def filter_findings_to_changes(
    findings: list[ToolFinding],
    context: GitContext,
    include_context: bool = False,
) -> list[ToolFinding]:
    """Filter findings to only those in changed lines.

    Args:
        findings: All findings from analysis
        context: Git context with changed files and line ranges
        include_context: Include findings within 5 lines of changes

    Returns:
        Filtered findings that are in or near changed lines
    """
    # Build a lookup of file -> changed line ranges
    changed_ranges: dict[str, list[tuple[int, int]]] = {}
    for change in context.changes:
        if change.status == "D":
            continue  # Skip deleted files
        ranges = [(r.start, r.end) for r in change.added_lines]
        changed_ranges[change.path] = ranges

    context_lines = 5 if include_context else 0
    filtered: list[ToolFinding] = []

    for finding in findings:
        # Parse location: "path:line" or "path:line:col"
        parts = finding.location.split(":")
        if len(parts) < 2:
            continue

        file_path = parts[0]
        try:
            line_num = int(parts[1])
        except ValueError:
            continue

        # Check if file is in changes (handle both absolute and relative paths)
        matching_file = None
        for changed_file in changed_ranges:
            if file_path.endswith(changed_file) or changed_file.endswith(file_path):
                matching_file = changed_file
                break

        if not matching_file:
            continue

        # Check if line is in changed ranges
        ranges = changed_ranges[matching_file]
        in_range = False
        for start, end in ranges:
            if start - context_lines <= line_num <= end + context_lines:
                in_range = True
                break

        if in_range:
            filtered.append(finding)

    return filtered


def compute_severity_counts(findings: list[ToolFinding]) -> dict[str, int]:
    """Compute severity counts for findings."""
    counts: dict[str, int] = {}
    for f in findings:
        sev = f.severity.value
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def load_skills_and_knowledge(
    domain: Domain,
    domain_tags: list[str],
    skills_override: list[str] | None = None,
) -> tuple[list[tuple[str, list[str]]], dict[str, str], set[str], dict[str, str]]:
    """Load matched skills and linked knowledge.

    Args:
        domain: Primary domain
        domain_tags: All domain tags
        skills_override: Override auto skill selection

    Returns:
        (matched_skills, skill_content, knowledge_files, knowledge_content)
    """
    from crucible.knowledge.loader import get_custom_knowledge_files, load_knowledge_file
    from crucible.skills.loader import (
        get_knowledge_for_skills,
        load_skill,
        match_skills_for_domain,
    )

    matched_skills = match_skills_for_domain(domain, domain_tags, skills_override)
    skill_names = [name for name, _ in matched_skills]

    # Load skill content
    skill_content: dict[str, str] = {}
    for skill_name, _ in matched_skills:
        result = load_skill(skill_name)
        if result.is_ok:
            _, content = result.value
            # Extract content after frontmatter
            if "\n---\n" in content:
                skill_content[skill_name] = content.split("\n---\n", 1)[1].strip()
            else:
                skill_content[skill_name] = content

    # Load knowledge from skills + custom project/user knowledge
    knowledge_files = get_knowledge_for_skills(skill_names)
    custom_knowledge = get_custom_knowledge_files()
    knowledge_files = knowledge_files | custom_knowledge

    knowledge_content: dict[str, str] = {}
    for filename in knowledge_files:
        result = load_knowledge_file(filename)
        if result.is_ok:
            knowledge_content[filename] = result.value

    return matched_skills, skill_content, knowledge_files, knowledge_content


def run_enforcement(
    path: str,
    content: str | None = None,
    changed_files: list[str] | None = None,
    repo_root: str | None = None,
) -> tuple[list, list[str], int, int]:
    """Run pattern assertions.

    Args:
        path: File or directory path
        content: File content (for single file mode)
        changed_files: List of changed files (for git mode)
        repo_root: Repository root path (for git mode)

    Returns:
        (enforcement_findings, errors, assertions_checked, assertions_skipped)
    """
    import os

    from crucible.enforcement.assertions import load_assertions
    from crucible.enforcement.models import EnforcementFinding
    from crucible.enforcement.patterns import run_pattern_assertions

    assertions, errors = load_assertions()
    if not assertions:
        return [], errors, 0, 0

    findings: list[EnforcementFinding] = []
    checked = 0
    skipped = 0

    if changed_files and repo_root:
        # Git mode: check each changed file
        for file_path in changed_files:
            full_path = os.path.join(repo_root, file_path)
            try:
                with open(full_path) as f:
                    file_content = f.read()
                f_findings, c, s = run_pattern_assertions(file_path, file_content, assertions)
                findings.extend(f_findings)
                checked = max(checked, c)
                skipped = max(skipped, s)
            except OSError:
                pass  # File may have been deleted
    elif content is not None:
        # Single file with provided content
        f_findings, checked, skipped = run_pattern_assertions(path, content, assertions)
        findings.extend(f_findings)
    elif os.path.isfile(path):
        # Single file
        try:
            with open(path) as f:
                file_content = f.read()
            findings, checked, skipped = run_pattern_assertions(path, file_content, assertions)
        except OSError as e:
            errors.append(f"Failed to read {path}: {e}")
    elif os.path.isdir(path):
        # Directory
        for root, _, files in os.walk(path):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, path)
                try:
                    with open(fpath) as f:
                        file_content = f.read()
                    f_findings, c, s = run_pattern_assertions(rel_path, file_content, assertions)
                    findings.extend(f_findings)
                    checked = max(checked, c)
                    skipped = max(skipped, s)
                except (OSError, UnicodeDecodeError):
                    pass  # Skip unreadable files

    return findings, errors, checked, skipped
