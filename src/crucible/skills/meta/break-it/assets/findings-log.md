# Break-It Findings Log

> Product: <name + commit/version under test>
> Tester: <you / persona>
> Date: <YYYY-MM-DD>
> Surface mapped: <link to the entry-point + action inventory you built first>

---

## Session log

Each session: one charter, one persona, one tour, ≤30 min. Copy the block per session.

### Session N — <charter, e.g. "impatient VP on the daily brief">
- **Persona:** <confused VP / impatient exec / over-truster / off-happy-path / adversary / edge>
- **Tour:** <obsessive-compulsive / saboteur / interruption / landmark / antisocial / couch-potato / supermodel>
- **Notes (running):**
  - <observation>
  - <observation>

---

## Findings

Copy one block per finding. Severity by REAL-WORLD CONSEQUENCE (see SKILL.md prime directive), not by how dramatic it looks.

### F-NNN — <one-line title>
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW
- **Class:** wrong-irreversible-action | confidently-wrong-output | data-exposure | dead-end/silent-fail | confusing-UX | cosmetic
- **Persona / tour:** <which session surfaced it>
- **Reproduction steps:**
  1. <exact step>
  2. <exact step>
  3. <exact step>
- **What happened:** <observed behavior>
- **What a user would expect:** <expected behavior>
- **If an agent action — reversible?** yes / no / partial — <what it would take to undo>
- **Guardrail involved?** <which confirmation/preview/undo, and whether it held>
- **Should become a regression eval?** yes / no — <why>

---

## Severity-sorted summary (fill at handoff)

| ID | Severity | Title | Class | Reversible? |
|----|----------|-------|-------|-------------|
| | | | | |

## Top 3 to fix before a VP touches it
1.
2.
3.

## Recommended regression evals
- <finding ID → eval description>
