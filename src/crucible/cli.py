"""crucible CLI."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from crucible.enforcement.models import ComplianceConfig

# Skills directories
SKILLS_BUNDLED = Path(__file__).parent / "skills"
SKILLS_USER = Path.home() / ".claude" / "crucible" / "skills"
SKILLS_PROJECT = Path(".crucible") / "skills"

# Knowledge directories
KNOWLEDGE_BUNDLED = Path(__file__).parent / "knowledge" / "principles"
KNOWLEDGE_USER = Path.home() / ".claude" / "crucible" / "knowledge"
KNOWLEDGE_PROJECT = Path(".crucible") / "knowledge"


def resolve_skill(skill_name: str) -> tuple[Path | None, str]:
    """Find skill with cascade priority.

    Returns (path, source) where source is 'project', 'user', or 'bundled'.
    """
    # 1. Project-level (highest priority)
    project_path = SKILLS_PROJECT / skill_name / "SKILL.md"
    if project_path.exists():
        return project_path, "project"

    # 2. User-level
    user_path = SKILLS_USER / skill_name / "SKILL.md"
    if user_path.exists():
        return user_path, "user"

    # 3. Bundled (lowest priority)
    bundled_path = SKILLS_BUNDLED / skill_name / "SKILL.md"
    if bundled_path.exists():
        return bundled_path, "bundled"

    return None, ""


def get_all_skill_names() -> set[str]:
    """Get all available skill names from all sources."""
    names: set[str] = set()

    for source_dir in [SKILLS_BUNDLED, SKILLS_USER, SKILLS_PROJECT]:
        if source_dir.exists():
            for skill_dir in source_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    names.add(skill_dir.name)

    return names


def resolve_knowledge(filename: str) -> tuple[Path | None, str]:
    """Find knowledge file with cascade priority.

    Returns (path, source) where source is 'project', 'user', or 'bundled'.
    """
    # 1. Project-level (highest priority)
    project_path = KNOWLEDGE_PROJECT / filename
    if project_path.exists():
        return project_path, "project"

    # 2. User-level
    user_path = KNOWLEDGE_USER / filename
    if user_path.exists():
        return user_path, "user"

    # 3. Bundled (lowest priority)
    bundled_path = KNOWLEDGE_BUNDLED / filename
    if bundled_path.exists():
        return bundled_path, "bundled"

    return None, ""


def get_all_knowledge_files() -> set[str]:
    """Get all available knowledge file names from all sources."""
    files: set[str] = set()

    for source_dir in [KNOWLEDGE_BUNDLED, KNOWLEDGE_USER, KNOWLEDGE_PROJECT]:
        if source_dir.exists():
            for file_path in source_dir.iterdir():
                if file_path.is_file() and file_path.suffix == ".md":
                    files.add(file_path.name)

    return files


# --- Skills commands ---


def cmd_skills_install(args: argparse.Namespace) -> int:
    """Install crucible skills to ~/.claude/crucible/skills/."""
    if not SKILLS_BUNDLED.exists():
        print(f"Error: Skills source not found at {SKILLS_BUNDLED}")
        return 1

    # Create destination directory
    SKILLS_USER.mkdir(parents=True, exist_ok=True)

    installed = []
    for skill_dir in SKILLS_BUNDLED.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            dest = SKILLS_USER / skill_dir.name
            if dest.exists() and not args.force:
                print(f"  Skip: {skill_dir.name} (exists, use --force to overwrite)")
                continue

            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill_dir, dest)
            installed.append(skill_dir.name)
            print(f"  Installed: {skill_dir.name}")

    if installed:
        print(f"\n✓ Installed {len(installed)} skill(s) to {SKILLS_USER}")
    else:
        print("\nNo skills to install.")

    return 0


def cmd_skills_list(args: argparse.Namespace) -> int:
    """List available and installed skills."""
    print("Bundled skills:")
    if SKILLS_BUNDLED.exists():
        for skill_dir in sorted(SKILLS_BUNDLED.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                print(f"  - {skill_dir.name}")
    else:
        print("  (none)")

    print("\nUser skills (~/.claude/crucible/skills/):")
    if SKILLS_USER.exists():
        found = False
        for skill_dir in sorted(SKILLS_USER.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                print(f"  - {skill_dir.name}")
                found = True
        if not found:
            print("  (none)")
    else:
        print("  (none)")

    print("\nProject skills (.crucible/skills/):")
    if SKILLS_PROJECT.exists():
        found = False
        for skill_dir in sorted(SKILLS_PROJECT.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                print(f"  - {skill_dir.name}")
                found = True
        if not found:
            print("  (none)")
    else:
        print("  (none)")

    return 0


def cmd_skills_init(args: argparse.Namespace) -> int:
    """Copy a skill to .crucible/skills/ for project-level customization."""
    skill_name = args.skill

    # Find source skill (user or bundled, not project)
    user_path = SKILLS_USER / skill_name / "SKILL.md"
    bundled_path = SKILLS_BUNDLED / skill_name / "SKILL.md"

    if user_path.exists():
        source_path = user_path.parent
        source_label = "user"
    elif bundled_path.exists():
        source_path = bundled_path.parent
        source_label = "bundled"
    else:
        print(f"Error: Skill '{skill_name}' not found")
        print(f"  Checked: {SKILLS_USER / skill_name}")
        print(f"  Checked: {SKILLS_BUNDLED / skill_name}")
        return 1

    # Destination
    dest_path = SKILLS_PROJECT / skill_name

    if dest_path.exists() and not args.force:
        print(f"Error: {dest_path} already exists")
        print("  Use --force to overwrite")
        return 1

    # Create and copy
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        shutil.rmtree(dest_path)
    shutil.copytree(source_path, dest_path)

    print(f"✓ Initialized {skill_name} from {source_label}")
    print(f"  → {dest_path}/SKILL.md")
    print("\nEdit this file to customize the skill for your project.")

    return 0


def cmd_skills_show(args: argparse.Namespace) -> int:
    """Show skill resolution - which file is active."""
    skill_name = args.skill

    active_path, active_source = resolve_skill(skill_name)

    if not active_path:
        print(f"Skill '{skill_name}' not found")
        return 1

    print(f"{skill_name}")

    # Project-level
    project_path = SKILLS_PROJECT / skill_name / "SKILL.md"
    if project_path.exists():
        marker = " ← active" if active_source == "project" else ""
        print(f"  Project: {project_path}{marker}")
    else:
        print("  Project: (not set)")

    # User-level
    user_path = SKILLS_USER / skill_name / "SKILL.md"
    if user_path.exists():
        marker = " ← active" if active_source == "user" else ""
        print(f"  User:    {user_path}{marker}")
    else:
        print("  User:    (not installed)")

    # Bundled
    bundled_path = SKILLS_BUNDLED / skill_name / "SKILL.md"
    if bundled_path.exists():
        marker = " ← active" if active_source == "bundled" else ""
        print(f"  Bundled: {bundled_path}{marker}")
    else:
        print("  Bundled: (not available)")

    return 0


# --- Knowledge commands ---


def cmd_knowledge_list(args: argparse.Namespace) -> int:
    """List available knowledge files."""
    print("Bundled knowledge (templates):")
    if KNOWLEDGE_BUNDLED.exists():
        for file_path in sorted(KNOWLEDGE_BUNDLED.iterdir()):
            if file_path.is_file() and file_path.suffix == ".md":
                print(f"  - {file_path.name}")
    else:
        print("  (none)")

    print("\nUser knowledge (~/.claude/crucible/knowledge/):")
    if KNOWLEDGE_USER.exists():
        found = False
        for file_path in sorted(KNOWLEDGE_USER.iterdir()):
            if file_path.is_file() and file_path.suffix == ".md":
                print(f"  - {file_path.name}")
                found = True
        if not found:
            print("  (none)")
    else:
        print("  (none)")

    print("\nProject knowledge (.crucible/knowledge/):")
    if KNOWLEDGE_PROJECT.exists():
        found = False
        for file_path in sorted(KNOWLEDGE_PROJECT.iterdir()):
            if file_path.is_file() and file_path.suffix == ".md":
                print(f"  - {file_path.name}")
                found = True
        if not found:
            print("  (none)")
    else:
        print("  (none)")

    return 0


def cmd_knowledge_init(args: argparse.Namespace) -> int:
    """Copy a knowledge file to .crucible/knowledge/ for project customization."""
    filename = args.file
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    # Find source (user or bundled, not project)
    user_path = KNOWLEDGE_USER / filename
    bundled_path = KNOWLEDGE_BUNDLED / filename

    if user_path.exists():
        source_path = user_path
        source_label = "user"
    elif bundled_path.exists():
        source_path = bundled_path
        source_label = "bundled"
    else:
        print(f"Error: Knowledge file '{filename}' not found")
        print(f"  Checked: {KNOWLEDGE_USER / filename}")
        print(f"  Checked: {KNOWLEDGE_BUNDLED / filename}")
        print("\nAvailable files:")
        for f in sorted(get_all_knowledge_files()):
            print(f"  - {f}")
        return 1

    # Destination
    dest_path = KNOWLEDGE_PROJECT / filename

    if dest_path.exists() and not args.force:
        print(f"Error: {dest_path} already exists")
        print("  Use --force to overwrite")
        return 1

    # Create and copy
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)

    print(f"✓ Initialized {filename} from {source_label}")
    print(f"  → {dest_path}")
    print("\nEdit this file to customize for your project.")

    return 0


def cmd_knowledge_show(args: argparse.Namespace) -> int:
    """Show knowledge resolution - which file is active."""
    filename = args.file
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    active_path, active_source = resolve_knowledge(filename)

    if not active_path:
        print(f"Knowledge file '{filename}' not found")
        return 1

    print(f"{filename}")

    # Project-level
    project_path = KNOWLEDGE_PROJECT / filename
    if project_path.exists():
        marker = " ← active" if active_source == "project" else ""
        print(f"  Project: {project_path}{marker}")
    else:
        print("  Project: (not set)")

    # User-level
    user_path = KNOWLEDGE_USER / filename
    if user_path.exists():
        marker = " ← active" if active_source == "user" else ""
        print(f"  User:    {user_path}{marker}")
    else:
        print("  User:    (not installed)")

    # Bundled
    bundled_path = KNOWLEDGE_BUNDLED / filename
    if bundled_path.exists():
        marker = " ← active" if active_source == "bundled" else ""
        print(f"  Bundled: {bundled_path}{marker}")
    else:
        print("  Bundled: (not available)")

    return 0


def cmd_knowledge_install(args: argparse.Namespace) -> int:
    """Install knowledge files to ~/.claude/crucible/knowledge/."""
    if not KNOWLEDGE_BUNDLED.exists():
        print(f"Error: Knowledge source not found at {KNOWLEDGE_BUNDLED}")
        return 1

    # Create destination directory
    KNOWLEDGE_USER.mkdir(parents=True, exist_ok=True)

    installed = []
    for file_path in KNOWLEDGE_BUNDLED.iterdir():
        if file_path.is_file() and file_path.suffix == ".md":
            dest = KNOWLEDGE_USER / file_path.name
            if dest.exists() and not args.force:
                print(f"  Skip: {file_path.name} (exists, use --force to overwrite)")
                continue

            shutil.copy2(file_path, dest)
            installed.append(file_path.name)
            print(f"  Installed: {file_path.name}")

    if installed:
        print(f"\n✓ Installed {len(installed)} file(s) to {KNOWLEDGE_USER}")
    else:
        print("\nNo files to install.")

    return 0


# --- Review command ---


def _load_review_config(repo_path: str | None = None) -> dict:
    """Load review config with cascade priority.

    Config file: .crucible/review.yaml or ~/.claude/crucible/review.yaml

    Example config:
        fail_on: high                    # default threshold
        fail_on_domain:                  # per-domain overrides
          smart_contract: critical       # stricter for smart contracts
          backend: high
        include_context: false
        skip_tools: []
        enforcement:
          compliance:
            enabled: true
            model: sonnet
            token_budget: 10000
            overflow_behavior: warn
    """
    import yaml

    config_data: dict = {}
    config_project = Path(".crucible/review.yaml")
    config_user = Path.home() / ".claude" / "crucible" / "review.yaml"

    if repo_path:
        config_project = Path(repo_path) / ".crucible" / "review.yaml"

    # Try project-level first
    if config_project.exists():
        try:
            with open(config_project) as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load {config_project}: {e}", file=sys.stderr)

    # Fall back to user-level
    if not config_data and config_user.exists():
        try:
            with open(config_user) as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load {config_user}: {e}", file=sys.stderr)

    return config_data


def _build_compliance_config(
    config: dict,
    cli_token_budget: int | None = None,
    cli_model: str | None = None,
    cli_no_compliance: bool = False,
) -> ComplianceConfig:
    """Build compliance config from config file and CLI overrides.

    Args:
        config: Loaded config dict
        cli_token_budget: CLI --token-budget override
        cli_model: CLI --compliance-model override
        cli_no_compliance: CLI --no-compliance flag

    Returns:
        ComplianceConfig instance
    """
    from crucible.enforcement.models import ComplianceConfig, OverflowBehavior

    # Get enforcement.compliance section from config
    enforcement_config = config.get("enforcement", {})
    compliance_section = enforcement_config.get("compliance", {})

    # Build config with defaults
    enabled = not cli_no_compliance and compliance_section.get("enabled", True)
    model = cli_model or compliance_section.get("model", "sonnet")
    token_budget = cli_token_budget if cli_token_budget is not None else compliance_section.get("token_budget", 10000)

    # Parse overflow behavior
    overflow_str = compliance_section.get("overflow_behavior", "warn")
    try:
        overflow_behavior = OverflowBehavior(overflow_str.lower())
    except ValueError:
        overflow_behavior = OverflowBehavior.WARN

    # Parse priority order
    priority_order = compliance_section.get("priority_order", ["critical", "high", "medium", "low"])
    if isinstance(priority_order, list):
        priority_order = tuple(priority_order)
    else:
        priority_order = ("critical", "high", "medium", "low")

    return ComplianceConfig(
        enabled=enabled,
        model=model,
        token_budget=token_budget,
        priority_order=priority_order,
        overflow_behavior=overflow_behavior,
    )


def _cmd_review_no_git(args: argparse.Namespace, path: str) -> int:
    """Run static analysis on a path without git awareness."""
    import json as json_mod
    from pathlib import Path

    from crucible.models import Domain, Severity, ToolFinding
    from crucible.review.core import (
        compute_severity_counts,
        deduplicate_findings,
        detect_domain_for_file,
        get_tools_for_domain,
        run_static_analysis,
    )

    path_obj = Path(path)
    if not path_obj.exists():
        print(f"Error: {path} does not exist")
        return 1

    # Load config from current directory or user level
    config = _load_review_config(".")

    # Parse severity threshold
    severity_order = ["critical", "high", "medium", "low", "info"]
    severity_map = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }
    default_threshold_str = args.fail_on or config.get("fail_on")
    default_threshold: Severity | None = None
    if default_threshold_str:
        default_threshold = severity_map.get(default_threshold_str.lower())

    skip_tools = set(config.get("skip_tools", []))

    # Collect files to analyze
    files_to_analyze: list[str] = []
    if path_obj.is_file():
        files_to_analyze = [str(path_obj)]
    else:
        # Recursively find files, respecting common ignores
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist"}
        for file_path in path_obj.rglob("*"):
            if file_path.is_file():
                # Skip ignored directories
                if any(ignored in file_path.parts for ignored in ignore_dirs):
                    continue
                files_to_analyze.append(str(file_path))

    if not files_to_analyze:
        print("No files to analyze.")
        return 0

    if not args.quiet and not args.json:
        print(f"Reviewing {len(files_to_analyze)} file(s) (no git)...")

    # Run analysis
    all_findings: list[ToolFinding] = []
    tool_errors: list[str] = []
    domains_detected: set[Domain] = set()
    all_domain_tags: set[str] = set()

    for file_path in files_to_analyze:
        domain, domain_tags = detect_domain_for_file(file_path)
        domains_detected.add(domain)
        all_domain_tags.update(domain_tags)

        tools = get_tools_for_domain(domain, domain_tags)
        tools = [t for t in tools if t not in skip_tools]

        findings, errors = run_static_analysis(file_path, domain, domain_tags, tools)
        all_findings.extend(findings)
        tool_errors.extend(errors)

    # Deduplicate
    all_findings = deduplicate_findings(all_findings)

    # Run enforcement assertions
    from crucible.review.core import run_enforcement

    compliance_config = _build_compliance_config(
        config,
        cli_token_budget=getattr(args, "token_budget", None),
        cli_model=getattr(args, "compliance_model", None),
        cli_no_compliance=getattr(args, "no_compliance", False),
    )

    # Use current directory as repo root for enforcement
    enforcement_findings, enforcement_errors, assertions_checked, assertions_skipped, budget_state = (
        run_enforcement(
            ".",
            changed_files=files_to_analyze,
            repo_root=".",
            compliance_config=compliance_config,
        )
    )
    tool_errors.extend(enforcement_errors)

    # Compute severity summary
    severity_counts = compute_severity_counts(all_findings)

    # Determine pass/fail
    passed = True
    if default_threshold:
        threshold_idx = severity_order.index(default_threshold.value)
        for sev in severity_order[: threshold_idx + 1]:
            if severity_counts.get(sev, 0) > 0:
                passed = False
                break

    # Output
    if args.json:
        output = {
            "mode": "no-git",
            "files_analyzed": len(files_to_analyze),
            "domains_detected": [d.value for d in domains_detected],
            "findings": [
                {
                    "tool": f.tool,
                    "rule": f.rule,
                    "severity": f.severity.value,
                    "message": f.message,
                    "location": f.location,
                    "suggestion": f.suggestion,
                }
                for f in all_findings
            ],
            "enforcement": {
                "findings": [
                    {
                        "assertion_id": f.assertion_id,
                        "severity": f.severity,
                        "message": f.message,
                        "location": f.location,
                        "source": f.source,
                    }
                    for f in enforcement_findings
                ],
                "assertions_checked": assertions_checked,
                "assertions_skipped": assertions_skipped,
                "tokens_used": budget_state.tokens_used if budget_state else 0,
            },
            "severity_counts": severity_counts,
            "passed": passed,
            "threshold": default_threshold.value if default_threshold else None,
            "errors": tool_errors,
        }
        print(json_mod.dumps(output, indent=2))
    else:
        # Text output
        if all_findings:
            print(f"\nFound {len(all_findings)} static analysis issue(s):\n")
            for f in all_findings:
                sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(
                    f.severity.value, "⚪"
                )
                print(f"{sev_icon} [{f.severity.value.upper()}] {f.location}")
                print(f"   {f.tool}/{f.rule}: {f.message}")
                if f.suggestion:
                    print(f"   💡 {f.suggestion}")
                print()

        # Enforcement findings
        if enforcement_findings:
            print(f"\nEnforcement Assertions ({len(enforcement_findings)}):")
            for f in enforcement_findings:
                sev_icon = {"error": "🔴", "warning": "🟠", "info": "⚪"}.get(f.severity, "⚪")
                source_tag = "[LLM]" if f.source == "llm" else "[Pattern]"
                print(f"  {sev_icon} [{f.severity.upper()}] {source_tag} {f.assertion_id}: {f.location}")
                print(f"    {f.message}")
                print()

        if not all_findings and not enforcement_findings:
            print("\n✅ No issues found.")

        # Summary
        if severity_counts:
            counts_str = ", ".join(f"{k}: {v}" for k, v in severity_counts.items() if v > 0)
            print(f"Summary: {counts_str}")

        if assertions_checked or assertions_skipped:
            print(f"Assertions: {assertions_checked} checked, {assertions_skipped} skipped")
            if budget_state and budget_state.tokens_used > 0:
                print(f"  LLM tokens used: {budget_state.tokens_used}")

        if tool_errors and not args.quiet:
            print(f"\n⚠️  {len(tool_errors)} tool error(s)")
            for err in tool_errors[:5]:
                print(f"   - {err}")

    return 0 if passed else 1


def cmd_review(args: argparse.Namespace) -> int:
    """Run code review on git changes or a path directly."""
    import json as json_mod

    from crucible.models import Domain, Severity, ToolFinding
    from crucible.review.core import (
        compute_severity_counts,
        deduplicate_findings,
        detect_domain_for_file,
        filter_findings_to_changes,
        get_tools_for_domain,
        run_static_analysis,
    )

    path = args.path or "."

    # Handle --no-git mode: simple static analysis without git awareness
    if getattr(args, "no_git", False):
        return _cmd_review_no_git(args, path)

    # Git-aware review mode
    from crucible.tools.git import (
        get_branch_diff,
        get_recent_commits,
        get_repo_root,
        get_staged_changes,
        get_unstaged_changes,
        is_git_repo,
    )

    mode = args.mode

    # Validate git repo
    if not is_git_repo(path):
        print(f"Error: {path} is not inside a git repository")
        print("Hint: Use --no-git to review files without git awareness")
        return 1

    root_result = get_repo_root(path)
    if root_result.is_err:
        print(f"Error: {root_result.error}")
        return 1

    repo_path = root_result.value

    # Load config
    config = _load_review_config(repo_path)

    # Parse severity threshold (CLI overrides config)
    severity_order = ["critical", "high", "medium", "low", "info"]
    severity_map = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }

    # Default threshold from CLI or config
    default_threshold_str = args.fail_on or config.get("fail_on")
    default_threshold: Severity | None = None
    if default_threshold_str:
        default_threshold = severity_map.get(default_threshold_str.lower())

    # Per-domain thresholds from config
    domain_thresholds: dict[Domain, Severity] = {}
    for domain_str, sev_str in config.get("fail_on_domain", {}).items():
        try:
            domain = Domain(domain_str)
        except ValueError:
            # Try common aliases
            domain_aliases = {
                "solidity": Domain.SMART_CONTRACT,
                "python": Domain.BACKEND,
                "typescript": Domain.FRONTEND,
                "javascript": Domain.FRONTEND,
            }
            domain = domain_aliases.get(domain_str.lower())
        if domain and sev_str:
            sev = severity_map.get(sev_str.lower())
            if sev:
                domain_thresholds[domain] = sev

    # Include context from config if not specified on CLI
    if not args.include_context and config.get("include_context"):
        args.include_context = True

    # Skip tools from config
    skip_tools = set(config.get("skip_tools", []))

    # Get changes based on mode
    if mode == "staged":
        context_result = get_staged_changes(repo_path)
    elif mode == "unstaged":
        context_result = get_unstaged_changes(repo_path)
    elif mode == "branch":
        base_branch = args.base if args.base else "main"
        context_result = get_branch_diff(repo_path, base_branch)
    elif mode == "commits":
        try:
            count = int(args.base) if args.base else 1
        except ValueError:
            print(f"Error: Invalid commit count '{args.base}'")
            return 1
        context_result = get_recent_commits(repo_path, count)
    else:
        print(f"Error: Unknown mode '{mode}'")
        return 1

    if context_result.is_err:
        print(f"Error: {context_result.error}")
        return 1

    context = context_result.value

    # Check for changes
    if not context.changes:
        if mode == "staged":
            print("No changes to review. Stage files with `git add` first.")
        elif mode == "unstaged":
            print("No unstaged changes to review.")
        else:
            print("No changes found.")
        return 0

    changed_files = [c.path for c in context.changes if c.status != "D"]
    if not changed_files:
        print("No files to analyze (only deletions).")
        return 0

    # Run analysis
    all_findings: list[ToolFinding] = []
    tool_errors: list[str] = []

    if not args.quiet and not args.json:
        print(f"Reviewing {len(changed_files)} file(s)...")

    # Track domains detected for per-domain threshold checking
    domains_detected: set[Domain] = set()
    all_domain_tags: set[str] = set()

    for file_path in changed_files:
        full_path = f"{repo_path}/{file_path}"
        domain, domain_tags = detect_domain_for_file(file_path)
        domains_detected.add(domain)
        all_domain_tags.update(domain_tags)

        # Get tools for this domain, applying skip_tools from config
        tools = get_tools_for_domain(domain, domain_tags)
        tools = [t for t in tools if t not in skip_tools]

        # Run static analysis
        findings, errors = run_static_analysis(full_path, domain, domain_tags, tools)
        all_findings.extend(findings)
        for err in errors:
            tool_errors.append(f"{err} ({file_path})")

    # Filter findings to changed lines and deduplicate
    filtered_findings = filter_findings_to_changes(
        all_findings, context, args.include_context
    )
    filtered_findings = deduplicate_findings(filtered_findings)

    # Match skills and load knowledge based on detected domains
    from crucible.knowledge.loader import load_knowledge_file
    from crucible.skills.loader import (
        get_knowledge_for_skills,
        load_skill,
        match_skills_for_domain,
    )

    # Use first domain for primary matching (most files determine this)
    primary_domain = next(iter(domains_detected)) if domains_detected else Domain.UNKNOWN
    matched_skills = match_skills_for_domain(
        primary_domain, list(all_domain_tags), override=None
    )

    # Load skill content
    skill_names = [name for name, _ in matched_skills]
    skill_content: dict[str, str] = {}
    for skill_name, _triggers in matched_skills:
        result = load_skill(skill_name)
        if result.is_ok:
            _, content = result.value
            skill_content[skill_name] = content

    # Load linked knowledge
    knowledge_files = get_knowledge_for_skills(skill_names)
    knowledge_content: dict[str, str] = {}
    for filename in knowledge_files:
        result = load_knowledge_file(filename)
        if result.is_ok:
            knowledge_content[filename] = result.value

    # Run enforcement assertions (pattern + LLM)
    from crucible.review.core import run_enforcement

    compliance_config = _build_compliance_config(
        config,
        cli_token_budget=getattr(args, "token_budget", None),
        cli_model=getattr(args, "compliance_model", None),
        cli_no_compliance=getattr(args, "no_compliance", False),
    )

    enforcement_findings, enforcement_errors, assertions_checked, assertions_skipped, budget_state = (
        run_enforcement(
            repo_path,
            changed_files=changed_files,
            repo_root=repo_path,
            compliance_config=compliance_config,
        )
    )

    # Add enforcement errors to tool errors
    tool_errors.extend(enforcement_errors)

    # Compute severity summary
    severity_counts = compute_severity_counts(filtered_findings)

    # Determine pass/fail using per-domain thresholds
    # Use the strictest applicable threshold
    passed = True
    effective_threshold: Severity | None = default_threshold

    # Check for per-domain thresholds (use strictest)
    for domain in domains_detected:
        if domain in domain_thresholds:
            domain_thresh = domain_thresholds[domain]
            if effective_threshold is None:
                effective_threshold = domain_thresh
            else:
                # Use the stricter threshold (higher in severity_order = stricter)
                if severity_order.index(domain_thresh.value) < severity_order.index(
                    effective_threshold.value
                ):
                    effective_threshold = domain_thresh

    if effective_threshold:
        threshold_idx = severity_order.index(effective_threshold.value)
        for sev in severity_order[: threshold_idx + 1]:
            if severity_counts.get(sev, 0) > 0:
                passed = False
                break

    # Track which threshold was used for output
    threshold_used = effective_threshold.value if effective_threshold else None

    # Output
    if args.json:
        output = {
            "mode": mode,
            "files_changed": len(changed_files),
            "domains_detected": [d.value for d in domains_detected],
            "skills_matched": dict(matched_skills),
            "knowledge_loaded": list(knowledge_files),
            "findings": [
                {
                    "tool": f.tool,
                    "rule": f.rule,
                    "severity": f.severity.value,
                    "message": f.message,
                    "location": f.location,
                    "suggestion": f.suggestion,
                }
                for f in filtered_findings
            ],
            "enforcement": {
                "findings": [
                    {
                        "assertion_id": f.assertion_id,
                        "severity": f.severity,
                        "message": f.message,
                        "location": f.location,
                        "source": f.source,
                        "suppressed": f.suppressed,
                    }
                    for f in enforcement_findings
                ],
                "assertions_checked": assertions_checked,
                "assertions_skipped": assertions_skipped,
                "llm_tokens_used": budget_state.tokens_used if budget_state else 0,
            },
            "severity_counts": severity_counts,
            "threshold": threshold_used,
            "errors": tool_errors,
            "passed": passed,
        }
        print(json_mod.dumps(output, indent=2))
    elif getattr(args, "format", "text") == "report":
        # Markdown report format
        from datetime import datetime

        print("# Code Review Report\n")
        print(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"**Mode:** {mode} changes")
        print(f"**Files reviewed:** {len(changed_files)}")
        print(f"**Domains detected:** {', '.join(d.value for d in domains_detected)}")
        if threshold_used:
            print(f"**Threshold:** {threshold_used}")
        print()

        # Summary
        print("## Summary\n")
        if filtered_findings:
            total = len(filtered_findings)
            print(f"**{total} finding(s)** detected:\n")
            for sev in ["critical", "high", "medium", "low", "info"]:
                count = severity_counts.get(sev, 0)
                if count > 0:
                    print(f"- {sev.upper()}: {count}")
            print()
        else:
            print("No issues found in changed code.\n")

        # Files changed
        print("## Files Changed\n")
        for c in context.changes:
            status_char = {"A": "Added", "M": "Modified", "D": "Deleted", "R": "Renamed"}.get(c.status, "?")
            print(f"- `{c.path}` ({status_char})")
        print()

        # Skills matched
        if matched_skills:
            print("## Applicable Skills\n")
            for skill_name, triggers in matched_skills:
                print(f"- **{skill_name}**: matched on {', '.join(triggers)}")
            print()

        # Knowledge loaded
        if knowledge_files:
            print("## Knowledge Loaded\n")
            print(f"Files: {', '.join(sorted(knowledge_files))}")
            print()

        # Findings by severity
        if filtered_findings:
            print("## Findings\n")

            # Group by severity
            by_severity: dict[str, list] = {}
            for f in filtered_findings:
                sev = f.severity.value
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append(f)

            for sev in ["critical", "high", "medium", "low", "info"]:
                if sev not in by_severity:
                    continue
                print(f"### {sev.upper()}\n")
                for f in by_severity[sev]:
                    print(f"#### `{f.location}`\n")
                    print(f"**Tool:** {f.tool}  ")
                    print(f"**Rule:** {f.rule}  ")
                    print(f"**Message:** {f.message}")
                    if f.suggestion:
                        print(f"\n**Suggestion:** {f.suggestion}")
                    print()

        # Tool errors
        if tool_errors:
            print("## Tool Errors\n")
            for error in tool_errors:
                print(f"- {error}")
            print()

        # Review checklists from skills
        if skill_content:
            print("## Review Checklists\n")
            for skill_name, content in skill_content.items():
                print(f"### {skill_name}\n")
                # Print the skill content (already markdown)
                print(content)
                print()

        # Knowledge reference
        if knowledge_content:
            print("## Principles Reference\n")
            for filename, content in sorted(knowledge_content.items()):
                print(f"### {filename}\n")
                print(content)
                print()

        # Result
        print("## Result\n")
        if effective_threshold:
            status = "PASSED" if passed else "FAILED"
            status_emoji = "PASS" if passed else "FAIL"
            print(f"**Status:** {status_emoji} ({threshold_used} threshold)")
        else:
            print("**Status:** Complete (no threshold set)")
        print()
        print("---")
        print("*Generated by Crucible*")
    else:
        # Text output
        print(f"\n{'='*60}")
        print(f"Review: {mode} changes")
        print(f"{'='*60}")

        print(f"\nFiles changed: {len(changed_files)}")
        for c in context.changes:
            status_char = {"A": "+", "M": "~", "D": "-", "R": "R"}.get(c.status, "?")
            print(f"  [{status_char}] {c.path}")

        if tool_errors:
            print(f"\nTool Errors ({len(tool_errors)}):")
            for error in tool_errors:
                print(f"  - {error}")

        if filtered_findings:
            print(f"\nFindings ({len(filtered_findings)}):")
            print(f"  Summary: {severity_counts}")
            print()
            for f in filtered_findings:
                sev_upper = f.severity.value.upper()
                print(f"  [{sev_upper}] {f.location}")
                print(f"    {f.tool}/{f.rule}: {f.message}")
                if f.suggestion:
                    print(f"    Suggestion: {f.suggestion}")
                print()
        else:
            print("\nNo issues found in changed code.")

        # Enforcement assertions
        if enforcement_findings:
            active_enforcement = [f for f in enforcement_findings if not f.suppressed]
            suppressed_enforcement = [f for f in enforcement_findings if f.suppressed]

            if active_enforcement:
                print(f"\nEnforcement Assertions ({len(active_enforcement)}):")
                for f in active_enforcement:
                    sev_upper = f.severity.upper()
                    source_label = "[LLM]" if f.source == "llm" else "[PATTERN]"
                    print(f"  [{sev_upper}] {source_label} {f.assertion_id}: {f.location}")
                    print(f"    {f.message}")
                    print()

            if suppressed_enforcement:
                print(f"  Suppressed: {len(suppressed_enforcement)}")

        if assertions_checked > 0:
            print(f"\nAssertions: {assertions_checked} checked, {assertions_skipped} skipped")
            if budget_state and budget_state.tokens_used > 0:
                print(f"  LLM tokens used: {budget_state.tokens_used}")

        if effective_threshold:
            status = "PASSED" if passed else "FAILED"
            print(f"\n{'='*60}")
            print(f"Result: {status} (threshold: {threshold_used})")
            print(f"{'='*60}")

    return 0 if passed else 1


# --- Assertions commands ---

# Assertions directories
ASSERTIONS_BUNDLED = Path(__file__).parent / "enforcement" / "bundled"
ASSERTIONS_USER = Path.home() / ".claude" / "crucible" / "assertions"
ASSERTIONS_PROJECT = Path(".crucible") / "assertions"


def cmd_assertions_validate(args: argparse.Namespace) -> int:
    """Validate assertion files."""
    from crucible.enforcement.assertions import (
        clear_assertion_cache,
        get_all_assertion_files,
        load_assertion_file,
    )

    clear_assertion_cache()

    files = get_all_assertion_files()
    if not files:
        print("No assertion files found.")
        print("\nCreate assertion files in:")
        print(f"  Project: {ASSERTIONS_PROJECT}/")
        print(f"  User:    {ASSERTIONS_USER}/")
        return 0

    valid_count = 0
    error_count = 0

    for filename in sorted(files):
        result = load_assertion_file(filename)
        if result.is_ok:
            assertion_count = len(result.value.assertions)
            print(f"  ✓ {filename}: {assertion_count} assertion(s) valid")
            valid_count += 1
        else:
            print(f"  ✗ {filename}: {result.error}")
            error_count += 1

    print()
    if error_count == 0:
        print(f"All {valid_count} file(s) valid.")
        return 0
    else:
        print(f"{error_count} file(s) with errors, {valid_count} valid.")
        return 1


def cmd_assertions_list(args: argparse.Namespace) -> int:
    """List available assertion files."""
    print("Bundled assertions:")
    if ASSERTIONS_BUNDLED.exists():
        found = False
        for file_path in sorted(ASSERTIONS_BUNDLED.iterdir()):
            if file_path.is_file() and file_path.suffix in (".yaml", ".yml"):
                print(f"  - {file_path.name}")
                found = True
        if not found:
            print("  (none)")
    else:
        print("  (none)")

    print("\nUser assertions (~/.claude/crucible/assertions/):")
    if ASSERTIONS_USER.exists():
        found = False
        for file_path in sorted(ASSERTIONS_USER.iterdir()):
            if file_path.is_file() and file_path.suffix in (".yaml", ".yml"):
                print(f"  - {file_path.name}")
                found = True
        if not found:
            print("  (none)")
    else:
        print("  (none)")

    print("\nProject assertions (.crucible/assertions/):")
    if ASSERTIONS_PROJECT.exists():
        found = False
        for file_path in sorted(ASSERTIONS_PROJECT.iterdir()):
            if file_path.is_file() and file_path.suffix in (".yaml", ".yml"):
                print(f"  - {file_path.name}")
                found = True
        if not found:
            print("  (none)")
    else:
        print("  (none)")

    return 0


def cmd_assertions_test(args: argparse.Namespace) -> int:
    """Test assertions against a file or directory."""
    import os

    from crucible.enforcement.assertions import load_assertions
    from crucible.enforcement.patterns import run_pattern_assertions

    target_path = Path(args.file)
    if not target_path.exists():
        print(f"Error: Path '{target_path}' not found")
        return 1

    assertions, errors = load_assertions()

    if errors:
        print("Assertion loading errors:")
        for error in errors:
            print(f"  - {error}")
        print()

    if not assertions:
        print("No assertions loaded.")
        return 0

    # Collect files to test
    files_to_test: list[tuple[str, str]] = []  # (display_path, content)

    if target_path.is_file():
        try:
            content = target_path.read_text()
            files_to_test.append((str(target_path), content))
        except UnicodeDecodeError:
            print(f"Error: Cannot read '{target_path}' (binary file?)")
            return 1
    else:
        # Directory mode
        for root, _, files in os.walk(target_path):
            for fname in files:
                fpath = Path(root) / fname
                rel_path = fpath.relative_to(target_path)
                try:
                    content = fpath.read_text()
                    files_to_test.append((str(rel_path), content))
                except (UnicodeDecodeError, OSError):
                    pass  # Skip binary/unreadable files

    # Run assertions on all files
    all_findings = []
    checked = 0
    skipped = 0

    for display_path, content in files_to_test:
        findings, c, s = run_pattern_assertions(display_path, content, assertions)
        all_findings.extend(findings)
        checked = max(checked, c)
        skipped = max(skipped, s)

    # Separate suppressed and active findings
    active = [f for f in all_findings if not f.suppressed]
    suppressed = [f for f in all_findings if f.suppressed]

    print(f"Testing {target_path}")
    print(f"  Files scanned: {len(files_to_test)}")
    print(f"  Assertions checked: {checked}")
    print(f"  Assertions skipped (LLM): {skipped}")
    print()

    if active:
        print(f"Findings ({len(active)}):")
        for f in active:
            sev = f.severity.upper()
            print(f"  [{sev}] {f.assertion_id}: {f.location}")
            print(f"    {f.message}")
            if f.match_text:
                print(f"    Matched: {f.match_text!r}")
            print()

    if suppressed:
        print(f"Suppressed ({len(suppressed)}):")
        for f in suppressed:
            reason = f" -- {f.suppression_reason}" if f.suppression_reason else ""
            print(f"  {f.assertion_id}: {f.location}{reason}")

    if not active and not suppressed:
        print("No matches found.")

    return 0


def cmd_assertions_explain(args: argparse.Namespace) -> int:
    """Explain what a rule does."""
    from crucible.enforcement.assertions import load_assertions

    rule_id = args.rule.lower()
    assertions, errors = load_assertions()

    for assertion in assertions:
        if assertion.id.lower() == rule_id:
            print(f"Rule: {assertion.id}")
            print(f"Type: {assertion.type.value}")
            if assertion.pattern:
                print(f"Pattern: {assertion.pattern}")
            print(f"Message: {assertion.message}")
            print(f"Severity: {assertion.severity}")
            print(f"Priority: {assertion.priority.value}")
            if assertion.languages:
                print(f"Languages: {', '.join(assertion.languages)}")
            if assertion.applicability:
                if assertion.applicability.glob:
                    print(f"Applies to: {assertion.applicability.glob}")
                if assertion.applicability.exclude:
                    print(f"Excludes: {', '.join(assertion.applicability.exclude)}")
            if assertion.compliance:
                print(f"Compliance: {assertion.compliance}")
            return 0

    print(f"Rule '{rule_id}' not found.")
    print("\nAvailable rules:")
    for a in assertions[:10]:
        print(f"  - {a.id}")
    if len(assertions) > 10:
        print(f"  ... and {len(assertions) - 10} more")
    return 1


def cmd_assertions_debug(args: argparse.Namespace) -> int:
    """Debug applicability for a rule and file."""
    from crucible.enforcement.assertions import load_assertions
    from crucible.enforcement.patterns import matches_glob, matches_language

    rule_id = args.rule.lower()
    file_path = args.file

    assertions, errors = load_assertions()

    for assertion in assertions:
        if assertion.id.lower() == rule_id:
            print(f"Applicability check for '{assertion.id}':")
            print()

            # Language check
            if assertion.languages:
                lang_match = matches_language(file_path, assertion.languages)
                lang_status = "MATCH" if lang_match else "NO MATCH"
                print(f"  Languages: {', '.join(assertion.languages)}")
                print(f"    File: {file_path} → {lang_status}")
            else:
                print("  Languages: (any)")

            # Glob check
            if assertion.applicability:
                if assertion.applicability.glob:
                    glob_match = matches_glob(
                        file_path,
                        assertion.applicability.glob,
                        assertion.applicability.exclude,
                    )
                    glob_status = "MATCH" if glob_match else "NO MATCH"
                    print(f"  Glob: {assertion.applicability.glob}")
                    if assertion.applicability.exclude:
                        print(f"  Exclude: {', '.join(assertion.applicability.exclude)}")
                    print(f"    File: {file_path} → {glob_status}")
                else:
                    print("  Glob: (any)")
            else:
                print("  Applicability: (none)")

            # Overall result
            print()
            lang_ok = matches_language(file_path, assertion.languages)
            glob_ok = True
            if assertion.applicability and assertion.applicability.glob:
                glob_ok = matches_glob(
                    file_path,
                    assertion.applicability.glob,
                    assertion.applicability.exclude,
                )
            overall = lang_ok and glob_ok
            result = "APPLICABLE" if overall else "NOT APPLICABLE"
            print(f"  Result: {result}")
            return 0

    print(f"Rule '{rule_id}' not found.")
    return 1


# --- Hooks commands ---

PRECOMMIT_HOOK_SCRIPT = """\
#!/bin/sh
# Crucible pre-commit hook
# Checks for secrets/sensitive files and runs static analysis

