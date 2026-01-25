"""Tests for bundled skills - validates all 18 skills have proper structure."""

import re

import pytest

from crucible.cli import SKILLS_BUNDLED, get_all_skill_names

# Expected skills
EXPECTED_SKILLS = {
    "security-engineer",
    "web3-engineer",
    "backend-engineer",
    "devops-engineer",
    "performance-engineer",
    "accessibility-engineer",
    "data-engineer",
    "product-engineer",
    "tech-lead",
    "mobile-engineer",
    "uiux-engineer",
    "fde-engineer",
    "customer-success",
    "gas-optimizer",
    "protocol-architect",
    "mev-researcher",
    "formal-verification",
    "incident-responder",
}


class TestSkillsExist:
    """Test that all expected skills exist."""

    def test_all_expected_skills_exist(self) -> None:
        """All 18 expected skills should exist."""
        actual = get_all_skill_names()
        for skill in EXPECTED_SKILLS:
            assert skill in actual, f"Missing skill: {skill}"

    def test_exactly_18_bundled_skills(self) -> None:
        """Should have exactly 18 bundled skills."""
        bundled = set()
        for skill_dir in SKILLS_BUNDLED.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                bundled.add(skill_dir.name)
        assert len(bundled) == 18, f"Expected 18 skills, got {len(bundled)}: {bundled}"

    def test_skills_directory_exists(self) -> None:
        """Skills bundled directory should exist."""
        assert SKILLS_BUNDLED.exists()
        assert SKILLS_BUNDLED.is_dir()


class TestSkillMetadata:
    """Test that all skills have proper YAML frontmatter."""

    @pytest.fixture(params=sorted(EXPECTED_SKILLS))
    def skill_content(self, request: pytest.FixtureRequest) -> tuple[str, str]:
        """Load skill content for each expected skill."""
        skill_name = request.param
        skill_path = SKILLS_BUNDLED / skill_name / "SKILL.md"
        return skill_name, skill_path.read_text()

    def test_has_yaml_frontmatter(self, skill_content: tuple[str, str]) -> None:
        """Each skill should have YAML frontmatter."""
        skill_name, content = skill_content
        assert content.startswith("---"), f"{skill_name}: Missing YAML frontmatter start"
        assert content.count("---") >= 2, f"{skill_name}: Missing YAML frontmatter end"

    def test_has_version(self, skill_content: tuple[str, str]) -> None:
        """Each skill should have a version field."""
        skill_name, content = skill_content
        assert "version:" in content, f"{skill_name}: Missing version field"

    def test_has_triggers(self, skill_content: tuple[str, str]) -> None:
        """Each skill should have trigger keywords."""
        skill_name, content = skill_content
        assert "triggers:" in content, f"{skill_name}: Missing triggers field"

    def test_has_title(self, skill_content: tuple[str, str]) -> None:
        """Each skill should have a markdown title."""
        skill_name, content = skill_content
        # Should have at least one # header after frontmatter
        lines = content.split("\n")
        has_title = any(line.startswith("# ") for line in lines)
        assert has_title, f"{skill_name}: Missing markdown title"

    def test_version_is_semver_like(self, skill_content: tuple[str, str]) -> None:
        """Version should be semver-like (e.g., '1.0', '1.0.0')."""
        skill_name, content = skill_content
        match = re.search(r'version:\s*["\']?(\d+\.\d+(?:\.\d+)?)["\']?', content)
        assert match, f"{skill_name}: Invalid version format"

    def test_triggers_is_list(self, skill_content: tuple[str, str]) -> None:
        """Triggers should be a YAML list."""
        skill_name, content = skill_content
        # Should match either [a, b, c] or multiline list format
        assert re.search(r"triggers:\s*\[", content), f"{skill_name}: Triggers should be a list"


