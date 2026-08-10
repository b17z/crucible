"""Tests for the design-taste knowledge files and their attributions.

Covers: src/crucible/knowledge/principles/design-taste.md,
motion-interaction.md, ux-writing.md, and THIRD-PARTY-NOTICES.md.
"""

from pathlib import Path

from crucible.knowledge.loader import load_knowledge_file

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTICES_PATH = REPO_ROOT / "THIRD-PARTY-NOTICES.md"

KNOWLEDGE_FILES = [
    "design-taste.md",
    "motion-interaction.md",
    "ux-writing.md",
]


class TestKnowledgeFilesLoad:
    """Knowledge files load via the loader's cascade, by name."""

    def test_design_taste_loads(self) -> None:
        result = load_knowledge_file("design-taste.md")
        assert result.is_ok
        assert len(result.value) > 500

    def test_motion_interaction_loads(self) -> None:
        result = load_knowledge_file("motion-interaction.md")
        assert result.is_ok
        assert len(result.value) > 500

    def test_ux_writing_loads(self) -> None:
        result = load_knowledge_file("ux-writing.md")
        assert result.is_ok
        assert len(result.value) > 500


class TestProvenanceLines:
    """Each file opens with a provenance line naming its sources."""

    def test_design_taste_provenance(self) -> None:
        result = load_knowledge_file("design-taste.md")
        assert result.is_ok
        assert "> Adapted from" in result.value

    def test_motion_interaction_provenance(self) -> None:
        result = load_knowledge_file("motion-interaction.md")
        assert result.is_ok
        assert "> Adapted from" in result.value

    def test_ux_writing_provenance(self) -> None:
        result = load_knowledge_file("ux-writing.md")
        assert result.is_ok
        assert "> Adapted from" in result.value


class TestDesignTasteContent:
    """Binding content per spec section 1: cluster-look detection signals."""

    def test_cluster_look_hex_present(self) -> None:
        result = load_knowledge_file("design-taste.md")
        assert result.is_ok
        assert "#F4F1EA" in result.value

    def test_default_not_a_choice_framing(self) -> None:
        result = load_knowledge_file("design-taste.md")
        assert result.is_ok
        assert "default is not a choice" in result.value


class TestMotionInteractionContent:
    """Binding content per spec section 1: forbidden patterns + reduced motion."""

    def test_reduced_motion_mandatory(self) -> None:
        result = load_knowledge_file("motion-interaction.md")
        assert result.is_ok
        assert "prefers-reduced-motion" in result.value

    def test_interactive_state_matrix(self) -> None:
        result = load_knowledge_file("motion-interaction.md")
        assert result.is_ok
        content_lower = result.value.lower()
        for state in ["hover", "focus", "active", "disabled", "loading", "empty", "error"]:
            assert state in content_lower


class TestUxWritingContent:
    """Binding content per spec section 1: active voice, exact verbs."""

    def test_save_changes_not_submit(self) -> None:
        result = load_knowledge_file("ux-writing.md")
        assert result.is_ok
        assert "Save changes" in result.value


class TestThirdPartyNotices:
    """THIRD-PARTY-NOTICES.md carries all three new attributions."""

    def test_notices_file_exists(self) -> None:
        assert NOTICES_PATH.exists()

    def test_leonxlnx_copyright_line(self) -> None:
        content = NOTICES_PATH.read_text()
        assert "Copyright (c) 2026 Leonxlnx" in content

    def test_dragoon0x_copyright_line(self) -> None:
        content = NOTICES_PATH.read_text()
        assert "Copyright (c) 2026 Dragoon" in content

    def test_apache_license_and_anthropic_marker(self) -> None:
        content = NOTICES_PATH.read_text()
        assert "Apache License" in content
        assert "Anthropic" in content
