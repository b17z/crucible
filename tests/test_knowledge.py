"""Tests for knowledge loader."""

from pathlib import Path
from unittest.mock import patch

import pytest

from crucible.knowledge.loader import (
    KNOWLEDGE_BUNDLED,
    get_all_knowledge_files,
    get_custom_knowledge_files,
    get_persona_section,
    load_all_knowledge,
    load_knowledge_file,
    load_principles,
    resolve_knowledge_file,
)


class TestResolveKnowledgeFile:
    """Test knowledge file resolution cascade."""

    def test_bundled_file_found(self, tmp_path: Path) -> None:
        """Bundled knowledge files should be found when no overrides exist."""
        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
        ):
            path, source = resolve_knowledge_file("SECURITY.md")
            assert path is not None
            assert source == "bundled"
            assert path.exists()

    def test_nonexistent_file_returns_none(self) -> None:
        """Non-existent file should return None."""
        path, source = resolve_knowledge_file("nonexistent-file-12345.md")
        assert path is None
        assert source == ""

    def test_project_takes_priority(self, tmp_path: Path) -> None:
        """Project-level knowledge should take priority over bundled."""
        project_knowledge = tmp_path / ".crucible" / "knowledge"
        project_knowledge.mkdir(parents=True)
        (project_knowledge / "SECURITY.md").write_text("# Custom Security\n")

        with patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", project_knowledge):
            path, source = resolve_knowledge_file("SECURITY.md")
            assert source == "project"
            assert "Custom Security" in path.read_text()

    def test_user_takes_priority_over_bundled(self, tmp_path: Path) -> None:
        """User-level knowledge should take priority over bundled."""
        user_knowledge = tmp_path / "user-knowledge"
        user_knowledge.mkdir(parents=True)
        (user_knowledge / "SECURITY.md").write_text("# User Security\n")

        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", user_knowledge),
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", tmp_path / "nonexistent"),
        ):
            path, source = resolve_knowledge_file("SECURITY.md")
            assert source == "user"
            assert "User Security" in path.read_text()


class TestGetAllKnowledgeFiles:
    """Test getting all available knowledge files."""

    def test_returns_bundled_files(self) -> None:
        """Should return bundled knowledge files."""
        files = get_all_knowledge_files()
        assert "SECURITY.md" in files
        assert "TESTING.md" in files
        assert "SMART_CONTRACT.md" in files

    def test_returns_at_least_10_files(self) -> None:
        """Should have at least 10 bundled knowledge files (domain-specific)."""
        files = get_all_knowledge_files()
        assert len(files) >= 10


class TestLoadPrinciples:
    """Test principles loading."""

    def test_load_default_principles(self) -> None:
        """Should load engineering principles with no topic."""
        result = load_principles()
        assert result.is_ok
        assert len(result.value) > 100

    def test_load_engineering_topic(self) -> None:
        """Should load engineering principles with 'engineering' topic."""
        result = load_principles("engineering")
        assert result.is_ok
        assert len(result.value) > 100

    def test_load_security_topic(self) -> None:
        """Should load security checklist."""
        result = load_principles("security")
        assert result.is_ok
        content_lower = result.value.lower()
        assert "security" in content_lower

    def test_load_smart_contract_topic(self) -> None:
        """Should load smart contract checklist."""
        result = load_principles("smart_contract")
        assert result.is_ok

    def test_load_checklist_topic(self) -> None:
        """Should load combined checklist."""
        result = load_principles("checklist")
        assert result.is_ok

    def test_unknown_topic_returns_default(self) -> None:
        """Unknown topic should return default principles."""
        result = load_principles("nonexistent-topic-xyz")
        assert result.is_ok  # Falls back to default


class TestKnowledgeBundled:
    """Test bundled knowledge files exist and have content."""

    def test_bundled_directory_exists(self) -> None:
        """Bundled knowledge directory should exist."""
        assert KNOWLEDGE_BUNDLED.exists()
        assert KNOWLEDGE_BUNDLED.is_dir()

    def test_security_file_exists(self) -> None:
        """Security file should exist."""
        path = KNOWLEDGE_BUNDLED / "SECURITY.md"
        assert path.exists()
        content = path.read_text()
        assert len(content) > 500
        assert "security" in content.lower()

    def test_testing_file_exists(self) -> None:
        """Testing file should exist."""
        path = KNOWLEDGE_BUNDLED / "TESTING.md"
        assert path.exists()
        content = path.read_text()
        assert "test" in content.lower()

    def test_smart_contract_file_exists(self) -> None:
        """Smart contract file should exist."""
        path = KNOWLEDGE_BUNDLED / "SMART_CONTRACT.md"
        assert path.exists()
        content = path.read_text()
        assert "solidity" in content.lower() or "contract" in content.lower()


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