crucible pre-commit "$@"
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo ""
    echo "Pre-commit check failed. Fix issues or use --no-verify to skip."
fi

exit $exit_code
"""


def cmd_hooks_install(args: argparse.Namespace) -> int:
    """Install git hooks to .git/hooks/."""
    from crucible.tools.git import get_repo_root, is_git_repo

    path = args.path or "."
    if not is_git_repo(path):
        print(f"Error: {path} is not inside a git repository")
        return 1

    root_result = get_repo_root(path)
    if root_result.is_err:
        print(f"Error: {root_result.error}")
        return 1

    repo_root = Path(root_result.value)
    hooks_dir = repo_root / ".git" / "hooks"

    if not hooks_dir.exists():
        print(f"Error: hooks directory not found at {hooks_dir}")
        return 1

    hook_path = hooks_dir / "pre-commit"

    if hook_path.exists():
        content = hook_path.read_text()
        is_crucible = "crucible" in content.lower()

        if is_crucible and not args.force:
            print("Crucible pre-commit hook is already installed")
            return 0
        elif not is_crucible and not args.force:
            print(f"Error: {hook_path} already exists")
            print("  Use --force to replace it")
            return 1

    hook_path.write_text(PRECOMMIT_HOOK_SCRIPT)
    hook_path.chmod(0o755)

    print(f"Installed pre-commit hook to {hook_path}")
    print("\nThe hook checks for:")
    print("  - Sensitive files (env, keys, credentials)")
    print("  - Static analysis issues (semgrep, ruff, bandit, slither)")
    print("\nUse 'git commit --no-verify' to skip if needed.")
    return 0


def cmd_hooks_uninstall(args: argparse.Namespace) -> int:
    """Uninstall crucible git hooks."""
    from crucible.tools.git import get_repo_root, is_git_repo

    path = args.path or "."
    if not is_git_repo(path):
        print(f"Error: {path} is not inside a git repository")
        return 1

    root_result = get_repo_root(path)
    if root_result.is_err:
        print(f"Error: {root_result.error}")
        return 1

    repo_root = Path(root_result.value)
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"

    if not hook_path.exists():
        print("No pre-commit hook installed")
        return 0

    # Check if it's our hook
    content = hook_path.read_text()
    if "crucible" not in content.lower():
        print("Error: pre-commit hook exists but wasn't installed by crucible")
        print("  Remove manually if you want to replace it")
        return 1

    hook_path.unlink()
    print(f"Removed pre-commit hook from {hook_path}")
    return 0


def cmd_hooks_status(args: argparse.Namespace) -> int:
    """Show status of installed hooks."""
    from crucible.tools.git import get_repo_root, is_git_repo

    path = args.path or "."
    if not is_git_repo(path):
        print(f"Error: {path} is not inside a git repository")
        return 1

    root_result = get_repo_root(path)
    if root_result.is_err:
        print(f"Error: {root_result.error}")
        return 1

    repo_root = Path(root_result.value)
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"

    print(f"Repository: {repo_root}")
    print()

    if hook_path.exists():
        content = hook_path.read_text()
        if "crucible" in content.lower():
            print("pre-commit: INSTALLED (crucible)")
        else:
            print("pre-commit: EXISTS (not crucible)")
    else:
        print("pre-commit: NOT INSTALLED")

    # Check for config file
    config_project = repo_root / ".crucible" / "precommit.yaml"
    config_user = Path.home() / ".claude" / "crucible" / "precommit.yaml"

    print()
    if config_project.exists():
        print(f"Config: {config_project} (project)")
    elif config_user.exists():
        print(f"Config: {config_user} (user)")
    else:
        print("Config: using defaults")

    return 0


def cmd_precommit(args: argparse.Namespace) -> int:
    """Run pre-commit checks (can be called directly or from hook)."""
    from crucible.hooks.precommit import (
        EXIT_ERROR,
        EXIT_FAIL,
        EXIT_PASS,
        PrecommitConfig,
        _parse_severity,
        format_precommit_output,
        load_precommit_config,
        run_precommit,
    )

    path = args.path or "."
    config = load_precommit_config(path)

    # Apply CLI overrides
    if args.fail_on or args.verbose:
        config = PrecommitConfig(
            fail_on=_parse_severity(args.fail_on) if args.fail_on else config.fail_on,
            timeout=config.timeout,
            exclude=config.exclude,
            include_context=config.include_context,
            tools=config.tools,
            skip_tools=config.skip_tools,
            verbose=args.verbose or config.verbose,
            secrets_tool=config.secrets_tool,
        )

    result = run_precommit(path, config)

    if args.json:
        import json
        output = {
            "passed": result.passed,
            "findings": [
                {
                    "tool": f.tool,
                    "rule": f.rule,
                    "severity": f.severity.value,
                    "message": f.message,
                    "location": f.location,
                    "suggestion": f.suggestion,
                }
                for f in result.findings
            ],
            "severity_counts": result.severity_counts,
            "files_checked": result.files_checked,
            "error": result.error,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_precommit_output(result, args.verbose or config.verbose))

    if result.error:
        return EXIT_ERROR
    return EXIT_PASS if result.passed else EXIT_FAIL


# --- Init command ---


def _detect_project_stack(path: Path) -> list[str]:
    """Detect the project's tech stack based on files present."""
    stack: list[str] = []

    indicators = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "typescript": ["tsconfig.json", "package.json"],
        "javascript": ["package.json"],
        "solidity": ["foundry.toml", "hardhat.config.js", "hardhat.config.ts", "truffle-config.js"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
    }

    for tech, files in indicators.items():
        for file in files:
            if (path / file).exists():
                if tech not in stack:
                    stack.append(tech)
                break

    # Check for .sol files directly
    if not any(t in stack for t in ["solidity"]):
        sol_files = list(path.glob("**/*.sol"))
        if sol_files and len(sol_files) < 1000:  # Sanity limit
            stack.append("solidity")

    return stack


