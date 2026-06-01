#!/bin/bash
# npm_install_gate.sh — PreToolUse(Bash) hook for Crucible v2
#
# Blocks dependency-install commands unless the target package@version
# appears in:
#   Pattern A (durable):       .crucible/approved-deps.yaml
#   Pattern B (session-scoped): .crucible/approved-deps.session.yaml
#
# Both files have the same shape; only lifetime differs. Pattern B is
# populated by the `crucible-approve:` magic-comment hook (see
# user_prompt_submit/magic_comments.sh) and deleted at session end.
#
# Background: postinstall hooks are the universal supply-chain vector
# (see skills/security-engineer/knowledge/supply-chain-2026.md). Any
# install of a new dependency is a potential entry point. This hook
# requires explicit operator approval before any install proceeds.
#
# Input: Claude Code passes the Bash command in stdin as JSON. We extract
# the command field and pattern-match against known install verbs.
#
# Exit codes:
#   0 — allow (not an install, or install is approved)
#   2 — block (install of unapproved package@version)

set -euo pipefail

APPROVED_DURABLE=".crucible/approved-deps.yaml"
APPROVED_SESSION=".crucible/approved-deps.session.yaml"

# Read the bash command from stdin (Claude Code passes a JSON envelope
# with tool_input.command). Fall back to $1 if invoked directly.
if [[ -n "${1:-}" ]]; then
    command_text="$1"
elif [[ ! -t 0 ]]; then
    # Try to parse the JSON envelope. jq if available, otherwise grep.
    stdin_buf=$(cat)
    if command -v jq >/dev/null 2>&1; then
        command_text=$(echo "$stdin_buf" | jq -r '.tool_input.command // .command // empty' 2>/dev/null || echo "")
    else
        # Brittle fallback: grep for "command":"..."
        command_text=$(echo "$stdin_buf" | grep -oE '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)"/\1/')
    fi
else
    # No input available — nothing to gate. Allow.
    exit 0
fi

if [[ -z "$command_text" ]]; then
    exit 0
fi

# Identify the install pattern. Each entry is a regex that must match
# the start of the command (after optional `sudo `) plus the install verb.
# Captured groups vary by tool; we re-parse the matched line below.
install_detected=false
tool=""
package_args=""

# Strip leading sudo and any env-var prefixes like NODE_ENV=production
stripped=$(echo "$command_text" | sed -E 's/^(sudo[[:space:]]+)?([A-Z_]+=[^[:space:]]+[[:space:]]+)*//')

if [[ "$stripped" =~ ^(npm|pnpm|yarn)[[:space:]]+(i|install|add)([[:space:]]+(.+))?$ ]]; then
    tool="${BASH_REMATCH[1]}"
    verb="${BASH_REMATCH[2]}"
    package_args="${BASH_REMATCH[4]:-}"
    install_detected=true
elif [[ "$stripped" =~ ^(pip|pip3)[[:space:]]+install([[:space:]]+(.+))?$ ]]; then
    tool="${BASH_REMATCH[1]}"
    verb="install"
    package_args="${BASH_REMATCH[3]:-}"
    install_detected=true
elif [[ "$stripped" =~ ^cargo[[:space:]]+add([[:space:]]+(.+))?$ ]]; then
    tool="cargo"
    verb="add"
    package_args="${BASH_REMATCH[2]:-}"
    install_detected=true
fi

if [[ "$install_detected" != "true" ]]; then
    # Not an install command. Allow.
    exit 0
fi

# `npm install` with no args = lockfile reinstall. Don't gate; the
# lockfile is the source of truth. But surface a note for the operator.
if [[ -z "$package_args" ]]; then
    echo "crucible: ${tool} ${verb} with no args — lockfile reinstall, not gated." >&2
    echo "  Lockfile diffs should still be reviewed; new transitive deps are a supply-chain vector." >&2
    exit 0
fi

