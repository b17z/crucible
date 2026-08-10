---
name: Motion and Interaction
description: Purposeful motion, forbidden animation patterns, reduced motion, and the full interactive-state matrix
triggers: [motion, animation, interaction, transition, hover, focus, accessibility]
type: principle
---

> Adapted from Leonxlnx/taste-skill and Dragoon0x/taste-skills
> (MIT, © 2026 Leonxlnx; MIT, © 2026 Dragoon). See
> THIRD-PARTY-NOTICES.md.

# Motion and Interaction

Rules for judging and building motion and interactive state. Cite these
against a diff in review; follow them while building a UI.

---

## Purposeful motion only

Animation serves exactly four purposes. If a piece of motion doesn't
serve one of them, it shouldn't exist — and the reviewer's question for
any animation is "which of the four, and can you say so in one
sentence."

1. **Feedback** (roughly 50-150ms) — confirms an action was received:
   button press, toggle, form submit.
2. **Orientation** (roughly 200-400ms) — shows spatial relationships: a
   sidebar sliding in, a modal scaling from its trigger.
3. **Emphasis** (roughly 300-600ms) — draws attention: a notification
   pulse, a new element fading in. Rare and meaningful, not routine.
4. **Delight** (variable, brief, skippable) — an emotional touch: loading
   personality, a completion moment. Never blocking.

"It looked cool" is not a fifth purpose. Before adding any animation,
name which of the four it serves; if you can't, drop it. Restraint is
itself a taste signal — the best-animated interfaces are the ones where
the animation isn't the thing you notice. Duration should scale with
purpose: the more functional the motion, the faster it should be.
Easing should be consistent across the whole system, and physics-based
(ease-out on arrival, ease-in on departure) rather than linear —
bouncy or elastic easing belongs to celebration moments, not navigation.

## Forbidden animation patterns

These are specific, citable defects, not stylistic disagreements:

- **Loading animations that outlast the actual load.** The animation
  should track real work, not manufacture a minimum wait.
- **Page transitions that delay content access.** Motion should never
  be the thing standing between a user and the content they came for.
- **Hover effects on every element.** Motion should guide attention to
  what matters, not create ambient noise across the whole page. If
  everything moves on hover, nothing is being pointed at.
- **`window.addEventListener("scroll", ...)`, or scroll position stored
  in component state on every frame.** Both run on every scroll frame
  with no batching and are jank-prone. Use a scroll-linked motion
  primitive (`useScroll`-style hooks, `ScrollTrigger`,
  `IntersectionObserver`, or CSS `animation-timeline: view()`) instead.
- **`requestAnimationFrame` loops that write to component state.**
  Continuous state writes re-render the tree on every frame. Use a
  motion-value primitive that lives outside the render cycle instead.
- **Animating layout properties** (`top`, `left`, `width`, `height`)
  instead of `transform` and `opacity`. The former forces layout on
  every frame; the latter is compositor-only and cheap.
- **Motion claimed but not shown, or shown but broken.** A page that
  promises rich motion and ships static, or ships motion with
  cut-off scroll triggers, jumpy entrances, or missing cleanup, is
  worse than a page that commits to no motion at all. Pick one and
  execute it fully.
- **Marquees, infinite loops, and scroll-hijacking used more than once
  per page**, or used where the content isn't actually a sequence that
  benefits from it. One of these per page, in the one place it earns
  its keep — not sprinkled throughout.

## Reduced motion is mandatory

- Any motion beyond a basic `:hover`/`:active` transition must honor
  `prefers-reduced-motion`. This is not a nice-to-have and not
  negotiable — its absence is a finding at the same severity as a
  missing focus state.
- Gate animation behind `@media (prefers-reduced-motion: no-preference)`,
  or provide an explicit override under
  `@media (prefers-reduced-motion: reduce)` that disables it. In a
  component-based motion library, check the reduced-motion signal and
  degrade to static rather than skipping the check.
- Infinite loops, parallax, scroll-hijacking, and any physics-driven
  hover effect must collapse to static or instant under reduced
  motion — "slightly less motion" is not the same as respecting the
  preference.

## The interactive-state matrix

A component is not done until every state in the matrix below has been
designed, not just the default and the happy path. Missing a state is
a finding, not a follow-up:

- **Hover** — signals that an element is interactive before it's
  activated. Should not be applied to every element on the page (see
  forbidden patterns above); reserve it for things that actually do
  something.
- **Focus** — must be visible for keyboard users on every interactive
  element, with no exceptions carved out for visual tidiness. A
  missing or suppressed focus ring is an accessibility regression, not
  a style preference.
- **Active** — the pressed/engaged moment. A small, immediate physical
  response (a slight downward shift or scale-down) reads as a real
  push rather than a static click target.
- **Disabled** — must be visually distinct from both the enabled and
  loading states, and must communicate *why* it's disabled where that
  isn't obvious from context alone.
- **Loading** — prefer a skeleton that matches the shape of the content
  arriving over it, rather than a generic spinner that gives no sense
  of what's coming.
- **Empty** — an empty state is composed deliberately and tells the
  user how to populate it. A blank space with no next step is a
  finding, not a minimal design.
- **Error** — errors are clear and scoped to where they occur: inline
  next to the form field that failed, contextual and transient for
  toast-style notices. A generic, disconnected error message is a
  finding.

Before any interactive element ships, verify contrast holds in every
state above, not just the resting one — placeholder text, focus rings,
helper text, and error text all need to clear WCAG AA against their
background, and a state that only reads correctly at rest has not
actually been designed.

## Timing and feedback

- Tie duration to distance and purpose: feedback is fast (50-150ms),
  orientation gives the eye time to track spatial movement
  (200-400ms), emphasis is deliberately slower and rarer (300-600ms).
  A feedback-purpose animation running at emphasis-length duration
  reads as sluggish, not considered.
- Every user-initiated action needs feedback of some kind, even if it's
  just an `:active` state change — an action with no acknowledgment at
  all reads as broken, not as restraint.
- Consistency across the system matters more than any single
  animation's cleverness: one easing curve, one duration scale, reused
  everywhere motion appears, is what makes an interface feel
  considered rather than assembled from parts.
