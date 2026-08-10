---
name: Design Taste
description: Typography, spacing, color, hierarchy, density, materiality, and default-detection for visual design
triggers: [design, ui, ux, frontend, layout, typography, color, visual]
type: principle
---

> Adapted from Leonxlnx/taste-skill, Dragoon0x/taste-skills, and
> anthropics/skills frontend-design (MIT, © 2026 Leonxlnx; MIT, © 2026
> Dragoon; Apache-2.0, © 2025 Anthropic, PBC). See
> THIRD-PARTY-NOTICES.md.

# Design Taste

Rules for judging and making visual decisions. Cite these against a diff
in review; follow them while building a UI. Where a project has its own
design system, that system outranks every rule below — compliance with
an existing system is not a taste question.

---

## Typographic scale and pairing

- A type scale is a system, not a pile of sizes picked by feel. Use a
  mathematical ratio between steps (1.25, 1.333, 1.5) and cap it at
  4-6 sizes per screen. If a size is not on the scale, it should not
  exist — a reviewer can point at an off-scale `font-size` as a
  finding, not a preference.
- Limit weights to what the hierarchy needs: 1-2 weights reads as
  discipline (scale and space carry hierarchy instead); 3 is the
  normal working range (body, emphasis, headline); 4 or more means
  either the system genuinely demands it or no decision was made.
- Line height varies by role and must be set per size, not copied
  everywhere: body text 1.5-1.7x, headlines 1.1-1.3x, UI labels
  1.2-1.4x. One line-height value applied to every text size is a
  finding, not a style choice.
- Letter spacing: leave body text alone (the typeface already handles
  it). Add 2-5% tracking to all-caps labels only. Only consider
  tightening large display text (72px and up).
- Pair a display face and a body face deliberately for the brief in
  front of you, not the pairing reached for on the last three
  projects. Reaching for Inter as an unexamined default, or a serif
  display face because the brief sounds "creative," are both
  default-detection signals (see below) — name the reason the pairing
  fits this brief, or change it.
- When emphasizing a word inside a headline, use italic or bold of the
  *same* family. Mixing in a second family for one word to "add
  interest" reads as an accident, not a decision.

## Spacing rhythm and grid consistency

- Spacing comes from a scale (4, 8, 16, 24, 32, 48, 64 or an
  equivalent progression), not arbitrary values. Two near-identical
  values that don't match (15px next to 16px) is a specific,
  citable defect — it reads as an error, not a texture.
- Use proximity to encode relationship: things that belong together
  sit close, things that don't sit apart. Identical spacing applied
  everywhere regardless of relationship erases the information
  spacing was supposed to carry.
- Outer margins and generous whitespace are not "space left over" —
  in most well-composed layouts whitespace is 40-60% of the total
  area. Cramming content in to "use the space" is a finding to raise,
  not a matter of taste.
- Rhythm should match content energy: regular, even spacing reads as
  orderly (data, tables, lists); a mostly-regular rhythm with
  intentional breaks reads as dynamic (editorial, marketing). A
  to-do app with syncopated rhythm, or an editorial page with
  mechanical regularity, is a mismatch worth flagging.

## Color roles and calibration

- Every color earns a named role: structural (background, border),
  semantic (error, success, warning — and semantic colors must mean
  the same thing everywhere they appear), accent (primary action,
  emphasis), or decorative. A color with no role, or a role split
  across colors inconsistently (red as both "featured" and "error"),
  is a finding.
- Neutrals should carry 80-90% of the visual weight. Color is the
  accent, not the foundation — a palette that leans on more than one
  or two saturated colors to do structural work has usually skipped a
  design decision, not made one.
- A 2-3 color palette used with intention outperforms a 7-color
  palette used without one. Before adding a color, ask whether
  removing it would lose information; if not, it does not earn its
  place.
- Verify contrast in context, not swatch-by-swatch — the same blue
  reads differently against warm gray than against cool white. WCAG
  AA is the floor for all foreground/background pairs, in both light
  and dark mode.
- Once an accent is chosen for a surface, it holds for that whole
  surface. A warm-neutral page that picks up a stray blue CTA
  somewhere downstream, or a rose accent that turns teal in the
  footer, is a consistency defect, not a variation.

## Hierarchy: where the eye goes first, and is it intentional

- Every screen needs one clear primary element. If everything is
  emphasized, nothing is — two elements competing at the same
  hierarchy level, with no intentional tension as the point, is a
  finding.
