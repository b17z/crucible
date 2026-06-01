"""SKILL.md parsing primitives.

Internal — consumers import from ``crucible.skills_core``. See SPEC.md.

Two functions:

- ``parse_frontmatter(content)`` — splits a SKILL.md string into
  ``(frontmatter_dict, body)``. Tolerant of variant YAML styles.
- ``read_skill(path, source)`` — reads a skill folder, parses
  frontmatter, enumerates sibling subdirectories. Does NOT eagerly load
  knowledge/assertion file contents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from crucible.errors import Err, Ok, Result, err, ok

from ._types import RawSkill


def parse_frontmatter(content: str) -> Result[tuple[dict[str, Any], str], str]:
    """Split SKILL.md content into (frontmatter_dict, body).

    Accepts:
      - ``---\\n<yaml>\\n---\\n<body>`` (standard)
      - ``---\\n<yaml>\\n---\\n`` (frontmatter-only, body is empty)

    Returns err on missing delimiters or invalid YAML.
    """
    if not content.startswith("---\n") and not content.startswith("---\r\n"):
        return err("missing opening frontmatter delimiter (file must start with '---')")

    # Find the closing delimiter. Match exactly '\n---\n' or '\n---\r\n'
    # so we don't false-match a '---' inside the body.
    delimiter_idx = content.find("\n---\n", 4)
    if delimiter_idx == -1:
        delimiter_idx = content.find("\n---\r\n", 4)
        if delimiter_idx == -1:
            # Tolerate frontmatter that ends at EOF without trailing newline.
            if content.rstrip().endswith("---"):
                stripped = content.rstrip()
                fm_text = stripped[4:-3].strip()
                body = ""
                try:
                    fields = yaml.safe_load(fm_text) or {}
                except yaml.YAMLError as e:
                    return err(f"invalid YAML in frontmatter: {e}")
                if not isinstance(fields, dict):
                    return err("frontmatter must be a YAML mapping (object)")
                return ok((fields, body))
            return err("missing closing frontmatter delimiter")
        body_start = delimiter_idx + len("\n---\r\n")
    else:
        body_start = delimiter_idx + len("\n---\n")

    fm_text = content[4:delimiter_idx]
    body = content[body_start:]

    try:
        fields = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        return err(f"invalid YAML in frontmatter: {e}")

    if not isinstance(fields, dict):
        return err("frontmatter must be a YAML mapping (object)")

    return ok((fields, body))


# Subfolders that read_skill enumerates by convention. If a skill ships
# additional folders beyond this set, they are still discoverable via
# sibling_paths but require the caller to know to look for them.
KNOWN_SUBFOLDERS = ("knowledge", "assertions", "checks", "personas", "hooks")


def read_skill(path: Path, source: str = "project") -> Result[RawSkill, str]:
    """Read a skill folder from disk.

    ``path`` is the resolved skill folder (typically from ``resolve()``).
    ``source`` is the tier tag from cascade resolution; passed through
    to the returned ``RawSkill``.

    Reads ``SKILL.md``, parses frontmatter, enumerates immediate
    subdirectories listed in ``KNOWN_SUBFOLDERS``. Does NOT read knowledge
    or assertion file contents — callers do that lazily.
    """
    if not path.exists():
        return err(f"skill folder does not exist: {path}")
    if not path.is_dir():
        return err(f"skill path is not a directory: {path}")

    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        return err(f"missing SKILL.md in skill folder: {path}")

    content = skill_md.read_text()
    parsed = parse_frontmatter(content)
    if isinstance(parsed, Err):
        return err(f"parse error in {skill_md}: {parsed.error}")

    fields, body = parsed.value

    sibling_paths: dict[str, Path] = {}
    for name in KNOWN_SUBFOLDERS:
        sub = path / name
        if sub.exists() and sub.is_dir():
            sibling_paths[name] = sub

    # Also surface a triggers.yaml file if present (Crucible-specific
    # but cheap to enumerate; consumers that don't use it ignore it).
    triggers = path / "triggers.yaml"
    if triggers.exists() and triggers.is_file():
        sibling_paths["triggers.yaml"] = triggers

    return ok(
        RawSkill(
            path=path,
            source=source,  # type: ignore[arg-type]
            used_fallback=False,
            frontmatter=fields,
            body=body,
            sibling_paths=sibling_paths,
        )
    )
