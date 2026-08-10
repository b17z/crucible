# Spec — Delivery Loop (professional cycle + notetaker genericization + portability)

Version: 1.0 (2026-08-10). Approved via brainstorm. v2.1 track, no
release this cycle.

## Goal

Add `meta/delivery-loop`: the professional counterpart to
`meta/engineering-loop` — spec-first, independently reviewed,
ledgered, git/CI-agnostic, with process artifacts kept out of the
repo. Plus: genericize every Obsidian-vault reference to a
notes-folder concept (key unchanged), and document harness/model
portability in `docs/PORTABILITY.md`.

## Decisions (from brainstorm)

1. Operationalize the-loop-at-scale as a new skill, with two work
   caveats binding: (a) in-between artifacts (specs, plans, ledgers,
   decision logs) are never committed to the repo — they live in a
   per-project workbench outside it; (b) the loop is agnostic about
   git/CI/merge process — it ends at "verified and handed off".
2. New sibling skill `meta/delivery-loop`; engineering-loop and
   delivery-loop cross-reference as on-ramp/off-ramp.
3. `teach.yaml` keeps the `vault:` key; prose genericizes to "notes
   folder" with Obsidian as an example, not a requirement.
4. Portability doc covers: Claude Code (any model behind it,
   gateways included) = full auto-activation; Codex / Gemini CLI /
   pi / Cursor = AGENTS.md-read, CLI-driven, no auto-fire; `--llm`
   is the only Anthropic-API-specific feature.

## 1. The skill — `src/crucible/skills/meta/delivery-loop/`

`SKILL.md` + `triggers.yaml`, crucible v2 shape, authored to
`meta/writing-good-skills` standards. Original to crucible (no
provenance line needed; no notices entry). Audience: working
engineers — professional register, no beginner metaphors.

### The seven steps (binding, each naming its carrier skill)

1. **Frame it** (`meta/wait-what` register) — one paragraph:
   problem, success criteria, constraints. No solution talk yet.
2. **Design under challenge** (`meta/brainstorming`, then
   `meta/challenge`) — options with tradeoffs; the chosen design
   pressure-tested; decisions recorded with the why.
3. **Spec it** (`meta/spec-validator`) — binding spec; run
   `crucible prewrite review <spec-path>` and address findings
   before any code.
4. **Plan the execution** — tasks with binding details (exact
   values, interfaces) and per-task verification steps.
5. **Execute with gates** — one task at a time, solo or with
   subagents; after each task an independent review pass
   (`crucible review` plus relevant persona skills, or a second
   agent) — the author never grades their own homework; every
   completion appended to the ledger before moving on.
6. **Prove and close** (`meta/but-for-real`) — run the project's
   full checks, take one skeptical pass over the whole change, do
   ONE fix wave, then hand off per the team's process. The loop
   mandates verification, not integration: no branch strategy,
   merge command, or CI shape is assumed or prescribed.
7. **Keep the learning** (`meta/teach-me`) — learning record +
   decision log to the notes folder.

When running step 5 with subagents, the skill points at
`meta/engineering-loop`'s `knowledge/the-loop-at-scale.md` (via
`crucible skills discover meta/engineering-loop`) rather than
duplicating it.

### The workbench (binding)

All in-between artifacts — spec, plan, ledger, decision log — live
in a per-project workbench, never committed to the repo. Resolution
order, checked before the first artifact is written:

1. `workbench:` key in `.crucible/teach.yaml` (project), then
   `~/.claude/crucible/teach.yaml` (user) — an explicit directory,
   e.g. an in-house notetaker's project folder;
2. else `vault:` set (same cascade) → `<vault>/crucible-work/
   <project-slug>/` (project-slug = project directory name,
   slugified);
3. else fallback `.crucible/workbench/` — and the skill instructs
   verifying it is gitignored before writing (add the ignore line if
   missing).

Artifact names inside the workbench: `spec.md`, `plan.md`,
`ledger.md`, `decisions.md`. The ledger is append-only during a
project; the skill instructs recovery from ledger + VCS history
after any context loss.

