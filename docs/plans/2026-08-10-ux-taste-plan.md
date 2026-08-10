# UX Taste Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the three taste knowledge files, the `uiux-engineer` upgrade, `meta/frontend-taste`, notices, and the loop wiring, per `docs/specs/2026-08-10-ux-taste.md` (Acceptance criteria are the gate).

**Architecture:** Content + tests. New: 3 knowledge files, 1 skill dir. Modified: uiux-engineer SKILL.md, delivery-loop/engineering-loop/LOOP.md wiring lines, THIRD-PARTY-NOTICES.md, docs counts.

## Global Constraints

- Spec sections 1–4 binding, including the Sources section's adaptation discipline: fetch real upstream text via `gh api "repos/<owner>/<repo>/contents/<path>" --jq .content | base64 -d`, distill (never paste wholesale), provenance line on every adapted file, unlicensed repos untouched.
- Provenance line format: `> Adapted from <repo(s)> (<license>, © <year> <author>). See THIRD-PARTY-NOTICES.md.` — get © year/name from each repo's LICENSE file, not guesses.
- The rule/taste split is binding language: objective = findings with severity; subjective = `TASTE (human call):` items, no severity, never blocking, never silently resolved.
- Design-system-first rule binding in both the persona and frontend-taste.
- Writing bar (`grep -P '[\x{00AD}\x{2018}\x{2019}\x{201C}\x{201D}]'`) on every new/changed doc; discover commands use full `meta/` names; commit style `type: subject` (no parens), terse, no trailer.
- Suite baseline 954 (`--ignore=tests/test_integration.py`); `ruff check src/` clean. Stage explicitly; never stage `.crucible/assertions/test-llm.yaml` or `CRUCIBLE_RESEARCH.md`.

---

### Task 1: Knowledge files + THIRD-PARTY-NOTICES

**Files:**
- Create: `src/crucible/knowledge/design-taste.md`, `src/crucible/knowledge/motion-interaction.md`, `src/crucible/knowledge/ux-writing.md`
- Modify: `THIRD-PARTY-NOTICES.md`
- Test: new `tests/test_ux_taste.py` — knowledge files load via the knowledge loader by name (find the loader's test pattern in existing tests); notices contains all three attribution markers (Leonxlnx MIT copyright line, Dragoon0x MIT copyright line, Anthropic Apache-2.0 marker + the string "Apache License")

**Sources to fetch (already verified accessible):**
- `repos/Leonxlnx/taste-skill/contents/skills/taste-skill/SKILL.md` (+ its LICENSE for the © line)
- `repos/Dragoon0x/taste-skills/contents/skills/perception/visual-audit/SKILL.md`, plus `skills/visual-language/{hierarchy-principles,spatial-rhythm,color-systems}/SKILL.md` and `skills/typography/type-systems/SKILL.md`, `skills/interaction/motion-design/SKILL.md` (+ LICENSE)
- `repos/anthropics/skills/contents/skills/frontend-design/SKILL.md` and its `LICENSE.txt` (full Apache text goes into notices)

**Binding content per file:** spec §1's bullet lists are the tables of contents. Each file: provenance line first, then rules phrased dual-use (citable by a reviewer, followable by a builder). The three AI-default cluster looks appear in design-taste.md as default-detection signals with their concrete descriptions.

- [ ] Fetch sources + licenses; write the three knowledge files; extend notices (Apache full text included).
- [ ] Tests; full suite + ruff; commit `feat: design taste knowledge + attributions`.

---

### Task 2: uiux-engineer upgrade + meta/frontend-taste

**Files:**
- Modify: `src/crucible/skills/uiux-engineer/SKILL.md` (keep existing mechanics sections; add per spec §2)
- Create: `src/crucible/skills/meta/frontend-taste/SKILL.md` + `triggers.yaml`
- Test: extend `tests/test_ux_taste.py` (content assertions per spec acceptance #2); `tests/test_trigger_router.py` (positive: "build a landing page for the club" fires frontend-taste; negative: "design the database schema" does not); bundled-count assertion 40 → 41 (tests/test_disclosure.py); `tests/test_packaging.py` pins for the new SKILL.md + triggers.yaml and the three knowledge files

**Binding details:** spec §2 and §3 in full — banned vague words verbatim (clean, nice, modern, sleek, beautiful, stunning, minimal, bold); critique output order intent → working → not working → single highest-impact change; `TASTE (human call):` heading exact; design-system-first in both files; frontend-taste Do-NOT boundary (not backend; never redesign untouched surfaces; never override an existing design system for taste; human wins taste disagreements); triggers conservative with anchored phrases (lesson of #18 — "design" alone must never fire it). uiux-engineer keeps its existing frontmatter shape (persona, not meta) — check `version:` bump and that its triggers.yaml (if any) still routes.

- [ ] Write both skills per binding details.
- [ ] Tests: RED at 40 → GREEN at 41; full suite + ruff; commit `feat: uiux taste upgrade + frontend-taste discipline`.

---

### Task 3: Wiring + sweep

**Files:**
- Modify: `src/crucible/skills/meta/delivery-loop/SKILL.md` (step-5 conditional UX gate sentence, per spec §4 — TASTE items go to the human unresolved), `src/crucible/skills/meta/engineering-loop/SKILL.md` + `docs/LOOP.md` (one gentle build-something-people-see sentence each), `CLAUDE.md` (one-liners + counts), `README.md`/`docs/FEATURES.md`/`docs/SKILLS.md`/`docs/KNOWLEDGE.md` (skills 41, knowledge 17 — locate every count)
- Test: extend `tests/test_ux_taste.py` (delivery-loop names the UX gate + uiux-engineer; content assertion)

- [ ] Wiring sentences + counts; tests.
- [ ] Sweep: `find src/crucible/skills -name SKILL.md | wc -l` = 41; knowledge file count check; wheel build + unzip grep (skill + 3 knowledge files); discover commands in changed docs exit 0; writing bar; full suite + ruff; commit `feat: ux gate wiring + docs counts`.
