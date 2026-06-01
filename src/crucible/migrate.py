"""crucible migrate v1-to-v2 — move .crucible/ overrides into the v2 layout.

Scope: project-local `.crucible/` files only. Never touches the package's
bundled content, never touches `~/.claude/crucible/` (user-tier overrides
keep their v1 shape across all five resolvers per Phase 0 audit).

Behavior:

- `.crucible/knowledge/<file>.md` → `.crucible/skills/<persona>/knowledge/<v2-name>.md`
  for files whose v1 name matches the bundled-knowledge convention.
  Custom files are listed but NOT moved; user decides where they belong.
- `.crucible/assertions/<file>.yaml` → `.crucible/skills/<persona>/assertions/<file>.yaml`
- `.crucible/templates/prewrite/<name>.md` → `.crucible/skills/pre-write/<name>/SKILL.md`

Idempotency: the migration script can run any number of times. If a
destination file already exists with matching content, it's a no-op.
If the source file is already gone (previous run completed), no-op.
Mismatched destination is reported as a conflict, never overwritten.

Backup: every moved file is copied (not symlinked, not hardlinked) into
`.crucible.v1-backup/` preserving the original relative path. The backup
directory is gitignored.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from crucible.errors import Result, err, ok

# Same mapping used by phase2_migrate.py — keep in sync.
# Maps v1 knowledge filename → (dest persona, v2 filename).
KNOWLEDGE_MAP: dict[str, tuple[str, str]] = {
    "API_DESIGN.md":     ("backend-engineer",     "api-design.md"),
    "COMMITS.md":        ("code-hygiene",         "commits.md"),
    "DATABASE.md":       ("backend-engineer",     "database.md"),
    "DOCUMENTATION.md":  ("tech-lead",            "documentation.md"),
    "ERROR_HANDLING.md": ("backend-engineer",     "error-handling.md"),
    "FP.md":             ("tech-lead",            "functional-programming.md"),
    "GITIGNORE.md":      ("code-hygiene",         "gitignore.md"),
    "OBSERVABILITY.md":  ("devops-engineer",      "observability.md"),
    "PRECOMMIT.md":      ("code-hygiene",         "precommit.md"),
    "SECURITY.md":       ("security-engineer",    "security-principles.md"),
    "SMART_CONTRACT.md": ("web3-engineer",        "smart-contract.md"),
    "SYSTEM_DESIGN.md":  ("tech-lead",            "system-design.md"),
    "TESTING.md":        ("tech-lead",            "testing.md"),
    "TYPE_SAFETY.md":    ("tech-lead",            "type-safety.md"),
}

# Assertion YAML mapping
ASSERTION_MAP: dict[str, tuple[str, str]] = {
    "error-handling.yaml": ("backend-engineer", "error-handling.yaml"),
    "prewrite.yaml":       ("spec-reviewer",    "prewrite.yaml"),
    "security.yaml":       ("security-engineer","security.yaml"),
    "smart-contract.yaml": ("web3-engineer",    "smart-contract.yaml"),
}

BACKUP_DIRNAME = ".crucible.v1-backup"


@dataclass
class MigrationReport:
    """Summary of what a migration run did."""

    moved: list[tuple[Path, Path]] = field(default_factory=list)
    skipped_already_done: list[Path] = field(default_factory=list)
    conflicts: list[tuple[Path, Path, str]] = field(default_factory=list)
    unmapped: list[Path] = field(default_factory=list)
    backed_up: list[Path] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.moved or self.backed_up)


def _backup_file(src: Path, project_root: Path, report: MigrationReport) -> None:
    """Copy src into .crucible.v1-backup/, preserving relative path."""
    rel = src.relative_to(project_root)
    backup = project_root / BACKUP_DIRNAME / rel
    if backup.exists():
        # Already backed up in a prior run — leave it; backups are
        # append-only proof, never overwritten by a subsequent run.
        return
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, backup)
    report.backed_up.append(backup)


def _migrate_one(
    src: Path,
    dest: Path,
    project_root: Path,
    report: MigrationReport,
    *,
    structural: bool = False,
) -> None:
    """Move a single file from src to dest with idempotency handling.

    structural=True means dest is the SKILL.md inside a new folder
    (prewrite case). Same idempotency rules apply.
    """
    if not src.exists():
        # Source already gone — prior run completed; nothing to do.
        return

    if dest.exists():
        # Compare contents to detect a true no-op vs a conflict.
        try:
            same = src.read_bytes() == dest.read_bytes()
        except OSError:
            same = False
        if same:
            report.skipped_already_done.append(src)
            # Source is stale but matches destination — back it up and
            # remove. We treat this as "in-progress" because removing the
            # source completes the previous half-finished migration.
            _backup_file(src, project_root, report)
            src.unlink()
            return
        # Different contents — conflict. Don't touch either file.
        report.conflicts.append(
            (
                src,
                dest,
                "destination exists with different content; resolve manually",
            )
        )
        return

    # Clean move: backup, copy to dest, delete src.
    _backup_file(src, project_root, report)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    src.unlink()
    report.moved.append((src, dest))


def migrate_v1_to_v2(project_root: Path) -> Result[MigrationReport, str]:
    """Migrate a project's `.crucible/` overrides from v1 to v2 shape.

    Idempotent. Returns a MigrationReport describing what happened.
    Conflicts (destination exists with different content) are reported
    but never overwritten.
    """
    project_root = project_root.resolve()
    crucible_dir = project_root / ".crucible"
    if not crucible_dir.exists():
        return ok(MigrationReport())  # nothing to migrate

    report = MigrationReport()

    # --- Knowledge files ---
    knowledge_src = crucible_dir / "knowledge"
    if knowledge_src.exists():
        for src in sorted(knowledge_src.iterdir()):
            if not src.is_file() or src.suffix != ".md":
                continue
            mapping = KNOWLEDGE_MAP.get(src.name)
            if mapping is None:
                report.unmapped.append(src)
                continue
            persona, v2_name = mapping
            dest = crucible_dir / "skills" / persona / "knowledge" / v2_name
            _migrate_one(src, dest, project_root, report)

    # --- Assertion files ---
    assertions_src = crucible_dir / "assertions"
    if assertions_src.exists():
        for src in sorted(assertions_src.iterdir()):
            if not src.is_file() or src.suffix not in (".yaml", ".yml"):
                continue
            mapping = ASSERTION_MAP.get(src.name)
            if mapping is None:
                report.unmapped.append(src)
                continue
            persona, v2_name = mapping
            dest = crucible_dir / "skills" / persona / "assertions" / v2_name
            _migrate_one(src, dest, project_root, report)

    # --- Prewrite templates (structural reshape) ---
    prewrite_src = crucible_dir / "templates" / "prewrite"
    if prewrite_src.exists():
        for src in sorted(prewrite_src.iterdir()):
            if not src.is_file() or src.suffix != ".md":
                continue
            name = src.stem  # e.g. "prd"
            dest = crucible_dir / "skills" / "pre-write" / name / "SKILL.md"
            _migrate_one(src, dest, project_root, report, structural=True)

    return ok(report)
