"""Progressive disclosure — Crucible's three-tier skill loading.

Per the SAGE cross-check (R8 in skills_core/SPEC.md), this orchestration
lives in core/, not skills_core/. It is a Crucible-specific loading
strategy built on the skills_core loader primitives. Sage's eager
build_context() is a different strategy on the same primitives.

The three tiers control context-window cost:

- Tier 1 — discover_skills(): load only frontmatter (~name + description)
  for every skill in the cascade. Cheap. Used at SessionStart so the
  agent knows what's available without paying to load every body.
- Tier 2 — activate_skill(): load the full SKILL.md body for one skill.
  Triggered when the skill actually activates (trigger match or explicit
  request).
- Tier 3 — load_knowledge(): load one named knowledge file's content.
  Triggered when the activated skill references it at runtime.

The cost saving is real and measured: discovering all 27 bundled skills
via Tier 1 costs ~3.8 KB (one description line each), versus ~119 KB to
load every body + knowledge file — a **96.8% reduction**, far above the
Phase 3 >30% target. The test
``tests/test_disclosure.py::TestProgressiveCost::test_real_bundled_tree_beats_30pct_target``
enforces the floor against the real tree so the claim can't silently rot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from crucible.core.specs import SKILLS_SPEC
from crucible.errors import Err, Result, err, ok
from crucible.skills_core import (
    CascadeSpec,
    parse_frontmatter,
    read_skill,
    resolve,
)


@dataclass(frozen=True)
class SkillSummary:
    """Tier 1: a skill's discovery metadata. Frontmatter only.

    This is what SessionStart surfaces to the agent — enough to decide
    whether a skill is relevant, without loading its body or knowledge.

    ``name`` is the cascade-resolution identity: the path relative to the
    skills root, including any namespace prefix (e.g. "meta/but-for-real",
    "pre-write/prd"). This is the string you pass to resolve() /
    discover_skill() to get this skill back. It is NOT the frontmatter
    ``name`` field — that's a display label exposed as ``display_name``.
    """

    name: str  # resolution identity (namespaced path)
    description: str
    path: Path  # the skill folder
    source: str  # "project" | "user" | "bundled"
    frontmatter: dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """The frontmatter `name`, falling back to the resolution name."""
        return str(self.frontmatter.get("name") or self.name)

    @property
    def discovery_text(self) -> str:
        """One-line discovery string: `name — description`."""
        desc = self.description.strip() if self.description else "(no description)"
        return f"{self.name} — {desc}"


@dataclass(frozen=True)
class ActivatedSkill:
    """Tier 2: a skill with its SKILL.md body loaded.

    Carries the Tier 1 summary plus the body and the names of available
    knowledge/assertion files (paths, not contents — those are Tier 3).
    """

    summary: SkillSummary
    body: str
    knowledge_files: tuple[str, ...]  # filenames available under knowledge/
    assertion_files: tuple[str, ...]  # filenames available under assertions/


def _summary_from_frontmatter(
    name: str, fm: dict[str, Any], path: Path, source: str
) -> SkillSummary:
    # `name` is the resolution identity (path-relative, namespaced). Do
    # NOT override it with the frontmatter name — that's a display label
    # and may lack the namespace prefix, which would break resolution.
    return SkillSummary(
        name=name,
        description=str(fm.get("description", "")),
        path=path,
        source=source,  # type: ignore[arg-type]
        frontmatter=fm,
    )


def discover_skills(spec: CascadeSpec = SKILLS_SPEC) -> list[SkillSummary]:
    """Tier 1: load frontmatter for every skill in the cascade.

    Reads only each skill's SKILL.md frontmatter (the part before the
    closing `---`), never the body. Skills whose SKILL.md is missing or
    whose frontmatter is unparseable are skipped (discovery is
    best-effort; a broken skill shouldn't break the whole listing).

    Returns summaries sorted by name. Also descends one level into
    namespace folders (meta/, pre-write/) so nested skills are
    discovered — list_available already handles that flattening for
    folder specs is shallow, so we recurse here explicitly.
    """
    summaries: list[SkillSummary] = []

    # Walk each tier directory. We can't rely on resolve() per-name here
    # because we don't know the names yet — discovery IS the enumeration.
    tiers: list[tuple[Path, str]] = [
        (spec.project_dir, "project"),
        (spec.user_dir, "user"),
        (spec.bundled_dir, "bundled"),
    ]
    if spec.fallback_project_dir is not None:
        tiers.insert(1, (spec.fallback_project_dir, "project"))

    # First-found-wins per skill name across tiers (project > user > bundled).
    seen: set[str] = set()
    for base, source in tiers:
        if not base.exists() or not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            if not entry.is_dir() or entry.name.startswith(".") or entry.name == "__pycache__":
                continue
            # A skill folder has a SKILL.md; a namespace folder (meta/,
            # pre-write/) does not — recurse one level into those.
            candidates: list[tuple[str, Path]] = []
            if (entry / "SKILL.md").exists():
                candidates.append((entry.name, entry))
            else:
                for sub in sorted(entry.iterdir()):
                    if sub.is_dir() and (sub / "SKILL.md").exists():
                        candidates.append((f"{entry.name}/{sub.name}", sub))

            for skill_name, skill_dir in candidates:
                if skill_name in seen:
                    continue
                summary = _read_summary(skill_name, skill_dir, source)
                if summary is not None:
                    seen.add(skill_name)
                    summaries.append(summary)

    summaries.sort(key=lambda s: s.name)
    return summaries


def _read_summary(skill_name: str, skill_dir: Path, source: str) -> SkillSummary | None:
    """Read only the frontmatter of one skill's SKILL.md. None on failure."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    try:
        content = skill_md.read_text()
    except OSError:
        return None
    parsed = parse_frontmatter(content)
    if isinstance(parsed, Err):
        return None
    fm, _body = parsed.value
    return _summary_from_frontmatter(skill_name, fm, skill_dir, source)


def discover_skill(name: str, spec: CascadeSpec = SKILLS_SPEC) -> Result[SkillSummary, str]:
    """Tier 1 for a single named skill. Resolves via the cascade.

    Supports namespaced names like "meta/but-for-real": resolve() handles
    the slash since the project/user/bundled dirs are the cascade roots.
    """
    resolved = resolve(spec, name)
    if isinstance(resolved, Err):
        return err(resolved.error)
    rp = resolved.value
    summary = _read_summary(name, rp.path, rp.source)
    if summary is None:
        return err(f"could not read frontmatter for skill '{name}' at {rp.path}")
    return ok(summary)


def activate_skill(summary: SkillSummary) -> Result[ActivatedSkill, str]:
    """Tier 2: load the full SKILL.md body for a discovered skill.

    Uses skills_core.read_skill to get the body and the sibling folder
    layout, then enumerates the knowledge/ and assertions/ filenames
    (names only — contents are Tier 3 via load_knowledge).
    """
    result = read_skill(summary.path, source=summary.source)
    if isinstance(result, Err):
        return err(result.error)
    raw = result.value

    knowledge_files = _list_dir_files(raw.sibling_paths.get("knowledge"), suffix=".md")
    assertion_files = _list_dir_files(raw.sibling_paths.get("assertions"), suffix=(".yaml", ".yml"))

    return ok(
        ActivatedSkill(
            summary=summary,
            body=raw.body,
            knowledge_files=knowledge_files,
            assertion_files=assertion_files,
        )
    )


def _list_dir_files(directory: Path | None, suffix: str | tuple[str, ...]) -> tuple[str, ...]:
    """Filenames in `directory` with the given suffix. Empty if None."""
    if directory is None or not directory.is_dir():
        return ()
    suffixes = (suffix,) if isinstance(suffix, str) else suffix
    names = [
        child.name
        for child in sorted(directory.iterdir())
        if child.is_file() and child.suffix in suffixes
    ]
    return tuple(names)


def load_knowledge(skill: ActivatedSkill, knowledge_file: str) -> Result[str, str]:
    """Tier 3: load one named knowledge file's content.

    `knowledge_file` is a filename as listed in skill.knowledge_files
    (with or without the .md suffix). Returns the file content.
    """
    if not knowledge_file.endswith(".md"):
        knowledge_file = f"{knowledge_file}.md"

    knowledge_dir = skill.summary.path / "knowledge"
    target = knowledge_dir / knowledge_file
    if not target.exists():
        available = ", ".join(skill.knowledge_files) or "(none)"
        return err(
            f"knowledge file '{knowledge_file}' not found for skill "
            f"'{skill.summary.name}'. Available: {available}"
        )
    try:
        return ok(target.read_text())
    except OSError as e:
        return err(f"failed to read '{knowledge_file}': {e}")


def discovery_digest(summaries: list[SkillSummary]) -> str:
    """Render Tier 1 summaries as a compact discovery block.

    This is what SessionStart injects: one line per skill, name +
    description. Cheap to produce, cheap to carry in context.
    """
    if not summaries:
        return "No skills available."
    lines = ["# Available skills (Tier 1 discovery)", ""]
    lines.extend(f"- {s.discovery_text}" for s in summaries)
    return "\n".join(lines)
