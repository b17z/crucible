"""Tests for crucible.skills_core public API.

Hermetic — uses tmp_path for all on-disk state. No reliance on the
bundled skills/ tree.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from crucible.skills_core import (
    CascadeSpec,
    RawSkill,
    ResolvedPath,
    list_available,
    parse_frontmatter,
    read_skill,
    resolve,
)


# --- parse_frontmatter ---------------------------------------------------


class TestParseFrontmatter:
    """SKILL.md frontmatter parsing — open schema, returns dict + body."""

    def test_minimal_frontmatter(self) -> None:
        content = "---\nname: foo\n---\n\n# Body"
        result = parse_frontmatter(content)
        assert result.is_ok
        fields, body = result.value
        assert fields == {"name": "foo"}
        assert body.startswith("\n# Body")

    def test_typed_values_preserved(self) -> None:
        """version stays str, triggers stays list, booleans stay bool."""
        content = (
            "---\n"
            'name: x\n'
            'version: "2.0"\n'
            "triggers: [security, auth]\n"
            "always_run: true\n"
            "---\n"
            "body"
        )
        result = parse_frontmatter(content)
        assert result.is_ok
        fields, _ = result.value
        assert fields["name"] == "x"
        assert fields["version"] == "2.0"
        assert fields["triggers"] == ["security", "auth"]
        assert fields["always_run"] is True

    def test_missing_opening_delimiter(self) -> None:
        content = "no frontmatter here"
        result = parse_frontmatter(content)
        assert result.is_err
        assert "opening frontmatter" in result.error

    def test_missing_closing_delimiter(self) -> None:
        content = "---\nname: foo\nbody but no closing\n"
        result = parse_frontmatter(content)
        assert result.is_err
        assert "closing frontmatter" in result.error

    def test_frontmatter_at_eof_no_trailing_newline(self) -> None:
        """Tolerate a SKILL.md that ends with `---` and no body."""
        content = "---\nname: x\n---"
        result = parse_frontmatter(content)
        assert result.is_ok
        fields, body = result.value
        assert fields == {"name": "x"}
        assert body == ""

    def test_invalid_yaml(self) -> None:
        content = "---\nname: [unclosed\n---\nbody"
        result = parse_frontmatter(content)
        assert result.is_err
        assert "invalid YAML" in result.error

    def test_non_mapping_yaml_rejected(self) -> None:
        """A top-level list isn't a valid frontmatter shape."""
        content = "---\n- one\n- two\n---\nbody"
        result = parse_frontmatter(content)
        assert result.is_err

    def test_open_schema_keeps_unknown_fields(self) -> None:
        """RawSkill.frontmatter is a dict — no Crucible-specific filtering."""
        # Use a quoted value to avoid YAML 1.1's `yes` → bool coercion.
        content = '---\nname: x\ncustom_sage_field: "tag-string"\n---\nbody'
        result = parse_frontmatter(content)
        assert result.is_ok
        fields, _ = result.value
        assert fields["custom_sage_field"] == "tag-string"


# --- read_skill ----------------------------------------------------------


def _make_skill_dir(tmp_path: Path, name: str, frontmatter: str, body: str = "body", subfolders: tuple[str, ...] = ()) -> Path:
    """Build a tiny skill folder for testing."""
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"---\n{frontmatter}\n---\n{body}")
    for sub in subfolders:
        (skill_dir / sub).mkdir()
    return skill_dir


