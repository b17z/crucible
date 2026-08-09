# Phase 8 — Structured Dogfood Pass

Version: 1.0 (2026-08-09). Evidence doc for `docs/v2/phase8_spec.md` §1.

Method: a scratch clone of this repo (`git clone` into a scratchpad dir,
fresh venv, `pip install -e ".[dev]"`, crucible 1.4.1) was used to walk the
new-user path in a genuinely fresh sub-project (`fresh-project/`, its own
`git init`), since the repo root itself already dogfoods `.crucible/` and
isn't representative of a first-time user. All commands below ran with
the scratch venv's `crucible` binary on PATH (`which crucible` confirmed
it resolved inside the scratch venv, not the main repo's editable
install). Machine-absolute paths outside the scratch dir are elided as
`<scratch>/…`. No secrets are recorded; the `--verify-llm` step sent only
a small seeded demo file to the Anthropic API via the machine's
already-configured credentials.

Seeded content: `demo/app.py` (an `eval(` violation), `demo/auth.py`
(REVIEW.md nudge target — matches `**/auth*`), `tests/test_demo.py`
(assert-based, verifier target for `bandit/B101`).

---

## Step 1: init / hooks / baselines

```
crucible init --with-claudemd
crucible hooks claudecode init   # x3, to check idempotency
crucible baselines init
```

Actual output (init):
```
No specific stack detected
Created <scratch>/fresh-project/.crucible/review.yaml
Created <scratch>/fresh-project/.crucible/approved-deps.yaml

Recommended skills for your stack: security-engineer

To customize a skill, run:
  crucible skills init security-engineer
Created <scratch>/fresh-project/CLAUDE.md
Created <scratch>/fresh-project/AGENTS.md
Created <scratch>/fresh-project/REVIEW.md

Initialized <scratch>/fresh-project/.crucible

Next steps:
  1. Customize skills:     crucible skills init <skill>
  2. Customize knowledge:  crucible knowledge init <file>
  3. Install git hooks:    crucible hooks install
  4. Claude Code hooks:    crucible hooks claudecode init
```
Files created: `CLAUDE.md`, `AGENTS.md`, `REVIEW.md`. **No `GUARDRAILS.md`.**
(Its creation turned out to be lazy — see Step 3, where it's created by
the Sign-append Stop hook on first acknowledged Sign, not by `init`.)

Actual output (hooks claudecode init, run 1):
```
Created Claude Code settings: .claude/settings.json
Created Crucible config: .crucible/claudecode.yaml

Crucible hooks installed:
  - PreToolUse: Bash deny-list + Edit/Write assertion pre-check
  - PostToolUse: Reviews files when Claude edits them
  - SessionStart: Injects enforcement context automatically
  - UserPromptSubmit: trigger routing + magic comments
  - FileChanged/ConfigChange/SubagentStop: settings integrity + config diff
  - SubagentStart: skill inheritance for spawned agents
  - PreCompact/PostCompact: context protection
```
`.claude/settings.json` hook registration count (by event): PostToolUse 1,
PreToolUse 3, SessionStart 1, UserPromptSubmit 2, FileChanged 2,
ConfigChange 1, SubagentStop 1, SubagentStart 1, PreCompact 1,
PostCompact 1, Stop 2 = **16 total hook entries** (≥13 claimed). Diffed
byte-for-byte `.claude/settings.json` between run 2 and run 3 — identical
(idempotent confirmed).

Actual output (baselines init):
```
Baselines captured in .crucible/baselines/
  settings     .claude/settings.json  sha256=2b483132cb96…
  mcp          .mcp.json  (absent — recorded as MISSING)
  extensions   .vscode/extensions.json  (absent — recorded as MISSING)
  manifest     (3 entries; tamper anchor)
```

**Verdict: ROUGH: init runs correctly and hooks are verified idempotent,
but `crucible init --with-claudemd` does not create `GUARDRAILS.md` as
the spec step 1 lists — it's created on-demand by the Sign lifecycle
(Step 3). Separately, running `init` against the repo root itself (which
ships its own `.crucible/`) refuses with "already exists" — correct
behavior, but means the "fresh user" path can't be walked at the repo
root of a clone of this project; a clean subdirectory was needed instead.**

---

## Step 2: review + verifier + --verify-llm

