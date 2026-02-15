"""Tests for pre-write review module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from crucible.prewrite.loader import (
    TEMPLATES_BUNDLED,
    detect_template_type,
    get_all_template_names,
    load_template,
    load_template_body,
    parse_template_frontmatter,
    resolve_template_path,
)
from crucible.prewrite.models import PrewriteFinding, PrewriteMetadata, PrewriteResult


class TestPrewriteMetadata:
    """Test PrewriteMetadata model."""

    def test_from_frontmatter_basic(self) -> None:
        """Should parse basic frontmatter."""
        data = {
            "name": "prd",
            "version": "1.0",
            "description": "Product requirements",
            "checklist": ["Item 1", "Item 2"],
            "knowledge": ["SECURITY.md"],
            "assertions": ["prewrite.yaml"],
        }
        metadata = PrewriteMetadata.from_frontmatter(data, "prd.md")

        assert metadata.name == "prd"
        assert metadata.version == "1.0"
        assert metadata.description == "Product requirements"
        assert metadata.checklist == ("Item 1", "Item 2")
        assert metadata.knowledge == ("SECURITY.md",)
        assert metadata.assertions == ("prewrite.yaml",)

    def test_from_frontmatter_defaults(self) -> None:
        """Should use defaults for missing fields."""
        data = {}
        metadata = PrewriteMetadata.from_frontmatter(data, "my-template.md")

        assert metadata.name == "My Template"  # Derived from filename
        assert metadata.version == "1.0"
        assert metadata.description == ""
        assert metadata.checklist == ()
        assert metadata.knowledge == ()
        assert metadata.assertions == ()

    def test_from_frontmatter_string_lists(self) -> None:
        """Should handle single string as list."""
        data = {
            "checklist": "Single item",
            "knowledge": "SECURITY.md",
            "assertions": "prewrite.yaml",
        }
        metadata = PrewriteMetadata.from_frontmatter(data, "test.md")

        assert metadata.checklist == ("Single item",)
        assert metadata.knowledge == ("SECURITY.md",)
        assert metadata.assertions == ("prewrite.yaml",)


class TestPrewriteResult:
    """Test PrewriteResult model."""

    def test_passed_with_no_errors(self) -> None:
        """Should pass with no error-level findings."""
        result = PrewriteResult(path="test.md", template="prd")
        result.findings = [
            PrewriteFinding("test", "warning", "warning"),
            PrewriteFinding("test2", "info", "info"),
        ]

        assert result.passed is True

    def test_failed_with_errors(self) -> None:
        """Should fail with error-level findings."""
        result = PrewriteResult(path="test.md", template="prd")
        result.findings = [
            PrewriteFinding("test", "error", "error"),
        ]

        assert result.passed is False

    def test_counts(self) -> None:
        """Should count findings by severity."""
        result = PrewriteResult(path="test.md", template="prd")
        result.findings = [
            PrewriteFinding("e1", "error 1", "error"),
            PrewriteFinding("e2", "error 2", "error"),
            PrewriteFinding("w1", "warning 1", "warning"),
            PrewriteFinding("i1", "info 1", "info"),
        ]

        assert result.error_count == 2
        assert result.warning_count == 1
        assert result.info_count == 1


class TestResolveTemplatePath:
    """Test template path resolution cascade."""

    def test_bundled_template_found(self, tmp_path: Path) -> None:
        """Bundled templates should be found when no overrides exist."""
        with (
            patch("crucible.prewrite.loader.TEMPLATES_PROJECT", tmp_path / "nonexistent-project"),
            patch("crucible.prewrite.loader.TEMPLATES_USER", tmp_path / "nonexistent-user"),
        ):
            path, source = resolve_template_path("prd")
            assert path is not None
            assert source == "bundled"
            assert path.exists()

    def test_nonexistent_template_returns_none(self) -> None:
        """Non-existent template should return None."""
        path, source = resolve_template_path("nonexistent-template-12345")
        assert path is None
        assert source == ""

    def test_project_takes_priority(self, tmp_path: Path) -> None:
        """Project-level template should take priority."""
        project_templates = tmp_path / ".crucible" / "templates" / "prewrite"
        project_templates.mkdir(parents=True)
        (project_templates / "prd.md").write_text("# Custom PRD\n")

        with patch("crucible.prewrite.loader.TEMPLATES_PROJECT", project_templates):
            path, source = resolve_template_path("prd")
            assert source == "project"
            assert "Custom PRD" in path.read_text()

    def test_adds_md_extension(self) -> None:
        """Should add .md extension if not provided."""
        path1, _ = resolve_template_path("prd")
        path2, _ = resolve_template_path("prd.md")
        assert path1 == path2


class TestGetAllTemplateNames:
    """Test getting all available template names."""

    def test_returns_bundled_templates(self) -> None:
        """Should return bundled template names."""
        names = get_all_template_names()
        assert "prd" in names
        assert "tdd" in names
        assert "rfc" in names
        assert "adr" in names
        assert "security-review" in names

    def test_returns_at_least_5_templates(self) -> None:
        """Should have at least 5 bundled templates."""
        names = get_all_template_names()
        assert len(names) >= 5


class TestParseTemplateFrontmatter:
    """Test frontmatter parsing."""

    def test_parse_valid_frontmatter(self) -> None:
        """Should parse valid frontmatter."""
        content = """---
