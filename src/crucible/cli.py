"""crucible CLI."""

import argparse
import shutil
import sys
from pathlib import Path

# Skills directory within the package
SKILLS_SOURCE = Path(__file__).parent / "skills"
SKILLS_DEST = Path.home() / ".claude" / "skills" / "crucible"


def cmd_skills_install(args: argparse.Namespace) -> int:
    """Install crucible skills to ~/.claude/skills/crucible/."""
    if not SKILLS_SOURCE.exists():
        print(f"Error: Skills source not found at {SKILLS_SOURCE}")
        return 1

    # Create destination directory
    SKILLS_DEST.mkdir(parents=True, exist_ok=True)

    installed = []
    for skill_dir in SKILLS_SOURCE.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            dest = SKILLS_DEST / skill_dir.name
            if dest.exists() and not args.force:
                print(f"  Skip: {skill_dir.name} (exists, use --force to overwrite)")
                continue

            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill_dir, dest)
            installed.append(skill_dir.name)
            print(f"  Installed: {skill_dir.name}")

    if installed:
        print(f"\n✓ Installed {len(installed)} skill(s) to {SKILLS_DEST}")
    else:
        print("\nNo skills to install.")

    return 0


def cmd_skills_list(args: argparse.Namespace) -> int:
    """List available and installed skills."""
    print("Available skills (bundled):")
    if SKILLS_SOURCE.exists():
        for skill_dir in sorted(SKILLS_SOURCE.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                print(f"  - {skill_dir.name}")
    else:
        print("  (none)")

    print("\nInstalled skills:")
    if SKILLS_DEST.exists():
        found = False
        for skill_dir in sorted(SKILLS_DEST.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                print(f"  - {skill_dir.name}")
                found = True
        if not found:
            print("  (none)")
    else:
        print("  (none)")

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
    install_parser = skills_sub.add_parser("install", help="Install skills to ~/.claude/skills/")
    install_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing skills"
    )

    # skills list
    skills_sub.add_parser("list", help="List available and installed skills")

    args = parser.parse_args()

    if args.command == "skills":
        if args.skills_command == "install":
            return cmd_skills_install(args)
        elif args.skills_command == "list":
            return cmd_skills_list(args)
        else:
            skills_parser.print_help()
            return 0
    else:
        # Default help
        print("crucible - Code review orchestration\n")
        print("Commands:")
        print("  crucible skills install    Install review skills")
        print("  crucible skills list       List available skills")
        print("  crucible-mcp               Run as MCP server\n")
        print("MCP Tools:")
        print("  quick_review    Run static analysis, returns findings + domains")
        print("  get_principles  Load engineering checklists")
        print("  delegate_*      Direct tool access (semgrep, ruff, slither)")
        print("  check_tools     Show installed analysis tools")
        return 0


if __name__ == "__main__":
    sys.exit(main())
