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

    # Deterministic verifier tier: suppress known false-positive shapes
    verify: bool = True

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
        verify=data.get("verify", True),
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

    # Add PreToolUse pre-check for Edit|Write (deny before content lands)
    pre_tool_use = existing["hooks"].get("PreToolUse", [])

    crucible_pretool_exists = any(
        "crucible hooks claudecode pretool"
        in (hook["hooks"][0].get("command", "") if hook.get("hooks") else "")
        for hook in pre_tool_use
        if isinstance(hook, dict)
    )

    if not crucible_pretool_exists:
        pre_tool_use.append({
            "matcher": "Edit|Write",
            "hooks": [
                {
                    "type": "command",
                    "command": "crucible hooks claudecode pretool"
                }
            ]
        })
        existing["hooks"]["PreToolUse"] = pre_tool_use

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

    # --- v2 hook scripts (Phase 1b + Phase 4) ---
    # These ship as package files under interfaces/claude_code/. Register
    # each idempotently against its event. A registration is identified by
    # the script's basename appearing in the command, so re-running init
    # never duplicates.
    _register_v2_hooks(existing["hooks"])

    # Write settings
    with open(settings_path, "w") as f:
        json.dump(existing, f, indent=2)

    return str(settings_path)


def _v2_hook_path(*parts: str) -> str:
    """Absolute path to a bundled v2 hook script."""
    base = Path(__file__).resolve().parent.parent / "interfaces" / "claude_code"
    return str(base.joinpath(*parts))


# (event, matcher, [path parts]) for every v2 hook script.
# matcher is None for events that don't take one (PreCompact/PostCompact).
_V2_HOOKS: list[tuple[str, str | None, tuple[str, ...]]] = [
    ("UserPromptSubmit", None, ("user_prompt_submit", "magic_comments.sh")),
    ("UserPromptSubmit", None, ("user_prompt_submit", "route.sh")),
    ("PreToolUse", "Bash", ("pre_tool_use", "npm_install_gate.sh")),
    ("PreToolUse", "Bash", ("pre_tool_use", "bash_deny.sh")),
    ("FileChanged", ".claude/settings.json|.mcp.json|.vscode/extensions.json",
     ("file_changed", "settings_integrity.sh")),
    ("FileChanged", ".claude/settings.json|.mcp.json|.vscode/extensions.json",
     ("file_changed", "config_diff.sh")),
    # Integrity recheck on config reloads and subagent completions: a
    # subagent (or anything that touched config) re-verifies the watched
    # files. Same script, different trigger; silent when clean.
    ("ConfigChange", None, ("file_changed", "settings_integrity.sh")),
    ("SubagentStop", None, ("file_changed", "settings_integrity.sh")),
    # Skill inheritance: subagents receive the parent session's activated
    # skills (recorded by route.sh in .crucible/active-skills.session).
    ("SubagentStart", None, ("subagent_start", "inherit.sh")),
    ("PreCompact", None, ("pre_compact", "protect.sh")),
    ("PostCompact", None, ("post_compact", "reinject.sh")),
    # GUARDRAILS.md auto-append: acknowledged candidate Signs (Task 6
    # layout, .crucible/inbox/signs/acked/) get rendered into the
    # project's GUARDRAILS.md at end of session.
    ("Stop", None, ("stop", "append_signs.sh")),
]


def _register_v2_hooks(hooks: dict) -> None:
    """Idempotently register the v2 hook scripts into a settings hooks dict."""
    for event, matcher, parts in _V2_HOOKS:
        script = parts[-1]
        path = _v2_hook_path(*parts)
        entries = hooks.get(event, [])

        already = any(
            script in (h["hooks"][0].get("command", "") if h.get("hooks") else "")
            for h in entries
            if isinstance(h, dict)
        )
        if already:
            continue

        entry: dict = {"hooks": [{"type": "command", "command": f"bash {path}"}]}
        if matcher is not None:
            entry["matcher"] = matcher
        entries.append(entry)
        hooks[event] = entries


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

    return _evaluate_content(file_path, file_content, assertions, config)


def _evaluate_content(
    file_path: str,
    content: str,
    assertions: list,
    config: ClaudeCodeHookConfig,
) -> int:
    """Run pattern assertions on content and turn findings into an exit code.

    Shared by the PostToolUse hook (content already on disk) and the
    PreToolUse pre-check (proposed content). 0 = allow, 2 = deny.
    """
    findings, checked, skipped = run_pattern_assertions(
        file_path=file_path,
        content=content,
        assertions=assertions,
    )

    if config.verify:
        from crucible.verify import run_verification
        _, findings, _ = run_verification(
            [], findings, file_contents={file_path: content})

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

    try:
        from crucible.signs import write_candidate

        for f in filtered_findings:
            write_candidate(
                trigger=f"assertion:{f.assertion_id}:{file_path}",
                instruction=f"Do not introduce `{f.assertion_id}` violations ({f.message})",
                reason="denied by the Claude Code assertion hook",
                source="claudecode-hook",
            )
    except OSError:
        pass

    return 2  # Exit 2 = block and show to Claude


