"""Pattern matching for enforcement assertions."""

import re
from pathlib import Path

from crucible.enforcement.models import (
    Assertion,
    AssertionType,
    EnforcementFinding,
    PatternMatch,
    Suppression,
)

# Language to file extension mapping
LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "python": (".py", ".pyw"),
    "typescript": (".ts", ".tsx"),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "solidity": (".sol",),
    "rust": (".rs",),
    "go": (".go",),
    "java": (".java",),
    "c": (".c", ".h"),
    "cpp": (".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx"),
    "ruby": (".rb",),
    "php": (".php",),
    "swift": (".swift",),
    "kotlin": (".kt", ".kts"),
    "scala": (".scala",),
}

# Suppression patterns
# Match: // crucible-ignore: rule1, rule2 -- reason
SUPPRESSION_PATTERN = re.compile(
    r"(?://|#|/\*)\s*crucible-ignore(?:-next-line)?:\s*([a-z0-9_,\s-]+?)(?:\s+--\s+(.+?))?(?:\s*\*/)?$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_suppressions(content: str) -> list[Suppression]:
    """Parse crucible-ignore comments from file content.

    Supports:
    - // crucible-ignore: rule-id
    - // crucible-ignore: rule-id, other-rule
    - // crucible-ignore-next-line: rule-id
    - # crucible-ignore: rule-id  (Python/shell)
    - /* crucible-ignore: rule-id */ (block comments)
    - // crucible-ignore: rule-id -- reason

    Returns:
        List of Suppression objects
    """
    suppressions: list[Suppression] = []
    lines = content.split("\n")

    for i, line in enumerate(lines):
        match = SUPPRESSION_PATTERN.search(line)
        if match:
            rule_ids_str = match.group(1)
            reason = match.group(2)

            rule_ids = tuple(r.strip().lower() for r in rule_ids_str.split(",") if r.strip())
            applies_to_next = "next-line" in line.lower()

            # Line numbers are 1-indexed
            line_num = i + 1

            suppressions.append(
                Suppression(
                    line=line_num,
                    rule_ids=rule_ids,
                    reason=reason.strip() if reason else None,
                    applies_to_next_line=applies_to_next,
                )
            )

    return suppressions


def is_suppressed(line_num: int, rule_id: str, suppressions: list[Suppression]) -> Suppression | None:
    """Check if a rule is suppressed at a given line.

    Args:
        line_num: 1-indexed line number
        rule_id: Rule ID to check
        suppressions: List of parsed suppressions

    Returns:
        The Suppression if suppressed, None otherwise
    """
    rule_id_lower = rule_id.lower()

    for suppression in suppressions:
        # Check if this rule is in the suppression list
        if rule_id_lower not in suppression.rule_ids:
            continue

        if suppression.applies_to_next_line:
            # Suppresses the line immediately after the comment
            if line_num == suppression.line + 1:
                return suppression
        else:
            # Suppresses the same line as the comment
            if line_num == suppression.line:
                return suppression

    return None


def matches_language(file_path: str, languages: tuple[str, ...]) -> bool:
    """Check if a file matches the specified languages.

    Args:
        file_path: Path to check
        languages: Tuple of language names (empty means match all)

    Returns:
        True if file matches or languages is empty
    """
    if not languages:
        return True

    ext = Path(file_path).suffix.lower()

    for language in languages:
        language_lower = language.lower()
        if language_lower in LANGUAGE_EXTENSIONS:
            if ext in LANGUAGE_EXTENSIONS[language_lower]:
                return True
        # Also allow direct extension matching (e.g., "ts" for .ts)
        elif ext == f".{language_lower}":
            return True

    return False


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert a glob pattern to a regex.

    Supports:
    - * matches any characters except /
    - ** matches any characters including /
    - ? matches single character
    - [abc] character classes
    """
    regex_parts = []
    i = 0
    n = len(pattern)

    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                # ** matches anything including /
                regex_parts.append(".*")
                i += 2
                # Skip trailing / after **
                if i < n and pattern[i] == "/":
                    i += 1
            else:
                # * matches anything except /
                regex_parts.append("[^/]*")
                i += 1
        elif c == "?":
            regex_parts.append("[^/]")
            i += 1
        elif c == "[":
            # Character class - find closing ]
            j = i + 1
            if j < n and pattern[j] == "!":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1
            if j >= n:
                regex_parts.append(re.escape(c))
            else:
                char_class = pattern[i : j + 1]
                if char_class[1] == "!":
                    char_class = "[^" + char_class[2:]
                regex_parts.append(char_class)
                i = j + 1
                continue
            i += 1
        else:
            regex_parts.append(re.escape(c))
            i += 1

    return re.compile("^" + "".join(regex_parts) + "$")


def _glob_match(file_path: str, pattern: str) -> bool:
    """Match a file path against a glob pattern supporting **.

    Args:
        file_path: Path to check (forward slashes)
        pattern: Glob pattern (supports **)

    Returns:
        True if file matches pattern
    """
    regex = _glob_to_regex(pattern)
    return regex.match(file_path) is not None


def matches_glob(file_path: str, glob_pattern: str | None, exclude: tuple[str, ...] = ()) -> bool:
    """Check if a file matches glob pattern and is not excluded.

    Args:
        file_path: Path to check
        glob_pattern: Glob pattern (None matches all)
        exclude: Patterns to exclude

    Returns:
        True if file matches glob and is not excluded
    """
    # Normalize path separators
    file_path = file_path.replace("\\", "/")

    # Check excludes first
    for excl in exclude:
        if _glob_match(file_path, excl):
            return False

    # If no glob pattern, match all (that weren't excluded)
    if glob_pattern is None:
        return True

    return _glob_match(file_path, glob_pattern)


def find_pattern_matches(
    file_path: str,
    content: str,
    pattern: str,
) -> list[PatternMatch]:
    """Find all matches of a regex pattern in file content.

    Args:
        file_path: Path to the file (for location reporting)
        content: File content to search
        pattern: Regex pattern to match

    Returns:
        List of PatternMatch objects
    """
    matches: list[PatternMatch] = []

    try:
        regex = re.compile(pattern)
    except re.error:
        return matches  # Invalid pattern, return empty

    lines = content.split("\n")
    for line_num, line in enumerate(lines, start=1):
        for match in regex.finditer(line):
            matches.append(
                PatternMatch(
                    assertion_id="",  # Set by caller
                    line=line_num,
                    column=match.start() + 1,  # 1-indexed
                    match_text=match.group(),
                    file_path=file_path,
                )
            )

    return matches


def run_pattern_assertions(
    file_path: str,
    content: str,
    assertions: list[Assertion],
) -> tuple[list[EnforcementFinding], int, int]:
    """Run pattern assertions against a file.

    Args:
        file_path: Path to the file
        content: File content
        assertions: List of assertions to check

    Returns:
        Tuple of (findings, checked_count, skipped_count)
    """
    findings: list[EnforcementFinding] = []
    checked = 0
    skipped = 0

    # Parse suppressions once
    suppressions = parse_suppressions(content)

    for assertion in assertions:
        # Skip non-pattern assertions
        if assertion.type != AssertionType.PATTERN:
            skipped += 1
            continue

        # Check language applicability
        if not matches_language(file_path, assertion.languages):
            continue

        # Check glob applicability
        if assertion.applicability and not matches_glob(
            file_path,
            assertion.applicability.glob,
            assertion.applicability.exclude,
        ):
            continue

        checked += 1

        # Find matches
        if assertion.pattern is None:
            continue

        matches = find_pattern_matches(file_path, content, assertion.pattern)

        for match in matches:
            # Check for suppression
            suppression = is_suppressed(match.line, assertion.id, suppressions)

            findings.append(
                EnforcementFinding(
                    assertion_id=assertion.id,
                    message=assertion.message,
                    severity=assertion.severity,
                    priority=assertion.priority,
                    location=f"{file_path}:{match.line}:{match.column}",
                    match_text=match.match_text,
                    suppressed=suppression is not None,
                    suppression_reason=suppression.reason if suppression else None,
                )
            )

    return findings, checked, skipped
