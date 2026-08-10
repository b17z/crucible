---
name: build-along-course
description: 'Use when someone wants a running interactive HTML course grown alongside their project — "course module", "build-along course", "add this to the course", "turn this into a course as we build", "teach me how this works as we build" — plus after a proven milestone in meta/engineering-loop step 6. Scaffolds course/ on first use, then writes exactly ONE module per invocation covering the diff since the last recorded commit — why-should-I-care opening, a real code-to-plain-English block, one quiz, one aha-callout, glossary tooltips, a fresh metaphor. Do NOT use to rewrite or restyle existing modules (ask first), to build more than one module in a single invocation, or as a general documentation/README generator — this is a taught-alongside course for a zero-technical-background learner, not project docs.'
version: "1.0"
---

> Original to crucible. Inspired by the build-first-understand-later
> philosophy of Zara Zhang's codebase-to-course; no code or text reused.

# Build-Along Course

The learner is building a real project, one milestone at a time. This
skill grows an interactive HTML course next to it — one module per
proven milestone, starting from the spec itself, so the course exists
before the first line of code does.

## Audience

Assume zero technical background. The learner reads the code that gets
built; they do not write it. No jargon without a glossary tooltip on
its first use anywhere in the course. See `references/content-guide.md`
for the full audience and content rules before writing any module.

## Scaffold on first use

The first time this skill runs in a project with no `course/`
directory, create it and populate it from `references/`. The assembled
course makes zero external requests — no CDN fonts, no remote images,
no fetch calls — the whole point of the system font stack and inlined
styles is that the course works offline, from a `file://` URL, forever:

- **Copy verbatim, never regenerate:** `styles.css`, `course.js`,
  `footer.html`, `assemble.sh`. These four ship byte-for-byte from the
  skill into `course/`. Never hand-edit a scaffolded copy and never
  rewrite one from the skill's version on a later invocation — if the
  reference assets need to change, that's a skill update, not a
  per-project regeneration.
- **Write `base.html` with exactly three substitutions**, using
  `references/base.html` as the source: the `COURSE_TITLE` placeholder
  (twice — `<title>` and the header `<h1>`), the accent `<style>` block
  (fill in the three CSS custom properties for the palette named in
  `course.yaml`'s `accent:` field — options are documented as comments
  at the top of `references/base.html`), and `NAV_DOTS` (one `<li>` per
  module, in module order — starts with just module 0's dot). Each nav
  dot is exactly this shape:
  `<li><a href="#module-NN">Module title</a></li>` — course.js keys off
  `.nav-dots a` for click-to-scroll and scroll-spy, so the anchor is
  required, not just an `<li>` of text.
- **Write `course.yaml`** with the module 0 entry (see manifest schema
  below).

`content-guide.md` and `module-template.html` stay in the skill's
`references/` — they are reading material for the agent at
module-writing time, not files that get copied into the project.

## Manifest schema (`course/course.yaml`)

The manifest is the skill's memory: module numbering, which commits are
already covered, and assembly order all come from it.

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

- `id` — two-digit ordinal string. `00` is always the spec module.
- `slug` — dash-case, used in the module's filename
  (`course/modules/<id>-<slug>.html`).
- `title` — plain language, becomes the link text in a
  `<li><a href="#module-NN">Module title</a></li>` nav dot and the
  freshness check for metaphors (see content-guide.md).
- `milestone` — one plain sentence describing what got proven.
- `commit` — short SHA of the commit this module covers; `none` for
  module 0 (there's no commit yet — it teaches the spec).
- `date` — ISO 8601.

## Module 0 is the spec

The first module teaches "what are we building and why" from the
project's spec or PRD — the course starts before code exists. If no
spec exists yet, say so and point the learner at `meta/brainstorming`
and `crucible prewrite` to write one. **Never invent a spec** to fill
this module.

## On invocation (after module 0 exists)

Each invocation writes exactly ONE module, covering the milestone just
proven:

1. Read `course/course.yaml` for the last recorded module's `commit`.
2. Diff the repo since that commit — `git diff <last-commit>..HEAD` —
   to see only what this milestone changed. This is the scope for the
   new module; do not survey the whole codebase.
3. Write the module content to
   `course/modules/<next-id>-<slug>.html`, following the contract in
   `references/content-guide.md` and the shape in
   `references/module-template.html`.
4. Append the new entry to `course/course.yaml`'s `modules:` list.
5. Add the new module's nav dot to `course/base.html`:
   `<li><a href="#module-NN">Module title</a></li>`.
6. Run `bash course/assemble.sh course` (or `cd course && ./assemble.sh`)
   to rebuild `index.html`.

## Module content contract

Every module needs all of: a why-should-I-care opening in plain
language before any code appears; at least one code-to-plain-English
block using a real, verbatim snippet from the learner's repo with its
file path; one quiz (check/reveal, testing application not recall);
one aha-callout; glossary tooltips on first-use technical terms; and a
fresh metaphor not reused from an earlier module (the manifest's module
titles are the check — if two titles would need the same metaphor,
reconsider the split). Full detail and judgment calls:
`references/content-guide.md`.

## Vault integration

Resolve a vault exactly as `meta/teach-me` does, in this exact order:

1. `.crucible/teach.yaml` in the project, `vault:` key.
2. `~/.claude/crucible/teach.yaml`, `vault:` key.
3. If neither sets one: no vault. Skip the note below silently.

If a vault is set: write or update ONE markdown note at
`<vault>/crucible-learning/<project-slug>/COURSE.md` (project-slug is
the project's directory name, slugified) listing every module (title,
milestone, date) and linking to `course/index.html`. The vault is your
notes folder — any tool that reads markdown from a directory
(Obsidian, Logseq, an in-house notetaker). The HTML course itself
always stays project-side — HTML doesn't belong in a notes folder,
regardless of vault configuration.

## Do NOT

- Generate more than one module per invocation.
- Rewrite an existing module unless the learner explicitly asks.
- Touch `styles.css` or `course.js` after the initial scaffold.
- Block anything. The course is invited, not enforced — if the learner
  doesn't want a module this time, that's fine.

## Related

- `references/content-guide.md` — full module content contract and
  audience rules, read at module-writing time.
- `references/module-template.html` — the module skeleton with every
  contract element marked, filled in and saved as
  `course/modules/NN-slug.html`.
- `references/base.html`, `references/footer.html`,
  `references/styles.css`, `references/course.js`,
  `references/assemble.sh` — copied/adapted into `course/` at scaffold
  (see "Scaffold on first use" above for exactly what's copied verbatim
  vs. substituted).
- `meta/teach-me` — the vault-resolution cascade this skill mirrors.
- `meta/engineering-loop` — step 6 offers this skill after a proven
  milestone.
- `meta/brainstorming`, `crucible prewrite` — where to send a learner
  with no spec yet, instead of inventing one for module 0.
