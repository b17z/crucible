"""Tests for unified review MCP tool."""

from pathlib import Path
from unittest.mock import patch

import pytest

from crucible.errors import ok
from crucible.models import Domain, Severity, ToolFinding
from crucible.review.core import detect_domain_for_file
from crucible.server import (
    _handle_load_knowledge,
    _handle_review,
)


class TestDomainDetection:
    """Test domain detection used by full_review."""

    def test_python_domain(self) -> None:
        """Python files should detect as backend."""
        domain, tags = detect_domain_for_file("app.py")
        assert domain == Domain.BACKEND
        assert "python" in tags
        assert "backend" in tags

    def test_solidity_domain(self) -> None:
        """Solidity files should detect as smart_contract."""
        domain, tags = detect_domain_for_file("Contract.sol")
        assert domain == Domain.SMART_CONTRACT
        assert "solidity" in tags
        assert "web3" in tags

    def test_typescript_domain(self) -> None:
        """TypeScript files should detect as frontend."""
        domain, tags = detect_domain_for_file("App.tsx")
        assert domain == Domain.FRONTEND
        assert "typescript" in tags
        assert "frontend" in tags

    def test_unknown_domain(self) -> None:
        """Unknown extensions should detect as unknown."""
        domain, tags = detect_domain_for_file("README.md")
        assert domain == Domain.UNKNOWN
        assert tags == []  # detect_domain_for_file returns empty list for unknown


class TestHandleLoadKnowledge:
    """Test _handle_load_knowledge handler."""

    def test_load_by_topic(self) -> None:
        """Should load knowledge by topic."""
        result = _handle_load_knowledge({"topic": "security"})
        assert len(result) == 1
        text = result[0].text
        assert "security" in text.lower()

    def test_load_specific_files(self) -> None:
        """Should load specific files."""
        result = _handle_load_knowledge({"files": ["SECURITY.md"]})
        assert len(result) == 1
        text = result[0].text
        assert "Knowledge Loaded" in text
        assert "SECURITY.md" in text

    def test_load_custom_knowledge_with_bundled(self, tmp_path: Path) -> None:
        """Should load custom project knowledge alongside bundled."""
        project_knowledge = tmp_path / ".crucible" / "knowledge"
        project_knowledge.mkdir(parents=True)
        (project_knowledge / "TEAM_RULES.md").write_text("# Team Rules\n\nAlways use TypeScript.\n")

        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", project_knowledge),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
        ):
            # With default include_bundled=True, should get both custom and bundled
            result = _handle_load_knowledge({})
            text = result[0].text
            assert "TEAM_RULES.md" in text
            assert "Always use TypeScript" in text
            # Should also have bundled files
            assert "SECURITY.md" in text

    def test_include_bundled_default(self) -> None:
        """Should include bundled files by default."""
        result = _handle_load_knowledge({})  # No arguments, defaults to include_bundled=True
        text = result[0].text
        assert "SECURITY.md" in text

    def test_exclude_bundled(self, tmp_path: Path) -> None:
        """Should be able to exclude bundled files."""
        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
        ):
            result = _handle_load_knowledge({"include_bundled": False})
            text = result[0].text
            # With no custom files and bundled excluded, should show no files message
            assert "No knowledge files found" in text


class TestUnifiedReview:
    """Test unified _handle_review handler."""

    def test_path_based_review(self, tmp_path: Path) -> None:
        """Path-based review should work like full_review."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = _handle_review({"path": str(test_file)})
            text = result[0].text
            assert "Code Review" in text
            assert "python" in text.lower()
            assert "security-engineer" in text

    def test_path_based_quick_review(self, tmp_path: Path) -> None:
        """Path-based review with include_skills=false should be quick."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = _handle_review({
                "path": str(test_file),
                "include_skills": False,
                "include_knowledge": False,
            })
            text = result[0].text
            assert "Code Review" in text
            # Should NOT have skills section
            assert "Applicable Skills" not in text
            # Should NOT have knowledge section
            assert "Knowledge Loaded" not in text

    def test_requires_path_or_mode(self) -> None:
        """Should error if neither path nor mode provided."""
        result = _handle_review({})
        text = result[0].text
        assert "Error" in text
        assert "path" in text.lower() or "mode" in text.lower()

    def test_skill_override(self, tmp_path: Path) -> None:
        """Should respect skill override."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = _handle_review({
                "path": str(test_file),
                "skills": ["web3-engineer"],
            })
            text = result[0].text
            assert "web3-engineer" in text

    def test_findings_included(self, tmp_path: Path) -> None:
        """Should include static analysis findings."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        mock_findings = [
            ToolFinding(
                tool="ruff",
                rule="E501",
                severity=Severity.LOW,
                message="Line too long",
                location="test.py:1",
            ),
        ]

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok(mock_findings)),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = _handle_review({"path": str(test_file)})
            text = result[0].text
            assert "E501" in text
            assert "Line too long" in text