def _get_recommended_skills(stack: list[str]) -> list[str]:
    """Get recommended skills based on detected stack."""
    skills: list[str] = ["security-engineer"]  # Always recommend

    stack_skills = {
        "python": ["backend-engineer"],
        "typescript": ["backend-engineer", "uiux-engineer"],
        "javascript": ["backend-engineer", "uiux-engineer"],
        "solidity": ["web3-engineer", "gas-optimizer", "protocol-architect"],
        "rust": ["backend-engineer", "performance-engineer"],
        "go": ["backend-engineer", "performance-engineer"],
    }

    for tech in stack:
        if tech in stack_skills:
            for skill in stack_skills[tech]:
                if skill not in skills:
                    skills.append(skill)

    return skills


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize .crucible/ directory for project customization."""
    project_path = Path(args.path).resolve()
    crucible_dir = project_path / ".crucible"

    if crucible_dir.exists() and not args.force:
        print(f"Error: {crucible_dir} already exists. Use --force to overwrite.")
        return 1

    # Detect stack
    stack = _detect_project_stack(project_path)
    if stack:
        print(f"Detected stack: {', '.join(stack)}")
    else:
        print("No specific stack detected")

    # Create directory structure
    (crucible_dir / "skills").mkdir(parents=True, exist_ok=True)
    (crucible_dir / "knowledge").mkdir(parents=True, exist_ok=True)

    # Create default review.yaml
    review_config = """# Crucible review configuration
