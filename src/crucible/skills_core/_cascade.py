"""Cascade resolution: project > user > bundled, with optional v1→v2 fallback.

Internal — consumers import from ``crucible.skills_core``. See SPEC.md.

Two public functions:

- ``resolve(spec, name)`` — finds a single content item.
- ``list_available(spec)`` — enumerates names across all tiers.
"""

from __future__ import annotations

import warnings

from crucible.errors import Result, err, ok

from ._types import CascadeSpec, ResolvedPath


def _candidate_for_name(spec: CascadeSpec, base, name: str):
    """Build the candidate path for a given tier base directory."""
    if spec.is_folder:
        return base / name
    # File mode: append the suffix if needed.
    if spec.suffix and not name.endswith(spec.suffix):
        return base / f"{name}{spec.suffix}"
    return base / name


def resolve(spec: CascadeSpec, name: str) -> Result[ResolvedPath, str]:
    """First-found-wins across project → (fallback if set) → user → bundled.

    When a hit comes from ``fallback_project_dir`` (the v1 path), emits a
    ``DeprecationWarning`` citing ``fallback_label`` and marks
    ``used_fallback=True`` on the result.
    """
    # Project tier (v2 shape)
    project_candidate = _candidate_for_name(spec, spec.project_dir, name)
    if project_candidate.exists():
        return ok(ResolvedPath(path=project_candidate, source="project", used_fallback=False))

    # Project tier fallback (v1 shape) — only if configured.
    if spec.fallback_project_dir is not None:
        fallback_candidate = _candidate_for_name(spec, spec.fallback_project_dir, name)
        if fallback_candidate.exists():
            label = spec.fallback_label or "v1 path"
            warnings.warn(
                f"crucible: resolved '{name}' via {label}. This path is "
                "deprecated and will be removed in v2.2. Run "
                "`crucible migrate v1-to-v2` to move it.",
                DeprecationWarning,
                stacklevel=2,
            )
            return ok(ResolvedPath(path=fallback_candidate, source="project", used_fallback=True))

    # User tier
    user_candidate = _candidate_for_name(spec, spec.user_dir, name)
    if user_candidate.exists():
        return ok(ResolvedPath(path=user_candidate, source="user", used_fallback=False))

    # Bundled tier
    bundled_candidate = _candidate_for_name(spec, spec.bundled_dir, name)
    if bundled_candidate.exists():
        return ok(ResolvedPath(path=bundled_candidate, source="bundled", used_fallback=False))

    return err(f"not found in cascade: '{name}'")


def list_available(spec: CascadeSpec) -> set[str]:
    """Names available across all tiers (including fallback if configured).

    For folder specs, names are subdirectory basenames. For file specs,
    names are file basenames with the suffix stripped (matching the
    lookup contract of ``resolve``).
    """
    found: set[str] = set()
    tiers = [spec.project_dir, spec.user_dir, spec.bundled_dir]
    if spec.fallback_project_dir is not None:
        tiers.insert(1, spec.fallback_project_dir)

    for base in tiers:
        if not base.exists() or not base.is_dir():
            continue
        for child in base.iterdir():
            # Skip dotfiles and Python cache directories — they are
            # never valid skill / content names.
            if child.name.startswith(".") or child.name == "__pycache__":
                continue
            if spec.is_folder:
                if child.is_dir():
                    found.add(child.name)
            else:
                if not child.is_file():
                    continue
                if spec.suffix:
                    if child.name.endswith(spec.suffix):
                        found.add(child.name[: -len(spec.suffix)])
                else:
                    found.add(child.name)
    return found
