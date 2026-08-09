# Phase 8 Implementation Plan — Dogfood + Ship v2.0.0

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the full v2 surface by structured dogfooding, burn down the confirmed deferred minors, and prepare the v2.0.0 release (the controller executes the actual push/tag/release/issue-filing after all gates pass).

**Architecture:** Spec: `docs/v2/phase8_spec.md`. Task 1 gathers evidence and may add controller-injected fix tasks; Tasks 2–6 are the burn-down; Tasks 7–8 are release prep + final sweep. No new features.

**Tech Stack:** Python 3.11+, bash 3.2 hooks, pytest; gh CLI (controller only).

## Global Constraints

- No new features; corrections and tests only. The spec's acceptance criteria are the phase gate.
- Every hook stays advisory/contract-identical: no exit-code or output-contract changes beyond what a task explicitly specifies.
- Bash 3.2-safe; errors as values; commit style `type: subject` (no parens), terse body, no trailer.
- `ruff check src/` clean; full suite green (`python -m pytest -q --ignore=tests/test_integration.py`, baseline 860; the 7 `test_integration.py` failures are known-env-broken).
- Stage explicitly (never `git add -A`); never stage `.crucible/assertions/test-llm.yaml` or `CRUCIBLE_RESEARCH.md`.
- The dogfood doc (`docs/v2/phase8_dogfood.md`) records scratch-clone content only: no secrets, no real project code, machine-absolute paths outside the scratch dir elided (write `<scratch>/…`).

---

### Task 1: Structured dogfood pass

**Files:**
- Create: `docs/v2/phase8_dogfood.md`

**Interfaces:**
- Produces: the committed evidence doc. One `## Step N` section per spec-section-1 step (init/hooks/baselines; review + verifier + --verify-llm; sign lifecycle; nudge; policies/spec-gate/pre-commit; session context), each with the command(s) run, the actual (elided) output, and a verdict line: `OK`, `ROUGH: <description>` or `BROKEN: <description>`. A final `## Findings` table mapping every ROUGH/BROKEN to `fix-this-phase` or `file-issue`, with one-line rationale.

- [ ] **Step 1: Set up the scratch clone** — `SCRATCH=<scratchpad>/p8-dogfood`; `git clone /Users/be.nvy/crucible "$SCRATCH"`, fresh venv, `pip install -e ".[dev]"`. All subsequent commands run in the scratch clone with the scratch venv's `crucible` on PATH (activate the venv or use its bin paths).
- [ ] **Step 2: Walk the surface** — execute spec section 1's six steps in order, recording each. Seeded content: a `demo/app.py` with an `eval(` violation, a `demo/auth.py` (nudge target), a `tests/test_demo.py` with asserts (verifier target — but note bandit findings need the tool installed; if bandit is env-broken use the enforcement-assertion path instead and note it). For `--verify-llm` use ONE small seeded file. For the pre-commit step: `git init` semantics are already there (it's a clone) — install the git hook (`crucible hooks install`), attempt a commit with the violation (expect block), fix, commit (expect pass).
- [ ] **Step 3: Write the doc** — per the Interfaces contract, with the data-handling rules applied.
- [ ] **Step 4: Commit** — `git add docs/v2/phase8_dogfood.md && git commit -m "docs: Phase 8 structured dogfood evidence"` (in the MAIN repo — the doc is written there, only the exercising happened in the scratch clone).
- [ ] **Step 5: Report** — reply with the Findings table verbatim in your report file so the controller can inject fix tasks.

---

### Task 2: append_signs.sh — atomic write + section insertion

**Files:**
- Modify: `src/crucible/interfaces/claude_code/stop/append_signs.sh` (python heredoc)
- Test: `tests/test_append_signs.sh` (append 2 cases)

**Interfaces:**
- Produces: GUARDRAILS.md written via temp file in the same directory + `os.replace` (atomic on POSIX); new Signs inserted at the END of the `## Signs` section (immediately before the next `\n## ` heading if one exists, else at EOF). All existing behavior (numbering, placeholder removal, malformed-skip, always exit 0) unchanged.

