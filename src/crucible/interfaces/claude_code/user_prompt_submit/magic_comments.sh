#!/bin/bash
# magic_comments.sh — UserPromptSubmit hook for Crucible v2
#
# Parses three `crucible-*:` magic-comment commands from the user's prompt
# and writes file-based state that downstream hooks/skills consume:
#
#   crucible-mode: exploration
#     → writes mode=exploration to .crucible/mode.session
#     → consumed by Phase 4 spec-validator gate as the bypass signal
#
#   crucible-approve: <name>@<version>
#     → appends an entry to .crucible/approved-deps.session.yaml
#     → consumed by pre_tool_use/npm_install_gate.sh as Pattern B
#
#   crucible-sign: <id>[, <id>...] | crucible-sign: all
#     → moves matching pending candidate(s) from .crucible/inbox/signs/
#       into .crucible/inbox/signs/acked/
#     → consumed by the Phase 7 Stop hook, which appends acked Signs to
#       GUARDRAILS.md
#
# This hook NEVER blocks. Magic comments are user-initiated side effects,
# not gates. Exit 0 always (unless misconfigured at the bash level).
#
# Multiple magic comments in one prompt are all honored — they can mix
# freely (e.g. exploration mode + dep approval in the same message).
#
# These are NOT slash commands. Slash commands in Claude Code are skill
# invocations with a specific shape. This hook intercepts plain-text
# magic comments in the user's prompt text, parses them, and side-effects.

set -euo pipefail

CRUCIBLE_DIR=".crucible"
MODE_FILE="${CRUCIBLE_DIR}/mode.session"
APPROVED_SESSION="${CRUCIBLE_DIR}/approved-deps.session.yaml"
INBOX_DIR="${CRUCIBLE_DIR}/inbox"
SIGNS_DIR="${INBOX_DIR}/signs"
SIGNS_ACKED_DIR="${SIGNS_DIR}/acked"

# Read the prompt text from stdin. Claude Code passes UserPromptSubmit
# as JSON; we extract the user message body.
#
# Proper JSON parsing matters: the magic-comment commands are matched with
# line-anchored regexes (^crucible-mode: ...), so the JSON string escapes
# (\n in particular) MUST be decoded into real newlines first. A naive
# grep/sed of the raw JSON leaves "\n" as a literal two-char token, the
# line anchors never match, and the hook silently does nothing.
#
# Preference order: jq → python3 → fail loudly. python3 is already a hard
# dependency of the package (PyYAML ships with it), so the fallback is
# reliable, not best-effort.
if [[ ! -t 0 ]]; then
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
        sys.stdout.write(v)
        break
' 2>/dev/null || echo "")
    else
        echo "" >&2
        echo "crucible: magic_comments hook needs jq or python3 to parse the" >&2
        echo "prompt JSON, but neither is on PATH. Magic comments" >&2
        echo "(crucible-mode/approve/sign) will not work until one is installed." >&2
        echo "" >&2
        # Don't block the prompt — this hook is non-gating. Exit 0.
        exit 0
    fi
else
    exit 0
fi

if [[ -z "$prompt_text" ]]; then
    exit 0
fi

# Ensure .crucible/ exists (don't auto-create the whole layout; that's
# the user's responsibility via `crucible init`). But mode.session and
# the inbox are session-scoped, so create their parent dirs lazily.
[[ -d "$CRUCIBLE_DIR" ]] || exit 0   # Crucible not initialized here; nothing to do.

# --- crucible-mode ---
# Match: any line starting with `crucible-mode:` followed by a token.
# Last match wins (so a user can flip modes mid-prompt by repeating).
#
# Charset: letters, digits, dot, underscore, hyphen. Wide enough for
# names like 'exploration', 'production-mode-2', 'v2.exploration', but
# excludes everything injection-relevant — no colons, slashes, at-signs,
# quotes, or whitespace can reach the mode.session file.
mode_value=$( { echo "$prompt_text" | grep -oE '^[[:space:]]*crucible-mode:[[:space:]]*[a-zA-Z0-9._-]+' || true; } | tail -1 | sed -E 's/^[[:space:]]*crucible-mode:[[:space:]]*//')
if [[ -n "$mode_value" ]]; then
    printf 'mode=%s\nset_at=%s\n' "$mode_value" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$MODE_FILE"
    echo "crucible: mode set to '${mode_value}' for this session (file: ${MODE_FILE})" >&2
