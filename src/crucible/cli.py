"""crucible CLI."""

import argparse
import shutil
import sys
from pathlib import Path

# Skills directories
SKILLS_BUNDLED = Path(__file__).parent / "skills"
SKILLS_USER = Path.home() / ".claude" / "skills" / "crucible"
SKILLS_PROJECT = Path(".crucible") / "skills"


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


def cmd_skills_install(args: argparse.Namespace) -> int:
    """Install crucible skills to ~/.claude/skills/crucible/."""
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

    print("\nUser skills (~/.claude/skills/crucible/):")
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


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="crucible",
        description="Code review orchestration",
    )
    subparsers = parser.add_subparsers(dest="command")

    # skills command
    skills_parser = subparsers.add_parser("skills", help="Manage review skills")
    skills_sub = skills_parser.add_subparsers(dest="skills_command")

    # skills install
    install_parser = skills_sub.add_parser(
        "install",
        help="Install skills to ~/.claude/skills/crucible/"
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

    args = parser.parse_args()

    if args.command == "skills":
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
    else:
        # Default help
        print("crucible - Code review orchestration\n")
        print("Commands:")
        print("  crucible skills install       Install skills to ~/.claude/skills/")
        print("  crucible skills list          List skills from all sources")
        print("  crucible skills init <skill>  Copy skill to .crucible/skills/ for customization")
        print("  crucible skills show <skill>  Show skill resolution (which file is active)")
        print("  crucible-mcp                  Run as MCP server\n")
        print("MCP Tools:")
        print("  quick_review    Run static analysis, returns findings + domains")
        print("  get_principles  Load engineering checklists")
        print("  delegate_*      Direct tool access (semgrep, ruff, slither, bandit)")
        print("  check_tools     Show installed analysis tools")
        return 0


if __name__ == "__main__":
    sys.exit(main())
