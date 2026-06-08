#!/bin/bash
# Tests for src/crucible/interfaces/claude_code/user_prompt_submit/route.sh
# Hermetic; runs the hook under the interpreter its shebang resolves to.

set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/src/crucible/interfaces/claude_code/user_prompt_submit/route.sh"
FAILED=0
RUNNER="${RUNNER:-/bin/bash}"
echo "Running route.sh tests under: $RUNNER ($($RUNNER --version | head -1))"

# crucible must be importable on PATH for routing to work.
if ! command -v crucible >/dev/null 2>&1; then
    echo "SKIP: crucible CLI not on PATH"
    exit 0
fi

assert_exit() {
    local expected="$1" json="$2" label="$3"
    printf '%s' "$json" | $RUNNER "$HOOK" >/dev/null 2>&1
    local actual=$?
    if [[ "$actual" != "$expected" ]]; then
        echo "FAIL [$label]: expected exit $expected, got $actual"
        FAILED=$((FAILED + 1))
    fi
}

# T1: feature request, no spec, advisory default → exit 0
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
assert_exit 0 '{"user_prompt":"please build a feature for user export"}' "feature-advisory-exit0"
cd /; rm -rf "$SCRATCH"

# T2: strict mode → exit 2
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible; touch .crucible/spec-gate.strict
assert_exit 2 '{"user_prompt":"please build a feature for user export"}' "feature-strict-exit2"
cd /; rm -rf "$SCRATCH"

# T3: exploration bypass even in strict mode → exit 0, bypass logged
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible; touch .crucible/spec-gate.strict
printf 'mode=exploration\n' > .crucible/mode.session
printf '{"user_prompt":"please build a feature for user export"}' | $RUNNER "$HOOK" >/dev/null 2>&1
CODE=$?
if [[ "$CODE" != "0" ]]; then echo "FAIL [explore-bypass-exit0]: got $CODE"; FAILED=$((FAILED+1)); fi
if [[ ! -f .crucible/inbox/spec-bypasses ]]; then echo "FAIL [explore-bypass-logged]"; FAILED=$((FAILED+1)); fi
cd /; rm -rf "$SCRATCH"

# T4: bug fix doesn't trip the gate → exit 0 even in strict mode
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible; touch .crucible/spec-gate.strict
assert_exit 0 '{"user_prompt":"fix the crash in the parser"}' "bugfix-no-gate-exit0"
cd /; rm -rf "$SCRATCH"

# T5: feature request WITH a spec present → exit 0 in strict mode
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible; touch .crucible/spec-gate.strict
printf '# PRD: Export\n\nreqs\n' > export-prd.md
assert_exit 0 '{"user_prompt":"please build a feature for user export"}' "feature-with-spec-exit0"
cd /; rm -rf "$SCRATCH"

# T6: not initialized (no .crucible) → exit 0
SCRATCH=$(mktemp -d); cd "$SCRATCH"
assert_exit 0 '{"user_prompt":"build a feature"}' "no-crucible-dir-exit0"
cd /; rm -rf "$SCRATCH"

if [[ $FAILED -eq 0 ]]; then
    echo "All route.sh tests passed."
    exit 0
else
    echo "$FAILED route.sh tests FAILED."
    exit 1
fi
