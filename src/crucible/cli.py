"""crucible CLI."""

import sys


def main() -> None:
    """CLI entry point."""
    print("crucible - Code review orchestration")
    print()
    print("Usage:")
    print("  crucible-mcp    Run as MCP server (for Claude Code)")
    print()
    print("MCP Tools available:")
    print("  review          Full code review with persona perspective")
    print("  quick_review    Fast review with static analysis tools")
    print("  detect_domain   Auto-detect code domain")
    print("  get_principles  Load engineering principles")
    print("  get_persona     Get persona review perspective")
    print("  delegate_*      Run specific tools (semgrep, ruff, slither)")
    sys.exit(0)


if __name__ == "__main__":
    main()
