"""Typed schema for policies/*.yaml.

The schema validates the load-bearing core (name, severity, hooks,
activation) and retains documentation sections (approval, recovery,
intentional_gaps, watched_files, rules, ...) raw in `extra` — policies
are docs-plus-contract, and the docs half stays free-form.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from crucible.errors import Result, err, ok

SEVERITIES = ("critical", "high", "medium", "low")

_CORE_KEYS = {"name", "description", "version", "severity", "hooks", "activated_by"}


@dataclass(frozen=True)
class PolicyHook:
    event: str
    matcher: str | None
    handler: str
    blocking: bool
    note: str | None


@dataclass(frozen=True)
class Policy:
    name: str
    description: str
    version: str
    severity: str
    hooks: tuple[PolicyHook, ...]
    activated_by_skills: tuple[str, ...]
    source_path: str
    extra: dict


def parse_policy(path: Path) -> Result[Policy, str]:
    """Parse one policy file. Errors as values, never exceptions."""
    try:
        data = yaml.safe_load(path.read_text())
    except (yaml.YAMLError, OSError) as e:
        return err(f"{path}: failed to load: {e}")
    if not isinstance(data, dict):
        return err(f"{path}: policy is not a mapping")

    name = str(data.get("name", "")).strip()
    if not name:
        return err(f"{path}: missing required field 'name'")
    description = str(data.get("description", "")).strip()
    if not description:
        return err(f"{path}: missing required field 'description'")
    severity = str(data.get("severity", "")).strip().lower()
    if severity not in SEVERITIES:
        return err(f"{path}: unknown severity '{severity}' (expected one of {SEVERITIES})")

    hooks: list[PolicyHook] = []
    for entry in data.get("hooks") or []:
        if not isinstance(entry, dict):
            return err(f"{path}: hooks entry is not a mapping")
        event = str(entry.get("event", "")).strip()
        handler = str(entry.get("handler", "")).strip()
        if not event or not handler:
            return err(f"{path}: hooks entry missing event/handler")
        hooks.append(
            PolicyHook(
                event=event,
                matcher=(str(entry["matcher"]) if entry.get("matcher") is not None else None),
                handler=handler,
                blocking=bool(entry.get("blocking", False)),
                note=(str(entry["note"]) if entry.get("note") is not None else None),
            )
        )

    activated = data.get("activated_by") or {}
    skills = tuple(str(s) for s in (activated.get("skills") or [])) if isinstance(activated, dict) else ()

    extra = {k: v for k, v in data.items() if k not in _CORE_KEYS}

    return ok(
        Policy(
            name=name,
            description=description,
            version=str(data.get("version", "")),
            severity=severity,
            hooks=tuple(hooks),
            activated_by_skills=skills,
            source_path=str(path),
            extra=extra,
        )
    )
