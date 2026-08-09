# Phase 5 — During-Coding Hooks

Reconstructed plan (the v4 handoff doc was never committed; scope from the
project memory: PreToolUse Bash deny-list, Edit/Write assertion pre-check,
remaining FileChanged handlers, ConfigChange, SubagentStart/Stop skill
inheritance).

Everything follows the Phase 1b/4 conventions: bash-3.2-safe scripts under
`src/crucible/interfaces/claude_code/<event>/`, hermetic shell test suites in
`tests/test_*.sh` bridged via `tests/test_hooks_shell.py`, idempotent
registration through `_V2_HOOKS` / `generate_settings_json`.

## 5a. PreToolUse(Bash) deny-list — `pre_tool_use/bash_deny.sh`

Blocks destructive/exfil command patterns before they run. Complements
`npm_install_gate.sh` (approval gate); this is a pattern deny-list.

- Bundled rules: `src/crucible/policies/bash_denylist.yaml` — `rules:` list of
  `{id, pattern (python regex), action (deny|warn), reason}`.
- Project file `.crucible/bash-denylist.yaml` may add `rules:` and list
  bundled ids under `disable:`.
- Matching runs in python3 (same yaml-parsing posture as npm_install_gate).
  **Fail-open** with a stderr warning if python3/PyYAML is missing — a broken
  deny-list must not brick every Bash call (unlike the install gate, which
  fails closed because it only gates installs).
- deny → exit 2 with rule id + reason; warn → stderr note, exit 0.
- Bundled rules (tight, high-signal): pipe-to-shell (curl/wget→sh),
  decode-to-shell (base64 -d→sh), eval-of-remote, rm targeting / ~ $HOME,
  writes to raw block devices, mkfs on /dev, fork bomb, chmod -R 777 /
  (deny); git push --force to main/master (warn).

## 5b. Edit/Write assertion pre-check — PreToolUse python hook

Today assertions run PostToolUse (after content lands). Pre-check denies the
write before it happens.

- `run_pretool_hook()` in `hooks/claudecode.py`; CLI
  `crucible hooks claudecode pretool`; registered under PreToolUse with
  matcher `Edit|Write` (same idempotency check style as the PostToolUse
  registration).
- Write → assert on `tool_input.content`. Edit → assert on `new_string` only:
  asserting the merged file would let a pre-existing violation elsewhere in
  the file block an unrelated edit (including the edit that fixes it).
- Same `claudecode.yaml` config (threshold, exclude, on_finding). PostToolUse
  stays as the backstop for content that arrives by other paths.

## 5c. FileChanged semantic diff — `file_changed/config_diff.sh` + snapshots

`settings_integrity.sh` (hash baselines) says *that* a watched file changed;
this says *what* changed, so the operator can judge the alert.

- `crucible baselines init` additionally stores `<name>.snapshot` (a copy of
  each watched file). The block decision still rests only on the
  manifest-covered hashes; snapshots are advisory display, so a tampered
  snapshot can mislabel the diff but never unblock.
- `config_diff.sh` (FileChanged, same three-file matcher): python3 diffs live
  vs snapshot — added/removed/changed `mcpServers` entries, extension
  `recommendations`, settings `hooks`/`env` keys. Always exit 0.
- No snapshot present (pre-Phase-5 baseline dir) → one-line hint to re-init,
  exit 0.

## 5d. ConfigChange + SubagentStop → integrity recheck

Register the existing `settings_integrity.sh` under `ConfigChange` and
`SubagentStop` (no matcher). Config reloads and subagent completions re-verify
the watched files. Zero new script code; silent when clean.

## 5e. SubagentStart skill inheritance — `subagent_start/inherit.sh`

- `route.sh` persists matched skills to `.crucible/active-skills.session`
  (append, dedup — same session-file convention as `mode.session`).
- `inherit.sh` (SubagentStart): if that file is non-empty, emit
  `hookSpecificOutput.additionalContext` listing the active skills so the
  subagent activates the same review perspectives. Exit 0 always.

## Registration summary (`_V2_HOOKS` + python-hook blocks)

| Event | Matcher | Handler |
|---|---|---|
| PreToolUse | Bash | bash_deny.sh (new) |
| PreToolUse | Edit\|Write | `crucible hooks claudecode pretool` (new) |
| FileChanged | 3 watched files | config_diff.sh (new) |
| ConfigChange | — | settings_integrity.sh (reuse) |
| SubagentStop | — | settings_integrity.sh (reuse) |
| SubagentStart | — | inherit.sh (new) |

## Test plan

- `tests/test_bash_deny.sh`, `tests/test_config_diff.sh`,
  `tests/test_inherit.sh` (+ route.sh persistence cases in
  `test_route_hook.sh`), each wrapped in `test_hooks_shell.py`, run under
  `/bin/bash` (3.2).
- Python: pretool hook unit tests (Write content, Edit application,
  replace_all, threshold, exclusion, deny/warn); settings registration
  idempotency for all new entries; baselines snapshot round-trip.

## Order (one commit per slice)

1. 5a bash_deny (policy + script + tests + registration)
2. 5b pretool pre-check (python + CLI + registration + tests)
3. 5c snapshots + config_diff (+ tests)
4. 5d/5e registrations + inherit.sh + route.sh persistence (+ tests)

## Follow-up found during verification

- **mcp 2.0 migration**: mcp 2.0 removed the `Server.list_tools` decorator
  API server.py uses; fresh installs were pulling 2.0.0 and breaking at
  import. Capped to `<2.0.0` in f653bb0 (1.29.0 passes the full suite).
  Migrate server.py to the 2.x API, then lift the cap. Tracked in
  b17z/crucible#11.
