"""Tests for crucible.core.trigger_router.

Hermetic — builds skills with triggers.yaml in tmp_path and points a
CascadeSpec at them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crucible.core.trigger_router import (
    Event,
    match_event,
    match_prompt,
)
from crucible.skills_core import CascadeSpec


def _write_skill_with_triggers(
    root: Path, name: str, triggers_yaml: str, description: str = "desc"
) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\nbody"
    )
    skill_dir.joinpath("triggers.yaml").write_text(triggers_yaml)
    return skill_dir


@pytest.fixture
def spec(tmp_path: Path) -> CascadeSpec:
    bundled = tmp_path / "bundled"
    project = tmp_path / "project"
    user = tmp_path / "user"
    for d in (bundled, project, user):
        d.mkdir()
    return CascadeSpec(
        project_dir=project, user_dir=user, bundled_dir=bundled,
        is_folder=True, suffix=None,
    )


class TestPromptMatch:
    def test_matches(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(
            spec.bundled_dir, "sec",
            "rules:\n  - type: prompt_match\n    pattern: '\\b(security|auth)\\b'\n",
        )
        matches = match_prompt("review the auth flow", project_root=tmp_path, spec=spec)
        assert [m.skill_name for m in matches] == ["sec"]

    def test_case_insensitive(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(
            spec.bundled_dir, "sec",
            "rules:\n  - type: prompt_match\n    pattern: 'security'\n",
        )
        matches = match_prompt("SECURITY concern", project_root=tmp_path, spec=spec)
        assert len(matches) == 1

    def test_no_match(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(
            spec.bundled_dir, "sec",
            "rules:\n  - type: prompt_match\n    pattern: 'security'\n",
        )
        matches = match_prompt("just refactoring", project_root=tmp_path, spec=spec)
        assert matches == []


class TestFileGlob:
    def test_full_path_and_basename(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(
            spec.bundled_dir, "sec",
            "rules:\n  - type: file_glob\n    pattern: '**/package.json'\n",
        )
        # nested path
        m1 = match_event(Event(file_paths=("a/b/package.json",)), project_root=tmp_path, spec=spec)
        assert len(m1) == 1
        # bare basename pattern
        _write_skill_with_triggers(
            spec.bundled_dir, "mcp",
            "rules:\n  - type: file_glob\n    pattern: '.mcp.json'\n",
        )
        m2 = match_event(Event(file_paths=(".mcp.json",)), project_root=tmp_path, spec=spec)
        names = [m.skill_name for m in m2]
        assert "mcp" in names

    def test_no_match(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(
            spec.bundled_dir, "sec",
            "rules:\n  - type: file_glob\n    pattern: '**/Cargo.toml'\n",
        )
        m = match_event(Event(file_paths=("src/main.py",)), project_root=tmp_path, spec=spec)
        assert m == []


class TestBashMatch:
    def test_matches(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(
            spec.bundled_dir, "sec",
            "rules:\n  - type: bash_match\n    pattern: '\\bnpm install\\b'\n",
        )
        m = match_event(Event(bash_command="npm install lodash"), project_root=tmp_path, spec=spec)
        assert len(m) == 1


class TestPreconditions:
    PUBLISHER_TRIGGERS = (
        "preconditions:\n"
        "  - type: project_flag\n"
        "    flag: 'tool.crucible.publishable'\n"
        "rules:\n"
        "  - type: prompt_match\n"
        "    pattern: '\\b(publish|release)\\b'\n"
    )

    def test_dormant_without_flag(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(spec.bundled_dir, "pub", self.PUBLISHER_TRIGGERS)
        # tmp_path has no pyproject/package.json with the flag
        m = match_prompt("time to publish a release", project_root=tmp_path, spec=spec)
        assert m == []

    def test_active_with_pyproject_flag(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(spec.bundled_dir, "pub", self.PUBLISHER_TRIGGERS)
        (tmp_path / "pyproject.toml").write_text("[tool.crucible]\npublishable = true\n")
        m = match_prompt("time to publish a release", project_root=tmp_path, spec=spec)
        assert [x.skill_name for x in m] == ["pub"]

    def test_active_with_package_json_flag(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(spec.bundled_dir, "pub", self.PUBLISHER_TRIGGERS)
        (tmp_path / "package.json").write_text('{"crucible": {"publishable": true}}')
        m = match_prompt("publish the package", project_root=tmp_path, spec=spec)
        assert [x.skill_name for x in m] == ["pub"]

    def test_flag_false_stays_dormant(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(spec.bundled_dir, "pub", self.PUBLISHER_TRIGGERS)
        (tmp_path / "pyproject.toml").write_text("[tool.crucible]\npublishable = false\n")
        m = match_prompt("publish a release", project_root=tmp_path, spec=spec)
        assert m == []

    def test_unknown_precondition_stays_dormant(self, spec: CascadeSpec, tmp_path: Path) -> None:
        """A skill declaring a precondition type we don't understand should
        NOT activate — fail safe, not fail open."""
        triggers = (
            "preconditions:\n"
            "  - type: some_future_gate\n"
            "rules:\n"
            "  - type: prompt_match\n"
            "    pattern: 'anything'\n"
        )
        _write_skill_with_triggers(spec.bundled_dir, "future", triggers)
        m = match_prompt("anything goes", project_root=tmp_path, spec=spec)
        assert m == []


class TestUnionAndRobustness:
    def test_multiple_skills_union(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(
            spec.bundled_dir, "a",
            "rules:\n  - type: prompt_match\n    pattern: 'deploy'\n",
        )
        _write_skill_with_triggers(
            spec.bundled_dir, "b",
            "rules:\n  - type: prompt_match\n    pattern: 'deploy'\n",
        )
        m = match_prompt("deploy to prod", project_root=tmp_path, spec=spec)
        assert sorted(x.skill_name for x in m) == ["a", "b"]

    def test_skill_without_triggers_never_matches(self, spec: CascadeSpec, tmp_path: Path) -> None:
        # skill with SKILL.md but no triggers.yaml
        d = spec.bundled_dir / "plain"
        d.mkdir()
        d.joinpath("SKILL.md").write_text("---\nname: plain\ndescription: x\n---\nbody")
        m = match_prompt("plain anything", project_root=tmp_path, spec=spec)
        assert m == []

    def test_malformed_triggers_skipped(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(spec.bundled_dir, "good",
            "rules:\n  - type: prompt_match\n    pattern: 'go'\n")
        bad = spec.bundled_dir / "bad"
        bad.mkdir()
        bad.joinpath("SKILL.md").write_text("---\nname: bad\ndescription: x\n---\nbody")
        bad.joinpath("triggers.yaml").write_text("rules: [ this is : not valid yaml :::")
        m = match_prompt("go now", project_root=tmp_path, spec=spec)
        names = [x.skill_name for x in m]
        assert "good" in names
        assert "bad" not in names

    def test_namespaced_skill_name(self, spec: CascadeSpec, tmp_path: Path) -> None:
        _write_skill_with_triggers(
            spec.bundled_dir, "meta/checker",
            "rules:\n  - type: prompt_match\n    pattern: 'check'\n",
        )
        m = match_prompt("check this", project_root=tmp_path, spec=spec)
        assert [x.skill_name for x in m] == ["meta/checker"]


class TestBundledEngineeringLoopSkills:
    """Real bundled tree (no spec override) — one positive trigger match
    per adapted skill from THIRD-PARTY-NOTICES.md, confirming each
    triggers.yaml actually routes on a realistic prompt."""

    def test_brainstorming_matches(self) -> None:
        m = match_prompt("let's build a new feature for exporting reports")
        assert "meta/brainstorming" in [x.skill_name for x in m]

    def test_systematic_debugging_matches(self) -> None:
        m = match_prompt("this test is failing and I don't know why")
        assert "meta/systematic-debugging" in [x.skill_name for x in m]

    def test_tdd_matches(self) -> None:
        m = match_prompt("let's do this test-first, red-green-refactor")
        assert "meta/tdd" in [x.skill_name for x in m]

    def test_wait_what_matches(self) -> None:
        m = match_prompt("wait, what? I don't understand that explanation")
        assert "meta/wait-what" in [x.skill_name for x in m]

    def test_teach_me_matches(self) -> None:
        m = match_prompt("teach me how databases work")
        assert "meta/teach-me" in [x.skill_name for x in m]

    def test_engineering_loop_matches(self) -> None:
        m = match_prompt("I'm new to coding, help me build my first app")
        assert "meta/engineering-loop" in [x.skill_name for x in m]

    def test_delivery_loop_matches(self) -> None:
        m = match_prompt("let's run the delivery loop on this")
        assert "meta/delivery-loop" in [x.skill_name for x in m]

    def test_delivery_loop_matches_hyphenated_work_loop(self) -> None:
        m = match_prompt("run the work-loop on this")
        assert "meta/delivery-loop" in [x.skill_name for x in m]

    def test_delivery_loop_does_not_match_debugging_prompt(self) -> None:
        """A plain debugging prompt mentioning 'production' must not fire
        delivery-loop — the trigger phrases are anchored ('production
        loop') so bare 'production' alone doesn't match."""
        m = match_prompt("help me debug this failing request in production")
        assert "meta/delivery-loop" not in [x.skill_name for x in m]

    def test_build_along_course_matches(self) -> None:
        m = match_prompt("let's add this to the course")
        assert "meta/build-along-course" in [x.skill_name for x in m]

    def test_frontend_taste_matches_landing_page(self) -> None:
        m = match_prompt("build a landing page for the club")
        assert "meta/frontend-taste" in [x.skill_name for x in m]

    def test_frontend_taste_does_not_match_bare_design(self) -> None:
        """Lesson of #18: bare 'design' must never fire frontend-taste —
        'design the database schema' is not UI work."""
        m = match_prompt("design the database schema")
        assert "meta/frontend-taste" not in [x.skill_name for x in m]

    def test_frontend_taste_matches_build_a_dashboard(self) -> None:
        """Construction-verb-anchored form: building a dashboard is UI
        work and must fire frontend-taste."""
        m = match_prompt("build a dashboard for the metrics")
        assert "meta/frontend-taste" in [x.skill_name for x in m]

    def test_frontend_taste_does_not_match_dashboard_perf_complaint(self) -> None:
        """A performance complaint about an existing dashboard is not
        UI-building intent and must not fire frontend-taste."""
        m = match_prompt("the dashboard UI is slow")
        assert "meta/frontend-taste" not in [x.skill_name for x in m]