class TestReadSkill:
    def test_reads_skill_md_and_enumerates_siblings(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(
            tmp_path, "demo", "name: demo", "body content",
            subfolders=("knowledge", "assertions"),
        )
        result = read_skill(skill_dir, source="bundled")
        assert result.is_ok
        skill = result.value
        assert isinstance(skill, RawSkill)
        assert skill.path == skill_dir
        assert skill.source == "bundled"
        assert skill.used_fallback is False
        assert skill.frontmatter == {"name": "demo"}
        assert "body content" in skill.body
        assert "knowledge" in skill.sibling_paths
        assert "assertions" in skill.sibling_paths
        assert "checks" not in skill.sibling_paths  # not created in fixture

    def test_surfaces_triggers_yaml(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path, "demo", "name: demo")
        (skill_dir / "triggers.yaml").write_text("rules: []")
        result = read_skill(skill_dir)
        assert result.is_ok
        assert "triggers.yaml" in result.value.sibling_paths

    def test_missing_folder(self, tmp_path: Path) -> None:
        result = read_skill(tmp_path / "does-not-exist")
        assert result.is_err
        assert "does not exist" in result.error

    def test_missing_skill_md(self, tmp_path: Path) -> None:
        (tmp_path / "demo").mkdir()
        result = read_skill(tmp_path / "demo")
        assert result.is_err
        assert "missing SKILL.md" in result.error

    def test_path_is_file_not_dir(self, tmp_path: Path) -> None:
        f = tmp_path / "not-a-dir"
        f.write_text("hi")
        result = read_skill(f)
        assert result.is_err
        assert "not a directory" in result.error


# --- resolve and list_available ------------------------------------------


@pytest.fixture
def folder_spec(tmp_path: Path) -> CascadeSpec:
    """A folder-mode spec with project/user/bundled tiers in tmp_path."""
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


@pytest.fixture
def file_spec(tmp_path: Path) -> CascadeSpec:
    """A file-mode spec for .yaml content with project/user/bundled tiers."""
    project = tmp_path / "project_yaml"
    user = tmp_path / "user_yaml"
    bundled = tmp_path / "bundled_yaml"
    for d in (project, user, bundled):
        d.mkdir()
    return CascadeSpec(
        project_dir=project,
        user_dir=user,
        bundled_dir=bundled,
        is_folder=False,
        suffix=".yaml",
    )


class TestResolveFolder:
    def test_project_wins(self, folder_spec: CascadeSpec) -> None:
        (folder_spec.project_dir / "foo").mkdir()
        (folder_spec.user_dir / "foo").mkdir()
        (folder_spec.bundled_dir / "foo").mkdir()
        result = resolve(folder_spec, "foo")
        assert result.is_ok
        assert result.value.source == "project"
        assert result.value.used_fallback is False

    def test_user_wins_over_bundled(self, folder_spec: CascadeSpec) -> None:
        (folder_spec.user_dir / "foo").mkdir()
        (folder_spec.bundled_dir / "foo").mkdir()
        result = resolve(folder_spec, "foo")
        assert result.is_ok
        assert result.value.source == "user"

    def test_bundled_fallback(self, folder_spec: CascadeSpec) -> None:
        (folder_spec.bundled_dir / "foo").mkdir()
        result = resolve(folder_spec, "foo")
        assert result.is_ok
        assert result.value.source == "bundled"

    def test_not_found(self, folder_spec: CascadeSpec) -> None:
        result = resolve(folder_spec, "nothing")
        assert result.is_err
        assert "not found in cascade" in result.error


class TestResolveFile:
    def test_suffix_appended(self, file_spec: CascadeSpec) -> None:
        """Caller passes 'foo'; resolver looks for 'foo.yaml'."""
        (file_spec.bundled_dir / "foo.yaml").write_text("x: 1")
        result = resolve(file_spec, "foo")
        assert result.is_ok
        assert result.value.path.name == "foo.yaml"

    def test_suffix_already_present(self, file_spec: CascadeSpec) -> None:
        """Caller passes 'foo.yaml'; resolver doesn't double-append."""
        (file_spec.bundled_dir / "foo.yaml").write_text("x: 1")
        result = resolve(file_spec, "foo.yaml")
        assert result.is_ok
        assert result.value.path.name == "foo.yaml"


class TestDualPathFallback:
    """v1→v2 fallback semantics for shape-changing paths."""

    def test_v2_path_preferred(self, tmp_path: Path) -> None:
        """When v2 path exists, fallback is NOT consulted."""
        v2 = tmp_path / "v2"
        v1 = tmp_path / "v1"
        user = tmp_path / "user"
        bundled = tmp_path / "bundled"
        for d in (v2, v1, user, bundled):
            d.mkdir()
        (v2 / "foo").mkdir()
        (v1 / "foo").mkdir()

        spec = CascadeSpec(
            project_dir=v2,
            user_dir=user,
            bundled_dir=bundled,
            is_folder=True,
            fallback_project_dir=v1,
            fallback_label="v1 layout",
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = resolve(spec, "foo")
        assert result.is_ok
        assert result.value.used_fallback is False
        assert result.value.path.is_relative_to(v2)
        # No deprecation warning because v2 was hit first.
        assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]

    def test_v1_fallback_used_when_v2_missing(self, tmp_path: Path) -> None:
        v2 = tmp_path / "v2"
        v1 = tmp_path / "v1"
        user = tmp_path / "user"
        bundled = tmp_path / "bundled"
        for d in (v2, v1, user, bundled):
            d.mkdir()
        (v1 / "foo").mkdir()  # only v1 has it

        spec = CascadeSpec(
            project_dir=v2,
            user_dir=user,
            bundled_dir=bundled,
            is_folder=True,
            fallback_project_dir=v1,
            fallback_label="v1 layout",
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = resolve(spec, "foo")
        assert result.is_ok
        assert result.value.used_fallback is True
        assert result.value.path.is_relative_to(v1)
        # Deprecation warning fires, cites the label.
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(deprecations) == 1
        assert "v1 layout" in str(deprecations[0].message)

    def test_no_fallback_means_no_v1_lookup(self, folder_spec: CascadeSpec, tmp_path: Path) -> None:
        """fallback_project_dir=None means we never check a v1 path."""
        v1 = tmp_path / "v1_unused"
        v1.mkdir()
        (v1 / "foo").mkdir()  # the v1 dir HAS the content
        # but our spec doesn't know about it
        result = resolve(folder_spec, "foo")
        assert result.is_err


class TestListAvailable:
    def test_union_across_tiers(self, folder_spec: CascadeSpec) -> None:
        (folder_spec.project_dir / "alpha").mkdir()
        (folder_spec.user_dir / "beta").mkdir()
        (folder_spec.bundled_dir / "gamma").mkdir()
        assert list_available(folder_spec) == {"alpha", "beta", "gamma"}

    def test_skips_dotfiles_and_pycache(self, folder_spec: CascadeSpec) -> None:
        (folder_spec.bundled_dir / "real-skill").mkdir()
        (folder_spec.bundled_dir / "__pycache__").mkdir()
        (folder_spec.bundled_dir / ".hidden").mkdir()
        names = list_available(folder_spec)
        assert names == {"real-skill"}

    def test_file_mode_strips_suffix(self, file_spec: CascadeSpec) -> None:
        (file_spec.bundled_dir / "rules.yaml").write_text("x: 1")
        (file_spec.bundled_dir / "other.yaml").write_text("y: 2")
        # Non-matching suffix is ignored.
        (file_spec.bundled_dir / "readme.md").write_text("nope")
        assert list_available(file_spec) == {"rules", "other"}