fi

# --- crucible-approve ---
# Match: `crucible-approve: <name>@<version>` where name and version are
# composed only of characters legal in package identifiers across npm,
# PyPI, Cargo, etc. — letters, digits, dot, underscore, hyphen,
# at-sign, slash. This is deliberately stricter than the package
# managers themselves accept, but it eliminates YAML-injection vectors:
# colons, quotes, backslashes, newlines, and arbitrary characters
# cannot reach the YAML file even by accident.
#
# Anything that doesn't match this pattern is silently ignored with a
# warning to stderr. The hook never blocks, never errors.
PKG_CHARSET='[A-Za-z0-9._/@-]'
APPROVE_RE="^[[:space:]]*crucible-approve:[[:space:]]*${PKG_CHARSET}+\$"

# Build the arrays with a portable while-read loop. `mapfile`/`readarray`
# is bash 4+, but the shebang resolves to /bin/bash which on macOS is
# bash 3.2 — so we avoid it. IFS= + read -r preserves each line verbatim.
approve_lines=()
while IFS= read -r line; do
    [[ -n "$line" ]] && approve_lines+=("$line")
done < <(echo "$prompt_text" | grep -E "$APPROVE_RE" || true)

# Surface any malformed approve lines so the user knows their input
# didn't take effect. Only useful if there's a line that *looks* like
# an approve command but failed strict validation.
suspicious_lines=()
while IFS= read -r line; do
    [[ -n "$line" ]] && suspicious_lines+=("$line")
