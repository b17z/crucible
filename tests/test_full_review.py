"""Tests for unified review MCP tool and deprecated full_review."""

from pathlib import Path
from unittest.mock import patch

import pytest

from crucible.errors import ok
from crucible.models import Domain, FullReviewResult, Severity, ToolFinding
from crucible.review.core import detect_domain_for_file
from crucible.server import (
    _handle_full_review,
    _handle_load_knowledge,
    _handle_review,
)


class TestFullReviewResult:
    """Test FullReviewResult dataclass."""

    def test_create_result(self) -> None:
        """Should create a valid FullReviewResult."""
        result = FullReviewResult(
            domains_detected=("python", "backend"),
            severity_summary={"high": 1, "medium": 2},
            findings=(
                ToolFinding(
                    tool="ruff",
                    rule="E501",
                    severity=Severity.LOW,
                    message="Line too long",
                    location="test.py:10",
                ),
            ),
            applicable_skills=("security-engineer", "backend-engineer"),
            skill_triggers_matched={
                "security-engineer": ("always_run",),
                "backend-engineer": ("python", "backend"),
            },
            principles_loaded=("SECURITY.md", "ERROR_HANDLING.md"),
            principles_content="# Security\n...",
            sage_knowledge=None,
            sage_query_used=None,
        )
        assert result.domains_detected == ("python", "backend")
        assert result.severity_summary == {"high": 1, "medium": 2}
        assert len(result.findings) == 1
        assert len(result.applicable_skills) == 2
        assert result.sage_knowledge is None

    def test_result_is_frozen(self) -> None:
        """FullReviewResult should be immutable."""
        result = FullReviewResult(
            domains_detected=("python",),
            severity_summary={},
            findings=(),
            applicable_skills=(),
            skill_triggers_matched={},
            principles_loaded=(),
            principles_content="",
        )
        with pytest.raises(AttributeError):
            result.domains_detected = ("rust",)  # type: ignore[misc]


class TestHandleFullReview:
    """Test _handle_full_review handler."""

    def test_python_file_detects_backend_domain(self, tmp_path: Path) -> None:
        """Python file should detect backend domain."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            # Mock the delegation tools to avoid actual tool execution
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = _handle_full_review({"path": str(test_file)})
            assert len(result) == 1
            text = result[0].text
            assert "python" in text.lower()
            assert "backend" in text.lower()

    def test_solidity_file_detects_smart_contract_domain(self, tmp_path: Path) -> None:
        """Solidity file should detect smart_contract domain."""
        test_file = tmp_path / "Contract.sol"
        test_file.write_text("pragma solidity ^0.8.0;\n")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_slither", return_value=ok([])),
        ):
            result = _handle_full_review({"path": str(test_file)})
            assert len(result) == 1
            text = result[0].text
            assert "solidity" in text.lower()
            assert "smart_contract" in text.lower()

    def test_includes_applicable_skills(self, tmp_path: Path) -> None:
        """Should include applicable skills in output."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = _handle_full_review({"path": str(test_file)})
            text = result[0].text
            # Security engineer should always be included
            assert "security-engineer" in text
            # Backend engineer should match python
            assert "backend-engineer" in text

    def test_includes_knowledge_files(self, tmp_path: Path) -> None:
        """Should include knowledge files in output."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = _handle_full_review({"path": str(test_file)})
            text = result[0].text
            # SECURITY.md should be loaded (from security-engineer)
            assert "SECURITY.md" in text

    def test_skill_override(self, tmp_path: Path) -> None:
        """Should respect skill override parameter."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = _handle_full_review({
                "path": str(test_file),
                "skills": ["web3-engineer"],  # Override with web3 for python file
            })
            text = result[0].text
            assert "web3-engineer" in text
            # Security should NOT be included (override skips matching)
            assert "security-engineer" not in text or "explicit" in text

    def test_findings_included_in_output(self, tmp_path: Path) -> None:
        """Should include findings in output."""
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
            result = _handle_full_review({"path": str(test_file)})
            text = result[0].text
            assert "E501" in text
            assert "Line too long" in text

    def test_severity_summary(self, tmp_path: Path) -> None:
        """Should include severity summary in output."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        mock_findings = [
            ToolFinding(
                tool="bandit",
                rule="B101",
                severity=Severity.HIGH,
                message="Use of assert",
                location="test.py:1",
            ),
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
            patch("crucible.review.core.delegate_ruff", return_value=ok([mock_findings[1]])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([mock_findings[0]])),
        ):
            result = _handle_full_review({"path": str(test_file)})
            text = result[0].text
            assert "high" in text.lower()
            assert "low" in text.lower()


class TestFullReviewIntegration:
    """Integration tests for full_review (requires actual tools)."""

    @pytest.mark.integration
    def test_full_review_python_file(self, tmp_path: Path) -> None:
        """Full review of Python file should work end-to-end."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def hello():
    x=1  # Missing spaces around =
    print(x)
""")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            result = _handle_full_review({"path": str(test_file)})
            assert len(result) == 1
            text = result[0].text
            # Should have basic structure
            assert "Full Review Results" in text
            assert "Domains detected" in text
            assert "Applicable Skills" in text


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

    def test_load_custom_knowledge(self, tmp_path: Path) -> None:
        """Should load custom project knowledge."""
        project_knowledge = tmp_path / ".crucible" / "knowledge"
        project_knowledge.mkdir(parents=True)
        (project_knowledge / "TEAM_RULES.md").write_text("# Team Rules\n\nAlways use TypeScript.\n")

        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", project_knowledge),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
        ):
            result = _handle_load_knowledge({})
            text = result[0].text
            assert "TEAM_RULES.md" in text
            assert "Always use TypeScript" in text

    def test_include_bundled(self) -> None:
        """Should include bundled files when requested."""
        result = _handle_load_knowledge({"include_bundled": True})
        text = result[0].text
        assert "SECURITY.md" in text

    def test_no_files_message(self, tmp_path: Path) -> None:
        """Should show message when no files found."""
        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
        ):
            result = _handle_load_knowledge({})
            text = result[0].text
            assert "No knowledge files found" in text


class TestFullReviewIncludesCustomKnowledge:
    """Test that full_review includes custom knowledge."""

    def test_includes_project_knowledge(self, tmp_path: Path) -> None:
        """Full review should include project knowledge files."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        project_knowledge = tmp_path / ".crucible" / "knowledge"
        project_knowledge.mkdir(parents=True)
        (project_knowledge / "PROJECT_PATTERNS.md").write_text("# Project Patterns\n\nOur patterns here.\n")

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", project_knowledge),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
            patch("crucible.server.get_custom_knowledge_files", return_value={"PROJECT_PATTERNS.md"}),
            patch("crucible.review.core.delegate_semgrep", return_value=ok([])),
            patch("crucible.review.core.delegate_ruff", return_value=ok([])),
            patch("crucible.review.core.delegate_bandit", return_value=ok([])),
        ):
            result = _handle_full_review({"path": str(test_file)})
            text = result[0].text
            assert "PROJECT_PATTERNS.md" in text


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
