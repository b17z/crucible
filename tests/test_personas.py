"""Tests for persona engine."""

from crucible.personas.engine import (
    PersonaPerspective,
    _extract_bullet_points,
    format_multi_persona_review,
    invoke_personas,
    parse_persona_section,
)

SAMPLE_PERSONA_MD = """
## Security Engineer

### Key Questions
- What's the threat model?
- What if this input is malicious?
- Who can access this?

### Red Flags
- Raw user input in queries
- Missing auth checks
- Secrets in code

### Approval Criteria
- [ ] Threat model documented
- [ ] Input validated
- [ ] Auth verified

---

## Backend Engineer

### Key Questions
- What happens at 10x load?
- Is this idempotent?

### Red Flags
- N+1 queries
- Missing indexes

### Approval Criteria
- [ ] Load tested
- [ ] Indexes verified
"""


class TestExtractBulletPoints:
    """Test bullet point extraction from markdown."""

    def test_extract_key_questions(self) -> None:
        bullets = _extract_bullet_points(SAMPLE_PERSONA_MD, "Key Questions")
        assert "What's the threat model?" in bullets
        assert "What if this input is malicious?" in bullets

    def test_extract_red_flags(self) -> None:
        bullets = _extract_bullet_points(SAMPLE_PERSONA_MD, "Red Flags")
        assert "Raw user input in queries" in bullets
        assert "Missing auth checks" in bullets

    def test_extract_approval_criteria(self) -> None:
        bullets = _extract_bullet_points(SAMPLE_PERSONA_MD, "Approval Criteria")
        assert "Threat model documented" in bullets
        assert "Input validated" in bullets

    def test_extract_missing_section(self) -> None:
        bullets = _extract_bullet_points(SAMPLE_PERSONA_MD, "Nonexistent Section")
        assert bullets == []


class TestParsePersonaSection:
    """Test parsing persona sections into structured data."""

    def test_parse_security_persona(self) -> None:
        prompt = parse_persona_section("security", SAMPLE_PERSONA_MD)
        assert prompt is not None
        assert prompt.name == "security"
        assert len(prompt.key_questions) == 3
        assert len(prompt.red_flags) == 3
        assert len(prompt.approval_criteria) == 3

    def test_parse_missing_persona(self) -> None:
        prompt = parse_persona_section("nonexistent", SAMPLE_PERSONA_MD)
        assert prompt is None


class TestInvokePersonas:
    """Test invoking multiple personas."""

    def test_invoke_returns_perspectives(self) -> None:
        # This uses the actual knowledge files
        perspectives = invoke_personas(["security", "backend"], max_personas=2)
        assert len(perspectives) <= 2
        if perspectives:
            assert all(isinstance(p, PersonaPerspective) for p in perspectives)

    def test_invoke_respects_max(self) -> None:
        perspectives = invoke_personas(
            ["security", "backend", "devops", "product"],
            max_personas=2,
        )
        assert len(perspectives) <= 2


class TestFormatMultiPersonaReview:
    """Test formatting multi-persona reviews."""

    def test_format_includes_all_personas(self) -> None:
        perspectives = [
            PersonaPerspective(
                persona="security",
                questions=("What's the threat model?",),
                concerns=("Raw SQL",),
                checklist=("Auth verified",),
            ),
            PersonaPerspective(
                persona="backend",
                questions=("What happens at 10x?",),
                concerns=("N+1 queries",),
                checklist=("Load tested",),
            ),
        ]
        output = format_multi_persona_review(perspectives, "backend")

        assert "# Multi-Persona Code Review" in output
        assert "security" in output.lower()
        assert "backend" in output.lower()
        assert "What's the threat model?" in output
        assert "What happens at 10x?" in output
        assert "Raw SQL" in output
        assert "N+1 queries" in output

    def test_format_includes_domain(self) -> None:
        perspectives = [
            PersonaPerspective(
                persona="security",
                questions=(),
                concerns=(),
                checklist=(),
            ),
        ]
        output = format_multi_persona_review(perspectives, "smart_contract")
        assert "smart_contract" in output