name: test
version: "1.0"
checklist:
  - Item 1
  - Item 2
---

# Template Content
"""
        result = parse_template_frontmatter(content, "test.md")
        assert result.is_ok

        metadata, body = result.value
        assert metadata.name == "test"
        assert metadata.checklist == ("Item 1", "Item 2")
        assert "# Template Content" in body

    def test_no_frontmatter(self) -> None:
        """Should handle content without frontmatter."""
        content = "# Just Content\n\nNo frontmatter here."
        result = parse_template_frontmatter(content, "test.md")
        assert result.is_ok

        metadata, body = result.value
        assert metadata.name == "Test"  # From filename
        assert body == content

    def test_malformed_frontmatter(self) -> None:
        """Should error on malformed frontmatter."""
        content = """---
name: test
# No closing ---
"""
        result = parse_template_frontmatter(content, "test.md")
        assert result.is_err
        assert "closing" in result.error.lower()


class TestLoadTemplate:
    """Test template loading."""

    def test_load_existing_template(self) -> None:
        """Should load an existing template."""
        result = load_template("prd")
        assert result.is_ok

        metadata, content = result.value
        assert metadata.name == "prd"
        assert "---" in content  # Should include frontmatter

    def test_load_nonexistent_template(self) -> None:
        """Should error for nonexistent template."""
        result = load_template("nonexistent-12345")
        assert result.is_err
        assert "not found" in result.error


class TestLoadTemplateBody:
    """Test template body loading."""

    def test_load_body_without_frontmatter(self) -> None:
        """Should return body without frontmatter."""
        result = load_template_body("prd")
        assert result.is_ok

        metadata, body = result.value
        assert metadata.name == "prd"
        assert not body.startswith("---")


class TestDetectTemplateType:
    """Test template type auto-detection."""

    def test_detect_prd_from_content(self) -> None:
        """Should detect PRD from content."""
        content = """# Feature PRD

## Problem Statement

This is the problem we're solving.

## User Stories

- As a user, I want...

## Success Metrics

How we measure success.
"""
        assert detect_template_type(content) == "prd"

    def test_detect_tdd_from_content(self) -> None:
        """Should detect TDD from content."""
        content = """# Technical Design Document

## Overview

What we're building.

## Architecture

The system architecture.

## Data Model

The data structures.

## API Contracts

The interfaces.
"""
        assert detect_template_type(content) == "tdd"

    def test_detect_rfc_from_content(self) -> None:
        """Should detect RFC from content."""
        content = """# Request for Comments: New Feature

