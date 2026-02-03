"""File ignore patterns for Crucible.

Supports .crucibleignore files with gitignore-style syntax.

Cascade priority (first found wins):
1. .crucible/.crucibleignore (project)
2. ~/.claude/crucible/.crucibleignore (user)
3. Built-in defaults

Pattern syntax (subset of gitignore):
- Standard glob patterns: *.log, build/
- Directory markers: node_modules/ matches directory anywhere
- Negation: !important.log (include despite earlier exclusion)
- Comments: # this is a comment
- Blank lines are ignored
"""

from dataclasses import dataclass, field
from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path

# Default patterns - always applied as base
DEFAULT_PATTERNS = [
    # Version control
    ".git/",
    ".hg/",
    ".svn/",
    # Dependencies
    "node_modules/",
    "vendor/",
    "bower_components/",
    # Python
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    ".venv/",
    "venv/",
    ".env/",
    "env/",
    ".tox/",
    ".nox/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "*.egg-info/",
    # Build outputs
    "build/",
    "dist/",
    "out/",
    "target/",
    "_build/",
    # IDE/Editor
    ".idea/",
    ".vscode/",
    "*.swp",
    "*.swo",
    "*~",
    ".DS_Store",
    # Coverage/test artifacts
    "coverage/",
    ".coverage",
    "htmlcov/",
    ".nyc_output/",
    # Logs
    "*.log",
    "logs/",
    # Lock files (large, not useful to review)
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    "composer.lock",
    "Gemfile.lock",
    # Other common excludes
    ".next/",
    ".nuxt/",
    ".output/",
    ".cache/",
    ".parcel-cache/",
    ".turbo/",
]

# Ignore file locations (cascade priority)
IGNORE_PROJECT = Path(".crucible") / ".crucibleignore"
IGNORE_USER = Path.home() / ".claude" / "crucible" / ".crucibleignore"


@dataclass(frozen=True)
class IgnorePattern:
    """A parsed ignore pattern."""

    pattern: str
    negated: bool = False
    directory_only: bool = False

    def matches(self, path: str, is_dir: bool = False) -> bool:
        """Check if this pattern matches the given path.

        Args:
            path: Relative path to check (forward slashes)
            is_dir: Whether the path is a directory

        Returns:
            True if pattern matches
        """
        # Normalize pattern for matching
        pattern = self.pattern.rstrip("/")

        # If pattern contains /, match against full path
        if "/" in pattern:
            if fnmatch(path, pattern) or fnmatch(path, f"**/{pattern}"):
                # For directory-only patterns on a file, only match if path is under that dir
                if self.directory_only and not is_dir:
                    # Check if pattern matches a parent directory
                    return f"{pattern}/" in path or path.startswith(f"{pattern}/")
                return True
            return False

        # Otherwise, match against any path component
        parts = path.split("/")
        for i, part in enumerate(parts):
            if fnmatch(part, pattern):
                if self.directory_only:
                    # Directory-only patterns match if:
                    # 1. This component is not the last (so it's a directory in the path), OR
                    # 2. The path itself is a directory
                    if i < len(parts) - 1 or is_dir:
                        return True
                else:
                    return True

        return False


@dataclass
class IgnoreSpec:
    """Collection of ignore patterns with match logic."""

    patterns: list[IgnorePattern] = field(default_factory=list)
    source: str = "default"

    def is_ignored(self, path: str | Path, is_dir: bool = False) -> bool:
        """Check if a path should be ignored.

        Patterns are evaluated in order. Later patterns can override earlier ones.
        Negated patterns (starting with !) un-ignore previously ignored paths.

        Args:
            path: Path to check (relative to project root)
            is_dir: Whether the path is a directory

        Returns:
            True if the path should be ignored
        """
        if isinstance(path, Path):
            path = str(path)

        # Normalize path separators and strip ./ prefix (but not lone .)
        path = path.replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]

        ignored = False
        for pattern in self.patterns:
            if pattern.matches(path, is_dir):
                ignored = not pattern.negated

        return ignored

    def filter_paths(self, paths: list[Path], base: Path | None = None) -> list[Path]:
        """Filter a list of paths, removing ignored ones.

        Args:
            paths: List of paths to filter
            base: Base path for computing relative paths

        Returns:
            List of non-ignored paths
        """
        result = []
        for path in paths:
            rel_path = path.relative_to(base) if base else path
            is_dir = path.is_dir()
            if not self.is_ignored(str(rel_path), is_dir):
                result.append(path)
        return result


def parse_ignore_file(content: str) -> list[IgnorePattern]:
    """Parse a .crucibleignore file into patterns.

    Args:
        content: File content

    Returns:
        List of parsed patterns
    """
    patterns = []

    for line in content.splitlines():
        # Strip whitespace
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Check for negation
        negated = False
        if line.startswith("!"):
            negated = True
            line = line[1:]

        # Check for directory-only marker
        directory_only = line.endswith("/")

        patterns.append(
            IgnorePattern(
                pattern=line,
                negated=negated,
                directory_only=directory_only,
            )
        )

    return patterns


def _load_ignore_file(path: Path) -> list[IgnorePattern]:
    """Load patterns from an ignore file."""
    try:
        content = path.read_text()
        return parse_ignore_file(content)
    except OSError:
        return []


@lru_cache(maxsize=1)
def _get_default_patterns() -> list[IgnorePattern]:
    """Get default patterns (cached)."""
    return parse_ignore_file("\n".join(DEFAULT_PATTERNS))


def load_ignore_spec(project_root: Path | None = None) -> IgnoreSpec:
    """Load ignore specification with cascade resolution.

    Args:
        project_root: Project root directory (defaults to cwd)

    Returns:
        IgnoreSpec with all applicable patterns
    """
    if project_root is None:
        project_root = Path.cwd()

    patterns: list[IgnorePattern] = []
    source = "default"

    # Start with defaults
    patterns.extend(_get_default_patterns())

    # Layer user patterns (if exists)
    if IGNORE_USER.exists():
        patterns.extend(_load_ignore_file(IGNORE_USER))
        source = "user"

    # Layer project patterns (highest priority)
    project_ignore = project_root / IGNORE_PROJECT
    if project_ignore.exists():
        patterns.extend(_load_ignore_file(project_ignore))
        source = "project"

    return IgnoreSpec(patterns=patterns, source=source)


def should_ignore(path: str | Path, project_root: Path | None = None) -> bool:
    """Convenience function to check if a path should be ignored.

    Args:
        path: Path to check
        project_root: Project root for loading ignore spec

    Returns:
        True if path should be ignored
    """
    spec = load_ignore_spec(project_root)
    is_dir = Path(path).is_dir() if isinstance(path, str) else path.is_dir()
    return spec.is_ignored(path, is_dir)


def clear_ignore_cache() -> None:
    """Clear the ignore pattern cache. Useful for testing."""
    _get_default_patterns.cache_clear()
