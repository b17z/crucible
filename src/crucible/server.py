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
    delegate_ruff,
    delegate_semgrep,
    delegate_slither,
    get_semgrep_config,
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
                        "description": "Tools to run (semgrep, ruff, slither). Default: auto-detect based on file type",
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
            name="check_tools",
            description="Check which analysis tools are installed and available",
            inputSchema={
                "type": "object",
                "properties": {},
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
        default_tools = ["ruff", "semgrep"]
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


@server.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    handlers = {
        "get_principles": _handle_get_principles,
        "delegate_semgrep": _handle_delegate_semgrep,
        "delegate_ruff": _handle_delegate_ruff,
        "delegate_slither": _handle_delegate_slither,
        "quick_review": _handle_quick_review,
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
