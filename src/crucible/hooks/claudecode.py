"""Claude Code hooks integration.

Provides PreToolUse, PostToolUse, and SessionStart hooks for Claude Code
to enforce code quality via Crucible reviews and inject context.

Usage:
    crucible hooks claudecode init      # Generate .claude/settings.json
    crucible hooks claudecode hook      # PostToolUse hook (receives JSON on stdin)
    crucible hooks claudecode session   # SessionStart hook (injects context)

The hook receives JSON on stdin from Claude Code:
    {"tool_name": "Write", "tool_input": {"file_path": "...", "content": "..."}}

For SessionStart:
    {"cwd": "/path/to/project", "session_type": "startup|resume"}

Exit codes:
    0 = allow (optionally with JSON for structured control)
    2 = deny (stderr shown to Claude as feedback)
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from crucible.enforcement.assertions import load_assertions
from crucible.enforcement.patterns import run_pattern_assertions

# Config file for Claude Code hook settings
CONFIG_FILE = Path(".crucible") / "claudecode.yaml"
CLAUDE_SETTINGS_FILE = Path(".claude") / "settings.json"
SYSTEM_DIR = Path(".crucible") / "system"


@dataclass(frozen=True)
class ClaudeCodeHookConfig:
    """Configuration for Claude Code hooks."""

    # What to do when findings are detected
    on_finding: str = "deny"  # "deny", "warn", "allow"

    # Minimum severity to trigger action
    severity_threshold: str = "error"  # "error", "warning", "info"

    # Run pattern assertions (fast, free)
    run_assertions: bool = True

    # Run LLM assertions (expensive, semantic)
    run_llm_assertions: bool = False

    # Token budget for LLM assertions
    llm_token_budget: int = 2000

    # File patterns to exclude
    exclude: tuple[str, ...] = ()

    # Verbose output to stderr
    verbose: bool = False


def load_claudecode_config(repo_path: str | None = None) -> ClaudeCodeHookConfig:
    """Load Claude Code hook config."""
    config_path = Path(repo_path) / CONFIG_FILE if repo_path else CONFIG_FILE

    if not config_path.exists():
        return ClaudeCodeHookConfig()

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return ClaudeCodeHookConfig()

    return ClaudeCodeHookConfig(
        on_finding=data.get("on_finding", "deny"),
        severity_threshold=data.get("severity_threshold", "error"),
        run_assertions=data.get("run_assertions", True),
        run_llm_assertions=data.get("run_llm_assertions", False),
        llm_token_budget=data.get("llm_token_budget", 2000),
        exclude=tuple(data.get("exclude", [])),
        verbose=data.get("verbose", False),
    )


def generate_settings_json(repo_path: str | None = None) -> str:
    """Generate .claude/settings.json with Crucible hooks.

    Returns the path to the generated file.
    """
    base_path = Path(repo_path) if repo_path else Path(".")
    settings_path = base_path / CLAUDE_SETTINGS_FILE

    # Create .claude directory if needed
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing settings if present
    existing: dict = {}
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Ensure hooks section exists
    if "hooks" not in existing:
        existing["hooks"] = {}

    # Add PostToolUse hook for Edit|Write
    post_tool_use = existing["hooks"].get("PostToolUse", [])

    # Check if crucible hook already exists
    crucible_hook_exists = any(
        "crucible hooks claudecode" in hook.get("hooks", [{}])[0].get("command", "")
        for hook in post_tool_use
        if isinstance(hook, dict) and "hooks" in hook
    )

    if not crucible_hook_exists:
        post_tool_use.append({
            "matcher": "Edit|Write",
            "hooks": [
                {
                    "type": "command",
                    "command": "crucible hooks claudecode hook"
                }
            ]
        })
        existing["hooks"]["PostToolUse"] = post_tool_use

    # Add SessionStart hook for context injection
    session_start = existing["hooks"].get("SessionStart", [])

    # Check if crucible session hook already exists
    crucible_session_exists = any(
        "crucible hooks claudecode session" in hook.get("hooks", [{}])[0].get("command", "")
        for hook in session_start
        if isinstance(hook, dict) and "hooks" in hook
    )

    if not crucible_session_exists:
        session_start.append({
            "matcher": "startup|resume",
            "hooks": [
                {
                    "type": "command",
                    "command": "crucible hooks claudecode session"
                }
            ]
        })
        existing["hooks"]["SessionStart"] = session_start

    # Write settings
    with open(settings_path, "w") as f:
        json.dump(existing, f, indent=2)

    return str(settings_path)


def generate_config_template(repo_path: str | None = None) -> str:
    """Generate .crucible/claudecode.yaml config template.

    Returns the path to the generated file.
    """
    base_path = Path(repo_path) if repo_path else Path(".")
    config_path = base_path / CONFIG_FILE

    # Create .crucible directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        return str(config_path)  # Don't overwrite

    template = """\
