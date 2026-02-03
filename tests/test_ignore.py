"""Tests for crucible.ignore module."""

from pathlib import Path

import pytest

from crucible.ignore import (
    DEFAULT_PATTERNS,
    IgnorePattern,
    IgnoreSpec,
    clear_ignore_cache,
    load_ignore_spec,
    parse_ignore_file,
    should_ignore,
)


class TestIgnorePattern:
    """Tests for IgnorePattern matching."""

    def test_simple_glob(self) -> None:
        """Simple glob patterns match files."""
        pattern = IgnorePattern(pattern="*.log")
        assert pattern.matches("error.log", is_dir=False)
        assert pattern.matches("logs/error.log", is_dir=False)
        assert not pattern.matches("error.txt", is_dir=False)

    def test_directory_pattern(self) -> None:
        """Directory patterns match directories and files inside them."""
        pattern = IgnorePattern(pattern="node_modules/", directory_only=True)
        # Matches files inside the directory
        assert pattern.matches("node_modules/foo.js", is_dir=False)
        assert pattern.matches("src/node_modules/bar.js", is_dir=False)
        # Matches the directory itself
        assert pattern.matches("node_modules", is_dir=True)
        # Does not match files with similar names
        assert not pattern.matches("node_modules_backup.txt", is_dir=False)

    def test_dot_directory(self) -> None:
        """Directories starting with . are matched correctly."""
        pattern = IgnorePattern(pattern=".next/", directory_only=True)
        assert pattern.matches(".next/build.js", is_dir=False)
        assert pattern.matches("apps/web/.next/cache.js", is_dir=False)
        assert pattern.matches(".next", is_dir=True)

    def test_hidden_files(self) -> None:
        """Hidden files are matched."""
        pattern = IgnorePattern(pattern=".DS_Store")
        assert pattern.matches(".DS_Store", is_dir=False)
        assert pattern.matches("src/.DS_Store", is_dir=False)

    def test_nested_path(self) -> None:
        """Nested path patterns match correctly."""
        pattern = IgnorePattern(pattern="__pycache__/", directory_only=True)
        assert pattern.matches("src/__pycache__/mod.pyc", is_dir=False)
        assert pattern.matches("__pycache__/mod.pyc", is_dir=False)


class TestIgnoreSpec:
    """Tests for IgnoreSpec collection."""

    def test_is_ignored_basic(self) -> None:
        """Basic ignore checking works."""
        spec = IgnoreSpec(
            patterns=[
                IgnorePattern(pattern="*.log"),
                IgnorePattern(pattern="node_modules/", directory_only=True),
            ]
        )
        assert spec.is_ignored("error.log")
        assert spec.is_ignored("node_modules/foo.js")
        assert not spec.is_ignored("src/main.py")

    def test_negation(self) -> None:
        """Negated patterns un-ignore files."""
        spec = IgnoreSpec(
            patterns=[
                IgnorePattern(pattern="*.log"),
                IgnorePattern(pattern="important.log", negated=True),
            ]
        )
        assert spec.is_ignored("error.log")
        assert not spec.is_ignored("important.log")

    def test_filter_paths(self) -> None:
        """Filter paths removes ignored ones."""
        spec = IgnoreSpec(
            patterns=[IgnorePattern(pattern="*.pyc")],
        )
        base = Path("/project")
        paths = [
            Path("/project/main.py"),
            Path("/project/__pycache__/main.pyc"),
            Path("/project/util.py"),
        ]
        filtered = spec.filter_paths(paths, base)
        assert len(filtered) == 2
        assert Path("/project/main.py") in filtered
        assert Path("/project/util.py") in filtered


class TestParseIgnoreFile:
    """Tests for parsing .crucibleignore files."""

    def test_parse_simple(self) -> None:
        """Simple patterns are parsed."""
        content = """
*.log
node_modules/
"""
        patterns = parse_ignore_file(content)
        assert len(patterns) == 2
        assert patterns[0].pattern == "*.log"
        assert patterns[1].pattern == "node_modules/"
        assert patterns[1].directory_only

    def test_parse_comments(self) -> None:
        """Comments and blank lines are ignored."""
        content = """
# This is a comment
*.log

# Another comment
build/
"""
        patterns = parse_ignore_file(content)
        assert len(patterns) == 2

    def test_parse_negation(self) -> None:
        """Negated patterns are parsed."""
        content = """
*.log
!important.log
"""
        patterns = parse_ignore_file(content)
        assert len(patterns) == 2
        assert not patterns[0].negated
        assert patterns[1].negated
        assert patterns[1].pattern == "important.log"


class TestLoadIgnoreSpec:
    """Tests for loading ignore specs."""

    def test_default_patterns_included(self) -> None:
        """Default patterns are always included."""
        clear_ignore_cache()
        spec = load_ignore_spec()
        assert len(spec.patterns) >= len(DEFAULT_PATTERNS)
        # Check some key defaults
        assert spec.is_ignored("node_modules/foo.js")
        assert spec.is_ignored(".git/config")
        assert spec.is_ignored("__pycache__/mod.pyc")

    def test_project_file_override(self, tmp_path: Path) -> None:
        """Project .crucibleignore overrides defaults."""
        clear_ignore_cache()
        crucible_dir = tmp_path / ".crucible"
        crucible_dir.mkdir()
        ignore_file = crucible_dir / ".crucibleignore"
        ignore_file.write_text("custom_ignore/\n")

        spec = load_ignore_spec(tmp_path)
        assert spec.source == "project"
        assert spec.is_ignored("custom_ignore/file.txt")
        # Defaults still apply
        assert spec.is_ignored("node_modules/foo.js")


class TestDefaultPatterns:
    """Tests for default ignore patterns."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("node_modules/react/index.js", True),
            (".next/build/manifest.json", True),
            (".git/objects/abc123", True),
            ("__pycache__/module.cpython-311.pyc", True),
            (".venv/lib/python3.11/site.py", True),
            ("dist/bundle.js", True),
            ("build/output.o", True),
            ("package-lock.json", True),
            ("yarn.lock", True),
            ("src/main.py", False),
            ("components/Button.tsx", False),
            ("contracts/Token.sol", False),
        ],
    )
    def test_default_ignore_patterns(self, path: str, expected: bool) -> None:
        """Default patterns ignore common non-source files."""
        clear_ignore_cache()
        spec = load_ignore_spec()
        assert spec.is_ignored(path) == expected, f"{path} should be {'ignored' if expected else 'included'}"
