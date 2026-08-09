#!/bin/bash
# inherit.sh — SubagentStart hook for Crucible v2 (Phase 5)
#
# Skill inheritance: the parent session's trigger routing (route.sh)
# records activated skills in .crucible/active-skills.session; this hook
# hands that list to every spawned subagent as additionalContext, so a
# subtask keeps the same review perspectives instead of starting blind.
#
# Emits SubagentStart hookSpecificOutput JSON on stdout when there are
# active skills; silent otherwise. Always exits 0 — inheritance is a
# nudge, never a gate.

set -uo pipefail

ACTIVE_SKILLS_FILE=".crucible/active-skills.session"

[[ -f "$ACTIVE_SKILLS_FILE" ]] || exit 0

# Whitespace-only file → nothing to inherit.
if ! grep -q '[^[:space:]]' "$ACTIVE_SKILLS_FILE" 2>/dev/null; then
    exit 0
fi

# JSON-encode via python3 so skill names can't break the envelope.
command -v python3 >/dev/null 2>&1 || exit 0

python3 - "$ACTIVE_SKILLS_FILE" << 'PY'
import json
import sys

with open(sys.argv[1]) as f:
    skills = [line.strip() for line in f if line.strip()]

if not skills:
    sys.exit(0)

context_lines = [
    "crucible: the parent session activated these skills — activate the",
    "relevant ones for this subtask too (`crucible skills discover <name>`):",
]
context_lines.extend(f"  - {skill}" for skill in skills)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SubagentStart",
        "additionalContext": "\n".join(context_lines),
    }
}))
PY
exit 0