done < <(echo "$prompt_text" | grep -E '^[[:space:]]*crucible-approve:' | grep -vE "$APPROVE_RE" || true)
# Guard the expansion: under `set -u`, bash 3.2 (macOS /bin/bash) errors
# on "${empty_array[@]}". Only iterate when the array is non-empty.
if [[ ${#suspicious_lines[@]} -gt 0 ]]; then
    for bad in "${suspicious_lines[@]}"; do
        echo "crucible: ignoring malformed approve line '${bad}' — only [A-Za-z0-9._/@-] characters allowed in name/version" >&2
    done
fi

if [[ ${#approve_lines[@]} -gt 0 ]]; then
    # Bootstrap the session-scoped file with a header if it doesn't exist.
    if [[ ! -f "$APPROVED_SESSION" ]]; then
        cat > "$APPROVED_SESSION" << 'YAML_HEADER'
# Session-scoped dependency approvals (Pattern B).
# Populated by crucible-approve: magic comments. Deleted at session end.
# Consumed by interfaces/claude_code/pre_tool_use/npm_install_gate.sh.
approved:
YAML_HEADER
    fi

    for line in "${approve_lines[@]}"; do
        pkg=$(echo "$line" | sed -E 's/^[[:space:]]*crucible-approve:[[:space:]]*//')
        # Parse name@version (also handles @scope/name@version)
        if [[ "$pkg" == "@"* ]]; then
            tail="${pkg:1}"
            if [[ "$tail" == *"@"* ]]; then
                name="@${tail%@*}"
                version="${tail##*@}"
            else
                name="$pkg"; version=""
            fi
        elif [[ "$pkg" == *"=="* ]]; then
            name="${pkg%==*}"; version="${pkg##*==}"
        elif [[ "$pkg" == *"@"* ]]; then
            name="${pkg%@*}"; version="${pkg##*@}"
        else
            name="$pkg"; version=""
        fi

        if [[ -z "$version" ]]; then
            echo "crucible: ignoring 'crucible-approve: ${pkg}' — version required (use name@version)" >&2
            continue
        fi

        # Defense in depth: also enforce the charset on the parsed name
        # and version individually. The whole-line regex above should
        # have caught anything bad already, but if the parsing logic
        # ever changes we don't want unstrict values reaching the
        # YAML file.
        if ! [[ "$name" =~ ^${PKG_CHARSET}+$ && "$version" =~ ^${PKG_CHARSET}+$ ]]; then
            echo "crucible: ignoring parsed approve '${name}@${version}' — invalid characters" >&2
            continue
        fi

        # Append a YAML entry. The session file is small and short-lived;
        # we don't dedupe — duplicate entries are harmless to the gate.
        # Quote names that start with `@` (scoped npm packages) — bare
        # @ is a reserved YAML indicator. Other names use double quotes
        # too for consistency; the charset filter already guarantees no
        # internal quotes can appear.
        cat >> "$APPROVED_SESSION" << YAML_ENTRY
  - name: "${name}"
    version: "${version}"
    reason: session approval via crucible-approve magic comment
    approved_at: $(date -u +%Y-%m-%d)
    approved_by: session
YAML_ENTRY
        echo "crucible: approved ${name}@${version} for this session" >&2
    done
fi

# --- crucible-sign ---
# Match: `crucible-sign: <id>[, <id>...]` or `crucible-sign: all`. IDs are
# the 8-char lowercase hex prefixes minted by crucible.signs.write_candidate
# (sha256(trigger)[:8]), so the charset is deliberately narrow — hex digits
# only, plus the literal `all`. Anything else can't reach the filesystem.
#
# Acknowledging a Sign moves its file from the pending inbox dir into
# acked/ (created on demand); the Phase 7 Stop hook consumes acked/ to
# append entries to GUARDRAILS.md. This hook never blocks: an unknown id
# is a stderr note, not an error, and we always exit 0.
sign_line=$( { echo "$prompt_text" | grep -oE 'crucible-sign:[[:space:]]*([a-f0-9]{8}([,[:space:]]+[a-f0-9]{8})*|all)\b' || true; } | tail -1 | sed -E 's/^crucible-sign:[[:space:]]*//')
if [[ -n "$sign_line" ]]; then
    # Normalize to space-separated tokens. Strip commas, collapse whitespace,
    # and trim (echo appends a trailing newline that `tr -s` turns into a
    # trailing space rather than removing — that would break the exact
    # `== "all"` comparison below).
    sign_tokens=$(echo "$sign_line" | tr ',' ' ' | tr -s '[:space:]' ' ')
    sign_tokens="${sign_tokens# }"
    sign_tokens="${sign_tokens% }"

    # Build the id array with a portable while-read loop (bash 3.2 has no
    # mapfile). `all` expands to every pending *.yaml basename; otherwise
    # each whitespace-separated token is validated against the hex-id
    # charset individually — defense in depth even though the line-level
    # regex above should already exclude anything else.
    sign_ids=()
    if [[ "$sign_tokens" == "all" ]]; then
        if [[ -d "$SIGNS_DIR" ]]; then
            for f in "$SIGNS_DIR"/*.yaml; do
                [[ -e "$f" ]] || continue   # guard empty glob under set -u/-e (nullglob unset in bash 3.2)
                base=$(basename "$f" .yaml)
                sign_ids+=("$base")
            done
        fi
    else
        for tok in $sign_tokens; do
            if [[ "$tok" =~ ^[a-f0-9]{8}$ ]]; then
                sign_ids+=("$tok")
            else
                echo "crucible: ignoring malformed sign id '${tok}' — expected 8-char hex or 'all'" >&2
            fi
        done
    fi

    if [[ ${#sign_ids[@]} -gt 0 ]]; then
        mkdir -p "$SIGNS_ACKED_DIR"
        for id in "${sign_ids[@]}"; do
            pending_file="${SIGNS_DIR}/${id}.yaml"
            if [[ -f "$pending_file" ]]; then
                mv "$pending_file" "${SIGNS_ACKED_DIR}/${id}.yaml"
                echo "crucible: sign ${id} acknowledged" >&2
            else
                echo "crucible: sign ${id} not found" >&2
            fi
        done
    fi
fi

exit 0