- [ ] **Step 1: Write the failing shell cases** — append to `tests/test_append_signs.sh` before the final FAILED check (follow the suite's existing mktemp/RUNNER conventions):
  - Case `section-insertion`: GUARDRAILS.md containing `## Signs` with one existing `### Sign 1`, followed by a later `## Appendix` section with the line `KEEP-LAST`. After the hook runs with one acked candidate, assert `### Sign 2` appears BEFORE `## Appendix` (e.g. `awk '/### Sign 2/{s2=NR} /## Appendix/{ap=NR} END{exit !(s2<ap)}'`) and `KEEP-LAST` is still the file's content after the appendix heading.
  - Case `atomic-write-no-partial`: after a successful run, assert no `GUARDRAILS.md.tmp*`/temp artifacts remain in the project dir (`ls GUARDRAILS.md.* 2>/dev/null | wc -l` is 0).
- [ ] **Step 2: RED** — `/bin/bash tests/test_append_signs.sh` → section-insertion FAILS (current code appends at EOF).
- [ ] **Step 3: Implement** — in the heredoc: build the new content string; find the insertion point: locate the `## Signs` heading, then the next line matching `^## ` after it; insert the rendered blocks before that heading (with a separating blank line) or append at EOF when none. Write via `tempfile.NamedTemporaryFile(dir=<same dir>, delete=False)` + `os.replace(tmp, guardrails_path)`.
- [ ] **Step 4: GREEN** — full shell suite + `python -m pytest tests/test_hooks_shell.py tests/test_signs.py -q` + `/bin/bash tests/test_sign_lifecycle_e2e.sh`.
- [ ] **Step 5: Commit** — `git commit -m "fix: append_signs inserts under Signs section, writes atomically"` (staged files explicitly).

---

### Task 3: review_nudge.sh — silent malformed values + count assertion

**Files:**
- Modify: `src/crucible/interfaces/claude_code/stop/review_nudge.sh` (python heredoc)
- Test: `tests/test_review_nudge.sh` (append 2 cases)

**Interfaces:**
- Produces: a trigger whose `min_changed_lines` is not int-coercible is SKIPPED silently (no traceback on stderr; other triggers still evaluated; exit 0). Suite gains a count assertion: two matching triggers → exactly 2 `crucible:` lines on stderr.

- [ ] **Step 1: Write the failing shell cases** — append:
  - Case `type-malformed-min-lines-silent`: REVIEW.md frontmatter with two triggers — one `min_changed_lines: ten` (paths matching a changed file) and one valid path-only trigger that matches. Assert exit 0, stderr contains exactly ONE `crucible:` line (the valid trigger), and stderr does NOT contain `Traceback`.
  - Case `two-matches-exactly-two-lines`: two valid triggers both matching different changed files; assert `grep -c '^crucible:' <stderr-file>` equals 2.
- [ ] **Step 2: RED** — the malformed case currently prints a traceback.
- [ ] **Step 3: Implement** — wrap the per-trigger `min_changed_lines` handling: `try: threshold = int(raw) except (TypeError, ValueError): continue` (with a one-line comment: malformed trigger values are skipped, matching the silent-on-malformed contract).
- [ ] **Step 4: GREEN** — `/bin/bash tests/test_review_nudge.sh`, `python -m pytest tests/test_hooks_shell.py -q`.
- [ ] **Step 5: Commit** — `git commit -m "fix: review_nudge skips type-malformed trigger values silently"`.

---

### Task 4: Shared REVIEW.md frontmatter rule

**Files:**
- Modify: `src/crucible/hooks/claudecode.py` (the REVIEW.md injection block in `run_session_hook`)
- Test: `tests/test_session_hooks.py` (append)

**Interfaces:**
- Produces: `_split_review_frontmatter(text: str) -> str` module-level helper in claudecode.py: if the FIRST line's `strip()` is `---`, find the next line whose `strip()` is `---`; the body is everything after that line; otherwise the body is the whole text. The injection block uses it. A comment in the helper AND in review_nudge.sh's parser notes the rule is intentionally duplicated and must match (`first/next line strip()=='---'`).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_session_hooks.py`:

```python
class TestFrontmatterRule:
    def test_dash_run_line_not_treated_as_closer(self, tmp_path, monkeypatch, capsys) -> None:
        """A '----' rule line inside frontmatter must not close it (the old
        find('\\n---') bug); only a line that strips to exactly '---' does."""
        import json

        from crucible.hooks.claudecode import run_session_hook

        monkeypatch.chdir(tmp_path)
        (tmp_path / "REVIEW.md").write_text(
            "---\ntriggers:\n  - paths: ['x']\n    note: 'a----b'\n---\n# Body\nREAL-BODY\n"
        )
        run_session_hook(json.dumps({"cwd": str(tmp_path)}))
        out = capsys.readouterr().out
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert "REAL-BODY" in ctx
        assert "triggers:" not in ctx

    def test_no_frontmatter_whole_text_is_body(self, tmp_path, monkeypatch, capsys) -> None:
        import json

        from crucible.hooks.claudecode import run_session_hook

        monkeypatch.chdir(tmp_path)
        (tmp_path / "REVIEW.md").write_text("# Conventions only\nNO-FM-BODY\n")
        run_session_hook(json.dumps({"cwd": str(tmp_path)}))
        out = capsys.readouterr().out
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        assert "NO-FM-BODY" in ctx
```

- [ ] **Step 2: RED** — the `a----b` note (containing `----`) breaks the current `text.find("\n---", 3)` logic mid-line.
- [ ] **Step 3: Implement** — the helper with line-based splitting; replace the inline find() logic; add the matching-rule comments in both files.
- [ ] **Step 4: GREEN** — `python -m pytest tests/test_session_hooks.py -q`; `/bin/bash tests/test_review_nudge.sh` (unchanged but verifies the documented rule still holds there); `ruff check src/`.
- [ ] **Step 5: Commit** — `git commit -m "fix: line-based REVIEW.md frontmatter split, rule documented in both parsers"`.

---

### Task 5: Wheel-content pin test

**Files:**
- Test: `tests/test_packaging.py` (create)

**Interfaces:**
- Produces: a test asserting the INSTALLED package (editable or wheel) carries every bundled artifact:

```python
"""Pin the bundled files the wheel must ship (regression guard for
package-data): a file listed here that exists in the repo but not in the
installed package means pyproject's package-data globs regressed."""

from pathlib import Path

import crucible

PKG = Path(crucible.__file__).parent

BUNDLED = [
    "templates/REVIEW.md",
    "templates/GUARDRAILS.md",
    "templates/AGENTS.md",
    "verify/bundled/verifiers.yaml",
    "interfaces/claude_code/stop/append_signs.sh",
    "interfaces/claude_code/stop/review_nudge.sh",
    "interfaces/claude_code/pre_tool_use/bash_deny.sh",
    "policies/dependency_quarantine.yaml",
    "policies/settings_integrity.yaml",
    "policies/bash_denylist.yaml",
]


def test_bundled_files_ship() -> None:
    missing = [rel for rel in BUNDLED if not (PKG / rel).exists()]
    assert missing == [], f"bundled files missing from installed package: {missing}"
```

- [ ] **Step 1: Write it**, **Step 2: run** (`python -m pytest tests/test_packaging.py -q` → PASS immediately on the editable install — that's expected; the guard's value is the WHEEL check: `pip install dist/*.whl` in a scratch venv then run this test, which Task 8's sweep does), **Step 3: commit** — `git commit -m "test: pin bundled package contents"`.

---

### Task 6: Docs corrections + Phase 6 quick wins

**Files:**
- Modify: `docs/FEATURES.md` (policy cascade wording), `docs/v2/phase7_spec.md` (Deviations accepted note), `src/crucible/hooks/precommit.py` (verbose verify errors), `src/crucible/cli.py` (LLM knob threading — reuse existing flags only)
- Test: `tests/test_precommit.py` (append)

**Interfaces:**
- FEATURES.md: the policy layer paragraph states the cascade as "project (.crucible/policies/) then bundled" — no user tier (deliberate).
- phase7_spec.md: append `## Deviations accepted` with one line: bash_deny candidate triggers use `bash_deny:<rule_id>` without command text (dedup-friendly; avoids leaking command content into a committed GUARDRAILS.md).
- precommit.py: where `_verify_errors` is currently discarded, when `config.verbose` print each to stderr as `crucible: verify: <error>`; variable renamed accordingly.
- cli.py: the review command's existing LLM-related flags (check what exists: `--model`/`--token-budget` style on the review or prewrite parser) thread into `run_llm_verification(model=..., token_budget=...)` where the `--verify-llm` call sites pass defaults today. If the review command has NO such flags, thread nothing, add nothing, and record that in the report (spec: reuse existing flags only).

- [ ] **Step 1: Failing test** — append to `tests/test_precommit.py` a case: project with a malformed `.crucible/verifiers.yaml` + `verbose: true` in precommit.yaml → `run_precommit`'s stderr (capsys) contains `crucible: verify:`. (Non-verbose case: silent — assert both.)
- [ ] **Step 2: RED → implement → GREEN** — targeted tests + full suite.
- [ ] **Step 3: Docs edits** (no tests).
- [ ] **Step 4: Commit** — `git commit -m "fix: verbose verify errors in precommit + docs corrections"`.

---

### Task 7: Release prep

**Files:**
- Modify: `pyproject.toml` (version 2.0.0)
- Create: `CHANGELOG.md`
- Modify: `README.md` / `docs/QUICKSTART.md` (corrections only, if the sanity pass finds drift)

**Interfaces:**
- CHANGELOG.md format: `# Changelog`, `## 2.0.0 (2026-08-09)` with subsections `### The v2 restructure` (one bullet per phase, one line each), `### Notable fixes` (suppression gate honored in pre-commit; retired model pins replaced; live-API test guard; deny-path fail-open hardening), `### Known deferred` (repo_root-aware cascades, no-git suppressed-display asymmetry, policy user tier, mcp 2.x migration — each with `(#N)` placeholder the controller fills after filing issues).

- [ ] **Step 1: Version bump** — `pyproject.toml` version = "2.0.0".
- [ ] **Step 2: CHANGELOG.md** — per the contract above; distill phase bullets from `docs/v2/phase*_spec.md` headers (read them; keep each to one line).
- [ ] **Step 3: README/QUICKSTART sanity pass** — run every command block shown in both docs against the installed CLI (`--help` level verification is fine for destructive ones); fix drift (corrections only, no new sections); list each correction in your report.
- [ ] **Step 4: Verify + commit** — full suite; `git commit -m "release: crucible 2.0.0"` (all release-prep files in one commit).

---

### Task 8: Final sweep

**Files:** none new (report only, to the SDD report file).

- [ ] **Step 1: Full suite** — `python -m pytest -q` → only the 7 documented env-broken failures.
- [ ] **Step 2: Wheel** — build; `unzip -l` shows everything `tests/test_packaging.py` pins; then in a scratch venv `pip install dist/*.whl && python -m pytest tests/test_packaging.py -q` from a directory OUTSIDE the repo (proves the wheel, not the checkout) — expect PASS; then clean dist/build.
- [ ] **Step 3: Fresh clone** — clone current HEAD to the scratchpad, venv, editable install, suite (`--ignore=tests/test_integration.py`) → all pass.
- [ ] **Step 4: Report** — exact numbers for each step. The controller ships from here (push, tag v2.0.0, gh release, file deferred issues, fill CHANGELOG issue numbers, amend/commit).
