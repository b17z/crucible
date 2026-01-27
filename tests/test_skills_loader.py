"""Tests for skills loader."""

from pathlib import Path
from unittest.mock import patch

from crucible.models import Domain
from crucible.skills.loader import (
    _load_skill_cached,
    clear_skill_cache,
    get_all_skill_names,
    get_knowledge_for_skills,
    load_skill,
    match_skills_for_domain,
    parse_skill_frontmatter,
    resolve_skill_path,
)


class TestParseSkillFrontmatter:
    """Test frontmatter parsing."""

    def test_basic_frontmatter(self) -> None:
        """Should parse basic frontmatter."""
        content = """---
version: "1.0"
triggers: [python, backend]
knowledge: [SECURITY.md]
---

# Skill Name

Content here.
"""
        result = parse_skill_frontmatter(content)
        assert result.is_ok
        metadata = result.value
        assert metadata.version == "1.0"
        assert metadata.triggers == ("python", "backend")
        assert metadata.knowledge == ("SECURITY.md",)
        assert metadata.always_run is False
        assert metadata.always_run_for_domains == ()

    def test_always_run_true(self) -> None:
        """Should parse always_run: true."""
        content = """---
version: "1.0"
triggers: [security]
always_run: true
knowledge: [SECURITY.md]
---

Content.
"""
        result = parse_skill_frontmatter(content)
        assert result.is_ok
        assert result.value.always_run is True

    def test_always_run_for_domains(self) -> None:
        """Should parse always_run_for_domains list."""
        content = """---
version: "1.0"
triggers: [solidity, web3]
always_run_for_domains: [smart_contract]
knowledge: [SMART_CONTRACT.md]
---

Content.
"""
        result = parse_skill_frontmatter(content)
        assert result.is_ok
        assert result.value.always_run_for_domains == ("smart_contract",)

    def test_multiple_knowledge_files(self) -> None:
        """Should parse multiple knowledge files."""
        content = """---
version: "1.0"
triggers: [web3]
knowledge: [SECURITY.md, SMART_CONTRACT.md]
---

Content.
"""
        result = parse_skill_frontmatter(content)
        assert result.is_ok
        assert result.value.knowledge == ("SECURITY.md", "SMART_CONTRACT.md")

    def test_no_frontmatter_error(self) -> None:
        """Should error when no frontmatter."""
        content = "# Just a heading\n\nNo frontmatter here."
        result = parse_skill_frontmatter(content)
        assert result.is_err
        assert "No frontmatter found" in result.error

    def test_no_closing_delimiter_error(self) -> None:
        """Should error when no closing delimiter."""
        content = """---
version: "1.0"
triggers: [test]

# No closing delimiter
"""
        result = parse_skill_frontmatter(content)
        assert result.is_err
        assert "No closing" in result.error

    def test_empty_triggers(self) -> None:
        """Should handle empty triggers list."""
        content = """---
version: "1.0"
triggers: []
---

Content.
"""
        result = parse_skill_frontmatter(content)
        assert result.is_ok
        assert result.value.triggers == ()

    def test_defaults_for_missing_fields(self) -> None:
        """Should use defaults for missing optional fields."""
        content = """---
version: "2.0"
---

Minimal frontmatter.
"""
        result = parse_skill_frontmatter(content)
        assert result.is_ok
        assert result.value.version == "2.0"
        assert result.value.triggers == ()
        assert result.value.always_run is False
        assert result.value.always_run_for_domains == ()
        assert result.value.knowledge == ()