```
crucible review demo/ --no-git                              # default: verifier + LLM compliance
crucible review demo/ --no-git --no-compliance               # verifier suppressions, no LLM compliance cost
crucible review tests/ --no-git --no-compliance               # verifier suppression on bandit/B101
crucible review tests/ --no-git --no-compliance --no-verify   # raw findings
crucible review demo/app.py --no-git --no-compliance --verify-llm   # the one live --verify-llm call
```

Default run (`demo/`, no flags beyond `--no-git`) surfaced the seeded
`eval()` finding (bandit B307 + pattern `no-eval`) plus, unexpectedly,
**22 LLM-backed `spec-*` compliance findings against `demo/auth.py`**
(`spec-missing-auth`, `spec-missing-data-handling`, `spec-no-failure-modes`,
`spec-no-success-criteria`, `spec-no-version`), consuming 10,010 LLM
tokens — a live API call made by default, not opt-in. Re-running with
`--no-compliance` suppressed that cost and left only the pattern/bandit
finding.

`tests/test_demo.py --no-compliance` (verifier suppression visible):
```
✅ No issues found.
Assertions: 19 checked, 11 skipped

Suppressed by verifier (2):
  ./tests/test_demo.py:6 bandit/B101 — verifier:is_test_file — assert is pytest's mechanism; test runs never use -O
  ./tests/test_demo.py:10 bandit/B101 — verifier:is_test_file — assert is pytest's mechanism; test runs never use -O
```

Same target with `--no-verify` (raw, unsuppressed):
```
Found 2 static analysis issue(s):
🔵 [LOW] ./tests/test_demo.py:6
   bandit/B101: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
🔵 [LOW] ./tests/test_demo.py:10
   bandit/B101: Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.
```
bandit was installed and functional in-venv (1.9.3); no fallback to the
enforcement-assertion path was needed.

`--verify-llm` on `demo/app.py` (one file, one live call): completed
without error; the `eval()` finding was correctly NOT suppressed (true
positive held up under the adversarial counterargument pass). No retry
was needed — the call succeeded on the first attempt.

Every review invocation also reported **2 semgrep tool errors**
(`semgrep exited 1 with no output` — Python traceback importing
`semgrep.cli`). Root-caused: the scratch venv has no `semgrep` package
installed (`pip show semgrep` → not found); the `semgrep` resolved on
PATH was a global pyenv shim with a broken install, unrelated to the
`pip install -e ".[dev]"` the scratch venv performed. This is an
environment issue, not a crucible defect — crucible degraded correctly
(reported the tool error, did not crash, other tools' findings still
returned).

**Verdict: ROUGH: LLM compliance assertions (`spec-missing-auth` et al.)
run on every `crucible review` by default — a live API call happens
without `--verify-llm` and without being flagged in the CLI help as
opt-in/costs-tokens the way `--verify-llm` is. Verifier suppression,
`--no-verify` raw mode, and the single `--verify-llm` call all worked
exactly as specified. semgrep tool error is environment-local (broken
global pyenv shim), not a crucible bug.**

---

## Step 3: sign lifecycle end to end

```
echo '{"tool_input":{"command":"chmod -R 0777 /"}}' | /bin/bash bash_deny.sh   # block
crucible signs list                                                            # candidate visible
echo '{"prompt":"crucible-sign: <id>"}' | /bin/bash magic_comments.sh          # ack
crucible signs list                                                            # moved to acked
echo '{}' | /bin/bash append_signs.sh                                          # Stop append
cat GUARDRAILS.md
```

Block (`bash_deny.sh`, piped JSON envelope on stdin, run via
`/bin/bash <path>` as `tests/test_bash_deny.sh` does):
```
🛑 crucible: COMMAND BLOCKED by bash deny-list

Command: chmod -R 0777 /

  [chmod-777-root] world-writable root filesystem
...
EXIT:2
```
The block itself wrote a candidate Sign automatically (no separate step
needed):
```
crucible signs list
pending:
  e2da4402  bash_deny:chmod-777-root  [2026-08-09 via bash_deny.sh]
acked (unappended):
```

Ack via `crucible-sign: e2da4402` piped into `magic_comments.sh`:
```
crucible: sign e2da4402 acknowledged
```
```
crucible signs list
pending:
acked (unappended):
  e2da4402  bash_deny:chmod-777-root  [2026-08-09 via bash_deny.sh]
```

