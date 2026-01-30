"""Load and validate assertion files.

Assertions follow the same cascade as skills/knowledge:
1. Project: .crucible/assertions/
2. User: ~/.claude/crucible/assertions/
3. Bundled: package assertions/ (none bundled by default)
"""

from functools import lru_cache
from pathlib import Path

import yaml

from crucible.enforcement.models import (
    Applicability,
    Assertion,
    AssertionFile,
    AssertionType,
    Priority,
)
from crucible.errors import Result, err, ok

# Assertion directories (cascade priority)
ASSERTIONS_BUNDLED = Path(__file__).parent / "bundled"
ASSERTIONS_USER = Path.home() / ".claude" / "crucible" / "assertions"
ASSERTIONS_PROJECT = Path(".crucible") / "assertions"


def resolve_assertion_file(filename: str) -> tuple[Path | None, str]:
    """Find assertion file with cascade priority.

    Returns (path, source) where source is 'project', 'user', or 'bundled'.
    """
    # Ensure .yaml extension
    if not filename.endswith((".yaml", ".yml")):
        filename = f"{filename}.yaml"

    # 1. Project-level (highest priority)
    project_path = ASSERTIONS_PROJECT / filename
    if project_path.exists():
        return project_path, "project"

    # 2. User-level
    user_path = ASSERTIONS_USER / filename
    if user_path.exists():
        return user_path, "user"

    # 3. Bundled (lowest priority)
    bundled_path = ASSERTIONS_BUNDLED / filename
    if bundled_path.exists():
        return bundled_path, "bundled"

    return None, ""


def get_all_assertion_files() -> set[str]:
    """Get all available assertion file names from all sources."""
    files: set[str] = set()

    for source_dir in [ASSERTIONS_BUNDLED, ASSERTIONS_USER, ASSERTIONS_PROJECT]:
        if source_dir.exists():
            for file_path in source_dir.iterdir():
                if file_path.is_file() and file_path.suffix in (".yaml", ".yml"):
                    files.add(file_path.name)

    return files


def _parse_priority(value: str | None) -> Priority:
    """Parse priority string to enum."""
    if value is None:
        return Priority.MEDIUM
    try:
        return Priority(value.lower())
    except ValueError:
        return Priority.MEDIUM


def _parse_applicability(data: dict | None) -> Applicability | None:
    """Parse applicability configuration."""
    if data is None:
        return None

    exclude_raw = data.get("exclude", [])
    if isinstance(exclude_raw, str):
        exclude_raw = [exclude_raw]

    return Applicability(
        glob=data.get("glob"),
        exclude=tuple(exclude_raw),
    )


def _parse_assertion(data: dict) -> Result[Assertion, str]:
    """Parse a single assertion from YAML data."""
    # Required fields
    assertion_id = data.get("id")
    if not assertion_id:
        return err("Assertion missing required 'id' field")

    type_str = data.get("type", "pattern")
    try:
        assertion_type = AssertionType(type_str)
    except ValueError:
        return err(f"Invalid assertion type: {type_str}")

    message = data.get("message")
    if not message:
        return err(f"Assertion '{assertion_id}' missing required 'message' field")

    # Optional fields with defaults
    severity = data.get("severity", "warning")
    if severity not in ("error", "warning", "info"):
        severity = "warning"

    priority = _parse_priority(data.get("priority"))

    # Pattern-specific fields
    pattern = data.get("pattern")
    if assertion_type == AssertionType.PATTERN and not pattern:
        return err(f"Pattern assertion '{assertion_id}' missing required 'pattern' field")

    # Languages
    languages_raw = data.get("languages", [])
    if isinstance(languages_raw, str):
        languages_raw = [languages_raw]
    languages = tuple(lang.lower() for lang in languages_raw)

    # Applicability
    applicability = _parse_applicability(data.get("applicability"))

    # LLM-specific fields (v0.5+)
    compliance = data.get("compliance")
    model = data.get("model")

    return ok(
        Assertion(
            id=assertion_id,
            type=assertion_type,
            message=message,
            severity=severity,  # type: ignore[arg-type]
            priority=priority,
            pattern=pattern,
            languages=languages,
            applicability=applicability,
            compliance=compliance,
            model=model,
        )
    )


def _validate_assertion_file(data: dict, path: str) -> Result[AssertionFile, str]:
    """Validate and parse an assertion file."""
    version = data.get("version", "0.4")
    name = data.get("name", "")
    description = data.get("description", "")

    assertions_data = data.get("assertions", [])
    if not isinstance(assertions_data, list):
        return err(f"{path}: 'assertions' must be a list")

    assertions: list[Assertion] = []
    for i, assertion_data in enumerate(assertions_data):
        if not isinstance(assertion_data, dict):
            return err(f"{path}: assertion {i} must be an object")

        result = _parse_assertion(assertion_data)
        if result.is_err:
            return err(f"{path}: {result.error}")
        assertions.append(result.value)

    # Check for duplicate IDs
    seen_ids: set[str] = set()
    for assertion in assertions:
        if assertion.id in seen_ids:
            return err(f"{path}: duplicate assertion ID '{assertion.id}'")
        seen_ids.add(assertion.id)

    return ok(
        AssertionFile(
            version=str(version),
            name=name,
            description=description,
            assertions=tuple(assertions),
            source="",  # Set by caller
            path=path,
        )
    )


@lru_cache(maxsize=64)
def _load_assertion_file_cached(path_str: str) -> AssertionFile | str:
    """Internal cached assertion file loader.

    Returns AssertionFile on success, error string on failure.
    """
    path = Path(path_str)
    try:
        content = path.read_text()
        data = yaml.safe_load(content)
    except OSError as e:
        return f"Failed to read '{path}': {e}"
    except yaml.YAMLError as e:
        return f"Invalid YAML in '{path}': {e}"

    if not isinstance(data, dict):
        return f"'{path}' must contain a YAML object"

    result = _validate_assertion_file(data, str(path))
    if result.is_err:
        return result.error

    return result.value


def load_assertion_file(filename: str) -> Result[AssertionFile, str]:
    """Load a single assertion file by name with cascade resolution.

    Args:
        filename: Assertion file name (e.g., "security.yaml")

    Returns:
        Result containing AssertionFile or error message
    """
    path, source = resolve_assertion_file(filename)
    if path is None:
        return err(f"Assertion file '{filename}' not found")

    cached = _load_assertion_file_cached(str(path))
    if isinstance(cached, str):
        return err(cached)

    # Return a new AssertionFile with the correct source
    return ok(
        AssertionFile(
            version=cached.version,
            name=cached.name,
            description=cached.description,
            assertions=cached.assertions,
            source=source,
            path=str(path),
        )
    )


def load_assertions(filenames: set[str] | None = None) -> tuple[list[Assertion], list[str]]:
    """Load all assertions from specified or all available files.

    Args:
        filenames: Specific files to load (if None, loads all)

    Returns:
        Tuple of (list of assertions, list of error messages)
    """
    if filenames is None:
        filenames = get_all_assertion_files()

    assertions: list[Assertion] = []
    errors: list[str] = []

    for filename in sorted(filenames):
        result = load_assertion_file(filename)
        if result.is_err:
            errors.append(result.error)
        else:
            assertions.extend(result.value.assertions)

    # Sort by priority (critical first)
    assertions.sort(key=lambda a: a.priority.rank)

    return assertions, errors


def clear_assertion_cache() -> None:
    """Clear the assertion loading cache. Useful for testing or after updates."""
    _load_assertion_file_cached.cache_clear()
