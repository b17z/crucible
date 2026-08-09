---
name: brainstorming
description: Use when about to do any creative work — creating features, building components, adding functionality, or modifying behavior — before implementation starts. Explores user intent, requirements, and design through one-question-at-a-time dialogue, then gates implementation behind a presented, approved design. Do NOT use for bug fixes (the bug report is its own spec), pure refactors, or questions — those need no design dialogue.
version: "2.0"
---

> Adapted from obra/superpowers (MIT, © 2025 Jesse Vincent). See THIRD-PARTY-NOTICES.md.

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural
collaborative dialogue.

Start by understanding the current project context, then ask questions
one at a time to refine the idea. Once you understand what you're
building, present the design and get user approval.

## The hard gate

Do NOT invoke any implementation skill, write any code, scaffold any
project, or take any implementation action until you have presented a
design and the user has approved it. This applies to EVERY project
regardless of perceived simplicity.

## Anti-pattern: "this is too simple to need a design"

Every project goes through this process. A todo list, a single-function
utility, a config change — all of them. "Simple" projects are where
unexamined assumptions cause the most wasted work. The design can be
short (a few sentences for truly simple projects), but you MUST present
it and get approval.

## Checklist

Complete these in order:

1. **Explore project context** — check files, docs, recent commits.
2. **Ask clarifying questions** — one at a time, understand
   purpose/constraints/success criteria.
3. **Propose 2-3 approaches** — with trade-offs and your recommendation.
4. **Present design** — in sections scaled to their complexity, get user
   approval after each section.
5. **Write design doc** — save it and commit.
6. **Spec self-review** — quick inline check for placeholders,
   contradictions, ambiguity, scope (see below).
7. **User reviews written spec** — ask user to review the spec file
   before proceeding.
8. **Transition to implementation** — once approved, hand off to
   whatever this project uses to turn a spec into an implementation plan.

**The terminal state is handing off to implementation planning.** Do not
jump straight to writing code, and do not invoke any other creative or
design skill after this one — the next step is planning the
implementation, not re-exploring the idea.

## The process

**Understanding the idea:**

- Check out the current project state first (files, docs, recent
  commits).
- Before asking detailed questions, assess scope: if the request
  describes multiple independent subsystems (e.g. "build a platform with
  chat, file storage, billing, and analytics"), flag this immediately.
  Don't spend questions refining details of a project that needs to be
  decomposed first.
- If the project is too large for a single spec, help the user decompose
  into sub-projects: what are the independent pieces, how do they
  relate, what order should they be built? Then brainstorm the first
  sub-project through the normal design flow. Each sub-project gets its
  own spec → plan → implementation cycle.
- For appropriately-scoped projects, ask questions one at a time to
  refine the idea.
- Prefer multiple choice questions when possible, but open-ended is fine
  too.
- Only one question per message — if a topic needs more exploration,
  break it into multiple questions.
- Focus on understanding: purpose, constraints, success criteria.

**Exploring approaches:**

- Propose 2-3 different approaches with trade-offs.
- Present options conversationally with your recommendation and
  reasoning.
- Lead with your recommended option and explain why.
- YAGNI ruthlessly — remove unnecessary features from every approach and
  design.

**Presenting the design:**

- Once you believe you understand what you're building, present the
  design.
- Scale each section to its complexity: a few sentences if
  straightforward, up to 200-300 words if nuanced.
- Ask after each section whether it looks right so far.
- Cover: architecture, components, data flow, error handling, testing.
- Be ready to go back and clarify if something doesn't make sense.

**Design for isolation and clarity:**

- Break the system into smaller units that each have one clear purpose,
  communicate through well-defined interfaces, and can be understood and
  tested independently.
- For each unit, you should be able to answer: what does it do, how do
  you use it, and what does it depend on?
- Can someone understand what a unit does without reading its internals?
  Can you change the internals without breaking consumers? If not, the
  boundaries need work.
- Smaller, well-bounded units are also easier for you to work with — you
  reason better about code you can hold in context at once, and your
  edits are more reliable when files are focused. When a file grows
  large, that's often a signal it's doing too much.

**Working in existing codebases:**

- Explore the current structure before proposing changes. Follow
  existing patterns.
- Where existing code has problems that affect the work (e.g. a file
  that's grown too large, unclear boundaries, tangled responsibilities),
  include targeted improvements as part of the design — the way a good
  developer improves code they're working in.
- Don't propose unrelated refactoring. Stay focused on what serves the
  current goal.

## After the design

**Documentation:**

- Write the validated design (spec) to a durable location in the repo
  (this project keeps specs under `docs/specs/YYYY-MM-DD-<topic>.md` —
  follow whatever convention is already in use).
- Commit the design document to git.

**Spec self-review:**

After writing the spec document, look at it with fresh eyes:

1. **Placeholder scan** — any "TBD", "TODO", incomplete sections, or
   vague requirements? Fix them.
2. **Internal consistency** — do any sections contradict each other?
   Does the architecture match the feature descriptions?
3. **Scope check** — is this focused enough for a single implementation
   plan, or does it need decomposition?
4. **Ambiguity check** — could any requirement be interpreted two
   different ways? If so, pick one and make it explicit.

Fix any issues inline. No need to re-review — just fix and move on.

**User review gate:**

After the spec review loop passes, ask the user to review the written
spec before proceeding:

> "Spec written and committed to `<path>`. Please review it and let me
> know if you want to make any changes before we start writing out the
> implementation plan."

Wait for the user's response. If they request changes, make them and
re-run the spec review loop. Only proceed once the user approves.

**Implementation:**

- Hand off to whatever this project uses to turn an approved spec into
  an implementation plan. Do not skip straight to code.
