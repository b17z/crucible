# Spec — The Engineering Loop (skill fold-in + beginner loop)

Version: 1.0 (2026-08-09). Approved via brainstorm. Post-2.0 feature work
(v2.1 track, no release this cycle).

## Goal

Bundle five adapted third-party skills that fill crucible's think/debug/
prove/translate/learn gaps, add a beginner-facing `meta/engineering-loop`
skill that ties them into a plain-language cycle, and document the loop for
new users — with full MIT attribution for the sources.

## Decisions (from brainstorm)

1. Fold in all five: `brainstorming` + `systematic-debugging` (from
   obra/superpowers, MIT © 2025 Jesse Vincent), `tdd` + `wait-what` +
   `teach` (from mattpocock/skills, MIT © 2026 Matt Pocock).
2. `teach-me` gets Obsidian wiring via a configurable vault path with
   workspace fallback (upstream behavior preserved when unset).
3. Loop ships as bundled skill (`meta/engineering-loop`) + `docs/LOOP.md`.

## 1. Adapted skills — `src/crucible/skills/meta/<name>/`

Each in crucible v2 skill shape: `SKILL.md` (+ `triggers.yaml`, +
`knowledge/` where noted), authored to `meta/writing-good-skills` standards
(description-as-trigger with "Use when X", Do-NOT boundaries, no
placeholder text). Each SKILL.md starts with a provenance line:
`> Adapted from <repo> (MIT, © <year> <author>). See THIRD-PARTY-NOTICES.md.`

- **`meta/brainstorming`** — from superpowers `skills/brainstorming`.
  Keep: the hard gate (no implementation before a presented, approved
  design), one-question-at-a-time, YAGNI, section-by-section design
  presentation, spec self-review. Strip: superpowers plugin cross-refs,
  visual-companion section, platform-adaptation table, superpowers file
  paths. Trigger: creating/building/adding features or "let's build".
- **`meta/systematic-debugging`** — from superpowers
  `skills/systematic-debugging`. Keep the phased root-cause discipline and
  its rationalization table. Strip plugin cross-refs. Trigger: bug/broken/
  failing/unexpected behavior, before proposing fixes.
- **`meta/tdd`** — from mattpocock `skills/engineering/tdd`. Red-green-
  refactor loop. Trigger: implementing features/fixes test-first.
- **`meta/wait-what`** — from mattpocock `skills/productivity/wait-what`.
  Re-pitch unclear messages in plain English. Trigger: user confusion
  signals ("wait what", "I don't understand", "explain that simply").
- **`meta/teach-me`** — from mattpocock `skills/productivity/teach` plus
  its four FORMAT reference files (MISSION, LEARNING-RECORD, RESOURCES,
  GLOSSARY) as `knowledge/` files. Adaptation — vault resolution, checked
  in this order before any workspace file is written:
  1. `.crucible/teach.yaml` `vault:` key (project), then
     `~/.claude/crucible/teach.yaml` (user);
  2. vault set → MISSION.md, learning-records/, RESOURCES.md, NOTES.md
     live under `<vault>/crucible-learning/<topic-slug>/` (lessons/ and
     assets/ stay in the workspace — HTML doesn't belong in a vault);
  3. unset → pure upstream workspace behavior, AND on first use the skill
     asks once whether to save learning to an Obsidian vault, offering to
     write the config.
  Trigger: "teach me", "I want to learn", user-invocable.

## 2. `meta/engineering-loop` — the beginner cycle

New original skill (no upstream). Plain, jargon-free language addressed to
someone who has never shipped software. The cycle, each step naming the
bundled skill that carries it (by namespaced path, activation via
`crucible skills discover <name>`):

1. Say it plainly (`meta/wait-what`) — one sentence a friend would get.
2. Think small first (`meta/brainstorming`) — smallest version that could
   work; what could go wrong.
3. Write it down (`meta/spec-validator`) — 3–5 sentences is a spec.
4. Build the smallest thing (`meta/coding-discipline`) — one step, not the
   whole dream.
5. Prove it honestly (`meta/tdd`, then `meta/but-for-real`) — a check
   before you trust it; a skeptical pass before "done".
6. Keep what you learned (`meta/teach-me`) — one learning record per
   session; beginners compound.

Includes a "when to break the loop" note (tiny experiments skip steps 3-5;
`crucible-mode: exploration` exists) so it teaches judgment, not ritual.
Triggers: "I'm new", "first project", "where do I start", "help me build my
first", plus user-invocable.

## 3. Attribution

- Root `THIRD-PARTY-NOTICES.md`: full MIT license text for
  obra/superpowers (© 2025 Jesse Vincent) and mattpocock/skills
  (© 2026 Matt Pocock), each with the list of adapted skills and source
  URLs; plus the existing Karpathy-skills attribution
  (multica-ai/andrej-karpathy-skills) migrated here from prose.
- CLAUDE.md bundled-skills section gains the provenance one-liners.

## 4. docs/LOOP.md

Plain-language quickstart: what the loop is, the six steps with one worked
non-technical example (e.g. "a page that shows my running club's next
meetup") walked through each step, how to invoke each skill, and the vault
setup for teach-me. Linked from README's docs list and `crucible init`
output (one line added).

## Acceptance criteria

1. `crucible skills discover` lists 38 bundled skills (32 + 6); all six new
   triggers.yaml files load without validator/router errors (existing
   trigger-router tests extended with one match case per new skill).
2. `meta/teach-me` vault resolution covered by tests at the doc/contract
   level: SKILL.md instructs the cascade order above verbatim (content
   assertions), and `.crucible/teach.yaml` parsing has a unit test if any
   python touches it (if the vault logic lives purely in SKILL.md
   instructions, the test asserts the SKILL.md documents the exact cascade).
3. `THIRD-PARTY-NOTICES.md` exists with both full MIT texts (asserted by
   test: file exists, contains both copyright lines); wheel pin test
   extended with the six new skill dirs' SKILL.md paths.
4. Docs counts updated honestly everywhere the bundled-skill count appears
   (README, CLAUDE.md, FEATURES, SKILLS.md); full suite green at the
   873-pass baseline + new tests; wheel + fresh-clone sweep at branch end.

## Non-goals

No new hooks or config surfaces beyond teach.yaml; no changes to existing
bundled skills; no release/tag this cycle; no vendoring of superpowers
process skills crucible already relies on via the plugin (executing-plans,
subagent-driven-development, etc. stay plugin-side).
