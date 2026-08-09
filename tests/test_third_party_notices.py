"""Tests for THIRD-PARTY-NOTICES.md and the attribution/provenance
contract on the five adapted engineering-loop skills.

Content-level assertions only — these skills carry their contract in
prose (SKILL.md), not in parsed config, so the tests assert the prose
says what the spec requires rather than exercising runtime behavior.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
NOTICES = REPO_ROOT / "THIRD-PARTY-NOTICES.md"
SKILLS_META = REPO_ROOT / "src" / "crucible" / "skills" / "meta"

ADAPTED_SKILLS = {
    "brainstorming": ("obra/superpowers", "2025", "Jesse Vincent"),
    "systematic-debugging": ("obra/superpowers", "2025", "Jesse Vincent"),
    "tdd": ("mattpocock/skills", "2026", "Matt Pocock"),
    "wait-what": ("mattpocock/skills", "2026", "Matt Pocock"),
    "teach-me": ("mattpocock/skills", "2026", "Matt Pocock"),
}


class TestNoticesFileExists:
    def test_file_exists(self) -> None:
        assert NOTICES.exists()

    def test_contains_both_copyright_lines(self) -> None:
        text = NOTICES.read_text()
        assert "Copyright (c) 2025 Jesse Vincent" in text
        assert "Copyright (c) 2026 Matt Pocock" in text

    def test_contains_both_full_mit_texts(self) -> None:
        """Full MIT text (not just the copyright line) appears once per
        source repo — checked via a distinctive clause from the license
        body that only appears in the full text."""
        text = NOTICES.read_text()
        assert text.count("Permission is hereby granted, free of charge") == 2
        assert text.count('THE SOFTWARE IS PROVIDED "AS IS"') == 2

    def test_lists_source_urls(self) -> None:
        text = NOTICES.read_text()
        assert "https://github.com/obra/superpowers" in text
        assert "https://github.com/mattpocock/skills" in text

    def test_contains_karpathy_attribution(self) -> None:
        text = NOTICES.read_text()
        assert "Karpathy" in text
        assert "multica-ai/andrej-karpathy-skills" in text

    def test_claude_md_points_at_notices(self) -> None:
        claude_md = (REPO_ROOT / "CLAUDE.md").read_text()
        assert "THIRD-PARTY-NOTICES.md" in claude_md


class TestProvenanceLines:
    """Every adapted SKILL.md carries the spec's exact provenance-line
    format right after frontmatter."""

    def test_each_skill_has_provenance_line(self) -> None:
        for name, (repo, year, author) in ADAPTED_SKILLS.items():
            skill_md = SKILLS_META / name / "SKILL.md"
            assert skill_md.exists(), f"{name}: SKILL.md missing"
            text = skill_md.read_text()
            assert f"Adapted from {repo}" in text, f"{name}: missing repo in provenance line"
            assert f"MIT, © {year} {author}" in text, f"{name}: missing MIT/year/author"
            assert "THIRD-PARTY-NOTICES.md" in text, f"{name}: missing notices pointer"

    def test_provenance_line_immediately_follows_frontmatter(self) -> None:
        for name in ADAPTED_SKILLS:
            skill_md = SKILLS_META / name / "SKILL.md"
            text = skill_md.read_text()
            # Frontmatter is delimited by --- ... ---; provenance blockquote
            # must appear before the first H1 heading.
            parts = text.split("---", 2)
            assert len(parts) == 3, f"{name}: malformed frontmatter"
            body = parts[2]
            first_heading_idx = body.index("\n# ")
            provenance_idx = body.index("> Adapted from")
            assert provenance_idx < first_heading_idx, (
                f"{name}: provenance line must precede the first heading"
            )


class TestTeachMeVaultCascade:
    """Spec section 1: vault resolution must be documented verbatim, in
    order: project .crucible/teach.yaml -> user ~/.claude/crucible/teach.yaml
    -> workspace fallback with a one-time offer to write config. lessons/
    and assets/ always stay workspace-side."""

    def test_skill_md_documents_cascade_order(self) -> None:
        text = (SKILLS_META / "teach-me" / "SKILL.md").read_text()
        assert ".crucible/teach.yaml" in text
        assert "~/.claude/crucible/teach.yaml" in text
        project_idx = text.index(".crucible/teach.yaml")
        user_idx = text.index("~/.claude/crucible/teach.yaml")
        assert project_idx < user_idx, "project teach.yaml must be checked before user teach.yaml"

    def test_skill_md_documents_first_use_offer(self) -> None:
        text = (SKILLS_META / "teach-me" / "SKILL.md").read_text()
        assert "first use" in text.lower()
        assert "vault" in text.lower()

    def test_skill_md_documents_lessons_and_assets_stay_workspace_side(self) -> None:
        text = (SKILLS_META / "teach-me" / "SKILL.md").read_text()
        assert "lessons/" in text
        assert "assets/" in text
        assert "workspace" in text.lower()

    def test_knowledge_format_files_exist(self) -> None:
        knowledge_dir = SKILLS_META / "teach-me" / "knowledge"
        for fname in (
            "mission-format.md",
            "learning-record-format.md",
            "resources-format.md",
            "glossary-format.md",
        ):
            assert (knowledge_dir / fname).exists(), f"missing {fname}"
