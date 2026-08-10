# Delivery Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `meta/delivery-loop`, the notetaker genericization, and `docs/PORTABILITY.md`, per `docs/specs/2026-08-10-delivery-loop.md` (its Acceptance criteria are the gate).

**Architecture:** Pure content + tests: one new skill dir (SKILL.md + triggers.yaml only), one new doc, prose edits across five existing surfaces. No python changes beyond tests.

## Global Constraints

- Spec §1–4 binding: seven steps with exact carrier skills, workbench cascade order verbatim, Do-NOT boundary, conservative triggers, genericization register, portability matrix.
- Professional register in delivery-loop SKILL.md — no beginner metaphors; `meta/writing-good-skills` bar (description = "Use when X" + Do-NOT).
- No git command may appear in the loop's handoff/integration language.
- `vault:` key unchanged everywhere; existing teach-me/build-along cascade + content assertions must stay green.
- Discover commands in prose use full `meta/` names; writing bar: no smart-quote/soft-hyphen artifacts (`grep -P '[\x{00AD}\x{2018}\x{2019}\x{201C}\x{201D}]'`).
- Commit style `type: subject` (no parens), terse body, no trailer; suite baseline 911 (`--ignore=tests/test_integration.py`); `ruff check src/` clean.
- Stage explicitly; never stage `.crucible/assertions/test-llm.yaml` or `CRUCIBLE_RESEARCH.md`.

---

### Task 1: meta/delivery-loop skill + tests

**Files:**
- Create: `src/crucible/skills/meta/delivery-loop/SKILL.md`, `triggers.yaml`
- Test: extend `tests/test_trigger_router.py` (one positive case, e.g. "let's run the delivery loop on this"; one NEGATIVE case proving "help me debug this failing request" does not match delivery-loop); bump bundled-count assertion 39 → 40 (tests/test_disclosure.py); extend `tests/test_packaging.py` BUNDLED with the new SKILL.md path; new `tests/test_delivery_loop.py` for content assertions

**Binding details (spec §1):**
- SKILL.md sections in order: description frontmatter; who it's for (working engineers; beginners → `meta/engineering-loop`); the seven steps exactly as spec'd, each naming its carrier skill with the full `meta/` discover command; the workbench (cascade order VERBATIM from spec: teach.yaml `workbench:` project → user; else `vault:` → `<vault>/crucible-work/<project-slug>/`, project-slug = project directory name slugified; else `.crucible/workbench/` with gitignore verification); artifact names `spec.md`, `plan.md`, `ledger.md`, `decisions.md`; ledger append-only + recovery-from-ledger instruction; subagent pointer to `meta/engineering-loop`'s `knowledge/the-loop-at-scale.md`; Do-NOT boundary (never commit workbench artifacts; never prescribe branch/merge/CI mechanics; never skip independent review for "small" changes; never start step 5 before prewrite passes; beginners → engineering-loop).
- triggers.yaml phrases (conservative): "delivery loop", "delivery-loop", "professional loop", "work loop", "production loop". Copy the shape from `src/crucible/skills/meta/engineering-loop/triggers.yaml`.

**`tests/test_delivery_loop.py` must assert on SKILL.md:** the workbench cascade appears with `workbench:` before `vault:` before `.crucible/workbench/`; the string "never commit" (case-insensitive) near workbench; the handoff/step-6 text contains none of `git merge`, `git push`, `git rebase`, `pull request` as instructions (assert those substrings absent from the step-6 section); "prewrite review" appears before the execution step; all four artifact names present.

- [ ] Write SKILL.md + triggers.yaml per binding details.
- [ ] Extend router/count/packaging tests; write test_delivery_loop.py; RED at 39 → GREEN at 40.
- [ ] Full suite + ruff; commit `feat: delivery-loop professional cycle`.

---

### Task 2: PORTABILITY.md + genericization + wiring

**Files:**
- Create: `docs/PORTABILITY.md`
- Modify: `src/crucible/templates/CLAUDE.md` (one sentence: non-hook harnesses run `crucible skills discover` at session start — place it in the "No MCP server required" section); `src/crucible/skills/meta/teach-me/SKILL.md` and `src/crucible/skills/meta/build-along-course/SKILL.md` (vault prose genericized); `docs/BUILD-ALONG.md`, `docs/LOOP.md` (genericized + LOOP.md gains the step-up sentence); `src/crucible/skills/meta/engineering-loop/SKILL.md` (step-up sentence); `CLAUDE.md` (delivery-loop one-liner in bundled-skills list; count 40), `README.md` (PORTABILITY.md docs-list row; count 40), `docs/FEATURES.md`, `docs/SKILLS.md` (count 40)
- Test: extend `tests/test_delivery_loop.py` (PORTABILITY.md exists + README links it; generic phrase "reads markdown from a directory" present in BUILD-ALONG.md, LOOP.md, and both vault-aware SKILL.mds; no sentence requiring Obsidian — assert `"you need Obsidian"` style absent is unenforceable, so instead assert the generic phrase present in all four); extend `tests/test_cli.py::test_generated_claudemd_says_mcp_is_optional`-adjacent with the non-hook-harness sentence pin

**Binding details (spec §2–4):**
- Genericization register (adapt per sentence): "your notes folder — any tool that reads markdown from a directory (Obsidian, Logseq, an in-house notetaker)". Obsidian stays as example; `vault:` key and all paths unchanged; existing content assertions (teach-me cascade, build-along vault note) must still pass — run them before committing.
- PORTABILITY.md structure: The contract (shell + instructions file; CLI is the API; `--no-git` exists) / The matrix (Claude Code any-model-backend incl. gateways = hooks+routing+injection+gates auto-fire; Codex, Gemini CLI, pi, Cursor = AGENTS.md read, CLI-driven, no auto-fire, AGENTS.md must instruct `crucible skills discover` at session start) / Models (only `--llm` is Anthropic-API-bound).
- Step-up sentences: engineering-loop SKILL.md and LOOP.md each get ONE sentence pointing at `meta/delivery-loop` for professional work; delivery-loop already points down (Task 1).

- [ ] Write PORTABILITY.md; template sentence; genericization sweep; wiring lines; counts 40.
- [ ] Extend tests; verify every printed discover command exits 0; full suite + ruff; commit `feat: portability doc + notetaker genericization`.

---

### Task 3: Sweep

- [ ] `find src/crucible/skills -name SKILL.md | wc -l` = 40; docs counts all say 40 (grep README, CLAUDE.md, docs/FEATURES.md, docs/SKILLS.md).
- [ ] Wheel build + `unzip -l` grep for `delivery-loop/SKILL.md` + triggers.yaml; clean artifacts after.
- [ ] Run every `crucible skills discover meta/...` printed in the new/changed docs; all exit 0.
- [ ] Writing-bar grep over changed docs; full suite + ruff; commit `test: pin delivery-loop bundle + docs counts` only if changes needed; report numbers.