class TestLoadKnowledgeFile:
    """Test single knowledge file loading."""

    def test_load_existing_file(self) -> None:
        """Should load an existing knowledge file."""
        result = load_knowledge_file("SECURITY.md")
        assert result.is_ok
        assert len(result.value) > 100
        assert "security" in result.value.lower()

    def test_load_nonexistent_file_error(self) -> None:
        """Should error for nonexistent file."""
        result = load_knowledge_file("nonexistent-file-xyz.md")
        assert result.is_err
        assert "not found" in result.error


class TestGetCustomKnowledgeFiles:
    """Test custom knowledge file discovery."""

    def test_returns_empty_when_no_custom(self, tmp_path: Path) -> None:
        """Should return empty set when no project/user knowledge."""
        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
        ):
            files = get_custom_knowledge_files()
            assert files == set()

    def test_returns_project_files(self, tmp_path: Path) -> None:
        """Should return files from project knowledge directory."""
        project_knowledge = tmp_path / ".crucible" / "knowledge"
        project_knowledge.mkdir(parents=True)
        (project_knowledge / "MY_PATTERNS.md").write_text("# My Patterns\n")
        (project_knowledge / "TEAM_RULES.md").write_text("# Team Rules\n")

        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", project_knowledge),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
        ):
            files = get_custom_knowledge_files()
            assert "MY_PATTERNS.md" in files
            assert "TEAM_RULES.md" in files

    def test_returns_user_files(self, tmp_path: Path) -> None:
        """Should return files from user knowledge directory."""
        user_knowledge = tmp_path / "user-knowledge"
        user_knowledge.mkdir(parents=True)
        (user_knowledge / "MY_PREFS.md").write_text("# My Preferences\n")

        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", user_knowledge),
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", tmp_path / "nonexistent-project"),
        ):
            files = get_custom_knowledge_files()
            assert "MY_PREFS.md" in files

    def test_does_not_include_bundled(self, tmp_path: Path) -> None:
        """Should NOT include bundled knowledge files."""
        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
        ):
            files = get_custom_knowledge_files()
            # Bundled files like SECURITY.md should not be in custom
            assert "SECURITY.md" not in files


class TestLoadAllKnowledge:
    """Test bulk knowledge loading."""

    def test_load_specific_files(self) -> None:
        """Should load specific files by name."""
        loaded, content = load_all_knowledge(filenames={"SECURITY.md", "TESTING.md"})
        assert "SECURITY.md" in loaded
        assert "TESTING.md" in loaded
        assert "security" in content.lower()

    def test_load_bundled_includes_all(self) -> None:
        """Should load all bundled files when include_bundled=True."""
        loaded, content = load_all_knowledge(include_bundled=True)
        assert "SECURITY.md" in loaded
        assert len(loaded) >= 5  # Should have multiple bundled files
        assert len(content) > 1000  # Should have substantial content

    def test_load_custom_only(self, tmp_path: Path) -> None:
        """Should only load custom files when include_bundled=False."""
        project_knowledge = tmp_path / ".crucible" / "knowledge"
        project_knowledge.mkdir(parents=True)
        (project_knowledge / "CUSTOM.md").write_text("# Custom Knowledge\n")

        with (
            patch("crucible.knowledge.loader.KNOWLEDGE_PROJECT", project_knowledge),
            patch("crucible.knowledge.loader.KNOWLEDGE_USER", tmp_path / "nonexistent-user"),
        ):
            loaded, content = load_all_knowledge(include_bundled=False)
            assert loaded == ["CUSTOM.md"]
            assert "Custom Knowledge" in content

    def test_empty_when_no_matches(self) -> None:
        """Should return empty when no files match."""
        loaded, content = load_all_knowledge(filenames={"nonexistent.md"})
        assert loaded == []
        assert content == ""
