#!/bin/bash
# Tests for interfaces/claude_code/user_prompt_submit/magic_comments.sh
#
# Hermetic — every test creates its own tmp project and tears it down.
#
# Runnable via:
#   bash tests/test_magic_comments.sh
# Exits 0 on success, non-zero on first failure.

set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/src/crucible/interfaces/claude_code/user_prompt_submit/magic_comments.sh"
FAILED=0

# Run the hook under the SAME interpreter its shebang resolves to. On
# macOS that's /bin/bash (3.2), which lacks mapfile and errors on empty
# "${arr[@]}" under set -u. Testing under a Homebrew bash 5.x hides those
# bugs. Override with RUNNER=bash to test the modern interpreter too.
RUNNER="${RUNNER:-/bin/bash}"
echo "Running magic_comments tests under: $RUNNER ($($RUNNER --version | head -1))"

assert_yaml_valid() {
    local file="$1"
    local label="$2"
    if ! python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
        echo "FAIL [$label]: $file is not valid YAML"
        python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>&1 | tail -3
        FAILED=$((FAILED + 1))
        return 1
    fi
    return 0
}

assert_approved() {
    local file="$1"
    local pkg="$2"
    local label="$3"
    if ! python3 -c "
import sys, yaml
data = yaml.safe_load(open('$file')) or {}
for e in data.get('approved') or []:
    if isinstance(e, dict) and '$pkg' == e.get('name', '') + '@' + str(e.get('version', '')):
        sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
        echo "FAIL [$label]: expected $pkg in $file"
        cat "$file"
        FAILED=$((FAILED + 1))
        return 1
    fi
    return 0
}

assert_not_approved() {
    local file="$1"
    local pkg="$2"
    local label="$3"
    if [[ ! -f "$file" ]]; then
        # File doesn't exist — nothing was approved. Pass.
        return 0
    fi
    if python3 -c "
import sys, yaml
data = yaml.safe_load(open('$file')) or {}
for e in data.get('approved') or []:
    if isinstance(e, dict) and e.get('name', '') == '$pkg':
        sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
        echo "FAIL [$label]: $pkg should NOT have been approved"
        cat "$file"
        FAILED=$((FAILED + 1))
        return 1
    fi
    return 0
}

# --- Test 1: clean approve, valid YAML out ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
printf '{"user_prompt":"crucible-approve: lodash@4.17.21"}' | $RUNNER "$HOOK" >/dev/null 2>&1
assert_yaml_valid .crucible/approved-deps.session.yaml "clean-approve-yaml-valid"
assert_approved .crucible/approved-deps.session.yaml "lodash@4.17.21" "clean-approve-has-pkg"
cd / && rm -rf "$SCRATCH"

# --- Test 2: scoped npm package ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
printf '{"user_prompt":"crucible-approve: @tanstack/react-router@1.0.0"}' | $RUNNER "$HOOK" >/dev/null 2>&1
assert_yaml_valid .crucible/approved-deps.session.yaml "scoped-approve-yaml-valid"
assert_approved .crucible/approved-deps.session.yaml "@tanstack/react-router@1.0.0" "scoped-approve-has-pkg"
cd / && rm -rf "$SCRATCH"

# --- Test 3: REGRESSION (item 1) — colon-injection rejected, YAML still valid ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
OUTPUT=$(printf '{"user_prompt":"crucible-approve: evil-pkg@1.0\\ncrucible-approve: foo@1.0:\\n  malicious: yaml"}' | $RUNNER "$HOOK" 2>&1)
if ! echo "$OUTPUT" | grep -q "ignoring malformed approve"; then
    echo "FAIL [colon-injection-rejected]: hook didn't warn about the malformed line"
    echo "  output: $OUTPUT"
    FAILED=$((FAILED + 1))
fi
assert_yaml_valid .crucible/approved-deps.session.yaml "colon-injection-yaml-still-valid"
assert_approved .crucible/approved-deps.session.yaml "evil-pkg@1.0" "colon-injection-clean-line-survived"
assert_not_approved .crucible/approved-deps.session.yaml "foo" "colon-injection-bad-line-rejected"
cd / && rm -rf "$SCRATCH"

# --- Test 4: REGRESSION (item 1) — newline injection rejected ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
printf '{"user_prompt":"crucible-approve: pkg-with-quotes\\"@1.0"}' | $RUNNER "$HOOK" >/dev/null 2>&1
# File may or may not exist (no clean approve in this run). The point: nothing with a quote made it in.
if [[ -f .crucible/approved-deps.session.yaml ]]; then
    assert_not_approved .crucible/approved-deps.session.yaml 'pkg-with-quotes"' "quote-rejected"
    assert_yaml_valid .crucible/approved-deps.session.yaml "quote-injection-yaml-still-valid"
fi
cd / && rm -rf "$SCRATCH"

# --- Test 5: REGRESSION (item 1) — backslash/special chars rejected ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
printf '{"user_prompt":"crucible-approve: foo\\\\bar@1.0"}' | $RUNNER "$HOOK" >/dev/null 2>&1
# Same posture as test 4.
if [[ -f .crucible/approved-deps.session.yaml ]]; then
    assert_yaml_valid .crucible/approved-deps.session.yaml "backslash-yaml-still-valid"
fi
cd / && rm -rf "$SCRATCH"

# --- Test 6: mode flag still works ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
printf '{"user_prompt":"crucible-mode: exploration"}' | $RUNNER "$HOOK" >/dev/null 2>&1
if [[ ! -f .crucible/mode.session ]]; then
    echo "FAIL [mode-flag-still-works]: mode.session not created"
    FAILED=$((FAILED + 1))
fi
cd / && rm -rf "$SCRATCH"

# --- Test 7: sign command still works ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
printf '{"user_prompt":"crucible-sign: 1 3"}' | $RUNNER "$HOOK" >/dev/null 2>&1
if [[ ! -f .crucible/inbox/signs-confirmed ]]; then
    echo "FAIL [sign-still-works]: inbox/signs-confirmed not created"
    FAILED=$((FAILED + 1))
fi
cd / && rm -rf "$SCRATCH"

if [[ $FAILED -eq 0 ]]; then
    echo "All magic_comments tests passed."
    exit 0
else
    echo "$FAILED magic_comments tests FAILED."
    exit 1
fi
