"""Tests for knowledge loader."""

from pathlib import Path
from unittest.mock import patch

import pytest

from crucible.knowledge.loader import (
    find_knowledge_dir,
    get_persona_section,
    load_principles,
)


class TestFindKnowledgeDir:
    """Test knowledge directory discovery."""

    def test_finds_package_knowledge_dir(self) -> None:
        """Should find the bundled knowledge directory."""
        knowledge_dir = find_knowledge_dir()
        assert knowledge_dir is not None
        assert knowledge_dir.is_dir()
        assert (knowledge_dir / "ENGINEERING_PRINCIPLES.md").exists()

    def test_project_local_takes_priority(self, tmp_path: Path) -> None:
        """Project-local knowledge/ should take priority."""
        project_knowledge = tmp_path / "knowledge"
        project_knowledge.mkdir()
        (project_knowledge / "TEST.md").write_text("# Test\n")

        with patch("crucible.knowledge.loader.Path.cwd", return_value=tmp_path):
            result = find_knowledge_dir()
            assert result == project_knowledge

    def test_fallback_to_package_dir(self, tmp_path: Path) -> None:
        """Should fall back to package knowledge when project-local doesn't exist."""
        # When cwd has no knowledge dir, should still find package knowledge
        with patch("crucible.knowledge.loader.Path.cwd", return_value=tmp_path):
            result = find_knowledge_dir()
            # Should find the package knowledge dir
            assert result is not None
            assert result.is_dir()
            assert (result / "ENGINEERING_PRINCIPLES.md").exists()


class TestLoadPrinciples:
    """Test principles loading."""

    def test_load_default_principles(self) -> None:
        """Should load engineering principles with no topic."""
        result = load_principles()
        assert result.is_ok
        assert "ENGINEERING_PRINCIPLES" in result.value or len(result.value) > 100

    def test_load_engineering_topic(self) -> None:
        """Should load engineering principles with 'engineering' topic."""
        result = load_principles("engineering")
        assert result.is_ok
        assert len(result.value) > 100

    def test_load_security_topic(self) -> None:
        """Should load security checklist."""
        result = load_principles("security")
        assert result.is_ok
        # Should contain security-related content
        content_lower = result.value.lower()
        assert "security" in content_lower or "engineer" in content_lower

    def test_load_smart_contract_topic(self) -> None:
        """Should load smart contract checklist."""
        result = load_principles("smart_contract")
        assert result.is_ok

    def test_load_checklist_topic(self) -> None:
        """Should load checklist."""
        result = load_principles("checklist")
        assert result.is_ok

    def test_unknown_topic_returns_default(self) -> None:
        """Unknown topic should return default principles."""
        result = load_principles("nonexistent-topic-xyz")
        assert result.is_ok  # Falls back to default


class TestGetPersonaSection:
    """Test persona section extraction."""

    @pytest.fixture
    def sample_checklist(self) -> str:
        """Sample checklist content for testing."""
        return """# Engineering Checklist

## Security Engineer

Security content here.
- Point 1
- Point 2

## Backend/Systems Engineer

Backend content here.
- Point A
- Point B

## Web3/Blockchain Engineer

Web3 content here.
"""

    def test_extract_security_section(self, sample_checklist: str) -> None:
        """Should extract security engineer section."""
        section = get_persona_section("security", sample_checklist)
        assert section is not None
        assert "Security content here" in section
        assert "Backend content" not in section

    def test_extract_backend_section(self, sample_checklist: str) -> None:
        """Should extract backend engineer section."""
        section = get_persona_section("backend", sample_checklist)
        assert section is not None
        assert "Backend content here" in section
        assert "Security content" not in section

    def test_extract_web3_section(self, sample_checklist: str) -> None:
        """Should extract web3 engineer section."""
        section = get_persona_section("web3", sample_checklist)
        assert section is not None
        assert "Web3 content here" in section

    def test_case_insensitive_persona(self, sample_checklist: str) -> None:
        """Persona name should be case insensitive."""
        section_lower = get_persona_section("security", sample_checklist)
        section_upper = get_persona_section("SECURITY", sample_checklist)
        assert section_lower == section_upper

    def test_unknown_persona_returns_none(self, sample_checklist: str) -> None:
        """Unknown persona should return None."""
        section = get_persona_section("unknown-persona", sample_checklist)
        assert section is None

    def test_all_supported_personas(self) -> None:
        """Should support all documented personas."""
        supported = [
            "security",
            "web3",
            "backend",
            "devops",
            "product",
            "performance",
            "data",
            "accessibility",
            "mobile",
            "uiux",
            "fde",
            "customer_success",
            "tech_lead",
            "pragmatist",
            "purist",
        ]

        # Create content with all headers
        content = "# Test\n\n"
        for persona in supported:
            header_map = {
                "security": "## Security Engineer",
                "web3": "## Web3/Blockchain Engineer",
                "backend": "## Backend/Systems Engineer",
                "devops": "## DevOps/SRE",
                "product": "## Product Engineer",
                "performance": "## Performance Engineer",
                "data": "## Data Engineer",
                "accessibility": "## Accessibility Engineer",
                "mobile": "## Mobile/Client Engineer",
                "uiux": "## UI/UX Designer",
                "fde": "## Forward Deployed",
                "customer_success": "## Customer Success",
                "tech_lead": "## Tech Lead",
                "pragmatist": "## Pragmatist",
                "purist": "## Purist",
            }
            content += f"\n{header_map[persona]}\n\nContent for {persona}.\n"

        for persona in supported:
            section = get_persona_section(persona, content)
            assert section is not None, f"Failed to extract {persona}"
            assert f"Content for {persona}" in section
