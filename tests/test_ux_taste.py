"""Tests for the design-taste knowledge files and their attributions.

Covers: src/crucible/knowledge/principles/design-taste.md,
motion-interaction.md, ux-writing.md, THIRD-PARTY-NOTICES.md, the
uiux-engineer persona upgrade, and the meta/frontend-taste skill.
"""

from pathlib import Path

import crucible
from crucible.knowledge.loader import load_knowledge_file

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTICES_PATH = REPO_ROOT / "THIRD-PARTY-NOTICES.md"

PKG = Path(crucible.__file__).parent
UIUX_ENGINEER_SKILL = PKG / "skills" / "uiux-engineer" / "SKILL.md"
FRONTEND_TASTE_SKILL = PKG / "skills" / "meta" / "frontend-taste" / "SKILL.md"
FRONTEND_TASTE_TRIGGERS = PKG / "skills" / "meta" / "frontend-taste" / "triggers.yaml"

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

    def test_design_taste_provenance_names_all_three_sources(self) -> None:
        """design-taste.md embeds content from all three sources (the
        three cluster looks and typography/color from Leonxlnx, the
        hierarchy/spatial-rhythm/color-systems/type-systems distillation
        input from Dragoon0x) — the provenance line must name all three
        so extracting just this file doesn't drop an attribution."""
        result = load_knowledge_file("design-taste.md")
        assert result.is_ok
        assert "Leonxlnx/taste-skill" in result.value
        assert "Dragoon0x/taste-skills" in result.value
        assert "anthropics/skills frontend-design" in result.value

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


BANNED_TASTE_WORDS = [
    "clean",
    "nice",
    "modern",
    "sleek",
    "beautiful",
    "stunning",
    "minimal",
    "bold",
]


class TestUiuxEngineerUpgrade:
    """Binding content per spec section 2: critique protocol, banned
    words, the rule/taste split, design-system-first, provenance."""

    def test_skill_file_exists(self) -> None:
        assert UIUX_ENGINEER_SKILL.exists()

    def test_banned_words_list_verbatim(self) -> None:
        content = UIUX_ENGINEER_SKILL.read_text()
        for word in BANNED_TASTE_WORDS:
            assert word in content, f"banned word {word!r} missing from uiux-engineer"

    def test_taste_human_call_heading_exact(self) -> None:
        content = UIUX_ENGINEER_SKILL.read_text()
        assert "TASTE (human call):" in content

    def test_design_system_first_rule(self) -> None:
        content = UIUX_ENGINEER_SKILL.read_text()
        assert "Design-system-first rule" in content

    def test_critique_output_order(self) -> None:
        """Critique output ordered intent -> working -> not working ->
        single highest-impact change (spec section 2)."""
        content = UIUX_ENGINEER_SKILL.read_text()
        assert "Intent" in content
        assert "Not working" in content
        assert "highest-impact change" in content
        intent_pos = content.index("**Intent**")
        working_pos = content.index("**Working**")
        not_working_pos = content.index("**Not working**")
        change_pos = content.index("**The single highest-impact change**")
        assert intent_pos < working_pos < not_working_pos < change_pos

    def test_provenance_line_names_all_three_sources(self) -> None:
        content = UIUX_ENGINEER_SKILL.read_text()
        assert "Leonxlnx/taste-skill" in content
        assert "Dragoon0x/taste-skills" in content
        assert "anthropics/skills frontend-design" in content

    def test_version_bumped_past_2_0(self) -> None:
        content = UIUX_ENGINEER_SKILL.read_text()
        assert 'version: "2.0"' not in content


class TestFrontendTasteSkill:
    """Binding content per spec section 3: Do-NOT boundary, hard rules,
    provenance, and file existence."""

    def test_skill_and_triggers_exist(self) -> None:
        assert FRONTEND_TASTE_SKILL.exists()
        assert FRONTEND_TASTE_TRIGGERS.exists()

    def test_do_not_boundary_items(self) -> None:
        content = FRONTEND_TASTE_SKILL.read_text()
        assert "backend" in content.lower()
        assert "never redesign" in content.lower()
        assert "never override" in content.lower()
        assert "theirs to win" in content.lower()

    def test_hard_rules_list(self) -> None:
        content = FRONTEND_TASTE_SKILL.read_text().lower()
        assert "design system first" in content
        assert "interactive-state matrix" in content
        assert "reduced motion" in content
        assert "ux-writing.md" in content
        assert "responsive floor" in content
        assert "visible keyboard focus" in content

    def test_provenance_line_names_all_three_sources(self) -> None:
        content = FRONTEND_TASTE_SKILL.read_text()
        assert "Leonxlnx/taste-skill" in content
        assert "Dragoon0x/taste-skills" in content
        assert "anthropics/skills frontend-design" in content

    def test_knowledge_tier3_pointers(self) -> None:
        content = FRONTEND_TASTE_SKILL.read_text()
        assert "design-taste.md" in content
        assert "motion-interaction.md" in content
        assert "ux-writing.md" in content