### Do-NOT boundary

Never commit workbench artifacts; never prescribe branch/merge/CI
mechanics; never skip the independent review because the change
"looks small"; never start step 5 before the spec passed prewrite
review. Not for beginners — point them at `meta/engineering-loop`.

### Triggers (`triggers.yaml`)

Conservative, invocation-leaning (lesson of issue #18): "delivery
loop", "delivery-loop", "professional loop", "work loop",
"production loop". User-invocable via
`crucible skills discover meta/delivery-loop`.

## 2. Notetaker genericization (prose only; `vault:` key unchanged)

Replace Obsidian-as-requirement with notes-folder-as-concept in:

- `meta/teach-me/SKILL.md`, `meta/build-along-course/SKILL.md`
  (vault sections), `docs/BUILD-ALONG.md`, `docs/LOOP.md`,
  `CLAUDE.md` one-liners, `src/crucible/templates/CLAUDE.md` if it
  mentions vaults.
- House phrasing (adapt per sentence, this is the register): "your
  notes folder — any tool that reads markdown from a directory
  (Obsidian, Logseq, an in-house notetaker)".
- Obsidian may remain as an example everywhere; no sentence may
  *require* Obsidian. The `vault:` key, cascade order, and all paths
  are unchanged; existing teach-me/build-along content assertions
  must still pass.

## 3. docs/PORTABILITY.md

Compact, linked from README's docs list:

- **The contract**: an agent with shell access + a place to put
  project instructions. Skills are markdown; the CLI is the API;
  git is used by review modes but `--no-git` paths exist.
- **The matrix**: Claude Code (any model backend, gateways
  included) → hooks fire, trigger routing, session injection,
  enforcement gates — full auto-activation. Codex / Gemini CLI /
  pi / Cursor → AGENTS.md is read; skills are discovered and run
  via CLI on instruction; no auto-fire, so AGENTS.md must say to
  run `crucible skills discover` at session start.
- **Models**: nothing in the loop is model-specific; the only
  Anthropic-API-bound feature is the opt-in `--llm` assertion tier.
- Generated `src/crucible/templates/CLAUDE.md` gains one sentence:
  harnesses that don't run hooks should run
  `crucible skills discover` at session start.

## 4. Wiring

- `meta/engineering-loop` SKILL.md + `docs/LOOP.md`: one sentence
  each — when the work is professional, step up to
  `meta/delivery-loop`.
- `meta/delivery-loop` SKILL.md points down for beginners.
- CLAUDE.md (repo) bundled-skills one-liner; README docs list gains
  PORTABILITY.md; bundled count 39 → 40 everywhere it appears.

## Acceptance criteria

1. `crucible skills discover` lists 40; delivery-loop triggers load
   clean; one positive trigger-router match case; a negative case
   proving a plain debugging prompt does not fire it.
2. Content assertions on delivery-loop SKILL.md: workbench cascade
   documented in the exact order above; never-commit rule; the
   handoff sentence contains no git command; prewrite-review gate
   before execution.
3. `docs/PORTABILITY.md` exists, linked from README; generated
   CLAUDE.md template contains the non-hook-harness sentence
   (pinned in tests/test_cli.py alongside the MCP-optional test).
4. Genericization: `docs/BUILD-ALONG.md`, `docs/LOOP.md`, and both
   vault-aware SKILL.mds contain the notes-folder phrasing; existing
   teach-me/build-along cascade and content assertions still pass;
   `vault:` remains the config key everywhere.
5. Wheel ships the new skill dir; docs counts say 40; full suite
   green at 911 baseline + new tests.

## Non-goals

- No code that parses `teach.yaml` (workbench stays
  SKILL.md-instructed, like the vault).
- No CI templates, no git workflow tooling, no per-harness hook
  ports (portability is documented, not implemented).
- No renaming of `vault:`; no changes to engineering-loop's six
  steps; no release/tag.