# See: https://github.com/be-nvy/crucible

# Fail on findings at or above this severity
fail_on: high

# Per-domain overrides (uncomment to customize)
# fail_on_domain:
#   smart_contract: critical
#   backend: high

# Skip specific tools (uncomment to customize)
# skip_tools:
#   - slither

# Include findings near (within 5 lines of) changes
include_context: false
"""
    (crucible_dir / "review.yaml").write_text(review_config)
    print(f"Created {crucible_dir / 'review.yaml'}")

    if not args.minimal:
        # Get recommended skills
        recommended = _get_recommended_skills(stack)
        print(f"\nRecommended skills for your stack: {', '.join(recommended)}")
        print("\nTo customize a skill, run:")
        for skill in recommended:
            print(f"  crucible skills init {skill}")

    # Create .gitignore if not exists
    gitignore_path = crucible_dir / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text("# Local overrides (optional)\n*.local.md\n")

    # Create minimal CLAUDE.md if requested
    if args.with_claudemd:
        claudemd_path = project_path / "CLAUDE.md"
        if claudemd_path.exists() and not args.force:
            print(f"Warning: {claudemd_path} exists, skipping (use --force to overwrite)")
        else:
            project_name = project_path.name
            claudemd_content = f"""# {project_name}

Use Crucible for code review: `crucible review`

