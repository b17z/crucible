# Prewrite Checklist Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `crucible prewrite review --checklist` (agent-mediated, no-API semantic review) and the honest exit codes, per `docs/specs/2026-08-10-prewrite-checklist.md` (Acceptance criteria are the gate).

**Architecture:** Refactor assertion selection out of `prewrite_review` into a shared function; add a pure `render_prewrite_checklist`; wire flag + exit logic in `cmd_prewrite_review`. Then docs.

## Global Constraints

- Spec §1–4 binding: flag semantics, output format verbatim, exit rules (all-errored → 1 with pointer; partial → warning, findings-based), shared selection (no duplication), pure render (no network, errors as values).
- House patterns: `Result`/`ok`/`err` where errors are values; frozen dataclasses for new models; no new config keys.
- Tests must not reach the live API (conftest autouse guard exists; keyless tests additionally patch `crucible.enforcement.compliance._load_api_key_from_config` and clear `ANTHROPIC_API_KEY` from env).
- Commit style `type: subject` (no parens), terse body, no trailer; suite baseline 927 (`--ignore=tests/test_integration.py`); `ruff check src/` clean.
- Stage explicitly; never stage `.crucible/assertions/test-llm.yaml` or `CRUCIBLE_RESEARCH.md`.

---

### Task 1: Selection refactor + checklist render + CLI wiring + tests

**Files:**
- Modify: `src/crucible/prewrite/review.py` (factor selection; add render), `src/crucible/cli.py` (`cmd_prewrite_review` + argparse `--checklist` flag on the prewrite review subparser)
- Test: new `tests/test_prewrite_checklist.py`; existing `tests/test_prewrite*.py` stay green untouched

**Binding details (spec §1–3):**
- Shared selection function returns the ordered checks (id, severity, criteria) exactly as the API path runs them (template detection + skill filtering identical — call sites prove it by both using the new function).
- `render_prewrite_checklist` output format verbatim from spec §2 (header, instruction paragraph, `## Checks`, one `### <id> — severity: <severity>` block per assertion with verbatim criteria, no other prose).
- CLI: `--checklist` renders and exits 0, requires no `anthropic` import on that path and no key; `--checklist --json` emits `{"path", "template", "mode": "checklist", "checks": [{"id", "severity", "criteria"}]}`.
- API path exit fix in `cmd_prewrite_review`: all-errored (errors non-empty AND zero assertions evaluated — the review module must expose the evaluated count, e.g. on `PrewriteResult` as a new field or derivable) → print errors + pointer line naming `--checklist` → exit 1 even under `--fail-on`. Partial → `⚠ N of M assertions errored — partial evaluation` before the verdict, findings-based exit. API-run JSON gains `"evaluated"`.
- **tests/test_prewrite_checklist.py:** checklist render on a fixture spec (assert every applicable assertion id present, format markers present, exit 0 via `cmd_prewrite_review` with a Namespace); no-key guard test (monkeypatch `sys.modules` to make `import anthropic` raise if attempted on the checklist path, plus cleared env/config key); keyless API run → exit 1 + pointer (patch `_load_api_key_from_config` → None, `monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)`); keyless + `--fail-on info` → still 1; partial-error → warning + findings-based exit (patch `_run_prewrite_assertion` to error once, succeed once); full-pass and full-fail exits unchanged (patch `_run_prewrite_assertion`); `--checklist --json` shape.

- [ ] Refactor selection; write render; wire CLI + argparse.
- [ ] Write tests; full suite + ruff; commit `feat: prewrite checklist mode + honest exit codes`.

---

### Task 2: Docs wiring + sweep

**Files:**
- Modify: `src/crucible/skills/meta/delivery-loop/SKILL.md` (step-3 fallback names the command; keep the gate-blocking rule), `docs/PORTABILITY.md` (Models section line), `docs/BUILD-ALONG.md` (kickoff step 4 sentence — keep placeholders/tests green), `docs/FEATURES.md` (prewrite section flag docs)
- Test: extend `tests/test_prewrite_checklist.py` (delivery-loop SKILL.md names `--checklist`; PORTABILITY mentions it; BUILD-ALONG kickoff block mentions it)

**Binding details (spec §4):** exact sentences per spec §4; writing bar (`grep -P '[\x{00AD}\x{2018}\x{2019}\x{201C}\x{201D}]'`) on changed docs; run the live checklist command on a bundled-template spec fixture (exit 0) and every discover command printed in changed files.

- [ ] Docs edits + test extensions; verify commands live; full suite + ruff; commit `docs: checklist mode wiring`.
- [ ] Sweep: writing bar; `python -m build --wheel` + confirm no new data files needed; report numbers.
