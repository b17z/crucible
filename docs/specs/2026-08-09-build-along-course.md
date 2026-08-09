# Spec — Build-Along Course (piecewise course generation + kickoff prompt)

Version: 1.0 (2026-08-09). Approved via brainstorm. Stacks on the
engineering-loop branch (v2.1 track, no release this cycle).

## Goal

Add `meta/build-along-course`: a clean-room original skill that grows an
interactive HTML course alongside a project — one module per proven
milestone, starting from the spec itself — plus a generic
`docs/BUILD-ALONG.md` walkthrough ending in a copy-paste kickoff prompt
that bootstraps a fresh Claude Code session into building a new project
with crucible end to end.

## Decisions (from brainstorm)

1. Clean-room original. Inspired by the build-first-understand-later
   philosophy of Zara Zhang's codebase-to-course (github.com/zarazhangrui/
   codebase-to-course, unlicensed — default copyright). No code, CSS, JS,
   or prose from that repo is reused or opened during authoring. No
   THIRD-PARTY-NOTICES entry (an acknowledgment is not a license claim);
   the skill carries an inspiration line instead.
2. Polish bar v1: warm + minimal interactive. No animation engine.
3. Trigger: engineering-loop step 6 offers a module after each proven
   milestone; the skill is also directly invocable anytime.
4. Starter kit: generic guide + kickoff-prompt template in docs; the
   personal filled prompt is a chat deliverable, never committed.
5. Stacked on the engineering-loop branch; one continuous story.

## 1. The skill — `src/crucible/skills/meta/build-along-course/`

`SKILL.md` + `triggers.yaml` + `references/` in crucible v2 skill shape,
authored to `meta/writing-good-skills` standards. Provenance line:
`> Original to crucible. Inspired by the build-first-understand-later
philosophy of Zara Zhang's codebase-to-course; no code or text reused.`

### Behavior contract (binding)

- **Course home:** `course/` in the learner's project. Contents:
  `course.yaml` (manifest), `modules/NN-slug.html`, assets copied from
  references, assembled `index.html`.
- **Manifest `course.yaml`:** `title`, `accent` (one of the palette names
  documented in `base.html` comments), `modules:` list — each entry
  `id` (two-digit ordinal), `slug`, `title`, `milestone` (one plain
  sentence), `commit` (short SHA at module time; `none` for module 0),
  `date` (ISO). The manifest is the skill's memory: module numbering,
  which commits are already covered, and assembly order all come from it.
- **First use scaffolds:** create `course/`, copy `styles.css`,
  `course.js`, `footer.html`, `assemble.sh` verbatim (never regenerate);
  write `base.html` from the reference with exactly three substitutions —
  title, accent variables, nav dots. Write `course.yaml` with module 0.
- **Module 0 is the spec:** the first module teaches "what are we
  building and why" from the project's spec/PRD — the course starts
  before code exists. If no spec exists, the skill says so and points at
  `meta/brainstorming` + `crucible prewrite` instead of inventing one.
- **On invocation** (after a milestone): read the manifest, diff the repo
  since the last module's recorded commit (`git diff <commit>..HEAD`
  scope, not the whole codebase), write ONE module teaching what that
  milestone built, append the manifest entry, add the module's nav dot
  to the scaffolded `course/base.html`, run `assemble.sh`.
