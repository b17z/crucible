#!/bin/bash
# Tests for src/crucible/interfaces/claude_code/stop/review_nudge.sh
#
# Hermetic — every test creates its own tmp git repo and tears it down.
#
# Runnable via:
#   bash tests/test_review_nudge.sh
# Exits 0 on success, non-zero if any test failed.

set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/src/crucible/interfaces/claude_code/stop/review_nudge.sh"
FAILED=0

RUNNER="${RUNNER:-/bin/bash}"
echo "Running review_nudge tests under: $RUNNER ($($RUNNER --version | head -1))"

# run_hook → captures stderr into $STDERR_OUT and exit code into $EXIT_CODE.
# The hook is always advisory: anything other than exit 0 is a failure.
run_hook() {
    STDERR_OUT=$($RUNNER "$HOOK" 2>&1 >/dev/null)
    EXIT_CODE=$?
}

assert_exit_zero() {
    local label="$1"
    if [[ "$EXIT_CODE" != 0 ]]; then
        echo "FAIL [$label]: expected exit 0, got $EXIT_CODE"
        FAILED=$((FAILED + 1))
    fi
}

assert_stderr_contains() {
    local needle="$1"
    local label="$2"
    if [[ "$STDERR_OUT" != *"$needle"* ]]; then
        echo "FAIL [$label]: stderr missing '$needle'"
        echo "  got: $STDERR_OUT"
        FAILED=$((FAILED + 1))
    fi
}

assert_stderr_empty() {
    local label="$1"
    if [[ -n "$STDERR_OUT" ]]; then
        echo "FAIL [$label]: expected silent, got: $STDERR_OUT"
        FAILED=$((FAILED + 1))
    fi
}

# init_repo → fresh git repo with committed baseline (empty) commit, cwd'd into it.
init_repo() {
    SCRATCH=$(mktemp -d)
    cd "$SCRATCH"
    git init -q
    git -c user.email=t@t -c user.name=t commit -q --allow-empty -m "init"
}

teardown() {
    cd /
    rm -rf "$SCRATCH"
}

# write_review_md <content> → writes REVIEW.md with the given frontmatter+body.
write_review_md() {
    printf '%s' "$1" > REVIEW.md
}

# nlines <count> → writes $count newline-terminated lines to stdout.
nlines() {
    local n="$1"
    local i=0
    while [[ "$i" -lt "$n" ]]; do
        printf 'line %d\n' "$i"
        i=$((i + 1))
    done
}

# --- no REVIEW.md → silent 0 ---
init_repo
run_hook
assert_exit_zero "no-review-md-exit"
assert_stderr_empty "no-review-md-silent"
teardown

# --- not a git repo → silent 0 ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
write_review_md $'---\ntriggers:\n  - paths: ["*.py"]\n    note: "review please"\n---\n# Review\n'
run_hook
assert_exit_zero "not-git-repo-exit"
assert_stderr_empty "not-git-repo-silent"
teardown

# --- glob match without min_changed_lines → nudge contains the note ---
init_repo
write_review_md $'---\ntriggers:\n  - paths: ["*.py"]\n    note: "Python change — please review"\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
echo "print('hi')" > foo.py
git add foo.py
run_hook
assert_exit_zero "glob-match-exit"
assert_stderr_contains "Python change — please review" "glob-match-note"
assert_stderr_contains "REVIEW.md trigger matched" "glob-match-suffix"
teardown

# --- non-matching path → silent 0 ---
init_repo
write_review_md $'---\ntriggers:\n  - paths: ["*.py"]\n    note: "Python change — please review"\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
echo "hello" > foo.txt
git add foo.txt
run_hook
assert_exit_zero "non-matching-path-exit"
assert_stderr_empty "non-matching-path-silent"
teardown

# --- min_changed_lines boundary: exactly N lines matches ---
init_repo
write_review_md $'---\ntriggers:\n  - paths: ["*.py"]\n    min_changed_lines: 10\n    note: "Substantial change"\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
nlines 10 > foo.py
git add foo.py
run_hook
assert_exit_zero "boundary-at-n-exit"
assert_stderr_contains "Substantial change" "boundary-at-n-matches"
teardown

