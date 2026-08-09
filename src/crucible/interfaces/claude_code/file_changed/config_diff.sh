#!/bin/bash
# config_diff.sh — FileChanged hook for Crucible v2 (Phase 5)
#
# The semantic layer on top of settings_integrity.sh: the hash check says
# THAT a watched file changed; this says WHAT changed, so the operator can
# judge the alert without opening three JSON files. Reads the content
# snapshots that `crucible baselines init` stores alongside the hashes.
#
# ADVISORY ONLY — always exits 0. The block decision belongs to
# settings_integrity.sh, whose hashes are manifest-covered. Snapshots are
# not: a tampered snapshot can mislabel this diff but never unblock.
#
# Installation: registered by `crucible hooks claudecode init` under
# FileChanged with the same three-file matcher as settings_integrity.sh.

set -uo pipefail

BASELINES_DIR=".crucible/baselines"

# Not opted in → silent.
[[ -d "$BASELINES_DIR" ]] || exit 0

# Advisory hook: no python3 means no diff, and that's okay.
command -v python3 >/dev/null 2>&1 || exit 0

python3 - "$BASELINES_DIR" << 'PY'
import json
import sys
from pathlib import Path

baselines_dir = Path(sys.argv[1])

# (snapshot name, watched path, kind) — order and names must match
# WATCHED_FILES in src/crucible/baselines.py.
WATCHED = (
    ("settings", Path(".claude/settings.json"), "settings"),
    ("mcp", Path(".mcp.json"), "mcp"),
    ("extensions", Path(".vscode/extensions.json"), "extensions"),
)

lines = []       # diff detail lines
no_snapshot = [] # watched files present on disk but with nothing to diff against


def parse(text, label):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        lines.append(f"  {label}: cannot parse as JSON — inspect manually")
        return None


def diff_mcp(old, new):
    old_servers = old.get("mcpServers") or {}
    new_servers = new.get("mcpServers") or {}
    for name in sorted(set(new_servers) - set(old_servers)):
        cmd = (new_servers[name] or {}).get("command", "?")
        lines.append(f"  + added server '{name}' (command: {cmd})")
    for name in sorted(set(old_servers) - set(new_servers)):
        lines.append(f"  - removed server '{name}'")
    for name in sorted(set(old_servers) & set(new_servers)):
        if old_servers[name] != new_servers[name]:
            lines.append(f"  ~ changed server '{name}'")


def diff_extensions(old, new):
    old_recs = set(old.get("recommendations") or [])
    new_recs = set(new.get("recommendations") or [])
    for ext in sorted(new_recs - old_recs):
        lines.append(f"  + added recommendation '{ext}'")
    for ext in sorted(old_recs - new_recs):
        lines.append(f"  - removed recommendation '{ext}'")


def diff_settings(old, new):
    old_hooks = old.get("hooks") or {}
    new_hooks = new.get("hooks") or {}
    for event in sorted(set(new_hooks) - set(old_hooks)):
        lines.append(f"  + added hook event '{event}' ({len(new_hooks[event] or [])} entrie(s))")
    for event in sorted(set(old_hooks) - set(new_hooks)):
        lines.append(f"  - removed hook event '{event}'")
    for event in sorted(set(old_hooks) & set(new_hooks)):
        if old_hooks[event] != new_hooks[event]:
            lines.append(f"  ~ changed hook event '{event}'")
    old_env = old.get("env") or {}
    new_env = new.get("env") or {}
    for key in sorted(set(new_env) - set(old_env)):
        lines.append(f"  + added env key '{key}'")
    for key in sorted(set(old_env) - set(new_env)):
        lines.append(f"  - removed env key '{key}'")


DIFFERS = {"settings": diff_settings, "mcp": diff_mcp, "extensions": diff_extensions}

for name, watched, kind in WATCHED:
    snapshot = baselines_dir / f"{name}.snapshot"
    if not snapshot.exists():
        if watched.exists():
            no_snapshot.append(str(watched))
        continue
    if not watched.exists():
        lines.append(f"  {watched}: removed since baseline (snapshot exists)")
        continue

    snap_bytes = snapshot.read_bytes()
    live_bytes = watched.read_bytes()
    if snap_bytes == live_bytes:
        continue

    lines.append(f"  {watched}:")
    old = parse(snap_bytes.decode("utf-8", "replace"), f"{watched} (snapshot)")
    new = parse(live_bytes.decode("utf-8", "replace"), str(watched))
    if old is not None and new is not None:
        before = len(lines)
        DIFFERS[kind](old, new)
        if len(lines) == before:
            lines.append("    (byte-level change only — formatting/whitespace)")

if lines:
    print("crucible: config change details (live vs baseline snapshot):", file=sys.stderr)
    for line in lines:
        print(line, file=sys.stderr)

if no_snapshot:
    print(
        "crucible: no baseline snapshot for "
        + ", ".join(no_snapshot)
        + " — re-run 'crucible baselines init --force' (after verifying the "
        "files) to enable semantic change details.",
        file=sys.stderr,
    )

sys.exit(0)
PY
exit 0