Stop hook (`append_signs.sh`) run: exit 0, no stdout/stderr (advisory,
silent on success). After it: `crucible signs list` showed both lists
empty, and `GUARDRAILS.md` was created for the first time, containing:
```
### Sign 1 — Do not run commands matching `chmod-777-root`:

- **Trigger:** bash_deny:chmod-777-root
- **Instruction:** Do not run commands matching `chmod-777-root`: world-writable root filesystem
- **Reason:** blocked by the bash deny-list
- **Provenance:** 2026-08-09 via bash_deny.sh
```

**Verdict: OK. Full lifecycle (block → candidate → list → ack → Stop
append → GUARDRAILS.md) worked exactly as specified end to end, and this
also explains the Step 1 GUARDRAILS.md absence — it's intentionally
lazy-created here, not at `init` time.**

---

## Step 4: REVIEW.md trigger nudge

Seeded `REVIEW.md` frontmatter (from `init`) has two triggers:
`src/**/*.py` (min 50 changed lines) and `**/auth*` / `**/crypto*` (any
touch).

First attempt (before an initial commit existed in `fresh-project`) was
silent even with `demo/auth.py` staged — `git diff --name-only HEAD`
fails on a repo with no commits yet (`fatal: ambiguous argument 'HEAD'`),
and `review_nudge.sh`'s git wrapper swallows that failure, returning
empty file lists. After making an initial commit (so `HEAD` exists) and
modifying `demo/auth.py`:
```
crucible: Security-sensitive paths — review with the security-engineer skill (REVIEW.md trigger matched)
```
Non-matching case (`demo/app.py`, not under `src/`, doesn't match
`**/auth*`/`**/crypto*`): no output, exit 0, as specified.

**Verdict: ROUGH: on a brand-new repo with no commits yet, the nudge
silently no-ops instead of nudging (or explicitly staying silent by
design) because `git diff --name-only HEAD` errors before any commit
exists. Matches the hook's documented fail-silent posture, but a truly
fresh project's very first commit is exactly the moment this silently
skips — the matching and non-matching cases both worked correctly once
a HEAD existed.**

---

## Step 5: policies / spec-gate / pre-commit

```
crucible policies list
crucible policies validate
```
```
bash_denylist            high     Block destructive or exfil-shaped shell commands before they run.  [1 hook(s), bundled]
dependency_quarantine    high     Block any npm/pip/pnpm/cargo install that adds a new package@version unless explicitly pre-approved.  [1 hook(s), bundled]
settings_integrity       critical Hash-monitor .claude/settings.json, .mcp.json, .vscode/extensions.json against baselines captured by `crucible baselines init`.  [1 hook(s), bundled]

All policies valid (3 checked)
```

