# Build-Along Course Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `meta/build-along-course` (clean-room piecewise course skill + reference assets), loop wiring, and `docs/BUILD-ALONG.md` with the kickoff-prompt template, per `docs/specs/2026-08-09-build-along-course.md` (its Acceptance criteria are the gate).

**Architecture:** Pure content + tests: one new skill dir with seven reference assets, two edited docs surfaces, one new doc. No python-surface or hook changes.

## Global Constraints

- Spec sections 1–4 are binding: behavior contract, manifest schema, asset list, module content contract, vault-note rule, Do-NOT boundary.
- **Clean-room discipline:** never fetch, open, or quote anything from github.com/zarazhangrui/codebase-to-course. All CSS/JS/HTML/prose written from scratch. Provenance line verbatim from spec §1.
- `styles.css` and `base.html` contain no `http://`/`https://` URLs; system font stack only; assembled page makes zero external requests.
- `assemble.sh` is /bin/bash 3.2-safe (no mapfile, no `**`, guarded expansions).
- Every SKILL.md meets `meta/writing-good-skills`; discover commands in docs always use full `meta/` names; commit style `type: subject` (no parens), terse body, no trailer.
- Suite baseline 888 (`--ignore=tests/test_integration.py`) + new tests; ruff clean.
- Stage explicitly; never stage `.crucible/assertions/test-llm.yaml` or `CRUCIBLE_RESEARCH.md`.

---

### Task 1: The skill + reference assets + tests

**Files:**
- Create: `src/crucible/skills/meta/build-along-course/SKILL.md`, `triggers.yaml`, and `references/{styles.css,course.js,base.html,footer.html,module-template.html,assemble.sh,content-guide.md}`
- Test: extend `tests/test_trigger_router.py` (one positive match case); bump the bundled-count assertion 38 → 39 (locate the existing `38`); extend `tests/test_packaging.py` BUNDLED with the SKILL.md + all seven reference paths; new `tests/test_build_along_course.py`

**Binding details (from spec §1–2):**
- SKILL.md documents, in this order: provenance line; audience; scaffold-on-first-use (copy `styles.css`, `course.js`, `footer.html`, `assemble.sh` verbatim — never regenerate; write `base.html` with exactly three substitutions: title, accent variables, nav dots); manifest schema with this example:

```yaml
title: "How My Project Works"
accent: coral
modules:
  - id: "00"
    slug: what-we-are-building
    title: "What we're building and why"
    milestone: "The spec exists"
    commit: none
    date: 2026-08-09
```

- Module 0 = the spec (no spec → point at `meta/brainstorming` + `crucible prewrite`, do not invent one); on invocation: read manifest → diff since last recorded commit → write ONE module → append manifest entry → add nav dot to `course/base.html` → run `assemble.sh`.
- Module content contract: why-should-I-care opening; ≥1 code↔plain-English block with verbatim repo snippets + file paths; 1 quiz; 1 aha-callout; glossary tooltips on first-use terms; fresh metaphor per module (manifest titles are the check).
- Vault: resolve exactly as `meta/teach-me` (`.crucible/teach.yaml` `vault:` → `~/.claude/crucible/teach.yaml` → none); vault set → ONE note at `<vault>/crucible-learning/<project-slug>/COURSE.md` (project-slug = project directory name, slugified) listing modules + linking `course/index.html`; HTML always stays project-side; no vault → skip silently.
- Do-NOT: one module per invocation; no rewrites unless asked; never touch styles/js post-scaffold; never block.
- `triggers.yaml` match phrases: "course module", "build-along course", "add this to the course", "turn this into a course as we build", "teach me how this works as we build". Copy the shape from an existing `src/crucible/skills/meta/*/triggers.yaml`.
- `assemble.sh`: concatenate `base.html` + `modules/*.html` (lexicographic) + `footer.html` → `index.html`; missing base/footer or empty `modules/` → non-zero exit with a message; never edits module files.
- `course.js`: scroll-spy nav dots + click-to-scroll; quiz check/reveal; tooltips visible on hover AND focus. Vanilla, no dependencies.
- `module-template.html`: one `<section class="module" id="module-NN">` skeleton demonstrating every contract element with clearly-marked placeholder content.

