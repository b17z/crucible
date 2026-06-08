#!/bin/bash
# reinject.sh — PostCompact hook for Crucible v2
#
# Runs right after Claude Code compacts the conversation. Two jobs:
#
#   1. Re-inject active assertions — if compaction dropped them, the
#      agent needs them restated to keep enforcing.
#   2. Re-verify baseline integrity — a compaction is a natural moment to
#      re-check that .claude/settings.json et al still match their
#      baselines (an attacker might time tampering for when the context
#      is being rewritten).
#
# Output: JSON with hookSpecificOutput.additionalContext (PostCompact).
# Never blocks.

set -uo pipefail

CRUCIBLE_DIR=".crucible"
[[ -d "$CRUCIBLE_DIR" ]] || exit 0

command -v crucible >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

assertions_summary=$(crucible assertions list 2>/dev/null | head -40 || true)

# Re-run the integrity check. Reuse the settings_integrity hook's logic
# by invoking it and capturing whether it flagged anything (exit 2).
integrity_status="ok"
INTEGRITY_HOOK="$(dirname "$0")/../file_changed/settings_integrity.sh"
if [[ -f "$INTEGRITY_HOOK" ]]; then
    if ! bash "$INTEGRITY_HOOK" >/dev/null 2>&1; then
        integrity_status="DIVERGED"
    fi
fi

python3 - "$assertions_summary" "$integrity_status" << 'PY'
import json, sys

assertions = sys.argv[1].strip() if len(sys.argv) > 1 else ""
integrity = sys.argv[2] if len(sys.argv) > 2 else "ok"

parts = ["## Crucible context restored (post-compaction)", ""]
if assertions:
    parts.append("Active assertions (re-injected — these still apply):")
    parts.append("```")
    parts.append(assertions)
    parts.append("```")
    parts.append("")

if integrity == "DIVERGED":
    parts.append(
        "⚠️ Settings integrity check FAILED after compaction. A watched "
        "file (.claude/settings.json, .mcp.json, .vscode/extensions.json) "
        "diverges from its baseline or a baseline is missing. Suspend tool "
        "use and investigate before continuing."
    )
else:
    parts.append("Settings integrity: OK (watched files match baselines).")

out = {
    "hookSpecificOutput": {
        "hookEventName": "PostCompact",
        "additionalContext": "\n".join(parts),
    }
}
print(json.dumps(out))
PY

exit 0
