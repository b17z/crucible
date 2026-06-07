#!/bin/bash
# settings_integrity.sh — FileChanged hook for Crucible v2
#
# Checks whether the live contents of .claude/settings.json, .mcp.json,
# or .vscode/extensions.json still match the SHA-256 baselines captured by
# `crucible baselines init` (stored at .crucible/baselines/*.sha256).
#
# A divergence is a HIGH-severity signal. Per the TeamPCP TTP confirmed by
# CSA on 2026-05-17, malware modifies .claude/settings.json to install
# persistence hooks that survive a node_modules purge. This hook is the
# layered defense against that TTP.
#
# Behavior on divergence:
#   - Print a clear alert to stderr
#   - Exit 2 to block continued tool use until the user acknowledges
#
# Behavior on missing baseline:
#   - Print a one-line warning suggesting `crucible baselines init`
#   - Exit 0 (don't block work on a project that hasn't opted in yet)
#
# Behavior on match:
#   - Silent. Exit 0.
#
# Installation: Claude Code FileChanged hook config in settings.json:
#   {
#     "hooks": {
#       "FileChanged": [{
#         "matcher": ".claude/settings.json|.mcp.json|.vscode/extensions.json",
#         "command": "bash interfaces/claude_code/file_changed/settings_integrity.sh"
#       }]
#     }
#   }
#
# The matcher in Claude Code is the trust boundary — this script doesn't
# decide which files to monitor, the hook config does.

set -euo pipefail

BASELINES_DIR=".crucible/baselines"
MANIFEST_PATH="${BASELINES_DIR}/manifest.sha256"

# Map watched filename → baseline filename. Order must match
# WATCHED_FILES in src/crucible/baselines.py so the manifest input
# stays stable.
declare -a WATCHED_NAMES=("settings" "mcp" "extensions")
declare -a WATCHED_PATHS=(".claude/settings.json" ".mcp.json" ".vscode/extensions.json")

# Compute sha256 in a portable way (macOS shasum vs Linux sha256sum).
sha256() {
    local path="$1"
    if [[ -e "$path" ]]; then
        if command -v sha256sum >/dev/null 2>&1; then
            sha256sum "$path" | awk '{print $1}'
        elif command -v shasum >/dev/null 2>&1; then
            shasum -a 256 "$path" | awk '{print $1}'
        else
            echo "ERROR: no sha256 tool found on PATH" >&2
            exit 1
        fi
    else
        echo "MISSING"
    fi
}

if [[ ! -d "$BASELINES_DIR" ]]; then
    echo "crucible: no baselines configured. Run 'crucible baselines init' to enable integrity monitoring." >&2
    exit 0
fi

# Build the same manifest-input string the Python init code builds, in the
# same order, and check whether any individual baseline diverges.
#
# Note: by this point BASELINES_DIR exists (checked at the top). A MISSING
# individual baseline file here is NOT a "you haven't opted in" state — the
# directory exists, so init was run, so a baseline that's now gone is
# suspicious. An attacker who wants to silence monitoring for one watched
# file would simply delete its baseline. Treat a missing-but-expected
# baseline as a HARD failure (exit 2), not a friendly skip.
manifest_input=""
divergent=()
missing_baselines=()
for i in "${!WATCHED_NAMES[@]}"; do
    name="${WATCHED_NAMES[$i]}"
    watched="${WATCHED_PATHS[$i]}"
    baseline="${BASELINES_DIR}/${name}.sha256"

    if [[ ! -f "$baseline" ]]; then
        missing_baselines+=("$name|$baseline")
        # Still contribute a placeholder to the manifest input so the
        # manifest check below also notices the tampering.
        manifest_input+="${name} BASELINE_MISSING"$'\n'
        continue
    fi

    expected=$(cat "$baseline")
    actual=$(sha256 "$watched")

    if [[ "$expected" != "$actual" ]]; then
        divergent+=("$name|$watched|$expected|$actual")
    fi

    manifest_input+="${name} ${actual}"$'\n'
done

