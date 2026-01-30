"""Tests for git operations."""

import tempfile
from pathlib import Path

import pytest

from crucible.models import Severity, ToolFinding
from crucible.tools.git import (
    GitChange,
    GitContext,
    LineRange,
    _lines_to_ranges,
    _parse_changes,
    get_changed_files,
    get_repo_root,
    is_git_repo,
    parse_diff_line_ranges,
)


class TestLineRange:
    """Test LineRange functionality."""

    def test_contains_within_range(self) -> None:
        r = LineRange(start=10, end=20)
        assert r.contains(10) is True
        assert r.contains(15) is True
        assert r.contains(20) is True

    def test_contains_outside_range(self) -> None:
        r = LineRange(start=10, end=20)
        assert r.contains(9) is False
        assert r.contains(21) is False

    def test_single_line_range(self) -> None:
        r = LineRange(start=5, end=5)
        assert r.contains(5) is True
        assert r.contains(4) is False
        assert r.contains(6) is False


class TestLinesToRanges:
    """Test conversion of line numbers to ranges."""

    def test_empty_list(self) -> None:
        assert _lines_to_ranges([]) == []

    def test_single_line(self) -> None:
        ranges = _lines_to_ranges([5])
        assert len(ranges) == 1
        assert ranges[0].start == 5
        assert ranges[0].end == 5

    def test_consecutive_lines(self) -> None:
        ranges = _lines_to_ranges([1, 2, 3, 4, 5])
        assert len(ranges) == 1
        assert ranges[0].start == 1
        assert ranges[0].end == 5

    def test_multiple_ranges(self) -> None:
        ranges = _lines_to_ranges([1, 2, 3, 10, 11, 20])
        assert len(ranges) == 3
        assert ranges[0] == LineRange(start=1, end=3)
        assert ranges[1] == LineRange(start=10, end=11)
        assert ranges[2] == LineRange(start=20, end=20)


class TestParseDiffLineRanges:
    """Test parsing of unified diff output."""

    def test_empty_diff(self) -> None:
        result = parse_diff_line_ranges("")
        assert result == {}

    def test_simple_addition(self) -> None:
        diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 line1
+new line
 line2
 line3
"""
        result = parse_diff_line_ranges(diff)
        assert "test.py" in result
        assert len(result["test.py"]) == 1
        assert result["test.py"][0] == LineRange(start=2, end=2)

    def test_multiple_additions(self) -> None:
        diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,2 +1,4 @@
+new line 1
 original line
+new line 2
+new line 3
"""
        result = parse_diff_line_ranges(diff)
        assert "test.py" in result
        # Lines 1, 3, 4 are additions (not consecutive from diff perspective)
        # Line 1 is added, line 2 is context, lines 3-4 are added
        ranges = result["test.py"]
        # Should have line 1 as one range, and lines 3-4 as another
        assert LineRange(start=1, end=1) in ranges
        assert LineRange(start=3, end=4) in ranges

    def test_multiple_files(self) -> None:
        diff = """diff --git a/file1.py b/file1.py
--- a/file1.py
+++ b/file1.py
@@ -1 +1,2 @@
 existing
+new in file1
diff --git a/file2.py b/file2.py
--- a/file2.py
+++ b/file2.py
@@ -1 +1,2 @@
 existing
+new in file2
"""
        result = parse_diff_line_ranges(diff)
        assert "file1.py" in result
        assert "file2.py" in result

    def test_new_file(self) -> None:
        diff = """diff --git a/newfile.py b/newfile.py
new file mode 100644
--- /dev/null
+++ b/newfile.py
@@ -0,0 +1,3 @@
+line 1
+line 2
+line 3
"""
        result = parse_diff_line_ranges(diff)
        assert "newfile.py" in result
        ranges = result["newfile.py"]
        assert len(ranges) == 1
        assert ranges[0] == LineRange(start=1, end=3)

    def test_deletion_only_no_ranges(self) -> None:
        diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,2 @@
 line1
-deleted line
 line2