# --- min_changed_lines boundary: N-1 lines does not match ---
init_repo
write_review_md $'---\ntriggers:\n  - paths: ["*.py"]\n    min_changed_lines: 10\n    note: "Substantial change"\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
nlines 9 > foo.py
git add foo.py
run_hook
assert_exit_zero "boundary-below-n-exit"
assert_stderr_empty "boundary-below-n-silent"
teardown

# --- staged-only change counted (unstaged working tree is clean) ---
init_repo
write_review_md $'---\ntriggers:\n  - paths: ["*.py"]\n    min_changed_lines: 5\n    note: "Staged change matters"\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
nlines 5 > bar.py
git add bar.py
# working tree has no unstaged diff for bar.py — it's fully staged.
run_hook
assert_exit_zero "staged-only-exit"
assert_stderr_contains "Staged change matters" "staged-only-counted"
teardown

# --- stage a large change, then partially revert the worktree: the true
# HEAD->worktree delta (not the stale staged delta) must drive the
# threshold. Baseline is 5 lines; stage a jump to 25 lines (staged delta
# 20, over the N=10 threshold), then edit the worktree back down to 12
# lines (true delta 7, under the threshold) — no nudge should fire.
init_repo
write_review_md $'---\ntriggers:\n  - paths: ["*.py"]\n    min_changed_lines: 10\n    note: "Substantial change"\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
nlines 5 > baz.py
git add baz.py
git -c user.email=t@t -c user.name=t commit -q -m "baz.py baseline"
nlines 25 > baz.py
git add baz.py
nlines 12 > baz.py
run_hook
assert_exit_zero "stale-staged-revert-exit"
assert_stderr_empty "stale-staged-revert-silent"
teardown

# --- malformed frontmatter → silent 0 ---
init_repo
write_review_md $'---\n{ not yaml [\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
echo "print('hi')" > foo.py
git add foo.py
run_hook
assert_exit_zero "malformed-frontmatter-exit"
assert_stderr_empty "malformed-frontmatter-silent"
teardown

# --- root-level file matches a leading-**/ pattern (fnmatch has no **
# special-casing — "**/auth*" must still match a root-level "auth.py") ---
init_repo
write_review_md $'---\ntriggers:\n  - paths: ["**/auth*"]\n    note: "Security-sensitive paths"\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
echo "def login(): pass" > auth.py
git add auth.py
run_hook
assert_exit_zero "root-level-double-star-exit"
assert_stderr_contains "Security-sensitive paths" "root-level-double-star-matches"
teardown

# --- root-level-under-dir file matches an interior /**/ pattern
# ("src/**/*.py" must still match "src/x.py" with zero intervening dirs) ---
init_repo
write_review_md $'---\ntriggers:\n  - paths: ["src/**/*.py"]\n    note: "Substantial source changes"\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
mkdir -p src
echo "print('hi')" > src/x.py
git add src/x.py
run_hook
assert_exit_zero "interior-double-star-exit"
assert_stderr_contains "Substantial source changes" "interior-double-star-matches"
teardown

# --- no trigger matches at all → silent 0 (multiple triggers, none match) ---
init_repo
write_review_md $'---\ntriggers:\n  - paths: ["**/auth*"]\n    note: "Security-sensitive"\n  - paths: ["*.rb"]\n    note: "Ruby change"\n---\n# Review\n'
git add REVIEW.md
git -c user.email=t@t -c user.name=t commit -q -m "add review.md"
echo "hello" > plain.txt
git add plain.txt
run_hook
assert_exit_zero "no-match-multi-exit"
assert_stderr_empty "no-match-multi-silent"
teardown

if [[ "$FAILED" -gt 0 ]]; then
    echo "$FAILED test(s) failed"
    exit 1
fi
echo "All review_nudge tests passed"
exit 0
