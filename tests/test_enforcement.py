"""Tests for enforcement module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from crucible.enforcement.assertions import (
    _load_assertion_file_cached,
    clear_assertion_cache,
    get_all_assertion_files,
    load_assertion_file,
    load_assertions,
    resolve_assertion_file,
)
from crucible.enforcement.models import AssertionType, Priority
from crucible.enforcement.patterns import (
    find_pattern_matches,
    is_suppressed,
    matches_glob,
    matches_language,
    parse_suppressions,
    run_pattern_assertions,
)


class TestAssertionParsing:
    """Test assertion file parsing."""

    def test_parse_valid_assertion_file(self, tmp_path: Path) -> None:
        """Should parse a valid assertion file."""
        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)
        (assertions_dir / "test.yaml").write_text("""
version: "0.4"
name: test-rules
description: Test assertions

assertions:
  - id: no-let
    type: pattern
    pattern: "\\\\blet\\\\s+\\\\w+"
    message: "Avoid let"
    severity: warning
    priority: high
    languages: [typescript, javascript]
""")

        with patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir):
            result = load_assertion_file("test.yaml")
            assert result.is_ok
            file = result.value
            assert file.name == "test-rules"
            assert file.version == "0.4"
            assert len(file.assertions) == 1
            assert file.assertions[0].id == "no-let"
            assert file.assertions[0].type == AssertionType.PATTERN
            assert file.assertions[0].priority == Priority.HIGH

    def test_parse_assertion_with_applicability(self, tmp_path: Path) -> None:
        """Should parse assertion with applicability config."""
        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)
        (assertions_dir / "test.yaml").write_text("""
version: "0.4"
name: test

assertions:
  - id: api-rule
    type: pattern
    pattern: "foo"
    message: "Found foo"
    severity: error
    applicability:
      glob: "**/api/**/*.ts"
      exclude:
        - "**/test/**"
        - "**/*.test.ts"
""")

        with patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir):
            result = load_assertion_file("test.yaml")
            assert result.is_ok
            assertion = result.value.assertions[0]
            assert assertion.applicability is not None
            assert assertion.applicability.glob == "**/api/**/*.ts"
            assert "**/test/**" in assertion.applicability.exclude

    def test_error_missing_pattern(self, tmp_path: Path) -> None:
        """Should error when pattern assertion missing pattern field."""
        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)
        (assertions_dir / "test.yaml").write_text("""
assertions:
  - id: bad-rule
    type: pattern
    message: "Missing pattern"
""")

        with patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir):
            result = load_assertion_file("test.yaml")
            assert result.is_err
            assert "missing required 'pattern' field" in result.error

    def test_error_missing_id(self, tmp_path: Path) -> None:
        """Should error when assertion missing id."""
        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)
        (assertions_dir / "test.yaml").write_text("""
assertions:
  - type: pattern
    pattern: "foo"
    message: "Missing id"
""")

        with patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir):
            result = load_assertion_file("test.yaml")
            assert result.is_err
            assert "missing required 'id' field" in result.error

    def test_error_duplicate_ids(self, tmp_path: Path) -> None:
        """Should error on duplicate assertion IDs."""
        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)
        (assertions_dir / "test.yaml").write_text("""
assertions:
  - id: same-id
    type: pattern
    pattern: "foo"
    message: "First"
  - id: same-id
    type: pattern
    pattern: "bar"
    message: "Second"
""")

        with patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir):
            result = load_assertion_file("test.yaml")
            assert result.is_err
            assert "duplicate assertion ID" in result.error

    def test_defaults_for_optional_fields(self, tmp_path: Path) -> None:
        """Should use defaults for optional fields."""
        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)
        (assertions_dir / "test.yaml").write_text("""
assertions:
  - id: minimal
    type: pattern
    pattern: "foo"
    message: "Found foo"
