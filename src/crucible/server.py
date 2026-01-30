"""crucible MCP server - code review orchestration."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from crucible.knowledge.loader import (
    get_custom_knowledge_files,
    load_all_knowledge,
    load_principles,
)
from crucible.models import Domain, FullReviewResult, Severity, ToolFinding
from crucible.review.core import (
    compute_severity_counts,
    deduplicate_findings,
    detect_domain,
    filter_findings_to_changes,
    load_skills_and_knowledge,
    run_enforcement,
    run_static_analysis,
)
from crucible.skills import get_knowledge_for_skills, load_skill, match_skills_for_domain
from crucible.tools.delegation import (
    check_all_tools,
    delegate_bandit,
    delegate_ruff,
    delegate_semgrep,
    delegate_slither,
    get_semgrep_config,
)
from crucible.tools.git import (
    GitContext,
    get_branch_diff,
    get_changed_files,
    get_recent_commits,
    get_repo_root,
    get_staged_changes,
    get_unstaged_changes,
)

server = Server("crucible")


def _format_findings(findings: list[ToolFinding]) -> str:
    """Format tool findings as markdown."""
    if not findings:
        return "No findings."

    # Group by severity
    by_severity: dict[Severity, list[ToolFinding]] = {}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)

    parts: list[str] = []
    for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
        items = by_severity.get(severity, [])
        if not items:
            continue

        parts.append(f"\n### {severity.value.upper()} ({len(items)})\n")
        for f in items:
            parts.append(f"- **[{f.tool}:{f.rule}]** {f.message}")
            parts.append(f"  - Location: `{f.location}`")
            if f.suggestion:
                parts.append(f"  - Suggestion: {f.suggestion}")

    return "\n".join(parts) if parts else "No findings."


@server.list_tools()  # type: ignore[misc]
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="review",
            description="Unified code review tool. Supports path-based review OR git-aware review. Runs static analysis, matches skills, loads knowledge.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory path to review. If not provided, uses git mode.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["staged", "unstaged", "branch", "commits"],
                        "description": "Git mode: staged (about to commit), unstaged (working dir), branch (PR diff), commits (recent N)",
                    },
                    "base": {
                        "type": "string",
                        "description": "Base branch for 'branch' mode (default: main) or commit count for 'commits' mode (default: 1)",
                    },
                    "include_context": {
                        "type": "boolean",
                        "description": "For git modes: include findings near (within 5 lines of) changes (default: false)",
                    },
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Override skill selection (default: auto-detect based on domain)",
                    },
                    "include_skills": {
                        "type": "boolean",
                        "description": "Load skills and checklists (default: true). Set false for quick analysis only.",
                        "default": True,
                    },
                    "include_knowledge": {
                        "type": "boolean",
                        "description": "Load knowledge files (default: true). Set false for quick analysis only.",
                        "default": True,
                    },
                    "enforce": {
                        "type": "boolean",
                        "description": "Run pattern assertions from .crucible/assertions/ (default: true).",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="quick_review",
            description="[DEPRECATED: use review(path, include_skills=false)] Run static analysis only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory path to scan",
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tools to run (semgrep, ruff, slither, bandit). Default: auto-detect based on file type",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="full_review",
            description="[DEPRECATED: use review(path)] Comprehensive code review with skills and knowledge.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory path to review",
                    },
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Override skill selection (default: auto-detect based on domain)",
                    },
                    "include_sage": {
                        "type": "boolean",
                        "description": "Include Sage knowledge recall (not yet implemented)",
                        "default": True,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="review_changes",
            description="[DEPRECATED: use review(mode='staged')] Review git changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["staged", "unstaged", "branch", "commits"],
                        "description": "What changes to review",
                    },
                    "base": {
                        "type": "string",
                        "description": "Base branch for 'branch' mode or commit count for 'commits' mode",
                    },
                    "path": {
                        "type": "string",
                        "description": "Repository path (default: current directory)",
                    },
                    "include_context": {
                        "type": "boolean",
                        "description": "Include findings near changes (default: false)",
                    },
                },
                "required": ["mode"],
            },
        ),
        Tool(
            name="get_principles",
            description="Load engineering principles by topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic filter (engineering, security, smart_contract, checklist)",
                    },
                },
            },
        ),
        Tool(
            name="delegate_semgrep",
            description="Run semgrep static analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory to scan",
                    },
                    "config": {
                        "type": "string",
                        "description": "Semgrep config (auto, p/python, p/javascript, etc.)",
                        "default": "auto",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="delegate_ruff",
            description="Run ruff Python linter",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory to scan",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="delegate_slither",
            description="Run slither Solidity analyzer",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory to scan",
                    },
                    "detectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific detectors to run",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="delegate_bandit",
            description="Run bandit Python security analyzer",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory to scan",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="check_tools",
            description="Check which analysis tools are installed and available",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="load_knowledge",
            description="Load knowledge/principles files without running static analysis. Useful for getting guidance on patterns, best practices, or domain-specific knowledge. Automatically includes project and user knowledge files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific knowledge files to load (e.g., ['SECURITY.md', 'SMART_CONTRACT.md']). If not specified, loads all project/user knowledge files.",
                    },
                    "include_bundled": {
                        "type": "boolean",
                        "description": "Include bundled knowledge files in addition to project/user files (default: false)",
                        "default": False,
                    },
                    "topic": {
                        "type": "string",
                        "description": "Load by topic instead of files: 'security', 'engineering', 'smart_contract', 'checklist', 'repo_hygiene'",
                    },
                },
            },
        ),
    ]


def _format_review_output(
    path: str | None,
    git_context: GitContext | None,
    domains: list[str],
    severity_counts: dict[str, int],
    findings: list[ToolFinding],
    tool_errors: list[str],
    matched_skills: list[tuple[str, list[str]]] | None,
    skill_content: dict[str, str] | None,
    knowledge_files: set[str] | None,
    knowledge_content: dict[str, str] | None,
    enforcement_findings: list | None = None,
    enforcement_errors: list[str] | None = None,
    assertions_checked: int = 0,
    assertions_skipped: int = 0,
) -> str:
    """Format unified review output."""
    parts: list[str] = ["# Code Review\n"]

    # Header based on mode
    if git_context:
        parts.append(f"**Mode:** {git_context.mode}")
        if git_context.base_ref:
            parts.append(f"**Base:** {git_context.base_ref}")
    elif path:
        parts.append(f"**Path:** `{path}`")

    parts.append(f"**Domains:** {', '.join(domains)}")
    parts.append(f"**Severity summary:** {severity_counts or 'No findings'}\n")

    # Files changed (git mode)
    if git_context and git_context.changes:
        added = [c for c in git_context.changes if c.status == "A"]
        modified = [c for c in git_context.changes if c.status == "M"]
        deleted = [c for c in git_context.changes if c.status == "D"]
        renamed = [c for c in git_context.changes if c.status == "R"]

        total = len(git_context.changes)
        parts.append(f"## Files Changed ({total})")
        for c in added:
            parts.append(f"- `+` {c.path}")
        for c in modified:
            parts.append(f"- `~` {c.path}")
        for c in renamed:
            parts.append(f"- `R` {c.old_path} -> {c.path}")
        for c in deleted:
            parts.append(f"- `-` {c.path}")
        parts.append("")

        # Commit messages
        if git_context.commit_messages:
            parts.append("## Commits")
            for msg in git_context.commit_messages:
                parts.append(f"- {msg}")
            parts.append("")

    # Tool errors
    if tool_errors:
        parts.append("## Tool Errors\n")
        for error in tool_errors:
            parts.append(f"- {error}")
        parts.append("")

    # Applicable skills
    if matched_skills:
        parts.append("## Applicable Skills\n")
        for skill_name, triggers in matched_skills:
            parts.append(f"- **{skill_name}**: matched on {', '.join(triggers)}")
        parts.append("")

    # Knowledge loaded
    if knowledge_files:
        parts.append("## Knowledge Loaded\n")
        parts.append(f"Files: {', '.join(sorted(knowledge_files))}")
        parts.append("")

    # Findings
    parts.append("## Static Analysis Findings\n")
    if findings:
        parts.append(_format_findings(findings))
    else:
        parts.append("No issues found.")
    parts.append("")

    # Enforcement assertions
    if enforcement_findings is not None:
        active = [f for f in enforcement_findings if not f.suppressed]
        suppressed = [f for f in enforcement_findings if f.suppressed]

        parts.append("## Pattern Assertions\n")
        if assertions_checked > 0 or assertions_skipped > 0:
            parts.append(f"*Checked: {assertions_checked}, Skipped (LLM): {assertions_skipped}*\n")

        if enforcement_errors:
            parts.append("**Errors:**")
            for err in enforcement_errors:
                parts.append(f"- {err}")
            parts.append("")

        if active:
            # Group by severity
            by_sev: dict[str, list] = {}
            for f in active:
                by_sev.setdefault(f.severity.upper(), []).append(f)

            for sev in ["ERROR", "WARNING", "INFO"]:
                if sev in by_sev:
                    parts.append(f"### {sev} ({len(by_sev[sev])})\n")
                    for f in by_sev[sev]:
                        parts.append(f"- **[{f.assertion_id}]** {f.message}")
                        parts.append(f"  - Location: `{f.location}`")
                        if f.match_text:
                            parts.append(f"  - Match: `{f.match_text}`")
        else:
            parts.append("No pattern violations found.")

        if suppressed:
            parts.append(f"\n*Suppressed: {len(suppressed)}*")
            for f in suppressed:
                reason = f" ({f.suppression_reason})" if f.suppression_reason else ""
                parts.append(f"- {f.assertion_id}: {f.location}{reason}")

        parts.append("")

    # Review checklists from skills
    if skill_content:
        parts.append("---\n")
        parts.append("## Review Checklists\n")
        for skill_name, content in skill_content.items():
            parts.append(f"### {skill_name}\n")
            parts.append(content)
            parts.append("")

    # Knowledge reference
    if knowledge_content:
        parts.append("---\n")
        parts.append("## Principles Reference\n")
        for filename, content in sorted(knowledge_content.items()):
            parts.append(f"### {filename}\n")
            parts.append(content)
            parts.append("")

    return "\n".join(parts)


def _handle_review(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle unified review tool."""
    import os

    path = arguments.get("path")
    mode = arguments.get("mode")
    base = arguments.get("base")
    include_context = arguments.get("include_context", False)
    skills_override = arguments.get("skills")
    include_skills = arguments.get("include_skills", True)
    include_knowledge = arguments.get("include_knowledge", True)
    enforce = arguments.get("enforce", True)

    # Determine if this is path-based or git-based review
    git_context: GitContext | None = None
    changed_files: list[str] = []

    if mode:
        # Git-based review
        repo_path = path if path else os.getcwd()
        root_result = get_repo_root(repo_path)
        if root_result.is_err:
            return [TextContent(type="text", text=f"Error: {root_result.error}")]
        repo_path = root_result.value

        # Get git context based on mode
        if mode == "staged":
            context_result = get_staged_changes(repo_path)
        elif mode == "unstaged":
            context_result = get_unstaged_changes(repo_path)
        elif mode == "branch":
            base_branch = base if base else "main"
            context_result = get_branch_diff(repo_path, base_branch)
        elif mode == "commits":
            try:
                count = int(base) if base else 1
            except ValueError:
                return [TextContent(type="text", text=f"Error: Invalid commit count '{base}'")]
            context_result = get_recent_commits(repo_path, count)
        else:
            return [TextContent(type="text", text=f"Error: Unknown mode '{mode}'")]

        if context_result.is_err:
            return [TextContent(type="text", text=f"Error: {context_result.error}")]

        git_context = context_result.value

        if not git_context.changes:
            if mode == "staged":
                return [TextContent(type="text", text="No changes to review. Stage files with `git add` first.")]
            elif mode == "unstaged":
                return [TextContent(type="text", text="No unstaged changes to review.")]
            else:
                return [TextContent(type="text", text="No changes found.")]

        changed_files = get_changed_files(git_context)
        if not changed_files:
            return [TextContent(type="text", text="No files to analyze (only deletions).")]

    elif not path:
        return [TextContent(type="text", text="Error: Either 'path' or 'mode' is required.")]

    # Detect domains and run analysis
    all_findings: list[ToolFinding] = []
    tool_errors: list[str] = []
    domains_detected: set[Domain] = set()
    all_domain_tags: set[str] = set()

    if git_context:
        # Git mode: analyze each changed file
        repo_path = get_repo_root(path if path else os.getcwd()).value
        for file_path in changed_files:
            full_path = f"{repo_path}/{file_path}"
            domain, domain_tags = detect_domain(file_path)
            domains_detected.add(domain)
            all_domain_tags.update(domain_tags)

            findings, errors = run_static_analysis(full_path, domain, domain_tags)
            all_findings.extend(findings)
            tool_errors.extend([f"{e} ({file_path})" for e in errors])

        # Filter findings to changed lines
        all_findings = filter_findings_to_changes(all_findings, git_context, include_context)
    else:
        # Path mode: analyze the path directly
        domain, domain_tags = detect_domain(path)
        domains_detected.add(domain)
        all_domain_tags.update(domain_tags)

        findings, errors = run_static_analysis(path, domain, domain_tags)
        all_findings.extend(findings)
        tool_errors.extend(errors)

    # Deduplicate findings
    all_findings = deduplicate_findings(all_findings)

    # Run pattern assertions
    enforcement_findings = []
    enforcement_errors: list[str] = []
    assertions_checked = 0
    assertions_skipped = 0

    if enforce:
        if git_context:
            repo_path = get_repo_root(path if path else os.getcwd()).value
            enforcement_findings, enforcement_errors, assertions_checked, assertions_skipped = (
                run_enforcement(path or "", changed_files=changed_files, repo_root=repo_path)
            )
        elif path:
            enforcement_findings, enforcement_errors, assertions_checked, assertions_skipped = (
                run_enforcement(path)
            )

    # Compute severity summary
    severity_counts = compute_severity_counts(all_findings)

    # Load skills and knowledge
    matched_skills: list[tuple[str, list[str]]] | None = None
    skill_content: dict[str, str] | None = None
    knowledge_files: set[str] | None = None
    knowledge_content: dict[str, str] | None = None

    if include_skills or include_knowledge:
        primary_domain = next(iter(domains_detected)) if domains_detected else Domain.UNKNOWN
        matched, s_content, k_files, k_content = load_skills_and_knowledge(
            primary_domain, list(all_domain_tags), skills_override
        )
        if include_skills:
            matched_skills = matched
            skill_content = s_content
        if include_knowledge:
            knowledge_files = k_files
            knowledge_content = k_content

    # Format output
    output = _format_review_output(
        path,
        git_context,
        list(all_domain_tags) if all_domain_tags else ["unknown"],
        severity_counts,
        all_findings,
        tool_errors,
        matched_skills,
        skill_content,
        knowledge_files,
        knowledge_content,
        enforcement_findings if enforce else None,
        enforcement_errors if enforce else None,
        assertions_checked,
        assertions_skipped,
    )

    return [TextContent(type="text", text=output)]


