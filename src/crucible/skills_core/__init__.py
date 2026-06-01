"""Crucible v2 skills_core — loader primitives for skills.

This module owns the on-disk representation of skills: cascade resolution
across project/user/bundled tiers, SKILL.md parsing, and the shared types
those primitives produce.

It is deliberately narrow. Progressive disclosure orchestration, trigger
routing, frontmatter schema validation, and Crucible-specific cascade
spec instances all live in ``crucible.core`` — see SPEC.md for the
rationale (Sage cross-check, R8).

Public API surface:

- Types: ``CascadeSpec``, ``ResolvedPath``, ``RawSkill``
- Cascade: ``resolve()``, ``list_available()``
- Loader: ``parse_frontmatter()``, ``read_skill()``

When code outside this package needs any of those, it imports them
from ``crucible.skills_core``, never from internal ``_modules``.

Long-term contract: see SPEC.md in this directory.
"""

from ._cascade import list_available, resolve
from ._loader import parse_frontmatter, read_skill
from ._types import CascadeSpec, RawSkill, ResolvedPath

__all__ = [
    "CascadeSpec",
    "RawSkill",
    "ResolvedPath",
    "list_available",
    "parse_frontmatter",
    "read_skill",
    "resolve",
]
