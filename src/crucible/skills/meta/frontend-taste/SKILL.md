---
name: frontend-taste
description: Behavioral guidelines for building user-facing UI — a one-line design read before coding, anti-default discipline, and hard rules for state coverage, motion, and copy. Use when building or styling frontend/UI work — landing pages, dashboards, components, visual styling. Do NOT use for backend or non-visual work, and do NOT fire on bare "design" (database schema, API design, system design are not UI work).
version: "1.0"
---

# Frontend Taste

The generation-side counterpart to `meta/coding-discipline`: activates
on frontend/UI building intent, not on implementation intent generally.
Professional register — this shapes how UI gets built, not whether to
build it.

> **Attribution.** Distilled from Leonxlnx/taste-skill (MIT, © 2026
> Leonxlnx), Dragoon0x/taste-skills (MIT, © 2026 Dragoon), and
> anthropics/skills frontend-design (Apache-2.0, © 2025 Anthropic,
> PBC). See THIRD-PARTY-NOTICES.md.

## 1. State the design read first

Before writing UI code, state one line: what this is, who it serves,
what tone fits. This is a stated decision, not an assumed one — if you
can't state it, you don't know enough yet to make the choices below.

## 2. Anti-default discipline

Generated interfaces cluster around a small number of default looks
regardless of the brief — full detail and detection signals live in
`design-taste.md`. Don't reach for a cluster look, or the nearest
template answer (three equal feature cards, a centered hero over a
dark mesh gradient, Inter + slate-900 because it's fastest), when an
axis is free. Spend the freedom on a choice specific to this brief.

**Design-system-first rule:** where the project already has a design
system, compliance with it outranks every rule in this skill. This
pass never introduces a competing visual language.

Spend boldness in one place — one signature element the page is
remembered by, everything around it quiet and disciplined. A page
that tries to be bold everywhere reads as loud, not confident.

## 3. Hard rules (binding)

These are not taste — treat them as requirements to satisfy before UI
work is done:

- **Design system first** when one exists (see above).
- **Full interactive-state matrix** — hover, focus, active, disabled,
  loading, empty, error. A component missing a state is not done.
- **Reduced motion respected** — anything beyond a basic hover/active
  transition must honor `prefers-reduced-motion`.
- **Purposeful animation only** — every animation serves feedback,
  orientation, emphasis, or delight; if you can't name which, drop it.
- **Copy per `ux-writing.md`** — active voice, exact verbs, one name
  per action through a flow, errors that explain and direct.
- **Responsive floor** — the layout holds across breakpoints, not just
  the viewport it was eyeballed in.
- **Visible keyboard focus** — no suppressed or invisible focus rings,
  on any interactive element, ever.

## 4. Do NOT

- Not for backend or non-visual work — this skill has nothing to say
  about a database schema, an API contract, or a background job.
- Never redesign surfaces the task didn't touch. Fix or build what was
  asked; leave the rest of the product alone.
- Never override an existing design system for taste. A design system
  wins every time, on this pass, with no exception.
- Taste disagreements with the human are theirs to win. Where this
  skill's guidance and the human's stated preference conflict on a
  subjective call, defer — state the tradeoff once, then follow their
  call.

## Knowledge

Tier-3 pointers — load by name via the knowledge loader:

- `design-taste.md` — typographic scale, spacing rhythm, color roles,
  hierarchy, density, materiality, the three AI-default cluster looks,
  anti-default discipline.
- `motion-interaction.md` — purposeful motion, forbidden animation
  patterns, mandatory reduced motion, the full interactive-state
  matrix, timing and feedback.
- `ux-writing.md` — copy as design material, active voice and exact
  verbs, one name per action, direct errors, inviting empty states.

## Relationship to other Crucible skills

- `meta/coding-discipline` — the general counterpart this skill
  specializes for frontend/UI work. Both apply together on a UI change;
  this skill adds the visual and copy rules coding-discipline doesn't
  cover.
- `uiux-engineer` — the detection-side counterpart. This skill guides
  building the UI; `uiux-engineer` reviews it afterward, citing the
  same rule/taste split (objective rules as findings, subjective calls
  under `TASTE (human call):`).
