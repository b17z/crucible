"""Tests for crucible CLI - skill management commands."""

from pathlib import Path
from unittest.mock import patch

from crucible.cli import (
    SKILLS_BUNDLED,
    _load_review_config,
    cmd_review,
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


class TestLoadReviewConfig:
    """Test review config loading."""

    def test_load_config_from_project(self, tmp_path: Path) -> None:
        """Should load config from .crucible/review.yaml."""
        config_dir = tmp_path / ".crucible"
        config_dir.mkdir()
        config_content = """
fail_on: medium
skip_tools:
  - slither
  - bandit
fail_on_domain:
  smart_contract: critical
include_context: true
"""
        (config_dir / "review.yaml").write_text(config_content)

        config = _load_review_config(str(tmp_path))

        assert config.get("fail_on") == "medium"
        assert config.get("skip_tools") == ["slither", "bandit"]
        assert config.get("fail_on_domain") == {"smart_contract": "critical"}
        assert config.get("include_context") is True

    def test_load_config_empty_when_no_file(self, tmp_path: Path) -> None:
        """Should return empty dict when no config file exists."""
        config = _load_review_config(str(tmp_path))
        assert config == {}

    def test_load_config_handles_invalid_yaml(self, tmp_path: Path) -> None:
        """Should handle invalid YAML gracefully."""
        config_dir = tmp_path / ".crucible"
        config_dir.mkdir()
        (config_dir / "review.yaml").write_text("invalid: yaml: content: [")

        config = _load_review_config(str(tmp_path))
        # Should return empty dict on error
        assert config == {}


class TestCmdReview:
    """Test the review command."""

    def test_review_not_a_git_repo(self, tmp_path: Path, capsys) -> None:
        """Should error when not in a git repo."""
        class Args:
            mode = "staged"
            base = None
            fail_on = None
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        result = cmd_review(Args())
        assert result == 1
        captured = capsys.readouterr()
        assert "not a git repository" in captured.out

    def test_review_staged_no_changes(self, tmp_path: Path, capsys) -> None:
        """Should handle no staged changes."""
        from crucible.errors import ok
        from crucible.tools.git import GitContext

        class Args:
            mode = "staged"
            base = None
            fail_on = None
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        empty_context = GitContext(mode="staged", base_ref=None, changes=(), commit_messages=())

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_staged_changes", return_value=ok(empty_context)),
        ):
            result = cmd_review(Args())
            assert result == 0
            captured = capsys.readouterr()
            assert "No changes to review" in captured.out

    def test_review_unstaged_no_changes(self, tmp_path: Path, capsys) -> None:
        """Should handle no unstaged changes."""
        from crucible.errors import ok
        from crucible.tools.git import GitContext

        class Args:
            mode = "unstaged"
            base = None
            fail_on = None
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        empty_context = GitContext(mode="unstaged", base_ref=None, changes=(), commit_messages=())

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_unstaged_changes", return_value=ok(empty_context)),
        ):
            result = cmd_review(Args())
            assert result == 0
            captured = capsys.readouterr()
            assert "No unstaged changes" in captured.out

    def test_review_with_findings_passes_without_threshold(self, tmp_path: Path, capsys) -> None:
        """Should pass when findings exist but no fail threshold set."""
        from crucible.errors import ok
        from crucible.models import Severity, ToolFinding
        from crucible.tools.git import GitChange, GitContext, LineRange

        class Args:
            mode = "staged"
            base = None
            fail_on = None
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        change = GitChange(path="test.py", status="M", added_lines=(LineRange(1, 1),), old_path=None)
        context = GitContext(mode="staged", base_ref=None, changes=(change,), commit_messages=())
        finding = ToolFinding(
            tool="ruff",
            rule="E501",
            severity=Severity.LOW,
            message="Line too long",
            location="test.py:1",
        )

        # Create test file
        (tmp_path / "test.py").write_text("x = 1\n")

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_staged_changes", return_value=ok(context)),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([finding])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = cmd_review(Args())
            # Without --fail-on, should always pass
            assert result == 0

    def test_review_with_findings_fails_with_threshold(self, tmp_path: Path, capsys) -> None:
        """Should fail when findings exceed threshold."""
        from crucible.errors import ok
        from crucible.models import Severity, ToolFinding
        from crucible.tools.git import GitChange, GitContext, LineRange

        class Args:
            mode = "staged"
            base = None
            fail_on = "low"  # Fail on low or higher
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        change = GitChange(path="test.py", status="M", added_lines=(LineRange(1, 1),), old_path=None)
        context = GitContext(mode="staged", base_ref=None, changes=(change,), commit_messages=())
        finding = ToolFinding(
            tool="ruff",
            rule="E501",
            severity=Severity.LOW,
            message="Line too long",
            location="test.py:1",
        )

        # Create test file
        (tmp_path / "test.py").write_text("x = 1\n")

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_staged_changes", return_value=ok(context)),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([finding])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = cmd_review(Args())
            # With --fail-on low, should fail
            assert result == 1
            captured = capsys.readouterr()
            assert "FAILED" in captured.out

    def test_review_json_output(self, tmp_path: Path, capsys) -> None:
        """Should output JSON when --json is set."""
        import json

        from crucible.errors import ok
        from crucible.models import Severity, ToolFinding
        from crucible.tools.git import GitChange, GitContext, LineRange

        class Args:
            mode = "staged"
            base = None
            fail_on = None
            include_context = False
            json = True
            quiet = False
            path = str(tmp_path)

        change = GitChange(path="test.py", status="M", added_lines=(LineRange(1, 1),), old_path=None)
        context = GitContext(mode="staged", base_ref=None, changes=(change,), commit_messages=())
        finding = ToolFinding(
            tool="ruff",
            rule="E501",
            severity=Severity.LOW,
            message="Line too long",
            location="test.py:1",
        )

        # Create test file
        (tmp_path / "test.py").write_text("x = 1\n")

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_staged_changes", return_value=ok(context)),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([finding])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = cmd_review(Args())
            assert result == 0

            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert output["mode"] == "staged"
            assert output["passed"] is True
            assert "findings" in output

    def test_review_branch_mode(self, tmp_path: Path, capsys) -> None:
        """Should use branch diff mode correctly."""
        from crucible.errors import ok
        from crucible.tools.git import GitContext

        class Args:
            mode = "branch"
            base = "develop"
            fail_on = None
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        empty_context = GitContext(mode="branch", base_ref="develop", changes=(), commit_messages=())

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_branch_diff", return_value=ok(empty_context)) as mock_diff,
        ):
            result = cmd_review(Args())
            assert result == 0
            mock_diff.assert_called_once_with(str(tmp_path), "develop")

    def test_review_commits_mode(self, tmp_path: Path, capsys) -> None:
        """Should use commits mode correctly."""
        from crucible.errors import ok
        from crucible.tools.git import GitContext

        class Args:
            mode = "commits"
            base = "3"  # Last 3 commits
            fail_on = None
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        empty_context = GitContext(mode="commits", base_ref=None, changes=(), commit_messages=())

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_recent_commits", return_value=ok(empty_context)) as mock_commits,
        ):
            result = cmd_review(Args())
            assert result == 0
            mock_commits.assert_called_once_with(str(tmp_path), 3)

    def test_review_config_default_threshold(self, tmp_path: Path, capsys) -> None:
        """Should use threshold from config when not specified on CLI."""
        from crucible.errors import ok
        from crucible.models import Severity, ToolFinding
        from crucible.tools.git import GitChange, GitContext, LineRange

        # Create config file with fail_on: low
        config_dir = tmp_path / ".crucible"
        config_dir.mkdir()
        (config_dir / "review.yaml").write_text("fail_on: low\n")

        class Args:
            mode = "staged"
            base = None
            fail_on = None  # Not specified on CLI
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        change = GitChange(path="test.py", status="M", added_lines=(LineRange(1, 1),), old_path=None)
        context = GitContext(mode="staged", base_ref=None, changes=(change,), commit_messages=())
        finding = ToolFinding(
            tool="ruff",
            rule="E501",
            severity=Severity.LOW,
            message="Line too long",
            location="test.py:1",
        )

        (tmp_path / "test.py").write_text("x = 1\n")

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_staged_changes", return_value=ok(context)),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([finding])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = cmd_review(Args())
            # Config specifies fail_on: low, so should fail
            assert result == 1
            captured = capsys.readouterr()
            assert "FAILED" in captured.out

    def test_review_config_per_domain_threshold(self, tmp_path: Path, capsys) -> None:
        """Should use stricter per-domain threshold for smart contracts."""
        from crucible.errors import ok
        from crucible.models import Severity, ToolFinding
        from crucible.tools.git import GitChange, GitContext, LineRange

        # Create config with stricter threshold for smart_contract
        config_dir = tmp_path / ".crucible"
        config_dir.mkdir()
        config = """
fail_on: low
fail_on_domain:
  smart_contract: critical
"""
        (config_dir / "review.yaml").write_text(config)

        class Args:
            mode = "staged"
            base = None
            fail_on = None
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        # Solidity file triggers smart_contract domain
        change = GitChange(path="Vault.sol", status="M", added_lines=(LineRange(1, 1),), old_path=None)
        context = GitContext(mode="staged", base_ref=None, changes=(change,), commit_messages=())
        finding = ToolFinding(
            tool="slither",
            rule="reentrancy",
            severity=Severity.HIGH,  # HIGH, not CRITICAL
            message="Reentrancy vulnerability",
            location="Vault.sol:1",
        )

        (tmp_path / "Vault.sol").write_text("// solidity\n")

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_staged_changes", return_value=ok(context)),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_slither", return_value=ok([finding])),
        ):
            result = cmd_review(Args())
            # Per-domain threshold is critical, but finding is high, so should pass
            assert result == 0

    def test_review_config_skip_tools(self, tmp_path: Path, capsys) -> None:
        """Should skip tools specified in config."""
        from crucible.errors import ok
        from crucible.tools.git import GitChange, GitContext, LineRange

        # Create config that skips bandit
        config_dir = tmp_path / ".crucible"
        config_dir.mkdir()
        (config_dir / "review.yaml").write_text("skip_tools:\n  - bandit\n")

        class Args:
            mode = "staged"
            base = None
            fail_on = None
            include_context = False
            json = False
            quiet = False
            path = str(tmp_path)

        change = GitChange(path="test.py", status="M", added_lines=(LineRange(1, 1),), old_path=None)
        context = GitContext(mode="staged", base_ref=None, changes=(change,), commit_messages=())

        (tmp_path / "test.py").write_text("x = 1\n")

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_staged_changes", return_value=ok(context)),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])) as mock_bandit,
        ):
            result = cmd_review(Args())
            # bandit should not be called due to skip_tools config
            mock_bandit.assert_not_called()
            assert result == 0

    def test_review_report_format(self, tmp_path: Path, capsys) -> None:
        """Should output markdown report when --format report is used."""
        from crucible.errors import ok
        from crucible.models import Severity, ToolFinding
        from crucible.tools.git import GitChange, GitContext, LineRange

        class Args:
            mode = "staged"
            base = None
            fail_on = "high"
            include_context = False
            json = False
            format = "report"
            quiet = False
            path = str(tmp_path)

        change = GitChange(path="test.py", status="M", added_lines=(LineRange(1, 1),), old_path=None)
        context = GitContext(mode="staged", base_ref=None, changes=(change,), commit_messages=())
        finding = ToolFinding(
            tool="ruff",
            rule="E501",
            severity=Severity.MEDIUM,
            message="Line too long",
            location="test.py:1",
        )

        (tmp_path / "test.py").write_text("x = 1\n")

        with (
            patch("crucible.tools.git.is_git_repo", return_value=True),
            patch("crucible.tools.git.get_repo_root", return_value=ok(str(tmp_path))),
            patch("crucible.tools.git.get_staged_changes", return_value=ok(context)),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([finding])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = cmd_review(Args())
            captured = capsys.readouterr()

            # Should be markdown format
            assert "# Code Review Report" in captured.out
            assert "## Summary" in captured.out
            assert "## Files Changed" in captured.out
            assert "## Findings" in captured.out
            assert "### MEDIUM" in captured.out
            assert "`test.py`" in captured.out
            assert "**Tool:** ruff" in captured.out
            assert "*Generated by Crucible*" in captured.out
            # Should pass because only medium findings and threshold is high
            assert result == 0


class TestInitCommand:
    """Test crucible init command."""

    def test_init_creates_directory_structure(self, tmp_path: Path) -> None:
        """Should create .crucible directory with subdirs and config."""
        from argparse import Namespace

        from crucible.cli import cmd_init

        args = Namespace(path=str(tmp_path), force=False, minimal=True)
        result = cmd_init(args)

        assert result == 0
        assert (tmp_path / ".crucible").exists()
        assert (tmp_path / ".crucible" / "skills").exists()
        assert (tmp_path / ".crucible" / "knowledge").exists()
        assert (tmp_path / ".crucible" / "review.yaml").exists()
        assert (tmp_path / ".crucible" / ".gitignore").exists()

    def test_init_fails_if_exists_without_force(self, tmp_path: Path, capsys) -> None:
        """Should fail if .crucible exists and --force not specified."""
        from argparse import Namespace

        from crucible.cli import cmd_init

        (tmp_path / ".crucible").mkdir()

        args = Namespace(path=str(tmp_path), force=False, minimal=True)
        result = cmd_init(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "already exists" in captured.out

    def test_init_succeeds_with_force(self, tmp_path: Path) -> None:
        """Should overwrite if --force specified."""
        from argparse import Namespace

        from crucible.cli import cmd_init

        (tmp_path / ".crucible").mkdir()

        args = Namespace(path=str(tmp_path), force=True, minimal=True)
        result = cmd_init(args)

        assert result == 0

    def test_init_detects_python_stack(self, tmp_path: Path, capsys) -> None:
        """Should detect Python stack from pyproject.toml."""
        from argparse import Namespace

        from crucible.cli import cmd_init

        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        args = Namespace(path=str(tmp_path), force=False, minimal=False)
        result = cmd_init(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "python" in captured.out.lower()

    def test_init_detects_solidity_stack(self, tmp_path: Path, capsys) -> None:
        """Should detect Solidity stack from foundry.toml."""
        from argparse import Namespace

        from crucible.cli import cmd_init

        (tmp_path / "foundry.toml").write_text("[profile.default]\n")

        args = Namespace(path=str(tmp_path), force=False, minimal=False)
        result = cmd_init(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "solidity" in captured.out.lower()


class TestCiGenerateCommand:
    """Test crucible ci generate command."""

    def test_ci_generate_outputs_workflow(self, capsys) -> None:
        """Should output valid GitHub Actions workflow."""
        from argparse import Namespace

        from crucible.cli import cmd_ci_generate

        args = Namespace(fail_on="high", output=None)
        result = cmd_ci_generate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "name: Crucible Code Review" in captured.out
        assert "pip install crucible-mcp" in captured.out
        assert "--fail-on high" in captured.out
        assert "${{ github.event_name }}" in captured.out

    def test_ci_generate_respects_fail_on(self, capsys) -> None:
        """Should use specified fail-on threshold."""
        from argparse import Namespace

        from crucible.cli import cmd_ci_generate

        args = Namespace(fail_on="critical", output=None)
        result = cmd_ci_generate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "--fail-on critical" in captured.out

    def test_ci_generate_writes_to_file(self, tmp_path: Path) -> None:
        """Should write to file when --output specified."""
        from argparse import Namespace

        from crucible.cli import cmd_ci_generate

        output_path = tmp_path / ".github" / "workflows" / "crucible.yml"
        args = Namespace(fail_on="high", output=str(output_path))
        result = cmd_ci_generate(args)

        assert result == 0
        assert output_path.exists()
        content = output_path.read_text()
        assert "name: Crucible Code Review" in content
