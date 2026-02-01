"""Claude Code hooks integration.

Provides PreToolUse and PostToolUse hooks for Claude Code to enforce
code quality via Crucible reviews on file writes/edits.

Usage:
    crucible hooks claudecode init    # Generate .claude/settings.json
    crucible hooks claudecode hook    # Run as hook (receives JSON on stdin)

The hook receives JSON on stdin from Claude Code:
    {"tool_name": "Write", "tool_input": {"file_path": "...", "content": "..."}}

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

from crucible.enforcement.patterns import run_pattern_assertions
from crucible.enforcement.assertions import load_assertions

# Config file for Claude Code hook settings
CONFIG_FILE = Path(".crucible") / "claudecode.yaml"
CLAUDE_SETTINGS_FILE = Path(".claude") / "settings.json"


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


def main_init(repo_path: str | None = None) -> int:
    """Initialize Claude Code hooks for a project.

    Creates:
    - .claude/settings.json with PostToolUse hook
    - .crucible/claudecode.yaml config template

    Returns:
        Exit code
    """
    settings_path = generate_settings_json(repo_path)
    config_path = generate_config_template(repo_path)

    print(f"Created Claude Code settings: {settings_path}")
    print(f"Created Crucible config: {config_path}")
    print()
    print("Crucible will now review files when Claude edits them.")
    print("Configure behavior in .crucible/claudecode.yaml")

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

    # hook command (called by Claude Code)
    subparsers.add_parser("hook", help="Run hook (reads from stdin)")

    args = parser.parse_args()

    if args.command == "init":
        return main_init(args.path)
    elif args.command == "hook":
        return run_hook()

    return 0


if __name__ == "__main__":
    sys.exit(main())
