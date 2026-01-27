"""crucible MCP server - code review orchestration."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from crucible.knowledge.loader import load_principles
from crucible.models import Domain, Severity, ToolFinding
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
            name="quick_review",
            description="Run static analysis tools on code. Returns findings with domain metadata for skill selection.",
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
            name="review_changes",
            description="Review git changes (staged, unstaged, branch diff, commits). Runs analysis on changed files and filters findings to changed lines only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["staged", "unstaged", "branch", "commits"],
                        "description": "What changes to review: staged (about to commit), unstaged (working dir), branch (PR diff vs base), commits (recent N commits)",
                    },
                    "base": {
                        "type": "string",
                        "description": "Base branch for 'branch' mode (default: main) or commit count for 'commits' mode (default: 1)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Repository path (default: current directory)",
                    },
                    "include_context": {
                        "type": "boolean",
                        "description": "Include findings near (within 5 lines of) changes, not just in changed lines (default: false)",
                    },
                },
                "required": ["mode"],
            },
        ),
    ]


def _handle_get_principles(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_principles tool."""
    topic = arguments.get("topic")
    result = load_principles(topic)

    if result.is_ok:
        return [TextContent(type="text", text=result.value)]
    return [TextContent(type="text", text=f"Error: {result.error}")]


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


def _detect_domain(path: str) -> tuple[Domain, list[str]]:
    """Internal domain detection from file path.

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
        return Domain.UNKNOWN, ["unknown"]


def _handle_quick_review(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle quick_review tool - returns findings with domain metadata."""
    path = arguments.get("path", "")
    tools = arguments.get("tools")

    # Internal domain detection
    domain, domain_tags = _detect_domain(path)

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


def _filter_findings_to_changes(
    findings: list[ToolFinding],
    context: GitContext,
    include_context: bool = False,
) -> list[ToolFinding]:
    """Filter findings to only those in changed lines."""
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

        # Check if file is in changes
        # Handle both absolute and relative paths
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


def _format_change_review(
    context: GitContext,
    findings: list[ToolFinding],
    severity_counts: dict[str, int],
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

    # Findings
    if findings:
        parts.append("## Findings in Changed Code\n")
        parts.append(f"**Summary:** {severity_counts}\n")
        parts.append(_format_findings(findings))
    else:
        parts.append("## Findings in Changed Code\n")
        parts.append("No issues found in changed code.")

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
    for file_path in changed_files:
        full_path = f"{repo_path}/{file_path}"

        # Detect domain for this file
        domain, domain_tags = _detect_domain(file_path)

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

        if "ruff" in tools:
            result = delegate_ruff(full_path)
            if result.is_ok:
                all_findings.extend(result.value)

        if "slither" in tools:
            result = delegate_slither(full_path)
            if result.is_ok:
                all_findings.extend(result.value)

        if "bandit" in tools:
            result = delegate_bandit(full_path)
            if result.is_ok:
                all_findings.extend(result.value)

    # Filter findings to changed lines
    filtered_findings = _filter_findings_to_changes(all_findings, context, include_context)

    # Compute severity summary
    severity_counts: dict[str, int] = {}
    for f in filtered_findings:
        sev = f.severity.value
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Format output
    output = _format_change_review(context, filtered_findings, severity_counts)
    return [TextContent(type="text", text=output)]


@server.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    handlers = {
        "get_principles": _handle_get_principles,
        "delegate_semgrep": _handle_delegate_semgrep,
        "delegate_ruff": _handle_delegate_ruff,
        "delegate_slither": _handle_delegate_slither,
        "delegate_bandit": _handle_delegate_bandit,
        "quick_review": _handle_quick_review,
        "check_tools": _handle_check_tools,
        "review_changes": _handle_review_changes,
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
