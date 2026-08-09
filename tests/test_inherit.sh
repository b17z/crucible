#!/bin/bash
# Tests for src/crucible/interfaces/claude_code/subagent_start/inherit.sh
#
# Hermetic — every test creates its own tmp project and tears it down.
#
# Runnable via:
#   bash tests/test_inherit.sh
# Exits 0 on success, non-zero if any test failed.

set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/src/crucible/interfaces/claude_code/subagent_start/inherit.sh"
FAILED=0

RUNNER="${RUNNER:-/bin/bash}"
echo "Running inherit tests under: $RUNNER ($($RUNNER --version | head -1))"

# --- T1: no session file → exit 0, no stdout ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
OUT=$($RUNNER "$HOOK" 2>/dev/null)
CODE=$?
if [[ "$CODE" != 0 ]]; then echo "FAIL [no-file-exit0]: got $CODE"; FAILED=$((FAILED+1)); fi
if [[ -n "$OUT" ]]; then echo "FAIL [no-file-silent]: got '$OUT'"; FAILED=$((FAILED+1)); fi
cd /; rm -rf "$SCRATCH"

# --- T2: whitespace-only file → exit 0, no stdout ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
printf '\n  \n' > .crucible/active-skills.session
OUT=$($RUNNER "$HOOK" 2>/dev/null)
CODE=$?
if [[ "$CODE" != 0 ]]; then echo "FAIL [empty-exit0]: got $CODE"; FAILED=$((FAILED+1)); fi
if [[ -n "$OUT" ]]; then echo "FAIL [empty-silent]: got '$OUT'"; FAILED=$((FAILED+1)); fi
cd /; rm -rf "$SCRATCH"

# --- T3: active skills → valid SubagentStart JSON naming each skill ---
SCRATCH=$(mktemp -d); cd "$SCRATCH"; mkdir -p .crucible
printf 'meta/but-for-real\nsecurity-engineer\n' > .crucible/active-skills.session
OUT=$($RUNNER "$HOOK" 2>/dev/null)
CODE=$?
if [[ "$CODE" != 0 ]]; then echo "FAIL [skills-exit0]: got $CODE"; FAILED=$((FAILED+1)); fi
echo "$OUT" | python3 -c '
import json, sys
d = json.load(sys.stdin)
out = d["hookSpecificOutput"]
assert out["hookEventName"] == "SubagentStart", out
ctx = out["additionalContext"]
assert "meta/but-for-real" in ctx, ctx
assert "security-engineer" in ctx, ctx
' 2>/dev/null
if [[ $? != 0 ]]; then
    echo "FAIL [skills-json]: invalid or incomplete JSON: $OUT"
    FAILED=$((FAILED+1))
fi
cd /; rm -rf "$SCRATCH"

if [[ "$FAILED" -gt 0 ]]; then
    echo "$FAILED test(s) failed"
    exit 1
fi
echo "All inherit tests passed"
exit 0