# Crucible Claude Code Hook Configuration
# See: https://github.com/b17z/crucible

# What to do when findings are detected
# Options: deny (block and show to Claude), warn (allow but log), allow (silent)
on_finding: deny

# Minimum severity to trigger action
# Options: error, warning, info
severity_threshold: error

# Run pattern assertions (fast, free)
run_assertions: true

# Run LLM assertions (expensive, semantic) - off by default for hooks
run_llm_assertions: false

# Token budget for LLM assertions (if enabled)
llm_token_budget: 2000

# File patterns to exclude from review
exclude:
  - "**/*.md"
  - "**/test_*.py"
  - "**/*_test.py"

# Show verbose output in stderr (visible in Claude Code verbose mode)
verbose: false
"""

    with open(config_path, "w") as f:
        f.write(template)

    return str(config_path)


def _should_exclude(file_path: str, exclude_patterns: tuple[str, ...]) -> bool:
    """Check if file should be excluded."""
    from fnmatch import fnmatch
    return any(fnmatch(file_path, pattern) for pattern in exclude_patterns)


def _get_language_from_path(file_path: str) -> str | None:
    """Get language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".sol": "solidity",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".java": "java",
    }
    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext)


def run_hook(stdin_data: str | None = None) -> int:
    """Run the Claude Code hook.

    Reads tool input from stdin, runs Crucible review, returns exit code.

    Exit codes:
        0 = allow (with optional JSON output)
        2 = deny (stderr shown to Claude)

    Returns:
        Exit code
    """
    # Read from stdin if not provided
    if stdin_data is None:
        stdin_data = sys.stdin.read()

    # Parse input
    try:
        input_data = json.loads(stdin_data)
    except json.JSONDecodeError as e:
        print(f"Failed to parse hook input: {e}", file=sys.stderr)
        return 0  # Allow on parse error

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only process Edit and Write tools
    if tool_name not in ("Edit", "Write"):
        return 0

    file_path = tool_input.get("file_path", "")
    if not file_path:
        return 0

    # Get content for Write, or we'll read from disk for Edit
    content = tool_input.get("content") or tool_input.get("new_string")

    # Load config
    cwd = input_data.get("cwd", os.getcwd())
    config = load_claudecode_config(cwd)

    if config.verbose:
        print(f"Crucible hook: reviewing {file_path}", file=sys.stderr)

    # Check exclusions
    if _should_exclude(file_path, config.exclude):
        if config.verbose:
            print(f"Crucible hook: {file_path} excluded", file=sys.stderr)
        return 0

    # Skip if assertions disabled
    if not config.run_assertions:
        return 0

    # Load assertions
    assertions, load_errors = load_assertions()
    if load_errors and config.verbose:
        for err in load_errors:
            print(f"Crucible hook warning: {err}", file=sys.stderr)

    if not assertions:
        return 0

    # For Edit tool, we need to read the file and apply the edit
    # For Write tool, we have the content directly
    if tool_name == "Write" and content:
        file_content = content
    elif tool_name == "Edit":
        # For Edit, the file should already exist on disk after PostToolUse
        full_path = Path(cwd) / file_path if not Path(file_path).is_absolute() else Path(file_path)
        if full_path.exists():
            try:
                file_content = full_path.read_text()
            except OSError:
                return 0  # Allow on read error
        else:
            return 0  # Allow if file doesn't exist
    else:
        return 0  # No content to analyze

    # Run pattern assertions
    findings, checked, skipped = run_pattern_assertions(
        file_path=file_path,
        content=file_content,
        assertions=assertions,
    )

    # Filter by severity threshold
    severity_order = {"error": 0, "warning": 1, "info": 2}
    threshold = severity_order.get(config.severity_threshold, 1)

    filtered_findings = [
        f for f in findings
        if severity_order.get(f.severity, 2) <= threshold and not f.suppressed
    ]

    if not filtered_findings:
        if config.verbose:
            print(f"Crucible hook: {file_path} passed ({checked} assertions)", file=sys.stderr)
        return 0

    # Handle findings based on config
    if config.on_finding == "allow":
        return 0

    # Format findings for Claude
    messages = []
    for f in filtered_findings:
        messages.append(f"[{f.severity.upper()}] {f.assertion_id}: {f.message}")
        messages.append(f"  at {f.location}")
        if f.match_text:
            messages.append(f"  matched: {f.match_text[:100]}")

    output = f"Crucible found {len(filtered_findings)} issue(s) in {file_path}:\n"
    output += "\n".join(messages)

    if config.on_finding == "warn":
        # Warn but allow
        print(output, file=sys.stderr)
        return 0

    # Deny (default)
    print(output, file=sys.stderr)
    return 2  # Exit 2 = block and show to Claude