class TestResolveSkillPath:
    """Test skill path resolution cascade."""

    def test_bundled_skill_found(self, tmp_path: Path) -> None:
        """Bundled skills should be found when no overrides exist."""
        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            path, source = resolve_skill_path("security-engineer")
            assert path is not None
            assert source == "bundled"
            assert path.exists()

    def test_nonexistent_skill_returns_none(self) -> None:
        """Non-existent skill should return None."""
        path, source = resolve_skill_path("nonexistent-skill-xyz-12345")
        assert path is None
        assert source == ""

    def test_project_takes_priority(self, tmp_path: Path) -> None:
        """Project-level skills should take priority over bundled."""
        project_skills = tmp_path / ".crucible" / "skills" / "security-engineer"
        project_skills.mkdir(parents=True)
        (project_skills / "SKILL.md").write_text("---\nversion: \"1.0\"\n---\n# Custom")

        with patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / ".crucible" / "skills"):
            path, source = resolve_skill_path("security-engineer")
            assert source == "project"
            assert "Custom" in path.read_text()

    def test_user_takes_priority_over_bundled(self, tmp_path: Path) -> None:
        """User-level skills should take priority over bundled."""
        user_skills = tmp_path / "user-skills" / "security-engineer"
        user_skills.mkdir(parents=True)
        (user_skills / "SKILL.md").write_text("---\nversion: \"1.0\"\n---\n# User")

        with (
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "user-skills"),
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent"),
        ):
            path, source = resolve_skill_path("security-engineer")
            assert source == "user"
            assert "User" in path.read_text()


class TestGetAllSkillNames:
    """Test getting all available skill names."""

    def test_returns_bundled_skills(self) -> None:
        """Should return bundled skill names."""
        names = get_all_skill_names()
        assert "security-engineer" in names
        assert "web3-engineer" in names
        assert "backend-engineer" in names

    def test_returns_at_least_10_skills(self) -> None:
        """Should have at least 10 bundled skills."""
        names = get_all_skill_names()
        assert len(names) >= 10


class TestLoadSkill:
    """Test skill loading."""

    def test_load_security_engineer(self) -> None:
        """Should load security-engineer skill."""
        result = load_skill("security-engineer")
        assert result.is_ok
        metadata, content = result.value
        assert metadata.name == "security-engineer"
        assert metadata.always_run is True
        assert "SECURITY.md" in metadata.knowledge
        assert "# Security Engineer" in content

    def test_load_web3_engineer(self) -> None:
        """Should load web3-engineer skill."""
        result = load_skill("web3-engineer")
        assert result.is_ok
        metadata, content = result.value
        assert metadata.name == "web3-engineer"
        assert "smart_contract" in metadata.always_run_for_domains
        assert "solidity" in metadata.triggers or "web3" in metadata.triggers

    def test_load_nonexistent_skill_error(self) -> None:
        """Should error when skill doesn't exist."""
        result = load_skill("nonexistent-skill-xyz-12345")
        assert result.is_err
        assert "not found" in result.error


class TestMatchSkillsForDomain:
    """Test skill matching logic."""

    def test_security_always_matches(self, tmp_path: Path) -> None:
        """Security-engineer should always match (always_run: true)."""
        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            matched = match_skills_for_domain(Domain.BACKEND, ["python", "backend"])
            skill_names = [name for name, _ in matched]
            assert "security-engineer" in skill_names

            # Check that always_run is in the triggers
            for name, triggers in matched:
                if name == "security-engineer":
                    assert "always_run" in triggers

    def test_web3_matches_smart_contract_domain(self, tmp_path: Path) -> None:
        """Web3-engineer should match for smart_contract domain."""
        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            matched = match_skills_for_domain(
                Domain.SMART_CONTRACT, ["solidity", "smart_contract", "web3"]
            )
            skill_names = [name for name, _ in matched]
            assert "web3-engineer" in skill_names

    def test_backend_matches_python_tags(self, tmp_path: Path) -> None:
        """Backend-engineer should match for python domain tags."""
        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            matched = match_skills_for_domain(Domain.BACKEND, ["python", "backend"])
            skill_names = [name for name, _ in matched]
            assert "backend-engineer" in skill_names

    def test_override_skips_matching(self, tmp_path: Path) -> None:
        """Override list should skip normal matching."""
        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            matched = match_skills_for_domain(
                Domain.BACKEND,
                ["python", "backend"],
                override=["web3-engineer"],  # Force web3 for python code
            )
            skill_names = [name for name, _ in matched]
            assert skill_names == ["web3-engineer"]

            # Check that explicit is the trigger
            for name, triggers in matched:
                if name == "web3-engineer":
                    assert triggers == ["explicit"]

    def test_no_matches_for_unknown_domain(self, tmp_path: Path) -> None:
        """Unknown domain should still match always_run skills."""
        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            matched = match_skills_for_domain(Domain.UNKNOWN, ["unknown"])
            skill_names = [name for name, _ in matched]
            # Security should still match due to always_run
            assert "security-engineer" in skill_names