## Summary

One paragraph summary.

## Motivation

Why are we doing this?

## Rationale

Why this approach?

## Drawbacks

What are the downsides?
"""
        assert detect_template_type(content) == "rfc"

    def test_detect_adr_from_content(self) -> None:
        """Should detect ADR from content."""
        content = """# Architecture Decision Record

## Status

Proposed

## Decision

We will use X.

## Consequences

What happens next.
"""
        assert detect_template_type(content) == "adr"

    def test_detect_from_frontmatter(self) -> None:
        """Should detect type from frontmatter name."""
        content = """---
name: tdd
---

# Some Content
"""
        assert detect_template_type(content) == "tdd"

    def test_unknown_content(self) -> None:
        """Should return None for unknown content."""
        content = "# Just a Random Document\n\nSome text."
        assert detect_template_type(content) is None


class TestBundledTemplates:
    """Test bundled templates exist and have content."""

    def test_bundled_directory_exists(self) -> None:
        """Bundled templates directory should exist."""
        assert TEMPLATES_BUNDLED.exists()
        assert TEMPLATES_BUNDLED.is_dir()

    @pytest.mark.parametrize("template", ["prd", "tdd", "rfc", "adr", "security-review"])
    def test_bundled_template_exists(self, template: str) -> None:
        """Each bundled template should exist."""
        path = TEMPLATES_BUNDLED / f"{template}.md"
        assert path.exists()
        content = path.read_text()
        assert len(content) > 100  # Should have substantial content
        assert "---" in content  # Should have frontmatter

    @pytest.mark.parametrize("template", ["prd", "tdd", "rfc", "adr", "security-review"])
    def test_bundled_template_has_frontmatter(self, template: str) -> None:
        """Each bundled template should have valid frontmatter."""
        path = TEMPLATES_BUNDLED / f"{template}.md"
        content = path.read_text()

        result = parse_template_frontmatter(content, f"{template}.md")
        assert result.is_ok

        metadata, _ = result.value
        assert metadata.name == template
        assert metadata.version


class TestPrewriteAssertions:
    """Test pre-write assertions loading and scope filtering."""

    def test_prewrite_assertions_exist(self) -> None:
        """Pre-write assertions file should exist."""
        from crucible.enforcement.assertions import resolve_assertion_file

        path, source = resolve_assertion_file("prewrite.yaml")
        assert path is not None
        assert path.exists()

    def test_prewrite_assertions_have_scope(self) -> None:
        """Pre-write assertions should have scope: prewrite."""
        from crucible.enforcement.assertions import load_assertion_file

        result = load_assertion_file("prewrite.yaml")
        assert result.is_ok

        for assertion in result.value.assertions:
            assert assertion.scope in ("prewrite", "all"), f"Assertion {assertion.id} should have prewrite scope"

    def test_prewrite_assertions_are_llm_only(self) -> None:
        """Pre-write assertions should all be LLM type."""
        from crucible.enforcement.assertions import load_assertion_file
        from crucible.enforcement.models import AssertionType

        result = load_assertion_file("prewrite.yaml")
        assert result.is_ok

        for assertion in result.value.assertions:
            assert assertion.type == AssertionType.LLM, f"Assertion {assertion.id} should be LLM type"


class TestSpecReviewerSkill:
    """Test spec-reviewer skill exists."""

    def test_skill_exists(self) -> None:
        """Spec-reviewer skill should exist."""
        from crucible.cli import resolve_skill

        path, source = resolve_skill("spec-reviewer")
        assert path is not None
        assert path.exists()
        assert source == "bundled"

    def test_skill_has_triggers(self) -> None:
        """Spec-reviewer skill should have relevant triggers."""
        from crucible.cli import resolve_skill

        path, _ = resolve_skill("spec-reviewer")
        content = path.read_text()

        assert "triggers:" in content
        assert "spec" in content.lower()
        assert "prd" in content.lower()