def _handle_get_principles(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_principles tool."""
    topic = arguments.get("topic")
    result = load_principles(topic)

    if result.is_ok:
        return [TextContent(type="text", text=result.value)]
    return [TextContent(type="text", text=f"Error: {result.error}")]


def _handle_load_knowledge(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle load_knowledge tool."""
    files = arguments.get("files")
    include_bundled = arguments.get("include_bundled", False)
    topic = arguments.get("topic")

    # If topic specified, use load_principles
    if topic:
        result = load_principles(topic)
        if result.is_ok:
            return [TextContent(type="text", text=result.value)]
        return [TextContent(type="text", text=f"Error: {result.error}")]

    # Otherwise load by files
    filenames = set(files) if files else None
    loaded, content = load_all_knowledge(
        include_bundled=include_bundled,
        filenames=filenames,
    )

    if not loaded:
        if filenames:
            return [TextContent(type="text", text=f"No knowledge files found matching: {', '.join(sorted(filenames))}")]
        return [TextContent(type="text", text="No knowledge files found. Add files to .crucible/knowledge/ or ~/.claude/crucible/knowledge/")]

    output_parts = [
        "# Knowledge Loaded\n",
        f"**Files:** {', '.join(loaded)}\n",
        "---\n",
        content,
    ]

    return [TextContent(type="text", text="\n".join(output_parts))]


def _handle_delegate_semgrep(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle delegate_semgrep tool."""
    path = arguments.get("path", "")
    config = arguments.get("config", "auto")
    result = delegate_semgrep(path, config)

    if result.is_ok:
        return [TextContent(type="text", text=_format_findings(result.value))]
    return [TextContent(type="text", text=f"Error: {result.error}")]


def _handle_delegate_ruff(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle delegate_ruff tool."""
    path = arguments.get("path", "")
    result = delegate_ruff(path)

    if result.is_ok:
        return [TextContent(type="text", text=_format_findings(result.value))]
    return [TextContent(type="text", text=f"Error: {result.error}")]


def _handle_delegate_slither(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle delegate_slither tool."""
    path = arguments.get("path", "")
    detectors = arguments.get("detectors")
    result = delegate_slither(path, detectors)

    if result.is_ok:
        return [TextContent(type="text", text=_format_findings(result.value))]
    return [TextContent(type="text", text=f"Error: {result.error}")]


def _handle_delegate_bandit(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle delegate_bandit tool."""
    path = arguments.get("path", "")
    result = delegate_bandit(path)

    if result.is_ok:
        return [TextContent(type="text", text=_format_findings(result.value))]
    return [TextContent(type="text", text=f"Error: {result.error}")]


def _handle_check_tools(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle check_tools tool."""
    statuses = check_all_tools()

    parts: list[str] = ["# Tool Status\n"]
    for name, status in statuses.items():
        if status.installed:
            version_str = f" ({status.version})" if status.version else ""
            parts.append(f"- **{name}**: ✅ Installed{version_str}")
        else:
            parts.append(f"- **{name}**: ❌ Not found")

    # Add install hints for missing tools
    missing = [name for name, status in statuses.items() if not status.installed]
    if missing:
        parts.append("\n## Install Missing Tools\n")
        install_cmds = {
            "semgrep": "pip install semgrep",
            "ruff": "pip install ruff",
            "slither": "pip install slither-analyzer",
            "bandit": "pip install bandit",
        }
        for name in missing:
            if name in install_cmds:
                parts.append(f"```bash\n{install_cmds[name]}\n```")

    return [TextContent(type="text", text="\n".join(parts))]


def _handle_quick_review(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle quick_review tool - returns findings with domain metadata."""
    path = arguments.get("path", "")
    tools = arguments.get("tools")

    # Internal domain detection
    domain, domain_tags = detect_domain(path)

    # Select tools based on domain
    if domain == Domain.SMART_CONTRACT:
        default_tools = ["slither", "semgrep"]
    elif domain == Domain.BACKEND and "python" in domain_tags:
        default_tools = ["ruff", "bandit", "semgrep"]
    elif domain == Domain.FRONTEND:
        default_tools = ["semgrep"]
    else:
        default_tools = ["semgrep"]

    if not tools:
        tools = default_tools

    # Collect all findings
    all_findings: list[ToolFinding] = []
    tool_results: list[str] = []

    if "semgrep" in tools:
        config = get_semgrep_config(domain)
        result = delegate_semgrep(path, config)
        if result.is_ok:
            all_findings.extend(result.value)
            tool_results.append(f"## Semgrep\n{_format_findings(result.value)}")
        else:
            tool_results.append(f"## Semgrep\nError: {result.error}")

    if "ruff" in tools:
        result = delegate_ruff(path)
        if result.is_ok:
            all_findings.extend(result.value)
            tool_results.append(f"## Ruff\n{_format_findings(result.value)}")
        else:
            tool_results.append(f"## Ruff\nError: {result.error}")

    if "slither" in tools:
        result = delegate_slither(path)
        if result.is_ok:
            all_findings.extend(result.value)
            tool_results.append(f"## Slither\n{_format_findings(result.value)}")
        else:
            tool_results.append(f"## Slither\nError: {result.error}")

    if "bandit" in tools:
        result = delegate_bandit(path)
        if result.is_ok:
            all_findings.extend(result.value)
            tool_results.append(f"## Bandit\n{_format_findings(result.value)}")
        else:
            tool_results.append(f"## Bandit\nError: {result.error}")

    # Deduplicate findings
    all_findings = deduplicate_findings(all_findings)

    # Compute severity summary
    severity_counts: dict[str, int] = {}
    for f in all_findings:
        sev = f.severity.value
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Build structured output
    output_parts = [
        "# Review Results\n",
        f"**Domains detected:** {', '.join(domain_tags)}",
        f"**Severity summary:** {severity_counts or 'No findings'}\n",
        "\n".join(tool_results),
    ]

    return [TextContent(type="text", text="\n".join(output_parts))]


def _format_change_review(
    context: GitContext,
    findings: list[ToolFinding],
    severity_counts: dict[str, int],
    tool_errors: list[str] | None = None,
    matched_skills: list[tuple[str, list[str]]] | None = None,
    skill_content: dict[str, str] | None = None,
    knowledge_files: set[str] | None = None,
    knowledge_content: dict[str, str] | None = None,
) -> str:
    """Format change review output."""
    parts: list[str] = ["# Change Review\n"]
    parts.append(f"**Mode:** {context.mode}")
    if context.base_ref:
        parts.append(f"**Base:** {context.base_ref}")
    parts.append("")

    # Files changed
    added = [c for c in context.changes if c.status == "A"]
    modified = [c for c in context.changes if c.status == "M"]
    deleted = [c for c in context.changes if c.status == "D"]
    renamed = [c for c in context.changes if c.status == "R"]

    total = len(context.changes)
    parts.append(f"## Files Changed ({total})")
    for c in added:
        parts.append(f"- `+` {c.path}")
    for c in modified:
        parts.append(f"- `~` {c.path}")
    for c in renamed:
        parts.append(f"- `R` {c.old_path} -> {c.path}")
    for c in deleted:
        parts.append(f"- `-` {c.path}")
    parts.append("")

    # Commit messages (if available)
    if context.commit_messages:
        parts.append("## Commits")
        for msg in context.commit_messages:
            parts.append(f"- {msg}")
        parts.append("")

    # Applicable skills
    if matched_skills:
        parts.append("## Applicable Skills\n")
        for skill_name, triggers in matched_skills:
            parts.append(f"- **{skill_name}**: matched on {', '.join(triggers)}")
        parts.append("")

    # Knowledge loaded
    if knowledge_files:
        parts.append("## Knowledge Loaded\n")
        parts.append(f"Files: {', '.join(sorted(knowledge_files))}")
        parts.append("")

    # Tool errors (if any)
    if tool_errors:
        parts.append("## Tool Errors\n")
        for error in tool_errors:
            parts.append(f"- {error}")
        parts.append("")

    # Findings
    if findings:
        parts.append("## Findings in Changed Code\n")
        parts.append(f"**Summary:** {severity_counts}\n")
        parts.append(_format_findings(findings))
    else:
        parts.append("## Findings in Changed Code\n")
        parts.append("No issues found in changed code.")
    parts.append("")

    # Review checklists from skills
    if skill_content:
        parts.append("---\n")
        parts.append("## Review Checklists\n")
        for skill_name, content in skill_content.items():
            parts.append(f"### {skill_name}\n")
            parts.append(content)
            parts.append("")

    # Knowledge reference
    if knowledge_content:
        parts.append("---\n")
        parts.append("## Principles Reference\n")
        for filename, content in sorted(knowledge_content.items()):
            parts.append(f"### {filename}\n")
            parts.append(content)
            parts.append("")

    return "\n".join(parts)


def _handle_review_changes(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle review_changes tool - review git changes."""
    import os

    mode = arguments.get("mode", "staged")
    base = arguments.get("base")
    path = arguments.get("path", os.getcwd())
    include_context = arguments.get("include_context", False)

    # Get repo root
    root_result = get_repo_root(path)
    if root_result.is_err:
        return [TextContent(type="text", text=f"Error: {root_result.error}")]

    repo_path = root_result.value

    # Get git context based on mode
    if mode == "staged":
        context_result = get_staged_changes(repo_path)
    elif mode == "unstaged":
        context_result = get_unstaged_changes(repo_path)
    elif mode == "branch":
        base_branch = base if base else "main"
        context_result = get_branch_diff(repo_path, base_branch)
    elif mode == "commits":
        try:
            count = int(base) if base else 1
        except ValueError:
            return [TextContent(type="text", text=f"Error: Invalid commit count '{base}'")]
        context_result = get_recent_commits(repo_path, count)
    else:
        return [TextContent(type="text", text=f"Error: Unknown mode '{mode}'")]

    if context_result.is_err:
        return [TextContent(type="text", text=f"Error: {context_result.error}")]

    context = context_result.value

    # Check if there are any changes
    if not context.changes:
        if mode == "staged":
            return [TextContent(type="text", text="No changes to review. Stage files with `git add` first.")]
        elif mode == "unstaged":
            return [TextContent(type="text", text="No unstaged changes to review.")]
        else:
            return [TextContent(type="text", text="No changes found.")]

    # Get changed files (excluding deleted)
    changed_files = get_changed_files(context)
    if not changed_files:
        return [TextContent(type="text", text="No files to analyze (only deletions).")]

    # Run analysis on changed files
    all_findings: list[ToolFinding] = []
    tool_errors: list[str] = []
    domains_detected: set[Domain] = set()
    all_domain_tags: set[str] = set()

    for file_path in changed_files:
        full_path = f"{repo_path}/{file_path}"

        # Detect domain for this file
        domain, domain_tags = detect_domain(file_path)
        domains_detected.add(domain)
        all_domain_tags.update(domain_tags)

        # Select tools based on domain
        if domain == Domain.SMART_CONTRACT:
            tools = ["slither", "semgrep"]
        elif domain == Domain.BACKEND and "python" in domain_tags:
            tools = ["ruff", "bandit", "semgrep"]
        elif domain == Domain.FRONTEND:
            tools = ["semgrep"]
        else:
            tools = ["semgrep"]

        # Run tools
        if "semgrep" in tools:
            config = get_semgrep_config(domain)
            result = delegate_semgrep(full_path, config)
            if result.is_ok:
                all_findings.extend(result.value)
            elif result.is_err:
                tool_errors.append(f"semgrep ({file_path}): {result.error}")

        if "ruff" in tools:
            result = delegate_ruff(full_path)
            if result.is_ok:
                all_findings.extend(result.value)
            elif result.is_err:
                tool_errors.append(f"ruff ({file_path}): {result.error}")

        if "slither" in tools:
            result = delegate_slither(full_path)
            if result.is_ok:
                all_findings.extend(result.value)
            elif result.is_err:
                tool_errors.append(f"slither ({file_path}): {result.error}")

        if "bandit" in tools:
            result = delegate_bandit(full_path)
            if result.is_ok:
                all_findings.extend(result.value)
            elif result.is_err:
                tool_errors.append(f"bandit ({file_path}): {result.error}")

    # Filter findings to changed lines
    filtered_findings = filter_findings_to_changes(all_findings, context, include_context)

    # Deduplicate findings
    filtered_findings = deduplicate_findings(filtered_findings)

    # Compute severity summary
    severity_counts: dict[str, int] = {}
    for f in filtered_findings:
        sev = f.severity.value
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Match skills and load knowledge based on detected domains
    from crucible.knowledge.loader import load_knowledge_file
    from crucible.skills.loader import (
        get_knowledge_for_skills,
        load_skill,
        match_skills_for_domain,
    )

    primary_domain = next(iter(domains_detected)) if domains_detected else Domain.UNKNOWN
    matched_skills = match_skills_for_domain(
        primary_domain, list(all_domain_tags), override=None
    )

    skill_names = [name for name, _ in matched_skills]
    skill_content: dict[str, str] = {}
    for skill_name, _triggers in matched_skills:
        result = load_skill(skill_name)
        if result.is_ok:
            _, content = result.value
            skill_content[skill_name] = content

    knowledge_files = get_knowledge_for_skills(skill_names)
    knowledge_content: dict[str, str] = {}
    for filename in knowledge_files:
        result = load_knowledge_file(filename)
        if result.is_ok:
            knowledge_content[filename] = result.value

    # Format output
    output = _format_change_review(
        context,
        filtered_findings,
        severity_counts,
        tool_errors,
        matched_skills,
        skill_content,
        knowledge_files,
        knowledge_content,
    )
    return [TextContent(type="text", text=output)]


def _handle_full_review(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle full_review tool - comprehensive code review.

    DEPRECATED: Use _handle_review with path parameter instead.
    """
    from crucible.review.core import run_static_analysis

    path = arguments.get("path", "")
    skills_override = arguments.get("skills")

    # 1. Detect domain
    domain, domain_tags = detect_domain(path)

    # 2. Run static analysis using shared core function
    all_findings, tool_errors = run_static_analysis(path, domain, domain_tags)

    # 3. Match applicable skills
    matched_skills = match_skills_for_domain(domain, domain_tags, skills_override)
    skill_names = [name for name, _ in matched_skills]
    skill_triggers: dict[str, tuple[str, ...]] = {
        name: tuple(triggers) for name, triggers in matched_skills
    }

    # 4. Load skill content (checklists/prompts)
    skill_contents: dict[str, str] = {}
    for skill_name in skill_names:
        result = load_skill(skill_name)
        if result.is_ok:
            _, content = result.value
            # Extract content after frontmatter
            if "\n---\n" in content:
                skill_contents[skill_name] = content.split("\n---\n", 1)[1].strip()
            else:
                skill_contents[skill_name] = content

    # 5. Collect knowledge files from matched skills + custom project/user knowledge
    skill_knowledge = get_knowledge_for_skills(skill_names)
    custom_knowledge = get_custom_knowledge_files()
    # Merge: custom knowledge always included, plus skill-referenced files
    knowledge_files = skill_knowledge | custom_knowledge

    # 6. Load knowledge content
    loaded_files, principles_content = load_all_knowledge(
        include_bundled=False,
        filenames=knowledge_files,
    )

    # 7. Deduplicate findings
    all_findings = deduplicate_findings(all_findings)

    # 8. Compute severity summary
    severity_counts = compute_severity_counts(all_findings)

    # 8. Build result
    review_result = FullReviewResult(
        domains_detected=tuple(domain_tags),
        severity_summary=severity_counts,
        findings=tuple(all_findings),
        applicable_skills=tuple(skill_names),
        skill_triggers_matched=skill_triggers,
        principles_loaded=tuple(loaded_files),
        principles_content=principles_content,
        sage_knowledge=None,  # Not implemented yet
        sage_query_used=None,  # Not implemented yet
    )

    # 8. Format output
    output_parts = [
        "# Full Review Results\n",
        f"**Path:** `{path}`",
        f"**Domains detected:** {', '.join(review_result.domains_detected)}",
        f"**Severity summary:** {review_result.severity_summary or 'No findings'}\n",
    ]

    if tool_errors:
        output_parts.append("## Tool Errors\n")
        for error in tool_errors:
            output_parts.append(f"- {error}")
        output_parts.append("")

    output_parts.append("## Applicable Skills\n")
    if review_result.applicable_skills:
        for skill in review_result.applicable_skills:
            triggers = review_result.skill_triggers_matched.get(skill, ())
            output_parts.append(f"- **{skill}**: matched on {', '.join(triggers)}")
    else:
        output_parts.append("- No skills matched")
    output_parts.append("")

    # Include skill checklists
    if skill_contents:
        output_parts.append("## Review Checklists\n")
        for skill_name, content in skill_contents.items():
            output_parts.append(f"### {skill_name}\n")
            output_parts.append(content)
            output_parts.append("")

    output_parts.append("## Knowledge Loaded\n")
    if review_result.principles_loaded:
        output_parts.append(f"Files: {', '.join(review_result.principles_loaded)}\n")
    else:
        output_parts.append("No knowledge files loaded.\n")

    output_parts.append("## Static Analysis Findings\n")
    output_parts.append(_format_findings(list(review_result.findings)))

    if review_result.principles_content:
        output_parts.append("\n---\n")
        output_parts.append("## Principles Reference\n")
        output_parts.append(review_result.principles_content)

    return [TextContent(type="text", text="\n".join(output_parts))]


@server.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    handlers = {
        # Unified review tool
        "review": _handle_review,
        # Deprecated tools (kept for backwards compatibility)
        "quick_review": _handle_quick_review,
        "full_review": _handle_full_review,
        "review_changes": _handle_review_changes,
        # Other tools
        "get_principles": _handle_get_principles,
        "load_knowledge": _handle_load_knowledge,
        "delegate_semgrep": _handle_delegate_semgrep,
        "delegate_ruff": _handle_delegate_ruff,
        "delegate_slither": _handle_delegate_slither,
        "delegate_bandit": _handle_delegate_bandit,
        "check_tools": _handle_check_tools,
    }

    handler = handlers.get(name)
    if handler:
        return handler(arguments)

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def main() -> None:
    """Run the MCP server."""
    asyncio.run(run_server())


async def run_server() -> None:
    """Async server runner."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    main()
