# Phase 7 Spec — Policy Layer: Validator, GUARDRAILS Auto-Append, REVIEW.md

Version: 1.0 (2026-08-09). Design spec (brainstormed 2026-08-09, approved).
Implementation plan follows separately. Phase 7 completes the policy layer: the three bundled policies
stop being docs-plus-hooks and gain a schema and validator; the GUARDRAILS
Sign machinery documented in `templates/GUARDRAILS.md` gets implemented; and
REVIEW.md gives projects review conventions plus advisory review triggering.

## Decisions (from brainstorm)

1. REVIEW.md = review-conventions template + **trigger ability** (the lost
   handoff's intent, reconstructed with the user): frontmatter trigger
   conditions, markdown conventions body.
2. Trigger mode: **advisory nudge only** — stderr context via a Stop hook,
   never blocking, consistent with the spec-gate's advisory default.
3. Architecture: three thin, separate features (approach A) — no unified
   policy engine; YAGNI until more policies exist.
4. Opt-in by file presence for REVIEW.md; no new config keys anywhere in
   this phase. Sign machinery is always-on but inert without candidates.

## 1. Policy schema/validator — `src/crucible/policy/`

### `schema.py`

- Frozen dataclass `Policy`: `name: str`, `description: str`,
  `version: str`, `severity: str` (one of `critical|high|medium|low`),
  `hooks: tuple[PolicyHook, ...]` (`PolicyHook`: `event`, `matcher | None`,
  `handler`, `blocking: bool`, `note | None`),
  `activated_by_skills: tuple[str, ...]`,
  `source_path: str`. Free-form documented sections (`approval`,
  `intentional_gaps`, `recovery`, `watched_files`, `rules`, …) are retained
  raw in `extra: dict` — the schema validates the load-bearing core and
  tolerates the documentation sections.
- `parse_policy(path) -> Result[Policy, str]` (errors as values; malformed
  YAML, missing required field, unknown severity → `err`).

### `validator.py`

- `load_policies() -> tuple[list[Policy], list[str]]` — cascade:
  `.crucible/policies/*.yaml` (project) then bundled
  `src/crucible/policies/*.yaml`; first-found-wins by `name`. Parse errors
  become error strings, never exceptions.
- `validate_policies(policies) -> list[PolicyIssue]` with
  `PolicyIssue(policy: str, field: str, message: str, level: str)`
  (`error|warning`):
  - every `hooks[].handler` resolves to an existing file (relative to the
    package for bundled handlers like
    `interfaces/claude_code/pre_tool_use/bash_deny.sh`, or the project root
    for project handlers) — missing handler = `error`;
  - `activated_by.skills` entries resolve via the skills loader — unknown
    skill = `warning`;
  - settings_integrity cross-ref: its `watched_files[].path` set must equal
    `crucible.baselines.WATCHED_FILES` paths — drift = `error` (the yaml
    itself demands "keep them in sync").

### Surfaces

- CLI `crucible policies list` — name, severity, description one-liner,
  hook count, source (bundled/project).
- CLI `crucible policies validate` — prints issues; exit 1 if any
  `error`-level issue, else 0.
- SessionStart: `_session_policy_note` in `hooks/claudecode.py` upgrades
  from listing names to running the validator; each issue appends a
  `⚠ policy <name>: <message>` line. Never raises; wrapped like the other
  session-note helpers.

## 2. GUARDRAILS auto-append — `src/crucible/signs.py` + hooks

Implements exactly the machinery `templates/GUARDRAILS.md` documents.

### Candidate generation (deny events → inbox)

- `signs.py`: `write_candidate(trigger, instruction, reason, source,
  base_path=".") -> str | None` — writes
  `.crucible/inbox/signs/<id>.yaml`, id = `sha256(trigger)[:8]`; existing
  id → skip (dedup, return None). Fields: `id`, `trigger`, `instruction`,
  `reason`, `provenance` (ISO date + source hook name). Never raises —
  any OSError is swallowed (candidate generation must not break a deny).
- Sources and their draft instruction text:
  - `bash_deny.sh` on block (python3 heredoc calls `signs.write_candidate`
    via `python3 -c` or inline): trigger = the matched rule id + command
    shape; instruction = "Do not run commands matching `<rule>`: <reason>".
  - `run_pretool_hook` on deny: trigger = assertion id + file path;
    instruction = "Do not introduce `<assertion_id>` violations
    (<message>)".
  - `run_precommit` on gate failure: trigger = the failing rule ids;
    instruction = "Resolve `<ids>` findings before committing".
- Candidates are drafts; the human edits GUARDRAILS.md after append if the
  phrasing needs work.

### Acknowledgement (`crucible-sign:`)

- `magic_comments.sh` gains the reserved verb:
  `crucible-sign: <id>[, <id>…]` or `crucible-sign: all` — moves the named
  candidate files to `.crucible/inbox/signs/acked/`. Unknown id → stderr
  note, continue. (Bash 3.2-safe, mirrors the existing crucible-approve
  parsing.)

### Append (Stop event)

- New bundled hook `interfaces/claude_code/stop/append_signs.sh`,
  registered in `_V2_HOOKS` as `("Stop", None, ("stop",
  "append_signs.sh"))`:
  - no `acked/` files → exit 0 silent;
  - GUARDRAILS.md absent → create from `templates/GUARDRAILS.md` first;
  - for each acked candidate: render the template's Sign format
    (`### Sign N — <title>` with Trigger/Instruction/Reason/Provenance
    bullets), N continuing from the highest existing `### Sign N` header;
    append under `## Signs`; delete the acked file; replace the
    "_(none yet …)_" placeholder line on first append;
  - malformed candidate YAML → stderr note, file left in place, others
    proceed; hook always exits 0 (never blocks Stop).
- PostToolUse never mutates GUARDRAILS.md (the template's anti-spam rule).
- CLI `crucible signs list` — pending candidates (id, trigger, source) and
  acked-but-unappended ones.

## 3. REVIEW.md — conventions + advisory review triggering

### Template (`src/crucible/templates/REVIEW.md`)

```markdown
---
triggers:
  - paths: ["src/**/*.py"]
    min_changed_lines: 50
    note: "Substantial source changes — run `crucible review` before committing"
  - paths: ["**/auth*", "**/crypto*"]
    note: "Security-sensitive paths — review with the security-engineer skill"
---
# Review Conventions

## Severity bar
<!-- What blocks a merge here vs what is advisory -->

## Focus areas
<!-- What reviewers (human or agent) should weight for this project -->

## Checklist
<!-- The project's review checklist -->
```

- `crucible init` offers REVIEW.md creation alongside AGENTS.md (same
  don't-overwrite semantics).

### Nudge (`interfaces/claude_code/stop/review_nudge.sh`)

- Registered `("Stop", None, ("stop", "review_nudge.sh"))`.
- No REVIEW.md in the project → exit 0 silent (file presence is the
  opt-in).
- Parse frontmatter with python3 + PyYAML (fail-open: no python3, no
  PyYAML, malformed frontmatter → exit 0 silent).
- Changed files: union of `git diff --name-only HEAD` and staged
  (`git diff --cached --name-only`); per-file changed lines from
  `--numstat` when a trigger sets `min_changed_lines`.
- A trigger matches when any changed file matches any of its `paths` globs
  AND the total changed lines across matching files meets
  `min_changed_lines` (absent = 0). Emit ONE stderr nudge per matched
  trigger: `crucible: <note> (REVIEW.md trigger matched)`. Always exit 0.

### SessionStart injection

- `run_session_hook` injects REVIEW.md's markdown body (frontmatter
  stripped) as a "Review Conventions" section alongside the other system
  context, so review skills see the project's severity conventions.

## Error handling (phase-wide)

- Errors as values in all python (`Result`/error-string lists).
- Every hook in this phase is advisory: `append_signs.sh`,
  `review_nudge.sh` always exit 0; candidate generation swallows its own
  failures; the policy validator never raises into SessionStart.
- Bash 3.2-safe scripts (no mapfile, guarded array expansion), python3
  heredocs for YAML/JSON work, jq→python3 fallback where stdin JSON is
  parsed — the house hook conventions.

## Testing

- **Policy**: parse table (valid, missing field, bad severity, malformed
  YAML); validator against seeded broken policies in a tmp cascade
  (nonexistent handler → error, unknown skill → warning, watched_files
  drift → error); all three bundled policies validate clean; CLI exit
  codes; SessionStart ⚠ injection.
- **Signs**: unit tests per python source (write, dedup, fields,
  OSError-swallow); `test_magic_comments.sh` extended for the sign verb
  (single, list, all, unknown id); new `test_append_signs.sh` (numbering
  continuation, template creation, placeholder replacement, malformed
  skip, empty inbox silent, always-exit-0); end-to-end test: bash_deny
  block → candidate exists → sign ack → Stop → GUARDRAILS.md contains
  Sign 1.
- **REVIEW.md**: new `test_review_nudge.sh` (no file silent; glob match
  nudges; min_changed_lines boundary both sides; malformed frontmatter
  silent; staged-only changes counted); SessionStart injection test
  (frontmatter stripped).
- All shell suites under `RUNNER=/bin/bash`, bridged in
  `test_hooks_shell.py`. Wheel must ship `policy/`, `templates/REVIEW.md`,
  and both `stop/*.sh` hooks (package-data check). Full suite green;
  fresh-clone check at phase close.

## Acceptance criteria (definition of done)

Enforced by tests (regression on any of these fails the suite):

1. **Validator**: all three bundled policies validate clean; each seeded
   defect class is caught at exactly its specified level — missing handler
   file → `error`, unknown skill → `warning`, settings_integrity
   watched_files drift → `error`, malformed YAML → parse `err`;
   `crucible policies validate` exits 1 on errors and 0 clean.
2. **Signs**: the full path proves out end-to-end in one test — bash_deny
   block writes a candidate, `crucible-sign` acks it, the Stop hook appends
   `### Sign 1` to GUARDRAILS.md in the template's format and clears the
   inbox; a repeat of the same deny before ack produces no second
   candidate (dedup); numbering continues correctly past existing Signs.
3. **REVIEW.md**: a matching trigger emits exactly one nudge per trigger
   per Stop; non-matching, absent-file, and malformed-frontmatter cases
   are silent; `min_changed_lines` is boundary-tested on both sides;
   SessionStart injects the conventions body without frontmatter.
4. **Phase close**: full suite green at ≥ the Phase 6 baseline (824 +
   this phase's tests, with only the 7 documented env-broken integration
   failures); wheel ships `policy/`, `templates/REVIEW.md`, and both
   `stop/*.sh` hooks; fresh clone installs and passes.

Real-world nudge usefulness (noise rate, adoption) is explicitly a Phase 8
dogfooding measurement, not a Phase 7 gate — the structural cap here is
one nudge per matched trigger per Stop event.

## Non-goals

- No unified policy engine; no blocking review triggers; no automatic Sign
  generation from review findings (deny events only); no policy authoring
  CLI (`crucible policies new`) — YAGNI until asked for.

## Follow-ups seeded

- Phase 6 deferred items remain tracked in the project memory (repo_root-
  aware cascade loading would benefit `load_policies` too — same cwd
  convention, same limitation, noted not fixed here).

## Deviations accepted

- bash_deny candidate triggers use `bash_deny:<rule_id>` without command
  text (dedup-friendly; avoids leaking command content into a committed
  GUARDRAILS.md).
