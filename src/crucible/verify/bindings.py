"""Verifier bindings: rule -> predicate, resolved through the cascade.

Same priority convention as every other crucible surface:
project (.crucible/) -> user (~/.claude/crucible/) -> bundled.
First binding found for a rule wins; a `disable:` entry in any file
removes the rule outright.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from crucible.verify.predicates import PREDICATES

VERIFIERS_PROJECT = Path(".crucible") / "verifiers.yaml"
VERIFIERS_USER = Path.home() / ".claude" / "crucible" / "verifiers.yaml"
VERIFIERS_BUNDLED = Path(__file__).resolve().parent / "bundled" / "verifiers.yaml"


@dataclass(frozen=True)
class VerifierBinding:
    rule: str
    predicate: str
    reason: str


def _load_file(path: Path) -> tuple[list[dict], list[str], list[str]]:
    """(entries, disables, errors) from one verifiers.yaml; empty on missing."""
    if not path.exists():
        return [], [], []
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except (yaml.YAMLError, OSError) as e:
        return [], [], [f"verifiers: failed to load {path}: {e}"]
    if not isinstance(data, dict):
        return [], [], [f"verifiers: {path} is not a mapping"]
    entries = [e for e in (data.get("verifiers") or []) if isinstance(e, dict)]
    disables = [str(d) for d in (data.get("disable") or [])]
    return entries, disables, []


def load_bindings() -> tuple[dict[str, VerifierBinding], list[str]]:
    """Resolve bindings through the cascade. Returns ({rule: binding}, errors)."""
    bindings: dict[str, VerifierBinding] = {}
    disables: set[str] = set()
    errors: list[str] = []

    for path in (VERIFIERS_PROJECT, VERIFIERS_USER, VERIFIERS_BUNDLED):
        entries, file_disables, file_errors = _load_file(path)
        errors.extend(file_errors)
        disables.update(file_disables)
        for entry in entries:
            rule = str(entry.get("rule", "")).strip()
            predicate = str(entry.get("predicate", "")).strip()
            reason = str(entry.get("reason", "")).strip()
            if not rule or not predicate:
                errors.append(f"verifiers: entry missing rule/predicate in {path}")
                continue
            if predicate not in PREDICATES:
                errors.append(
                    f"verifiers: unknown predicate '{predicate}' for rule "
                    f"'{rule}' in {path} — binding skipped"
                )
                continue
            if rule not in bindings:  # first found (highest priority) wins
                bindings[rule] = VerifierBinding(rule=rule, predicate=predicate, reason=reason)

    for rule in disables:
        bindings.pop(rule, None)
    return bindings, errors
