"""run_verification: apply bound predicates to findings, marking false
positives suppressed. Marks, never drops; unbound rules pass through;
every internal failure fails open toward showing the finding."""

from __future__ import annotations

import dataclasses
import os

from crucible.enforcement.models import EnforcementFinding
from crucible.models import ToolFinding
from crucible.verify.bindings import load_bindings
from crucible.verify.predicates import PREDICATES, FindingContext


def _split_location(location: str) -> tuple[str, int | None, int | None]:
    """'path:line:col' | 'path:line' | 'path' -> (path, line, col)."""
    parts = location.rsplit(":", 2)
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        return parts[0], int(parts[1]), int(parts[2])
    head = location.rsplit(":", 1)
    if len(head) == 2 and head[1].isdigit():
        return head[0], int(head[1]), None
    return location, None, None


def _read(path: str, repo_root: str | None,
          file_contents: dict[str, str] | None,
          cache: dict[str, str | None]) -> str | None:
    if file_contents is not None and path in file_contents:
        return file_contents[path]
    if path in cache:
        return cache[path]
    full = os.path.join(repo_root, path) if repo_root else path
    try:
        with open(full, encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        content = None
    cache[path] = content
    return content


def run_verification(
    tool_findings: list[ToolFinding],
    enforcement_findings: list[EnforcementFinding],
    repo_root: str | None = None,
    file_contents: dict[str, str] | None = None,
) -> tuple[list[ToolFinding], list[EnforcementFinding], list[str]]:
    bindings, errors = load_bindings()
    if not bindings:
        return tool_findings, enforcement_findings, errors

    cache: dict[str, str | None] = {}

    def verify(finding, rule_key: str, match_text: str | None):
        if finding.suppressed or rule_key not in bindings:
            return finding
        binding = bindings[rule_key]
        path, line, col = _split_location(finding.location)
        content = _read(path, repo_root, file_contents, cache)
        if content is None:
            return finding  # unreadable → fail open
        ctx = FindingContext(path=path, line=line, column=col, match_text=match_text)
        try:
            is_fp = PREDICATES[binding.predicate](ctx, content)
        except Exception:  # crucible-ignore: no-catch-exception -- fail-open boundary: a predicate bug must never hide a finding
            return finding
        if not is_fp:
            return finding
        return dataclasses.replace(
            finding,
            suppressed=True,
            suppression_reason=f"verifier:{binding.predicate} — {binding.reason}",
        )

    verified_tools = [
        verify(f, f"{f.tool}/{f.rule}", None) for f in tool_findings
    ]
    verified_enforcement = [
        verify(f, f.assertion_id, getattr(f, "match_text", None))
        for f in enforcement_findings
    ]
    return verified_tools, verified_enforcement, errors
