#!/bin/bash
# protect.sh — PreCompact hook for Crucible v2
#
# Runs right before Claude Code compacts the conversation. Compaction can
# drop Crucible's enforcement context (active assertions, the supply-chain
# threat posture) — exactly the things the agent must keep obeying. This
# hook emits that context as additionalContext so it survives the compact.
#
# It does NOT block compaction; it just makes sure the load-bearing
# context is re-stated on the other side.
#
# Output: JSON with hookSpecificOutput.additionalContext (PreCompact
# event), so Claude Code carries it through the summary.

set -uo pipefail

CRUCIBLE_DIR=".crucible"
[[ -d "$CRUCIBLE_DIR" ]] || exit 0

if ! command -v crucible >/dev/null 2>&1; then
    exit 0
fi

# Build the protected-context block. Assertions are the most important
# thing to preserve — they're what the agent is enforcing. We keep this
# compact (Tier-1-style) rather than dumping everything.
assertions_summary=$(crucible assertions list 2>/dev/null | head -40 || true)

if command -v python3 >/dev/null 2>&1; then
    python3 - "$assertions_summary" << 'PY'
import json, sys

assertions = sys.argv[1].strip() if len(sys.argv) > 1 else ""

parts = ["## Crucible enforcement context (preserved across compaction)", ""]
if assertions:
    parts.append("Active assertions still apply to all code in this session:")
    parts.append("")
    parts.append("```")
    parts.append(assertions)
    parts.append("```")
parts.append("")
parts.append(
    "Supply-chain posture remains in effect: review dependency/lockfile "
    "diffs, treat .claude/settings.json / .mcp.json changes as suspect, "
    "and keep the security-engineer perspective active for any "
    "dependency, CI, or credential-path change."
)

out = {
    "hookSpecificOutput": {
        "hookEventName": "PreCompact",
        "additionalContext": "\n".join(parts),
    }
}
print(json.dumps(out))
PY
fi

exit 0
