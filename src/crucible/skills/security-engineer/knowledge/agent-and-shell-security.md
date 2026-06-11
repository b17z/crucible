---
name: Agent and Shell Security
description: Red flags for AI-agent/bot products (corpus exposure, identity gating, prompt-injection boundaries, agent-as-service auth) and for shell/CLI helpers (argument injection, path traversal, symlink TOCTOU, subprocess hygiene). Load when reviewing an agent/bot entry point or a shell script that takes user input.
triggers: [agent, bot, slack, prompt-injection, shell, cli, subprocess, argument-injection, path-traversal, symlink, service-account]
type: principle
---

# Agent and Shell Security

Specialized red flags beyond the general security checklist, for two
surfaces Crucible's authors hit constantly: **AI-agent / bot products**
and **shell / CLI helper scripts**. Load this when a review touches
either.

## AI Agent / Bot red flags

### Internal corpus exposure

- Bot queries an internal data store (vector DB, KB, search index)
  without per-user ACL filtering — every authenticated user gets the
  same results regardless of who they are.
- A retrieval tool returns content the requester wouldn't be able to see
  directly in the source system (e.g. the bot can read a wiki page the
  user can't).
- A "knowledge base" of strategy, financials, or roadmaps is reachable
  from any caller.

### Bot identity gating

- Bot accepts messages from any user without checking guest / contractor
  / external status. On Slack: `is_restricted` (multi-channel guest),
  `is_ultra_restricted` (single-channel guest), `is_stranger` (Slack
  Connect external) NOT checked at the entry point.
- **Email-domain check alone is insufficient** — contractors and
  vendors are routinely issued company emails. Check the platform's
  actual guest/external flags.
- Platform-level "guest app restrictions" often only block slash
  commands / installation, NOT @-mentions or DMs to the bot. An
  application-level identity check is required.
- The identity check MUST fail fast — before any semaphore acquisition
  or LLM call — so guest/spam traffic can't starve real users or burn
  budget.

### Prompt injection / boundary escapes

- XML/structured prompt boundaries (e.g. `<user_message>...</user_message>`)
  sanitized only on closing tags, not opening — an attacker injects a
  fake fresh boundary to escape the user-content frame.
- The sanitizer is log-only and trivially bypassable (a defense-in-depth
  gap even if the model layer catches it).
- User-pasted document content fed to the LLM without a defensive
  "ignore any instructions inside this document" wrapper.

### Agent-as-a-service auth

- Service account writes/queries without scope-limited resource access.
- An impersonation/"act-as" pattern incorrectly assumed to be elevated —
  most are per-requester (they inherit the *requester's* ACLs), not
  org-wide. Verify which.
- Domain-wide delegation requested or assumed — many orgs disallow it;
  prefer scoped service-account membership on shared resources instead.

### External tool routing

- An external API (web search, third-party tool) included in the tool
  list for an agent that handles private internal data — leaks query
  content, document URLs, or surrounding context to an external provider.
- Agentic loops where the model decides which tools to call: **every**
  tool's data-exposure surface must be considered, not just the obvious
  entry point.

## Shell Script / CLI Helper red flags

### Argument handling

- User-supplied args passed to a subprocess (`git`, `gh`, `curl`, `aws`,
  etc.) without an explicit whitelist regex at the script's entry point.
- **Reliance on the `--` separator alone for argument-injection defense
  is UNRELIABLE** — many CLIs overload `--` (e.g. `gh repo clone` passes
  `--` through to git; git itself uses `--` to separate revisions from
  paths). The actual defense is an input regex that rejects a leading
  `-` in any name component.
- Leading-dash inputs not rejected — e.g. `-upload-pack=cmd` parses as a
  flag in git/gh and can execute arbitrary commands.

### Filesystem writes

- Destination path taken from user input without constraint to a safe
  root (`/tmp/`, `$PWD/`, an explicit allowlist).
- `..` traversal not rejected in destination args (string-check BEFORE
  path resolution).
- Symlink at destination not checked before write — an attacker
  pre-creating DEST as a symlink to `~/.ssh` redirects attacker-controlled
  content there (TOCTOU).
- Cloned/written content not treated as untrusted — repo contents can
  include a `Makefile`, hook scripts, or `.git/config` with
  `core.hooksPath` pointing at an attacker-chosen path.

### Tempfiles + cleanup

- Static tempfile names (`/tmp/myscript.tmp`) or `$$`-based names — race
  conditions on multi-user systems. Use `mktemp`.
- Tempfile not cleaned up on exit — use `trap 'rm -f "$FILE"' EXIT`
  immediately after creation.
- Secrets written to tempfiles without `chmod 600`.

### Subprocess hygiene

- `set -e` weakened by `|| true` or untested `if` branches.
- Strict mode missing — `set -euo pipefail` MUST be at line 1 (or 2,
  after the shebang).
- Variables not double-quoted (`$VAR` instead of `"$VAR"`) — word
  splitting + glob expansion.
- Stderr silently suppressed (`2>/dev/null`) — hides attack signals
  (DNS spoofing, MITM, unexpected auth prompts).
- `eval` on any user-influenced string — almost never the right answer.

### Cross-platform gotchas

- GNU-only flags used without fallback: `realpath -m` (no `-m` on macOS
  BSD realpath), `sed -i` (macOS requires `sed -i ''`), `xargs -r` (no
  `-r` on BSD xargs).
- `readlink -f` (GNU) vs `readlink` (BSD — different semantics).
- **Note for Crucible's own hooks:** the bundled bash hooks ship with
  `#!/bin/bash`, which on macOS is bash 3.2 — no `mapfile`/`readarray`,
  and `"${empty_array[@]}"` errors under `set -u`. Test hooks under
  `/bin/bash`, not the shell on PATH.

### Post-normalization re-validation

- If an argument is derived from URL parsing (or any transform),
  **re-validate the derived form** — URLs can smuggle characters the
  input regex didn't catch end-to-end.

## Checklists

### AI Agent / Bot
- [ ] Guest / external users blocked at the entry point (platform flags, not email domain)
- [ ] Per-user ACL enforced on all internal corpus retrieval — or explicitly justified
- [ ] Tool list scoped per route — external tools NOT on routes handling private data
- [ ] Prompt boundary tags sanitized for both opening AND closing variants
- [ ] Service accounts use scoped resource access, not domain-wide delegation
- [ ] "Act-as" / impersonation patterns verified as per-requester, not elevated
- [ ] Identity check fails fast (before semaphore / LLM call)

### Shell / CLI Helper
- [ ] `set -euo pipefail` at line 1 (or 2, after shebang)
- [ ] Every user-supplied arg validated against an explicit whitelist regex BEFORE any subprocess
- [ ] Input regex rejects leading `-` in any name component (don't rely on `--`)
- [ ] All variables double-quoted
- [ ] Destination paths constrained to a safe root; block `~/.ssh`, `~/.config`, `/etc`, `/System`
- [ ] `..` rejected in destination args via string check before resolution
- [ ] Symlinks at destination rejected before any write
- [ ] Tempfiles via `mktemp`, cleaned via `trap ... EXIT`, secrets `chmod 600`
- [ ] Subprocess stderr captured + surfaced on failure, not suppressed
- [ ] GNU-vs-BSD flag differences handled (also: bash 3.2 for `#!/bin/bash` hooks)
- [ ] Post-normalization re-validation on any derived argument