# Partial baselines = block. The baselines directory exists (init was run)
# but one or more expected baseline files are gone.
if [[ ${#missing_baselines[@]} -gt 0 ]]; then
    echo "" >&2
    echo "🛑 crucible: SETTINGS INTEGRITY BASELINE(S) MISSING" >&2
    echo "" >&2
    echo "The .crucible/baselines/ directory exists, but one or more" >&2
    echo "expected baseline files are gone. This is suspicious: an attacker" >&2
    echo "who wants to silence integrity monitoring for a watched file can" >&2
    echo "simply delete its baseline. Crucible blocks rather than skip." >&2
    echo "" >&2
    for entry in "${missing_baselines[@]}"; do
        IFS='|' read -r mname mpath <<< "$entry"
        echo "  ${mname}  (missing: ${mpath})" >&2
    done
    echo "" >&2
    echo "Recommended action:" >&2
    echo "  1. Suspend tool use." >&2
    echo "  2. Determine why the baseline is gone. If you deleted it on" >&2
    echo "     purpose and the watched file is known-good, re-baseline:" >&2
    echo "       crucible baselines init --force" >&2
    echo "  3. If you didn't delete it, treat as a compromise. See" >&2
    echo "     skills/security-engineer/knowledge/supply-chain-2026.md." >&2
    echo "" >&2
    exit 2
fi

# Independently verify the manifest hash. A tampered baseline + tampered
# watched file would pass individual checks but the manifest catches it.
if [[ -f "$MANIFEST_PATH" ]]; then
    expected_manifest=$(cat "$MANIFEST_PATH")
    if command -v sha256sum >/dev/null 2>&1; then
        actual_manifest=$(printf '%s' "$manifest_input" | sha256sum | awk '{print $1}')
    else
        actual_manifest=$(printf '%s' "$manifest_input" | shasum -a 256 | awk '{print $1}')
    fi

    if [[ "$expected_manifest" != "$actual_manifest" && ${#divergent[@]} -eq 0 ]]; then
        # Individual baselines all matched but the manifest doesn't. This
        # is the tampered-baselines attack — the attacker rewrote a
        # baseline but not the manifest.
        echo "" >&2
        echo "🛑 crucible: SETTINGS INTEGRITY MANIFEST DIVERGENCE" >&2
        echo "" >&2
        echo "All individual baseline hashes match the watched files, but the" >&2
        echo "manifest hash does NOT match. This pattern is consistent with" >&2
        echo "an attacker who modified both a watched file AND its baseline" >&2
        echo "but forgot to update the manifest." >&2
        echo "" >&2
        echo "Recommended action:" >&2
        echo "  1. Suspend tool use." >&2
        echo "  2. Inspect ${BASELINES_DIR} for unexpected modifications." >&2
        echo "  3. Inspect the watched files against a known-good source." >&2
        echo "  4. Re-init baselines only after confirming integrity." >&2
        echo "" >&2
        exit 2
    fi
fi

if [[ ${#divergent[@]} -eq 0 ]]; then
    # All clear. Silent success.
    exit 0
fi

# At least one watched file has diverged from its baseline.
echo "" >&2
echo "🛑 crucible: SETTINGS INTEGRITY ALERT" >&2
echo "" >&2
echo "The following file(s) no longer match their .crucible/baselines/ hash." >&2
echo "This is the persistence vector confirmed by CSA on 2026-05-17 for" >&2
echo "TeamPCP-style attacks against Claude Code users." >&2
echo "" >&2
for entry in "${divergent[@]}"; do
    IFS='|' read -r name watched expected actual <<< "$entry"
    echo "  ${name}  (${watched})" >&2
    echo "    expected: ${expected:0:24}…" >&2
    echo "    actual:   ${actual:0:24}…" >&2
done
echo "" >&2
echo "Recommended action:" >&2
echo "  1. Suspend tool use immediately. Do not auto-accept." >&2
echo "  2. Inspect the divergent file(s) against a known-good source." >&2
echo "  3. If the change is legitimate (you edited it yourself), re-baseline:" >&2
echo "       crucible baselines init --force" >&2
echo "  4. If the change is unexpected, treat as a compromise. See" >&2
echo "     skills/security-engineer/knowledge/supply-chain-2026.md." >&2
echo "" >&2

exit 2