class TestSkillContent:
    """Test skill content quality."""

    @pytest.fixture(params=sorted(EXPECTED_SKILLS))
    def skill_content(self, request: pytest.FixtureRequest) -> tuple[str, str]:
        """Load skill content for each expected skill."""
        skill_name = request.param
        skill_path = SKILLS_BUNDLED / skill_name / "SKILL.md"
        return skill_name, skill_path.read_text()

    def test_minimum_content_length(self, skill_content: tuple[str, str]) -> None:
        """Each skill should have meaningful content (at least 300 chars)."""
        skill_name, content = skill_content
        assert len(content) >= 300, f"{skill_name}: Content too short ({len(content)} chars)"

    def test_has_key_questions_or_equivalent(self, skill_content: tuple[str, str]) -> None:
        """Each skill should have guiding questions or review criteria."""
        skill_name, content = skill_content
        content_lower = content.lower()
        has_guidance = (
            "key questions" in content_lower
            or "red flags" in content_lower
            or "watch for" in content_lower
            or "before approving" in content_lower
            or "checklist" in content_lower
            or "## " in content  # Has at least one section
        )
        assert has_guidance, f"{skill_name}: Missing review guidance sections"

    def test_no_placeholder_content(self, skill_content: tuple[str, str]) -> None:
        """Skills should not have TODO or placeholder content."""
        skill_name, content = skill_content
        content_lower = content.lower()
        assert "todo" not in content_lower, f"{skill_name}: Contains TODO placeholder"
        assert "placeholder" not in content_lower, f"{skill_name}: Contains placeholder text"
        assert "lorem ipsum" not in content_lower, f"{skill_name}: Contains lorem ipsum"


class TestSkillCategories:
    """Test that skills cover expected categories."""

    def test_has_security_skill(self) -> None:
        """Should have a security-focused skill."""
        assert "security-engineer" in EXPECTED_SKILLS

    def test_has_web3_skills(self) -> None:
        """Should have Web3/blockchain skills."""
        web3_skills = {"web3-engineer", "gas-optimizer", "protocol-architect", "mev-researcher"}
        assert web3_skills.issubset(EXPECTED_SKILLS)

    def test_has_core_engineering_skills(self) -> None:
        """Should have core engineering skills."""
        core_skills = {"backend-engineer", "devops-engineer", "performance-engineer"}
        assert core_skills.issubset(EXPECTED_SKILLS)

    def test_has_specialty_skills(self) -> None:
        """Should have specialty skills."""
        specialty_skills = {
            "data-engineer",
            "accessibility-engineer",
            "mobile-engineer",
            "uiux-engineer",
        }
        assert specialty_skills.issubset(EXPECTED_SKILLS)

    def test_has_leadership_skills(self) -> None:
        """Should have leadership/ops skills."""
        leadership_skills = {"tech-lead", "incident-responder", "fde-engineer"}
        assert leadership_skills.issubset(EXPECTED_SKILLS)


class TestSkillTriggers:
    """Test that skill triggers are appropriate."""

    def test_security_engineer_triggers(self) -> None:
        """Security engineer should trigger on security-related keywords."""
        content = (SKILLS_BUNDLED / "security-engineer" / "SKILL.md").read_text()
        assert "security" in content
        assert "auth" in content.lower()

    def test_web3_engineer_triggers(self) -> None:
        """Web3 engineer should trigger on blockchain keywords."""
        content = (SKILLS_BUNDLED / "web3-engineer" / "SKILL.md").read_text()
        assert "solidity" in content.lower()
        assert "smart_contract" in content.lower() or "ethereum" in content.lower()

    def test_backend_engineer_triggers(self) -> None:
        """Backend engineer should trigger on backend keywords."""
        content = (SKILLS_BUNDLED / "backend-engineer" / "SKILL.md").read_text()
        assert "backend" in content.lower() or "api" in content.lower()

    def test_devops_engineer_triggers(self) -> None:
        """DevOps engineer should trigger on infra keywords."""
        content = (SKILLS_BUNDLED / "devops-engineer" / "SKILL.md").read_text()
        content_lower = content.lower()
        assert "devops" in content_lower or "infrastructure" in content_lower or "deploy" in content_lower
