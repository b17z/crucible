"""Shared types for skills_core loader primitives.

Internal — consumers import from ``crucible.skills_core`` (the public
surface), not from this module directly. See SPEC.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class CascadeSpec:
    """Declarative description of one content type's resolution surface.

    Each consumer (Crucible's core/specs.py, Sage's future loader) builds
    its own instances. ``skills_core`` exports the *type*, not the
    instances — keeping the loader free of consumer-specific paths.
    """

    project_dir: Path
    user_dir: Path
    bundled_dir: Path
    is_folder: bool  # True → lookup unit is a folder; False → a file
    suffix: str | None = None  # e.g. ".yaml" for files; None for folders

    # v1 → v2 dual-path fallback. None when the path is shape-stable
    # across versions.
    fallback_project_dir: Path | None = None
    fallback_label: str | None = None  # deprecation warning text


@dataclass(frozen=True)
class ResolvedPath:
    """The output of a successful cascade resolution."""

    path: Path
    source: Literal["project", "user", "bundled"]
    used_fallback: bool  # True if the v1 project-tier fallback was hit


@dataclass(frozen=True)
class RawSkill:
    """A skill as it exists on disk. Loader output; consumer-agnostic.

    ``frontmatter`` is an open dict — each consumer reads the keys it
    cares about. Crucible reads ``name``, ``description``, ``version``;
    Sage reads ``description``, ``sage_managed``, ``tags``; new consumers
    can add fields without changing this type.

    ``sibling_paths`` enumerates immediate children of the skill folder
    (e.g. ``{"knowledge": Path(...), "assertions": Path(...)}``). It does
    not read those folders' contents — consumers do that lazily.
    """

    path: Path  # The skill folder, NOT the SKILL.md inside it.
    source: Literal["project", "user", "bundled"]
    used_fallback: bool
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    sibling_paths: dict[str, Path] = field(default_factory=dict)
