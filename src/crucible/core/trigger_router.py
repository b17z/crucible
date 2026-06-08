"""Trigger routing — match prompts/events to the skills that should activate.

Per the SAGE cross-check (R8), this is Crucible-specific and lives in
core/, not skills_core/. It reads each skill's `triggers.yaml` (a separate
file inside the skill folder, NOT a frontmatter field) and decides which
skills a given prompt or event activates.

triggers.yaml shape (all keys optional):

    preconditions:           # ALL must hold or the skill never activates
      - type: project_flag
        flag: "tool.crucible.publishable"
    rules:                   # ANY match activates (union semantics)
      - type: prompt_match
        pattern: '\\b(security|auth)\\b'
      - type: file_glob
        pattern: '**/package.json'
      - type: bash_match
        pattern: '\\bnpm install\\b'

Rule types:
  - prompt_match: regex tested against the user's prompt text
  - file_glob:    glob tested against file paths in scope
  - bash_match:   regex tested against a bash command

Preconditions are a gate: if any precondition fails, the skill is dormant
regardless of rule matches. This is how publisher-security stays quiet
until a project sets `[tool.crucible].publishable = true`.
"""

from __future__ import annotations

import fnmatch
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from crucible.core.disclosure import SkillSummary, discover_skills
from crucible.core.specs import SKILLS_SPEC
from crucible.skills_core import CascadeSpec


@dataclass(frozen=True)
class TriggerMatch:
    """One skill matched by one or more of its rules."""

    skill_name: str
    matched_rules: tuple[str, ...]  # human-readable rule descriptions
    source: str  # "project" | "user" | "bundled"


@dataclass(frozen=True)
class Event:
    """A non-prompt activation event (file change, bash command, etc.)."""

    prompt: str | None = None
    file_paths: tuple[str, ...] = ()
    bash_command: str | None = None


def _load_triggers(skill: SkillSummary) -> dict[str, Any] | None:
    """Read and parse a skill's triggers.yaml. None if absent/malformed."""
    triggers_path = skill.path / "triggers.yaml"
    if not triggers_path.exists():
        return None
    try:
        data = yaml.safe_load(triggers_path.read_text())
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


# --- preconditions -------------------------------------------------------


def _read_project_flag(flag: str, project_root: Path) -> bool:
    """Read a dotted flag like 'tool.crucible.publishable' from
    pyproject.toml ([tool.crucible]) or package.json ("crucible" key).

    Returns the boolean value, or False if unset / unreadable.
    """
    # pyproject.toml path: tool.crucible.<rest>
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text())
        except (tomllib.TOMLDecodeError, OSError):
            data = {}
        node: Any = data
        for part in flag.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        if isinstance(node, bool):
            return node

    # package.json path: the flag's "tool." prefix maps to the top-level
    # "crucible" key, so tool.crucible.publishable -> crucible.publishable.
    package_json = project_root / "package.json"
    if package_json.exists():
        import json

        try:
            data = json.loads(package_json.read_text())
        except (json.JSONDecodeError, OSError):
            data = {}
        # Map "tool.crucible.X" -> "crucible.X"
        keys = flag.split(".")
        if keys and keys[0] == "tool":
            keys = keys[1:]
        node = data
        for part in keys:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        if isinstance(node, bool):
            return node

    return False


def _preconditions_hold(triggers: dict[str, Any], project_root: Path) -> bool:
    """True if every precondition holds (or there are none)."""
    preconditions = triggers.get("preconditions") or []
    if not isinstance(preconditions, list):
        return True
    for pc in preconditions:
        if not isinstance(pc, dict):
            continue
        if pc.get("type") == "project_flag":
            flag = pc.get("flag", "")
            if not flag or not _read_project_flag(flag, project_root):
                return False
        # Unknown precondition types are treated as not-satisfied to stay
        # safe — a skill that declares a precondition we don't understand
        # shouldn't silently activate.
        elif pc.get("type"):
            return False
    return True


# --- rule matching -------------------------------------------------------


def _rule_matches(rule: dict[str, Any], event: Event) -> str | None:
    """Return a human-readable match description if the rule fires, else None."""
    rtype = rule.get("type")
    pattern = rule.get("pattern", "")
    if not pattern:
        return None

    if rtype == "prompt_match":
        if event.prompt and re.search(pattern, event.prompt, re.IGNORECASE):
            return f"prompt_match:{pattern}"
        return None

    if rtype == "bash_match":
        if event.bash_command and re.search(pattern, event.bash_command, re.IGNORECASE):
            return f"bash_match:{pattern}"
        return None

    if rtype == "file_glob":
        for fp in event.file_paths:
            # Match against the full path and the basename so patterns like
            # '**/package.json' and '.mcp.json' both work.
            if fnmatch.fnmatch(fp, pattern) or fnmatch.fnmatch(Path(fp).name, pattern):
                return f"file_glob:{pattern}"
            # '**/' prefix: also try matching the tail.
            if pattern.startswith("**/") and fnmatch.fnmatch(fp, pattern[3:]):
                return f"file_glob:{pattern}"
        return None

    return None


def match_event(
    event: Event,
    project_root: Path | None = None,
    spec: CascadeSpec = SKILLS_SPEC,
    skills: list[SkillSummary] | None = None,
) -> list[TriggerMatch]:
    """Return every skill activated by the event, sorted by skill name.

    A skill activates iff its preconditions hold AND at least one rule
    matches. Skills without a triggers.yaml never match via this router
    (they can still be activated explicitly).
    """
    root = project_root or Path.cwd()
    summaries = skills if skills is not None else discover_skills(spec)

    matches: list[TriggerMatch] = []
    for skill in summaries:
        triggers = _load_triggers(skill)
        if triggers is None:
            continue
        if not _preconditions_hold(triggers, root):
            continue
        rules = triggers.get("rules") or []
        if not isinstance(rules, list):
            continue
        fired: list[str] = []
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            desc = _rule_matches(rule, event)
            if desc:
                fired.append(desc)
        if fired:
            matches.append(
                TriggerMatch(
                    skill_name=skill.name,
                    matched_rules=tuple(fired),
                    source=skill.source,
                )
            )

    matches.sort(key=lambda m: m.skill_name)
    return matches


def match_prompt(
    prompt: str,
    project_root: Path | None = None,
    spec: CascadeSpec = SKILLS_SPEC,
) -> list[TriggerMatch]:
    """Convenience: match a bare prompt string."""
    return match_event(Event(prompt=prompt), project_root=project_root, spec=spec)
