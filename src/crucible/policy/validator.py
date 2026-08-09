"""Policy loading (cascade) and validation.

Cascade: .crucible/policies/ (project) then bundled src/crucible/policies/;
first-found-wins by name — same convention as every other crucible surface.
Validation checks the load-bearing contract: handlers exist, referenced
skills resolve, and settings_integrity's watched_files stay in sync with
baselines.WATCHED_FILES (the yaml itself demands it).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crucible.policy.schema import Policy, parse_policy

POLICIES_PROJECT = Path(".crucible") / "policies"
POLICIES_BUNDLED = Path(__file__).resolve().parent.parent / "policies"

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PolicyIssue:
    policy: str
    field: str
    message: str
    level: str  # "error" | "warning"


def load_policies() -> tuple[list[Policy], list[str]]:
    """(policies, errors) through the cascade; parse errors never raise."""
    policies: dict[str, Policy] = {}
    errors: list[str] = []
    for directory in (POLICIES_PROJECT, POLICIES_BUNDLED):
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.yaml")):
            result = parse_policy(path)
            if result.is_err:
                errors.append(result.error)
                continue
            if result.value.name not in policies:  # first found wins
                policies[result.value.name] = result.value
    return list(policies.values()), errors


def _handler_exists(handler: str, policy: Policy) -> bool:
    if (_PACKAGE_ROOT / handler).exists():
        return True
    source_dir = Path(policy.source_path).resolve().parent
    # Project policies may reference project-root-relative handlers; the
    # project root is two levels up from .crucible/policies/.
    project_root = source_dir.parent.parent
    return (project_root / handler).exists() or Path(handler).exists()


def _known_skill_names() -> set[str]:
    try:
        from crucible.core.disclosure import discover_skills

        names: set[str] = set()
        for summary in discover_skills():
            name = getattr(summary, "name", None) or str(summary)
            names.add(name)
            names.add(name.rsplit("/", 1)[-1])
        return names
    except Exception:  # crucible-ignore: no-catch-exception -- validator must degrade, not crash, if discovery breaks
        return set()


def validate_policies(policies: list[Policy]) -> list[PolicyIssue]:
    issues: list[PolicyIssue] = []
    known_skills = _known_skill_names()

    for policy in policies:
        for hook in policy.hooks:
            if not _handler_exists(hook.handler, policy):
                issues.append(PolicyIssue(
                    policy=policy.name,
                    field=f"hooks.handler:{hook.handler}",
                    message=f"handler not found: {hook.handler}",
                    level="error",
                ))
        if known_skills:
            for skill in policy.activated_by_skills:
                if skill not in known_skills:
                    issues.append(PolicyIssue(
                        policy=policy.name,
                        field=f"activated_by.skills:{skill}",
                        message=f"unknown skill: {skill}",
                        level="warning",
                    ))
        if policy.name == "settings_integrity":
            from crucible.baselines import WATCHED_FILES

            declared = {
                str(entry.get("path", ""))
                for entry in (policy.extra.get("watched_files") or [])
                if isinstance(entry, dict)
            }
            expected = {str(path) for _, path in WATCHED_FILES}
            if declared != expected:
                issues.append(PolicyIssue(
                    policy=policy.name,
                    field="watched_files",
                    message=(
                        f"watched_files drift: policy declares {sorted(declared)}, "
                        f"baselines.WATCHED_FILES has {sorted(expected)}"
                    ),
                    level="error",
                ))
    return issues