- **Module content contract:** opens with why-should-I-care in plain
  language; at least one code↔plain-English side-by-side block using real
  snippets from the learner's repo (verbatim, with file paths); one quiz
  (check/reveal); one aha-callout; glossary tooltips on first-use
  technical terms; a fresh metaphor per module, never reused across the
  course (the manifest's module titles are the check).
- **Audience:** assume zero technical background. No jargon without a
  tooltip. The learner reads code; they do not write it.
- **Vault integration:** resolve a vault exactly as `meta/teach-me` does
  (`.crucible/teach.yaml` `vault:` → `~/.claude/crucible/teach.yaml` →
  none). Vault set → write/update ONE markdown course-index note at
  `<vault>/crucible-learning/<project-slug>/COURSE.md` (project-slug =
  the project directory name, slugified) listing modules
  (title, milestone, date) and linking to `course/index.html`. The HTML
  course itself always stays project-side — HTML doesn't belong in a
  vault. No vault → skip the note silently.
- **Do-NOT boundary:** never generate more than one module per
  invocation; never rewrite existing modules unless asked; never touch
  `styles.css`/`course.js` after scaffold; never block anything — the
  course is invited, not enforced.

### Triggers (`triggers.yaml`)

Match: "course module", "build-along course", "add this to the course",
"turn this into a course as we build", "teach me how this works as we
build". User-invocable via `crucible skills discover
meta/build-along-course`.

## 2. Reference assets (clean-room, binding)

All original files under the skill's `references/`:

- **`styles.css`** — warm paper-tone background, one accent through CSS
  custom properties, alternating module background tones (even/odd),
  dark IDE-style code blocks, generous whitespace, responsive.
  **System font stack only; the assembled page makes zero external
  requests** (no CDN fonts, no remote images, no fetch).
- **`course.js`** — progress nav dots (scroll-spy + click), quiz
  check/reveal, glossary tooltips (CSS-first, keyboard-accessible:
  focusable trigger, visible on focus). No animation engine. Vanilla JS,
  no dependencies.
- **`base.html`** — document shell with `COURSE_TITLE`, accent-variable
  block, and `NAV_DOTS` placeholders; palette options documented in
  comments. **`footer.html`** — closing shell.
- **`module-template.html`** — one semantic `<section class="module">`
  skeleton showing each contract element (translation block, quiz,
  callout, tooltip markup) with placeholder content clearly marked.
- **`assemble.sh`** — /bin/bash 3.2-safe: concatenates `base.html` +
  `modules/*.html` (lexicographic, which the two-digit ids make
  chronological) + `footer.html` → `index.html`. Fails loudly (non-zero,
  message) if `base.html` or `footer.html` is missing or `modules/` is
  empty; never edits module files.
- **`content-guide.md`** — the module content contract and audience
  rules in prose, read by the writing agent at module time; includes the
  metaphor-freshness rule and quiz guidance (test application, not
  recall).

## 3. Loop wiring

- `meta/engineering-loop` SKILL.md step 6 ("keep what you learned")
  gains the course offer alongside the learning record: one sentence +
  cross-ref to `meta/build-along-course`. `docs/LOOP.md` step 6 gains
  the matching sentence. No other bundled skill changes.

## 4. docs/BUILD-ALONG.md + kickoff prompt

Generic, public, no personal content:

- Start-to-finish walkthrough for starting a NEW project with crucible:
  install from GitHub (`pip install git+https://github.com/b17z/
  crucible.git` — not on PyPI), `crucible init --with-claudemd`,
  `crucible hooks claudecode init`, optional vault via
  `.crucible/teach.yaml`, then the engineering loop with a course module
  per milestone. Every command copy-pasteable; discover commands use
  full `meta/` names.
- Worked example: a genericized "personal knowledge base in an Obsidian
  vault" project (spec → vault skeleton → parser → board → automation),
  no names, no personal details.
- Ends with a **Kickoff Prompt template**: one fenced block a user
  copies into a fresh Claude Code session, with `<placeholders>` for
  project name, spec file location, and vault path. The prompt instructs
  the agent to: install crucible + hooks, read the spec file, run
  `crucible prewrite review` on it, then follow `meta/engineering-loop`
  piecewise from the spec's own staged scope — spec becomes course
  module 0, one module offered per completed stage. It also tells the
  agent what NOT to do (no building past the spec's v1 scope, no
  skipping the loop's prove-it step).
- Linked from README's docs list and the `crucible init` output line
  that already points at LOOP.md (extend that line, don't add a second).

## 5. The personal kickoff prompt (chat deliverable)

After this branch merges to main (the prompt installs crucible from
GitHub main, so merge order matters), fill the template for the AI Value
Chain KB project: her spec PDF saved into her repo, her repo-as-vault
teach.yaml, her spec's v1 scope (hand-seeded vault skeleton) as the
first loop pass and its "Sequencing after v1" stages as later milestones.
Delivered in chat only. Never committed, no name, no spec contents in
the repo.

## Acceptance criteria

1. `crucible skills discover` lists 39 bundled skills; the new
   triggers.yaml loads clean; trigger-router tests extended with one
   match case for the new skill.
2. Shell test for `assemble.sh` under `RUNNER=/bin/bash`: fixture course
   with base/footer + two modules assembles in order with both modules
   present; missing footer and empty modules/ each fail non-zero.
3. Content assertions on SKILL.md: provenance line present; vault-note
   cascade documented with the exact order; never-regenerate rule;
   zero-external-requests rule. Assertion that `styles.css` and
   `base.html` contain no `http://`/`https://` URLs.
4. Wheel pins: SKILL.md + all seven reference files ship in the wheel
   (packaging test extended); docs counts say 39 everywhere the bundled
   count appears (README, CLAUDE.md, FEATURES, SKILLS.md); full suite
   green at the branch baseline (888) + new tests.
5. BUILD-ALONG.md exists, linked from README + init output; every
   printed command in it verified runnable (discover commands exit 0).

## Non-goals

- **Not building the AI Value Chain KB.** No code, pages, or vault
  content for the PDF spec's project — her agent builds it; we ship the
  tooling and the prompt.
- No animation engine, no data-flow/chat visualizations (later pass).
- No CLI surface (`crucible course …` does not exist).
- No adaptation of codebase-to-course content in any form.
- No release/tag this cycle.
