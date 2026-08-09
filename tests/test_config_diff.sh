#!/bin/bash
# Tests for src/crucible/interfaces/claude_code/file_changed/config_diff.sh
#
# Hermetic — every test creates its own tmp project and tears it down.
#
# Runnable via:
#   bash tests/test_config_diff.sh
# Exits 0 on success, non-zero if any test failed.

set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/src/crucible/interfaces/claude_code/file_changed/config_diff.sh"
FAILED=0

RUNNER="${RUNNER:-/bin/bash}"
echo "Running config_diff tests under: $RUNNER ($($RUNNER --version | head -1))"

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

# --- no baselines dir → silent pass ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
run_hook
assert_exit_zero "no-baselines-exit"
assert_stderr_empty "no-baselines-silent"
cd /; rm -rf "$SCRATCH"

# --- baselines dir without snapshots → hint, pass ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/baselines .claude
echo '{"hooks": {}}' > .claude/settings.json
run_hook
assert_exit_zero "no-snapshot-exit"
assert_stderr_contains "snapshot" "no-snapshot-hint"
cd /; rm -rf "$SCRATCH"

# --- unchanged files → silent pass ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/baselines .claude
echo '{"hooks": {}}' > .claude/settings.json
cp .claude/settings.json .crucible/baselines/settings.snapshot
run_hook
assert_exit_zero "unchanged-exit"
assert_stderr_empty "unchanged-silent"
cd /; rm -rf "$SCRATCH"

# --- mcp server added → named in output ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/baselines
echo '{"mcpServers": {"good": {"command": "npx good"}}}' > .crucible/baselines/mcp.snapshot
echo '{"mcpServers": {"good": {"command": "npx good"}, "evil": {"command": "npx evil-server"}}}' > .mcp.json
run_hook
assert_exit_zero "mcp-added-exit"
assert_stderr_contains "evil" "mcp-added-named"
assert_stderr_contains "added" "mcp-added-verb"
cd /; rm -rf "$SCRATCH"

# --- mcp server command changed → named in output ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/baselines
echo '{"mcpServers": {"good": {"command": "npx good"}}}' > .crucible/baselines/mcp.snapshot
echo '{"mcpServers": {"good": {"command": "npx hijacked"}}}' > .mcp.json
run_hook
assert_exit_zero "mcp-changed-exit"
assert_stderr_contains "good" "mcp-changed-named"
assert_stderr_contains "changed" "mcp-changed-verb"
cd /; rm -rf "$SCRATCH"

# --- extension recommendation added → named in output ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/baselines .vscode
echo '{"recommendations": ["ms-python.python"]}' > .crucible/baselines/extensions.snapshot
echo '{"recommendations": ["ms-python.python", "evil.stealer"]}' > .vscode/extensions.json
run_hook
assert_exit_zero "ext-added-exit"
assert_stderr_contains "evil.stealer" "ext-added-named"
cd /; rm -rf "$SCRATCH"

# --- settings hook event added → named in output ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/baselines .claude
echo '{"hooks": {}}' > .crucible/baselines/settings.snapshot
echo '{"hooks": {"PostToolUse": [{"hooks": [{"command": "curl evil"}]}]}}' > .claude/settings.json
run_hook
assert_exit_zero "settings-hook-added-exit"
assert_stderr_contains "PostToolUse" "settings-hook-added-named"
cd /; rm -rf "$SCRATCH"

# --- malformed live JSON → manual-inspection note, pass ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/baselines
echo '{"mcpServers": {}}' > .crucible/baselines/mcp.snapshot
echo '{ not json [' > .mcp.json
run_hook
assert_exit_zero "malformed-exit"
assert_stderr_contains "inspect" "malformed-note"
cd /; rm -rf "$SCRATCH"

# --- watched file deleted (snapshot exists) → reported, pass ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"
mkdir -p .crucible/baselines
echo '{"mcpServers": {"good": {"command": "npx good"}}}' > .crucible/baselines/mcp.snapshot
run_hook
assert_exit_zero "deleted-exit"
assert_stderr_contains "removed" "deleted-reported"
cd /; rm -rf "$SCRATCH"

if [[ "$FAILED" -gt 0 ]]; then
    echo "$FAILED test(s) failed"
    exit 1
fi
echo "All config_diff tests passed"
exit 0
