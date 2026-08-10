---
name: UX Writing
description: Copy as design material - active voice, consistent naming, direct errors, and inviting empty states
triggers: [copy, ux writing, microcopy, error message, empty state, button label]
type: principle
---

> Adapted from anthropics/skills frontend-design (Apache-2.0, © 2025
> Anthropic, PBC). See THIRD-PARTY-NOTICES.md.

# UX Writing

Rules for judging and writing interface copy. Cite these against a diff
in review; follow them while writing the strings a user will actually
read.

---

## Copy is design material

Words appear in an interface for one reason: to make it easier to
understand and therefore easier to use. Copy is not decoration laid on
top of a finished design — it's material with the same weight as
spacing and color, and it deserves the same intentionality. Before
writing any string, ask what the interface needs to say at that moment,
and what phrasing gets the person to their next step fastest. A design
review that skips the copy and only checks layout has skipped half the
design.

## Write from the user's side of the screen

Name things by what people control and recognize, not by how the
system happens to be built. A person manages notifications, not
"webhook config." A person turns something on, not "toggles a feature
flag." Describe what a control does in plain terms rather than selling
it — "Deletes this project and everything in it" beats "Unlock a
cleaner workspace." Specific and literal always beats clever. If a
string only makes sense to someone who's read the codebase, it's
wrong, regardless of how accurate it is.

## Active voice, exact verbs

Default to active voice. A control should say exactly what happens when
it's used: **"Save changes,"** not "Submit." "Submit" describes the
mechanism (a form is being posted somewhere); "Save changes" describes
the outcome the user cares about. This is a specific, checkable
distinction — a reviewer can point at a vague verb (`Submit`, `OK`,
`Confirm`, `Proceed`) and ask what it's actually doing, and a builder
should be able to answer in the label itself.

## One action keeps one name through a flow

Once an action has a name, that name doesn't change as the user moves
through the flow. The button that says "Publish" produces a
confirmation that says "Published" — not "Success," not "Done," not
"Your content has been submitted." The vocabulary of an interface is
the signposting someone uses to navigate it; renaming the same action
partway through breaks that signposting and makes the user re-verify
they're still doing the thing they started. This applies across a
whole surface, not just one screen: if two buttons in the same product
both start a signup flow, they should use the same label, not "Get
started" in one place and "Sign up free" in another.

## Errors explain and direct — never apologize, never go vague

Treat failure as a moment for direction, not for mood. An error message
has two jobs: say what went wrong, and say what to do about it. It
should do both in the interface's own voice, not perform an apology on
a person's behalf ("Oops! Something went wrong" tells the user
nothing and asks for sympathy instead of giving them a next step).

- **Never vague.** "An error occurred" or "Something went wrong" is a
  finding, not an acceptable fallback — even a generic failure can name
  what was being attempted ("Couldn't save your changes. Try again.").
- **Never apologetic.** "Sorry," "Oops," and similar filler add tone
  without adding information and should be cut in favor of the actual
  explanation.
- **Scoped to where it happened.** An inline, field-level error next to
  the input that failed beats a disconnected banner or toast for
  anything the user needs to fix in place.
- **Direct about the fix.** "Password must be at least 8 characters" is
  a finding fixed; "Invalid password" is not — it names the problem but
  not the resolution.

## Empty states invite action

An empty screen is not the absence of content — it's an invitation.
Every empty state should tell the person what belongs there and give
them the action that fills it in, rather than leaving a blank space
that only communicates "nothing here yet." A list with zero items and
no call to action is a finding: the empty state was left undesigned,
not deliberately minimal.

## Register

Keep the register conversational and tuned to the product: plain verbs,
sentence case, no filler. Match tone to the brand and the audience, but
don't let tone override clarity — a playful brand voice still needs to
say what a button does. Let each element do exactly one job: a label
labels, an example demonstrates, a helper text helps. When one string
is quietly doing two jobs (a label that's also trying to be a pitch), split
it or cut the excess.
