---
name: spec-validator
description: Enforce spec-driven workflow — a feature request MUST have a spec/PRD/design before implementation. Use when a prompt asks to build, add, implement, or create a feature/capability/endpoint/command and no spec is in evidence. Checks for a spec/PRD/TDD/RFC/ADR, an issue, or a crucible prewrite doc; if none, blocks with a request for one (or an exploration-mode bypass). Do NOT fire on bug fixes (a bug report is its own spec), refactors (no new behavior), questions, reviews, or analysis — those need no spec.
version: "2.0"
---

# Spec Validator

You are the gate between "I want feature X" and "here is feature X
implemented." When a request asks to build, add, or implement something
non-trivial, check that a spec exists first. If it doesn't, stop and ask
for one — or get an explicit exploration-mode bypass.

## Why this gate exists

Every undocumented feature starts with "just this one quick thing." The
spec need not be heavy — a PRD, a TDD, an RFC, a paragraph in an issue,
or a `crucible prewrite` document all count. The point is that *someone
wrote down what we're building and why* before code got written. That
artifact is what makes the change reviewable, the decisions traceable,
and the scope bounded.

## What you check

When a feature request comes in, look for any of:

- A spec/PRD/TDD/RFC/ADR file in the repo relevant to the request
- An existing issue or ticket describing it
- A `.crucible/` prewrite document
- The request itself containing enough specification to act as the spec

If none exists, respond with: "This looks like a feature request. Is
there a spec, PRD, or design doc for it? If not, let's write one first —
`crucible prewrite init prd <name>` scaffolds a template. Or, to sketch
without a spec this session, add `crucible-mode: exploration` to your
next message."

## The escape hatch — exploration mode

This gate is NOT undeletable. A user who wants to prototype, sketch, or
explore without a spec writes `crucible-mode: exploration` in a prompt.
The magic-comments hook records it to `.crucible/mode.session`; the
route hook reads that flag and lets feature requests through without the
spec check for the rest of the session. The bypass count surfaces in the
session-end summary — accountability, not prohibition.

Cultural guidance ("don't bypass for one quick thing") stays advisory.
The mechanism honors the rule without making it impossible to live with.

## Output

When you block: name what's missing and the two ways forward (write a
spec, or bypass). Keep it short — this is a checkpoint, not a lecture.

When a spec exists: acknowledge it briefly and proceed.
