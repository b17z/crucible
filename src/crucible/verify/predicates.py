"""Context predicates for the Phase 6 verifier.

Each predicate answers: "is this finding a confirmed false positive?"
(True = suppress). They are written in the suppress direction so bindings
never need invert flags. All are pure functions over the finding's
location context and the file content; on any doubt they return False —
the verifier must never eat a true positive.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class FindingContext:
    """Normalized location view of a finding, tool- and assertion-agnostic."""

    path: str
    line: int | None
    column: int | None
    match_text: str | None


def _line_at(content: str, line: int | None) -> str | None:
    if line is None or line < 1:
        return None
    lines = content.splitlines()
    if line > len(lines):
        return None
    return lines[line - 1]


def is_test_file(ctx: FindingContext, content: str) -> bool:
    """Corpus group 3 (bandit/B101): pytest uses assert as its mechanism."""
    path = PurePosixPath(ctx.path.replace("\\", "/"))
    if any(part in ("tests", "test") for part in path.parts[:-1]):
        return True
    name = path.name
    return (
        (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


_OCTAL_RE = re.compile(r"0o([0-7]{3,4})")


def octal_without_other_write(ctx: FindingContext, content: str) -> bool:
    """Corpus group 2 (world-writable-permissions): parse the octal at the
    match; suppress only when the other-write bit (0o2) is absent."""
    line = _line_at(content, ctx.line)
    if line is None:
        return False
    octals = _OCTAL_RE.findall(line)
    if not octals:
        return False
    return all(int(digits[-1], 8) & 0o2 == 0 for digits in octals)


_ARGPARSE_IMPORT_RE = re.compile(
    r"^\s*(import argparse\b|from argparse import\b)", re.MULTILINE
)


def is_cli_entry_point(ctx: FindingContext, content: str) -> bool:
    """Corpus group 1 (user-input-in-path): argparse output is
    operator-controlled — the CLI trust model, not the HTTP one."""
    if not _ARGPARSE_IMPORT_RE.search(content):
        return False
    line = _line_at(content, ctx.line)
    if line is None:
        return False
    return re.search(r"\bargs\.\w+", line) is not None


def match_in_string_literal(ctx: FindingContext, content: str) -> bool:
    """Corpus group 5 (no-todo-without-issue): a match inside a string
    literal is prose about the token, not a live comment marker."""
    line = _line_at(content, ctx.line)
    if line is None or ctx.column is None or ctx.column < 1:
        return False
    prefix = line[: ctx.column - 1]
    in_single = in_double = False
    escaped = False
    comment_start = False
    for ch in prefix:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            comment_start = True
            break
    if comment_start:
        return False  # the match sits in a comment → real finding
    return in_single or in_double


_SUBPROCESS_USE_RE = re.compile(
    r"\bsubprocess\.(run|Popen|call|check_call|check_output)\s*\("
)


def subprocess_import_used(ctx: FindingContext, content: str) -> bool:
    """Corpus group 4 (bandit/B404): an exercised import is the feature;
    the usage-level bandit rules still police the calls themselves."""
    return _SUBPROCESS_USE_RE.search(content) is not None


PREDICATES: dict[str, Callable[[FindingContext, str], bool]] = {
    "is_test_file": is_test_file,
    "octal_without_other_write": octal_without_other_write,
    "is_cli_entry_point": is_cli_entry_point,
    "match_in_string_literal": match_in_string_literal,
    "subprocess_import_used": subprocess_import_used,
}
