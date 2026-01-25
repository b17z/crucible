"""Tests for crucible CLI - skill management commands."""

from pathlib import Path
from unittest.mock import patch

from crucible.cli import (
    SKILLS_BUNDLED,
    cmd_skills_init,
    cmd_skills_list,
    cmd_skills_show,
    get_all_skill_names,
    resolve_skill,
)


class TestResolveSkill:
    """Test skill resolution cascade."""

    def test_bundled_skill_found(self, tmp_path: Path) -> None:
        """Bundled skills should be found when no overrides exist."""
        # Patch both project and user to non-existent paths
        with (
            patch("crucible.cli.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.cli.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            path, source = resolve_skill("security-engineer")
            assert path is not None
            assert source == "bundled"
            assert path.exists()

    def test_nonexistent_skill_returns_none(self) -> None:
        """Non-existent skill should return None."""
        path, source = resolve_skill("nonexistent-skill-12345")
        assert path is None
        assert source == ""

    def test_project_takes_priority(self, tmp_path: Path) -> None:
        """Project-level skill should take priority over bundled."""
        # Create a project skill
        project_skill = tmp_path / ".crucible" / "skills" / "security-engineer"
        project_skill.mkdir(parents=True)
        (project_skill / "SKILL.md").write_text("# Custom Security\n")

        with patch("crucible.cli.SKILLS_PROJECT", tmp_path / ".crucible" / "skills"):
            path, source = resolve_skill("security-engineer")
            assert source == "project"
            assert "Custom Security" in path.read_text()

    def test_user_takes_priority_over_bundled(self, tmp_path: Path) -> None:
        """User-level skill should take priority over bundled."""
        # Create a user skill
        user_skill = tmp_path / "user-skills" / "security-engineer"
        user_skill.mkdir(parents=True)
        (user_skill / "SKILL.md").write_text("# User Security\n")

        with (
            patch("crucible.cli.SKILLS_USER", tmp_path / "user-skills"),
            patch("crucible.cli.SKILLS_PROJECT", tmp_path / "nonexistent"),
        ):
            path, source = resolve_skill("security-engineer")
            assert source == "user"
            assert "User Security" in path.read_text()


class TestGetAllSkillNames:
    """Test getting all available skill names."""

    def test_returns_bundled_skills(self) -> None:
        """Should return all bundled skill names."""
        names = get_all_skill_names()
        assert "security-engineer" in names
        assert "web3-engineer" in names
        assert "backend-engineer" in names

    def test_returns_at_least_18_skills(self) -> None:
        """Should have at least 18 bundled skills."""
        names = get_all_skill_names()
        assert len(names) >= 18


class TestSkillsInit:
    """Test skills init command."""

    def test_init_creates_project_skill(self, tmp_path: Path) -> None:
        """skills init should copy skill to .crucible/skills/."""
        project_dir = tmp_path / ".crucible" / "skills"

        with patch("crucible.cli.SKILLS_PROJECT", project_dir):
            # Mock args
            class Args:
                skill = "security-engineer"
                force = False

            result = cmd_skills_init(Args())

            assert result == 0
            assert (project_dir / "security-engineer" / "SKILL.md").exists()

    def test_init_fails_if_exists_without_force(self, tmp_path: Path) -> None:
        """skills init should fail if skill exists without --force."""
        project_dir = tmp_path / ".crucible" / "skills"
        existing = project_dir / "security-engineer"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("# Existing\n")

        with patch("crucible.cli.SKILLS_PROJECT", project_dir):
            class Args:
                skill = "security-engineer"
                force = False

            result = cmd_skills_init(Args())
            assert result == 1  # Should fail

    def test_init_overwrites_with_force(self, tmp_path: Path) -> None:
        """skills init --force should overwrite existing skill."""
        project_dir = tmp_path / ".crucible" / "skills"
        existing = project_dir / "security-engineer"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("# Old Content\n")

        with patch("crucible.cli.SKILLS_PROJECT", project_dir):
            class Args:
                skill = "security-engineer"
                force = True

            result = cmd_skills_init(Args())
            assert result == 0

            # Content should be from bundled, not old
            content = (existing / "SKILL.md").read_text()
            assert "Old Content" not in content

    def test_init_nonexistent_skill_fails(self, tmp_path: Path) -> None:
        """skills init with non-existent skill should fail."""
        with patch("crucible.cli.SKILLS_PROJECT", tmp_path):
            class Args:
                skill = "nonexistent-skill-12345"
                force = False

            result = cmd_skills_init(Args())
            assert result == 1


class TestSkillsShow:
    """Test skills show command."""

    def test_show_bundled_skill(self, capsys) -> None:
        """skills show should display bundled skill location."""
        class Args:
            skill = "security-engineer"

        result = cmd_skills_show(Args())
        assert result == 0

        captured = capsys.readouterr()
        assert "security-engineer" in captured.out
        assert "Bundled:" in captured.out

    def test_show_nonexistent_skill_fails(self) -> None:
        """skills show with non-existent skill should fail."""
        class Args:
            skill = "nonexistent-skill-12345"

        result = cmd_skills_show(Args())
        assert result == 1

    def test_show_marks_active_source(self, capsys, tmp_path: Path) -> None:
        """skills show should mark the active source."""
        # Create a project skill
        project_dir = tmp_path / ".crucible" / "skills"
        project_skill = project_dir / "security-engineer"
        project_skill.mkdir(parents=True)
        (project_skill / "SKILL.md").write_text("# Project\n")

        with patch("crucible.cli.SKILLS_PROJECT", project_dir):
            class Args:
                skill = "security-engineer"

            result = cmd_skills_show(Args())
            assert result == 0

            captured = capsys.readouterr()
            assert "← active" in captured.out
            assert "Project:" in captured.out


class TestSkillsList:
    """Test skills list command."""

    def test_list_shows_bundled(self, capsys) -> None:
        """skills list should show bundled skills."""
        class Args:
            pass

        result = cmd_skills_list(Args())
        assert result == 0

        captured = capsys.readouterr()
        assert "Bundled skills:" in captured.out
        assert "security-engineer" in captured.out

    def test_list_shows_all_sources(self, capsys) -> None:
        """skills list should show all three source categories."""
        class Args:
            pass

        result = cmd_skills_list(Args())
        assert result == 0

        captured = capsys.readouterr()
        assert "Bundled skills:" in captured.out
        assert "User skills" in captured.out
        assert "Project skills" in captured.out


class TestSkillMetadata:
    """Test skill SKILL.md metadata."""

    def test_security_engineer_has_version(self) -> None:
        """Security engineer skill should have version metadata."""
        skill_path = SKILLS_BUNDLED / "security-engineer" / "SKILL.md"
        content = skill_path.read_text()
        assert "version:" in content

    def test_skill_has_triggers(self) -> None:
        """Skills should have trigger keywords."""
        skill_path = SKILLS_BUNDLED / "security-engineer" / "SKILL.md"
        content = skill_path.read_text()
        assert "triggers:" in content
        assert "security" in content.lower()
