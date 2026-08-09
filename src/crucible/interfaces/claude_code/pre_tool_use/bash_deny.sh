#!/bin/bash
# bash_deny.sh — PreToolUse(Bash) hook for Crucible v2 (Phase 5)
#
# Pattern deny-list for destructive or exfil-shaped shell commands. The
# rules live in policies/bash_denylist.yaml (bundled) plus the optional
# project file .crucible/bash-denylist.yaml (extra rules and a disable
# list). See the policy file for the threat model and intentional gaps.
#
# This gate FAILS OPEN: if python3 or PyYAML is missing we warn and allow,
# because a broken deny-list must not brick every Bash call. Contrast with
# npm_install_gate.sh, which fails closed — it only gates installs, so
# failing closed there blocks little; failing closed here blocks everything.
#
# Exit codes:
#   0 — allow (no deny rule matched; warn rules print to stderr)
#   2 — block (a deny rule matched)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLED_POLICY="${SCRIPT_DIR}/../../../policies/bash_denylist.yaml"
PROJECT_POLICY=".crucible/bash-denylist.yaml"

# --- read the command from stdin (jq → python3 → give up) ---
if [[ -n "${1:-}" ]]; then
    command_text="$1"
elif [[ ! -t 0 ]]; then
    stdin_buf=$(cat)
    if command -v jq >/dev/null 2>&1; then
        command_text=$(printf '%s' "$stdin_buf" | jq -r '.tool_input.command // .command // empty' 2>/dev/null || echo "")
    elif command -v python3 >/dev/null 2>&1; then
        command_text=$(printf '%s' "$stdin_buf" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
v = (d.get("tool_input") or {}).get("command") or d.get("command")
if isinstance(v, str):
    sys.stdout.write(v)
' 2>/dev/null || echo "")
    else
        # No JSON parser — cannot match. Fail open.
        exit 0
    fi
else
    exit 0
fi

if [[ -z "$command_text" ]]; then
    exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "crucible: bash_deny inactive — python3 not found (deny-list fails open)." >&2
    exit 0
fi

# Match in python: same yaml-parsing posture as npm_install_gate, but the
# regex engine is python re (the policy documents this), and a missing
# PyYAML degrades to fail-open with a warning rather than blocking.
python3 - "$command_text" "$BUNDLED_POLICY" "$PROJECT_POLICY" << 'PY'
import re
import sys

command, bundled_path, project_path = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    import yaml
except ImportError:
    print(
        "crucible: bash_deny inactive — PyYAML not installed (deny-list fails open).",
        file=sys.stderr,
    )
    sys.exit(0)


def load_rules(path):
    """(rules, disables) from a policy file; empty on missing/invalid."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return [], []
    if not isinstance(data, dict):
        return [], []
    rules = [r for r in (data.get("rules") or []) if isinstance(r, dict)]
    disables = [str(d) for d in (data.get("disable") or [])]
    return rules, disables


bundled_rules, _ = load_rules(bundled_path)
project_rules, disables = load_rules(project_path)

denied = []
warned = []
for rule in bundled_rules + project_rules:
    rule_id = str(rule.get("id", ""))
    pattern = rule.get("pattern")
    if not rule_id or not pattern or rule_id in disables:
        continue
    try:
        if not re.search(pattern, command):
            continue
    except re.error:
        print(f"crucible: bash_deny rule '{rule_id}' has an invalid regex — skipped.", file=sys.stderr)
        continue
    reason = str(rule.get("reason", ""))
    if rule.get("action", "deny") == "warn":
        warned.append((rule_id, reason))
    else:
        denied.append((rule_id, reason))

for rule_id, reason in warned:
    print(f"crucible: [{rule_id}] {reason}", file=sys.stderr)

if not denied:
    sys.exit(0)

print("", file=sys.stderr)
print("🛑 crucible: COMMAND BLOCKED by bash deny-list", file=sys.stderr)
print("", file=sys.stderr)
print(f"Command: {command}", file=sys.stderr)
print("", file=sys.stderr)
for rule_id, reason in denied:
    print(f"  [{rule_id}] {reason}", file=sys.stderr)
print("", file=sys.stderr)
print("If this command is genuinely needed, a human can run it directly,", file=sys.stderr)
print("or disable the rule for this project in .crucible/bash-denylist.yaml:", file=sys.stderr)
print("  disable:", file=sys.stderr)
for rule_id, _ in denied:
    print(f"    - {rule_id}", file=sys.stderr)
print("", file=sys.stderr)
sys.exit(2)
PY
exit $?