class TestReviewVerifierIntegration:
    """The review MCP tool should run the verifier before rendering output."""

    def test_b101_in_tests_suppressed(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_a.py"
        test_file.write_text("assert True\n")

        mock_findings = [
            ToolFinding(
                tool="bandit",
                rule="B101",
                severity=Severity.LOW,
                message="assert used",
                location=f"{test_file}:1",
            ),
        ]

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok(mock_findings)),
        ):
            result = _handle_review({"path": str(tests_dir)})
            text = result[0].text

        assert "Suppressed" in text
        assert "B101" not in text.split("Suppressed")[0]

    def test_git_mode_suppresses_with_repo_relative_location(self, tmp_path: Path) -> None:
        """Git-mode findings carry repo-relative locations; the verifier must
        resolve them against repo_root, not the process cwd."""
        from crucible.errors import ok as ok_result
        from crucible.tools.git import GitChange, GitContext, LineRange

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_a.py").write_text("assert True\n")

        # Repo-relative location, as produced by run_static_analysis in git mode
        # (full_path is built from repo_path, but findings from real tools
        # commonly report paths relative to repo root).
        mock_findings = [
            ToolFinding(
                tool="bandit",
                rule="B101",
                severity=Severity.LOW,
                message="assert used",
                location="tests/test_a.py:1",
            ),
        ]

        git_context = GitContext(
            mode="staged",
            base_ref=None,
            changes=(
                GitChange(
                    path="tests/test_a.py",
                    status="M",
                    added_lines=(LineRange(start=1, end=1),),
                ),
            ),
            commit_messages=(),
        )

        with (
            patch("crucible.server.get_repo_root", return_value=ok_result(str(tmp_path))),
            patch("crucible.server.get_staged_changes", return_value=ok_result(git_context)),
            patch("crucible.server.run_static_analysis", return_value=(mock_findings, [])),
            patch("crucible.server.run_enforcement", return_value=([], [], 0, 0, None)),
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            # Ensure a relative-path resolution against process cwd would fail:
            # if repo_root threading regresses, the verifier can't read the
            # file and fails open, leaving B101 active.
            patch("os.getcwd", return_value=str(tmp_path.parent)),
        ):
            result = _handle_review({"mode": "staged"})
            text = result[0].text

        assert "Suppressed" in text
        assert "B101" not in text.split("Suppressed")[0]


class TestSeverityCountsSkipSuppressed:
    def test_suppressed_not_counted(self) -> None:
        import dataclasses

        from crucible.models import Severity, ToolFinding
        from crucible.review.core import compute_severity_counts

        active = ToolFinding(tool="bandit", rule="B102", severity=Severity.HIGH,
                             message="m", location="a.py:1")
        muted = dataclasses.replace(
            ToolFinding(tool="bandit", rule="B101", severity=Severity.LOW,
                        message="m", location="tests/test_a.py:1"),
            suppressed=True, suppression_reason="verifier:is_test_file — t")
        counts = compute_severity_counts([active, muted])
        assert counts.get("high") == 1
        assert counts.get("low", 0) == 0


class TestParallelDelegation:
    def test_wall_clock_beats_sequential(self, tmp_path) -> None:
        import time
        from unittest.mock import patch

        from crucible.errors import ok
        from crucible.models import Domain
        from crucible.review.core import run_static_analysis

        def slow(name):
            def delegate(*args, **kwargs):
                time.sleep(0.3)
                return ok([])
            return delegate

        with (
            patch("crucible.review.core.delegate_semgrep", slow("semgrep")),
            patch("crucible.review.core.delegate_ruff", slow("ruff")),
            patch("crucible.review.core.delegate_slither", slow("slither")),
            patch("crucible.review.core.delegate_bandit", slow("bandit")),
        ):
            start = time.monotonic()
            findings, errors = run_static_analysis(
                str(tmp_path), Domain.BACKEND, ["python"],
                tools=["semgrep", "ruff", "slither", "bandit"])
            elapsed = time.monotonic() - start
        assert errors == []
        assert elapsed < 0.9, f"4×0.3s delegates took {elapsed:.2f}s — not parallel"

    def test_error_aggregation_and_order(self, tmp_path) -> None:
        from unittest.mock import patch

        from crucible.errors import err, ok
        from crucible.models import Domain, Severity, ToolFinding
        from crucible.review.core import run_static_analysis

        f_ruff = ToolFinding(tool="ruff", rule="E1", severity=Severity.LOW,
                             message="m", location="a.py:1")
        with (
            patch("crucible.review.core.delegate_semgrep",
                  lambda *a, **k: err("semgrep exploded")),
            patch("crucible.review.core.delegate_ruff", lambda *a, **k: ok([f_ruff])),
        ):
            findings, errors = run_static_analysis(
                str(tmp_path), Domain.BACKEND, ["python"], tools=["semgrep", "ruff"])
        assert findings == [f_ruff]
        assert errors == ["semgrep: semgrep exploded"]


class TestUnifiedReviewGitMode:
    """Test unified review in git mode."""

    def test_staged_mode_no_changes(self, tmp_path: Path) -> None:
        """Should handle no staged changes gracefully."""
        from crucible.errors import ok as ok_result
        from crucible.tools.git import GitContext

        with (
            patch("crucible.server.get_repo_root", return_value=ok_result(str(tmp_path))),
            patch("crucible.server.get_staged_changes", return_value=ok_result(
                GitContext(mode="staged", base_ref=None, changes=[], commit_messages=[])
            )),
        ):
            result = _handle_review({"mode": "staged"})
            text = result[0].text
            assert "No changes" in text or "Stage files" in text

    def test_invalid_mode(self) -> None:
        """Should error on invalid mode."""
        from crucible.errors import ok as ok_result

        with patch("crucible.server.get_repo_root", return_value=ok_result("/tmp")):
            result = _handle_review({"mode": "invalid"})
            text = result[0].text
            assert "Error" in text
            assert "invalid" in text.lower()