""")

        with patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir):
            result = load_assertion_file("test.yaml")
            assert result.is_ok
            assertion = result.value.assertions[0]
            assert assertion.severity == "warning"  # Default
            assert assertion.priority == Priority.MEDIUM  # Default
            assert assertion.languages == ()  # Default empty


class TestCascadeResolution:
    """Test cascade resolution for assertion files."""

    def test_project_takes_priority(self, tmp_path: Path) -> None:
        """Project assertions should override user/bundled."""
        project_dir = tmp_path / ".crucible" / "assertions"
        user_dir = tmp_path / "user" / "assertions"
        project_dir.mkdir(parents=True)
        user_dir.mkdir(parents=True)

        (project_dir / "rules.yaml").write_text("assertions: []")
        (user_dir / "rules.yaml").write_text("assertions: []")

        with (
            patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", project_dir),
            patch("crucible.enforcement.assertions.ASSERTIONS_USER", user_dir),
        ):
            path, source = resolve_assertion_file("rules.yaml")
            assert source == "project"
            assert path is not None

    def test_user_takes_priority_over_bundled(self, tmp_path: Path) -> None:
        """User assertions should override bundled."""
        user_dir = tmp_path / "user" / "assertions"
        bundled_dir = tmp_path / "bundled"
        user_dir.mkdir(parents=True)
        bundled_dir.mkdir(parents=True)

        (user_dir / "rules.yaml").write_text("assertions: []")
        (bundled_dir / "rules.yaml").write_text("assertions: []")

        with (
            patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", tmp_path / "nonexistent"),
            patch("crucible.enforcement.assertions.ASSERTIONS_USER", user_dir),
            patch("crucible.enforcement.assertions.ASSERTIONS_BUNDLED", bundled_dir),
        ):
            path, source = resolve_assertion_file("rules.yaml")
            assert source == "user"

    def test_nonexistent_returns_none(self, tmp_path: Path) -> None:
        """Non-existent file should return None."""
        with (
            patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", tmp_path / "nonexistent"),
            patch("crucible.enforcement.assertions.ASSERTIONS_USER", tmp_path / "nonexistent"),
            patch("crucible.enforcement.assertions.ASSERTIONS_BUNDLED", tmp_path / "nonexistent"),
        ):
            path, source = resolve_assertion_file("does-not-exist.yaml")
            assert path is None
            assert source == ""


class TestPatternMatching:
    """Test pattern matching functionality."""

    def test_find_single_match(self) -> None:
        """Should find a single pattern match."""
        content = "let x = 1;\nconst y = 2;"
        matches = find_pattern_matches("test.ts", content, r"\blet\s+\w+")
        assert len(matches) == 1
        assert matches[0].line == 1
        assert matches[0].match_text == "let x"

    def test_find_multiple_matches(self) -> None:
        """Should find multiple pattern matches."""
        content = "let x = 1;\nlet y = 2;\nconst z = 3;"
        matches = find_pattern_matches("test.ts", content, r"\blet\s+\w+")
        assert len(matches) == 2
        assert matches[0].line == 1
        assert matches[1].line == 2

    def test_find_matches_with_column(self) -> None:
        """Should report correct column numbers."""
        content = "const foo = let bar = 1;"
        matches = find_pattern_matches("test.ts", content, r"\blet\s+\w+")
        assert len(matches) == 1
        assert matches[0].column == 13  # 1-indexed, after "const foo = "

    def test_invalid_pattern_returns_empty(self) -> None:
        """Invalid regex should return empty list."""
        content = "some content"
        matches = find_pattern_matches("test.ts", content, r"[invalid(regex")
        assert matches == []


class TestInlineSuppression:
    """Test inline suppression parsing."""

    def test_parse_single_rule_suppression(self) -> None:
        """Should parse single rule suppression."""
        content = "// crucible-ignore: no-let\nlet x = 1;"
        suppressions = parse_suppressions(content)
        assert len(suppressions) == 1
        assert "no-let" in suppressions[0].rule_ids
        assert not suppressions[0].applies_to_next_line

    def test_parse_multiple_rules_suppression(self) -> None:
        """Should parse multiple rules in one comment."""
        content = "// crucible-ignore: no-let, no-any\nlet x: any = 1;"
        suppressions = parse_suppressions(content)
        assert len(suppressions) == 1
        assert "no-let" in suppressions[0].rule_ids
        assert "no-any" in suppressions[0].rule_ids

    def test_parse_next_line_suppression(self) -> None:
        """Should parse next-line suppression."""
        content = "// crucible-ignore-next-line: no-let\nlet x = 1;"
        suppressions = parse_suppressions(content)
        assert len(suppressions) == 1
        assert suppressions[0].applies_to_next_line

    def test_parse_suppression_with_reason(self) -> None:
        """Should parse suppression with reason."""
        content = "// crucible-ignore: no-let -- loop counter\nlet i = 0;"
        suppressions = parse_suppressions(content)
        assert len(suppressions) == 1
        assert suppressions[0].reason == "loop counter"

    def test_parse_python_style_comment(self) -> None:
        """Should parse Python-style # comments."""
        content = "# crucible-ignore: no-eval\neval(code)"
        suppressions = parse_suppressions(content)
        assert len(suppressions) == 1
        assert "no-eval" in suppressions[0].rule_ids

    def test_is_suppressed_same_line(self) -> None:
        """Should detect suppression on same line."""
        content = "let x = 1; // crucible-ignore: no-let"
        suppressions = parse_suppressions(content)
        assert is_suppressed(1, "no-let", suppressions) is not None

    def test_is_suppressed_next_line(self) -> None:
        """Should detect suppression on next line."""
        content = "// crucible-ignore-next-line: no-let\nlet x = 1;"
        suppressions = parse_suppressions(content)
        assert is_suppressed(2, "no-let", suppressions) is not None
        assert is_suppressed(1, "no-let", suppressions) is None

    def test_is_suppressed_case_insensitive(self) -> None:
        """Suppression should be case insensitive."""
        content = "// crucible-ignore: No-Let\nlet x = 1;"
        suppressions = parse_suppressions(content)
        assert is_suppressed(1, "NO-LET", suppressions) is not None
        assert is_suppressed(1, "no-let", suppressions) is not None


