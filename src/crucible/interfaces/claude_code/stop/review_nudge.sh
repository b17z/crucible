#!/bin/bash
# review_nudge.sh — Stop hook for Crucible v2 (Phase 7)
#
# Evaluates the project's REVIEW.md frontmatter (Task 8 format: a
# `triggers:` list of {paths, min_changed_lines?, note}) against the
# files changed since HEAD (union of unstaged + staged). A trigger
# matches when any changed file fnmatches any of its `paths` globs AND
# the total changed lines across those matching files is at least
# `min_changed_lines` (absent = 0, i.e. any touch matches). One stderr
# line is printed per matched trigger.
#
# ADVISORY ONLY — always exits 0. Silent on: no REVIEW.md, not a git
# repo, no python3, no PyYAML, malformed frontmatter, or no matches.
#
# Installation: registered by `crucible hooks claudecode init` under
# Stop with no matcher.

set -uo pipefail

[[ -f REVIEW.md ]] || exit 0

git rev-parse --git-dir >/dev/null 2>&1 || exit 0

command -v python3 >/dev/null 2>&1 || exit 0

python3 - << 'PY'
import subprocess
import sys
from fnmatch import fnmatch

try:
    import yaml
except ImportError:
    sys.exit(0)


def run_git(args):
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def changed_names():
    """Union of unstaged + staged changed file names (for glob matching).

    Both listings are needed here: a file can be staged-only (only shows
    up under --cached) or have unstaged-only changes."""
    unstaged = run_git(["diff", "--name-only", "HEAD"])
    staged = run_git(["diff", "--cached", "--name-only", "HEAD"])
    return unstaged, staged


def parse_names(*blobs):
    names = set()
    for blob in blobs:
        for line in blob.splitlines():
            line = line.strip()
            if line:
                names.add(line)
    return names


def _matches(path, pattern):
    """Match `path` against a REVIEW.md glob `pattern`.

    `fnmatch` treats `**` as no different from a single `*` — it is not
    special like it is in gitignore/git-pathspec globbing, and `*`
    (single or double) never crosses `/` boundaries either way. That
    means the natural-looking authoring patterns `**/auth*` and
    `src/**/*.py` do NOT match root-level `auth.py` or `src/x.py`
    respectively (both need at least one path segment to sit where the
    `**/` implies "zero or more directories"). Try a few equivalent
    forms so those authoring patterns work as intended:
      - the pattern as-written, verbatim fnmatch;
      - a leading `**/` also tried with that prefix stripped, against
        both the full path and just its basename (covers the "zero
        directories" case for both `**/auth*` and `src/**/auth*`-style
        interior globs... but only for a *leading* `**/`);
      - `/**/` collapsed to `/` anywhere in the pattern (covers the
        "zero directories" case for interior globs like `src/**/*.py`).
    """
    if fnmatch(path, pattern):
        return True
    if pattern.startswith("**/"):
        stripped = pattern[3:]
        if fnmatch(path, stripped) or fnmatch(path.rsplit("/", 1)[-1], stripped):
            return True
    if "/**/" in pattern:
        collapsed = pattern.replace("/**/", "/")
        if fnmatch(path, collapsed):
            return True
    return False


def parse_numstat_lines():
    """path -> added+deleted lines, from `git diff --numstat HEAD` alone.

    Unlike --name-only, `git diff HEAD` (no --cached) already compares the
    working tree directly to HEAD — it is the complete HEAD-to-worktree
    delta for every file, independent of staging state. --cached numstat
    is NOT needed and must not be merged in: it reflects only the index,
    which can be stale relative to the worktree (e.g. staged 5->25 lines,
    then partially reverted the worktree to 12 lines — the true total is
    7, but the staged blob still says 20). A file staged-then-fully-
    reverted to match HEAD legitimately has 0 changed lines and simply
    won't appear in this listing."""
    counts: dict[str, int] = {}
    blob = run_git(["diff", "--numstat", "HEAD"])
    for line in blob.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        try:
            n = (int(added) if added != "-" else 0) + (int(deleted) if deleted != "-" else 0)
        except ValueError:
            continue
        counts[path] = n
    return counts


try:
    content = open("REVIEW.md", encoding="utf-8").read()
except OSError:
    sys.exit(0)

if not content.startswith("---"):
    sys.exit(0)

lines = content.split("\n")
end_idx = None
for i, line in enumerate(lines[1:], 1):
    if line.strip() == "---":
        end_idx = i
        break

if end_idx is None:
    sys.exit(0)

frontmatter_text = "\n".join(lines[1:end_idx])

try:
    data = yaml.safe_load(frontmatter_text)
except yaml.YAMLError:
    sys.exit(0)

if not isinstance(data, dict):
    sys.exit(0)

triggers = data.get("triggers")
if not isinstance(triggers, list) or not triggers:
    sys.exit(0)

names_unstaged, names_staged = changed_names()
changed = parse_names(names_unstaged, names_staged)
if not changed:
    sys.exit(0)

# Only pay for numstat if some trigger actually needs line counts.
needs_lines = any(
    isinstance(t, dict) and t.get("min_changed_lines") for t in triggers
)
line_counts: dict[str, int] = {}
if needs_lines:
    line_counts = parse_numstat_lines()

for trigger in triggers:
    if not isinstance(trigger, dict):
        continue
    paths = trigger.get("paths")
    note = trigger.get("note")
    if not isinstance(paths, list) or not paths or not note:
        continue

    # Malformed trigger values are skipped silently, matching the silent-on-malformed contract.
    raw_min_lines = trigger.get("min_changed_lines")
    try:
        min_lines = int(raw_min_lines) if raw_min_lines else 0
    except (TypeError, ValueError):
        continue

    matching_files = [
        f for f in changed
        if any(_matches(f, pattern) for pattern in paths)
    ]
    if not matching_files:
        continue

    total_lines = sum(line_counts.get(f, 0) for f in matching_files)
    if total_lines < min_lines:
        continue

    print(f"crucible: {note} (REVIEW.md trigger matched)", file=sys.stderr)

sys.exit(0)
PY
exit 0