- Hierarchy is built from at least two of: scale, weight, contrast,
  color, space, position — not scale alone, which produces flat,
  monotonous layouts even when sizes vary.
- Visual weight should match content priority. Test it directly: cover
  half the screen and check whether the most important thing is still
  obvious. If navigation reads louder than the content it serves, that
  is backwards and citable.
- Position carries hierarchy too: top-left is seen first in
  left-to-right reading, center pulls attention, bottom-right gets
  ignored unless hierarchy is deliberately pulling the eye there.

## Density matched to use case

- Density is a decision tied to the work being done, not a global
  style. Dense layouts suit data tools, comparison tasks, experienced
  users, and long sessions. Low density suits content meant to be
  read rather than scanned, new users, and focus-critical moments.
- Applying one density philosophy everywhere is itself a finding — a
  settings page and a marketing page inside the same product are
  allowed, and often required, to feel different.
- At high density, generic card containers stop paying for themselves;
  let data breathe in a plain layout with hairline separators instead
  of wrapping every row in a box.

## Materiality and shadows

- Use elevation (cards, shadows) only when it communicates real
  hierarchy — a group that doesn't need to be lifted off the page
  should be grouped with a border or negative space instead.
- Tint shadows toward the background hue. A pure-black drop shadow on
  a light, warm background is a mismatch a reviewer can name directly.
- Pick one corner-radius scale for the whole surface and hold it:
  all-sharp, all-soft, or all-pill for interactive elements. Mixed
  radii are allowed only under a documented, followed rule (for
  example, "buttons are pill, cards are 16px, inputs are 8px") — a
  round button dropped into an otherwise-square layout without that
  rule is broken, not eclectic.

---

## The three AI-default cluster looks (default-detection signals)

Generated interfaces cluster around a small number of default looks
regardless of the brief. None of the three below is wrong on its own
merits — each is legitimate for some brief. What makes each one a
finding is that it shows up **because it is the default**, not because
someone chose it for this brief. **A default is not a choice.** When one
of these appears, the review question is not "is this ugly" but "was
this decided, or did it just happen."

1. **Warm cream + high-contrast serif + terracotta accent** — a
   background near `#F4F1EA`, paired with a high-contrast serif display
   face and a single terracotta/clay/oxblood accent. This is the
   reflexive answer to "premium," "editorial," or "artisan" briefs.
   Concrete tells to watch for: backgrounds in the `#f5f1ea`–`#fbf8f1`
   "warm paper" family, accents in the `#b08947`–`#9a2436`
   "brass/clay/oxblood" family, near-black warm text
   (`#1a1714`–`#1b1814`). If the brief didn't name this palette and
   nobody can say why *this* brand needs it, it's a default.
2. **Near-black background + a single bright acid-green or vermilion
   accent** — the "dark tech" default. Legitimate for a genuinely
   technical, nocturnal, or hacker-coded brand; a default-detection
   flag everywhere else, especially when paired with generic
   glassmorphism or purple/blue AI-glow gradients.
3. **Broadsheet hairline rules, zero border-radius, dense
   newspaper-like columns** — the "serious publication" default.
   Legitimate for editorial or data-dense work that actually behaves
   like a publication; a flag when applied to a product that has
   nothing to do with reading long-form text in columns.

**Where the brief pins down a direction, follow it exactly** — including
when it explicitly asks for one of these three looks. The point is not
banning them; it's refusing to let them fill in an axis the brief left
open by default.

## Anti-default discipline

- Before writing UI code, state the design read in one line: what this
  is, who it's for, what tone fits. A design that skipped this step
  and landed on a cluster look anyway is exactly the failure mode the
  cluster-look list exists to catch.
- Where an axis is free (the brief didn't specify it), spend that
  freedom on a choice specific to this brief — not on the nearest
  template answer. Reaching for three equal feature cards, a centered
  hero over a dark mesh gradient, or Inter + slate-900 because it's
  the fastest thing to reach for, are all default-detection signals
  in the same family as the three cluster looks.
- Spend boldness in one place. Pick a single signature element the
  page will be remembered by, keep everything around it quiet and
  disciplined, and cut decoration that doesn't serve the brief. A
  page that tries to be bold everywhere reads as loud, not confident.
- Not every default is bad — sometimes the default *is* the right
  choice for a boring, trust-first, or accessibility-critical brief.
  The rule is "was this decided," not "was this avoided."
