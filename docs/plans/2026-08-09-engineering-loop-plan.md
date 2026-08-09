# Engineering Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bundle five adapted MIT skills + `meta/engineering-loop` + attribution + docs/LOOP.md, per `docs/specs/2026-08-09-engineering-loop.md` (the spec's Acceptance criteria are the gate).

**Architecture:** Pure content + tests: six new skill dirs under `src/crucible/skills/meta/`, one notices file, one doc. No hook or python-surface changes beyond tests.

## Global Constraints

- Spec sections 1–4 govern content; the spec's provenance-line format and adaptation keep/strip lists are binding.
- Every SKILL.md meets `meta/writing-good-skills`: description is "Use when X" + Do-NOT boundary; no upstream branding left in prose (attribution lives in the provenance line + notices file only).
- Fetch upstream content with `gh api "repos/<owner>/<repo>/contents/<path>" --jq .content | base64 -d` — never paraphrase from memory; adapt the actual text.
- triggers.yaml files follow the existing bundled shape (copy the shape from an existing `src/crucible/skills/meta/*/triggers.yaml`).
- Commit style `type: subject` (no parens), terse body, no trailer; `ruff check src/` clean; full suite baseline 873 (`--ignore=tests/test_integration.py` → 866) + new tests.
- Stage explicitly; never stage `.crucible/assertions/test-llm.yaml` or `CRUCIBLE_RESEARCH.md`.

---

### Task 1: Five adapted skills + THIRD-PARTY-NOTICES

**Files:**
- Create: `src/crucible/skills/meta/{brainstorming,systematic-debugging,tdd,wait-what,teach-me}/SKILL.md` + `triggers.yaml` each; `src/crucible/skills/meta/teach-me/knowledge/{mission-format,learning-record-format,resources-format,glossary-format}.md`
- Create: `THIRD-PARTY-NOTICES.md` (repo root)
- Modify: `CLAUDE.md` (bundled-skills section: provenance one-liners)
- Test: extend `tests/test_trigger_router.py` (one positive match case per new skill) and `tests/test_disclosure.py` or equivalent discovery test (bundled count 32 → 38 — locate the existing count assertion first)

**Sources (fetch, then adapt per the spec's keep/strip lists):**
- `gh api "repos/obra/superpowers/contents/skills/brainstorming/SKILL.md" --jq .content | base64 -d` (likewise systematic-debugging)
- `gh api "repos/mattpocock/skills/contents/skills/engineering/tdd/SKILL.md" ...` (verify path via the repo tree first), `skills/productivity/wait-what/SKILL.md`, `skills/productivity/teach/SKILL.md` + its four FORMAT files
- LICENSE files from both repos for the notices texts.

**Binding details:** provenance line format from spec §1; teach-me vault cascade documented verbatim per spec §1 (order: project teach.yaml → user teach.yaml → workspace fallback + first-use offer); lessons/assets stay workspace-side. THIRD-PARTY-NOTICES.md: both full MIT texts + adapted-skill lists + source URLs + the Karpathy attribution (currently prose in CLAUDE.md — copy it in, leave the CLAUDE.md mention but point it at the notices file).

- [ ] Fetch all upstream content; adapt each skill (keep/strip per spec); write triggers.
- [ ] Write notices file + CLAUDE.md lines.
- [ ] Extend router/discovery tests; RED where the count assertion was 32 → GREEN at 38.
- [ ] Full suite + ruff; commit `feat: bundle engineering-loop skill set with attribution`.

---

### Task 2: meta/engineering-loop + docs/LOOP.md

**Files:**
- Create: `src/crucible/skills/meta/engineering-loop/SKILL.md` + `triggers.yaml` + `knowledge/the-loop-at-scale.md`
- Create: `docs/LOOP.md`
- Modify: `README.md` (docs list line), `src/crucible/cli.py` (one line in `crucible init` output pointing at docs/LOOP.md — locate the init print block)
- Test: extend the Task-1 tests (count 38 includes this one — write Task 1's assertions at 38 counting this skill, and this task makes them true if Task 1 committed at 37; coordinate: Task 1 asserts 37, this task bumps to 38. Choose whichever split keeps each task's suite green at its own commit.)

**Binding details:** spec §2's six steps with the exact skill cross-references; plain jargon-free language; the "when to break the loop" note; LOOP.md per spec §4 with the worked non-technical example.

- [ ] Write skill + triggers + LOOP.md + README/init lines.
- [ ] Tests green at this task's commit; full suite + ruff; commit `feat: engineering-loop beginner cycle + LOOP.md`.

---

### Task 3: Sweep

- [ ] Wheel pin test: add the six `skills/meta/<name>/SKILL.md` paths to `tests/test_packaging.py` BUNDLED (verify package-data covers `skills/**` — check pyproject; fix if not).
- [ ] Docs counts: every bundled-skill count (README, CLAUDE.md, docs/FEATURES.md, docs/SKILLS.md) says 38; verify by `find src/crucible/skills -name SKILL.md | wc -l`.
- [ ] Notices test: `tests/test_packaging.py` (or a small new test) asserts THIRD-PARTY-NOTICES.md exists at repo root and contains both copyright lines — note: the notices file ships in the sdist/repo, not the wheel; assert via repo-relative path guarded to skip when running from an installed wheel.
- [ ] Full suite, wheel build + unzip grep for the six skills, fresh clone quick check.
- [ ] Commit `test: pin engineering-loop bundle + docs counts`; report numbers.