"""
        result = parse_diff_line_ranges(diff)
        # Deletions don't create added line ranges
        assert result.get("test.py", []) == []


class TestGitChange:
    """Test GitChange dataclass."""

    def test_basic_change(self) -> None:
        change = GitChange(
            path="test.py",
            status="M",
            added_lines=(LineRange(1, 10),),
        )
        assert change.path == "test.py"
        assert change.status == "M"
        assert len(change.added_lines) == 1

    def test_renamed_file(self) -> None:
        change = GitChange(
            path="new_name.py",
            status="R",
            added_lines=(),
            old_path="old_name.py",
        )
        assert change.old_path == "old_name.py"


class TestGitContext:
    """Test GitContext dataclass."""

    def test_basic_context(self) -> None:
        ctx = GitContext(
            mode="staged",
            base_ref=None,
            changes=(),
        )
        assert ctx.mode == "staged"
        assert ctx.commit_messages is None

    def test_branch_context(self) -> None:
        ctx = GitContext(
            mode="branch",
            base_ref="main",
            changes=(),
            commit_messages=("feat: add feature", "fix: bug fix"),
        )
        assert ctx.base_ref == "main"
        assert len(ctx.commit_messages) == 2


class TestGetChangedFiles:
    """Test get_changed_files helper."""

    def test_excludes_deleted(self) -> None:
        ctx = GitContext(
            mode="staged",
            base_ref=None,
            changes=(
                GitChange(path="added.py", status="A", added_lines=()),
                GitChange(path="modified.py", status="M", added_lines=()),
                GitChange(path="deleted.py", status="D", added_lines=()),
            ),
        )
        files = get_changed_files(ctx)
        assert "added.py" in files
        assert "modified.py" in files
        assert "deleted.py" not in files


class TestParseChanges:
    """Test _parse_changes function."""

    def test_basic_parse(self) -> None:
        diff_output = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1 +1,2 @@
 line
+new
"""
        status_output = "M\ttest.py"
        changes = _parse_changes(diff_output, status_output)
        assert len(changes) == 1
        assert changes[0].path == "test.py"
        assert changes[0].status == "M"

    def test_multiple_statuses(self) -> None:
        status_output = """A\tnew.py
M\tmodified.py
D\tdeleted.py"""
        changes = _parse_changes("", status_output)
        assert len(changes) == 3
        statuses = {c.path: c.status for c in changes}
        assert statuses["new.py"] == "A"
        assert statuses["modified.py"] == "M"
        assert statuses["deleted.py"] == "D"


class TestIsGitRepo:
    """Test is_git_repo function."""

    def test_current_dir_is_repo(self) -> None:
        # The crucible project itself is a git repo
        assert is_git_repo(".") is True

    def test_temp_dir_is_not_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            assert is_git_repo(tmpdir) is False

    def test_nonexistent_path(self) -> None:
        assert is_git_repo("/nonexistent/path/12345") is False


class TestGetRepoRoot:
    """Test get_repo_root function."""

    def test_current_dir(self) -> None:
        result = get_repo_root(".")
        assert result.is_ok
        assert Path(result.value).exists()

    def test_non_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_repo_root(tmpdir)
            assert result.is_err
            assert "Not a git repository" in result.error


class TestFindingFiltering:
    """Test finding filtering logic."""

    def test_filter_findings_in_changed_lines(self) -> None:
        # Import the filter function from server
        from crucible.review.core import filter_findings_to_changes

        findings = [
            ToolFinding(
                tool="ruff",
                rule="E501",
                severity=Severity.LOW,
                message="Line too long",
                location="src/test.py:5",
            ),
            ToolFinding(
                tool="ruff",
                rule="E501",
                severity=Severity.LOW,
                message="Line too long",
                location="src/test.py:100",  # Not in changed lines
            ),
        ]

        context = GitContext(
            mode="staged",
            base_ref=None,
            changes=(
                GitChange(
                    path="src/test.py",
                    status="M",
                    added_lines=(LineRange(1, 10),),
                ),
            ),
        )

        filtered = filter_findings_to_changes(findings, context)
        assert len(filtered) == 1
        assert filtered[0].location == "src/test.py:5"

    def test_filter_with_context_lines(self) -> None:
        from crucible.review.core import filter_findings_to_changes

        findings = [
            ToolFinding(
                tool="ruff",
                rule="E501",
                severity=Severity.LOW,
                message="Line too long",
                location="test.py:15",  # Within 5 lines of change
            ),
            ToolFinding(
                tool="ruff",
                rule="E501",
                severity=Severity.LOW,
                message="Line too long",
                location="test.py:30",  # Far from change
            ),
        ]

        context = GitContext(
            mode="staged",
            base_ref=None,
            changes=(
                GitChange(
                    path="test.py",
                    status="M",
                    added_lines=(LineRange(10, 10),),
                ),
            ),
        )

        # Without context
        filtered = filter_findings_to_changes(findings, context, include_context=False)
        assert len(filtered) == 0

        # With context (within 5 lines)
        filtered = filter_findings_to_changes(findings, context, include_context=True)
        assert len(filtered) == 1
        assert filtered[0].location == "test.py:15"

    def test_filter_excludes_deleted_files(self) -> None:
        from crucible.review.core import filter_findings_to_changes

        findings = [
            ToolFinding(
                tool="ruff",
                rule="E501",
                severity=Severity.LOW,
                message="Line too long",
                location="deleted.py:5",
            ),
        ]

        context = GitContext(
            mode="staged",
            base_ref=None,
            changes=(
                GitChange(
                    path="deleted.py",
                    status="D",
                    added_lines=(),
                ),
            ),
        )

        filtered = filter_findings_to_changes(findings, context)
        assert len(filtered) == 0