class TestLanguageMatching:
    """Test language filtering."""

    def test_matches_typescript(self) -> None:
        """Should match typescript files."""
        assert matches_language("src/app.ts", ("typescript",))
        assert matches_language("src/Component.tsx", ("typescript",))
        assert not matches_language("src/app.js", ("typescript",))

    def test_matches_javascript(self) -> None:
        """Should match javascript files."""
        assert matches_language("src/app.js", ("javascript",))
        assert matches_language("src/app.jsx", ("javascript",))
        assert matches_language("src/app.mjs", ("javascript",))

    def test_matches_multiple_languages(self) -> None:
        """Should match any of multiple languages."""
        assert matches_language("src/app.ts", ("typescript", "javascript"))
        assert matches_language("src/app.js", ("typescript", "javascript"))

    def test_empty_languages_matches_all(self) -> None:
        """Empty languages tuple should match all files."""
        assert matches_language("src/app.ts", ())
        assert matches_language("src/app.py", ())
        assert matches_language("README.md", ())


class TestGlobMatching:
    """Test glob pattern matching."""

    def test_matches_simple_glob(self) -> None:
        """Should match simple glob patterns."""
        assert matches_glob("src/api/users.ts", "**/api/**/*.ts")
        assert not matches_glob("src/utils/helpers.ts", "**/api/**/*.ts")

    def test_excludes_patterns(self) -> None:
        """Should exclude specified patterns."""
        assert not matches_glob(
            "src/api/users.test.ts",
            "**/api/**/*.ts",
            ("**/*.test.ts",),
        )
        assert matches_glob(
            "src/api/users.ts",
            "**/api/**/*.ts",
            ("**/*.test.ts",),
        )

    def test_none_glob_matches_all(self) -> None:
        """None glob should match all files."""
        assert matches_glob("any/file.py", None)
        assert matches_glob("another/file.ts", None)

    def test_exclude_without_glob(self) -> None:
        """Should apply excludes even without glob."""
        assert not matches_glob("src/test/file.ts", None, ("**/test/**",))
        assert matches_glob("src/main/file.ts", None, ("**/test/**",))


