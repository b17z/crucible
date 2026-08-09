#!/bin/bash
# Tests for src/crucible/interfaces/claude_code/stop/append_signs.sh
#
# Hermetic — every test creates its own tmp project and tears it down.
#
# Runnable via:
#   bash tests/test_append_signs.sh
# Exits 0 on success, non-zero if any test failed.

set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/src/crucible/interfaces/claude_code/stop/append_signs.sh"
FAILED=0

RUNNER="${RUNNER:-/bin/bash}"
echo "Running append_signs tests under: $RUNNER ($($RUNNER --version | head -1))"

# run_hook → captures stdout/stderr and exit code, from inside the cwd
# the caller has already cd'd into.
run_hook() {
    STDOUT_OUT=$($RUNNER "$HOOK" 2>/tmp/append_signs_stderr_$$)
    EXIT_CODE=$?
    STDERR_OUT=$(cat /tmp/append_signs_stderr_$$)
    rm -f /tmp/append_signs_stderr_$$
}

assert_exit_zero() {
    local label="$1"
    if [[ "$EXIT_CODE" != 0 ]]; then
        echo "FAIL [$label]: expected exit 0, got $EXIT_CODE"
        FAILED=$((FAILED + 1))
    fi
}

assert_stderr_empty() {
    local label="$1"
    if [[ -n "$STDERR_OUT" ]]; then
        echo "FAIL [$label]: expected silent stderr, got: $STDERR_OUT"
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

assert_file_contains() {
    local file="$1"
    local needle="$2"
    local label="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL [$label]: $file does not exist"
        FAILED=$((FAILED + 1))
        return
    fi
    if ! grep -qF "$needle" "$file"; then
        echo "FAIL [$label]: $file missing '$needle'"
        FAILED=$((FAILED + 1))
    fi
}

assert_file_not_contains() {
    local file="$1"
    local needle="$2"
    local label="$3"
    if [[ -f "$file" ]] && grep -qF "$needle" "$file"; then
        echo "FAIL [$label]: $file should not contain '$needle'"
        FAILED=$((FAILED + 1))
    fi
}

write_candidate() {
    # write_candidate <dir> <id> <trigger> <instruction> <reason> <source>
    local dir="$1" id="$2" trigger="$3" instruction="$4" reason="$5" source="$6"
    cat > "$dir/${id}.yaml" << EOF
id: $id
trigger: $trigger
instruction: $instruction
reason: $reason
provenance: 2026-08-08 via $source
EOF
}

# --- missing acked dir → silent exit 0 ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
run_hook
assert_exit_zero "missing-acked-exit"
assert_stderr_empty "missing-acked-silent"
if [[ -f GUARDRAILS.md ]]; then
    echo "FAIL [missing-acked-no-file]: GUARDRAILS.md should not be created"
    FAILED=$((FAILED + 1))
fi
cd /; rm -rf "$SCRATCH"

# --- empty acked dir → silent exit 0 ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/inbox/signs/acked
run_hook
assert_exit_zero "empty-acked-exit"
assert_stderr_empty "empty-acked-silent"
if [[ -f GUARDRAILS.md ]]; then
    echo "FAIL [empty-acked-no-file]: GUARDRAILS.md should not be created"
    FAILED=$((FAILED + 1))
fi
cd /; rm -rf "$SCRATCH"

# --- one acked candidate, no GUARDRAILS.md → file created from template ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/inbox/signs/acked
write_candidate .crucible/inbox/signs/acked "abc12345" "bash_deny:pipe-to-shell" \
    "Do not run commands matching pipe-to-shell" "blocked by the bash deny-list" "bash_deny.sh"
run_hook
assert_exit_zero "first-append-exit"
assert_file_contains GUARDRAILS.md "### Sign 1 — " "first-append-sign-header"
assert_file_contains GUARDRAILS.md "**Trigger:**" "first-append-trigger-bullet"
assert_file_contains GUARDRAILS.md "**Instruction:**" "first-append-instruction-bullet"
assert_file_contains GUARDRAILS.md "**Reason:**" "first-append-reason-bullet"
assert_file_contains GUARDRAILS.md "**Provenance:**" "first-append-provenance-bullet"
assert_file_contains GUARDRAILS.md "pipe-to-shell" "first-append-trigger-content"
assert_file_not_contains GUARDRAILS.md "_(none yet" "first-append-placeholder-gone"
if [[ -f .crucible/inbox/signs/acked/abc12345.yaml ]]; then
    echo "FAIL [first-append-acked-deleted]: acked file should be deleted after append"
    FAILED=$((FAILED + 1))
fi
cd /; rm -rf "$SCRATCH"

# --- existing GUARDRAILS.md with Sign 3 → new sign numbered Sign 4 ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/inbox/signs/acked
write_candidate .crucible/inbox/signs/acked "def67890" "npm_install:evil-pkg" \
    "Do not install packages outside the approved-deps allow list" "blocked by install gate" "npm_install_gate.sh"
cat > GUARDRAILS.md << 'EOF'
# GUARDRAILS.md

## Signs

### Sign 3 — Some earlier sign

- **Trigger:** something
- **Instruction:** do not do the thing
- **Reason:** it broke once
- **Provenance:** 2026-01-01, session-abc
EOF
run_hook
assert_exit_zero "renumber-exit"
assert_file_contains GUARDRAILS.md "### Sign 4 — " "renumber-sign-4"
assert_file_contains GUARDRAILS.md "### Sign 3 — Some earlier sign" "renumber-sign-3-preserved"
cd /; rm -rf "$SCRATCH"

# --- malformed acked yaml → other candidates still append, malformed file remains, exit 0 ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/inbox/signs/acked
echo '{ not yaml [' > .crucible/inbox/signs/acked/bad.yaml
write_candidate .crucible/inbox/signs/acked "good1234" "some:trigger" \
    "Do not do the bad thing at all please" "it broke prod once" "some_hook.sh"
run_hook
assert_exit_zero "malformed-exit"
assert_stderr_contains "bad.yaml" "malformed-note"
assert_file_contains GUARDRAILS.md "### Sign 1 — " "malformed-other-still-appends"
if [[ ! -f .crucible/inbox/signs/acked/bad.yaml ]]; then
    echo "FAIL [malformed-file-remains]: malformed acked file should be left in place"
    FAILED=$((FAILED + 1))
fi
if [[ -f .crucible/inbox/signs/acked/good1234.yaml ]]; then
    echo "FAIL [malformed-good-deleted]: well-formed acked file should be deleted"
    FAILED=$((FAILED + 1))
fi
cd /; rm -rf "$SCRATCH"

# --- title falls back to trigger when instruction absent ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/inbox/signs/acked
cat > .crucible/inbox/signs/acked/notitle1.yaml << 'EOF'
id: notitle1
trigger: some_fallback_trigger
reason: it broke once
provenance: 2026-08-08 via some_hook.sh
EOF
run_hook
assert_exit_zero "fallback-title-exit"
assert_file_contains GUARDRAILS.md "### Sign 1 — some_fallback_trigger" "fallback-title-uses-trigger"
cd /; rm -rf "$SCRATCH"

if [[ "$FAILED" -gt 0 ]]; then
    echo "$FAILED test(s) failed"
    exit 1
fi
echo "All append_signs tests passed"
exit 0
