# Phase 8 Spec — Dogfood + Ship v2.0.0

Version: 1.0 (2026-08-09). Design spec (brainstormed 2026-08-09, approved).
The final recorded phase of the v2 restructure: prove the whole surface by
using it, burn down the confirmed deferred minors, and release.

## Decisions (from brainstorm)

1. **Ship = push + GitHub release**: version 2.0.0, push local main to
   origin, tag `v2.0.0`, `gh release create` with notes. No PyPI.
2. **mcp cap stays** (`mcp>=1.0.0,<2.0.0`): the server.py 2.x migration is
   a post-2.0 follow-up (b17z/crucible#11).
3. **Dogfood scope**: crucible on itself (full surface, fresh-user path in
   a scratch clone) + the deferred-minor burn-down. No external repos this
   phase.
4. Release steps (push/tag/release/issue-filing) are executed by the
   controller directly after all gates are green — outward-facing actions
   stay out of subagent hands.

## 1. Structured dogfood pass

In a scratch clone (fresh venv, editable install), walk the new-user path
and exercise every v2 surface, recording actual output for each step:

1. `crucible init --with-claudemd` (CLAUDE.md, AGENTS.md, GUARDRAILS.md,
   REVIEW.md created), `crucible hooks claudecode init` (13+ hook
   registrations, idempotent on second run), `crucible baselines init`.
2. `crucible review` on a seeded file set: verifier suppressions visible,
   `--no-verify` shows raw, `--verify-llm` runs (live API — one small
   file, budget-capped).
3. Sign lifecycle end to end via the real hooks: bash_deny block →
   candidate → `crucible signs list` → `crucible-sign:` ack → Stop append
   → GUARDRAILS.md Sign.
4. REVIEW.md trigger nudge on a matching change; silent on non-matching.
5. `crucible policies list|validate`; spec-gate advisory on a feature
   prompt; `crucible-mode: exploration` bypass; pre-commit gate on a real
   commit (block + fix + pass).
6. Session context: `crucible system show` / SessionStart output contains
   enforcement summary, skills discovery, policies, review conventions.

Every rough edge found becomes (a) a burn-down fix this phase, or (b) a
filed GitHub issue for post-2.0 — nothing is silently dropped. New FP
classes found → corpus entries + predicate/binding additions ONLY if
trivially rule-decidable; otherwise corpus entry + issue.

Data handling (the repo goes public at ship): the committed dogfood doc
records outputs from seeded scratch-clone content only — no real project
code, no secrets, and machine-specific absolute paths outside the scratch
dir are elided. The `--verify-llm` step sends only a seeded scratch file
to the API (standard Anthropic API data handling applies; the feature is
opt-in and documented as such).

## 2. Deferred-minor burn-down (in scope, from the Phase 6/7 ledgers)

1. `append_signs.sh`: atomic GUARDRAILS.md write (temp file + `os.replace`)
   and insertion under the `## Signs` section (not EOF) when later
   sections exist.
2. `review_nudge.sh`: type-malformed frontmatter values (e.g.
   `min_changed_lines: ten`) handled silently (int coercion under
   try/except, trigger skipped); a shell case asserting exactly N nudge
   lines when N triggers match (count, not contains).
3. One shared REVIEW.md frontmatter rule: `claudecode.py`'s injection
   split uses the same first-line-`strip()=='---'` … next-line rule as
   review_nudge.sh (extract a small helper in claudecode.py; the hook
   keeps its self-contained copy but the RULES match — documented in
   both).
4. Wheel-content pin test: a python test asserting the installed package
   carries `templates/REVIEW.md`, `templates/GUARDRAILS.md`,
   `policies/*.yaml` (3), `verify/bundled/verifiers.yaml`, and the two
   `stop/*.sh` hooks.
5. Docs: FEATURES.md policy-cascade wording corrected (project → bundled,
   no user tier — deliberate); `phase7_spec.md` gains a one-line
   "Deviations accepted" note for the bash_deny trigger shape (no command
   text — dedup-friendly, avoids leaking commands into GUARDRAILS.md).
6. Phase 6 quick wins: `run_precommit` prints verifier errors to stderr
   when `config.verbose`; CLI `--verify-llm` threads the existing
   `--model`/`--token-budget`-style knobs if the review command already
   has them (reuse existing flags only — add nothing new; if absent, pass
   defaults and note it).

**Explicitly deferred past 2.0 (filed as GitHub issues, not fixed):**
repo_root-aware cascade loading (all cascades); no-git inline-suppressed
display asymmetry; policy user-tier cascade; mcp 2.x migration (#11,
already filed).

## 3. Release

1. Version: `pyproject.toml` 1.4.1 → **2.0.0**.
2. `CHANGELOG.md` (new file): a v2.0.0 section summarizing the restructure
   by phase (skills-first core, progressive disclosure, trigger routing,
   during-coding hooks, verifier + parallel delegation, policy layer +
   Signs + REVIEW.md), plus the notable fixes (suppression gate, retired
   model pins, live-API test guard) and the known-deferred list.
3. README/QUICKSTART sanity pass: commands shown must exist and match
   shipped behavior (no feature additions — corrections only).
4. Final but-for-real sweep: full suite (only the 7 documented env-broken
   integration failures), wheel contents, fresh clone from the release
   candidate commit.
5. Controller-executed ship: push main, tag `v2.0.0` (annotated), GitHub
   release with notes distilled from the CHANGELOG, file the deferred
   issues via `gh issue create`.

## Acceptance criteria (definition of done)

1. **Dogfood evidence**: every step in section 1 has recorded actual
   output in the phase report doc (`docs/v2/phase8_dogfood.md`, committed);
   each rough edge maps to a fix commit or a filed-issue reference —
   auditable one-to-one.
2. **Burn-down enforced by tests**: atomic-write + section-insertion cases
   in the append_signs suite; malformed-value + count cases in the
   review_nudge suite; the wheel-content pin test; all green in the full
   suite.
3. **Release integrity**: suite ≥ 860 + new tests (7 known env failures
   only); wheel ships everything the pin test asserts; fresh clone from
   the tagged commit installs and passes; `pyproject.toml` says 2.0.0;
   CHANGELOG.md exists with the v2.0.0 section.
4. **Shipped**: origin/main == local main, tag `v2.0.0` on the release
   commit, GitHub release published, deferred issues filed and
   cross-linked from the CHANGELOG's known-deferred list.

## Non-goals

- No PyPI publish; no mcp 2.x migration; no new features; no external-repo
  dogfooding; no predicate additions beyond trivially rule-decidable FP
  classes surfaced by the dogfood pass.