def run_pretool_hook(stdin_data: str | None = None) -> int:
    """PreToolUse pre-check for Edit/Write: assert on the PROPOSED content
    so a violating write is denied before it lands (the PostToolUse hook
    remains the backstop for content that arrives by other paths).

    Write → the full new content is asserted. Edit → only the introduced
    new_string is asserted: a pre-existing violation elsewhere in the file
    must not block the unrelated edit that would fix or bypass it.

    Exit codes match run_hook: 0 = allow, 2 = deny.
    """
    if stdin_data is None:
        stdin_data = sys.stdin.read()

    try:
        input_data = json.loads(stdin_data)
    except json.JSONDecodeError as e:
        print(f"Failed to parse hook input: {e}", file=sys.stderr)
        return 0  # Allow on parse error

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name not in ("Edit", "Write"):
        return 0

    file_path = tool_input.get("file_path", "")
    if not file_path:
        return 0

    cwd = input_data.get("cwd", os.getcwd())
    config = load_claudecode_config(cwd)

    if _should_exclude(file_path, config.exclude):
        return 0
    if not config.run_assertions:
        return 0

    proposed = (
        tool_input.get("content") if tool_name == "Write" else tool_input.get("new_string")
    )
    if not proposed:
        return 0

    assertions, load_errors = load_assertions()
    if load_errors and config.verbose:
        for err in load_errors:
            print(f"Crucible hook warning: {err}", file=sys.stderr)
    if not assertions:
        return 0

    return _evaluate_content(file_path, proposed, assertions, config)


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


def _session_integrity_note(cwd_path: Path) -> str | None:
    """Return a warning if file-integrity baselines diverge, else None.

    Mirrors the FileChanged hook's logic at a high level: if
    .crucible/baselines/ exists, check each watched file against its
    baseline. We only WARN here (SessionStart shouldn't block the
    session); the blocking enforcement is the FileChanged hook.
    """
    from crucible.baselines import BASELINES_DIR, WATCHED_FILES, hash_file

    baselines_dir = cwd_path / BASELINES_DIR
    if not baselines_dir.exists():
        return None  # not opted in

    diverged: list[str] = []
    missing_baselines: list[str] = []
    for name, rel_watched in WATCHED_FILES:
        baseline = baselines_dir / f"{name}.sha256"
        watched = cwd_path / rel_watched
        if not baseline.exists():
            missing_baselines.append(name)
            continue
        expected = baseline.read_text().strip()
        actual = hash_file(watched) if watched.exists() else "MISSING"
        if expected != actual:
            diverged.append(name)

    if not diverged and not missing_baselines:
        return None

    lines = ["## ⚠️ Settings integrity"]
    if diverged:
        lines.append(
            f"These watched files diverge from their baseline: "
            f"{', '.join(diverged)}. Investigate before trusting this session — "
            f"see the supply-chain-2026 knowledge. Re-baseline with "
            f"`crucible baselines init --force` only if the change is known-good."
        )
    if missing_baselines:
        lines.append(
            f"Baseline(s) missing: {', '.join(missing_baselines)}. "
            f"The baselines directory exists but these are gone — suspicious."
        )
    return "\n".join(lines)


def _session_policy_note() -> str | None:
    """Names of active policies plus validator warnings, if any."""
    try:
        from crucible.policy import load_policies, validate_policies
    except ImportError:
        return None
    policies, errors = load_policies()
    if not policies and not errors:
        return None
    lines = [
        "## Active policies",
        "",
        ", ".join(sorted(p.name for p in policies))
        + " — cross-cutting enforcement composing the security skills.",
    ]
    for e in errors:
        lines.append(f"⚠ policy (parse): {e}")
    for issue in validate_policies(policies):
        lines.append(f"⚠ policy {issue.policy}: {issue.message}")
    return "\n".join(lines)


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

    # Review conventions (REVIEW.md body, frontmatter stripped)
    review_md = cwd_path / "REVIEW.md"
    if review_md.exists():
        try:
            text = review_md.read_text()
            if text.startswith("---"):
                closing = text.find("\n---", 3)
                if closing != -1:
                    text = text[closing + 4:]
            if text.strip():
                context_parts.append(text.strip())
        except OSError:
            pass

    # 3. Include recent findings if exists
    from crucible.history import load_recent_findings

    recent = load_recent_findings(cwd)
    if recent:
        context_parts.append(recent)

    # 4. Tier 1 skill discovery — cheap listing of available skills.
    try:
        from crucible.core.disclosure import discover_skills, discovery_digest

        summaries = discover_skills()
        if summaries:
            context_parts.append(discovery_digest(summaries))
    except Exception:
        pass  # Never fail the session on discovery errors.

    # 5. Settings-integrity check — surface a baseline divergence at
    #    session start (the FileChanged hook catches mid-session changes;
    #    this catches a change that happened while CC wasn't running).
    try:
        integrity_note = _session_integrity_note(cwd_path)
        if integrity_note:
            context_parts.append(integrity_note)
    except Exception:
        pass

    # 6. Active policy summary.
    try:
        policy_note = _session_policy_note()
        if policy_note:
            context_parts.append(policy_note)
    except Exception:
        pass

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
    print("  - PreToolUse: Bash deny-list + Edit/Write assertion pre-check")
    print("  - PostToolUse: Reviews files when Claude edits them")
    print("  - SessionStart: Injects enforcement context automatically")
    print("  - UserPromptSubmit: trigger routing + magic comments")
    print("  - FileChanged/ConfigChange/SubagentStop: settings integrity + config diff")
    print("  - SubagentStart: skill inheritance for spawned agents")
    print("  - PreCompact/PostCompact: context protection")
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

    # pretool command (called by Claude Code PreToolUse on Edit|Write)
    subparsers.add_parser("pretool", help="Run PreToolUse pre-check (reads from stdin)")

    # session command (called by Claude Code SessionStart)
    subparsers.add_parser("session", help="Run SessionStart hook (injects context)")

    args = parser.parse_args()

    if args.command == "init":
        return main_init(args.path)
    elif args.command == "hook":
        return run_hook()
    elif args.command == "pretool":
        return run_pretool_hook()
    elif args.command == "session":
        return run_session_hook()

    return 0


if __name__ == "__main__":
    sys.exit(main())
