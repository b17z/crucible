"""Content assertions on the bundled meta/delivery-loop SKILL.md.

Pins the binding details from docs/specs/2026-08-10-delivery-loop.md §1:
workbench cascade order, never-commit rule, git-free handoff language,
prewrite-review gate ordering, and the four workbench artifact names.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILL_PATH = (
    Path(__file__).parent.parent
    / "src"
    / "crucible"
    / "skills"
    / "meta"
    / "delivery-loop"
    / "SKILL.md"
)


def _text() -> str:
    return SKILL_PATH.read_text()


def _step_six_section(text: str) -> str:
    """Extract the step-6/handoff section: between the '### 6.' heading and
    the next '### ' or '## ' heading."""
    match = re.search(
        r"### 6\..*?(?=\n#{2,3} )", text, re.DOTALL
    )
    assert match, "could not locate step 6 section in SKILL.md"
    return match.group(0)


class TestSkillExists:
    def test_skill_md_exists(self) -> None:
        assert SKILL_PATH.exists()

    def test_triggers_yaml_exists(self) -> None:
        assert (SKILL_PATH.parent / "triggers.yaml").exists()


class TestWorkbenchCascade:
    def test_cascade_order(self) -> None:
        text = _text()
        workbench_idx = text.index("workbench:")
        vault_idx = text.index("vault:")
        fallback_idx = text.index(".crucible/workbench/")
        assert workbench_idx < vault_idx < fallback_idx, (
            "workbench cascade must read workbench: before vault: before "
            ".crucible/workbench/"
        )

    def test_never_commit_near_workbench(self) -> None:
        text = _text()
        workbench_heading = text.index("## The workbench")
        section = text[workbench_heading : workbench_heading + 2000]
        assert "never commit" in section.lower()

    def test_gitignore_verification_before_write(self) -> None:
        text = _text()
        assert "gitignored" in text.lower() or "gitignore" in text.lower()
        assert "check-ignore" in text or ".gitignore" in text


class TestArtifactNames:
    def test_all_four_artifact_names_present(self) -> None:
        text = _text()
        for name in ("spec.md", "plan.md", "ledger.md", "decisions.md"):
            assert name in text, f"missing artifact name: {name}"


class TestStepOrdering:
    def test_prewrite_review_before_execution_step(self) -> None:
        text = _text()
        prewrite_idx = text.index("prewrite review")
        execute_idx = text.index("### 5. Execute with gates")
        assert prewrite_idx < execute_idx, (
            "prewrite review gate must appear before the execution step"
        )


class TestHandoffIsGitAgnostic:
    def test_step_six_has_no_git_commands(self) -> None:
        section = _step_six_section(_text())
        for forbidden in ("git merge", "git push", "git rebase", "pull request"):
            assert forbidden not in section.lower(), (
                f"step 6/handoff section must not prescribe {forbidden!r}"
            )


class TestBoundary:
    def test_points_beginners_to_engineering_loop(self) -> None:
        text = _text()
        assert "meta/engineering-loop" in text

    def test_do_not_boundary_present(self) -> None:
        text = _text()
        assert "Do NOT" in text or "## Do NOT" in text
