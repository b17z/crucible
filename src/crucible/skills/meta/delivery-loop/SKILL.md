---
name: delivery-loop
description: Use when an experienced engineer is running a real piece of delivery work — a feature, a fix, a migration — end to end, or explicitly asks for "the delivery loop", "the professional loop", "the work loop", or "the production loop". Walks seven steps from framing through handoff, each naming the Crucible skill that carries it, with in-between artifacts (spec, plan, ledger, decision log) kept in a per-project workbench outside the repo. Do NOT use for someone who has never shipped software before (route them to `meta/engineering-loop`) or for a single narrow ask that only needs one skill directly (route to that skill instead of wrapping it in the whole loop).
version: "1.0"
---

# The Delivery Loop

Seven steps, on repeat, for a working engineer taking a real piece of
delivery work from framing to a verified, handed-off result. Each step
names the Crucible skill that does the work — this skill is the map,
not a replacement for any of them.

New to shipping software, or not sure how the pieces fit together yet?
This loop assumes you already know how to code and just want the
professional cycle named. Start at `meta/engineering-loop` instead —
the six-step, plain-language on-ramp this loop steps up from.

## The seven steps

### 1. Frame it

One paragraph: the problem, the success criteria, the constraints. No
solution talk yet — naming the fix before the problem is understood is
the fastest way to build the wrong thing carefully. If the framing
doesn't hold together, or you catch yourself or the agent restating
jargon instead of explaining it, that's `meta/wait-what` — re-pitch it
in plain language before moving on. `crucible skills discover
meta/wait-what`.

### 2. Design under challenge

Lay out options with real tradeoffs, pick one, and pressure-test the
choice before committing code to it. `meta/brainstorming` runs the
one-question-at-a-time design dialogue and gates implementation behind
an approved plan (`crucible skills discover meta/brainstorming`); once
a design exists, `meta/challenge` pressure-tests it as a skeptical
reviewer demanding evidence and tradeoffs, not agreement (`crucible
skills discover meta/challenge`). Record decisions with the reasoning
behind them, not just the outcome — future you (or the next agent)
needs the why, not only the what.

### 3. Spec it

Turn the approved design into a binding spec — exact values, exact
interfaces, no room for the next step to improvise the parts that
matter. Run `crucible prewrite review <spec-path>` and address every
finding before any code gets written. `meta/spec-validator` is the
skill that gates this — it's why the loop stops and asks "is there a
spec, and has it passed prewrite review?" instead of proceeding on
vibes. `crucible skills discover meta/spec-validator`.

Prewrite review's semantic assertions need an Anthropic API key to
run. The CLI exits 1 when nothing was evaluated, so a key-not-found
run won't read as a pass — but the exit code alone doesn't tell you
*why* nothing ran. If the output shows key-not-found errors, the
semantic gate did not run. Fall back to running `crucible prewrite
review <spec-path> --checklist`, which needs no key: it renders
every assertion as a check for you to evaluate inline, and you
record the completed checklist in the
workbench. A FAIL on any error-severity check blocks step 5 the same
as a failed API run.

### 4. Plan the execution

Break the spec into tasks. Each task carries binding details (exact
values, exact interfaces, not "roughly like this") and its own
verification step — how you'll know that task, specifically, is done.
A plan that only says what to build without saying how to check it
isn't a plan an independent reviewer or a fresh subagent can execute
against.

### 5. Execute with gates

Work one task at a time, solo or dispatching subagents. After every
task, run an independent review pass — `crucible review` plus whatever
persona skills fit the change, or a second agent with no stake in the
implementation. The author never grades their own homework: the person
or agent who wrote the code is the worst-positioned to spot what's
wrong with it. Append every completed task to the workbench ledger
(`ledger.md`, below) before moving to the next one — the ledger is the
record that survives a context loss even when memory doesn't.

When step 5 runs with subagents — a controller dispatching fresh
workers and an independent reviewer rather than one agent doing
everything — don't re-derive that discipline from scratch. Run
`crucible skills discover meta/engineering-loop` and read its
`knowledge/the-loop-at-scale.md`: the controller-never-builds rule,
the fix-loop shape, and the escalation path after repeated failed
fixes all live there.