Spec-gate advisory: a prompt phrased to match `meta/spec-validator`'s
trigger regex ("Please implement a new feature for CSV export") was
needed — several plausible feature-request phrasings ("Add a new
capability: CSV export", "Implement a new endpoint for CSV export")
matched other skills but not `meta/spec-validator`, because the trigger
regex requires `implement/build/create/add` immediately adjacent to a
feature-noun, or a conversational lead-in ("please/let's/can you") next
to a build verb. With a matching prompt, `route.sh` (piped the same way):
```
crucible: skills activated for this prompt:
  - meta/coding-discipline
  - meta/spec-validator
  - product-engineer

📋 crucible: this looks like a feature request, and no spec/PRD/design
doc was found. Spec-driven workflow keeps scope bounded and reviewable.

Options:
  • Write one first:  crucible prewrite init prd <name>
  • Sketch without a spec this session: add 'crucible-mode: exploration'
    to your next message.
```
exit 0 (advisory, not strict). With `crucible-mode: exploration` set via
`magic_comments.sh` first, `route.sh` on the same prompt:
```
crucible: skills activated for this prompt:
  - meta/coding-discipline
  - meta/spec-validator
  - product-engineer
crucible: spec-validator bypassed (exploration mode).
```

Pre-commit gate (`crucible hooks install`, then a real `git commit`):
block on a new file with an `eval()` violation —
```
Enforcement Assertions:
  🔴 [ERROR] [Pattern] no-eval
    demo/danger.py:5:12: eval() is dangerous - use ast.literal_eval() for data or safer alternatives
Pre-commit: FAILED
EXIT:1
```
fix (swap to `ast.literal_eval`) and commit —
```
Checked 1 file(s), 22 assertion(s) - no issues found
[main 60d8e0c] feat: add danger module
EXIT:0
```

**Verdict: OK. Policies list/validate, spec-gate advisory, exploration
bypass, and the pre-commit block→fix→pass cycle all worked exactly as
specified. The only friction was discovering the exact trigger-regex
phrasing needed to activate `meta/spec-validator` — a usability note,
not a defect.**

---

## Step 6: session context

```
crucible system init
crucible system show
echo '{"hook_event_name":"SessionStart","source":"startup"}' | crucible hooks claudecode session
```

`crucible system show` (CLI preview) printed 3 sections: Enforcement
Summary (severity-tiered assertion catalog), System Files
(`focus.md`, `team-patterns.md`), Recent Findings (empty — no reviews
run against `fresh-project` yet at that point).

The actual SessionStart hook (`crucible hooks claudecode session`, the
command Claude Code invokes) returned a JSON envelope
(`hookSpecificOutput.additionalContext`) with a superset: Enforcement
Summary, Focus, Team Patterns, **Review Conventions** (from `REVIEW.md`'s
body), **Available skills (Tier 1 discovery)** — all 32 bundled skills
listed with one-line trigger descriptions — and **Active policies**
(`bash_denylist, dependency_quarantine, settings_integrity`).

**Verdict: OK. The real SessionStart injection contains every element
the spec step lists (enforcement summary, skills discovery, policies,
review conventions). `crucible system show` is a narrower preview (3 of
the 5 sections) — worth knowing it isn't a 1:1 stand-in for the real
hook output, but not a defect since it's documented as a preview.**

---

## Findings

| # | Step | Verdict | Disposition | Rationale |
|---|------|---------|-------------|-----------|
| 1 | S1 init | ROUGH: `init --with-claudemd` doesn't create `GUARDRAILS.md` despite spec step 1 listing it as an init output | file-issue | Working as designed (GUARDRAILS.md is lazily created by the Sign-append Stop hook — confirmed in S3) — the spec/docs wording is what's stale, not the code; a doc-wording fix is lower-risk to defer than to rush into this phase's burn-down. |
| 2 | S1 init | ROUGH: `init` (correctly) refuses on the repo root of a clone of this project because it already ships `.crucible/` — the "fresh user" path could only be walked in a clean subdirectory | no-action (recorded) | Correct, intentional behavior (guards against clobbering existing config); the friction is specific to dogfooding crucible-on-crucible, not a real new-user scenario — no fix needed, just a documented dogfood-methodology note. |
| 3 | S2 review | ROUGH: LLM compliance assertions (`spec-missing-auth` etc.) make a live API call and spend tokens on every `crucible review` by default, without `--verify-llm` — the CLI help doesn't flag this default-on behavior as costing tokens the way `--verify-llm` is flagged | file-issue | Real UX gap (silent default cost) but not a correctness bug and not trivially rule-decidable as an FP class; needs a documentation/help-text decision (and possibly a default-off discussion) that's bigger than a burn-down-sized fix. |
| 4 | S2 review | ROUGH: semgrep tool errors (Python traceback, "exited 1 with no output") on every review | no-action (recorded) | Root-caused to a broken global pyenv `semgrep` shim leaking onto PATH ahead of the venv's (absent) install — an environment defect, not a crucible defect; crucible degraded correctly. No crucible-side action; noted so it isn't mistaken for a regression in a future pass. |
| 5 | S4 nudge | ROUGH: `review_nudge.sh` silently no-ops on a repo with no commits yet (`git diff --name-only HEAD` fails before any commit exists) instead of nudging or explicitly no-op-by-design | file-issue | Matches the hook's documented fail-silent posture and is a narrow edge case (a brand-new repo's very first commit), not a regression; still worth a filed issue since a first commit touching an auth-shaped path is a plausible real scenario where the nudge would silently fail to fire. |
| 6 | S5 spec-gate | ROUGH: no single obviously-correct feature-request phrasing reliably triggers `meta/spec-validator`; several natural phrasings ("add a new capability", "implement a new endpoint for X") don't match the trigger regex | file-issue | Usability friction in trigger-regex coverage, not a correctness bug — the regex works exactly as written once the right phrasing is used. Expanding trigger coverage is a rule/predicate change and per this phase's non-goals ("no predicate additions beyond trivially rule-decidable FP classes"), out of scope for the burn-down; better suited to a follow-up pass with real usage data on what phrasings people actually use. |

All other observations across S1 (baselines), S2 (verifier suppression,
`--no-verify`, the single `--verify-llm` call, bandit-in-venv), S3 (full
sign lifecycle), S5 (policies list/validate, exploration bypass,
pre-commit block/fix/pass), and S6 (SessionStart context contents) were
`OK` — no findings.