For full engineering principles and patterns, run:
- `crucible knowledge list` - see available knowledge
- `crucible skills list` - see available review personas
"""
            claudemd_path.write_text(claudemd_content)
            print(f"Created {claudemd_path}")

    print(f"\nInitialized {crucible_dir}")
    print("\nNext steps:")
    print("  1. Customize skills:     crucible skills init <skill>")
    print("  2. Customize knowledge:  crucible knowledge init <file>")
    print("  3. Install git hooks:    crucible hooks install")
    print("  4. Claude Code hooks:    crucible hooks claudecode init")
    return 0


# --- CI command ---


GITHUB_WORKFLOW_TEMPLATE = '''name: Crucible Code Review

on:
  pull_request:
    branches: [main, master]
  push:
    branches: [main, master]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for branch comparison

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install crucible
        run: pip install crucible-mcp

      - name: Review changes
        run: |
          if [ "${{{{ github.event_name }}}}" = "pull_request" ]; then
            crucible review --mode branch --base ${{{{ github.base_ref }}}} --fail-on {fail_on}
          else
            crucible review --mode commits --base 1 --fail-on {fail_on}
          fi
'''


def cmd_ci_generate(args: argparse.Namespace) -> int:
    """Generate GitHub Actions workflow for crucible."""
    workflow = GITHUB_WORKFLOW_TEMPLATE.format(fail_on=args.fail_on)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(workflow)
        print(f"Generated {output_path}")
    else:
        print(workflow)

    return 0


# --- Config commands ---

CONFIG_DIR = Path.home() / ".config" / "crucible"
SECRETS_FILE = CONFIG_DIR / "secrets.yaml"


def cmd_config_set_api_key(args: argparse.Namespace) -> int:
    """Set Anthropic API key for LLM compliance assertions."""
    import getpass

    import yaml

    print("Set Anthropic API key for LLM compliance assertions.")
    print("This will be stored in ~/.config/crucible/secrets.yaml")
    print()

    # Prompt for key (hidden input)
    api_key = getpass.getpass("Enter API key (input hidden): ")

    if not api_key:
        print("No key provided, aborting.")
        return 1

    if not api_key.startswith("sk-ant-"):
        print("Warning: Key doesn't start with 'sk-ant-', are you sure this is correct?")
        confirm = input("Continue? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted.")
            return 1

    # Create config directory
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    existing_config: dict = {}
    if SECRETS_FILE.exists():
        try:
            with open(SECRETS_FILE) as f:
                existing_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not read existing {SECRETS_FILE}: {e}", file=sys.stderr)

    # Update config
    existing_config["anthropic_api_key"] = api_key

    # Write with restrictive permissions
    SECRETS_FILE.write_text(yaml.dump(existing_config, default_flow_style=False))
    SECRETS_FILE.chmod(0o600)

    print(f"API key saved to {SECRETS_FILE}")
    print("Permissions set to 600 (owner read/write only)")
    return 0


def cmd_config_show(args: argparse.Namespace) -> int:
    """Show current configuration."""
    import os

    import yaml

    print("Crucible Configuration")
    print("=" * 40)

    # Check env var
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        print(f"ANTHROPIC_API_KEY (env): {env_key[:10]}...{env_key[-4:]}")
    else:
        print("ANTHROPIC_API_KEY (env): not set")

    # Check config file
    if SECRETS_FILE.exists():
        try:
            with open(SECRETS_FILE) as f:
                data = yaml.safe_load(f) or {}
            file_key = data.get("anthropic_api_key")
            if file_key:
                print(f"anthropic_api_key (file): {file_key[:10]}...{file_key[-4:]}")
            else:
                print("anthropic_api_key (file): not set")
            print(f"Config file: {SECRETS_FILE}")
        except Exception as e:
            print(f"Config file error: {e}")
    else:
        print(f"Config file: {SECRETS_FILE} (not found)")

    # Show which would be used
    print()
    if env_key:
        print("Active: environment variable (takes precedence)")
    elif SECRETS_FILE.exists():
        print("Active: config file")
    else:
        print("Active: none (LLM assertions will fail)")

    return 0


# --- Main ---


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="crucible",
        description="Code review orchestration",
    )
    subparsers = parser.add_subparsers(dest="command")

    # === skills command ===
    skills_parser = subparsers.add_parser("skills", help="Manage review skills")
    skills_sub = skills_parser.add_subparsers(dest="skills_command")

    # skills install
    install_parser = skills_sub.add_parser(
        "install",
        help="Install skills to ~/.claude/crucible/skills/"
    )
    install_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing skills"
    )

    # skills list
    skills_sub.add_parser("list", help="List skills from all sources")

    # skills init
    init_parser = skills_sub.add_parser(
        "init",
        help="Copy a skill to .crucible/skills/ for project customization"
    )
    init_parser.add_argument("skill", help="Name of the skill to initialize")
    init_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing project skill"
    )

    # skills show
    show_parser = skills_sub.add_parser(
        "show",
        help="Show skill resolution (which file is active)"
    )
    show_parser.add_argument("skill", help="Name of the skill to show")

    # === knowledge command ===
    knowledge_parser = subparsers.add_parser("knowledge", help="Manage engineering knowledge")
    knowledge_sub = knowledge_parser.add_subparsers(dest="knowledge_command")

    # knowledge install
    knowledge_install_parser = knowledge_sub.add_parser(
        "install",
        help="Install knowledge to ~/.claude/crucible/knowledge/"
    )
    knowledge_install_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing files"
    )

    # knowledge list
    knowledge_sub.add_parser("list", help="List knowledge from all sources")

    # knowledge init
    knowledge_init_parser = knowledge_sub.add_parser(
        "init",
        help="Copy knowledge to .crucible/knowledge/ for project customization"
    )
    knowledge_init_parser.add_argument("file", help="Name of the file to initialize")
    knowledge_init_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing project file"
    )

    # knowledge show
    knowledge_show_parser = knowledge_sub.add_parser(
        "show",
        help="Show knowledge resolution (which file is active)"
    )
    knowledge_show_parser.add_argument("file", help="Name of the file to show")

    # === hooks command ===
    hooks_parser = subparsers.add_parser("hooks", help="Manage git hooks")
    hooks_sub = hooks_parser.add_subparsers(dest="hooks_command")

    # hooks install
    hooks_install_parser = hooks_sub.add_parser(
        "install",
        help="Install crucible pre-commit hook"
    )
    hooks_install_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing hook"
    )
    hooks_install_parser.add_argument(
        "path", nargs="?", default=".", help="Repository path"
    )

    # hooks uninstall
    hooks_uninstall_parser = hooks_sub.add_parser(
        "uninstall",
        help="Remove crucible pre-commit hook"
    )
    hooks_uninstall_parser.add_argument(
        "path", nargs="?", default=".", help="Repository path"
    )

    # hooks status
    hooks_status_parser = hooks_sub.add_parser(
        "status",
        help="Show hook installation status"
    )
    hooks_status_parser.add_argument(
        "path", nargs="?", default=".", help="Repository path"
    )

    # hooks claudecode
    hooks_claudecode_parser = hooks_sub.add_parser(
        "claudecode",
        help="Claude Code hooks integration"
    )
    hooks_claudecode_sub = hooks_claudecode_parser.add_subparsers(dest="claudecode_command")

    # hooks claudecode init
    hooks_cc_init_parser = hooks_claudecode_sub.add_parser(
        "init",
        help="Initialize Claude Code hooks for project"
    )
    hooks_cc_init_parser.add_argument(
        "path", nargs="?", default=".", help="Project path"
    )

    # hooks claudecode hook (called by Claude Code)
    hooks_claudecode_sub.add_parser(
        "hook",
        help="Run hook (reads JSON from stdin)"
    )

    # === review command ===
    review_parser = subparsers.add_parser(
        "review",
        help="Review git changes (staged, unstaged, branch, commits)"
    )
    review_parser.add_argument(
        "--mode", "-m",
        choices=["staged", "unstaged", "branch", "commits"],
        default="staged",
        help="What changes to review (default: staged)"
    )
    review_parser.add_argument(
        "--base", "-b",
        help="Base branch for 'branch' mode or commit count for 'commits' mode"
    )
    review_parser.add_argument(
        "--fail-on",
        choices=["critical", "high", "medium", "low", "info"],
        help="Fail on findings at or above this severity"
    )
    review_parser.add_argument(
        "--include-context", "-c", action="store_true",
        help="Include findings near changed lines (within 5 lines)"
    )
    review_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )
    review_parser.add_argument(
        "--format", "-f",
        choices=["text", "report"],
        default="text",
        help="Output format: text (default) or report (markdown audit report)"
    )
    review_parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress progress messages"
    )
    review_parser.add_argument(
        "--token-budget", type=int,
        help="Token budget for LLM compliance assertions (0 = unlimited)"
    )
    review_parser.add_argument(
        "--compliance-model",
        choices=["sonnet", "opus", "haiku"],
        help="Model for LLM compliance assertions (default: sonnet)"
    )
    review_parser.add_argument(
        "--no-compliance", action="store_true",
        help="Disable LLM compliance assertions"
    )
    review_parser.add_argument(
        "--no-git", action="store_true",
        help="Review path directly without git awareness (static analysis only)"
    )
    review_parser.add_argument(
        "path", nargs="?", default=".", help="Path to review (file or directory)"
    )

    # === pre-commit command (direct invocation) ===
    precommit_parser = subparsers.add_parser(
        "pre-commit",
        help="Run pre-commit checks on staged changes"
    )
    precommit_parser.add_argument(
        "--fail-on",
        choices=["critical", "high", "medium", "low", "info"],
        help="Fail on findings at or above this severity"
    )
    precommit_parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show all findings, not just high+"
    )
    precommit_parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )
    precommit_parser.add_argument(
        "path", nargs="?", default=".", help="Repository path"
    )

    # === init command ===
    init_proj_parser = subparsers.add_parser(
        "init",
        help="Initialize .crucible/ directory for project customization"
    )
    init_proj_parser.add_argument(
        "--force", "-f", action="store_true",
        help="Overwrite existing .crucible/ directory"
    )
    init_proj_parser.add_argument(
        "--minimal", action="store_true",
        help="Create minimal config without copying skills"
    )
    init_proj_parser.add_argument(
        "--with-claudemd", action="store_true",
        help="Generate minimal CLAUDE.md that points to Crucible"
    )
    init_proj_parser.add_argument(
        "path", nargs="?", default=".",
        help="Project path (default: current directory)"
    )

    # === assertions command ===
    assertions_parser = subparsers.add_parser("assertions", help="Manage pattern assertions")
    assertions_sub = assertions_parser.add_subparsers(dest="assertions_command")

    # assertions validate
    assertions_sub.add_parser("validate", help="Validate assertion files")

    # assertions list
    assertions_sub.add_parser("list", help="List assertion files from all sources")

    # assertions test
    assertions_test_parser = assertions_sub.add_parser(
        "test",
        help="Test assertions against a file"
    )
    assertions_test_parser.add_argument("file", help="File to test")

    # assertions explain
    assertions_explain_parser = assertions_sub.add_parser(
        "explain",
        help="Explain what a rule does"
    )
    assertions_explain_parser.add_argument("rule", help="Rule ID to explain")

    # assertions debug
    assertions_debug_parser = assertions_sub.add_parser(
        "debug",
        help="Debug applicability for a rule and file"
    )
    assertions_debug_parser.add_argument("--rule", "-r", required=True, help="Rule ID")
    assertions_debug_parser.add_argument("--file", "-f", required=True, help="File to check")

    # === ci command ===
    ci_parser = subparsers.add_parser(
        "ci",
        help="Generate CI configuration"
    )
    ci_sub = ci_parser.add_subparsers(dest="ci_command")

    # ci generate
    ci_generate_parser = ci_sub.add_parser(
        "generate",
        help="Generate GitHub Actions workflow"
    )
    ci_generate_parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    ci_generate_parser.add_argument(
        "--fail-on",
        choices=["critical", "high", "medium", "low"],
        default="high",
        help="Fail threshold for CI (default: high)"
    )

    # === config command ===
    config_parser = subparsers.add_parser("config", help="Manage crucible configuration")
    config_sub = config_parser.add_subparsers(dest="config_command")

    # config set-api-key
    config_sub.add_parser(
        "set-api-key",
        help="Set Anthropic API key for LLM compliance assertions"
    )

    # config show
    config_sub.add_parser(
        "show",
        help="Show current configuration"
    )

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "ci":
        if args.ci_command == "generate":
            return cmd_ci_generate(args)
        else:
            ci_parser.print_help()
            return 0
    elif args.command == "skills":
        if args.skills_command == "install":
            return cmd_skills_install(args)
        elif args.skills_command == "list":
            return cmd_skills_list(args)
        elif args.skills_command == "init":
            return cmd_skills_init(args)
        elif args.skills_command == "show":
            return cmd_skills_show(args)
        else:
            skills_parser.print_help()
            return 0
    elif args.command == "knowledge":
        if args.knowledge_command == "install":
            return cmd_knowledge_install(args)
        elif args.knowledge_command == "list":
            return cmd_knowledge_list(args)
        elif args.knowledge_command == "init":
            return cmd_knowledge_init(args)
        elif args.knowledge_command == "show":
            return cmd_knowledge_show(args)
        else:
            knowledge_parser.print_help()
            return 0
    elif args.command == "hooks":
        if args.hooks_command == "install":
            return cmd_hooks_install(args)
        elif args.hooks_command == "uninstall":
            return cmd_hooks_uninstall(args)
        elif args.hooks_command == "status":
            return cmd_hooks_status(args)
        elif args.hooks_command == "claudecode":
            from crucible.hooks.claudecode import main_init, run_hook
            if args.claudecode_command == "init":
                return main_init(args.path)
            elif args.claudecode_command == "hook":
                return run_hook()
            else:
                hooks_claudecode_parser.print_help()
                return 0
        else:
            hooks_parser.print_help()
            return 0
    elif args.command == "assertions":
        if args.assertions_command == "validate":
            return cmd_assertions_validate(args)
        elif args.assertions_command == "list":
            return cmd_assertions_list(args)
        elif args.assertions_command == "test":
            return cmd_assertions_test(args)
        elif args.assertions_command == "explain":
            return cmd_assertions_explain(args)
        elif args.assertions_command == "debug":
            return cmd_assertions_debug(args)
        else:
            assertions_parser.print_help()
            return 0
    elif args.command == "review":
        return cmd_review(args)
    elif args.command == "pre-commit":
        return cmd_precommit(args)
    elif args.command == "config":
        if args.config_command == "set-api-key":
            return cmd_config_set_api_key(args)
        elif args.config_command == "show":
            return cmd_config_show(args)
        else:
            config_parser.print_help()
            return 0
    else:
        # Default help
        print("crucible - Code review orchestration\n")
        print("Getting Started:")
        print("  crucible init                   Initialize .crucible/ for project customization")
        print("  crucible ci generate            Generate GitHub Actions workflow")
        print()
        print("Commands:")
        print("  crucible skills list            List skills from all sources")
        print("  crucible skills install         Install skills to ~/.claude/crucible/")
        print("  crucible skills init <skill>    Copy skill for project customization")
        print("  crucible skills show <skill>    Show skill resolution")
        print()
        print("  crucible knowledge list         List knowledge from all sources")
        print("  crucible knowledge install      Install knowledge to ~/.claude/crucible/")
        print("  crucible knowledge init <file>  Copy knowledge for project customization")
        print("  crucible knowledge show <file>  Show knowledge resolution")
        print()
        print("  crucible hooks install          Install pre-commit hook to .git/hooks/")
        print("  crucible hooks uninstall        Remove pre-commit hook")
        print("  crucible hooks status           Show hook installation status")
        print("  crucible hooks claudecode init  Initialize Claude Code hooks")
        print()
        print("  crucible assertions list        List assertion files from all sources")
        print("  crucible assertions validate    Validate assertion files")
        print("  crucible assertions test <file> Test assertions against a file")
        print("  crucible assertions explain <r> Explain what a rule does")
        print("  crucible assertions debug       Debug applicability for a rule")
        print()
        print("  crucible review                 Review git changes or files")
        print("    --mode <mode>                 staged/unstaged/branch/commits (default: staged)")
        print("    --base <ref>                  Base branch or commit count")
        print("    --no-git                      Review path without git (static analysis only)")
        print("    --fail-on <severity>          Fail threshold (critical/high/medium/low/info)")
        print("    --format <format>             Output format: text (default) or report (markdown)")
        print()
        print("  crucible pre-commit             Run pre-commit checks on staged changes")
        print()
        print("  crucible-mcp                    Run as MCP server")
        return 0


if __name__ == "__main__":
    sys.exit(main())