When the change touches user-facing surfaces, the independent review
includes the UX pass — `uiux-engineer`, with `accessibility-engineer`
alongside — and its `TASTE (human call)` items go to the human with
the review, unresolved.

### 6. Prove and close

Run the project's full checks. Take one skeptical pass over the whole
change — not what you meant to build, what's actually there — and try
to break it. That's `meta/but-for-real`: it activates automatically
whenever work is about to be declared done, and it forces exactly one
fix wave, not an open-ended loop of second-guessing (`crucible skills
discover meta/but-for-real`). Once the change is verified, hand it off
per the team's own process.

This step mandates verification, not integration. The loop ends at
"verified and handed off" — it has no opinion on branch strategy,
review-tool conventions, or how the change ultimately reaches
production, and it never prescribes any of that.

### 7. Keep the learning

Write the learning record and decision log to the notes folder before
moving on to the next piece of work. `meta/teach-me` is the standing
workspace this belongs in — a learning record per non-obvious lesson,
grounded in why the work mattered. `crucible skills discover
meta/teach-me`. The workbench's `decisions.md` (see below) stays the
working record throughout the loop; at close, distill or copy its
contents into the learning record rather than moving it — the
workbench copy is not superseded.

## The workbench

Spec, plan, ledger, and decision log are in-between artifacts, not
deliverables — they live in a per-project workbench outside the repo
and are never committed. Resolve the workbench location, in this exact
order, before the first artifact is written:

1. A `workbench:` key in `.crucible/teach.yaml` (project), then
   `~/.claude/crucible/teach.yaml` (user) — an explicit directory,
   e.g. an in-house notetaker's project folder.
2. Else a `vault:` key set (same project-then-user cascade) →
   `<vault>/crucible-work/<project-slug>/`, where project-slug is the
   project directory name, slugified.
3. Else fall back to `.crucible/workbench/` inside the project — and
   before writing anything there, verify it's gitignored: look for a
   `.crucible/workbench/` line in `.gitignore`, or run `git
   check-ignore .crucible/workbench/` to confirm. If it isn't ignored,
   add exactly `.crucible/workbench/` as the ignore line — never a
   broader `.crucible/` pattern, which would also hide files `crucible
   init` creates to be committed. Never write a workbench artifact
   into a directory git would track.

Artifact names inside the workbench, always:

- `spec.md` — the binding spec from step 3.
- `plan.md` — the task breakdown from step 4.
- `ledger.md` — append-only. Never edit or delete a past entry; only
  add new ones. After any context loss, recover by reading the ledger
  alongside the project's VCS history — between the two, you can
  reconstruct exactly what was done and what's still open without
  redoing finished work.
- `decisions.md` — the decision log from step 2, carried through the
  rest of the loop.

Never commit workbench artifacts to the project repository, regardless
of which resolution branch produced the workbench path.

## Do NOT

- Never commit workbench artifacts (`spec.md`, `plan.md`, `ledger.md`,
  `decisions.md`) to the repo, under any workbench resolution branch.
- Never prescribe branch, merge, or CI mechanics in step 6 or anywhere
  else in this loop — handoff means verified, not integrated a
  particular way.
- Never skip the independent review in step 5 because a change "looks
  small." Size is not a review-exemption criterion.
- Never start step 5 before the spec from step 3 has passed prewrite
  review.
- Not for beginners. Someone who has never shipped software before
  should start at `meta/engineering-loop`, not here.

## Related

- `meta/engineering-loop` — the six-step, plain-language on-ramp for
  someone who hasn't shipped software before. This loop is what it
  steps up to once the work is professional.
- `meta/wait-what`, `meta/brainstorming`, `meta/challenge`,
  `meta/spec-validator`, `meta/but-for-real`, `meta/teach-me` — the
  carrier skills for steps 1, 2 (brainstorming and challenge both),
  3, 6, and 7.
- `meta/engineering-loop`'s `knowledge/the-loop-at-scale.md` — the
  controller/subagent discipline for step 5 at scale.
