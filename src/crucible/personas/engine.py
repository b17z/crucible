"""Persona engine - parse and invoke review personas."""

import re
from dataclasses import dataclass, field

from crucible.knowledge.loader import get_persona_section, load_principles


@dataclass(frozen=True)
class PersonaPrompt:
    """Structured persona review prompt."""

    name: str
    key_questions: tuple[str, ...] = field(default_factory=tuple)
    red_flags: tuple[str, ...] = field(default_factory=tuple)
    approval_criteria: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PersonaPerspective:
    """A persona's perspective on code."""

    persona: str
    questions: tuple[str, ...]  # Questions this persona would ask about the code
    concerns: tuple[str, ...]   # Red flags or concerns identified
    checklist: tuple[str, ...]  # Approval criteria to verify


def _extract_bullet_points(text: str, header: str) -> list[str]:
    """Extract bullet points from a section with given header."""
    # Find the section
    pattern = rf"###\s*{re.escape(header)}\s*\n(.*?)(?=###|^---|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    if not match:
        return []

    section = match.group(1)
    items: list[str] = []

    for line in section.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Match bullet with checkbox: - [ ] text or * [ ] text
        checkbox_match = re.match(r"^[\-\*]\s*\[.\]\s*(.+)$", line)
        if checkbox_match:
            items.append(checkbox_match.group(1).strip())
            continue

        # Match simple bullet: - text or * text
        bullet_match = re.match(r"^[\-\*]\s+(.+)$", line)
        if bullet_match:
            items.append(bullet_match.group(1).strip())
            continue

        # Match standalone checkbox: [ ] text
        standalone_checkbox = re.match(r"^\[.\]\s*(.+)$", line)
        if standalone_checkbox:
            items.append(standalone_checkbox.group(1).strip())

    return items


def parse_persona_section(persona_name: str, content: str) -> PersonaPrompt | None:
    """
    Parse a persona section from markdown into structured data.

    Args:
        persona_name: Name of the persona
        content: Full markdown content containing persona sections

    Returns:
        PersonaPrompt with extracted data, or None if not found
    """
    section = get_persona_section(persona_name, content)
    if not section:
        return None

    key_questions = _extract_bullet_points(section, "Key Questions")
    red_flags = _extract_bullet_points(section, "Red Flags")
    approval_criteria = _extract_bullet_points(section, "Approval Criteria")

    return PersonaPrompt(
        name=persona_name,
        key_questions=tuple(key_questions),
        red_flags=tuple(red_flags),
        approval_criteria=tuple(approval_criteria),
    )


def invoke_personas(
    persona_names: list[str],
    max_personas: int = 3,
) -> list[PersonaPerspective]:
    """
    Load and invoke multiple personas.

    Args:
        persona_names: List of persona names to invoke
        max_personas: Maximum number of personas to include

    Returns:
        List of PersonaPerspective objects
    """
    principles_result = load_principles("checklist")
    if principles_result.is_err:
        return []

    content = principles_result.value
    perspectives: list[PersonaPerspective] = []

    for name in persona_names[:max_personas]:
        prompt = parse_persona_section(name, content)
        if prompt:
            perspective = PersonaPerspective(
                persona=prompt.name,
                questions=prompt.key_questions,
                concerns=prompt.red_flags,
                checklist=prompt.approval_criteria,
            )
            perspectives.append(perspective)

    return perspectives


def format_multi_persona_review(
    perspectives: list[PersonaPerspective],
    domain: str,
) -> str:
    """
    Format multiple persona perspectives as markdown.

    Args:
        perspectives: List of persona perspectives
        domain: The detected code domain

    Returns:
        Formatted markdown string
    """
    parts: list[str] = []
    parts.append("# Multi-Persona Code Review\n")
    parts.append(f"**Domain:** {domain}")
    parts.append(f"**Personas:** {', '.join(p.persona for p in perspectives)}\n")

    for p in perspectives:
        parts.append(f"## {p.persona.replace('_', ' ').title()}\n")

        if p.questions:
            parts.append("### Questions to Ask")
            for q in p.questions:
                parts.append(f"- {q}")
            parts.append("")

        if p.concerns:
            parts.append("### Watch For")
            for c in p.concerns:
                parts.append(f"- ⚠️ {c}")
            parts.append("")

        if p.checklist:
            parts.append("### Before Approving")
            for item in p.checklist:
                parts.append(f"- [ ] {item}")
            parts.append("")

        parts.append("---\n")

    return "\n".join(parts)
