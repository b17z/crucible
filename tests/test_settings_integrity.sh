#!/bin/bash
# Tests for src/crucible/interfaces/claude_code/file_changed/settings_integrity.sh
#
# Hermetic — every test creates its own tmp project and tears it down.
#
# Runnable via:
#   bash tests/test_settings_integrity.sh
# Exits 0 on success, non-zero if any test failed.

set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/src/crucible/interfaces/claude_code/file_changed/settings_integrity.sh"
FAILED=0

RUNNER="${RUNNER:-/bin/bash}"
echo "Running settings_integrity tests under: $RUNNER ($($RUNNER --version | head -1))"

_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

_manifest_hash() {
    # _manifest_hash <input-string>
    if command -v sha256sum >/dev/null 2>&1; then
        printf '%s' "$1" | sha256sum | awk '{print $1}'
    else
        printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
    fi
}

# Build a valid baseline set for a project where only .claude/settings.json
# exists. mcp + extensions are recorded MISSING (they're absent).
setup_valid_baselines() {
    mkdir -p .crucible/baselines .claude
    echo "$1" > .claude/settings.json
    _sha256 .claude/settings.json > .crucible/baselines/settings.sha256
    echo "MISSING" > .crucible/baselines/mcp.sha256
    echo "MISSING" > .crucible/baselines/extensions.sha256
    local manifest_input
    manifest_input="settings $(_sha256 .claude/settings.json)
mcp MISSING
extensions MISSING
"
    _manifest_hash "$manifest_input" > .crucible/baselines/manifest.sha256
}

assert_exit() {
    local expected="$1"
    local label="$2"
    $RUNNER "$HOOK" >/dev/null 2>&1
    local actual=$?
    if [[ "$actual" != "$expected" ]]; then
        echo "FAIL [$label]: expected exit $expected, got $actual"
        FAILED=$((FAILED + 1))
    fi
}

# --- Test 1: no baselines dir → exit 0 (opt-out) ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible .claude
echo '{}' > .claude/settings.json
assert_exit 0 "no-baselines-opt-out"
cd /; rm -rf "$SCRATCH"

# --- Test 2: valid baselines, no drift → exit 0 (silent) ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
setup_valid_baselines '{"a":1}'
assert_exit 0 "valid-no-drift-silent"
cd /; rm -rf "$SCRATCH"

# --- Test 3: REGRESSION — partial baselines (one deleted) → exit 2 (block) ---
# An attacker who deletes a baseline must not silence monitoring.
SCRATCH=$(mktemp -d); cd "$SCRATCH"
setup_valid_baselines '{"a":1}'
rm .crucible/baselines/settings.sha256   # delete one baseline
OUT=$($RUNNER "$HOOK" 2>&1); CODE=$?
if [[ "$CODE" != "2" ]]; then
    echo "FAIL [partial-baselines-block]: expected exit 2, got $CODE"
    FAILED=$((FAILED + 1))
fi
if ! echo "$OUT" | grep -qi "BASELINE(S) MISSING"; then
    echo "FAIL [partial-baselines-message]: output didn't flag missing baselines"
    echo "  output: $OUT"
    FAILED=$((FAILED + 1))
fi
cd /; rm -rf "$SCRATCH"

# --- Test 4: watched file modified vs baseline → exit 2 (divergence) ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
setup_valid_baselines '{"original":1}'
echo '{"TAMPERED":1}' > .claude/settings.json
OUT=$($RUNNER "$HOOK" 2>&1); CODE=$?
if [[ "$CODE" != "2" ]]; then
    echo "FAIL [divergence-block]: expected exit 2, got $CODE"
    FAILED=$((FAILED + 1))
fi
if ! echo "$OUT" | grep -qi "INTEGRITY ALERT"; then
    echo "FAIL [divergence-message]: output didn't flag the divergence"
    echo "  output: $OUT"
    FAILED=$((FAILED + 1))
fi
cd /; rm -rf "$SCRATCH"

# --- Test 5: tampered baseline (manifest divergence) → exit 2 ---
# Attacker modifies both the watched file AND its baseline to match, but
# doesn't update the manifest. The manifest check catches it.
SCRATCH=$(mktemp -d); cd "$SCRATCH"
setup_valid_baselines '{"a":1}'
echo '{"INJECTED":1}' > .claude/settings.json
# rewrite the settings baseline to match the injected file
_sha256 .claude/settings.json > .crucible/baselines/settings.sha256
# manifest.sha256 left stale on purpose
OUT=$($RUNNER "$HOOK" 2>&1); CODE=$?
if [[ "$CODE" != "2" ]]; then
    echo "FAIL [manifest-divergence-block]: expected exit 2, got $CODE"
    FAILED=$((FAILED + 1))
fi
if ! echo "$OUT" | grep -qi "MANIFEST DIVERGENCE"; then
    echo "FAIL [manifest-divergence-message]: output didn't flag manifest tampering"
    echo "  output: $OUT"
    FAILED=$((FAILED + 1))
fi
cd /; rm -rf "$SCRATCH"

if [[ $FAILED -eq 0 ]]; then
    echo "All settings_integrity tests passed."
    exit 0
else
    echo "$FAILED settings_integrity tests FAILED."
    exit 1
fi
