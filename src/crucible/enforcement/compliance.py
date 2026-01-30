"""LLM-based compliance checking for assertions.

Uses Anthropic SDK to run compliance assertions against code.
Supports Sonnet (default) and Opus (for high-stakes assertions).
"""

import json
import os
from typing import Any

from crucible.enforcement.budget import (
    create_budget_state,
    estimate_assertion_tokens,
    prepare_llm_assertions,
)
from crucible.enforcement.models import (
    Assertion,
    AssertionType,
    BudgetState,
    ComplianceConfig,
    EnforcementFinding,
    LLMAssertionResult,
    OverflowBehavior,
)
from crucible.enforcement.patterns import matches_glob, matches_language

# Model ID mapping
MODEL_IDS = {
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
    "haiku": "claude-haiku-4-20250514",
}

# System prompt for compliance checking
SYSTEM_PROMPT = """You are a code compliance checker. Analyze the provided code against the compliance requirements.

Respond with a JSON object:
{
  "compliant": true/false,
  "findings": [
    {
      "line": <line_number or null>,
      "issue": "<description of the issue>",
      "severity": "error" | "warning" | "info"
    }
  ],
  "reasoning": "<brief explanation of your analysis>"
}

If the code is compliant, return compliant: true with an empty findings array.
If there are issues, return compliant: false with specific findings.
Be precise about line numbers when possible. Focus on actual compliance issues, not style preferences."""