# Parse positional package args (strip flags). Each non-flag arg is a
# potential package. Format we expect:
#   foo@1.2.3       → name=foo version=1.2.3
#   foo             → name=foo version=UNPINNED  (will block)
#   @scope/foo@1.2  → name=@scope/foo version=1.2
#   foo==1.2.3      → pip syntax, name=foo version=1.2.3
declare -a requested=()
for arg in $package_args; do
    # Skip flags (--save, -D, --dev, --no-save, --no-fund, etc.)
    if [[ "$arg" =~ ^- ]]; then
        continue
    fi
    requested+=("$arg")
done

if [[ ${#requested[@]} -eq 0 ]]; then
    # All args were flags. Treat as lockfile reinstall.
    exit 0
fi

# Helper: check whether a `name@version` is approved in either allow-list.
#
# Uses Python's yaml.safe_load — the same parser any downstream consumer
# of these files will use. Avoids the awk/yaml disagreement where a
# permissive text scan would accept malformed YAML that strict parsers
# reject. If the file is missing or invalid YAML, returns 1 (not
# approved) silently — the gate fails closed.
is_approved() {
    local name="$1"
    local version="$2"
    local file="$3"

    [[ -f "$file" ]] || return 1

    python3 - "$name" "$version" "$file" << 'PY' 2>/dev/null
import sys, yaml

name, version, file = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    data = yaml.safe_load(open(file)) or {}
except yaml.YAMLError:
    sys.exit(1)

if not isinstance(data, dict):
    sys.exit(1)

approved = data.get('approved') or []
if not isinstance(approved, list):
    sys.exit(1)

for entry in approved:
    if not isinstance(entry, dict):
        continue
    if str(entry.get('name', '')) == name and str(entry.get('version', '')) == version:
        sys.exit(0)
sys.exit(1)
PY
}

declare -a denied=()
for arg in "${requested[@]}"; do
    # Parse name@version or name==version (pip).
    if [[ "$arg" == *"=="* ]]; then
        name="${arg%==*}"
        version="${arg##*==}"
    elif [[ "$arg" == "@"* ]]; then
        # Scoped npm package: @scope/name[@version]
        # Split on the LAST @ that isn't the leading one.
        tail="${arg:1}"  # strip leading @
        if [[ "$tail" == *"@"* ]]; then
            name="@${tail%@*}"
            version="${tail##*@}"
        else
            name="$arg"
            version=""
        fi
    elif [[ "$arg" == *"@"* ]]; then
        name="${arg%@*}"
        version="${arg##*@}"
    else
        name="$arg"
        version=""
    fi

    if [[ -z "$version" ]]; then
        denied+=("$arg|unpinned (no @version) — Crucible requires pinned versions for supply-chain audit")
        continue
    fi

    if is_approved "$name" "$version" "$APPROVED_DURABLE"; then
        continue
    fi
    if is_approved "$name" "$version" "$APPROVED_SESSION"; then
        continue
    fi

    denied+=("$arg|not in .crucible/approved-deps.yaml or .session.yaml")
done

if [[ ${#denied[@]} -eq 0 ]]; then
    # All requested packages were pre-approved. Allow.
    exit 0
fi

echo "" >&2
echo "🛑 crucible: DEPENDENCY INSTALL BLOCKED" >&2
echo "" >&2
echo "Command: ${command_text}" >&2
echo "" >&2
echo "The following package(s) are not approved for install:" >&2
for entry in "${denied[@]}"; do
    IFS='|' read -r pkg reason <<< "$entry"
    echo "  ${pkg}" >&2
    echo "    reason: ${reason}" >&2
done
echo "" >&2
echo "To approve durably (across sessions), add an entry to:" >&2
echo "  ${APPROVED_DURABLE}" >&2
echo "" >&2
echo "To approve for this session only, include a magic comment in your" >&2
echo "next prompt:" >&2
echo "  crucible-approve: <name>@<version>" >&2
echo "" >&2
echo "Postinstall hooks are the universal supply-chain vector." >&2
echo "See skills/security-engineer/knowledge/supply-chain-2026.md." >&2
echo "" >&2

exit 2
