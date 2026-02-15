"""Pre-write review logic for specs and design documents.

Runs LLM assertions (no pattern assertions) against specifications
to catch gaps before implementation begins.
"""

from pathlib import Path

from crucible.enforcement.assertions import load_assertions
from crucible.enforcement.models import (
    AssertionType,
    ComplianceConfig,
)
from crucible.knowledge.loader import load_knowledge_file
from crucible.prewrite.loader import detect_template_type, load_template_body
from crucible.prewrite.models import PrewriteFinding, PrewriteResult

# System prompt specifically for pre-write review (specs/docs, not code)
PREWRITE_SYSTEM_PROMPT = """You are a specification reviewer. Analyze the provided document against the review requirements.

Respond with a JSON object:
{
  "compliant": true/false,
  "findings": [
    {
      "issue": "<description of the gap or concern>",
      "severity": "error" | "warning" | "info"
    }
  ],
  "reasoning": "<brief explanation of your analysis>"
}

If the specification is complete, return compliant: true with an empty findings array.
If there are gaps or concerns, return compliant: false with specific findings.
Focus on missing requirements, unclear scope, and unaddressed concerns - not writing style."""


def _build_prewrite_prompt(compliance_text: str, content: str) -> str:
    """Build user prompt for pre-write compliance check.

    Args:
        compliance_text: The compliance requirements from the assertion
        content: Document content

    Returns:
        Formatted user prompt
    """
    return f"""## Review Requirements
{compliance_text}

## Document to Analyze
{content}

Analyze this specification against the review requirements and respond with JSON."""


