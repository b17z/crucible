"""Concrete CascadeSpec instances for Crucible's content types.

Per the SAGE cross-check (R8 in skills_core/SPEC.md), the concrete specs
live here — not in skills_core — because they encode Crucible-specific
paths (the bundled-package root) that change meaning at v2.x extraction
time.

When Sage migrates and skills_core extracts into its own PyPI package,
this file stays in Crucible. Sage will construct its own CascadeSpec
instances using the same skills_core type.

Phase 0 cascade-surface audit:

  Skills folders are shape-stable (no fallback). SKILLS_SPEC below.
  Knowledge/assertions live nested under skill folders in v2; their
    cascade is "resolve the parent skill, then walk sibling_paths" —
    handled by the resolve_knowledge / resolve_assertion helpers below,
    NOT via a standalone CascadeSpec.
  Prewrite templates ARE skill folders under skills/pre-write/ — also
    covered by SKILLS_SPEC with a subdirectory filter.
  .crucibleignore is an outlier (merges across tiers) and stays in
    crucible.ignore — not migrated here.

Phase 2 scope notes:

- ``crucible.skills.loader`` is rewired through SKILLS_SPEC. The v1
  ``resolve_skill_path`` and ``get_all_skill_names`` functions delegate
  here while keeping their public contract.
- ``crucible.knowledge.loader``, ``crucible.enforcement.assertions``,
  and ``crucible.prewrite.loader`` keep their v1 implementations.
  Reason: their v1 layout (flat files at known bundled paths) is
  fundamentally different from v2 (nested under skill folders), and
  the v1 file *names* don't reverse-map cleanly to v2 names
  (``SECURITY.md`` vs ``security-principles.md``). Forcing those
  resolvers through skills_core would break the v1 contract without
  the migration command actually moving files. The new v2 API for
  these content types is exposed via the ``resolve_knowledge`` and
  ``resolve_assertion`` helpers below; v2 callers use those, v1
  callers keep working unchanged. Phase 3+ can deprecate the v1
  entry points after the migration command has run on real
  projects.
"""

from __future__ import annotations

from pathlib import Path

from crucible.errors import Result, err, ok
from crucible.skills_core import CascadeSpec, ResolvedPath, resolve

# Phase 2 plan-A: bundled skills stay at src/crucible/skills/ for this
# release. The new-shape skills/ at the repo root was laid down in Phase
# 1b/2 and contains the migrated content, but the v1 cascade still points
# here for backward compatibility with installed wheels. A later phase
# (or v2.1) flips the canonical bundled location to the repo-root
# skills/ and updates pyproject.toml package_data accordingly.
#
# The repo-root skills/ is still useful: it's what `crucible migrate
# v1-to-v2` migrates user-tier `.crucible/` overrides INTO the shape of,
# and what new-shape contributions live in (security-engineer migrated
# in 1b, all 20 personas migrated in 2).
_PKG_ROOT = Path(__file__).resolve().parent.parent  # src/crucible/
_BUNDLED_SKILLS = _PKG_ROOT / "skills"


SKILLS_SPEC = CascadeSpec(
    project_dir=Path(".crucible") / "skills",
    user_dir=Path.home() / ".claude" / "crucible" / "skills",
    bundled_dir=_BUNDLED_SKILLS,
    is_folder=True,
    suffix=None,
    fallback_project_dir=None,
    fallback_label=None,
)


# -- v1→v2 dual-path resolution for nested knowledge/assertions ---------
#
# The v1 cascade had flat .crucible/knowledge/<file>.md and
# .crucible/assertions/<file>.yaml. v2 nests them under skills. The
# dual-path resolver here covers users with v1-shape overrides.
#
# These are NOT CascadeSpec-backed because the v2 location depends on
# which persona owns the file — and skills_core.CascadeSpec is
# intentionally flat (one base dir per tier, not parameterized by
# persona). Resolving knowledge/assertion files goes through the
# corresponding skill first.


def resolve_knowledge(skill_name: str, knowledge_file: str) -> Result[ResolvedPath, str]:
    """Resolve a knowledge file. Tries v2 nested location, then v1 flat.

    Returns a ResolvedPath whose ``used_fallback=True`` signals the v1
    fallback path was hit, so the caller emits a deprecation warning
    on the user's behalf if appropriate.
    """
    # Normalize: caller may pass with or without the .md suffix.
    if not knowledge_file.endswith(".md"):
        knowledge_file = f"{knowledge_file}.md"

    # v2 path: look up the skill, then walk its knowledge/ sibling.
    skill_path_result = resolve(SKILLS_SPEC, skill_name)
    if skill_path_result.is_ok:
        skill_path = skill_path_result.value.path
        v2_candidate = skill_path / "knowledge" / knowledge_file
        if v2_candidate.exists():
            return ok(
                ResolvedPath(
                    path=v2_candidate,
                    source=skill_path_result.value.source,
                    used_fallback=False,
                )
            )

    # v1 fallback: flat .crucible/knowledge/<file>.md or user-tier
    # equivalent. Per the Phase 0 audit, the v1 file is uppercase-ish
    # (SECURITY.md, FP.md) while v2 is kebab-case (security-principles.md,
    # functional-programming.md). The caller passes the v2 name; we don't
    # try to reverse-map.
    v1_candidates = [
        (Path(".crucible") / "knowledge" / knowledge_file, "project"),
        (Path.home() / ".claude" / "crucible" / "knowledge" / knowledge_file, "user"),
    ]
    for candidate, source in v1_candidates:
        if candidate.exists():
            import warnings

            warnings.warn(
                f"crucible: resolved knowledge '{knowledge_file}' via v1 path "
                f"{candidate}. This path is deprecated; v2 nests knowledge "
                f"under skills/<persona>/knowledge/. Run `crucible migrate "
                f"v1-to-v2` to move it.",
                DeprecationWarning,
                stacklevel=2,
            )
            return ok(ResolvedPath(path=candidate, source=source, used_fallback=True))

    return err(f"knowledge file not found in v2 or v1 layout: {knowledge_file}")


def resolve_assertion(skill_name: str, assertion_file: str) -> Result[ResolvedPath, str]:
    """Resolve an assertion YAML. Tries v2 nested, then v1 flat. Same
    fallback semantics as resolve_knowledge."""
    if not assertion_file.endswith((".yaml", ".yml")):
        assertion_file = f"{assertion_file}.yaml"

    # v2: nested under skill.
    skill_path_result = resolve(SKILLS_SPEC, skill_name)
    if skill_path_result.is_ok:
        skill_path = skill_path_result.value.path
        v2_candidate = skill_path / "assertions" / assertion_file
        if v2_candidate.exists():
            return ok(
                ResolvedPath(
                    path=v2_candidate,
                    source=skill_path_result.value.source,
                    used_fallback=False,
                )
            )

    # v1 fallback: flat .crucible/assertions/<file>.yaml or user-tier.
    v1_candidates = [
        (Path(".crucible") / "assertions" / assertion_file, "project"),
        (Path.home() / ".claude" / "crucible" / "assertions" / assertion_file, "user"),
    ]
    for candidate, source in v1_candidates:
        if candidate.exists():
            import warnings

            warnings.warn(
                f"crucible: resolved assertion '{assertion_file}' via v1 path "
                f"{candidate}. This path is deprecated; v2 nests assertions "
                f"under skills/<persona>/assertions/. Run `crucible migrate "
                f"v1-to-v2` to move it.",
                DeprecationWarning,
                stacklevel=2,
            )
            return ok(ResolvedPath(path=candidate, source=source, used_fallback=True))

    return err(f"assertion file not found in v2 or v1 layout: {assertion_file}")
