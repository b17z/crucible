"""Tests for crucible.core.disclosure (progressive disclosure).

Hermetic — builds a fake skills tree in tmp_path and points a CascadeSpec
at it, so the tests don't depend on the bundled skills.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crucible.core.disclosure import (
    ActivatedSkill,
    activate_skill,
    discover_skill,
    discover_skills,
    discovery_digest,
    load_knowledge,
)
from crucible.skills_core import CascadeSpec


def _write_skill(
    root: Path,
    name: str,
    description: str,
    body: str = "# Body\n\nSome content.",
    knowledge: dict[str, str] | None = None,
    assertions: dict[str, str] | None = None,
    frontmatter_name: str | None = None,
) -> Path:
    """Create a skill folder under root. name may contain a namespace
    prefix like 'meta/foo' (the parent dir is created automatically)."""
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    fm_name = frontmatter_name if frontmatter_name is not None else name
    skill_dir.joinpath("SKILL.md").write_text(
        f"---\nname: {fm_name}\ndescription: {description}\nversion: \"2.0\"\n---\n{body}"
    )
    if knowledge:
        kdir = skill_dir / "knowledge"
        kdir.mkdir()
        for fn, content in knowledge.items():
            kdir.joinpath(fn).write_text(content)
    if assertions:
        adir = skill_dir / "assertions"
        adir.mkdir()
        for fn, content in assertions.items():
            adir.joinpath(fn).write_text(content)
    return skill_dir


@pytest.fixture
def spec(tmp_path: Path) -> CascadeSpec:
    """A folder spec with project/user/bundled dirs in tmp_path, bundled
    pre-populated with a few skills."""
    project = tmp_path / "project"
    user = tmp_path / "user"
    bundled = tmp_path / "bundled"
    for d in (project, user, bundled):
        d.mkdir()
    return CascadeSpec(
        project_dir=project,
        user_dir=user,
        bundled_dir=bundled,
        is_folder=True,
        suffix=None,
    )


# --- Tier 1: discover_skills ---------------------------------------------


class TestDiscover:
    def test_discovers_bundled_skills(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "alpha", "First skill")
        _write_skill(spec.bundled_dir, "beta", "Second skill")
        summaries = discover_skills(spec)
        names = [s.name for s in summaries]
        assert names == ["alpha", "beta"]  # sorted
        assert summaries[0].description == "First skill"
        assert summaries[0].source == "bundled"

    def test_tier1_does_not_read_body(self, spec: CascadeSpec, monkeypatch) -> None:
        """Tier 1 must read only frontmatter. We can't easily assert "body
        not read" at the byte level, but we CAN assert the summary carries
        no body field — there is intentionally no body on SkillSummary."""
        _write_skill(spec.bundled_dir, "alpha", "x", body="# Huge\n" + "z" * 10000)
        summaries = discover_skills(spec)
        assert not hasattr(summaries[0], "body")

    def test_namespaced_skills_keep_prefix(self, spec: CascadeSpec) -> None:
        """REGRESSION: nested skills under meta/ and pre-write/ must be
        named with their namespace prefix (the resolution identity), NOT
        the bare frontmatter name. Otherwise discover -> resolve breaks."""
        # frontmatter name is bare 'foo', but the skill lives at meta/foo
        _write_skill(spec.bundled_dir, "meta/foo", "A meta skill", frontmatter_name="foo")
        _write_skill(spec.bundled_dir, "pre-write/prd", "PRD template", frontmatter_name="prd")
        summaries = discover_skills(spec)
        names = [s.name for s in summaries]
        assert "meta/foo" in names
        assert "pre-write/prd" in names
        assert "foo" not in names  # bare name must NOT appear
        # display_name surfaces the frontmatter label
        meta_foo = next(s for s in summaries if s.name == "meta/foo")
        assert meta_foo.display_name == "foo"

    def test_project_shadows_bundled(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "alpha", "bundled version")
        _write_skill(spec.project_dir, "alpha", "project override")
        summaries = discover_skills(spec)
        assert len(summaries) == 1
        assert summaries[0].source == "project"
        assert summaries[0].description == "project override"

    def test_skips_broken_skill(self, spec: CascadeSpec) -> None:
        """A skill with unparseable frontmatter is skipped, not fatal."""
        _write_skill(spec.bundled_dir, "good", "fine")
        broken = spec.bundled_dir / "broken"
        broken.mkdir()
        broken.joinpath("SKILL.md").write_text("no frontmatter here at all")
        summaries = discover_skills(spec)
        names = [s.name for s in summaries]
        assert "good" in names
        assert "broken" not in names

    def test_skips_dotdirs_and_pycache(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "real", "ok")
        (spec.bundled_dir / "__pycache__").mkdir()
        (spec.bundled_dir / ".hidden").mkdir()
        summaries = discover_skills(spec)
        assert [s.name for s in summaries] == ["real"]

    def test_empty_cascade(self, spec: CascadeSpec) -> None:
        assert discover_skills(spec) == []


class TestDiscoverSingle:
    def test_discover_named(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "alpha", "desc")
        result = discover_skill("alpha", spec)
        assert result.is_ok
        assert result.value.name == "alpha"

    def test_discover_namespaced(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "meta/foo", "desc", frontmatter_name="foo")
        result = discover_skill("meta/foo", spec)
        assert result.is_ok
        assert result.value.name == "meta/foo"

    def test_discover_missing(self, spec: CascadeSpec) -> None:
        result = discover_skill("nope", spec)
        assert result.is_err


# --- Tier 2: activate_skill ----------------------------------------------


class TestActivate:
    def test_loads_body(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "alpha", "desc", body="# Alpha\n\nThe body.")
        summary = discover_skill("alpha", spec).value
        result = activate_skill(summary)
        assert result.is_ok
        act = result.value
        assert isinstance(act, ActivatedSkill)
        assert "The body." in act.body

    def test_enumerates_knowledge_and_assertions(self, spec: CascadeSpec) -> None:
        _write_skill(
            spec.bundled_dir,
            "alpha",
            "desc",
            knowledge={"one.md": "k1", "two.md": "k2"},
            assertions={"rules.yaml": "a: 1"},
        )
        summary = discover_skill("alpha", spec).value
        act = activate_skill(summary).value
        assert act.knowledge_files == ("one.md", "two.md")
        assert act.assertion_files == ("rules.yaml",)

    def test_no_subfolders(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "alpha", "desc")
        act = activate_skill(discover_skill("alpha", spec).value).value
        assert act.knowledge_files == ()
        assert act.assertion_files == ()


# --- Tier 3: load_knowledge ----------------------------------------------


class TestLoadKnowledge:
    def test_loads_named_file(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "alpha", "desc", knowledge={"topic.md": "the knowledge body"})
        act = activate_skill(discover_skill("alpha", spec).value).value
        result = load_knowledge(act, "topic.md")
        assert result.is_ok
        assert result.value == "the knowledge body"

    def test_suffix_optional(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "alpha", "desc", knowledge={"topic.md": "body"})
        act = activate_skill(discover_skill("alpha", spec).value).value
        result = load_knowledge(act, "topic")  # no .md
        assert result.is_ok
        assert result.value == "body"

    def test_missing_file_lists_available(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "alpha", "desc", knowledge={"real.md": "x"})
        act = activate_skill(discover_skill("alpha", spec).value).value
        result = load_knowledge(act, "ghost.md")
        assert result.is_err
        assert "real.md" in result.error  # error names what IS available


# --- discovery_digest ----------------------------------------------------


class TestDigest:
    def test_digest_format(self, spec: CascadeSpec) -> None:
        _write_skill(spec.bundled_dir, "alpha", "First")
        _write_skill(spec.bundled_dir, "beta", "Second")
        digest = discovery_digest(discover_skills(spec))
        assert "alpha — First" in digest
        assert "beta — Second" in digest

    def test_empty_digest(self) -> None:
        assert "No skills" in discovery_digest([])


# --- progressive cost shape ----------------------------------------------


class TestProgressiveCost:
    def test_tier1_cheaper_than_full(self, spec: CascadeSpec) -> None:
        """The point of the whole module: discovering N skills via Tier 1
        costs far less than loading all their bodies + knowledge."""
        big_body = "# Title\n\n" + ("lorem ipsum dolor sit amet. " * 500)
        big_knowledge = "knowledge content. " * 1000
        for i in range(10):
            _write_skill(
                spec.bundled_dir,
                f"skill{i}",
                f"description number {i}",
                body=big_body,
                knowledge={"deep.md": big_knowledge},
            )
        summaries = discover_skills(spec)
        tier1_cost = len(discovery_digest(summaries))

        # Full cost = every body + every knowledge file
        full_cost = 0
        for s in summaries:
            act = activate_skill(s).value
            full_cost += len(act.body)
            for kf in act.knowledge_files:
                full_cost += len(load_knowledge(act, kf).value)

        # Tier 1 should be a small fraction of the full load.
        assert tier1_cost < full_cost * 0.1, (
            f"Tier 1 ({tier1_cost}) not <10% of full ({full_cost})"
        )

    def test_bundled_skill_count(self) -> None:
        """Pin the bundled skill count. Update deliberately when skills are
        added or removed — this is a tripwire, not a ceiling."""
        summaries = discover_skills()  # default SKILLS_SPEC = bundled tree
        assert len(summaries) == 41, (
            f"Expected 41 bundled skills, got {len(summaries)}: "
            f"{sorted(s.name for s in summaries)}"
        )

    def test_real_bundled_tree_beats_30pct_target(self) -> None:
        """Phase 3 success criterion: >30% context reduction via Tier 1,
        measured against the ACTUAL bundled skill tree (no tmp_path).

        Measured ~96.8% at 27 skills (3.8KB Tier 1 vs ~119KB full). The
        assertion floor is the handoff's 30% target; the headroom is huge
        because skill bodies + knowledge dwarf their one-line descriptions.
        """
        summaries = discover_skills()  # default SKILLS_SPEC = bundled tree
        assert len(summaries) >= 20, "expected the full bundled persona set"

        tier1_cost = len(discovery_digest(summaries))
        full_cost = 0
        for s in summaries:
            act = activate_skill(s)
            if act.is_err:
                continue
            full_cost += len(act.value.body)
            for kf in act.value.knowledge_files:
                r = load_knowledge(act.value, kf)
                if r.is_ok:
                    full_cost += len(r.value)

        assert full_cost > 0
        reduction = 1 - (tier1_cost / full_cost)
        assert reduction > 0.30, (
            f"Tier 1 reduction {reduction:.1%} below the 30% target "
            f"(Tier 1 {tier1_cost} vs full {full_cost})"
        )