def _generate_enforcement_summary(assertions: list) -> str:
    """Generate markdown summary of active enforcement.

    Args:
        assertions: List of Assertion objects

    Returns:
        Markdown string summarizing what's enforced
    """
    parts = ["# Crucible Enforcement Active\n"]
    parts.append("These patterns are enforced. Crucible will flag violations.\n")

    # Group by priority
    by_priority: dict[str, list] = {"critical": [], "high": [], "medium": [], "low": []}
    for a in assertions:
        # Only include code assertions, not prewrite
        if getattr(a, "scope", "code") == "code":
            priority_val = a.priority.value if hasattr(a.priority, "value") else str(a.priority)
            if priority_val in by_priority:
                by_priority[priority_val].append(a)

    for priority in ["critical", "high", "medium"]:
        items = by_priority[priority]
        if items:
            parts.append(f"\n## {priority.title()} Priority\n")
            # Cap at 10 per priority to avoid overly long context
            for a in items[:10]:
                parts.append(f"- **{a.id}**: {a.message}")
            if len(items) > 10:
                parts.append(f"- ... and {len(items) - 10} more")

    parts.append("\n\nRun `crucible review` before committing.")
    return "\n".join(parts)


def run_session_hook(stdin_data: str | None = None) -> int:
    """Run SessionStart hook for Crucible context injection.

    Injects enforcement context into Claude Code sessions:
    - Active assertions (what patterns are enforced)
    - System files (.crucible/system/*.md)
    - Recent findings (from last review)

    Args:
        stdin_data: JSON input from Claude Code (optional, reads from stdin)

    Returns:
        Exit code (always 0, outputs JSON with additionalContext)
    """
    # Read from stdin if not provided
    if stdin_data is None:
        stdin_data = sys.stdin.read()

    # Parse input
    try:
        input_data = json.loads(stdin_data)
    except json.JSONDecodeError:
        return 0  # Silent fail, don't block session

    cwd = input_data.get("cwd", os.getcwd())
    cwd_path = Path(cwd)

    context_parts: list[str] = []

    # 1. Generate enforcement summary from active assertions
    try:
        assertions, _ = load_assertions()
        if assertions:
            context_parts.append(_generate_enforcement_summary(assertions))
    except Exception:
        pass  # Don't fail session on assertion loading errors

    # 2. Load static system files (.crucible/system/*.md)
    system_dir = cwd_path / SYSTEM_DIR
    if system_dir.exists():
        try:
            for md_file in sorted(system_dir.glob("*.md")):
                content = md_file.read_text()
                if content.strip():
                    # Use filename (without extension) as section header
                    header = md_file.stem.replace("-", " ").replace("_", " ").title()
                    context_parts.append(f"## {header}\n\n{content}")
        except OSError:
            pass  # Ignore file read errors

    # 3. Include recent findings if exists
    from crucible.history import load_recent_findings

    recent = load_recent_findings(cwd)
    if recent:
        context_parts.append(recent)

    # Output JSON for SessionStart hook
    if context_parts:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n\n---\n\n".join(context_parts)
            }
        }
        print(json.dumps(output))

    return 0


