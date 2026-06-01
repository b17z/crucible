"""Tests for crucible migrate v1-to-v2.

Hermetic: every test sets up its own tmp_path with a fixture v1
.crucible/ layout, runs the migration, asserts the resulting layout.
"""

from __future__ import annotations

from pathlib import Path

from crucible.migrate import migrate_v1_to_v2


def _setup_v1_project(root: Path) -> None:
    """Create a v1-shape .crucible/ with mapped + unmapped files."""
    cru = root / ".crucible"
    (cru / "knowledge").mkdir(parents=True)
    (cru / "assertions").mkdir(parents=True)
    (cru / "templates" / "prewrite").mkdir(parents=True)
    (cru / "knowledge" / "SECURITY.md").write_text("v1 SECURITY\n")
    (cru / "knowledge" / "TESTING.md").write_text("v1 TESTING\n")
    (cru / "knowledge" / "MY_CUSTOM.md").write_text("user file\n")
    (cru / "assertions" / "security.yaml").write_text("name: security\n")
    (cru / "templates" / "prewrite" / "prd.md").write_text("---\nname: prd\n---\nbody\n")


class TestMigrate:
    def test_moves_mapped_files_to_v2_locations(self, tmp_path: Path) -> None:
        _setup_v1_project(tmp_path)
        result = migrate_v1_to_v2(tmp_path)
        assert result.is_ok
        report = result.value

        assert len(report.moved) == 4  # SECURITY, TESTING, security.yaml, prd.md

        # Check actual destinations
        assert (tmp_path / ".crucible/skills/security-engineer/knowledge/security-principles.md").exists()
        assert (tmp_path / ".crucible/skills/tech-lead/knowledge/testing.md").exists()
        assert (tmp_path / ".crucible/skills/security-engineer/assertions/security.yaml").exists()
        assert (tmp_path / ".crucible/skills/pre-write/prd/SKILL.md").exists()

        # Sources removed
        assert not (tmp_path / ".crucible/knowledge/SECURITY.md").exists()
        assert not (tmp_path / ".crucible/knowledge/TESTING.md").exists()
        assert not (tmp_path / ".crucible/assertions/security.yaml").exists()
        assert not (tmp_path / ".crucible/templates/prewrite/prd.md").exists()

    def test_preserves_unmapped_user_files(self, tmp_path: Path) -> None:
        _setup_v1_project(tmp_path)
        result = migrate_v1_to_v2(tmp_path)
        assert result.is_ok
        report = result.value

        # MY_CUSTOM.md isn't in the persona map, so it stays
        assert (tmp_path / ".crucible/knowledge/MY_CUSTOM.md").exists()
        unmapped_names = [p.name for p in report.unmapped]
        assert "MY_CUSTOM.md" in unmapped_names

    def test_creates_backup(self, tmp_path: Path) -> None:
        _setup_v1_project(tmp_path)
        result = migrate_v1_to_v2(tmp_path)
        assert result.is_ok

        backup_root = tmp_path / ".crucible.v1-backup"
        assert (backup_root / ".crucible/knowledge/SECURITY.md").exists()
        assert (backup_root / ".crucible/assertions/security.yaml").exists()
        assert (backup_root / ".crucible/templates/prewrite/prd.md").exists()

        # Backup content equals original v1 content
        assert (backup_root / ".crucible/knowledge/SECURITY.md").read_text() == "v1 SECURITY\n"

    def test_idempotent_second_run_is_noop(self, tmp_path: Path) -> None:
        """The hard requirement from the Phase 0 SPEC."""
        _setup_v1_project(tmp_path)

        result1 = migrate_v1_to_v2(tmp_path)
        assert result1.is_ok

        # Snapshot final state.
        v2_path = tmp_path / ".crucible/skills/security-engineer/knowledge/security-principles.md"
        before_content = v2_path.read_text()
        before_mtime = v2_path.stat().st_mtime

        result2 = migrate_v1_to_v2(tmp_path)
        assert result2.is_ok
        report2 = result2.value

        # No new moves; no new backups; v2 file untouched.
        assert report2.moved == []
        assert report2.backed_up == []
        assert v2_path.read_text() == before_content
        assert v2_path.stat().st_mtime == before_mtime

        # Unmapped file still surfaces every run (the right behavior —
        # it's informational, not action-required).
        assert any(p.name == "MY_CUSTOM.md" for p in report2.unmapped)

    def test_conflict_does_not_overwrite(self, tmp_path: Path) -> None:
        """If destination exists with different content, fail loud."""
        _setup_v1_project(tmp_path)
        # Pre-create destination with conflicting content.
        dest = tmp_path / ".crucible/skills/security-engineer/knowledge/security-principles.md"
        dest.parent.mkdir(parents=True)
        dest.write_text("PRE-EXISTING different content\n")

        result = migrate_v1_to_v2(tmp_path)
        assert result.is_ok
        report = result.value

        # Conflict recorded
        assert len(report.conflicts) == 1
        src, dest_reported, _reason = report.conflicts[0]
        assert src.name == "SECURITY.md"
        assert dest_reported == dest

        # Destination NOT overwritten
        assert dest.read_text() == "PRE-EXISTING different content\n"
        # Source NOT removed (operator needs to resolve manually)
        assert (tmp_path / ".crucible/knowledge/SECURITY.md").exists()

    def test_no_op_on_empty_project(self, tmp_path: Path) -> None:
        """No .crucible/ → empty report, no error."""
        result = migrate_v1_to_v2(tmp_path)
        assert result.is_ok
        report = result.value
        assert not report.changed
        assert report.unmapped == []

    def test_partial_completion_recovery(self, tmp_path: Path) -> None:
        """If a prior run was interrupted mid-move (source still exists,
        destination already complete), the second run finishes the job."""
        _setup_v1_project(tmp_path)
        # Simulate half-finished: dest exists with same content, source still exists too.
        dest = tmp_path / ".crucible/skills/security-engineer/knowledge/security-principles.md"
        dest.parent.mkdir(parents=True)
        dest.write_text("v1 SECURITY\n")  # same content as source

        result = migrate_v1_to_v2(tmp_path)
        assert result.is_ok
        report = result.value

        # Source removed, dest kept
        assert not (tmp_path / ".crucible/knowledge/SECURITY.md").exists()
        assert dest.exists()
        # Recorded as "already done", not as a fresh move.
        assert any(p.name == "SECURITY.md" for p in report.skipped_already_done)
