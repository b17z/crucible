"""crucible MCP server - code review orchestration."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from crucible.domain.detection import detect_domain, get_personas_for_domain
from crucible.knowledge.loader import get_persona_section, load_principles
from crucible.models import Domain, Severity, ToolFinding
from crucible.tools.delegation import delegate_ruff, delegate_semgrep, delegate_slither

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
            description="Full code review: detect domain, run tools, apply persona perspective",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The source code to review",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional file path for domain detection",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Override domain (smart_contract, frontend, backend, infrastructure)",
                    },
                    "persona": {
                        "type": "string",
                        "description": "Specific persona to use (security, web3, backend, etc.)",
                    },
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="quick_review",
            description="Fast review: run tools only, no persona interpretation (good for CI)",
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
                        "description": "Tools to run (semgrep, ruff, slither). Default: auto-detect",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="detect_domain",
            description="Auto-detect code domain from content and file path",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The source code content",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional file path",
                    },
                },
                "required": ["code"],
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
            name="get_persona",
            description="Get a specific persona's review perspective",
            inputSchema={
                "type": "object",
                "properties": {
                    "persona": {
                        "type": "string",
                        "description": "Persona name (security, web3, backend, devops, etc.)",
                    },
                },
                "required": ["persona"],
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
    ]


def _handle_detect_domain(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle detect_domain tool."""
    code = arguments.get("code", "")
    file_path = arguments.get("file_path")
    result = detect_domain(code, file_path)

    if result.is_ok:
        domain = result.value
        personas = get_personas_for_domain(domain)
        return [
            TextContent(
                type="text",
                text=f"**Domain:** {domain.value}\n**Relevant personas:** {', '.join(personas)}",
            )
        ]
    return [TextContent(type="text", text=f"Error: {result.error}")]


def _handle_get_principles(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_principles tool."""
    topic = arguments.get("topic")
    result = load_principles(topic)

    if result.is_ok:
        return [TextContent(type="text", text=result.value)]
    return [TextContent(type="text", text=f"Error: {result.error}")]


def _handle_get_persona(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_persona tool."""
    persona = arguments.get("persona", "")
    principles_result = load_principles("checklist")

    if principles_result.is_err:
        return [TextContent(type="text", text=f"Error: {principles_result.error}")]

    section = get_persona_section(persona, principles_result.value)
    if section:
        return [TextContent(type="text", text=section)]
    return [TextContent(type="text", text=f"Persona not found: {persona}")]


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


def _handle_quick_review(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle quick_review tool."""
    path = arguments.get("path", "")
    tools = arguments.get("tools")

    # Auto-detect tools based on file extension if not specified
    if not tools:
        if path.endswith(".sol"):
            tools = ["slither", "semgrep"]
        elif path.endswith(".py"):
            tools = ["ruff", "semgrep"]
        else:
            tools = ["semgrep"]

    all_findings: list[str] = []

    if "semgrep" in tools:
        result = delegate_semgrep(path)
        if result.is_ok:
            all_findings.append("## Semgrep\n" + _format_findings(result.value))
        else:
            all_findings.append(f"## Semgrep\nError: {result.error}")

    if "ruff" in tools:
        result = delegate_ruff(path)
        if result.is_ok:
            all_findings.append("## Ruff\n" + _format_findings(result.value))
        else:
            all_findings.append(f"## Ruff\nError: {result.error}")

    if "slither" in tools:
        result = delegate_slither(path)
        if result.is_ok:
            all_findings.append("## Slither\n" + _format_findings(result.value))
        else:
            all_findings.append(f"## Slither\nError: {result.error}")

    return [TextContent(type="text", text="\n\n".join(all_findings))]


def _handle_review(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle review tool."""
    code = arguments.get("code", "")
    file_path = arguments.get("file_path")
    domain_override = arguments.get("domain")
    persona_name = arguments.get("persona")

    # Detect domain
    if domain_override:
        try:
            domain = Domain(domain_override)
        except ValueError:
            domain = Domain.UNKNOWN
    else:
        result = detect_domain(code, file_path)
        domain = result.value if result.is_ok else Domain.UNKNOWN

    # Get relevant personas
    personas = get_personas_for_domain(domain)
    if persona_name:
        personas = [persona_name]

    # Build review output
    parts: list[str] = []
    parts.append("# Code Review\n")
    parts.append(f"**Domain:** {domain.value}")
    parts.append(f"**Personas:** {', '.join(personas)}\n")

    # Load persona perspective
    principles_result = load_principles("checklist")
    if principles_result.is_ok:
        for p in personas[:1]:  # MVP: just first persona
            section = get_persona_section(p, principles_result.value)
            if section:
                parts.append(f"\n## {p.title()} Perspective\n")
                parts.append(section)

    parts.append("\n---\n")
    parts.append("*Use `quick_review` with a file path to run static analysis tools.*")

    return [TextContent(type="text", text="\n".join(parts))]


@server.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    handlers = {
        "detect_domain": _handle_detect_domain,
        "get_principles": _handle_get_principles,
        "get_persona": _handle_get_persona,
        "delegate_semgrep": _handle_delegate_semgrep,
        "delegate_ruff": _handle_delegate_ruff,
        "delegate_slither": _handle_delegate_slither,
        "quick_review": _handle_quick_review,
        "review": _handle_review,
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