def _run_prewrite_assertion(
    assertion_id: str,
    compliance_text: str,
    content: str,
    severity: str,
    model: str = "sonnet",
) -> tuple[list[PrewriteFinding], int, str | None]:
    """Run a single pre-write assertion against document content.

    Args:
        assertion_id: ID of the assertion being run
        compliance_text: The compliance requirements
        content: Document content
        severity: Default severity for findings
        model: Model to use (sonnet/opus/haiku)

    Returns:
        Tuple of (findings, tokens_used, error)
    """
    import json
    import os
    import sys

    try:
        import anthropic
    except ImportError:
        return [], 0, "anthropic package not installed"

    # Load API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Try config file
        from crucible.enforcement.compliance import _load_api_key_from_config
        api_key = _load_api_key_from_config()

    if not api_key:
        return [], 0, "Anthropic API key not found"

    # Model mapping
    model_ids = {
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
        "haiku": "claude-haiku-4-20250514",
    }
    model_id = model_ids.get(model, model_ids["sonnet"])

    try:
        client = anthropic.Anthropic(api_key=api_key)
        user_prompt = _build_prewrite_prompt(compliance_text, content)

        response = client.messages.create(
            model=model_id,
            max_tokens=1024,
            system=PREWRITE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract text from response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        # Parse response
        findings: list[PrewriteFinding] = []

        try:
            # Handle markdown code blocks
            text = response_text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
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
                    issue = finding_data.get("issue", "Issue detected")
                    finding_severity = finding_data.get("severity", severity)

                    if finding_severity not in ("error", "warning", "info"):
                        finding_severity = severity

                    findings.append(
                        PrewriteFinding(
                            assertion_id=assertion_id,
                            message=issue,
                            severity=finding_severity,  # type: ignore[arg-type]
                            reasoning=reasoning,
                        )
                    )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Warning: Failed to parse LLM response for {assertion_id}: {e}", file=sys.stderr)

        return findings, tokens_used, None

    except Exception as e:
        return [], 0, f"API error: {e}"


def prewrite_review(
    path: str,
    template: str | None = None,
    skills: list[str] | None = None,
    compliance_config: ComplianceConfig | None = None,
) -> PrewriteResult:
    """Review a specification against pre-write assertions.

    Args:
        path: Path to the spec/PRD/TDD file
        template: Template type (auto-detect if None)
        skills: Skill overrides (auto-detect if None)
        compliance_config: LLM config (uses defaults if None)

    Returns:
        PrewriteResult with findings and metadata
    """
    config = compliance_config or ComplianceConfig()

    result = PrewriteResult(path=path, template=template)

    # Read document content
    try:
        content = Path(path).read_text()
    except OSError as e:
        result.errors.append(f"Failed to read file: {e}")
        return result

    # Auto-detect template type if not specified
    if template is None:
        template = detect_template_type(content)
        result.template = template

    # Load template metadata if available
    checklist: list[str] = []
    knowledge_to_load: set[str] = set()
    assertions_to_load: set[str] = set()

    if template:
        template_result = load_template_body(template)
        if template_result.is_ok:
            metadata, _ = template_result.value
            checklist = list(metadata.checklist)
            knowledge_to_load.update(metadata.knowledge)
            assertions_to_load.update(metadata.assertions)

    result.checklist = checklist

    # Load linked knowledge
    for filename in knowledge_to_load:
        knowledge_result = load_knowledge_file(filename)
        if knowledge_result.is_ok:
            result.knowledge_loaded.append(filename)

    # Load skills
    if skills:
        result.skills_loaded = list(skills)
    elif template:
        # Default skill for pre-write review
        result.skills_loaded = ["spec-reviewer"]

    # Load pre-write assertions
    all_assertions, load_errors = load_assertions()
    result.errors.extend(load_errors)

    # Filter to prewrite-scope LLM assertions only
    prewrite_assertions = [
        a for a in all_assertions
        if a.type == AssertionType.LLM and a.scope in ("prewrite", "all")
    ]

    # If specific assertion files requested, filter to those
    if assertions_to_load:
        # Reload with specific files
        specific_assertions, specific_errors = load_assertions(assertions_to_load)
        result.errors.extend(specific_errors)
        prewrite_assertions = [
            a for a in specific_assertions
            if a.type == AssertionType.LLM and a.scope in ("prewrite", "all")
        ]

    if not config.enabled:
        # LLM assertions disabled
        return result

    # Run assertions
    total_tokens = 0

    for assertion in prewrite_assertions:
        if not assertion.compliance:
            continue

        # Check budget
        if config.token_budget > 0 and total_tokens >= config.token_budget:
            result.errors.append(
                f"Token budget exhausted ({total_tokens}/{config.token_budget}). "
                f"Skipped remaining assertions."
            )
            break

        findings, tokens, error = _run_prewrite_assertion(
            assertion_id=assertion.id,
            compliance_text=assertion.compliance,
            content=content,
            severity=assertion.severity,
            model=assertion.model or config.model,
        )

        total_tokens += tokens

        if error:
            result.errors.append(f"{assertion.id}: {error}")
        else:
            result.findings.extend(findings)

    result.tokens_used = total_tokens

    return result


def format_prewrite_result(result: PrewriteResult) -> str:
    """Format pre-write review result for display.

    Args:
        result: PrewriteResult from prewrite_review

    Returns:
        Formatted string for output
    """
    parts: list[str] = ["# Pre-Write Review\n"]

    parts.append(f"**File:** `{result.path}`")
    if result.template:
        parts.append(f"**Template:** {result.template}")
    parts.append("")

    # Summary
    if result.findings:
        parts.append(f"**Findings:** {result.error_count} errors, {result.warning_count} warnings, {result.info_count} info")
    else:
        parts.append("**Findings:** None")

    if result.tokens_used > 0:
        parts.append(f"**Tokens used:** {result.tokens_used}")
    parts.append("")

    # Errors from loading
    if result.errors:
        parts.append("## Errors\n")
        for error in result.errors:
            parts.append(f"- {error}")
        parts.append("")

    # Findings by severity
    if result.findings:
        parts.append("## Findings\n")

        for severity in ["error", "warning", "info"]:
            severity_findings = [f for f in result.findings if f.severity == severity]
            if severity_findings:
                parts.append(f"### {severity.upper()} ({len(severity_findings)})\n")
                for f in severity_findings:
                    parts.append(f"- **[{f.assertion_id}]** {f.message}")
                    if f.reasoning:
                        parts.append(f"  - *Reasoning:* {f.reasoning}")
                parts.append("")

    # Checklist
    if result.checklist:
        parts.append("## Review Checklist\n")
        for item in result.checklist:
            parts.append(f"- [ ] {item}")
        parts.append("")

    # Knowledge loaded
    if result.knowledge_loaded:
        parts.append("## Knowledge Loaded\n")
        parts.append(f"Files: {', '.join(result.knowledge_loaded)}")
        parts.append("")

    # Skills loaded
    if result.skills_loaded:
        parts.append("## Skills Applied\n")
        parts.append(f"Skills: {', '.join(result.skills_loaded)}")
        parts.append("")

    # Pass/fail status
    parts.append("---\n")
    if result.passed:
        parts.append("**Status:** PASSED")
    else:
        parts.append(f"**Status:** FAILED ({result.error_count} errors)")

    return "\n".join(parts)