def generate_system_templates(repo_path: str | None = None) -> list[str]:
    """Generate template files in .crucible/system/.

    Creates starter templates for team patterns and focus areas.

    Args:
        repo_path: Repository path

    Returns:
        List of created file paths
    """
    base_path = Path(repo_path) if repo_path else Path(".")
    system_dir = base_path / SYSTEM_DIR

    # Create system directory
    system_dir.mkdir(parents=True, exist_ok=True)

    created: list[str] = []

    # Team patterns template
    team_patterns_file = system_dir / "team-patterns.md"
    if not team_patterns_file.exists():
        team_patterns_content = """\
# Team Patterns

<!-- Add team-specific patterns and conventions here -->
<!-- This file is automatically injected into every Claude Code session -->

## Code Style
- Follow existing patterns in the codebase
- Keep functions focused and small

## Review Guidelines
- All code changes should be reviewed before committing
- Run `crucible review` to check for issues

## Project Conventions
<!-- Add project-specific conventions here -->
"""
        team_patterns_file.write_text(team_patterns_content)
        created.append(str(team_patterns_file))

    # Focus template
    focus_file = system_dir / "focus.md"
    if not focus_file.exists():
        focus_content = """\
# Current Focus

<!-- Add current priorities here -->
<!-- This file is automatically injected into every Claude Code session -->

## Active Work
<!-- What you're currently working on -->

## Known Issues
<!-- Issues to be aware of -->

## Blocked By
<!-- Dependencies or blockers -->
"""
        focus_file.write_text(focus_content)
        created.append(str(focus_file))

    return created


def main_init(repo_path: str | None = None) -> int:
    """Initialize Claude Code hooks for a project.

    Creates:
    - .claude/settings.json with PostToolUse and SessionStart hooks
    - .crucible/claudecode.yaml config template

    Returns:
        Exit code
    """
    settings_path = generate_settings_json(repo_path)
    config_path = generate_config_template(repo_path)

    print(f"Created Claude Code settings: {settings_path}")
    print(f"Created Crucible config: {config_path}")
    print()
    print("Crucible hooks installed:")
    print("  - PostToolUse: Reviews files when Claude edits them")
    print("  - SessionStart: Injects enforcement context automatically")
    print()
    print("Configure behavior in .crucible/claudecode.yaml")
    print()
    print("Optional: Create .crucible/system/*.md files for team context")
    print("  Run 'crucible system init' to create templates")

    return 0


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="crucible-claudecode",
        description="Claude Code hooks integration",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize Claude Code hooks")
    init_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # hook command (called by Claude Code PostToolUse)
    subparsers.add_parser("hook", help="Run PostToolUse hook (reads from stdin)")

    # session command (called by Claude Code SessionStart)
    subparsers.add_parser("session", help="Run SessionStart hook (injects context)")

    args = parser.parse_args()

    if args.command == "init":
        return main_init(args.path)
    elif args.command == "hook":
        return run_hook()
    elif args.command == "session":
        return run_session_hook()

    return 0


if __name__ == "__main__":
    sys.exit(main())
