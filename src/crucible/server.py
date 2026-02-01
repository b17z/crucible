"""crucible MCP server - code review orchestration."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from crucible.enforcement.assertions import load_assertions
from crucible.knowledge.loader import (
    load_all_knowledge,
    load_principles,
)
from crucible.models import Domain, Severity, ToolFinding
from crucible.review.core import (
    compute_severity_counts,
    deduplicate_findings,
    detect_domain,
    filter_findings_to_changes,
    load_skills_and_knowledge,
    run_enforcement,
    run_static_analysis,
)
from crucible.tools.delegation import (
    check_all_tools,
    delegate_bandit,
    delegate_ruff,
    delegate_semgrep,
    delegate_slither,
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
                    "compliance_enabled": {
                        "type": "boolean",
                        "description": "Enable LLM compliance assertions (default: true).",
                        "default": True,
                    },
                    "compliance_model": {
                        "type": "string",
                        "enum": ["sonnet", "opus", "haiku"],
                        "description": "Model for LLM compliance assertions (default: sonnet).",
                    },
                    "token_budget": {
                        "type": "integer",
                        "description": "Token budget for LLM assertions (0 = unlimited, default: 10000).",
                    },
                },
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
            description="Load knowledge/principles files without running static analysis. Useful for getting guidance on patterns, best practices, or domain-specific knowledge. Loads all 14 bundled knowledge files by default, with project/user files overriding bundled ones.",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific knowledge files to load (e.g., ['SECURITY.md', 'SMART_CONTRACT.md']). If not specified, loads all available knowledge files.",
                    },
                    "include_bundled": {
                        "type": "boolean",
                        "description": "Include bundled knowledge files (default: true). Project/user files override bundled ones with same name.",
                        "default": True,
                    },
                    "topic": {
                        "type": "string",
                        "description": "Load by topic instead of files: 'security', 'engineering', 'smart_contract', 'checklist', 'repo_hygiene'",
                    },
                },
            },
        ),
        Tool(
            name="get_assertions",
            description="Load active enforcement assertions for this project. Call at session start to understand what code patterns are enforced. Returns all pattern and LLM assertions that will be checked during reviews.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_compliance": {
                        "type": "boolean",
                        "description": "Include LLM compliance assertion details (default: true)",
                        "default": True,
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
    budget_state: Any = None,
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

        # Separate pattern vs LLM findings
        pattern_findings = [f for f in active if getattr(f, "source", "pattern") == "pattern"]
        llm_findings = [f for f in active if getattr(f, "source", "pattern") == "llm"]

        parts.append("## Enforcement Assertions\n")

        # Summary line
        summary_parts = []
        if assertions_checked > 0:
            summary_parts.append(f"Checked: {assertions_checked}")
        if assertions_skipped > 0:
            summary_parts.append(f"Skipped: {assertions_skipped}")
        if budget_state and budget_state.tokens_used > 0:
            summary_parts.append(f"LLM tokens: {budget_state.tokens_used}")
        if summary_parts:
            parts.append(f"*{', '.join(summary_parts)}*\n")

        if enforcement_errors:
            parts.append("**Errors:**")
            for err in enforcement_errors:
                parts.append(f"- {err}")
            parts.append("")

        # Pattern assertions
        if pattern_findings:
            parts.append("### Pattern Assertions\n")
            by_sev: dict[str, list] = {}
            for f in pattern_findings:
                by_sev.setdefault(f.severity.upper(), []).append(f)

            for sev in ["ERROR", "WARNING", "INFO"]:
                if sev in by_sev:
                    parts.append(f"#### {sev} ({len(by_sev[sev])})\n")
                    for f in by_sev[sev]:
                        parts.append(f"- **[{f.assertion_id}]** {f.message}")
                        parts.append(f"  - Location: `{f.location}`")
                        if f.match_text:
                            parts.append(f"  - Match: `{f.match_text}`")

        # LLM compliance assertions
        if llm_findings:
            parts.append("### LLM Compliance Assertions\n")
            by_sev_llm: dict[str, list] = {}
            for f in llm_findings:
                by_sev_llm.setdefault(f.severity.upper(), []).append(f)

            for sev in ["ERROR", "WARNING", "INFO"]:
                if sev in by_sev_llm:
                    parts.append(f"#### {sev} ({len(by_sev_llm[sev])})\n")
                    for f in by_sev_llm[sev]:
                        parts.append(f"- **[{f.assertion_id}]** {f.message}")
                        parts.append(f"  - Location: `{f.location}`")
                        if getattr(f, "llm_reasoning", None):
                            parts.append(f"  - Reasoning: {f.llm_reasoning}")

        if not pattern_findings and not llm_findings:
            parts.append("No assertion violations found.")

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

    from crucible.enforcement.models import ComplianceConfig, OverflowBehavior

    path = arguments.get("path")
    mode = arguments.get("mode")
    base = arguments.get("base")
    include_context = arguments.get("include_context", False)
    skills_override = arguments.get("skills")
    include_skills = arguments.get("include_skills", True)
    include_knowledge = arguments.get("include_knowledge", True)
    enforce = arguments.get("enforce", True)

    # Build compliance config
    compliance_enabled = arguments.get("compliance_enabled", True)
    compliance_model = arguments.get("compliance_model", "sonnet")
    token_budget = arguments.get("token_budget", 10000)

    compliance_config = ComplianceConfig(
        enabled=compliance_enabled,
        model=compliance_model,
        token_budget=token_budget,
        overflow_behavior=OverflowBehavior.WARN,
    )

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

    # Run pattern and LLM assertions
    enforcement_findings = []
    enforcement_errors: list[str] = []
    assertions_checked = 0
    assertions_skipped = 0
    budget_state = None

    if enforce:
        if git_context:
            repo_path = get_repo_root(path if path else os.getcwd()).value
            enforcement_findings, enforcement_errors, assertions_checked, assertions_skipped, budget_state = (
                run_enforcement(
                    path or "",
                    changed_files=changed_files,
                    repo_root=repo_path,
                    compliance_config=compliance_config,
                )
            )
        elif path:
            enforcement_findings, enforcement_errors, assertions_checked, assertions_skipped, budget_state = (
                run_enforcement(path, compliance_config=compliance_config)
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
        budget_state,
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
    include_bundled = arguments.get("include_bundled", True)
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


def _handle_get_assertions(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_assertions tool - load active enforcement rules."""
    include_compliance = arguments.get("include_compliance", True)

    assertions, load_errors = load_assertions()

    if not assertions and not load_errors:
        return [TextContent(type="text", text="No assertions found. Add assertion files to .crucible/assertions/ or use bundled assertions.")]

    parts: list[str] = ["# Active Enforcement Assertions\n"]
    parts.append("These patterns are enforced during code review. Avoid these in your code.\n")

    if load_errors:
        parts.append("## Load Errors\n")
        for error in load_errors:
            parts.append(f"- {error}")
        parts.append("")

    # Group by source file / category
    pattern_assertions = [a for a in assertions if a.type.value == "pattern"]
    llm_assertions = [a for a in assertions if a.type.value == "llm"]

    if pattern_assertions:
        parts.append("## Pattern Assertions (fast, always run)\n")
        parts.append("| ID | Message | Severity | Languages |")
        parts.append("|---|---|---|---|")
        for a in pattern_assertions:
            langs = ", ".join(a.languages) if a.languages else "all"
            parts.append(f"| `{a.id}` | {a.message} | {a.severity} | {langs} |")
        parts.append("")

    if llm_assertions and include_compliance:
        parts.append("## LLM Compliance Assertions (semantic, budget-controlled)\n")
        parts.append("| ID | Message | Severity | Model |")
        parts.append("|---|---|---|---|")
        for a in llm_assertions:
            model = a.model or "sonnet"
            parts.append(f"| `{a.id}` | {a.message} | {a.severity} | {model} |")
        parts.append("")

        # Show compliance requirements for LLM assertions
        parts.append("### Compliance Requirements\n")
        for a in llm_assertions:
            parts.append(f"**{a.id}:**")
            if a.compliance:
                parts.append(f"```\n{a.compliance.strip()}\n```")
            parts.append("")

    # Summary
    parts.append("---\n")
    parts.append(f"**Total:** {len(pattern_assertions)} pattern + {len(llm_assertions)} LLM assertions")

    return [TextContent(type="text", text="\n".join(parts))]


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


@server.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    handlers = {
        # Unified review tool
        "review": _handle_review,
        # Context injection tools (call at session start)
        "get_assertions": _handle_get_assertions,
        "get_principles": _handle_get_principles,
        "load_knowledge": _handle_load_knowledge,
        # Direct tool access
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