class TestRunPatternAssertions:
    """Test running pattern assertions against files."""

    @pytest.fixture
    def sample_assertions(self) -> list:
        """Create sample assertions for testing."""
        from crucible.enforcement.models import Applicability, Assertion, AssertionType, Priority

        return [
            Assertion(
                id="no-let",
                type=AssertionType.PATTERN,
                pattern=r"\blet\s+\w+",
                message="Avoid let",
                severity="warning",
                priority=Priority.MEDIUM,
                languages=("typescript", "javascript"),
            ),
            Assertion(
                id="no-any",
                type=AssertionType.PATTERN,
                pattern=r":\s*any\b",
                message="Avoid any",
                severity="error",
                priority=Priority.HIGH,
                languages=("typescript",),
            ),
            Assertion(
                id="llm-check",
                type=AssertionType.LLM,
                pattern=None,
                message="LLM check",
                severity="info",
                priority=Priority.LOW,
                compliance="Is this secure?",
            ),
        ]

    def test_finds_pattern_violations(self, sample_assertions: list) -> None:
        """Should find pattern violations."""
        content = "let x = 1;\nconst y: any = 2;"
        findings, checked, skipped = run_pattern_assertions(
            "test.ts", content, sample_assertions
        )
        # Filter to unsuppressed findings
        violations = [f for f in findings if not f.suppressed]
        assert len(violations) == 2
        assert any(f.assertion_id == "no-let" for f in violations)
        assert any(f.assertion_id == "no-any" for f in violations)

    def test_skips_llm_assertions(self, sample_assertions: list) -> None:
        """Should skip LLM assertions and report count."""
        content = "const x = 1;"
        findings, checked, skipped = run_pattern_assertions(
            "test.ts", content, sample_assertions
        )
        assert skipped == 1  # The LLM assertion

    def test_respects_language_filter(self, sample_assertions: list) -> None:
        """Should skip assertions for non-matching languages."""
        content = "let x: any = 1;"  # Would match both rules
        findings, checked, skipped = run_pattern_assertions(
            "test.js", content, sample_assertions  # .js not .ts
        )
        # no-any only applies to typescript
        violations = [f for f in findings if not f.suppressed]
        assert len(violations) == 1
        assert violations[0].assertion_id == "no-let"

    def test_respects_suppression(self, sample_assertions: list) -> None:
        """Should mark suppressed findings."""
        # Use next-line suppression since the let is on line 2
        content = "// crucible-ignore-next-line: no-let\nlet x = 1;"
        findings, _, _ = run_pattern_assertions("test.ts", content, sample_assertions)
        let_findings = [f for f in findings if f.assertion_id == "no-let"]
        assert len(let_findings) == 1
        assert let_findings[0].suppressed