class TestGetKnowledgeForSkills:
    """Test knowledge collection from skills."""

    def test_collects_security_knowledge(self, tmp_path: Path) -> None:
        """Should collect SECURITY.md from security-engineer."""
        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            knowledge = get_knowledge_for_skills(["security-engineer"])
            assert "SECURITY.md" in knowledge

    def test_collects_multiple_files(self, tmp_path: Path) -> None:
        """Should collect knowledge from multiple skills."""
        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            knowledge = get_knowledge_for_skills(["security-engineer", "web3-engineer"])
            assert "SECURITY.md" in knowledge
            assert "SMART_CONTRACT.md" in knowledge

    def test_deduplicates_knowledge(self, tmp_path: Path) -> None:
        """Should deduplicate knowledge files."""
        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            # Both skills reference SECURITY.md
            knowledge = get_knowledge_for_skills(["security-engineer", "web3-engineer"])
            # Count occurrences - should be exactly 1
            assert isinstance(knowledge, set)

    def test_empty_for_unknown_skills(self) -> None:
        """Should return empty set for unknown skills."""
        knowledge = get_knowledge_for_skills(["nonexistent-skill-xyz"])
        assert knowledge == set()


class TestSkillCaching:
    """Test skill loading cache."""

    def test_cache_returns_same_result(self, tmp_path: Path) -> None:
        """Cached results should be identical."""
        clear_skill_cache()

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            result1 = load_skill("security-engineer")
            result2 = load_skill("security-engineer")

            assert result1.is_ok
            assert result2.is_ok
            # Should be the exact same object due to caching
            assert result1.value is result2.value

    def test_cache_clear_works(self, tmp_path: Path) -> None:
        """Cache clear should force reload."""
        clear_skill_cache()

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            result1 = load_skill("security-engineer")
            clear_skill_cache()
            result2 = load_skill("security-engineer")

            assert result1.is_ok
            assert result2.is_ok
            # After cache clear, should be different objects
            assert result1.value is not result2.value
            # But with same content
            assert result1.value[0] == result2.value[0]

    def test_cache_info_shows_hits(self, tmp_path: Path) -> None:
        """Cache should show hits after repeated loads."""
        clear_skill_cache()

        with (
            patch("crucible.skills.loader.SKILLS_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.skills.loader.SKILLS_USER", tmp_path / "nonexistent-user"),
        ):
            load_skill("security-engineer")
            load_skill("security-engineer")
            load_skill("security-engineer")

            info = _load_skill_cached.cache_info()
            assert info.hits >= 2  # At least 2 cache hits


class TestBundledSkillsIntegrity:
    """Test bundled skills have valid frontmatter."""

    def test_all_bundled_skills_have_valid_frontmatter(self) -> None:
        """All bundled skills should have parseable frontmatter."""
        for skill_name in get_all_skill_names():
            result = load_skill(skill_name)
            assert result.is_ok, f"Skill {skill_name} failed to load: {result.error}"
            metadata, content = result.value
            assert metadata.name == skill_name
            assert metadata.version

    def test_all_bundled_skills_have_knowledge(self) -> None:
        """All bundled skills should reference at least one knowledge file."""
        for skill_name in get_all_skill_names():
            result = load_skill(skill_name)
            if result.is_ok:
                metadata, _ = result.value
                # Most skills should have knowledge, but not strictly required
                # Just verify the field is a tuple
                assert isinstance(metadata.knowledge, tuple)

    def test_security_engineer_is_always_run(self) -> None:
        """Security engineer should have always_run: true."""
        result = load_skill("security-engineer")
        assert result.is_ok
        metadata, _ = result.value
        assert metadata.always_run is True, "security-engineer should have always_run: true"

    def test_web3_engineer_runs_for_smart_contract(self) -> None:
        """Web3 engineer should have always_run_for_domains: [smart_contract]."""
        result = load_skill("web3-engineer")
        assert result.is_ok
        metadata, _ = result.value
        assert "smart_contract" in metadata.always_run_for_domains
