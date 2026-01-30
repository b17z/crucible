"""Tests for LLM compliance checking module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from crucible.enforcement.budget import (
    create_budget_state,
    estimate_assertion_tokens,
    estimate_total_budget,
    filter_llm_assertions,
    prepare_llm_assertions,
    select_within_budget,
    sort_by_priority,
)
from crucible.enforcement.compliance import (
    MODEL_IDS,
    _build_user_prompt,
    _parse_llm_response,
    filter_applicable_assertions,
    run_llm_assertions,
    run_single_assertion,
)
from crucible.enforcement.models import (
    Applicability,
    Assertion,
    AssertionType,
    BudgetState,
    ComplianceConfig,
    LLMAssertionResult,
    OverflowBehavior,
    Priority,
)


class TestBudgetEstimation:
    """Test token budget estimation."""

    def test_estimate_single_assertion(self) -> None:
        """Should estimate tokens for a single LLM assertion."""
        assertion = Assertion(
            id="test-compliance",
            type=AssertionType.LLM,
            message="Test",
            severity="warning",
            priority=Priority.MEDIUM,
            compliance="Check that authentication uses secure methods.",
        )

        # 1000 characters of content
        estimated = estimate_assertion_tokens(assertion, 1000)

        # Should include base overhead + content + compliance prompt
        assert estimated > 200  # At least base overhead
        assert estimated < 1000  # Not unreasonably high

    def test_estimate_returns_zero_for_pattern(self) -> None:
        """Pattern assertions should return zero tokens."""
        assertion = Assertion(
            id="pattern-rule",
            type=AssertionType.PATTERN,
            pattern="foo",
            message="Test",
            severity="warning",
            priority=Priority.MEDIUM,
        )

        estimated = estimate_assertion_tokens(assertion, 1000)
        assert estimated == 0

    def test_estimate_total_budget(self) -> None:
        """Should estimate total tokens for multiple assertions."""
        assertions = [
            Assertion(
                id="llm-1",
                type=AssertionType.LLM,
                message="Test 1",
                severity="warning",
                priority=Priority.HIGH,
                compliance="Check 1",
            ),
            Assertion(
                id="llm-2",
                type=AssertionType.LLM,
                message="Test 2",
                severity="warning",
                priority=Priority.LOW,
                compliance="Check 2",
            ),
            Assertion(
                id="pattern",
                type=AssertionType.PATTERN,
                pattern="foo",
                message="Pattern",
                severity="warning",
                priority=Priority.MEDIUM,
            ),
        ]

        total = estimate_total_budget(assertions, 1000)

        # Should only count LLM assertions (2 of them)
        single_estimate = estimate_assertion_tokens(assertions[0], 1000)
        assert total >= 2 * single_estimate * 0.8  # Allow some variance


class TestPrioritySorting:
    """Test priority-based sorting."""

    def test_sort_by_priority(self) -> None:
        """Should sort assertions by priority (critical first)."""
        assertions = [
            Assertion(
                id="low", type=AssertionType.LLM, message="", severity="info",
                priority=Priority.LOW, compliance="check",
            ),
            Assertion(
                id="critical", type=AssertionType.LLM, message="", severity="error",
                priority=Priority.CRITICAL, compliance="check",
            ),
            Assertion(
                id="medium", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
            ),
            Assertion(
                id="high", type=AssertionType.LLM, message="", severity="error",
                priority=Priority.HIGH, compliance="check",
            ),
        ]

        sorted_assertions = sort_by_priority(assertions)

        assert sorted_assertions[0].id == "critical"
        assert sorted_assertions[1].id == "high"
        assert sorted_assertions[2].id == "medium"
        assert sorted_assertions[3].id == "low"


class TestBudgetSelection:
    """Test budget-constrained selection."""

    def test_select_within_budget(self) -> None:
        """Should select assertions within budget."""
        assertions = [
            Assertion(
                id="first", type=AssertionType.LLM, message="", severity="error",
                priority=Priority.CRITICAL, compliance="check",
            ),
            Assertion(
                id="second", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.HIGH, compliance="check",
            ),
            Assertion(
                id="third", type=AssertionType.LLM, message="", severity="info",
                priority=Priority.LOW, compliance="check",
            ),
        ]

        # Budget that only fits ~1 assertion
        selected, skipped = select_within_budget(assertions, 100, 300)

        assert len(selected) >= 1
        assert len(skipped) >= 0
        assert len(selected) + len(skipped) == 3

    def test_unlimited_budget_selects_all(self) -> None:
        """Budget of 0 should select all assertions."""
        assertions = [
            Assertion(
                id=f"rule-{i}", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
            )
            for i in range(5)
        ]

        selected, skipped = select_within_budget(assertions, 1000, 0)

        assert len(selected) == 5
        assert len(skipped) == 0


class TestFilterLLMAssertions:
    """Test filtering to LLM-only assertions."""

    def test_filters_to_llm_only(self) -> None:
        """Should filter out pattern assertions."""
        assertions = [
            Assertion(
                id="llm", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
            ),
            Assertion(
                id="pattern", type=AssertionType.PATTERN, pattern="foo",
                message="", severity="warning", priority=Priority.MEDIUM,
            ),
        ]

        filtered = filter_llm_assertions(assertions)

        assert len(filtered) == 1
        assert filtered[0].id == "llm"


class TestBudgetState:
    """Test BudgetState tracking."""

    def test_initial_state(self) -> None:
        """Should initialize with correct values."""
        state = BudgetState(total_budget=10000)

        assert state.total_budget == 10000
        assert state.tokens_used == 0
        assert state.assertions_run == 0
        assert state.assertions_skipped == 0
        assert not state.overflow_triggered
        assert state.skipped_assertions == []

    def test_consume_tokens(self) -> None:
        """Should track token consumption."""
        state = BudgetState(total_budget=10000)

        state.consume(500)
        assert state.tokens_used == 500
        assert state.assertions_run == 1
        assert state.tokens_remaining == 9500

        state.consume(300)
        assert state.tokens_used == 800
        assert state.assertions_run == 2

    def test_is_exhausted(self) -> None:
        """Should detect budget exhaustion."""
        state = BudgetState(total_budget=1000)

        assert not state.is_exhausted

        state.consume(1000)
        assert state.is_exhausted

    def test_skip_assertion(self) -> None:
        """Should track skipped assertions."""
        state = BudgetState(total_budget=1000)

        state.skip("rule-1")
        state.skip("rule-2")

        assert state.assertions_skipped == 2
        assert state.overflow_triggered
        assert "rule-1" in state.skipped_assertions
        assert "rule-2" in state.skipped_assertions

    def test_unlimited_budget_never_exhausted(self) -> None:
        """Budget of 0 (unlimited) should never be exhausted."""
        state = BudgetState(total_budget=0)

        state.consume(1000000)
        assert not state.is_exhausted


class TestComplianceConfig:
    """Test ComplianceConfig defaults and behavior."""

    def test_defaults(self) -> None:
        """Should have sensible defaults."""
        config = ComplianceConfig()

        assert config.enabled is True
        assert config.model == "sonnet"
        assert config.token_budget == 10000
        assert config.overflow_behavior == OverflowBehavior.WARN

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        config = ComplianceConfig(
            enabled=False,
            model="opus",
            token_budget=5000,
            overflow_behavior=OverflowBehavior.FAIL,
        )

        assert config.enabled is False
        assert config.model == "opus"
        assert config.token_budget == 5000
        assert config.overflow_behavior == OverflowBehavior.FAIL


class TestPrepareAssertions:
    """Test prepare_llm_assertions function."""

    def test_prepares_and_sorts(self) -> None:
        """Should filter, sort, and select within budget."""
        assertions = [
            Assertion(
                id="low", type=AssertionType.LLM, message="", severity="info",
                priority=Priority.LOW, compliance="check",
            ),
            Assertion(
                id="pattern", type=AssertionType.PATTERN, pattern="foo",
                message="", severity="warning", priority=Priority.MEDIUM,
            ),
            Assertion(
                id="high", type=AssertionType.LLM, message="", severity="error",
                priority=Priority.HIGH, compliance="check",
            ),
        ]
        config = ComplianceConfig(token_budget=0)  # Unlimited

        to_run, budget_state = prepare_llm_assertions(assertions, 1000, config)

        # Should only include LLM assertions, sorted by priority
        assert len(to_run) == 2
        assert to_run[0].id == "high"
        assert to_run[1].id == "low"


class TestParseResponse:
    """Test LLM response parsing."""

    def test_parse_compliant_response(self) -> None:
        """Should parse compliant response."""
        response = json.dumps({
            "compliant": True,
            "findings": [],
            "reasoning": "Code follows best practices.",
        })

        assertion = Assertion(
            id="test", type=AssertionType.LLM, message="", severity="warning",
            priority=Priority.MEDIUM, compliance="check",
        )

        findings, reasoning = _parse_llm_response(response, assertion, "test.py")

        assert len(findings) == 0
        assert reasoning == "Code follows best practices."

    def test_parse_non_compliant_response(self) -> None:
        """Should parse non-compliant response with findings."""
        response = json.dumps({
            "compliant": False,
            "findings": [
                {
                    "line": 10,
                    "issue": "Missing input validation",
                    "severity": "error",
                }
            ],
            "reasoning": "Found security issue.",
        })

        assertion = Assertion(
            id="security-check", type=AssertionType.LLM, message="Security issue",
            severity="warning", priority=Priority.HIGH, compliance="check",
        )

        findings, reasoning = _parse_llm_response(response, assertion, "test.py")

        assert len(findings) == 1
        assert findings[0].assertion_id == "security-check"
        assert findings[0].message == "Missing input validation"
        assert findings[0].location == "test.py:10"
        assert findings[0].source == "llm"

    def test_parse_markdown_wrapped_json(self) -> None:
        """Should handle markdown code blocks."""
        response = """```json
{
    "compliant": true,
    "findings": [],
    "reasoning": "All good."
}
```"""

        assertion = Assertion(
            id="test", type=AssertionType.LLM, message="", severity="warning",
            priority=Priority.MEDIUM, compliance="check",
        )

        findings, reasoning = _parse_llm_response(response, assertion, "test.py")

        assert len(findings) == 0
        assert reasoning == "All good."

    def test_parse_invalid_json(self) -> None:
        """Should handle invalid JSON gracefully."""
        response = "This is not valid JSON"

        assertion = Assertion(
            id="test", type=AssertionType.LLM, message="Check", severity="warning",
            priority=Priority.MEDIUM, compliance="check",
        )

        findings, reasoning = _parse_llm_response(response, assertion, "test.py")

        # Should create a single warning finding
        assert len(findings) == 1
        assert "failed to parse" in findings[0].message.lower()


class TestBuildPrompt:
    """Test prompt building."""

    def test_builds_user_prompt(self) -> None:
        """Should build proper user prompt."""
        assertion = Assertion(
            id="auth-check", type=AssertionType.LLM,
            message="Auth issue", severity="error", priority=Priority.CRITICAL,
            compliance="Check that passwords are hashed.",
        )

        prompt = _build_user_prompt(assertion, "auth.py", "def login(): pass")

        assert "auth.py" in prompt
        assert "Check that passwords are hashed." in prompt
        assert "def login(): pass" in prompt


class TestFilterApplicableAssertions:
    """Test applicability filtering."""

    def test_filters_by_language(self) -> None:
        """Should filter by language."""
        assertions = [
            Assertion(
                id="py-only", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
                languages=("python",),
            ),
            Assertion(
                id="ts-only", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
                languages=("typescript",),
            ),
        ]

        applicable = filter_applicable_assertions(assertions, "app.py")

        assert len(applicable) == 1
        assert applicable[0].id == "py-only"

    def test_filters_by_glob(self) -> None:
        """Should filter by glob pattern."""
        assertions = [
            Assertion(
                id="api-only", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
                applicability=Applicability(glob="**/api/**"),
            ),
            Assertion(
                id="any-file", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
            ),
        ]

        # File in api directory
        applicable = filter_applicable_assertions(assertions, "src/api/users.py")
        assert len(applicable) == 2

        # File not in api directory
        applicable = filter_applicable_assertions(assertions, "src/utils/helpers.py")
        assert len(applicable) == 1
        assert applicable[0].id == "any-file"


class TestRunSingleAssertion:
    """Test running a single LLM assertion."""

    def test_skips_non_llm_assertion(self) -> None:
        """Should skip non-LLM assertions."""
        assertion = Assertion(
            id="pattern", type=AssertionType.PATTERN, pattern="foo",
            message="", severity="warning", priority=Priority.MEDIUM,
        )
        config = ComplianceConfig()

        result = run_single_assertion(assertion, "test.py", "content", config)

        assert result.passed is True
        assert result.tokens_used == 0
        assert result.error == "Not an LLM assertion"

    @patch("crucible.enforcement.compliance._get_anthropic_client")
    def test_handles_missing_api_key(self, mock_get_client: MagicMock) -> None:
        """Should handle missing API key gracefully."""
        mock_get_client.side_effect = ValueError("ANTHROPIC_API_KEY not set")

        assertion = Assertion(
            id="test", type=AssertionType.LLM, message="", severity="warning",
            priority=Priority.MEDIUM, compliance="check",
        )
        config = ComplianceConfig()

        result = run_single_assertion(assertion, "test.py", "content", config)

        assert result.passed is True  # Don't fail on missing key
        assert "API_KEY" in result.error

    @patch("crucible.enforcement.compliance._get_anthropic_client")
    def test_uses_model_override(self, mock_get_client: MagicMock) -> None:
        """Should use assertion-specific model override."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"compliant": true, "findings": [], "reasoning": "ok"}')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        assertion = Assertion(
            id="high-stakes", type=AssertionType.LLM, message="", severity="error",
            priority=Priority.CRITICAL, compliance="check",
            model="opus",  # Override to opus
        )
        config = ComplianceConfig(model="sonnet")  # Default is sonnet

        result = run_single_assertion(assertion, "test.py", "content", config)

        # Should use opus model
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == MODEL_IDS["opus"]
        assert result.model_used == "opus"