def _load_api_key_from_config() -> str | None:
    """Try to load API key from config file.

    Checks (in order):
    1. ~/.config/crucible/secrets.yaml
    2. ~/.crucible/secrets.yaml (legacy)

    Returns:
        API key if found, None otherwise
    """
    from pathlib import Path

    import yaml

    config_paths = [
        Path.home() / ".config" / "crucible" / "secrets.yaml",
        Path.home() / ".crucible" / "secrets.yaml",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = yaml.safe_load(f) or {}
                    key = data.get("anthropic_api_key") or data.get("ANTHROPIC_API_KEY")
                    if key:
                        return key
            except Exception:
                pass  # Ignore malformed config files

    return None


def _get_anthropic_client() -> Any:
    """Get Anthropic client instance.

    Checks for API key in order:
    1. ANTHROPIC_API_KEY environment variable
    2. ~/.config/crucible/secrets.yaml
    3. ~/.crucible/secrets.yaml

    Returns:
        Anthropic client

    Raises:
        ImportError: If anthropic package is not installed
        ValueError: If API key not found in any location
    """
    try:
        import anthropic
    except ImportError as e:
        raise ImportError(
            "anthropic package is required for LLM compliance checking. "
            "Install with: pip install anthropic"
        ) from e

    # Try env var first (standard for CI)
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    # Fall back to config file (convenient for local dev)
    if not api_key:
        api_key = _load_api_key_from_config()

    if not api_key:
        raise ValueError(
            "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
            "or add to ~/.config/crucible/secrets.yaml:\n"
            "  anthropic_api_key: sk-ant-..."
        )

    return anthropic.Anthropic(api_key=api_key)


def _build_user_prompt(assertion: Assertion, file_path: str, content: str) -> str:
    """Build user prompt for compliance check.

    Args:
        assertion: The assertion to check
        file_path: Path to the file being checked
        content: File content

    Returns:
        Formatted user prompt
    """
    return f"""## File: {file_path}

## Compliance Requirements
{assertion.compliance}

## Code to Analyze
```
{content}
```

Analyze this code against the compliance requirements and respond with JSON."""


def _parse_llm_response(
    response_text: str,
    assertion: Assertion,
    file_path: str,
) -> tuple[list[EnforcementFinding], str | None]:
    """Parse LLM response into findings.

    Args:
        response_text: Raw response from LLM
        assertion: The assertion that was checked
        file_path: Path to the file

    Returns:
        Tuple of (findings, reasoning)
    """
    findings: list[EnforcementFinding] = []
    reasoning = None

    try:
        # Try to extract JSON from response
        # Handle markdown code blocks
        text = response_text.strip()
        if text.startswith("```"):
            # Remove markdown code block
            lines = text.split("\n")
            # Find first and last ``` lines
            start = 0
            end = len(lines)
            for i, line in enumerate(lines):
                if line.startswith("```") and i == 0:
                    start = i + 1
                elif line.startswith("```") and i > 0:
                    end = i
                    break
            text = "\n".join(lines[start:end])

        data = json.loads(text)

        reasoning = data.get("reasoning")
        is_compliant = data.get("compliant", True)

        if not is_compliant and "findings" in data:
            for finding_data in data["findings"]:
                line_num = finding_data.get("line")
                issue = finding_data.get("issue", "Compliance issue detected")
                severity = finding_data.get("severity", assertion.severity)

                # Validate severity
                if severity not in ("error", "warning", "info"):
                    severity = assertion.severity

                location = f"{file_path}:{line_num}" if line_num else file_path

                findings.append(
                    EnforcementFinding(
                        assertion_id=assertion.id,
                        message=issue,
                        severity=severity,  # type: ignore[arg-type]
                        priority=assertion.priority,
                        location=location,
                        source="llm",
                        llm_reasoning=reasoning,
                    )
                )

    except (json.JSONDecodeError, KeyError, TypeError):
        # If we can't parse the response, create a single finding with the raw response
        findings.append(
            EnforcementFinding(
                assertion_id=assertion.id,
                message=f"LLM compliance check failed to parse: {response_text[:200]}...",
                severity="warning",
                priority=assertion.priority,
                location=file_path,
                source="llm",
            )
        )

    return findings, reasoning


def run_single_assertion(
    assertion: Assertion,
    file_path: str,
    content: str,
    config: ComplianceConfig,
) -> LLMAssertionResult:
    """Run a single LLM assertion against file content.

    Args:
        assertion: The assertion to run
        file_path: Path to the file
        content: File content
        config: Compliance configuration

    Returns:
        LLMAssertionResult with findings
    """
    if assertion.type != AssertionType.LLM:
        return LLMAssertionResult(
            assertion_id=assertion.id,
            passed=True,
            findings=(),
            tokens_used=0,
            model_used="",
            error="Not an LLM assertion",
        )

    # Determine model to use
    model_name = assertion.model or config.model
    model_id = MODEL_IDS.get(model_name, MODEL_IDS["sonnet"])

    try:
        client = _get_anthropic_client()

        user_prompt = _build_user_prompt(assertion, file_path, content)

        response = client.messages.create(
            model=model_id,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract text from response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        # Calculate tokens used
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        # Parse response
        findings, reasoning = _parse_llm_response(response_text, assertion, file_path)

        return LLMAssertionResult(
            assertion_id=assertion.id,
            passed=len(findings) == 0,
            findings=tuple(findings),
            tokens_used=tokens_used,
            model_used=model_name,
        )

    except ImportError as e:
        return LLMAssertionResult(
            assertion_id=assertion.id,
            passed=True,  # Don't fail on missing dependency
            findings=(),
            tokens_used=0,
            model_used=model_name,
            error=str(e),
        )
    except ValueError as e:
        return LLMAssertionResult(
            assertion_id=assertion.id,
            passed=True,  # Don't fail on missing API key
            findings=(),
            tokens_used=0,
            model_used=model_name,
            error=str(e),
        )
    except Exception as e:
        return LLMAssertionResult(
            assertion_id=assertion.id,
            passed=True,  # Don't fail on API errors
            findings=(),
            tokens_used=0,
            model_used=model_name,
            error=f"API error: {e}",
        )


def filter_applicable_assertions(
    assertions: list[Assertion],
    file_path: str,
) -> list[Assertion]:
    """Filter assertions to those applicable to the given file.

    Args:
        assertions: All LLM assertions
        file_path: File path to check

    Returns:
        Assertions applicable to this file
    """
    applicable: list[Assertion] = []

    for assertion in assertions:
        # Check language applicability
        if assertion.languages and not matches_language(file_path, assertion.languages):
            continue

        # Check glob applicability
        if assertion.applicability and not matches_glob(
            file_path,
            assertion.applicability.glob,
            assertion.applicability.exclude,
        ):
            continue

        applicable.append(assertion)

    return applicable


def run_llm_assertions(
    file_path: str,
    content: str,
    assertions: list[Assertion],
    config: ComplianceConfig,
) -> tuple[list[EnforcementFinding], BudgetState, list[str]]:
    """Run LLM assertions against a file.

    Args:
        file_path: Path to the file
        content: File content
        assertions: All assertions (will filter to LLM type)
        config: Compliance configuration

    Returns:
        Tuple of (findings, budget_state, errors)
    """
    if not config.enabled:
        return [], create_budget_state(config), []

    all_findings: list[EnforcementFinding] = []
    errors: list[str] = []

    # Prepare assertions (filter, sort, select within budget)
    to_run, budget_state = prepare_llm_assertions(
        assertions,
        len(content),
        config,
    )

    # Filter to applicable assertions for this file
    applicable = filter_applicable_assertions(to_run, file_path)

    # Run each applicable assertion
    for assertion in applicable:
        # Check if we still have budget
        estimated = estimate_assertion_tokens(assertion, len(content))
        if budget_state.total_budget > 0 and budget_state.tokens_used + estimated > budget_state.total_budget:
            budget_state.skip(assertion.id)

            if config.overflow_behavior == OverflowBehavior.FAIL:
                errors.append(
                    f"Token budget exceeded before running '{assertion.id}'. "
                    f"Used: {budget_state.tokens_used}, Budget: {budget_state.total_budget}"
                )
                break
            elif config.overflow_behavior == OverflowBehavior.WARN:
                errors.append(
                    f"Skipped '{assertion.id}' due to token budget. "
                    f"Used: {budget_state.tokens_used}, Budget: {budget_state.total_budget}"
                )
            continue

        # Run the assertion
        result = run_single_assertion(assertion, file_path, content, config)

        # Update budget state
        budget_state.consume(result.tokens_used)

        # Collect findings
        all_findings.extend(result.findings)

        # Record errors
        if result.error:
            errors.append(f"{assertion.id}: {result.error}")

    return all_findings, budget_state, errors


def run_llm_assertions_batch(
    files: list[tuple[str, str]],
    assertions: list[Assertion],
    config: ComplianceConfig,
) -> tuple[list[EnforcementFinding], BudgetState, list[str]]:
    """Run LLM assertions against multiple files with shared budget.

    Args:
        files: List of (file_path, content) tuples
        assertions: All assertions
        config: Compliance configuration

    Returns:
        Tuple of (all_findings, budget_state, errors)
    """
    if not config.enabled:
        return [], create_budget_state(config), []

    all_findings: list[EnforcementFinding] = []
    all_errors: list[str] = []

    # Calculate total content length for budget estimation
    total_content_length = sum(len(content) for _, content in files)

    # Prepare assertions with total budget
    to_run, budget_state = prepare_llm_assertions(
        assertions,
        total_content_length // max(1, len(files)),  # Average per file
        config,
    )

    # Process each file
    for file_path, content in files:
        applicable = filter_applicable_assertions(to_run, file_path)

        for assertion in applicable:
            # Check budget before each assertion
            estimated = estimate_assertion_tokens(assertion, len(content))
            if budget_state.total_budget > 0 and budget_state.tokens_used + estimated > budget_state.total_budget:
                budget_state.skip(assertion.id)

                if config.overflow_behavior == OverflowBehavior.FAIL:
                    all_errors.append(
                        f"Token budget exceeded at '{file_path}' before '{assertion.id}'"
                    )
                    return all_findings, budget_state, all_errors
                elif config.overflow_behavior == OverflowBehavior.WARN:
                    all_errors.append(
                        f"Skipped '{assertion.id}' on '{file_path}' due to budget"
                    )
                continue

            result = run_single_assertion(assertion, file_path, content, config)
            budget_state.consume(result.tokens_used)
            all_findings.extend(result.findings)

            if result.error:
                all_errors.append(f"{file_path}:{assertion.id}: {result.error}")

    return all_findings, budget_state, all_errors
