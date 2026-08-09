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


def changed_names(numstat=False):
    """Union of unstaged + staged changed files, or their numstat lines."""
    flag = "--numstat" if numstat else "--name-only"
    unstaged = run_git(["diff", flag, "HEAD"])
    staged = run_git(["diff", "--cached", flag])
    return unstaged, staged


def parse_names(*blobs):
    names = set()
    for blob in blobs:
        for line in blob.splitlines():
            line = line.strip()
            if line:
                names.add(line)
    return names


def parse_numstat_lines(*blobs):
    """path -> added+deleted lines, per diff blob.

    `git diff HEAD` (no --cached) compares the working tree to HEAD, so a
    file that is staged-only still shows its full delta there too — the
    same change appears in both the unstaged-vs-HEAD and staged-vs-HEAD
    listings. Each blob already reports that file's *total* change versus
    HEAD, so take the max across blobs per file rather than summing them
    (summing would double-count a staged-only change)."""
    counts: dict[str, int] = {}
    for blob in blobs:
        for line in blob.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, deleted, path = parts
            try:
                n = (int(added) if added != "-" else 0) + (int(deleted) if deleted != "-" else 0)
            except ValueError:
                continue
            counts[path] = max(counts.get(path, 0), n)
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

names_unstaged, names_staged = changed_names(numstat=False)
changed = parse_names(names_unstaged, names_staged)
if not changed:
    sys.exit(0)

# Only pay for numstat if some trigger actually needs line counts.
needs_lines = any(
    isinstance(t, dict) and t.get("min_changed_lines") for t in triggers
)
line_counts: dict[str, int] = {}
if needs_lines:
    numstat_unstaged, numstat_staged = changed_names(numstat=True)
    line_counts = parse_numstat_lines(numstat_unstaged, numstat_staged)

for trigger in triggers:
    if not isinstance(trigger, dict):
        continue
    paths = trigger.get("paths")
    note = trigger.get("note")
    if not isinstance(paths, list) or not paths or not note:
        continue
    min_lines = trigger.get("min_changed_lines") or 0

    matching_files = [
        f for f in changed
        if any(fnmatch(f, pattern) for pattern in paths)
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
