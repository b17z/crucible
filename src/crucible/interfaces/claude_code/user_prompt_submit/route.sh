#!/bin/bash
# route.sh — UserPromptSubmit hook for Crucible v2
#
# Two jobs, both driven by the prompt text:
#
#   1. Trigger routing. Shell out to `crucible triggers match` to find
#      which skills activate for this prompt, and surface them as a
#      hint so the agent loads the right review perspective.
#
#   2. Spec-validator gate. If the prompt is a feature request AND no
#      spec exists AND exploration mode is not on, emit a checkpoint
#      reminder asking for a spec. By default this is ADVISORY (exit 0,
#      message to stderr) — a hard wall on every feature request is how
#      gates get disabled. Projects that want hard blocking create
#      .crucible/spec-gate.strict, which makes the gate exit 2.
#
# This hook is separate from magic_comments.sh (which parses
# crucible-mode/approve/sign). route.sh consumes the mode flag that
# magic_comments.sh writes; run magic_comments.sh BEFORE this one.
#
# Exit codes:
#   0 — allow (always, unless strict mode + unmet spec gate)
#   2 — block (strict mode only: feature request, no spec, no bypass)

set -uo pipefail

CRUCIBLE_DIR=".crucible"
MODE_FILE="${CRUCIBLE_DIR}/mode.session"
BYPASS_LOG="${CRUCIBLE_DIR}/inbox/spec-bypasses"
STRICT_FLAG="${CRUCIBLE_DIR}/spec-gate.strict"
ACTIVE_SKILLS_FILE="${CRUCIBLE_DIR}/active-skills.session"

# Nothing to do if Crucible isn't initialized here.
[[ -d "$CRUCIBLE_DIR" ]] || exit 0

# --- read the prompt from stdin (jq → python3 → give up) ---
if [[ -t 0 ]]; then
    exit 0
fi
stdin_buf=$(cat)
if command -v jq >/dev/null 2>&1; then
    prompt_text=$(printf '%s' "$stdin_buf" | jq -r '.user_prompt // .prompt // .message // empty' 2>/dev/null || echo "")
elif command -v python3 >/dev/null 2>&1; then
    prompt_text=$(printf '%s' "$stdin_buf" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for k in ("user_prompt", "prompt", "message"):
    v = d.get(k)
    if isinstance(v, str) and v:
        sys.stdout.write(v); break
' 2>/dev/null || echo "")
else
    # No JSON parser — can't route. Stay silent, don't block.
    exit 0
fi

[[ -n "$prompt_text" ]] || exit 0

# crucible CLI must be available for routing.
if ! command -v crucible >/dev/null 2>&1; then
    exit 0
fi

# --- job 1: trigger routing ---
# Get the skills that activate for this prompt (names only).
matched=$(crucible triggers match --prompt "$prompt_text" --names-only 2>/dev/null || true)

if [[ -n "$matched" ]]; then
    echo "crucible: skills activated for this prompt:" >&2
    while IFS= read -r skill; do
        [[ -n "$skill" ]] && echo "  - ${skill}" >&2
    done <<< "$matched"

    # Persist for subagent inheritance (dedup) — the SubagentStart hook
    # (subagent_start/inherit.sh) reads this session file so spawned
    # agents load the same review perspectives.
    while IFS= read -r skill; do
        [[ -n "$skill" ]] || continue
        if [[ ! -f "$ACTIVE_SKILLS_FILE" ]] || ! grep -qxF "$skill" "$ACTIVE_SKILLS_FILE"; then
            printf '%s\n' "$skill" >> "$ACTIVE_SKILLS_FILE"
        fi
    done <<< "$matched"
fi

# --- job 2: spec-validator gate ---
# Only relevant if spec-validator was among the activated skills.
if ! echo "$matched" | grep -q '^meta/spec-validator$'; then
    exit 0
fi

# Exploration mode bypasses the gate. magic_comments.sh writes
# `mode=exploration` to MODE_FILE.
if [[ -f "$MODE_FILE" ]] && grep -q '^mode=exploration' "$MODE_FILE"; then
    # Record the bypass for the session-end accountability summary.
    mkdir -p "$(dirname "$BYPASS_LOG")"
    printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$BYPASS_LOG"
    echo "crucible: spec-validator bypassed (exploration mode)." >&2
    exit 0
fi

# Does a spec already exist? Cheap heuristics: any spec-shaped file in
# the repo, or a .crucible prewrite doc. This is intentionally loose —
# the gate is a reminder, not a forensic audit.
spec_exists=false
if compgen -G "*.md" >/dev/null 2>&1; then
    if grep -rilE "^#+ *(prd|product requirements|tdd|technical design|rfc|adr|spec|specification)" \
        --include="*.md" . 2>/dev/null | head -1 | grep -q .; then
        spec_exists=true
    fi
fi
if [[ -d "${CRUCIBLE_DIR}/prewrite" ]] || compgen -G "${CRUCIBLE_DIR}/skills/pre-write/*/SKILL.md" >/dev/null 2>&1; then
    # A prewrite doc/template presence is a weak signal; only count an
    # actual .crucible prewrite *document*, not the bundled templates.
    if compgen -G "${CRUCIBLE_DIR}/prewrite/*.md" >/dev/null 2>&1; then
        spec_exists=true
    fi
fi

if [[ "$spec_exists" == "true" ]]; then
    echo "crucible: feature request — a spec-shaped doc exists; proceeding." >&2
    exit 0
fi

# No spec. Emit the checkpoint.
echo "" >&2
echo "📋 crucible: this looks like a feature request, and no spec/PRD/design" >&2
echo "doc was found. Spec-driven workflow keeps scope bounded and reviewable." >&2
echo "" >&2
echo "Options:" >&2
echo "  • Write one first:  crucible prewrite init prd <name>" >&2
echo "  • Sketch without a spec this session: add 'crucible-mode: exploration'" >&2
echo "    to your next message." >&2
echo "" >&2

# Default is advisory (exit 0). Strict projects opt into hard blocking.
if [[ -f "$STRICT_FLAG" ]]; then
    echo "crucible: spec-gate is in STRICT mode — blocking until a spec exists" >&2
    echo "or exploration mode is set." >&2
    exit 2
fi

exit 0