**`tests/test_build_along_course.py` must cover:**
- Content assertions on SKILL.md: provenance line present verbatim; cascade order documented (`.crucible/teach.yaml` before `~/.claude/crucible/teach.yaml`); "never regenerate" rule; zero-external-requests rule.
- `styles.css` and `base.html` contain neither `http://` nor `https://`.
- `assemble.sh` via `subprocess` with `/bin/bash`: tmp fixture (base + footer + two modules `01-a.html`, `02-b.html`) → `index.html` contains both module markers in order, base content first, footer last; missing `footer.html` → returncode != 0; empty `modules/` → returncode != 0.

- [ ] Write SKILL.md + triggers.yaml + all seven references per the binding details.
- [ ] Extend router/count/packaging tests; write `tests/test_build_along_course.py`; RED where count was 38 → GREEN at 39.
- [ ] Full suite + ruff; commit `feat: build-along-course skill + reference assets`.

---

### Task 2: Loop wiring + BUILD-ALONG.md

**Files:**
- Modify: `src/crucible/skills/meta/engineering-loop/SKILL.md` (step 6), `docs/LOOP.md` (step 6), `README.md` (docs list), `src/crucible/cli.py` (extend the existing init line that points at LOOP.md — do not add a second line)
- Create: `docs/BUILD-ALONG.md`
- Test: extend `tests/test_build_along_course.py` (BUILD-ALONG.md exists; contains the kickoff fenced block; every `crucible skills discover` command in it uses `meta/` prefix)

**Binding details (from spec §3–4):**
- Step 6 wiring: ONE sentence + cross-ref to `meta/build-along-course` in each of engineering-loop SKILL.md and LOOP.md ("keep what you learned" now = learning record + optional course module).
- BUILD-ALONG.md structure: (1) what build-along means (course grows with the project, module 0 = the spec); (2) setup: `pip install "crucible @ git+https://github.com/b17z/crucible.git"` (verify the exact install form works in Task 3 — if plain `pip install git+…` is what works, use that), `crucible init --with-claudemd`, `crucible hooks claudecode init`, optional `.crucible/teach.yaml` vault; (3) the loop with a course module per milestone, discover commands with `meta/` names; (4) genericized worked example: personal knowledge base in an Obsidian vault (spec → vault skeleton → parser → board → automation) — no names, no personal details; (5) the Kickoff Prompt template.
- Kickoff Prompt template: one fenced block with `<PROJECT-NAME>`, `<SPEC-FILE>`, `<VAULT-PATH>` placeholders. It must instruct the receiving agent to: install crucible from GitHub + run both init commands; read `<SPEC-FILE>`; run `crucible prewrite review <SPEC-FILE>`; follow `meta/engineering-loop` starting from the spec's own v1 scope, one milestone at a time; create course module 0 from the spec via `meta/build-along-course` and offer a module per completed milestone; write teach-me learning records to `<VAULT-PATH>`; NOT build past the spec's v1 scope; NOT skip the prove-it step.
- README: one line in the docs list. cli.py: extend the existing LOOP.md pointer line to mention BUILD-ALONG.md (GitHub URL form, same as the LOOP.md URL fix).

- [ ] Write BUILD-ALONG.md; wire step 6 in both files; README + cli.py lines.
- [ ] Extend tests; full suite + ruff; commit `feat: loop wiring + BUILD-ALONG guide`.

---

### Task 3: Sweep

- [ ] Docs counts: every bundled-skill count says 39 (README, CLAUDE.md, docs/FEATURES.md, docs/SKILLS.md); verify with `find src/crucible/skills -name SKILL.md | wc -l`.
- [ ] Verify every printed command in BUILD-ALONG.md and the new SKILL.md: each `crucible skills discover meta/...` exits 0; the pip install form is syntactically valid (`pip install --dry-run` acceptable; no live install of the remote needed).
- [ ] Wheel build + unzip grep for `build-along-course` SKILL.md and all seven references.
- [ ] Full suite + ruff; commit `test: pin build-along-course bundle + docs counts` (only if changes needed); report numbers.
