#!/bin/bash
# Tests for src/crucible/interfaces/claude_code/pre_tool_use/npm_install_gate.sh
#
# Hermetic — every test creates its own tmp project and tears it down.
#
# Runnable via:
#   bash tests/test_npm_install_gate.sh
# Exits 0 on success, non-zero if any test failed.

set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/src/crucible/interfaces/claude_code/pre_tool_use/npm_install_gate.sh"
FAILED=0

# Run the hook under the SAME interpreter its shebang resolves to. On
# macOS that's /bin/bash (3.2). Testing under Homebrew bash 5.x hides
# bash-3.2-only bugs. Override with RUNNER=bash for the modern interpreter.
RUNNER="${RUNNER:-/bin/bash}"
echo "Running npm_install_gate tests under: $RUNNER ($($RUNNER --version | head -1))"

# assert_exit <expected> <command-json> <label>
# Feeds the JSON to the hook on stdin and checks the exit code.
assert_exit() {
    local expected="$1"
    local json="$2"
    local label="$3"
    local actual
    printf '%s' "$json" | $RUNNER "$HOOK" >/dev/null 2>&1
    actual=$?
    if [[ "$actual" != "$expected" ]]; then
        echo "FAIL [$label]: expected exit $expected, got $actual"
        FAILED=$((FAILED + 1))
    fi
}

write_durable() {
    # write_durable <name> <version>
    cat > .crucible/approved-deps.yaml <<EOF
approved:
  - name: "$1"
    version: "$2"
    reason: test
EOF
}

# --- Test 1: approved pinned package passes ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
write_durable lodash 4.17.21
assert_exit 0 '{"tool_input":{"command":"npm install lodash@4.17.21"}}' "approved-pinned-passes"
cd /; rm -rf "$SCRATCH"

# --- Test 2: unpinned package blocks ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
write_durable lodash 4.17.21
assert_exit 2 '{"tool_input":{"command":"npm install lodash"}}' "unpinned-blocks"
cd /; rm -rf "$SCRATCH"

# --- Test 3: pinned-but-unapproved blocks ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
write_durable lodash 4.17.21
assert_exit 2 '{"tool_input":{"command":"npm install evil@9.9.9"}}' "unapproved-pin-blocks"
cd /; rm -rf "$SCRATCH"

# --- Test 4: non-install command passes ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
assert_exit 0 '{"tool_input":{"command":"echo hello"}}' "non-install-passes"
cd /; rm -rf "$SCRATCH"

# --- Test 5: bare `npm install` (lockfile reinstall) passes ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
assert_exit 0 '{"tool_input":{"command":"npm install"}}' "lockfile-reinstall-passes"
cd /; rm -rf "$SCRATCH"

# --- Test 6: scoped npm package, approved, passes ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
write_durable "@tanstack/react-router" 1.0.0
assert_exit 0 '{"tool_input":{"command":"npm install @tanstack/react-router@1.0.0"}}' "scoped-approved-passes"
cd /; rm -rf "$SCRATCH"

# --- Test 7: pip == syntax, approved, passes ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
write_durable requests 2.31.0
assert_exit 0 '{"tool_input":{"command":"pip install requests==2.31.0"}}' "pip-eq-approved-passes"
cd /; rm -rf "$SCRATCH"

# --- Test 8: REGRESSION — malformed YAML fails closed ---
# Previously the awk parser would accept name:"x"/version:"y" and falsely
# approve. With python yaml.safe_load, malformed YAML → fail closed.
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
cat > .crucible/approved-deps.yaml <<'EOF'
approved:
  - name:"x"
    version:"y"
EOF
assert_exit 2 '{"tool_input":{"command":"npm install x@y"}}' "malformed-yaml-fails-closed"
cd /; rm -rf "$SCRATCH"

# --- Test 9: session-scoped allow-list is honored ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
cat > .crucible/approved-deps.session.yaml <<'EOF'
approved:
  - name: "leftpad"
    version: "1.0.0"
    reason: session
EOF
assert_exit 0 '{"tool_input":{"command":"npm install leftpad@1.0.0"}}' "session-allowlist-passes"
cd /; rm -rf "$SCRATCH"

# --- Test 10: cargo add, unapproved, blocks ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
assert_exit 2 '{"tool_input":{"command":"cargo add serde@1.0.0"}}' "cargo-unapproved-blocks"
cd /; rm -rf "$SCRATCH"

# --- Test 11: PyYAML-missing preflight surfaces clearly and fails closed ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible faked-bin
write_durable lodash 4.17.21
# Shadow python3 with a stub whose `import yaml` fails. Keep everything
# else (the install-parse uses python3 only for is_approved + preflight).
cat > faked-bin/python3 <<'PYEOF'
#!/bin/sh
if [ "$1" = "-c" ] && [ "$2" = "import yaml" ]; then
    echo "ModuleNotFoundError: No module named 'yaml'" >&2
    exit 1
fi
exec /usr/bin/env python3 "$@"
PYEOF
chmod +x faked-bin/python3
OUT=$(printf '{"tool_input":{"command":"npm install lodash@4.17.21"}}' | PATH="$SCRATCH/faked-bin:$PATH" $RUNNER "$HOOK" 2>&1)
CODE=$?
if [[ "$CODE" != "2" ]]; then
    echo "FAIL [pyyaml-missing-fails-closed]: expected exit 2, got $CODE"
    FAILED=$((FAILED + 1))
fi
if ! echo "$OUT" | grep -qi "PyYAML"; then
    echo "FAIL [pyyaml-missing-clear-message]: output didn't mention PyYAML"
    echo "  output: $OUT"
    FAILED=$((FAILED + 1))
fi
cd /; rm -rf "$SCRATCH"

if [[ $FAILED -eq 0 ]]; then
    echo "All npm_install_gate tests passed."
    exit 0
else
    echo "$FAILED npm_install_gate tests FAILED."
    exit 1
fi
