"""Opt-in LLM escalation tier: findings the deterministic verifier could
not decide get one adversarial pass — construct the strongest
counterargument; suppress only if it is materially stronger than the
finding's evidence. Structured outputs guarantee parseable verdicts."""

from __future__ import annotations

import dataclasses
import json
import os

from crucible.enforcement.compliance import MODEL_IDS, _get_anthropic_client
from crucible.enforcement.models import EnforcementFinding
from crucible.models import ToolFinding
from crucible.verify.core import _split_location

_VERDICT_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "suppress": {"type": "boolean"},
            "counterargument": {"type": "string"},
        },
        "required": ["suppress", "counterargument"],
        "additionalProperties": False,
    },
}

_SYSTEM = (
    "You are a code-review verifier. You receive one static-analysis "
    "finding plus file context. Construct the strongest counterargument "
    "that the finding is a false positive. Set suppress=true ONLY if that "
    "counterargument is materially stronger than the finding's evidence; "
    "when uncertain, set suppress=false — a shown false positive is "
    "cheaper than a hidden true positive."
)


def _context_snippet(content: str, line: int | None, radius: int = 10) -> str:
    lines = content.splitlines()
    if line is None:
        return "\n".join(lines[:40])
    lo, hi = max(0, line - 1 - radius), min(len(lines), line + radius)
    return "\n".join(f"{i + 1}: {text}" for i, text in enumerate(lines[lo:hi], start=lo))


def run_llm_verification(
    tool_findings: list[ToolFinding],
    enforcement_findings: list[EnforcementFinding],
    repo_root: str | None = None,
    model: str = "sonnet",
    token_budget: int = 10000,
) -> tuple[list[ToolFinding], list[EnforcementFinding], list[str]]:
    errors: list[str] = []
    try:
        client = _get_anthropic_client()
    except (ImportError, ValueError) as e:
        return tool_findings, enforcement_findings, [f"llm-verify unavailable: {e}"]

    model_id = MODEL_IDS.get(model, MODEL_IDS["sonnet"])
    spent = 0

    def verify(finding, rule_key: str):
        nonlocal spent
        if finding.suppressed:
            return finding
        if spent >= token_budget:
            return finding
        path, line, _ = _split_location(finding.location)
        full = os.path.join(repo_root, path) if repo_root else path
        try:
            with open(full, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return finding
        prompt = (
            f"Finding: [{rule_key}] {finding.message}\n"
            f"Location: {finding.location}\n\n"
            f"File context:\n{_context_snippet(content, line)}\n"
        )
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=1024,
                system=_SYSTEM,
                output_config={"format": _VERDICT_SCHEMA},
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:  # crucible-ignore: no-catch-exception -- fail-open boundary: API failures must never hide findings
            errors.append(f"llm-verify API error: {e}")
            spent = token_budget  # stop trying
            return finding
        spent += response.usage.input_tokens + response.usage.output_tokens
        if spent >= token_budget:
            errors.append(f"llm-verify budget exhausted ({spent}/{token_budget})")
        try:
            verdict = json.loads(response.content[0].text)
        except (ValueError, IndexError, AttributeError):
            return finding
        if not verdict.get("suppress"):
            return finding
        reason = str(verdict.get("counterargument", ""))[:200]
        return dataclasses.replace(
            finding, suppressed=True, suppression_reason=f"llm:{model} — {reason}")

    verified_tools = [verify(f, f"{f.tool}/{f.rule}") for f in tool_findings]
    verified_enf = [verify(f, f.assertion_id) for f in enforcement_findings]
    return verified_tools, verified_enf, errors