class TestAssertionCaching:
    """Test assertion loading cache."""

    def test_cache_returns_same_result(self, tmp_path: Path) -> None:
        """Cached results should be identical."""
        clear_assertion_cache()

        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)
        (assertions_dir / "test.yaml").write_text("""
assertions:
  - id: test-rule
    type: pattern
    pattern: "test"
    message: "Test message"
""")

        with patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir):
            result1 = load_assertion_file("test.yaml")
            result2 = load_assertion_file("test.yaml")

            assert result1.is_ok
            assert result2.is_ok
            # Should have same assertions (cached)
            assert result1.value.assertions == result2.value.assertions

    def test_cache_clear_works(self, tmp_path: Path) -> None:
        """Cache clear should allow reloading."""
        clear_assertion_cache()

        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)
        yaml_path = assertions_dir / "test.yaml"
        yaml_path.write_text("""
assertions:
  - id: rule-v1
    type: pattern
    pattern: "v1"
    message: "Version 1"
""")

        with patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir):
            result1 = load_assertion_file("test.yaml")
            assert result1.is_ok
            assert result1.value.assertions[0].id == "rule-v1"

            # Update file
            yaml_path.write_text("""
assertions:
  - id: rule-v2
    type: pattern
    pattern: "v2"
    message: "Version 2"
""")

            # Without cache clear, still returns v1
            result2 = load_assertion_file("test.yaml")
            assert result2.value.assertions[0].id == "rule-v1"

            # After cache clear, returns v2
            clear_assertion_cache()
            result3 = load_assertion_file("test.yaml")
            assert result3.value.assertions[0].id == "rule-v2"


class TestLoadAssertions:
    """Test bulk assertion loading."""

    def test_loads_all_files(self, tmp_path: Path) -> None:
        """Should load assertions from all files."""
        clear_assertion_cache()

        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)

        (assertions_dir / "security.yaml").write_text("""
assertions:
  - id: security-rule
    type: pattern
    pattern: "secret"
    message: "Found secret"
""")
        (assertions_dir / "style.yaml").write_text("""
assertions:
  - id: style-rule
    type: pattern
    pattern: "style"
    message: "Style issue"
""")

        with (
            patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir),
            patch("crucible.enforcement.assertions.ASSERTIONS_USER", tmp_path / "nonexistent"),
            patch("crucible.enforcement.assertions.ASSERTIONS_BUNDLED", tmp_path / "nonexistent"),
        ):
            assertions, errors = load_assertions()
            assert len(errors) == 0
            assert len(assertions) == 2
            ids = {a.id for a in assertions}
            assert "security-rule" in ids
            assert "style-rule" in ids

    def test_sorts_by_priority(self, tmp_path: Path) -> None:
        """Should sort assertions by priority (critical first)."""
        clear_assertion_cache()

        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)

        (assertions_dir / "test.yaml").write_text("""
assertions:
  - id: low-priority
    type: pattern
    pattern: "low"
    message: "Low"
    priority: low
  - id: critical-priority
    type: pattern
    pattern: "critical"
    message: "Critical"
    priority: critical
  - id: high-priority
    type: pattern
    pattern: "high"
    message: "High"
    priority: high
""")

        with (
            patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir),
            patch("crucible.enforcement.assertions.ASSERTIONS_USER", tmp_path / "nonexistent"),
            patch("crucible.enforcement.assertions.ASSERTIONS_BUNDLED", tmp_path / "nonexistent"),
        ):
            assertions, _ = load_assertions()
            assert assertions[0].id == "critical-priority"
            assert assertions[1].id == "high-priority"
            assert assertions[2].id == "low-priority"

    def test_reports_errors(self, tmp_path: Path) -> None:
        """Should report errors for invalid files."""
        clear_assertion_cache()

        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)

        (assertions_dir / "valid.yaml").write_text("""
assertions:
  - id: valid-rule
    type: pattern
    pattern: "valid"
    message: "Valid"
""")
        (assertions_dir / "invalid.yaml").write_text("""
assertions:
  - id: missing-pattern
    type: pattern
    message: "Missing pattern field"
""")

        with (
            patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT", assertions_dir),
            patch("crucible.enforcement.assertions.ASSERTIONS_USER", tmp_path / "nonexistent"),
            patch("crucible.enforcement.assertions.ASSERTIONS_BUNDLED", tmp_path / "nonexistent"),
        ):
            assertions, errors = load_assertions()
            assert len(assertions) == 1  # Only valid one loaded
            assert len(errors) == 1  # One error reported
            assert "missing required 'pattern' field" in errors[0]