class TestRunLLMAssertions:
    """Test running multiple LLM assertions."""

    def test_disabled_returns_empty(self) -> None:
        """Should return empty when disabled."""
        assertions = [
            Assertion(
                id="test", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
            ),
        ]
        config = ComplianceConfig(enabled=False)

        findings, budget_state, errors = run_llm_assertions(
            "test.py", "content", assertions, config
        )

        assert len(findings) == 0
        assert len(errors) == 0

    @patch("crucible.enforcement.compliance.run_single_assertion")
    def test_respects_budget(self, mock_run: MagicMock) -> None:
        """Should respect token budget."""
        mock_run.return_value = LLMAssertionResult(
            assertion_id="test",
            passed=True,
            findings=(),
            tokens_used=5000,
            model_used="sonnet",
        )

        assertions = [
            Assertion(
                id=f"rule-{i}", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
            )
            for i in range(5)
        ]
        config = ComplianceConfig(token_budget=8000)  # Only fits ~1-2 assertions

        findings, budget_state, errors = run_llm_assertions(
            "test.py", "x" * 100, assertions, config
        )

        # Should have hit budget limit
        assert budget_state.overflow_triggered or mock_run.call_count <= 2

    @patch("crucible.enforcement.compliance.run_single_assertion")
    def test_fail_on_overflow(self, mock_run: MagicMock) -> None:
        """Should fail when overflow_behavior is FAIL."""
        mock_run.return_value = LLMAssertionResult(
            assertion_id="test",
            passed=True,
            findings=(),
            tokens_used=5000,
            model_used="sonnet",
        )

        assertions = [
            Assertion(
                id=f"rule-{i}", type=AssertionType.LLM, message="", severity="warning",
                priority=Priority.MEDIUM, compliance="check",
            )
            for i in range(5)
        ]
        config = ComplianceConfig(
            token_budget=3000,
            overflow_behavior=OverflowBehavior.FAIL,
        )

        findings, budget_state, errors = run_llm_assertions(
            "test.py", "x" * 100, assertions, config
        )

        # Should have error about budget exceeded
        assert any("budget" in e.lower() for e in errors)


class TestModelIDs:
    """Test model ID mapping."""

    def test_all_models_have_ids(self) -> None:
        """Should have IDs for all supported models."""
        assert "sonnet" in MODEL_IDS
        assert "opus" in MODEL_IDS
        assert "haiku" in MODEL_IDS

    def test_model_ids_are_valid(self) -> None:
        """Model IDs should follow expected format."""
        for name, model_id in MODEL_IDS.items():
            assert "claude" in model_id
            assert name in model_id
