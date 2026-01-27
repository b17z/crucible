"""Git operations for change-aware code review."""

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from crucible.errors import Result, err, ok


@dataclass(frozen=True)
class LineRange:
    """A range of lines in a file."""

    start: int
    end: int

    def contains(self, line: int) -> bool:
        """Check if a line number is within this range."""
        return self.start <= line <= self.end


@dataclass(frozen=True)
class GitChange:
    """A changed file in git with its modified line ranges."""

    path: str
    status: str  # A=added, M=modified, D=deleted, R=renamed
    added_lines: tuple[LineRange, ...]
    old_path: str | None = None


@dataclass(frozen=True)
class GitContext:
    """Context about git changes for a review."""

    mode: str
    base_ref: str | None
    changes: tuple[GitChange, ...]
    commit_messages: tuple[str, ...] | None = None


def is_git_repo(path: str | Path) -> bool:
    """Check if the path is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def get_repo_root(path: str | Path) -> Result[str, str]:
    """Get the root directory of the git repository."""
    if not shutil.which("git"):
        return err("git not found")

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return err("Not a git repository")
        return ok(result.stdout.strip())
    except subprocess.TimeoutExpired:
        return err("git command timed out")
    except OSError as e:
        return err(f"Failed to run git: {e}")


def _run_git(args: list[str], cwd: str, timeout: int = 30) -> Result[str, str]:
    """Run a git command and return stdout or error."""
    if not shutil.which("git"):
        return err("git not found")

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "unknown revision" in stderr.lower() or "bad revision" in stderr.lower():
                return err(f"Unknown ref: {stderr}")
            return err(stderr or f"git {args[0]} failed")
        return ok(result.stdout)
    except subprocess.TimeoutExpired:
        return err(f"git command timed out after {timeout}s")
    except OSError as e:
        return err(f"Failed to run git: {e}")


def parse_diff_line_ranges(diff_output: str) -> dict[str, list[LineRange]]:
    """
    Parse unified diff output to extract added line ranges per file.

    Returns a dict mapping file paths to lists of LineRange for added/modified lines.
    """
    result: dict[str, list[LineRange]] = {}
    current_file: str | None = None

    # Match diff header: +++ b/path/to/file
    file_pattern = re.compile(r"^\+\+\+ b/(.+)$")
    # Match hunk header: @@ -old_start,old_count +new_start,new_count @@
    hunk_pattern = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    lines = diff_output.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for new file
        file_match = file_pattern.match(line)
        if file_match:
            current_file = file_match.group(1)
            if current_file not in result:
                result[current_file] = []
            i += 1
            continue

        # Check for hunk header
        hunk_match = hunk_pattern.match(line)
        if hunk_match and current_file:
            new_start = int(hunk_match.group(1))

            # Track which lines within this hunk are additions
            i += 1
            current_line = new_start
            hunk_added_lines: list[int] = []

            while i < len(lines):
                hunk_line = lines[i]
                if hunk_line.startswith("@@") or hunk_line.startswith("diff "):
                    break
                if hunk_line.startswith("+") and not hunk_line.startswith("+++"):
                    hunk_added_lines.append(current_line)
                    current_line += 1
                elif hunk_line.startswith("-") and not hunk_line.startswith("---"):
                    pass  # Deleted line, don't increment current_line
                else:
                    current_line += 1
                i += 1

            # Convert consecutive lines to ranges
            if hunk_added_lines:
                ranges = _lines_to_ranges(hunk_added_lines)
                result[current_file].extend(ranges)
            continue

        i += 1

    return result


def _lines_to_ranges(lines: list[int]) -> list[LineRange]:
    """Convert a sorted list of line numbers to LineRange objects."""
    if not lines:
        return []

    ranges: list[LineRange] = []
    start = lines[0]
    end = lines[0]

    for line in lines[1:]:
        if line == end + 1:
            end = line
        else:
            ranges.append(LineRange(start=start, end=end))
            start = line
            end = line

    ranges.append(LineRange(start=start, end=end))
    return ranges


def get_staged_changes(repo_path: str) -> Result[GitContext, str]:
    """Get staged changes (ready to commit)."""
    # Get diff of staged changes
    diff_result = _run_git(["diff", "--cached", "--unified=0"], repo_path)
    if diff_result.is_err:
        return err(diff_result.error)

    # Get list of staged files with status
    status_result = _run_git(["diff", "--cached", "--name-status"], repo_path)
    if status_result.is_err:
        return err(status_result.error)

    changes = _parse_changes(diff_result.value, status_result.value)
    return ok(GitContext(mode="staged", base_ref=None, changes=tuple(changes)))


def get_unstaged_changes(repo_path: str) -> Result[GitContext, str]:
    """Get unstaged changes (working directory)."""
    diff_result = _run_git(["diff", "--unified=0"], repo_path)
    if diff_result.is_err:
        return err(diff_result.error)

    status_result = _run_git(["diff", "--name-status"], repo_path)
    if status_result.is_err:
        return err(status_result.error)

    changes = _parse_changes(diff_result.value, status_result.value)
    return ok(GitContext(mode="unstaged", base_ref=None, changes=tuple(changes)))


def get_branch_diff(repo_path: str, base: str = "main") -> Result[GitContext, str]:
    """Get diff between current branch and base branch."""
    # Use three-dot diff to show changes since branching
    diff_result = _run_git(["diff", f"{base}...HEAD", "--unified=0"], repo_path)
    if diff_result.is_err:
        return err(diff_result.error)

    status_result = _run_git(["diff", f"{base}...HEAD", "--name-status"], repo_path)
    if status_result.is_err:
        return err(status_result.error)

    # Get commit messages since base
    log_result = _run_git(
        ["log", f"{base}..HEAD", "--pretty=format:%s", "--reverse"], repo_path
    )
    commit_messages = None
    if log_result.is_ok and log_result.value.strip():
        commit_messages = tuple(log_result.value.strip().split("\n"))

    changes = _parse_changes(diff_result.value, status_result.value)
    return ok(
        GitContext(
            mode="branch",
            base_ref=base,
            changes=tuple(changes),
            commit_messages=commit_messages,
        )
    )


def get_recent_commits(repo_path: str, count: int = 1) -> Result[GitContext, str]:
    """Get changes from recent N commits."""
    if count < 1:
        return err("Commit count must be at least 1")

    diff_result = _run_git(["diff", f"HEAD~{count}..HEAD", "--unified=0"], repo_path)
    if diff_result.is_err:
        return err(diff_result.error)

    status_result = _run_git(["diff", f"HEAD~{count}..HEAD", "--name-status"], repo_path)
    if status_result.is_err:
        return err(status_result.error)

    # Get commit messages
    log_result = _run_git(
        ["log", f"HEAD~{count}..HEAD", "--pretty=format:%s", "--reverse"], repo_path
    )
    commit_messages = None
    if log_result.is_ok and log_result.value.strip():
        commit_messages = tuple(log_result.value.strip().split("\n"))

    changes = _parse_changes(diff_result.value, status_result.value)
    return ok(
        GitContext(
            mode="commits",
            base_ref=f"HEAD~{count}",
            changes=tuple(changes),
            commit_messages=commit_messages,
        )
    )


def _parse_changes(diff_output: str, status_output: str) -> list[GitChange]:
    """Parse git diff and status output into GitChange objects."""
    # Parse line ranges from diff
    line_ranges = parse_diff_line_ranges(diff_output)

    # Parse file statuses
    changes: list[GitChange] = []
    for line in status_output.strip().split("\n"):
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        status = parts[0][0]  # First char of status (A, M, D, R)
        path = parts[-1]  # Last part is always the current path
        old_path = parts[1] if status == "R" and len(parts) > 2 else None

        # Get added lines for this file
        added_lines = tuple(line_ranges.get(path, []))

        changes.append(
            GitChange(
                path=path,
                status=status,
                added_lines=added_lines,
                old_path=old_path,
            )
        )

    return changes


def get_changed_files(context: GitContext) -> list[str]:
    """Get list of changed file paths from a git context (excluding deleted)."""
    return [c.path for c in context.changes if c.status != "D"]
